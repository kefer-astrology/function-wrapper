from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Any
import math
import sys

# Standardized imports with fallback for direct execution
try:
    from module.models import (
        Aspect, AspectDefinition, AstroModel, BodyDefinition, CelestialBody, ChartMode, DateRange,
        EngineType, ChartConfig, ChartInstance, Location, ModelOverrides, ModelSettings, Sign,
        ObjectType, Workspace
    )
except ImportError:
    from models import (
        Aspect, AspectDefinition, AstroModel, BodyDefinition, CelestialBody, ChartMode, DateRange,
        EngineType, ChartConfig, ChartInstance, Location, ModelOverrides, ModelSettings, Sign,
        ObjectType, Workspace
    )

try:
    from module.utils import Actual, default_ephemeris_path, ensure_aware, prepare_horoscope, compute_vernal_equinox_offset, _safe_get_attr
except ImportError:
    from utils import Actual, default_ephemeris_path, ensure_aware, prepare_horoscope, compute_vernal_equinox_offset, _safe_get_attr

try:
    from module.z_visual import build_radix_figure
except ImportError:
    from z_visual import build_radix_figure

from kerykeion import AstrologicalSubject, KerykeionChartSVG, Report, KerykeionPointModel
from pandas import DataFrame

try:
    from skyfield.api import load, load_file, Topos
    JPL = True
except ImportError:
    JPL = False
    print("NASA JPL Ephemeris deactivated", file=sys.stderr)


# ─────────────────────
# 🗺️ COMPUTATION MAPPING SYSTEM
# ─────────────────────

def _get_kerykeion_object_mapping() -> Dict[str, str]:
    """Map object IDs to kerykeion AstrologicalSubject attribute names.
    
    Returns a dict mapping object_id -> attribute_name for kerykeion extraction.
    """
    return {
        # Planets (standard)
        "sun": "sun",
        "moon": "moon",
        "mercury": "mercury",
        "venus": "venus",
        "mars": "mars",
        "jupiter": "jupiter",
        "saturn": "saturn",
        "uranus": "uranus",
        "neptune": "neptune",
        "pluto": "pluto",
        # Angles
        "asc": "asc",
        "ascendant": "asc",
        "desc": "desc",
        "descendant": "desc",
        "mc": "mc",
        "midheaven": "mc",
        "ic": "ic",
        "imum_coeli": "ic",
        # Lunar nodes
        "north_node": "north_node",
        "south_node": "south_node",
        "true_north_node": "true_north_node",
        "true_south_node": "true_south_node",
        # Calculated points
        "lilith": "lilith",
        "black_moon_lilith": "lilith",
        "chiron": "chiron",
        "ceres": "ceres",
        "pallas": "pallas",
        "juno": "juno",
        "vesta": "vesta",
        # Houses (will be handled separately via houses_list)
        "house_1": "house_1",
        "house_2": "house_2",
        "house_3": "house_3",
        "house_4": "house_4",
        "house_5": "house_5",
        "house_6": "house_6",
        "house_7": "house_7",
        "house_8": "house_8",
        "house_9": "house_9",
        "house_10": "house_10",
        "house_11": "house_11",
        "house_12": "house_12",
    }


def _extract_kerykeion_observable_objects(subj: AstrologicalSubject, requested_objects: Optional[List[str]] = None) -> Dict[str, float]:
    """Extract all observable objects from a kerykeion AstrologicalSubject.
    
    Includes planets, angles, houses, lunar nodes, and calculated points.
    Returns a dict mapping object_id -> ecliptic_longitude (degrees).
    """
    positions: Dict[str, float] = {}
    mapping = _get_kerykeion_object_mapping()
    lon_keys = ("ecliptic_longitude", "longitude", "lon", "degree", "deg")
    
    # Extract from KerykeionPointModel attributes
    for attr_name in dir(subj):
        if attr_name.startswith('_'):
            continue
        try:
            attr = getattr(subj, attr_name)
            if isinstance(attr, KerykeionPointModel):
                # Try to get the object name/id
                obj_name = (getattr(attr, "name", None) or attr_name or "").strip().lower()
                # Normalize name using mapping
                obj_id = mapping.get(obj_name, obj_name)
                
                # Check if this object is requested
                if requested_objects and obj_id not in requested_objects and obj_name not in requested_objects:
                    continue
                
                # Extract longitude
                lon_val = None
                for k in lon_keys:
                    if hasattr(attr, k):
                        lon_val = getattr(attr, k)
                        break
                
                if lon_val is not None:
                    try:
                        positions[obj_id] = float(lon_val) % 360.0
                    except (ValueError, TypeError):
                        continue
        except Exception:
            continue
    
    # Extract houses from houses_list if available
    if hasattr(subj, 'houses_list') and isinstance(subj.houses_list, list):
        for i, house_info in enumerate(subj.houses_list, 1):
            house_id = f"house_{i}"
            if requested_objects and house_id not in requested_objects:
                continue
            try:
                if isinstance(house_info, dict):
                    # Try different possible keys
                    degree = (house_info.get('longitude') or 
                             house_info.get('lon') or 
                             house_info.get('degree') or
                             house_info.get('cusp'))
                    if degree is not None:
                        positions[house_id] = float(degree) % 360.0
                elif hasattr(house_info, 'longitude'):
                    positions[house_id] = float(house_info.longitude) % 360.0
            except (ValueError, TypeError, AttributeError):
                continue
    
    # Also extract from planets_list for compatibility
    if hasattr(subj, 'planets_list') and hasattr(subj, 'planets_degrees_ut'):
        try:
            planets_list = subj.planets_list
            planets_degrees = subj.planets_degrees_ut
            if isinstance(planets_list, list) and isinstance(planets_degrees, list):
                for i, planet_info in enumerate(planets_list):
                    if isinstance(planet_info, dict):
                        planet_name = planet_info.get('name', '').strip().lower()
                    else:
                        planet_name = str(planet_info).strip().lower() if planet_info else ''
                    
                    if planet_name:
                        obj_id = mapping.get(planet_name, planet_name)
                        if requested_objects and obj_id not in requested_objects and planet_name not in requested_objects:
                            continue
                        if i < len(planets_degrees):
                            try:
                                degree = float(planets_degrees[i]) % 360.0
                                positions[obj_id] = degree
                            except (ValueError, TypeError, IndexError):
                                continue
        except Exception:
            pass
    
    return positions


