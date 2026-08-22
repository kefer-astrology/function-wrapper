from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import math
import sys
import logging

# Modern logging setup
try:
    from module.logging_config import get_logger
except ImportError:
    from logging_config import get_logger

logger = get_logger(__name__)

# Standardized imports with fallback for direct execution
try:
    from module.models import (
        Aspect, AspectDefinition, AstroModel, Ayanamsa, BodyDefinition, CelestialBody, ChartMode, DateRange,
        EngineType, ChartConfig, ChartInstance, Location, ModelOverrides, ModelSettings, Sign,
        ObjectType, Workspace
    )
except ImportError:
    from models import (
        Aspect, AspectDefinition, AstroModel, Ayanamsa, BodyDefinition, CelestialBody, ChartMode, DateRange,
        EngineType, ChartConfig, ChartInstance, Location, ModelOverrides, ModelSettings, Sign,
        ObjectType, Workspace
    )

try:
    from module.astronomy import (
        ChartData, apply_ayanamsa_to_chart_data, backend_for_chart, compute_normalized_chart_aspects,
    )
except ImportError:
    from astronomy import (
        ChartData, apply_ayanamsa_to_chart_data, backend_for_chart, compute_normalized_chart_aspects,
    )

try:
    from module.utils import Actual, default_ephemeris_path, default_mpc_elements_path, ensure_aware, prepare_horoscope, compute_vernal_equinox_offset, _safe_get_attr, to_timezone
except ImportError:
    from utils import Actual, default_ephemeris_path, default_mpc_elements_path, ensure_aware, prepare_horoscope, compute_vernal_equinox_offset, _safe_get_attr, to_timezone

from pandas import DataFrame

try:
    from skyfield.api import load, load_file, Topos
    from skyfield.data import mpc
    from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2 as _GM_SUN_KM3_S2
    JPL = True
except ImportError:
    JPL = False
    logger.warning("NASA JPL Ephemeris deactivated")

# Module-level fallback constants (used when model is not available)
# These match ModelSettings defaults and can be overridden by model settings
DEGREES_IN_CIRCLE = 360.0  # Full circle in degrees
OBLIQUITY_J2000_DEGREES = 23.4392911  # J2000.0 obliquity of the ecliptic in degrees
COORDINATE_TOLERANCE = 0.0001  # Coordinate comparison tolerance

# Lunar nodes computed natively on the JPL/Skyfield path (do not merge from Kerykeion).
_JPL_NATIVE_LUNAR_NODES = frozenset(
    {
        "north_node",
        "south_node",
        "mean_node",
        "mean_south_node",
        "true_north_node",
        "true_south_node",
        "true_node",
    }
)

# Black Moon Lilith variants computed natively on the JPL/Skyfield path.
_JPL_NATIVE_LILITH = frozenset({"lilith", "mean_lilith", "true_lilith"})

# Minor planets computed natively via MPC orbital elements (see _load_mpc_orbits).
_MPC_MINOR_BODY_IDS: tuple[str, ...] = ("chiron", "ceres", "pallas", "juno", "vesta")

# Packed MPCORB designation prefixes for the bodies vendored in source/mpc_bodies.dat.
_MPC_PACKED_DESIGNATIONS = {
    "ceres": "00001",
    "pallas": "00002",
    "juno": "00003",
    "vesta": "00004",
    "chiron": "02060",
}

_mpc_orbit_cache: Dict[str, Any] = {}


def _load_mpc_orbits(ts, path: Optional[str] = None) -> Dict[str, Any]:
    """Load Chiron/Ceres/Pallas/Juno/Vesta orbits from the vendored MPCORB rows.

    Returns a dict of body_id -> Skyfield Kepler orbit (heliocentric), cached
    at module scope since the vendored orbital elements don't change per-call.
    """
    if _mpc_orbit_cache:
        return _mpc_orbit_cache

    elements_path = path or default_mpc_elements_path()
    with open(elements_path, "rb") as fobj:
        df = mpc.load_mpcorb_dataframe(fobj)

    for body_id, packed in _MPC_PACKED_DESIGNATIONS.items():
        rows = df[df["designation_packed"] == packed]
        if rows.empty:
            logger.warning("mpc_bodies.dat missing row for %s (packed=%s)", body_id, packed)
            continue
        row = rows.iloc[0]
        _mpc_orbit_cache[body_id] = mpc.mpcorb_orbit(row, ts, _GM_SUN_KM3_S2)

    return _mpc_orbit_cache


