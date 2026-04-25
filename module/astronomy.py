from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Protocol, Union

try:
    from module.models import ChartInstance, EngineType, Workspace
except ImportError:
    from models import ChartInstance, EngineType, Workspace


PositionResult = Dict[str, Union[float, Dict[str, float]]]
DEGREES_IN_CIRCLE = 360.0


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
    return _normalize_deg(asc)


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


def _local_ramc_from_fraction(anchor_deg: float, fraction: float, sa_deg: float) -> float:
    return _normalize_deg(anchor_deg + fraction * sa_deg)


def _placidus_cusp(anchor_deg: float, fraction: float, eps_rad: float, lat_rad: float) -> float:
    lon = anchor_deg
    for _ in range(20):
        lon_rad = math.radians(lon)
        dec = math.asin(math.sin(eps_rad) * math.sin(lon_rad))
        cos_dec = math.cos(dec)
        if abs(cos_dec) < 1e-10:
            break
        cos_sa = -(math.tan(lat_rad) * math.tan(dec))
        if abs(cos_sa) > 1.0:
            break
        sa = math.degrees(math.acos(cos_sa))
        ramc_cusp = _local_ramc_from_fraction(anchor_deg, fraction, sa)
        ramc_rad = math.radians(ramc_cusp)
        new_lon = math.degrees(
            math.atan2(math.sin(ramc_rad), math.cos(ramc_rad) * math.cos(eps_rad))
        )
        new_lon = _normalize_deg(new_lon)
        if abs(new_lon - lon) < 1e-6:
            return new_lon
        lon = new_lon
    return lon


def _placidus_cusps(
    jd_ut: float,
    geo_lat_deg: float,
    asc_lon_deg: float,
    mc_lon_deg: float,
) -> tuple[List[float], List[str]]:
    if abs(geo_lat_deg) > 66.0:
        return (
            _whole_sign_cusps(asc_lon_deg),
            ["placidus_undefined_at_latitude; whole_sign_used"],
        )

    eps = math.radians(_mean_obliquity_deg(jd_ut))
    lat = math.radians(geo_lat_deg)
    desc = _normalize_deg(asc_lon_deg + 180.0)
    ic = _normalize_deg(mc_lon_deg + 180.0)

    h11 = _placidus_cusp(mc_lon_deg, 1.0 / 3.0, eps, lat)
    h12 = _placidus_cusp(mc_lon_deg, 2.0 / 3.0, eps, lat)
    h2 = _placidus_cusp(ic, 2.0 / 3.0, eps, lat)
    h3 = _placidus_cusp(ic, 1.0 / 3.0, eps, lat)
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
            axes["asc"],
            axes["mc"],
        )
    else:
        house_cusps = _whole_sign_cusps(axes["asc"])
        warnings = []

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
class SwissAstronomyBackend:
    def backend_id(self) -> str:
        return "swisseph"

    def ephemeris_source(self, chart: ChartInstance) -> Optional[str]:
        return None

    def compute_positions(
        self,
        chart: ChartInstance,
        ws: Optional[Workspace] = None,
        include_physical: bool = False,
        include_topocentric: bool = False,
    ) -> PositionResult:
        try:
            from module.services import compute_swiss_positions_for_chart
        except ImportError:
            from services import compute_swiss_positions_for_chart

        return compute_swiss_positions_for_chart(chart, ws=ws)

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
        return _positions_to_chart_data(positions)


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
    cfg = getattr(chart, "config", None)
    engine = getattr(cfg, "engine", None) if cfg else None
    ephemeris_path = getattr(cfg, "override_ephemeris", None) if cfg else None

    if engine is None and ephemeris_path:
        engine = EngineType.JPL

    if engine == EngineType.JPL:
        return JplAstronomyBackend(ephemeris_path=ephemeris_path)

    return SwissAstronomyBackend()
