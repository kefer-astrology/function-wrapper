try:
    from module.models import (
        Location, DateRange, CelestialBody, Aspect, AstroModel,
        ChartConfig, ModelOverrides, BodyDefinition, AspectDefinition, Sign, EngineType, ChartInstance
    )
except ImportError:
    from models import (
        Location, DateRange, CelestialBody, Aspect, AstroModel,
        ChartConfig, ModelOverrides, BodyDefinition, AspectDefinition, Sign, EngineType, ChartInstance
    )
from kerykeion import AstrologicalSubject, KerykeionChartSVG, Report, KerykeionPointModel
from pandas import DataFrame
from typing import Dict, List, Optional
from utils import Actual, default_ephemeris_path, ensure_aware, prepare_horoscope
from z_visual import build_radix_figure
try:
    from skyfield.api import load, load_file, Topos
    JPL = True
except ImportError:
    JPL = False
    print("NASA JPL Ephemeris deactivated")

# ─────────────────────
# 🪐 POSITION CALCULATIONS (Skyfield-based for JPL)
# ─────────────────────

def compute_jpl_positions(name: str, dt_str: str, loc_str: str, ephemeris_path: Optional[str] = None) -> Dict[str, float]:
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
        t = ts.from_datetime(ensure_aware(time.value, getattr(place, 'tz', None)))
        eph_file = ephemeris_path or default_ephemeris_path()
        # Use load_file for explicit local path support
        eph = load_file(eph_file)
        observer = Topos(latitude_degrees=place.value.latitude, longitude_degrees=place.value.longitude)

        planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
        positions = {}

        for planet in planets:
            body = eph[planet]
            astrometric = (eph["earth"] + observer).at(t).observe(body).apparent()
            lon, lat, distance = astrometric.ecliptic_latlon()
            positions[planet] = lon.degrees

        return positions
    else:
        return "JPL Ephemeris not implemented yet"


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
    """Construct a Kerykeion AstrologicalSubject from strings (date/place/zodiac)."""
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

def extract_kerykeion_points(obj) -> DataFrame:
    """Extract KerykeionPointModel attributes from an object into a DataFrame."""
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
    """Create a Kerykeion SVG chart for relation/composite types and return it."""
    chart = KerykeionChartSVG(subject1, chart_type=chart_type, second_obj=subject2)
    chart.makeSVG()
    return chart


# ─────────────────────
# 🔺 ASPECT DETECTION
# ─────────────────────

def compute_aspects(bodies: List[CelestialBody], aspect_defs: List[AspectDefinition]) -> List[Aspect]:
    """Placeholder for aspect detection between bodies using provided definitions."""
    return []  # To be implemented


# ─────────────────────
# 🧬 MODEL MERGING
# ─────────────────────

def merge_model_with_overrides(model: AstroModel, overrides: Optional[ModelOverrides]) -> AstroModel:
    """Return a new AstroModel with selective overrides applied (no-op for now)."""
    if not overrides:
        return model
    return model


def compute_positions(engine: Optional[EngineType], name: str, dt_str: str, loc_str: str,
                      ephemeris_path: Optional[str] = None) -> Dict[str, float]:
    """Dispatch position computation based on engine.
    - For EngineType.JPL, returns a dict of ecliptic longitudes using Skyfield and a local ephemeris file.
    - For other or None, returns Kerykeion planet ecliptic longitudes (degrees) as a dict.
    """
    if engine == EngineType.JPL:
        return compute_jpl_positions(name, dt_str, loc_str, ephemeris_path=ephemeris_path)
    # Fallback to Kerykeion: robust extraction from KerykeionPointModel attributes
    subj = compute_subject(name, dt_str, loc_str)
    positions: Dict[str, float] = {}
    # Preferred keys for longitude on KerykeionPointModel
    lon_keys = ("ecliptic_longitude", "longitude", "lon", "degree", "deg")
    try:
        for attr_name in dir(subj):
            attr = getattr(subj, attr_name)
            if isinstance(attr, KerykeionPointModel):
                # Determine name label
                pname = (getattr(attr, "name", None) or attr_name or "").strip().lower()
                # Find a longitude-like value
                lon_val = None
                for k in lon_keys:
                    if hasattr(attr, k):
                        lon_val = getattr(attr, k)
                        break
                if lon_val is None and hasattr(attr, "__dict__"):
                    for k in lon_keys:
                        if k in attr.__dict__:
                            lon_val = attr.__dict__[k]
                            break
                if lon_val is not None:
                    try:
                        positions[pname] = float(lon_val) % 360.0
                    except Exception:
                        continue
    except Exception:
        pass
    # If we found many points, prefer canonical planetary subset when possible
    canonical = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
    subset = {k: positions[k] for k in canonical if k in positions}
    return subset or positions