# ─────────────────────
# 🪐 POSITION CALCULATIONS (Skyfield-based for JPL)
# ─────────────────────

def _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset: float) -> Optional[float]:
    """Compute ecliptic longitude for a planet from RA/Dec.
    
    Args:
        body: Skyfield body object
        eph: Skyfield ephemeris
        observer: Skyfield Topos observer
        t: Skyfield time object
        vernal_equinox_offset: Offset to adjust for vernal equinox
        
    Returns:
        Ecliptic longitude in degrees [0, 360), or None on error
    """
    try:
        astrometric = (eph["earth"] + observer).at(t).observe(body).apparent()
        ra, dec, _ = astrometric.radec()
        
        # Compute ecliptic longitude from RA/Dec using J2000.0 obliquity
        ra_deg = ra.hours * 15.0  # Convert hours to degrees
        dec_deg = dec.degrees
        ra_rad = math.radians(ra_deg)
        dec_rad = math.radians(dec_deg)
        obliquity_j2000 = math.radians(23.4392911)  # J2000.0 obliquity
        
        # Formula: tan(ecl_lon) = (sin(RA) * cos(obl) + tan(Dec) * sin(obl)) / cos(RA)
        sin_ra = math.sin(ra_rad)
        cos_ra = math.cos(ra_rad)
        tan_dec = math.tan(dec_rad)
        sin_obl = math.sin(obliquity_j2000)
        cos_obl = math.cos(obliquity_j2000)
        
        ecl_lon_rad = math.atan2(sin_ra * cos_obl + tan_dec * sin_obl, cos_ra)
        lon_deg = math.degrees(ecl_lon_rad) % 360.0
        if lon_deg < 0:
            lon_deg += 360.0
        
        # Adjust for vernal equinox: subtract the offset so vernal equinox = 0°
        lon_deg_tropical = (lon_deg - vernal_equinox_offset) % 360.0
        if lon_deg_tropical < 0:
            lon_deg_tropical += 360.0
        
        return lon_deg_tropical
    except (KeyError, ValueError, AttributeError) as e:
        print(f"Warning: Could not compute planet position: {e}", file=sys.stderr)
        return None


def _compute_single_planet_position(planet: str, eph, observer, t, is_de421: bool, 
                                     vernal_equinox_offset: float) -> Optional[float]:
    """Compute position for a single planet.
    
    Args:
        planet: Planet name (e.g., "jupiter")
        eph: Skyfield ephemeris
        observer: Skyfield Topos observer
        t: Skyfield time object
        is_de421: Whether using de421 ephemeris (requires barycenters for outer planets)
        vernal_equinox_offset: Offset to adjust for vernal equinox
        
    Returns:
        Ecliptic longitude in degrees [0, 360), or None on error
    """
    outer_planets = ["jupiter", "saturn", "uranus", "neptune", "pluto"]
    
    # For de421, always try barycenter first for outer planets to avoid Skyfield errors
    if is_de421 and planet in outer_planets:
        body_name = f"{planet} barycenter"
        try:
            body = eph[body_name]
            return _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
        except (KeyError, ValueError, AttributeError) as e:
            print(f"Warning: Could not compute {planet} barycenter position: {e}", file=sys.stderr)
            return None
    
    # For non-de421 or inner planets, try direct name first
    try:
        body = eph[planet]
        return _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
    except KeyError:
        # If direct access fails, try barycenter for outer planets (for other ephemeris files)
        if planet in outer_planets:
            try:
                body_name = f"{planet} barycenter"
                body = eph[body_name]
                return _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
            except (KeyError, ValueError, AttributeError) as e:
                print(f"Warning: Could not compute {planet} position: {e}", file=sys.stderr)
                return None
        return None