def _jd_ut_from_datetime_utc(dt: datetime) -> float:
    """Julian day (UT) consistent with the Rust `julian_day_from_unix` convention."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    unix = dt.timestamp()
    return 2440587.5 + unix / 86400.0


def _mean_lunar_node_lon_deg(jd_ut: float) -> float:
    """Mean ascending node longitude (degrees, [0,360)) — IAU polynomial, matches Rust `mean_node_lon`."""
    t = (jd_ut - 2451545.0) / 36525.0
    omega = (
        125.04455501
        - 1934.13626197 * t
        + 0.00207581 * t * t
        + 0.00000215 * t * t * t
    ) % DEGREES_IN_CIRCLE
    if omega < 0:
        omega += DEGREES_IN_CIRCLE
    return omega


def _icrf_vec_to_ecliptic_xyz(x: float, y: float, z: float, obl_deg: float) -> tuple[float, float, float]:
    obl = math.radians(obl_deg)
    xe = x
    ye = y * math.cos(obl) + z * math.sin(obl)
    ze = -y * math.sin(obl) + z * math.cos(obl)
    return xe, ye, ze


def _ecliptic_lon_deg_from_icrf_vec(x: float, y: float, z: float, obl_deg: float) -> float:
    xe, ye, _ = _icrf_vec_to_ecliptic_xyz(x, y, z, obl_deg)
    lon = math.degrees(math.atan2(ye, xe)) % DEGREES_IN_CIRCLE
    if lon < 0:
        lon += DEGREES_IN_CIRCLE
    return lon


def _true_node_tropical_deg(
    rx: float,
    ry: float,
    rz: float,
    vx: float,
    vy: float,
    vz: float,
    vernal_equinox_offset: float,
) -> Optional[float]:
    """Osculating true ascending node; tropical via J2000 obliquity + vernal offset (matches JPL planet pipeline)."""
    hx = ry * vz - rz * vy
    hy = rz * vx - rx * vz
    hz = rx * vy - ry * vx
    h_sq = hx * hx + hy * hy + hz * hz
    if not math.isfinite(h_sq) or h_sq < 1e-50:
        return None
    obl = math.radians(OBLIQUITY_J2000_DEGREES)
    kx, ky, kz = 0.0, -math.sin(obl), math.cos(obl)
    nx = ky * hz - kz * hy
    ny = kz * hx - kx * hz
    nz = kx * hy - ky * hx
    n_sq = nx * nx + ny * ny + nz * nz
    if not math.isfinite(n_sq) or n_sq < 1e-60:
        return None
    nn = math.sqrt(n_sq)
    nxs, nys, nzs = nx / nn, ny / nn, nz / nn
    lam = _ecliptic_lon_deg_from_icrf_vec(nxs, nys, nzs, OBLIQUITY_J2000_DEGREES)
    tropical = (lam - vernal_equinox_offset) % DEGREES_IN_CIRCLE
    if tropical < 0:
        tropical += DEGREES_IN_CIRCLE

    _, _, mz_e = _icrf_vec_to_ecliptic_xyz(rx, ry, rz, OBLIQUITY_J2000_DEGREES)
    _, _, vz_e = _icrf_vec_to_ecliptic_xyz(vx, vy, vz, OBLIQUITY_J2000_DEGREES)
    ascending = mz_e * vz_e < 0.0 or (abs(mz_e) < 1e-9 and vz_e > 0.0)
    if not ascending:
        tropical = (tropical + 180.0) % DEGREES_IN_CIRCLE
    return tropical


# Reduced two-body gravitational parameter for geocentric Moon vectors (km^3/s^2).
_MU_EARTH_MOON_KM3_S2 = 403503.235


def _mean_lilith_lon_deg(jd_ut: float) -> float:
    """Mean lunar apogee (mean Black Moon Lilith), degrees [0,360).

    Meeus (Astronomical Algorithms, ch.47) low-precision mean-perigee polynomial,
    plus 180 degrees to get the apogee (Lilith is defined at the empty focus/apogee
    side of the Moon's orbit, opposite the perigee).
    """
    t = (jd_ut - 2451545.0) / 36525.0
    perigee = (
        83.3532465
        + 4069.0137287 * t
        - 0.0103200 * t * t
        - (t ** 3) / 80053.0
        + (t ** 4) / 18999000.0
    )
    apogee = (perigee + 180.0) % DEGREES_IN_CIRCLE
    if apogee < 0:
        apogee += DEGREES_IN_CIRCLE
    return apogee


def _true_lilith_tropical_deg(
    rx: float,
    ry: float,
    rz: float,
    vx: float,
    vy: float,
    vz: float,
    vernal_equinox_offset: float,
) -> Optional[float]:
    """Osculating true Black Moon Lilith (lunar apogee), tropical degrees.

    Same family of computation as `_true_node_tropical_deg`, but built from the
    eccentricity (Laplace-Runge-Lenz) vector instead of the angular-momentum
    vector, since apogee/perigee is defined by the orbit's apsidal line rather
    than its nodal line.
    """
    r_sq = rx * rx + ry * ry + rz * rz
    r = math.sqrt(r_sq)
    if r < 1e-6:
        return None
    v_sq = vx * vx + vy * vy + vz * vz
    r_dot_v = rx * vx + ry * vy + rz * vz
    mu = _MU_EARTH_MOON_KM3_S2

    ex = ((v_sq - mu / r) * rx - r_dot_v * vx) / mu
    ey = ((v_sq - mu / r) * ry - r_dot_v * vy) / mu
    ez = ((v_sq - mu / r) * rz - r_dot_v * vz) / mu
    e_sq = ex * ex + ey * ey + ez * ez
    if not math.isfinite(e_sq) or e_sq < 1e-12:
        return None
    e_mag = math.sqrt(e_sq)

    # Eccentricity vector points toward perigee; apogee is the opposite direction.
    ax, ay, az = -ex / e_mag, -ey / e_mag, -ez / e_mag
    lam = _ecliptic_lon_deg_from_icrf_vec(ax, ay, az, OBLIQUITY_J2000_DEGREES)
    tropical = (lam - vernal_equinox_offset) % DEGREES_IN_CIRCLE
    if tropical < 0:
        tropical += DEGREES_IN_CIRCLE
    return tropical


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
        obliquity_j2000_deg = OBLIQUITY_J2000_DEGREES
        obliquity_j2000 = math.radians(obliquity_j2000_deg)  # J2000.0 obliquity
        
        # Formula: tan(ecl_lon) = (sin(RA) * cos(obl) + tan(Dec) * sin(obl)) / cos(RA)
        sin_ra = math.sin(ra_rad)
        cos_ra = math.cos(ra_rad)
        tan_dec = math.tan(dec_rad)
        sin_obl = math.sin(obliquity_j2000)
        cos_obl = math.cos(obliquity_j2000)
        
        ecl_lon_rad = math.atan2(sin_ra * cos_obl + tan_dec * sin_obl, cos_ra)
        lon_deg = math.degrees(ecl_lon_rad) % DEGREES_IN_CIRCLE
        if lon_deg < 0:
            lon_deg += DEGREES_IN_CIRCLE
        
        # Adjust for vernal equinox: subtract the offset so vernal equinox = 0°
        lon_deg_tropical = (lon_deg - vernal_equinox_offset) % DEGREES_IN_CIRCLE
        if lon_deg_tropical < 0:
            lon_deg_tropical += DEGREES_IN_CIRCLE
        
        return lon_deg_tropical
    except (KeyError, ValueError, AttributeError) as e:
        logger.warning("Could not compute planet position: %s", e)
        return None


def _compute_planet_extended_position(body, eph, observer, t, vernal_equinox_offset: float, 
                                      include_physical: bool = False, 
                                      include_topocentric: bool = False) -> Optional[Dict[str, float]]:
    """Compute extended position data for a planet using Skyfield.
    
    Args:
        body: Skyfield body object
        eph: Skyfield ephemeris
        observer: Skyfield Topos observer
        t: Skyfield time object
        vernal_equinox_offset: Offset to adjust for vernal equinox
        include_physical: If True, include magnitude/phase/elongation
        include_topocentric: If True, include altitude/azimuth
        
    Returns:
        Dictionary with position data, or None on error. Keys:
        - longitude: float (degrees, always present)
        - latitude: float (degrees, if available)
        - distance: float (AU, always present for JPL)
        - declination: float (degrees, always present for JPL)
        - right_ascension: float (degrees, always present for JPL)
        - altitude: float (degrees, if include_topocentric)
        - azimuth: float (degrees, if include_topocentric)
        - apparent_magnitude: float (if include_physical)
        - phase_angle: float (degrees, if include_physical)
        - elongation: float (degrees, if include_physical)
        - light_time: float (seconds, if include_physical)
        - speed: float (degrees/day, if available)
        - retrograde: bool (if available)
    """
    try:
        astrometric = (eph["earth"] + observer).at(t).observe(body).apparent()
        ra, dec, distance = astrometric.radec()
        
        # Always compute basic equatorial coordinates
        ra_deg = ra.hours * 15.0  # Convert hours to degrees
        dec_deg = dec.degrees
        distance_au = distance.au  # Distance in AU
        
        # Compute ecliptic longitude from RA/Dec
        ra_rad = math.radians(ra_deg)
        dec_rad = math.radians(dec_deg)
        obliquity_j2000_deg = OBLIQUITY_J2000_DEGREES
        obliquity_j2000 = math.radians(obliquity_j2000_deg)  # J2000.0 obliquity
        
        sin_ra = math.sin(ra_rad)
        cos_ra = math.cos(ra_rad)
        tan_dec = math.tan(dec_rad)
        sin_obl = math.sin(obliquity_j2000)
        cos_obl = math.cos(obliquity_j2000)
        
        ecl_lon_rad = math.atan2(sin_ra * cos_obl + tan_dec * sin_obl, cos_ra)
        lon_deg = math.degrees(ecl_lon_rad) % DEGREES_IN_CIRCLE
        if lon_deg < 0:
            lon_deg += DEGREES_IN_CIRCLE
        
        # Adjust for vernal equinox
        lon_deg_tropical = (lon_deg - vernal_equinox_offset) % DEGREES_IN_CIRCLE
        if lon_deg_tropical < 0:
            lon_deg_tropical += DEGREES_IN_CIRCLE
        
        # Build result dictionary
        result = {
            'longitude': float(lon_deg_tropical),
            'distance': float(distance_au),
            'declination': float(dec_deg),
            'right_ascension': float(ra_deg),
        }
        
        # Compute ecliptic latitude (optional, may not always be needed)
        # For now, set to 0.0 as approximation (full calculation would require more complex math)
        result['latitude'] = 0.0
        
        # Topocentric coordinates (altitude/azimuth)
        if include_topocentric:
            try:
                # Compute topocentric position (observer's view from Earth's surface)
                # Use the same pattern as astrometric: (eph["earth"] + observer).at(t).observe(body)
                # This gives us the position from the observer's location on Earth's surface
                topocentric = (eph["earth"] + observer).at(t).observe(body).apparent()
                # Now compute altaz from the observer's perspective
                alt, az, distance_altaz = topocentric.altaz()
                result['altitude'] = float(alt.degrees)
                result['azimuth'] = float(az.degrees)
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                logger.warning("Could not compute topocentric coordinates for %s: %s", body, e)
                # Set to None so we know it failed
                result['altitude'] = None
                result['azimuth'] = None
        
        # Physical properties
        if include_physical:
            try:
                # Light time is available from astrometric
                result['light_time'] = float(astrometric.light_time * 86400.0)  # Convert days to seconds
                
                # For planets, compute phase angle and elongation
                # Phase angle: angle between Sun, planet, and Earth
                # Elongation: angular distance from Sun
                try:
                    sun = eph["sun"]
                    sun_astrometric = (eph["earth"] + observer).at(t).observe(sun).apparent()
                    # Compute elongation (simplified - full calculation would use spherical trigonometry)
                    # For now, approximate using ecliptic longitude difference
                    sun_ra, sun_dec, _ = sun_astrometric.radec()
                    sun_ra_deg = sun_ra.hours * 15.0
                    # Elongation approximation (full calculation would be more complex)
                    elongation_approx = abs(ra_deg - sun_ra_deg)
                    if elongation_approx > 180.0:
                        elongation_approx = DEGREES_IN_CIRCLE - elongation_approx
                    result['elongation'] = float(elongation_approx)
                    
                    # Phase angle approximation (simplified)
                    # Full calculation would use distance to Sun and distance to planet
                    result['phase_angle'] = float(elongation_approx)  # Approximation
                except (AttributeError, KeyError, TypeError, ValueError):
                    pass
                
                # Apparent magnitude (not directly available from Skyfield for all bodies)
                # Would need additional computation or lookup tables
                # For now, skip this as it requires more complex calculations
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
        
        # Speed and retrograde (would require computing position at two time points)
        # For now, set defaults - full implementation would compute speed from two positions
        result['speed'] = 0.0  # Placeholder - would need to compute from two time points
        result['retrograde'] = False  # Placeholder - would need to compute from speed
        
        return result
    except (KeyError, ValueError, AttributeError) as e:
        logger.warning("Could not compute extended planet position: %s", e)
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
    outer_planets = ["mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]  # de440s.bsp only has barycenter segments for these
    
    # For de421, always try barycenter first for outer planets to avoid Skyfield errors
    if is_de421 and planet in outer_planets:
        body_name = f"{planet} barycenter"
        try:
            body = eph[body_name]
            return _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
        except (KeyError, ValueError, AttributeError) as e:
            logger.warning("Could not compute %s barycenter position: %s", planet, e)
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
                logger.warning("Could not compute %s position: %s", planet, e)
                return None
        return None


def compute_jpl_positions(name: str, dt_str: str, loc_str: str, ephemeris_path: Optional[str] = None,
                          requested_objects: Optional[List[str]] = None,
                          include_physical: bool = False,
                          include_topocentric: bool = False,
                          extended: bool = False) -> Dict[str, Union[float, Dict[str, float]]]:
    """Compute planetary positions using Skyfield JPL ephemerides.

    Parameters:
    - name: subject name (human-readable; not used in computation)
    - dt_str: datetime string (parsed by utils.Actual)
    - loc_str: location string (parsed by utils.Actual)
    - ephemeris_path: optional path to a local BSP file; falls back to default
    - requested_objects: optional list of object IDs to compute
    - include_physical: if True, include magnitude/phase/elongation (extended mode only)
    - include_topocentric: if True, include altitude/azimuth (extended mode only)
    - extended: if True, return extended format with distance/declination/RA

    Returns:
    - Mapping planet -> ecliptic longitude (float) or extended dict
    - Empty dict if computation is unavailable
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
        year = dt_aware.year
        vernal_equinox_offset = compute_vernal_equinox_offset(year, eph, observer, ts)

        for planet in planets:
            if extended:
                # Get body for extended computation
                body = None
                outer_planets = ["mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]  # de440s.bsp only has barycenter segments for these
                if is_de421 and planet in outer_planets:
                    try:
                        body = eph[f"{planet} barycenter"]
                    except KeyError:
                        pass
                if body is None:
                    try:
                        body = eph[planet]
                    except KeyError:
                        if planet in outer_planets:
                            try:
                                body = eph[f"{planet} barycenter"]
                            except KeyError:
                                pass
                
                if body is not None:
                    extended_pos = _compute_planet_extended_position(
                        body, eph, observer, t, vernal_equinox_offset,
                        include_physical=include_physical,
                        include_topocentric=include_topocentric
                    )
                    if extended_pos is not None:
                        positions[planet] = extended_pos
            else:
                # Legacy mode: return only longitude
                lon_deg_tropical = _compute_single_planet_position(planet, eph, observer, t, is_de421, vernal_equinox_offset)
                if lon_deg_tropical is not None:
                    positions[planet] = lon_deg_tropical

        # Chiron + Ceres/Pallas/Juno/Vesta: MPC-orbital-element bodies, reusing the
        # same body-observation pipeline as the planets above (extended or legacy mode).
        requested_minor = [
            b for b in _MPC_MINOR_BODY_IDS if not requested_objects or b in requested_objects
        ]
        if requested_minor:
            orbits = _load_mpc_orbits(ts)
            sun = eph["sun"]
            for body_id in requested_minor:
                orbit = orbits.get(body_id)
                if orbit is None:
                    continue
                body = sun + orbit
                if extended:
                    minor_pos = _compute_planet_extended_position(
                        body, eph, observer, t, vernal_equinox_offset,
                        include_physical=include_physical,
                        include_topocentric=include_topocentric,
                    )
                    if minor_pos is not None:
                        positions[body_id] = minor_pos
                else:
                    lon_deg_tropical = _compute_planet_ecliptic_longitude(body, eph, observer, t, vernal_equinox_offset)
                    if lon_deg_tropical is not None:
                        positions[body_id] = lon_deg_tropical

        def _wants_lunar_nodes() -> bool:
            if not requested_objects:
                return True
            return any(o in _JPL_NATIVE_LUNAR_NODES for o in requested_objects)

        def _wants_lilith() -> bool:
            if not requested_objects:
                return True
            return any(o in _JPL_NATIVE_LILITH for o in requested_objects)

        if _wants_lunar_nodes() or _wants_lilith():
            jd_ut = _jd_ut_from_datetime_utc(dt_aware)
            mean_lon = _mean_lunar_node_lon_deg(jd_ut)
            mean_lilith_lon = _mean_lilith_lon_deg(jd_ut)
            ro = requested_objects

            def w(key: str) -> bool:
                return ro is None or key in ro

            def wrap(lon: float) -> Union[float, Dict[str, float]]:
                # Pure-formula points (nodes/Lilith) have no observed distance/RA/Dec;
                # keep the extended dict shape minimal rather than fabricate values.
                return {'longitude': float(lon), 'latitude': 0.0} if extended else float(lon)

            true_nn: Optional[float] = None
            true_lilith_lon: Optional[float] = None
            try:
                geom = (eph["moon"] - eph["earth"]).at(t)
                r = geom.position.km
                v = geom.velocity.km_per_s
                true_nn = _true_node_tropical_deg(
                    float(r[0]),
                    float(r[1]),
                    float(r[2]),
                    float(v[0]),
                    float(v[1]),
                    float(v[2]),
                    vernal_equinox_offset,
                )
                true_lilith_lon = _true_lilith_tropical_deg(
                    float(r[0]),
                    float(r[1]),
                    float(r[2]),
                    float(v[0]),
                    float(v[1]),
                    float(v[2]),
                    vernal_equinox_offset,
                )
            except Exception as exc:
                logger.warning("JPL lunar node/Lilith computation failed: %s", exc)

            if w("north_node"):
                positions["north_node"] = wrap(mean_lon)
            if w("mean_node"):
                positions["mean_node"] = wrap(mean_lon)
            if w("south_node"):
                positions["south_node"] = wrap((mean_lon + 180.0) % DEGREES_IN_CIRCLE)
            if w("mean_south_node"):
                positions["mean_south_node"] = wrap((mean_lon + 180.0) % DEGREES_IN_CIRCLE)
            if true_nn is not None:
                if w("true_north_node") or w("true_node"):
                    positions["true_north_node"] = wrap(true_nn)
                    if w("true_node"):
                        positions["true_node"] = wrap(true_nn)
                if w("true_south_node"):
                    positions["true_south_node"] = wrap((true_nn + 180.0) % DEGREES_IN_CIRCLE)

            if w("lilith") or w("mean_lilith"):
                positions["lilith"] = wrap(mean_lilith_lon)
                if w("mean_lilith"):
                    positions["mean_lilith"] = wrap(mean_lilith_lon)
            if true_lilith_lon is not None and w("true_lilith"):
                positions["true_lilith"] = wrap(true_lilith_lon)

        return positions
    else:
        # Return empty dict to maintain consistent return type
        return {}


# ─────────────────────
# 🪐 REPORTING & TUI HELPERS
# ─────────────────────

_ZODIAC_SIGN_NAMES = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

# Section groupings for build_text_report, in display order.
_REPORT_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Planets", ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto")),
    ("Angles", ("asc", "mc", "desc", "ic")),
    ("Lunar Nodes", ("north_node", "south_node", "mean_node", "mean_south_node", "true_north_node", "true_south_node", "true_node")),
    ("Calculated Points", ("lilith", "mean_lilith", "true_lilith")),
    ("Asteroids", ("chiron", "ceres", "pallas", "juno", "vesta")),
    ("Houses", tuple(f"house_{i}" for i in range(1, 13))),
)