def compute_positions_for_chart(chart: ChartInstance) -> Dict[str, float]:
    """Compute positions using a ChartInstance's engine and ephemeris settings.
    Uses chart.subject.event_time and chart.subject.location.name for location lookup.
    """
    engine = getattr(chart.config, 'engine', None)
    eph = getattr(chart.config, 'override_ephemeris', None)
    name = chart.subject.name
    dt_str = str(chart.subject.event_time)
    loc_str = chart.subject.location.name
    return compute_positions(engine, name, dt_str, loc_str, ephemeris_path=eph)


# ─────────────────────
# 📦 HIGHER-LEVEL APP SERVICES (UI-agnostic)
# ─────────────────────

def build_chart_instance(name: str, dt_str: str, loc_text: str,
                         mode, ws=None, ephemeris_path: Optional[str] = None) -> ChartInstance:
    """Build a ChartInstance using workspace defaults when provided.
    - Resolves engine and house system from ws if available.
    - Uses utils.prepare_horoscope to produce a fully-typed ChartInstance.
    """
    # Resolve engine and house defaults
    if ws is not None:
        try:
            d = getattr(ws, 'default', None)
            engine = getattr(d, 'ephemeris_engine', None)
        except Exception:
            engine = None
        # House system not part of new default block; leave as None for now
        house = None
    else:
        engine = None
        house = None
    # Normalize inputs via utils.Actual and to_model_location
    t = Actual(dt_str, t="date").value
    loc_model = Actual(loc_text, t="loc").to_model_location()
    # Delegate to prepare_horoscope (ensures ChartSubject/ChartConfig types)
    chart = prepare_horoscope(name=name, dt=t, loc=loc_model, engine=engine,
                              ephemeris_path=ephemeris_path, house=house)
    try:
        chart.config.mode = mode
    except Exception:
        pass
    return chart


def find_chart_by_name_or_id(ws, name_or_id: str) -> Optional[ChartInstance]:
    """Find a chart in the workspace by subject.name or chart.id."""
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


def search_charts(ws, query: str) -> List[ChartInstance]:
    """Simple case-insensitive search across name, event_time, location name, and tags."""
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


def list_open_view_rows(ws) -> List[Dict[str, str]]:
    """Produce table rows for Open view: name, event_time, location, tags, search_text."""
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
            search_text = f"{name} {event_time} {location_name} {tags}".lower()
            rows.append({
                'name': name,
                'event_time': event_time,
                'location': location_name,
                'tags': tags,
                'search_text': search_text,
            })
        except Exception:
            continue
    return rows


def build_radix_figure_for_chart(chart: ChartInstance):
    """Compute positions for a ChartInstance and return a Plotly Figure ready to render."""
    positions = compute_positions_for_chart(chart)
    return build_radix_figure(positions)


def compute_positions_for_inputs(engine: Optional[EngineType], name: str,
                                 dt_str: str, loc_text: str,
                                 ephemeris_path: Optional[str] = None) -> Dict[str, float]:
    """Thin wrapper over compute_positions to normalize/forward parameters from UI layers."""
    return compute_positions(engine, name, dt_str, loc_text, ephemeris_path=ephemeris_path)