def compute_jpl_positions(name: str, dt_str: str, loc_str: str, ephemeris_path: Optional[str] = None,
                          requested_objects: Optional[List[str]] = None) -> Dict[str, float]:
    """Compute planetary ecliptic longitudes (degrees) using Skyfield JPL ephemerides.

    Parameters:
    - name: subject name (human-readable; not used in computation)
    - dt_str: datetime string (parsed by utils.Actual)
    - loc_str: location string (parsed by utils.Actual)
    - ephemeris_path: optional path to a local BSP file; falls back to default

    Returns a mapping: planet -> ecliptic longitude in degrees [0, 360).
    """
    if JPL:
        ts = load.timescale()
        time = Actual(dt_str, t="date")
        place = Actual(loc_str, t="loc")

        # Ensure timezone-aware datetime using centralized utils
        dt_aware = ensure_aware(time.value, getattr(place, 'tz', None))
        t = ts.from_datetime(dt_aware)
        
        eph_file = ephemeris_path or default_ephemeris_path()
        # Use load_file for explicit local path support
        eph = load_file(eph_file)
        observer = Topos(latitude_degrees=place.value.latitude, longitude_degrees=place.value.longitude)
        
        # Debug output - print to stderr so it shows in Streamlit
        # print(f"DEBUG JPL: dt_str={dt_str}", file=sys.stderr)
        # print(f"DEBUG JPL: time.value={time.value}, dt_aware={dt_aware}", file=sys.stderr)
        # try:
        #     print(f"DEBUG JPL: t={t.utc_strftime('%Y-%m-%d %H:%M:%S UTC')}", file=sys.stderr)
        # except:
        #     print(f"DEBUG JPL: t={t}", file=sys.stderr)
        # print(f"DEBUG JPL: location={loc_str}, lat={place.value.latitude}, lon={place.value.longitude}", file=sys.stderr)

        # Check if we're using de421 (which requires barycenters for outer planets: Jupiter, Saturn, Uranus, Neptune, Pluto)
        is_de421 = eph_file and "de421" in Path(eph_file).name.lower()
        
        # Determine which planets to compute
        jpl_supported = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
        if requested_objects:
            # Filter to only requested objects that JPL can compute
            planets = [p for p in jpl_supported if p in requested_objects]
        else:
            planets = jpl_supported
        
        positions = {}
        
        # For tropical astrology, we need to adjust for the vernal equinox of date
        # The vernal equinox is where 0° Aries is defined (Sun crosses celestial equator going north)
        # JPL/Skyfield gives positions in J2000.0 coordinates, but tropical uses equinox of date
        # Compute the vernal equinox offset using utils function
        year = dt_aware.year
        vernal_equinox_offset = compute_vernal_equinox_offset(year, eph, observer, ts)

        for planet in planets:
            lon_deg_tropical = _compute_single_planet_position(planet, eph, observer, t, is_de421, vernal_equinox_offset)
            if lon_deg_tropical is not None:
                positions[planet] = lon_deg_tropical

        return positions
    else:
        # Return empty dict instead of string to maintain consistent return type
        return {}


# ─────────────────────
# 🪐 POSITION CALCULATIONS (Kerykeion-based)
# ─────────────────────
# TO-DO: decide between class and a method

class Subject:
    """Lightweight wrapper around Kerykeion's AstrologicalSubject builder.

    Usage:
    - Call at_place() then at_time() to prepare `self.computed`.
    - Use data() to extract names, degrees, and labels for plotting.
    """
    def __init__(self, s_name: str, s_type: str = "Tropic") -> None:
        self.computed = None
        self.name = s_name
        self.place = None
        self.time = None
        self.type = s_type

    def at_place(self, location: object) -> None:
        """Set place from a free-text location or coordinates string."""
        self.place = Actual(location, t="loc")

    def at_time(self, time: str) -> None:
        """Set event time from a free-text datetime string and build computed subject."""
        self.time = Actual(time, t="date")
        self.computed = AstrologicalSubject(
            self.name,
            self.time.value.year,
            self.time.value.month,
            self.time.value.day,
            self.time.value.hour,
            self.time.value.minute,
            lng=self.place.value.longitude if self.place.value else "",
            lat=self.place.value.latitude if self.place.value else "",
            tz_str=self.place.tz if self.place.value else "",
            city=self.place.value.address if self.place.value else "",
            zodiac_type=self.type,
            nation="GB",
        )

    def data(self):
        """Return (object_names, degrees, labels) extracted from computed planets list."""
        object_list = [x["name"] for x in self.computed.planets_list]
        label_list = [x["emoji"] for x in self.computed.planets_list]
        return object_list, self.computed.planets_degrees_ut, label_list

    def report(self):
        """Build a Kerykeion textual Report for the computed subject."""
        return Report(self.computed)