def _extract_longitude_value(value: Any) -> Optional[float]:
    lon = value.get("longitude") if isinstance(value, dict) else value
    try:
        return float(lon)
    except (TypeError, ValueError):
        return None


def _lon_to_sign_string(lon_deg: float) -> str:
    normalized = lon_deg % DEGREES_IN_CIRCLE
    sign_index = int(normalized // 30) % 12
    deg_in_sign = normalized % 30
    deg = int(deg_in_sign)
    minute = int(round((deg_in_sign - deg) * 60))
    if minute == 60:
        minute = 0
        deg += 1
    return f"{deg}°{minute:02d}' {_ZODIAC_SIGN_NAMES[sign_index]}"


def build_text_report(name: str, place: Optional[str], time: Optional[str], positions: Dict[str, Any]) -> str:
    """Plain-text position summary, grouped by object type (Skyfield-backed, no kerykeion)."""
    lines = [f"Report for {name}", f"Place: {place}", f"Time: {time}", ""]
    remaining = dict(positions)

    for section_name, body_ids in _REPORT_SECTIONS:
        rows = []
        for body_id in body_ids:
            if body_id not in remaining:
                continue
            lon = _extract_longitude_value(remaining.pop(body_id))
            if lon is not None:
                rows.append(f"  {body_id}: {_lon_to_sign_string(lon)}")
        if rows:
            lines.append(f"{section_name}:")
            lines.extend(rows)
            lines.append("")

    if remaining:
        rows = []
        for body_id, value in remaining.items():
            lon = _extract_longitude_value(value)
            if lon is not None:
                rows.append(f"  {body_id}: {_lon_to_sign_string(lon)}")
        if rows:
            lines.append("Other:")
            lines.extend(rows)
            lines.append("")

    return "\n".join(lines).rstrip()


class Subject:
    """Thin wrapper around the skyfield/JPL position pipeline, for the TUI menu.

    Usage:
    - Call at_place() then at_time() to compute `self.positions`.
    - Use data() to extract names/degrees for plotting; report() for a text summary.
    """
    def __init__(self, s_name: str, s_type: str = "Tropical") -> None:
        self.name = s_name
        self.type = s_type
        self.place_str: Optional[str] = None
        self.time_str: Optional[str] = None
        self.positions: Dict[str, Any] = {}

    def at_place(self, location: object) -> None:
        """Set place from a free-text location or coordinates string."""
        self.place_str = str(location)

    def at_time(self, time: str) -> None:
        """Set event time from a free-text datetime string and compute positions."""
        self.time_str = str(time)
        self.positions = compute_positions(EngineType.JPL, self.name, self.time_str, self.place_str or "")

    def data(self):
        """Return (object_names, degrees, labels) extracted from computed positions."""
        names: List[str] = []
        degrees: List[float] = []
        for body_id, value in self.positions.items():
            lon = _extract_longitude_value(value)
            if lon is None:
                continue
            names.append(body_id)
            degrees.append(lon)
        return names, degrees, list(names)

    def report(self) -> str:
        """Build a plain-text position report for the computed subject."""
        return build_text_report(self.name, self.place_str, self.time_str, self.positions)


def positions_to_dataframe(positions: Dict[str, Any]) -> DataFrame:
    """Flatten a positions dict (float longitudes or extended dicts) into a DataFrame.

    One row per object: id, longitude, sign, degree_in_sign, plus any other
    extended fields (distance/declination/right_ascension/...) present.
    """
    rows = []
    for body_id, value in positions.items():
        lon = _extract_longitude_value(value)
        if lon is None:
            continue
        normalized = lon % DEGREES_IN_CIRCLE
        sign_index = int(normalized // 30) % 12
        row = {
            "id": body_id,
            "longitude": normalized,
            "sign": _ZODIAC_SIGN_NAMES[sign_index],
            "degree_in_sign": normalized % 30,
        }
        if isinstance(value, dict):
            for k, v in value.items():
                if k not in row:
                    row[k] = v
        rows.append(row)
    return DataFrame(rows)


# ─────────────────────
# 🔺 ASPECT DETECTION
# ─────────────────────

def compute_aspects(bodies: List[CelestialBody], aspect_defs: List[AspectDefinition]) -> List[Aspect]:
    """Compute aspects between celestial bodies using provided definitions.
    
    Args:
        bodies: List of celestial bodies to compute aspects for
        aspect_defs: List of aspect definitions to use for detection
        
    Returns:
        List of Aspect objects representing detected aspects
    """
    aspects = []
    
    if not bodies or not aspect_defs:
        return aspects
    
    # Build a map of aspect definitions by angle for quick lookup
    aspect_by_angle: Dict[float, AspectDefinition] = {}
    for asp_def in aspect_defs:
        aspect_by_angle[asp_def.angle] = asp_def
    
    # Compare all pairs of bodies
    for i, body1 in enumerate(bodies):
        for j, body2 in enumerate(bodies[i+1:], start=i+1):
            # Get longitudes
            lon1 = body1.degree
            lon2 = body2.degree
            
            # Compute angular distance (shortest arc, always positive)
            angle_diff = abs(lon1 - lon2)
            if angle_diff > 180.0:
                angle_diff = DEGREES_IN_CIRCLE - angle_diff
            
            # Check each aspect definition
            for asp_def in aspect_defs:
                exact_angle = asp_def.angle
                orb = asp_def.default_orb
                
                # Normalize exact_angle to 0-180° range (aspects are symmetric)
                if exact_angle > 180.0:
                    exact_angle_normalized = DEGREES_IN_CIRCLE - exact_angle
                else:
                    exact_angle_normalized = exact_angle
                
                # Check if the angle difference is within orb of the exact aspect
                # angle_diff is already in 0-180° range (shortest arc)
                diff_to_exact = abs(angle_diff - exact_angle_normalized)
                
                if diff_to_exact <= orb:
                    # Found an aspect
                    aspect = Aspect(
                        type=asp_def.id,
                        source_id=body1.id,
                        target_id=body2.id,
                        angle=angle_diff,
                        orb=diff_to_exact
                    )
                    aspects.append(aspect)
                    break  # Only record one aspect per pair (the first match)
    
    return aspects


def compute_aspects_for_chart(
    chart: ChartInstance,
    aspect_definitions: Optional[List[AspectDefinition]] = None,
    ws: Optional['Workspace'] = None
) -> List[Dict[str, Any]]:
    """Compute aspects between celestial bodies in a chart.
    
    Args:
        chart: ChartInstance to compute aspects for
        aspect_definitions: List of aspect definitions (orbs, types)
                          If None, uses chart.config.aspect_orbs or workspace defaults
        ws: Optional workspace for default aspect definitions
    
    Returns:
        List of aspect dictionaries, each with:
        {
            'from': str,  # Source object ID (e.g., 'sun')
            'to': str,    # Target object ID (e.g., 'moon')
            'type': str,  # Aspect type: 'conjunction', 'sextile', 'square', 'trine', 'opposition'
            'angle': float,  # Actual angle between objects (degrees)
            'orb': float,    # Orb (deviation from exact aspect, degrees)
            'exact_angle': float,  # Exact aspect angle (0, 60, 90, 120, 180)
            'applying': bool,  # True if aspect is applying (getting closer)
            'separating': bool  # True if aspect is separating
        }
    """
    # Get positions for the chart
    positions = compute_positions_for_chart(chart, ws=ws)
    
    if not positions:
        return []
    
    # Convert positions to CelestialBody objects
    # Extract longitude from position data (handle both float and dict formats)
    bodies: List[CelestialBody] = []
    for obj_id, pos_data in positions.items():
        if isinstance(pos_data, dict):
            longitude = pos_data.get('longitude', 0.0)
        else:
            longitude = float(pos_data)
        
        # Create a CelestialBody object (we need to get definition_id from somewhere)
        # For now, use obj_id as definition_id
        body = CelestialBody(
            id=obj_id,
            definition_id=obj_id,
            degree=longitude,
            sign="",  # Sign would need to be computed from longitude
            retrograde=False,  # Would need speed data to determine
            speed=0.0  # Would need to compute from two positions
        )
        bodies.append(body)
    
    # Get aspect definitions
    if aspect_definitions is None:
        # Try to get from chart config
        cfg = _safe_get_attr(chart, 'config')
        aspect_orbs = _safe_get_attr(cfg, 'aspect_orbs') if cfg else None
        selected_aspects = _safe_get_attr(cfg, 'selected_aspects') if cfg else None
        
        # Get aspect definitions from workspace/model
        aspect_definitions = []
        if ws:
            try:
                model = get_active_model(ws)
                if model:
                    # Get aspect definitions from model
                    aspect_definitions = list(getattr(model, 'aspect_definitions', []) or [])
                    
                    if selected_aspects:
                        selected_set = {str(aspect_id).strip().lower() for aspect_id in selected_aspects}
                        aspect_definitions = [
                            asp_def for asp_def in aspect_definitions
                            if getattr(asp_def, 'id', '').strip().lower() in selected_set
                        ]

                    # Apply orb overrides from chart config
                    if aspect_orbs:
                        # Create new aspect definitions with overridden orbs
                        updated_defs = []
                        for asp_def in aspect_definitions:
                            if asp_def.id in aspect_orbs:
                                # Create new definition with overridden orb
                                new_orb = float(aspect_orbs[asp_def.id])
                                updated_def = AspectDefinition(
                                    id=asp_def.id,
                                    glyph=asp_def.glyph,
                                    angle=asp_def.angle,
                                    default_orb=new_orb,
                                    i18n=asp_def.i18n,
                                    color=asp_def.color,
                                    importance=asp_def.importance,
                                    line_style=asp_def.line_style,
                                    line_width=asp_def.line_width,
                                    show_label=asp_def.show_label,
                                    valid_contexts=asp_def.valid_contexts
                                )
                                updated_defs.append(updated_def)
                            else:
                                updated_defs.append(asp_def)
                        aspect_definitions = updated_defs
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                logger.warning("Could not get aspect definitions from workspace: %s", e)
        
        # If still no definitions, use defaults
        if not aspect_definitions:
            try:
                from module.workspace import get_all_aspect_definitions
                # Get aspects from workspace/model YAML, not SQLite
                all_aspects = get_all_aspect_definitions(ws=ws, model=model)
                aspect_definitions = list(all_aspects.values())
            except (ImportError, AttributeError, KeyError, TypeError, ValueError):
                # Fallback: create basic aspect definitions
                aspect_definitions = [
                    AspectDefinition(id='conjunction', glyph='☌', angle=0.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='opposition', glyph='☍', angle=180.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='trine', glyph='△', angle=120.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='square', glyph='□', angle=90.0, default_orb=8.0, i18n={}),
                    AspectDefinition(id='sextile', glyph='⚹', angle=60.0, default_orb=6.0, i18n={}),
                ]
    
    if aspect_definitions and selected_aspects:
        selected_set = {str(aspect_id).strip().lower() for aspect_id in selected_aspects}
        aspect_definitions = [
            asp_def for asp_def in aspect_definitions
            if getattr(asp_def, 'id', '').strip().lower() in selected_set
        ]

    # Compute aspects
    aspects = compute_aspects(bodies, aspect_definitions)
    
    # Convert Aspect objects to dictionaries
    result = []
    for aspect in aspects:
        # Find the aspect definition to get exact angle
        exact_angle = 0.0
        for asp_def in aspect_definitions:
            if asp_def.id == aspect.type:
                exact_angle = asp_def.angle
                break
        
        # Determine applying/separating
        # For now, set both to False (would need speed data to determine accurately)
        # Applying means the faster body is catching up to the slower one
        # Separating means they're moving apart
        applying = False
        separating = False
        
        # Try to determine from speeds if available
        body1 = next((b for b in bodies if b.id == aspect.source_id), None)
        body2 = next((b for b in bodies if b.id == aspect.target_id), None)
        if body1 and body2:
            # If we have speed data, we could determine applying/separating
            # For now, we'll leave it as False/False
            pass
        
        result.append({
            'from': aspect.source_id,
            'to': aspect.target_id,
            'type': aspect.type,
            'angle': float(aspect.angle),
            'orb': float(aspect.orb),
            'exact_angle': float(exact_angle),
            'applying': applying,
            'separating': separating
        })
    
    return result


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
    
    Falls back to first model if no active model is specified.
    
    Args:
        ws: Workspace instance to get active model from
        
    Returns:
        Active AstroModel instance, or None if no models available
    """
    if ws is None:
        return None
    models = getattr(ws, 'models', {}) or {}
    if not models:
        return None
    # Get active model name
    name = getattr(ws, 'active_model', None)
    if name and name in models:
        return models[name]
    # Fallback: return first available model
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

    # Aspect orbs map from model, overridden by workspace defaults when present
    aspect_orbs = _build_aspect_orbs(model)
    ws_aspect_orbs = getattr(d, 'default_aspect_orbs', None) if d else None
    if ws_aspect_orbs:
        aspect_orbs.update(dict(ws_aspect_orbs))
    out['aspect_orbs'] = aspect_orbs
    return out


def compute_positions(engine: Optional[EngineType], name: str, dt_str: str, loc_str: str,
                      ephemeris_path: Optional[str] = None, requested_objects: Optional[List[str]] = None) -> Dict[str, Union[float, Dict[str, float]]]:
    """Compute planetary/point positions via the Skyfield JPL pipeline.

    Skyfield is the only computation engine; `engine` is accepted for backward
    compatibility with older workspace files/API calls that still pass a
    `swisseph`/`jyotish`/`custom` engine value, which are logged and ignored.

    Args:
        engine: Requested engine (only JPL is honored; others are logged and ignored)
        name: Subject name
        dt_str: Datetime string
        loc_str: Location string
        ephemeris_path: Optional path to ephemeris file
        requested_objects: Optional list of object IDs to compute (filters results)

    Returns:
        Dict mapping object_id -> ecliptic_longitude (degrees) or extended dict.
        Empty dict on error or if no positions found.

    Raises:
        ValueError: If datetime or location cannot be parsed
        FileNotFoundError: If ephemeris file is specified but not found
    """
    if engine is not None and engine != EngineType.JPL:
        logger.info("engine=%s requested but only the skyfield/JPL engine is available; using JPL", engine)
    return compute_jpl_positions(name, dt_str, loc_str, ephemeris_path=ephemeris_path, requested_objects=requested_objects)


def compute_jpl_positions_for_chart(
    chart: ChartInstance,
    ws: Optional['Workspace'] = None,
    include_physical: bool = False,
    include_topocentric: bool = False,
    ephemeris_path: Optional[str] = None,
) -> Dict[str, Union[float, Dict[str, float]]]:
    """Compute JPL-backed chart positions through the backend seam."""
    cfg = _safe_get_attr(chart, 'config')

    requested_objects = _safe_get_attr(cfg, 'observable_objects') if cfg else None
    if requested_objects is None and ws:
        try:
            model = get_active_model(ws)
            if model:
                eff = resolve_effective_defaults(ws, model)
                requested_objects = eff.get('observable_objects')
        except (AttributeError, KeyError, TypeError) as e:
            logger.warning("Could not resolve observable objects from workspace: %s", e)

    name, dt_str, loc_str = _extract_chart_compute_inputs(chart)
    return compute_jpl_positions(
        name,
        dt_str,
        loc_str,
        ephemeris_path=ephemeris_path,
        requested_objects=requested_objects,
        include_physical=include_physical,
        include_topocentric=include_topocentric,
        extended=True,
    )


def _extract_chart_compute_inputs(chart: ChartInstance) -> tuple[str, str, str]:
    """Extract canonical compute inputs from a chart object."""
    subj = _safe_get_attr(chart, 'subject')
    if subj is None:
        raise ValueError("Chart has no subject")

    name = _safe_get_attr(subj, 'name')
    if not name:
        if isinstance(subj, dict):
            name = subj.get('name') or subj.get('id') or 'chart'
        else:
            name = 'chart'

    event_time = _safe_get_attr(subj, 'event_time')
    if event_time is None:
        raise ValueError(f"Chart subject has no event_time (subject type: {type(subj)})")
    if isinstance(event_time, datetime):
        dt_str = event_time.isoformat()
    else:
        dt_str = str(event_time)

    loc = _safe_get_attr(subj, 'location')
    if loc is None:
        raise ValueError("Chart subject has no location")

    lat = _safe_get_attr(loc, 'latitude')
    lon = _safe_get_attr(loc, 'longitude')
    if lat is None and isinstance(loc, dict):
        lat = loc.get('latitude')
    if lon is None and isinstance(loc, dict):
        lon = loc.get('longitude')

    if lat is not None and lon is not None:
        loc_str = f"{lat},{lon}"
    else:
        loc_str = _safe_get_attr(loc, 'name')
        if not loc_str and isinstance(loc, dict):
            loc_str = loc.get('name') or ''

    if not loc_str:
        raise ValueError(f"Could not determine location name (location type: {type(loc)})")

    return name, dt_str, loc_str


def compute_positions_for_chart(
    chart: ChartInstance, 
    ws: Optional['Workspace'] = None,
    include_physical: bool = False,
    include_topocentric: bool = False
) -> Dict[str, Union[float, Dict[str, float]]]:
    """Compute positions using a ChartInstance's engine and ephemeris settings.
    Uses chart.subject.event_time and chart.subject.location.name for location lookup.
    Handles both ChartInstance objects and dict-like structures safely.
    
    Args:
        chart: ChartInstance to compute positions for
        ws: Optional workspace for resolving observable objects defaults
        include_physical: If True, include magnitude/phase/elongation (JPL only)
        include_topocentric: If True, include altitude/azimuth (JPL with location)
        
    Returns:
        Dict mapping object_id -> position data.
        Empty dict on error or if no positions found:
        - For non-JPL engines: float (longitude in degrees)
        - For JPL engine: dict with keys:
            - 'longitude': float (degrees) - always present
            - 'latitude': float (degrees) - if available
            - 'distance': float (AU) - always present for JPL
            - 'declination': float (degrees) - always present for JPL
            - 'right_ascension': float (degrees) - always present for JPL
            - 'altitude': float (degrees) - if include_topocentric and location available
            - 'azimuth': float (degrees) - if include_topocentric and location available
            - 'apparent_magnitude': float - if include_physical
            - 'phase_angle': float (degrees) - if include_physical
            - 'elongation': float (degrees) - if include_physical
            - 'light_time': float (seconds) - if include_physical
            - 'speed': float (degrees/day) - if available
            - 'retrograde': bool - if available
        
    Raises:
        ValueError: If chart is missing required subject or location data
    """
    chart_data = compute_chart_data_for_chart(
        chart,
        ws=ws,
        include_physical=include_physical,
        include_topocentric=include_topocentric,
    )

    result = chart_data.positions

    # Ensure we return a dict
    if not isinstance(result, dict):
        logger.warning("compute_positions returned non-dict: %s = %s", type(result), result)
        return {}

    # Return empty dict if no positions found
    if not result:
        try:
            name, dt_str, loc_str = _extract_chart_compute_inputs(chart)
            logger.warning("compute_positions returned empty dict for %s at %s in %s", name, dt_str, loc_str)
        except Exception:
            logger.warning("compute_positions returned empty dict for chart %s", getattr(chart, 'id', '<unknown>'))
        return {}

    return result


def compute_chart_data_for_chart(
    chart: ChartInstance,
    ws: Optional['Workspace'] = None,
    include_physical: bool = False,
    include_topocentric: bool = False,
) -> ChartData:
    """Compute structured chart data using the active backend seam."""
    backend = backend_for_chart(chart)
    chart_data = backend.compute_chart_data(
        chart,
        ws=ws,
        include_physical=include_physical,
        include_topocentric=include_topocentric,
    )

    cfg = _safe_get_attr(chart, 'config')
    zodiac_type = _safe_get_attr(cfg, 'zodiac_type') if cfg else None
    zodiac_value = str(getattr(zodiac_type, 'value', zodiac_type) or '').lower()
    if zodiac_value == "sidereal":
        ayanamsa = _safe_get_attr(cfg, 'ayanamsa') if cfg else None
        try:
            _, dt_str, _ = _extract_chart_compute_inputs(chart)
            jd_ut = _jd_ut_from_datetime_utc(ensure_aware(Actual(dt_str, t="date").value))
            chart_data = apply_ayanamsa_to_chart_data(chart_data, ayanamsa, jd_ut)
        except (ValueError, AttributeError, KeyError) as e:
            logger.warning("Could not apply ayanamsa for sidereal chart: %s", e)

    return chart_data


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
        except (AttributeError, TypeError):
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
            logger.warning("Could not resolve all defaults from workspace/model: %s", e)
 
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
        logger.warning("Could not set all chart config defaults: %s", e)
    
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
        except (AttributeError, TypeError):
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
        except (AttributeError, TypeError):
            continue
    return rows


def build_radix_figure_for_chart(chart: ChartInstance, engine_override: Optional[EngineType] = None,
                                 ephemeris_path_override: Optional[str] = None, ws: Optional['Workspace'] = None,
                                 transit_positions: Optional[Dict[str, Any]] = None) -> Any:
    """Extract positions from a ChartInstance's computed_chart and return a Plotly Figure ready to render.

    Always recomputes positions to ensure accuracy, as stored computed_chart may contain
    initial/default values that are incorrect.

    Args:
        chart: ChartInstance to compute positions for
        engine_override: Optional engine to use instead of chart's stored engine
        ephemeris_path_override: Optional ephemeris path to use instead of chart's stored path
        ws: Optional workspace for resolving observable objects defaults
        transit_positions: Optional transiting-body longitudes; when supplied, the figure
            gains an additional ring outside the radix's own outer border (a bi-wheel), the
            same way a transit overlay works in the React reference app.

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
        if requested_objects is None and ws:
            try:
                model = get_active_model(ws)
                if model:
                    eff = resolve_effective_defaults(ws, model)
                    requested_objects = eff.get('observable_objects')
            except (AttributeError, KeyError, TypeError) as e:
                # Log but don't fail - use None as fallback (will compute all objects)
                logger.warning("Could not resolve observable objects from workspace: %s", e)
        
        subj = _safe_get_attr(chart, 'subject')
        name = _safe_get_attr(subj, 'name') or 'chart'
        event_time = _safe_get_attr(subj, 'event_time')
        # Convert datetime to ISO format string for reliable parsing
        if isinstance(event_time, datetime):
            dt_str = event_time.isoformat()
        else:
            dt_str = str(event_time) if event_time else ''
        loc = _safe_get_attr(subj, 'location')
        loc_str = _safe_get_attr(loc, 'name') or '' if loc else ''
        if not loc_str and loc:
            lat = _safe_get_attr(loc, 'latitude')
            lon = _safe_get_attr(loc, 'longitude')
            if lat is not None and lon is not None:
                loc_str = f"{lat},{lon}"
        
        positions = compute_positions(engine_override, name, dt_str, loc_str,
                                     ephemeris_path=ephemeris_path_override,
                                     requested_objects=requested_objects)
    else:
        positions = compute_positions_for_chart(chart, ws=ws)

    # House cusps/axes are engine-agnostic (derived from ASC/house-system math, not the
    # planetary ephemeris backend), so fetch them from the chart's own configured engine
    # even when an override engine was used for the positions above.
    house_cusps, axis_longitudes, aspects = None, None, None
    try:
        chart_data = compute_chart_data_for_chart(chart, ws=ws)
        house_cusps = chart_data.house_cusps or None
        axis_longitudes = chart_data.axes or None
        cfg = _safe_get_attr(chart, 'config')
        selected_aspects = _safe_get_attr(cfg, 'selected_aspects') if cfg else None
        aspect_orbs = _safe_get_attr(cfg, 'aspect_orbs') if cfg else None
        try:
            from module.z_visual import _canonical_positions
        except ImportError:
            from z_visual import _canonical_positions
        aspects = compute_normalized_chart_aspects(
            _canonical_positions(positions), aspect_orbs=aspect_orbs, selected_aspects=selected_aspects,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        logger.warning("Could not resolve house cusps/axes/aspects for radix rendering: %s", e)

    # Verify we got valid positions (not all zeros or suspiciously clustered)
    if not positions:
        # If no positions, log error and return empty figure with warning
        logger.error("build_radix_figure_for_chart got empty positions for chart %s", _safe_get_attr(chart, 'id', default='unknown'))
        # Return an empty figure rather than crashing
        import plotly.graph_objects as go
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="No positions computed. Check chart data and computation engine settings.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return empty_fig
    
    # Check if all values are suspiciously close to 0 (within -5 to 5 degrees).
    # Values may be plain floats or extended {'longitude': ...} dicts (JPL engine).
    longitudes = [v.get("longitude") if isinstance(v, dict) else v for v in positions.values()]
    longitudes = [v for v in longitudes if isinstance(v, (int, float))]
    all_near_zero = bool(longitudes) and all(abs(v) < 5.0 for v in longitudes)
    if all_near_zero:
        # This suggests the computation might be using wrong parameters
        # But we'll still render it - the user can see the issue
        import warnings
        warnings.warn(
            f"All computed positions are near 0° (within -5° to 5°). "
            f"This may indicate incorrect time/location parameters. "
            f"Positions: {positions}"
        )
    
    try:
        from module.z_visual import build_radix_figure
    except ImportError:
        from z_visual import build_radix_figure
    return build_radix_figure(
        positions, house_cusps=house_cusps, axis_longitudes=axis_longitudes, aspects=aspects,
        transit_positions=transit_positions,
    )


def compute_positions_for_inputs(engine: Optional[EngineType], name: str,
                                 dt_str: str, loc_text: str,
                                 ephemeris_path: Optional[str] = None,
                                 requested_objects: Optional[List[str]] = None) -> Dict[str, float]:
    """Thin wrapper over compute_positions to normalize/forward parameters from UI layers."""
    return compute_positions(engine, name, dt_str, loc_text, ephemeris_path=ephemeris_path, requested_objects=requested_objects)
