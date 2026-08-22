from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Protocol, Union

try:
    from module.models import Ayanamsa, ChartInstance, Workspace
except ImportError:
    from models import Ayanamsa, ChartInstance, Workspace


PositionResult = Dict[str, Union[float, Dict[str, float]]]
DEGREES_IN_CIRCLE = 360.0

_NORMALIZED_ASPECT_SPECS: List[tuple[str, float, float]] = [
    ("conjunction", 0.0, 8.0),
    ("sextile", 60.0, 6.0),
    ("square", 90.0, 8.0),
    ("trine", 120.0, 8.0),
    ("quincunx", 150.0, 3.0),
    ("opposition", 180.0, 8.0),
]


@dataclass
class ChartData:
    """Structured chart computation result — mirrors Rust's AstronomyChartData.

    positions: planet/point longitudes keyed by body id
    axes: asc/mc/ic/desc longitudes (empty dict when unavailable)
    house_cusps: 12 house cusp longitudes in order (empty list when unavailable)
    warnings: non-fatal issues such as partial_axes or partial_house_cusps
    """
    positions: PositionResult
    axes: Dict[str, float] = field(default_factory=dict)
    house_cusps: List[float] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _extract_longitude(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        lon = value.get("longitude")
        if isinstance(lon, (int, float)):
            return float(lon)
    return None


def _positions_to_chart_data(positions: PositionResult) -> ChartData:
    """Split a flat positions dict (including angle/house keys) into ChartData."""
    warnings: List[str] = []

    axes: Dict[str, float] = {}
    for key in ("asc", "desc", "mc", "ic"):
        lon = _extract_longitude(positions.get(key))
        if lon is not None:
            axes[key] = lon
    if len(axes) not in (0, 4):
        warnings.append("partial_axes")

    house_cusps: List[float] = []
    partial_houses = False
    for index in range(1, 13):
        lon = _extract_longitude(positions.get(f"house_{index}"))
        if lon is None:
            partial_houses = partial_houses or bool(house_cusps)
            house_cusps = []
            break
        house_cusps.append(lon)
    if partial_houses:
        warnings.append("partial_house_cusps")

    planet_positions = {
        k: v for k, v in positions.items()
        if k not in ("asc", "desc", "mc", "ic")
        and not k.startswith("house_")
    }
    return ChartData(
        positions=planet_positions,
        axes=axes,
        house_cusps=house_cusps,
        warnings=warnings,
    )


def _normalize_deg(deg: float) -> float:
    return deg % DEGREES_IN_CIRCLE


def _shortest_arc_deg(a: float, b: float) -> float:
    diff = abs(_normalize_deg(a) - _normalize_deg(b))
    if diff > 180.0:
        diff = 360.0 - diff
    return diff


def _extract_longitude_for_aspect_detection(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        lon = value.get("longitude")
        if isinstance(lon, (int, float)):
            return float(lon)
    return None


def compute_normalized_chart_aspects(
    positions: Dict[str, Any],
    aspect_orbs: Optional[Dict[str, float]] = None,
    selected_aspects: Optional[List[str]] = None,
    aspect_definitions: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """Compute chart aspects from resolved model definitions and effective orbs."""
    normalized_positions: Dict[str, float] = {}
    for key, value in positions.items():
        lon = _extract_longitude_for_aspect_detection(value)
        if lon is not None:
            normalized_positions[key] = lon

    selected = None
    if selected_aspects is not None:
        selected = {str(item).strip().lower() for item in selected_aspects}

    specs: List[tuple[str, float, float]] = []
    orb_map = aspect_orbs or {}
    definitions = (
        [
            (
                str(definition.id),
                float(definition.angle),
                float(definition.default_orb),
            )
            for definition in aspect_definitions
        ]
        if aspect_definitions is not None
        else _NORMALIZED_ASPECT_SPECS
    )
    for aspect_id, angle, default_orb in definitions:
        if selected is not None and aspect_id not in selected:
            continue
        orb = orb_map.get(aspect_id, default_orb)
        try:
            orb_value = max(0.0, float(orb))
        except (TypeError, ValueError):
            orb_value = default_orb
        specs.append((aspect_id, angle, orb_value))

    ids = sorted(normalized_positions.keys())
    output: List[Dict[str, Any]] = []
    for index, source_id in enumerate(ids):
        source_lon = normalized_positions[source_id]
        for target_id in ids[index + 1:]:
            target_lon = normalized_positions[target_id]
            angle = _shortest_arc_deg(source_lon, target_lon)
            for aspect_id, exact_angle, allowed_orb in specs:
                normalized_exact = 360.0 - exact_angle if exact_angle > 180.0 else exact_angle
                orb = abs(angle - normalized_exact)
                if orb <= allowed_orb:
                    output.append(
                        {
                            "from": source_id,
                            "to": target_id,
                            "type": aspect_id,
                            "angle": angle,
                            "orb": orb,
                            "exact_angle": exact_angle,
                            "applying": False,
                            "separating": False,
                        }
                    )
                    break
    return output


def compute_normalized_cross_aspects(
    source_positions: Dict[str, Any],
    target_positions: Dict[str, Any],
    aspect_orbs: Optional[Dict[str, float]] = None,
    selected_aspects: Optional[List[str]] = None,
    aspect_definitions: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """Compute aspects between two charts using the resolved model contract."""
    source = {
        key: longitude
        for key, value in source_positions.items()
        if (longitude := _extract_longitude_for_aspect_detection(value)) is not None
    }
    target = {
        key: longitude
        for key, value in target_positions.items()
        if (longitude := _extract_longitude_for_aspect_detection(value)) is not None
    }
    selected = (
        {str(item).strip().lower() for item in selected_aspects}
        if selected_aspects is not None
        else None
    )
    definitions = (
        [
            (str(item.id), float(item.angle), float(item.default_orb))
            for item in aspect_definitions
        ]
        if aspect_definitions is not None
        else _NORMALIZED_ASPECT_SPECS
    )
    orb_map = aspect_orbs or {}
    specs = []
    for aspect_id, exact_angle, default_orb in definitions:
        if selected is not None and aspect_id not in selected:
            continue
        try:
            allowed_orb = max(0.0, float(orb_map.get(aspect_id, default_orb)))
        except (TypeError, ValueError):
            allowed_orb = default_orb
        specs.append((aspect_id, exact_angle, allowed_orb))

    output: List[Dict[str, Any]] = []
    for source_id in sorted(source):
        for target_id in sorted(target):
            angle = _shortest_arc_deg(source[source_id], target[target_id])
            for aspect_id, exact_angle, allowed_orb in specs:
                normalized_exact = (
                    360.0 - exact_angle if exact_angle > 180.0 else exact_angle
                )
                orb = abs(angle - normalized_exact)
                if orb <= allowed_orb:
                    output.append(
                        {
                            "from": source_id,
                            "to": target_id,
                            "type": aspect_id,
                            "angle": angle,
                            "orb": orb,
                            "exact_angle": exact_angle,
                            "applying": False,
                            "separating": False,
                        }
                    )
                    break
    return output


def _julian_day_from_unix(unix_secs: float) -> float:
    return 2440587.5 + unix_secs / 86400.0


def _j2000_centuries(jd_ut: float) -> float:
    return (jd_ut - 2451545.0) / 36525.0


def _mean_obliquity_deg(jd_ut: float) -> float:
    t = _j2000_centuries(jd_ut)
    return (
        23.439291111
        - 0.013004167 * t
        - 0.000000164 * t * t
        + 0.000000504 * t * t * t
    )


# Ayanamsa value at J2000.0, degrees. There is no existing numeric ayanamsa
# table anywhere in this codebase or the sibling tauri-application repo to
# mirror (its Rust swisseph.rs path only maps the enum to libswe's sidereal-mode
# constants, behind a disabled-by-default feature) — this is a new, Python-only
# reference table. Cross-check against a published ephemeris before relying on
# it for precision work; it's a linear (precession-rate) approximation.
_AYANAMSA_J2000_DEG: Dict[Ayanamsa, float] = {
    Ayanamsa.LAHIRI: 23.85667,
    Ayanamsa.FAGAN_BRADLEY: 24.73648,
    Ayanamsa.RAMAN: 22.33667,
    Ayanamsa.KRISHNAMURTI: 23.75722,
    Ayanamsa.DE_LUCE: 24.04528,
}

# General precession in longitude, degrees/century (~50.29"/yr).
_AYANAMSA_PRECESSION_DEG_PER_CENTURY = 1.396971


def _ayanamsa_value_deg(ayanamsa: Optional[Ayanamsa], jd_ut: float) -> float:
    """Ayanamsa (tropical - sidereal offset) for the given ayanamsa and date.

    `Ayanamsa.USER_DEFINED` and unset/unknown values fall back to Fagan-Bradley
    (matches the fallback the sibling Rust backend uses for the same enum).
    """
    base = _AYANAMSA_J2000_DEG.get(ayanamsa, _AYANAMSA_J2000_DEG[Ayanamsa.FAGAN_BRADLEY]) if ayanamsa is not None else _AYANAMSA_J2000_DEG[Ayanamsa.FAGAN_BRADLEY]
    return base + _AYANAMSA_PRECESSION_DEG_PER_CENTURY * _j2000_centuries(jd_ut)


def _shift_longitude_value(value: Any, shift_deg: float) -> Any:
    """Shift a position value (float or dict-with-longitude) by -shift_deg, wrapped to [0,360)."""
    if isinstance(value, (int, float)):
        return _normalize_deg(float(value) - shift_deg)
    if isinstance(value, dict) and isinstance(value.get("longitude"), (int, float)):
        shifted = dict(value)
        shifted["longitude"] = _normalize_deg(float(value["longitude"]) - shift_deg)
        return shifted
    return value


def apply_ayanamsa_to_chart_data(chart_data: ChartData, ayanamsa: Optional[Ayanamsa], jd_ut: float) -> ChartData:
    """Shift positions/axes/house_cusps from tropical to sidereal by a uniform ayanamsa offset."""
    shift = _ayanamsa_value_deg(ayanamsa, jd_ut)
    chart_data.positions = {k: _shift_longitude_value(v, shift) for k, v in chart_data.positions.items()}
    chart_data.axes = {k: _normalize_deg(v - shift) for k, v in chart_data.axes.items()}
    chart_data.house_cusps = [_normalize_deg(v - shift) for v in chart_data.house_cusps]
    return chart_data


def _gmst_deg(jd_ut: float) -> float:
    d = jd_ut - 2451545.0
    t = d / 36525.0
    theta = (
        280.46061837
        + 360.98564736629 * d
        + 0.000387933 * t * t
        - t * t * t / 38710000.0
    )
    return _normalize_deg(theta)


def _local_sidereal_time_deg(jd_ut: float, geo_lon_deg: float) -> float:
    return _normalize_deg(_gmst_deg(jd_ut) + geo_lon_deg)


def _midheaven_lon(ramc_deg: float, obliquity_deg: float) -> float:
    ramc = math.radians(ramc_deg)
    eps = math.radians(obliquity_deg)
    mc = math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps)))
    return _normalize_deg(mc)


def _ascendant_lon(ramc_deg: float, obliquity_deg: float, geo_lat_deg: float) -> float:
    ramc = math.radians(ramc_deg)
    eps = math.radians(obliquity_deg)
    lat = math.radians(geo_lat_deg)

    if abs(lat) >= math.pi / 2.0 - 1e-9:
        raise ValueError("Ascendant undefined at geographic poles")

    y = -math.cos(ramc)
    x = math.sin(eps) * math.tan(lat) + math.cos(eps) * math.sin(ramc)
    asc = math.degrees(math.atan2(y, x))
    return _normalize_deg(asc + 180.0)


def _compute_axes(jd_ut: float, geo_lat_deg: float, geo_lon_deg: float) -> Dict[str, float]:
    eps = _mean_obliquity_deg(jd_ut)
    ramc = _local_sidereal_time_deg(jd_ut, geo_lon_deg)
    mc = _midheaven_lon(ramc, eps)
    asc = _ascendant_lon(ramc, eps, geo_lat_deg)
    return {
        "asc": asc,
        "desc": _normalize_deg(asc + 180.0),
        "mc": mc,
        "ic": _normalize_deg(mc + 180.0),
    }


def _whole_sign_cusps(asc_lon_deg: float) -> List[float]:
    first_house_start = math.floor(asc_lon_deg / 30.0) * 30.0
    return [_normalize_deg(first_house_start + i * 30.0) for i in range(12)]


def _angular_delta_deg_shortest(from_deg: float, to_deg: float) -> float:
    delta = _normalize_deg(to_deg) - _normalize_deg(from_deg)
    if delta > 180.0:
        delta -= 360.0
    elif delta < -180.0:
        delta += 360.0
    return delta


def _placidus_cusp(
    rectasc_deg: float,
    initial_pole_height_deg: float,
    divisor: float,
    obliquity_deg: float,
    lat_rad: float,
) -> float:
    cusp = _great_circle_ecliptic_intersection(rectasc_deg, initial_pole_height_deg, obliquity_deg)
    tan_lat = math.tan(lat_rad)

    for _ in range(100):
        decl_tan = math.tan(
            math.asin(math.sin(math.radians(obliquity_deg)) * math.sin(math.radians(cusp)))
        )
        if abs(decl_tan) < 1e-12:
            return rectasc_deg

        asin_arg = max(-1.0, min(1.0, tan_lat * decl_tan))
        pole_height = math.degrees(
            math.atan(math.sin(math.asin(asin_arg) / divisor) / decl_tan)
        )
        next_cusp = _great_circle_ecliptic_intersection(rectasc_deg, pole_height, obliquity_deg)

        if abs(_angular_delta_deg_shortest(cusp, next_cusp)) < 1.0 / 360_000.0:
            return next_cusp
        cusp = next_cusp

    return cusp


def _placidus_cusps(
    jd_ut: float,
    geo_lat_deg: float,
    geo_lon_deg: float,
    asc_lon_deg: float,
    mc_lon_deg: float,
) -> tuple[List[float], List[str]]:
    eps_deg = _mean_obliquity_deg(jd_ut)
    if abs(geo_lat_deg) >= 90.0 - eps_deg:
        return (
            _whole_sign_cusps(asc_lon_deg),
            ["placidus_undefined_at_latitude; whole_sign_used"],
        )

    ramc = _local_sidereal_time_deg(jd_ut, geo_lon_deg)
    lat = math.radians(geo_lat_deg)
    desc = _normalize_deg(asc_lon_deg + 180.0)
    ic = _normalize_deg(mc_lon_deg + 180.0)

    tan_eps = math.tan(math.radians(eps_deg))
    a = math.degrees(math.asin(math.tan(lat) * tan_eps))
    fh1 = math.degrees(math.atan(math.sin(math.radians(a / 3.0)) / tan_eps))
    fh2 = math.degrees(math.atan(math.sin(math.radians(a * 2.0 / 3.0)) / tan_eps))

    h11 = _placidus_cusp(_normalize_deg(ramc + 30.0), fh1, 3.0, eps_deg, lat)
    h12 = _placidus_cusp(_normalize_deg(ramc + 60.0), fh2, 1.5, eps_deg, lat)
    h2 = _placidus_cusp(_normalize_deg(ramc + 120.0), fh2, 1.5, eps_deg, lat)
    h3 = _placidus_cusp(_normalize_deg(ramc + 150.0), fh1, 3.0, eps_deg, lat)

    h5 = _normalize_deg(h11 + 180.0)
    h6 = _normalize_deg(h12 + 180.0)
    h8 = _normalize_deg(h2 + 180.0)
    h9 = _normalize_deg(h3 + 180.0)

    return ([
        asc_lon_deg,
        h2,
        h3,
        ic,
        h5,
        h6,
        desc,
        h8,
        h9,
        mc_lon_deg,
        h11,
        h12,
    ], [])


def _great_circle_ecliptic_intersection_q1(
    x_deg: float, pole_height_deg: float, obliquity_deg: float
) -> float:
    x = math.radians(x_deg)
    pole_height = math.radians(pole_height_deg)
    eps = math.radians(obliquity_deg)
    denominator = -math.tan(pole_height) * math.sin(eps) + math.cos(eps) * math.cos(x)
    angle = math.degrees(math.atan2(math.sin(x), denominator))
    return angle + 180.0 if angle < 0.0 else angle


def _great_circle_ecliptic_intersection(
    equator_crossing_deg: float, pole_height_deg: float, obliquity_deg: float
) -> float:
    x = _normalize_deg(equator_crossing_deg)
    if abs(90.0 - pole_height_deg) < 1e-10:
        return 180.0
    if abs(90.0 + pole_height_deg) < 1e-10:
        return 0.0

    quadrant = math.floor(x / 90.0) + 1
    if quadrant == 1:
        projected = _great_circle_ecliptic_intersection_q1(x, pole_height_deg, obliquity_deg)
    elif quadrant == 2:
        projected = 180.0 - _great_circle_ecliptic_intersection_q1(
            180.0 - x, -pole_height_deg, obliquity_deg
        )
    elif quadrant == 3:
        projected = 180.0 + _great_circle_ecliptic_intersection_q1(
            x - 180.0, -pole_height_deg, obliquity_deg
        )
    else:
        projected = 360.0 - _great_circle_ecliptic_intersection_q1(
            360.0 - x, pole_height_deg, obliquity_deg
        )
    return _normalize_deg(projected)


def _campanus_cusps(
    jd_ut: float,
    geo_lat_deg: float,
    geo_lon_deg: float,
    asc_lon_deg: float,
    mc_lon_deg: float,
) -> tuple[List[float], List[str]]:
    eps = _mean_obliquity_deg(jd_ut)
    ramc = _local_sidereal_time_deg(jd_ut, geo_lon_deg)

    lat = math.radians(geo_lat_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    if abs(cos_lat) < 1e-12:
        return (
            _whole_sign_cusps(asc_lon_deg),
            ["campanus_undefined_at_geographic_pole; whole_sign_used"],
        )

    sqrt3 = math.sqrt(3.0)
    fh1 = math.degrees(math.asin(sin_lat * 0.5))
    fh2 = math.degrees(math.asin(sin_lat * sqrt3 * 0.5))
    xh1 = math.degrees(math.atan(sqrt3 / cos_lat))
    xh2 = math.degrees(math.atan((1.0 / sqrt3) / cos_lat))

    h11 = _great_circle_ecliptic_intersection(ramc + 90.0 - xh1, fh1, eps)
    h12 = _great_circle_ecliptic_intersection(ramc + 90.0 - xh2, fh2, eps)
    h2 = _great_circle_ecliptic_intersection(ramc + 90.0 + xh2, fh2, eps)
    h3 = _great_circle_ecliptic_intersection(ramc + 90.0 + xh1, fh1, eps)

    desc = _normalize_deg(asc_lon_deg + 180.0)
    ic = _normalize_deg(mc_lon_deg + 180.0)
    cusps = [
        asc_lon_deg,
        h2,
        h3,
        ic,
        _normalize_deg(h11 + 180.0),
        _normalize_deg(h12 + 180.0),
        desc,
        _normalize_deg(h2 + 180.0),
        _normalize_deg(h3 + 180.0),
        mc_lon_deg,
        h11,
        h12,
    ]
    return cusps, []


def _chart_axes_and_house_cusps(chart: ChartInstance) -> tuple[Dict[str, float], List[float], List[str]]:
    subject = getattr(chart, "subject", None)
    event_time = getattr(subject, "event_time", None)
    location = getattr(subject, "location", None)
    if event_time is None or location is None:
        return {}, [], []

    latitude = getattr(location, "latitude", None)
    longitude = getattr(location, "longitude", None)
    if latitude is None or longitude is None:
        return {}, [], []

    unix_secs = event_time.timestamp()
    jd_ut = _julian_day_from_unix(unix_secs)
    axes = _compute_axes(jd_ut, float(latitude), float(longitude))

    house_system = getattr(getattr(chart, "config", None), "house_system", None)
    house_system_value = getattr(house_system, "value", house_system)
    if house_system_value == "Placidus":
        house_cusps, warnings = _placidus_cusps(
            jd_ut,
            float(latitude),
            float(longitude),
            axes["asc"],
            axes["mc"],
        )
    elif house_system_value == "Campanus":
        house_cusps, warnings = _campanus_cusps(
            jd_ut,
            float(latitude),
            float(longitude),
            axes["asc"],
            axes["mc"],
        )
    elif house_system_value in (None, "Whole Sign"):
        house_cusps = _whole_sign_cusps(axes["asc"])
        warnings = []
    else:
        house_cusps = _whole_sign_cusps(axes["asc"])
        name = house_system_value.lower()
        warnings = [f"house_system_{name}_not_yet_supported: whole_sign_used"]

    return axes, house_cusps, warnings


class AstronomyBackend(Protocol):
    def backend_id(self) -> str: ...
    def ephemeris_source(self, chart: ChartInstance) -> Optional[str]: ...
    def compute_positions(
        self,
        chart: ChartInstance,
        ws: Optional[Workspace] = None,
        include_physical: bool = False,
        include_topocentric: bool = False,
    ) -> PositionResult: ...
    def compute_chart_data(
        self,
        chart: ChartInstance,
        ws: Optional[Workspace] = None,
        include_physical: bool = False,
        include_topocentric: bool = False,
    ) -> ChartData: ...


@dataclass(frozen=True)
class JplAstronomyBackend:
    ephemeris_path: Optional[str] = None

    def backend_id(self) -> str:
        return "jpl"

    def ephemeris_source(self, chart: ChartInstance) -> Optional[str]:
        override = getattr(getattr(chart, "config", None), "override_ephemeris", None)
        if override:
            return str(override)

        try:
            from module.utils import default_ephemeris_path
        except ImportError:
            from utils import default_ephemeris_path

        try:
            return str(default_ephemeris_path())
        except Exception:
            return None

    def compute_positions(
        self,
        chart: ChartInstance,
        ws: Optional[Workspace] = None,
        include_physical: bool = False,
        include_topocentric: bool = False,
    ) -> PositionResult:
        try:
            from module.services import compute_jpl_positions_for_chart
        except ImportError:
            from services import compute_jpl_positions_for_chart

        return compute_jpl_positions_for_chart(
            chart,
            ws=ws,
            include_physical=include_physical,
            include_topocentric=include_topocentric,
            ephemeris_path=self.ephemeris_path,
        )

    def compute_chart_data(
        self,
        chart: ChartInstance,
        ws: Optional[Workspace] = None,
        include_physical: bool = False,
        include_topocentric: bool = False,
    ) -> ChartData:
        positions = self.compute_positions(
            chart, ws=ws,
            include_physical=include_physical,
            include_topocentric=include_topocentric,
        )
        chart_data = _positions_to_chart_data(positions)
        axes, house_cusps, warnings = _chart_axes_and_house_cusps(chart)
        chart_data.axes = axes
        chart_data.house_cusps = house_cusps
        chart_data.warnings.extend(warnings)
        return chart_data


def backend_for_chart(chart: ChartInstance) -> AstronomyBackend:
    """Skyfield/JPL is the only astronomy backend; `engine` config is accepted
    for backward compatibility with old workspace files but does not change
    which backend runs.
    """
    cfg = getattr(chart, "config", None)
    ephemeris_path = getattr(cfg, "override_ephemeris", None) if cfg else None
    return JplAstronomyBackend(ephemeris_path=ephemeris_path)