def compute_subject(name: str, dt_str: str, loc_str: str, zodiac: str = "Tropic") -> AstrologicalSubject:
    """Construct a Kerykeion AstrologicalSubject from strings.
    
    Args:
        name: Subject name (human-readable identifier)
        dt_str: Datetime string (parsed by utils.Actual)
        loc_str: Location string (parsed by utils.Actual)
        zodiac: Zodiac type, defaults to "Tropic"
        
    Returns:
        AstrologicalSubject instance with computed positions
    """
    time = Actual(dt_str, t="date")
    place = Actual(loc_str, t="loc")
    return AstrologicalSubject(
        name,
        time.value.year,
        time.value.month,
        time.value.day,
        time.value.hour,
        time.value.minute,
        lng=place.value.longitude if place.value else 0.0,
        lat=place.value.latitude if place.value else 0.0,
        tz_str=place.tz if place.value else "UTC",
        city=place.value.address if place.value else "",
        zodiac_type=zodiac,
        nation="GB"
    )

def extract_kerykeion_points(obj: Any) -> DataFrame:
    """Extract KerykeionPointModel attributes from an object into a DataFrame.
    
    Args:
        obj: Object containing KerykeionPointModel attributes
        
    Returns:
        DataFrame with one row per KerykeionPointModel attribute found
    """
    data = []
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        if isinstance(attr, KerykeionPointModel):
            data.append(attr.__dict__)
    return DataFrame(data)


# ─────────────────────
# 🔁 COMPOSITE / RELATION CHART
# ─────────────────────

def create_relation_svg(subject1: AstrologicalSubject, subject2: AstrologicalSubject, chart_type: str = "Synastry") -> KerykeionChartSVG:
    """Create a Kerykeion SVG chart for relation/composite types.
    
    Args:
        subject1: First astrological subject
        subject2: Second astrological subject
        chart_type: Type of relation chart (e.g., "Synastry", "Composite"), defaults to "Synastry"
        
    Returns:
        KerykeionChartSVG instance with generated SVG chart
    """
    chart = KerykeionChartSVG(subject1, chart_type=chart_type, second_obj=subject2)
    chart.makeSVG()
    return chart


# ─────────────────────
# 🔺 ASPECT DETECTION
# ─────────────────────

def compute_aspects(bodies: List[CelestialBody], aspect_defs: List[AspectDefinition]) -> List[Aspect]:
    """Compute aspects between celestial bodies using provided definitions.
    
    Note: This is a placeholder implementation. Full aspect detection logic
    should be implemented here.
    
    Args:
        bodies: List of celestial bodies to compute aspects for
        aspect_defs: List of aspect definitions to use for detection
        
    Returns:
        List of Aspect objects representing detected aspects
    """
    return []  # To be implemented


# ─────────────────────
# 🧬 MODEL MERGING
# ─────────────────────

def merge_model_with_overrides(model: AstroModel, overrides: Optional[ModelOverrides]) -> AstroModel:
    """Return a new AstroModel with selective overrides applied.
    
    Applies:
    - OverrideEntry for aspects: glyph/angle/default_orb overrides
    - OverrideEntry for points: glyph overrides and computed flag (if applicable)
    - override_orbs: map of aspect-id -> orb to override AspectDefinition.default_orb
    
    This function does not mutate the original model; it returns a modified copy.
    
    Args:
        model: Base AstroModel to apply overrides to
        overrides: Optional ModelOverrides containing override definitions
        
    Returns:
        New AstroModel instance with overrides applied
    """
    if not overrides:
        return model

    m = deepcopy(model)

    # Index helpers
    aspect_by_id: Dict[str, AspectDefinition] = {a.id: a for a in m.aspect_definitions}
    body_by_id: Dict[str, BodyDefinition] = {b.id: b for b in m.body_definitions}

    # Apply aspect overrides
    for oe in getattr(overrides, 'aspects', []) or []:
        a = aspect_by_id.get(oe.id)
        if not a:
            continue
        # Rebuild AspectDefinition with overrides
        new_angle = oe.angle if oe.angle is not None else a.angle
        new_orb = oe.default_orb if oe.default_orb is not None else a.default_orb
        new_glyph = oe.glyph if oe.glyph is not None else a.glyph
        new_i18n = oe.i18n if oe.i18n is not None else a.i18n
        aspect_by_id[oe.id] = AspectDefinition(id=a.id, glyph=new_glyph, angle=new_angle, default_orb=new_orb, i18n=new_i18n)
    m.aspect_definitions = list(aspect_by_id.values())

    # Apply point overrides (glyph only; computed flag is metadata not present on BodyDefinition)
    for oe in getattr(overrides, 'points', []) or []:
        b = body_by_id.get(oe.id)
        if not b:
            continue
        new_glyph = oe.glyph if oe.glyph is not None else b.glyph
        new_formula = b.formula  # angle/element/avg_speed/max_orb are part of definition; only glyph/i18n commonly overridden
        new_element = b.element
        new_avg = b.avg_speed
        new_max_orb = b.max_orb
        new_i18n = oe.i18n if oe.i18n is not None else b.i18n
        body_by_id[oe.id] = BodyDefinition(
            id=b.id,
            glyph=new_glyph,
            formula=new_formula,
            element=new_element,
            avg_speed=new_avg,
            max_orb=new_max_orb,
            i18n=new_i18n,
        )
    m.body_definitions = list(body_by_id.values())

    # Apply override_orbs map
    orb_map = getattr(overrides, 'override_orbs', {}) or {}
    if orb_map:
        new_aspects: List[AspectDefinition] = []
        for a in m.aspect_definitions:
            if a.id in orb_map:
                new_aspects.append(AspectDefinition(id=a.id, glyph=a.glyph, angle=a.angle, default_orb=float(orb_map[a.id]), i18n=a.i18n))
            else:
                new_aspects.append(a)
        m.aspect_definitions = new_aspects

    return m


def _build_aspect_orbs(model: AstroModel) -> Dict[str, float]:
    """Create a map aspect-id -> default orb from the model's aspect definitions.
    
    Args:
        model: AstroModel containing aspect definitions
        
    Returns:
        Dictionary mapping aspect ID to default orb value
    """
    return {a.id: float(a.default_orb) for a in getattr(model, 'aspect_definitions', []) or []}


def get_active_model(ws: Optional['Workspace']) -> Optional[AstroModel]:
    """Resolve the currently active AstroModel instance from a Workspace, if available.
    
    Prefers active_model_name over active_model (deprecated). Falls back to first model
    if no active model is specified.
    
    Args:
        ws: Workspace instance to get active model from
        
    Returns:
        Active AstroModel instance, or None if no models available
        
    Note:
        The 'active_model' attribute is deprecated. Use 'active_model_name' instead.
    """
    if ws is None:
        return None
    models = getattr(ws, 'models', {}) or {}
    if not models:
        return None
    # Prefer active_model_name (new), fallback to active_model (deprecated)
    name = getattr(ws, 'active_model_name', None) or getattr(ws, 'active_model', None)
    if name and name in models:
        return models[name]
    # Fallback: return any model
    try:
        return next(iter(models.values()))
    except StopIteration:
        return None


def resolve_effective_defaults(ws: 'Workspace', model: Optional[AstroModel]) -> Dict[str, object]:
    """Resolve effective defaults merging workspace overrides on top of AstroModel settings.
    
    Args:
        ws: Workspace containing default overrides
        model: Optional AstroModel with base settings
        
    Returns:
        Dictionary with keys: house_system, bodies, aspects, standard_orb, engine,
        zodiac_type, ayanamsa, aspect_orbs, observable_objects
    """
    out: Dict[str, object] = {}
    if model is None:
        return out

    ms = getattr(model, 'settings', None)
    d = getattr(ws, 'default', None) if ws is not None else None

    # House system
    out['house_system'] = getattr(d, 'default_house_system', None) or (getattr(ms, 'default_house_system', None) if ms else None)

    # Bodies (from model settings)
    ws_bodies = getattr(d, 'default_bodies', None) if d else None
    out['bodies'] = ws_bodies or (getattr(ms, 'default_bodies', None) if ms else None) or []

    # Observable objects (extends bodies with angles, houses, etc.)
    ws_observable = getattr(d, 'observable_objects', None) if d else None
    # Merge with bodies if both exist
    if ws_observable:
        combined = list(set((out.get('bodies') or []) + ws_observable))
        out['observable_objects'] = combined
    else:
        out['observable_objects'] = out.get('bodies') or []

    # Aspects: prefer top-level ws.aspects, then defaults override, then model settings
    ws_aspects_top = getattr(ws, 'aspects', []) if ws is not None else []
    if ws_aspects_top:
        out['aspects'] = ws_aspects_top
    else:
        ws_aspects = getattr(d, 'default_aspects', None) if d else None
        out['aspects'] = ws_aspects or (getattr(ms, 'default_aspects', None) if ms else None) or []

    # Standard orb (from model settings)
    out['standard_orb'] = getattr(ms, 'standard_orb', None) if ms else None

    # Engine prefs (workspace default can override model engine)
    out['engine'] = (getattr(d, 'ephemeris_engine', None) if d else None) or getattr(model, 'engine', None)
    out['zodiac_type'] = getattr(model, 'zodiac_type', None)
    out['ayanamsa'] = getattr(model, 'ayanamsa', None)

    # Aspect orbs map from model
    out['aspect_orbs'] = _build_aspect_orbs(model)
    return out


def compute_positions(engine: Optional[EngineType], name: str, dt_str: str, loc_str: str,
                      ephemeris_path: Optional[str] = None, requested_objects: Optional[List[str]] = None) -> Dict[str, float]:
    """Dispatch position computation based on engine.
    - For EngineType.JPL, returns a dict of ecliptic longitudes using Skyfield and a local ephemeris file.
    - For other or None, returns Kerykeion observable object longitudes (degrees) as a dict.
    
    Args:
        engine: Computation engine to use
        name: Subject name
        dt_str: Datetime string
        loc_str: Location string
        ephemeris_path: Optional path to ephemeris file
        requested_objects: Optional list of object IDs to compute (filters results)
    
    Returns:
        Dict mapping object_id -> ecliptic_longitude (degrees). Empty dict on error.
        
    Raises:
        ValueError: If datetime or location cannot be parsed
        FileNotFoundError: If ephemeris file is specified but not found
    """
    if engine == EngineType.JPL:
        result = compute_jpl_positions(name, dt_str, loc_str, ephemeris_path=ephemeris_path, requested_objects=requested_objects)
        # Ensure we return a dict, not a string
        if isinstance(result, dict):
            # For JPL, we only get planets; angles/houses need kerykeion fallback
            jpl_positions = result
            
            # If requested objects include non-planets, fall through to kerykeion
            non_planet_objects = []
            if requested_objects:
                jpl_planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
                non_planet_objects = [obj for obj in requested_objects if obj not in jpl_planets]
            
            if non_planet_objects:
                # Get additional objects from kerykeion
                try:
                    subj = compute_subject(name, dt_str, loc_str)
                    kerykeion_positions = _extract_kerykeion_observable_objects(subj, requested_objects=non_planet_objects)
                    jpl_positions.update(kerykeion_positions)
                except (ValueError, AttributeError, KeyError) as e:
                    print(f"Warning: Could not compute non-planet objects with Kerykeion: {e}", file=sys.stderr)
            
            return jpl_positions
        else:
            # If JPL failed, fall through to Kerykeion
            pass
    
    # Kerykeion: extract all observable objects
    try:
        subj = compute_subject(name, dt_str, loc_str)
        positions = _extract_kerykeion_observable_objects(subj, requested_objects=requested_objects)
        return positions
    except (ValueError, AttributeError, KeyError) as e:
        # Log specific errors for debugging
        print(f"Error computing positions with Kerykeion: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        # Catch-all for unexpected errors
        print(f"Unexpected error computing positions: {e}", file=sys.stderr)
        return {}


def compute_positions_for_chart(chart: ChartInstance, ws: Optional['Workspace'] = None) -> Dict[str, float]:
    """Compute positions using a ChartInstance's engine and ephemeris settings.
    Uses chart.subject.event_time and chart.subject.location.name for location lookup.
    Handles both ChartInstance objects and dict-like structures safely.
    
    Args:
        chart: ChartInstance to compute positions for
        ws: Optional workspace for resolving observable objects defaults
        
    Returns:
        Dict mapping object_id -> ecliptic_longitude (degrees)
        
    Raises:
        ValueError: If chart is missing required subject or location data
    """
    # Get engine and ephemeris from config
    cfg = _safe_get_attr(chart, 'config')
    engine = _safe_get_attr(cfg, 'engine') if cfg else None
    eph = _safe_get_attr(cfg, 'override_ephemeris') if cfg else None
    
    # If engine is None but override_ephemeris is set, infer that we should use JPL
    if engine is None and eph:
        engine = EngineType.JPL
    
    # Get observable objects: prefer chart config, then workspace defaults, then model defaults
    requested_objects = _safe_get_attr(cfg, 'observable_objects') if cfg else None
    if not requested_objects and ws:
        try:
            model = get_active_model(ws)
            if model:
                eff = resolve_effective_defaults(ws, model)
                requested_objects = eff.get('observable_objects')
                # Debug: log what we resolved
                if requested_objects:
                    print(f"DEBUG: Resolved observable_objects from workspace/model: {len(requested_objects)} objects", file=sys.stderr)
                else:
                    print(f"DEBUG: No observable_objects found in workspace/model defaults", file=sys.stderr)
        except (AttributeError, KeyError, TypeError) as e:
            # Log but don't fail - use None as fallback (will compute all objects)
            print(f"Warning: Could not resolve observable objects from workspace: {e}", file=sys.stderr)
    
    # Debug: log final requested_objects
    if requested_objects:
        print(f"DEBUG: Using observable_objects: {requested_objects[:10]}..." if len(requested_objects) > 10 else f"DEBUG: Using observable_objects: {requested_objects}", file=sys.stderr)
    else:
        print(f"DEBUG: No observable_objects filter - will compute all available objects", file=sys.stderr)
    
    # Get subject data safely
    subj = _safe_get_attr(chart, 'subject')
    if subj is None:
        raise ValueError("Chart has no subject")
    
    # Get name - handle both object and dict
    name = _safe_get_attr(subj, 'name')
    if not name:
        # Try alternative access patterns
        if isinstance(subj, dict):
            name = subj.get('name') or subj.get('id') or 'chart'
        else:
            name = 'chart'
    
    # Get event_time
    event_time = _safe_get_attr(subj, 'event_time')
    if event_time is None:
        raise ValueError(f"Chart subject has no event_time (subject type: {type(subj)})")
    dt_str = str(event_time)
    
    # Get location name - handle both object and dict
    loc = _safe_get_attr(subj, 'location')
    if loc is None:
        raise ValueError("Chart subject has no location")
    
    loc_str = _safe_get_attr(loc, 'name')
    if not loc_str:
        # Try alternative access patterns
        if isinstance(loc, dict):
            loc_str = loc.get('name') or ''
        # If still no name, try to construct from lat/lon if available
        if not loc_str:
            lat = _safe_get_attr(loc, 'latitude')
            lon = _safe_get_attr(loc, 'longitude')
            if lat is not None and lon is not None:
                loc_str = f"{lat},{lon}"
    
    if not loc_str:
        raise ValueError(f"Could not determine location name (location type: {type(loc)})")
    
    # Call compute_positions with the extracted parameters
    result = compute_positions(engine, name, dt_str, loc_str, ephemeris_path=eph, requested_objects=requested_objects)
    
    # Ensure we return a dict
    if not isinstance(result, dict):
        return {}
    
    # Return empty dict if no positions found
    if not result:
        return {}
    
    return result


# ─────────────────────
# 📦 HIGHER-LEVEL APP SERVICES (UI-agnostic)
# ─────────────────────

def build_chart_instance(name: str, dt_str: str, loc_text: str,
                         mode: ChartMode, ws: Optional[Workspace] = None, 
                         ephemeris_path: Optional[str] = None) -> ChartInstance:
    """Build a ChartInstance using workspace defaults when provided.
    - Resolves engine and house system from ws if available.
    - Uses utils.prepare_horoscope to produce a fully-typed ChartInstance.
    """
    # Resolve engine and model-based defaults
    engine = None
    house = None
    zodiac_type = None
    included_points: List[str] = []
    observable_objects: Optional[List[str]] = None
    aspect_orbs: Dict[str, float] = {}
    ayanamsa = None

    if ws is not None:
        try:
            # Workspace default engine override
            d = getattr(ws, 'default', None)
            engine = getattr(d, 'ephemeris_engine', None)
        except Exception:
            pass
        # Resolve effective defaults from active model
        try:
            model = get_active_model(ws)
            if model is not None:
                eff_model = merge_model_with_overrides(model, getattr(ws, 'model_overrides', None))
                eff = resolve_effective_defaults(ws, eff_model)
                house = eff.get('house_system') or house
                zodiac_type = eff.get('zodiac_type') or zodiac_type
                included_points = list(eff.get('bodies') or [])
                observable_objects = list(eff.get('observable_objects') or [])
                aspect_orbs = dict(eff.get('aspect_orbs') or {})
                ayanamsa = eff.get('ayanamsa') or ayanamsa
                # If workspace default specifies engine, that already took priority above; otherwise use model engine
                engine = engine or eff.get('engine')
        except (AttributeError, KeyError, TypeError) as e:
            # Best-effort: if anything fails, continue with minimal defaults
            print(f"Warning: Could not resolve all defaults from workspace/model: {e}", file=sys.stderr)
 
    # Normalize inputs via utils.Actual and to_model_location
    try:
        t = Actual(dt_str, t="date").value
        loc_model = Actual(loc_text, t="loc").to_model_location()
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Failed to parse date or location: {e}") from e
    
    # Delegate to prepare_horoscope (ensures ChartSubject/ChartConfig types)
    chart = prepare_horoscope(name=name, dt=t, loc=loc_model, engine=engine,
                              ephemeris_path=ephemeris_path, house=house)
    try:
        chart.config.mode = mode
    except AttributeError:
        # ChartConfig might not support mode assignment directly
        pass
    
    # Apply additional resolved defaults onto ChartConfig
    try:
        if house is not None:
            chart.config.house_system = house
        if zodiac_type is not None:
            chart.config.zodiac_type = zodiac_type
        if included_points:
            chart.config.included_points = included_points
        if observable_objects:
            chart.config.observable_objects = observable_objects
        if aspect_orbs:
            chart.config.aspect_orbs = aspect_orbs
        if engine is not None:
            chart.config.engine = engine
        if ayanamsa is not None:
            chart.config.ayanamsa = ayanamsa
    except AttributeError as e:
        print(f"Warning: Could not set all chart config defaults: {e}", file=sys.stderr)
    
    return chart


def find_chart_by_name_or_id(ws: Optional[Workspace], name_or_id: str) -> Optional[ChartInstance]:
    """Find a chart in the workspace by subject name or chart ID.
    
    Args:
        ws: Workspace to search in
        name_or_id: Subject name or chart ID to search for
        
    Returns:
        ChartInstance if found, None otherwise
    """
    if not ws or not getattr(ws, 'charts', None):
        return None
    key = (name_or_id or '').strip()
    for c in ws.charts:
        subj = getattr(c, 'subject', None)
        cid = getattr(c, 'id', None)
        nm = getattr(subj, 'name', None) if subj else None
        if key and (key == nm or key == cid):
            return c
    return None


def search_charts(ws: Optional[Workspace], query: str) -> List[ChartInstance]:
    """Search charts in workspace using case-insensitive text matching.
    
    Searches across chart name, event_time, location name, and tags.
    
    Args:
        ws: Workspace to search in
        query: Search query string
        
    Returns:
        List of ChartInstance objects matching the query
    """
    if not ws or not getattr(ws, 'charts', None):
        return []
    q = (query or '').strip().lower()
    if not q:
        return list(ws.charts)
    out: List[ChartInstance] = []
    for ch in ws.charts:
        try:
            subj = getattr(ch, 'subject', None)
            loc = getattr(subj, 'location', None) if subj else None
            tags = getattr(ch, 'tags', []) or []
            hay = " ".join([
                str(getattr(subj, 'name', '') or ''),
                str(getattr(subj, 'event_time', '') or ''),
                str(getattr(loc, 'name', '') or ''),
                ",".join([str(t) for t in tags])
            ]).lower()
            if q in hay:
                out.append(ch)
        except Exception:
            continue
    return out


def list_open_view_rows(ws: Optional[Workspace]) -> List[Dict[str, str]]:
    """Produce table rows for Open view display.
    
    Args:
        ws: Workspace containing charts
        
    Returns:
        List of dictionaries with keys: name, event_time, location, tags, search_text
    """
    rows: List[Dict[str, str]] = []
    if not ws or not getattr(ws, 'charts', None):
        return rows
    for ch in ws.charts:
        try:
            subj = getattr(ch, 'subject', None)
            loc = getattr(subj, 'location', None) if subj else None
            name = getattr(subj, 'name', '') if subj else ''
            event_time = str(getattr(subj, 'event_time', '') or '')
            location_name = getattr(loc, 'name', '') if loc else ''
            tags = ", ".join(getattr(ch, 'tags', []) or [])
            # Get chart type from config
            cfg = getattr(ch, 'config', None)
            chart_type = ''
            if cfg:
                mode = getattr(cfg, 'mode', None)
                if mode:
                    chart_type = mode.value if hasattr(mode, 'value') else str(mode)
            search_text = f"{name} {chart_type} {event_time} {location_name} {tags}".lower()
            rows.append({
                'name': name,
                'chart_type': chart_type,
                'event_time': event_time,
                'location': location_name,
                'tags': tags,
                'search_text': search_text,
            })
        except Exception:
            continue
    return rows


def build_radix_figure_for_chart(chart: ChartInstance, engine_override: Optional[EngineType] = None, 
                                 ephemeris_path_override: Optional[str] = None, ws: Optional['Workspace'] = None) -> Any:
    """Extract positions from a ChartInstance's computed_chart and return a Plotly Figure ready to render.
    
    Always recomputes positions to ensure accuracy, as stored computed_chart may contain
    initial/default values that are incorrect.
    
    Args:
        chart: ChartInstance to compute positions for
        engine_override: Optional engine to use instead of chart's stored engine
        ephemeris_path_override: Optional ephemeris path to use instead of chart's stored path
        ws: Optional workspace for resolving observable objects defaults
        
    Returns:
        Plotly Figure object ready for rendering
    """
    # Always recompute positions to ensure we have accurate, up-to-date values
    # The computed_chart may contain stale or initial values
    # Use override engine if provided, otherwise use chart's stored engine
    if engine_override is not None or ephemeris_path_override is not None:
        # Get observable objects: prefer chart config, then workspace defaults, then model defaults
        cfg = _safe_get_attr(chart, 'config')
        requested_objects = _safe_get_attr(cfg, 'observable_objects') if cfg else None
        if not requested_objects and ws:
            try:
                model = get_active_model(ws)
                if model:
                    eff = resolve_effective_defaults(ws, model)
                    requested_objects = eff.get('observable_objects')
            except (AttributeError, KeyError, TypeError) as e:
                # Log but don't fail - use None as fallback (will compute all objects)
                print(f"Warning: Could not resolve observable objects from workspace: {e}", file=sys.stderr)
        
        subj = _safe_get_attr(chart, 'subject')
        name = _safe_get_attr(subj, 'name') or 'chart'
        event_time = _safe_get_attr(subj, 'event_time')
        dt_str = str(event_time) if event_time else ''
        loc = _safe_get_attr(subj, 'location')
        loc_str = _safe_get_attr(loc, 'name') or ''
        if not loc_str:
            lat = _safe_get_attr(loc, 'latitude')
            lon = _safe_get_attr(loc, 'longitude')
            if lat is not None and lon is not None:
                loc_str = f"{lat},{lon}"
        
        positions = compute_positions(engine_override, name, dt_str, loc_str, 
                                     ephemeris_path=ephemeris_path_override, 
                                     requested_objects=requested_objects)
    else:
        positions = compute_positions_for_chart(chart, ws=ws)
    
    # Verify we got valid positions (not all zeros or suspiciously clustered)
    if positions:
        values = list(positions.values())
        # Check if all values are suspiciously close to 0 (within -5 to 5 degrees)
        all_near_zero = all(abs(v) < 5.0 for v in values)
        if all_near_zero:
            # This suggests the computation might be using wrong parameters
            # But we'll still render it - the user can see the issue
            import warnings
            warnings.warn(
                f"All computed positions are near 0° (within -5° to 5°). "
                f"This may indicate incorrect time/location parameters. "
                f"Positions: {positions}"
            )
    
    return build_radix_figure(positions)


def compute_positions_for_inputs(engine: Optional[EngineType], name: str,
                                 dt_str: str, loc_text: str,
                                 ephemeris_path: Optional[str] = None,
                                 requested_objects: Optional[List[str]] = None) -> Dict[str, float]:
    """Thin wrapper over compute_positions to normalize/forward parameters from UI layers."""
    return compute_positions(engine, name, dt_str, loc_text, ephemeris_path=ephemeris_path, requested_objects=requested_objects)