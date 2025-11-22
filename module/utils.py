# utils.py

from dataclasses import asdict, is_dataclass
from datetime import datetime, date, time, timedelta
from dateutil.parser import parse
from enum import Enum
from geopy.geocoders import Nominatim
from geopy.location import Location as GeoLocation
from geopy.exc import GeopyError
import math
import pytz
from re import match
from timezonefinder import TimezoneFinder
from typing import Optional, Union, List, Tuple, Dict, Any
from pathlib import Path
import yaml
import json



try:
    # For running as part of the package (e.g. from root or in tests)
    from module.models import (
        AspectDefinition, AstroModel, BodyDefinition, DateRange, HouseSystem, ChartConfig, ChartInstance, ChartSubject,
        Location, ModelSettings, Sign, ChartMode, EngineType, ZodiacType, Ayanamsa,
        Workspace, EphemerisSource, WorkspaceDefaults
    )
except ImportError:
    # For running directly (e.g. python3 module/utils.py)
    from models import (
        AspectDefinition, AstroModel, BodyDefinition, DateRange, HouseSystem, ChartConfig, ChartInstance, ChartSubject,
        Location, ModelSettings, Sign, ChartMode, EngineType, ZodiacType, Ayanamsa,
        Workspace, EphemerisSource, WorkspaceDefaults
    )

# simple in-process cache to avoid repeated geocoding of same string
_GEOCODE_CACHE: dict[str, Optional[GeoLocation]] = {}

def now_utc() -> datetime:
    """Return current time as a timezone-aware UTC datetime."""
    return datetime.now(pytz.UTC)


def find_vernal_equinox_datetime(year: int) -> datetime:
    """Find the approximate datetime of the vernal equinox for a given year.
    
    The vernal equinox typically occurs around March 20-21. This function returns
    an approximate datetime (March 20, noon UTC) that can be refined by iterating
    to find when the Sun's declination is exactly 0°.
    
    Args:
        year: The year to find the vernal equinox for
        
    Returns:
        A timezone-aware UTC datetime for the approximate vernal equinox
    """
    return datetime(year, 3, 20, 12, 0, 0, tzinfo=pytz.UTC)


def compute_vernal_equinox_offset(year: int, eph, observer, ts) -> float:
    """Compute the vernal equinox offset for tropical astrology adjustment.
    
    Finds the exact vernal equinox (when Sun's declination = 0°) and computes
    the Sun's ecliptic longitude at that moment. This offset is used to adjust
    JPL/Skyfield positions from J2000.0 coordinates to equinox-of-date coordinates
    for tropical astrology.
    
    Args:
        year: The year to compute the vernal equinox for
        eph: Skyfield ephemeris object
        observer: Skyfield Topos observer object
        ts: Skyfield timescale object
        
    Returns:
        The ecliptic longitude offset in degrees [0, 360)
    """
    
    
    # Get approximate vernal equinox date
    vernal_start = find_vernal_equinox_datetime(year)
    sun = eph["sun"]
    
    # Iterate to find exact vernal equinox (when Sun's declination crosses 0 going north)
    best_t = None
    best_dec = 999.0
    for day_offset in range(-2, 3):  # Check March 18-22
        test_date = vernal_start + timedelta(days=day_offset)
        for hour in range(0, 24, 6):  # Check every 6 hours
            # Create a new datetime with the hour set, preserving timezone
            test_datetime = test_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            # Ensure it's timezone-aware (should already be from vernal_start)
            if test_datetime.tzinfo is None:
                test_datetime = test_datetime.replace(tzinfo=pytz.UTC)
            t_test = ts.from_datetime(test_datetime)
            astrometric_test = (eph["earth"] + observer).at(t_test).observe(sun).apparent()
            ra_test, dec_test, _ = astrometric_test.radec()
            dec_deg = abs(dec_test.degrees)
            if dec_deg < best_dec:
                best_dec = dec_deg
                best_t = t_test
    
    # Compute Sun's ecliptic longitude at vernal equinox
    if best_t is not None:  # Use 'is not None' to avoid Skyfield Time object truthiness issues
        astrometric_vernal = (eph["earth"] + observer).at(best_t).observe(sun).apparent()
        ra_vernal, dec_vernal, _ = astrometric_vernal.radec()
        ra_v_deg = ra_vernal.hours * 15.0
        ra_v_rad = math.radians(ra_v_deg)
        dec_v_rad = math.radians(dec_vernal.degrees)
        obliquity_j2000 = math.radians(23.4392911)
        sin_ra_v = math.sin(ra_v_rad)
        cos_ra_v = math.cos(ra_v_rad)
        tan_dec_v = math.tan(dec_v_rad)
        sin_obl = math.sin(obliquity_j2000)
        cos_obl = math.cos(obliquity_j2000)
        ecl_lon_vernal_rad = math.atan2(sin_ra_v * cos_obl + tan_dec_v * sin_obl, cos_ra_v)
        ecl_lon_vernal_deg = math.degrees(ecl_lon_vernal_rad) % 360.0
        if ecl_lon_vernal_deg < 0:
            ecl_lon_vernal_deg += 360.0
        return ecl_lon_vernal_deg
    
    # Fallback: return 0 if we couldn't find the vernal equinox
    return 0.0

class _QuickLoc:
    """Lightweight stand-in for geopy's Location with address/latitude/longitude."""
    def __init__(self, addr: str, lat: float, lon: float):
        self.address = addr
        self.latitude = lat
        self.longitude = lon

def _parse_dateutil(value_to_parse: str) -> Optional[datetime]:
    """Try parsing with dateutil.parser, with dayfirst fallback for month errors."""
    try:
        return parse(value_to_parse)
    except ValueError as ve:
        # If error is about month > 12, try dayfirst
        if "month must be in 1..12" in str(ve) or "month out of range" in str(ve):
            try:
                return parse(value_to_parse, dayfirst=True)
            except Exception:
                pass
    except Exception:
        pass
    return None


def _parse_ordinal_date(s: str) -> Optional[datetime]:
    """Parse ordinal date format: YYYY-DDD (day-of-year)."""
    m = match(r"^(\d{4})-(\d{3})$", s)
    if m:
        year, day_of_year = int(m.group(1)), int(m.group(2))
        return datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
    return None


def _parse_iso_week_date(s: str) -> Optional[datetime]:
    """Parse ISO week date format: YYYY-Www-d."""
    m = match(r"^(\d{4})-W(\d{2})-(\d)$", s)
    if m:
        return datetime.strptime(s, "%G-W%V-%u")
    return None


def _parse_compact_date(s: str) -> Optional[datetime]:
    """Parse compact date format: YYYYMMDD."""
    m = match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _parse_year_month(s: str) -> Optional[datetime]:
    """Parse year-month format: YYYY-MM."""
    m = match(r"^(\d{4})-(\d{2})$", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), 1)
    return None


def _parse_year_only(s: str) -> Optional[datetime]:
    """Parse year-only format: YYYY."""
    m = match(r"^(\d{4})$", s)
    if m:
        return datetime(int(m.group(1)), 1, 1)
    return None


def _parse_relative_date(s: str) -> Optional[datetime]:
    """Parse relative date strings: today, yesterday, tomorrow."""
    s_lower = s.lower()
    if s_lower == "today":
        return now_utc()
    if s_lower == "yesterday":
        return now_utc() - timedelta(days=1)
    if s_lower == "tomorrow":
        return now_utc() + timedelta(days=1)
    return None


def _parse_unix_timestamp(s: str) -> Optional[datetime]:
    """Parse Unix timestamp (>=10 digits)."""
    if s.isdigit() and len(s) >= 10:
        return datetime.fromtimestamp(int(s), tz=pytz.UTC)
    return None


def _parse_julian_day(s: str) -> Optional[datetime]:
    """Parse Julian Day Number (JD2451545.0 or 2451545.0)."""
    m = match(r"^(?:JD)?(\d{7}\.\d+|\d{7})$", s)
    if m:
        # Julian Day to datetime conversion
        jd = float(m.group(1))
        jd += 0.5
        Z = int(jd)
        F = jd - Z
        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - int(alpha / 4)
        B = A + 1524
        C = int((B - 122.1) / 365.25)
        D = int(365.25 * C)
        E = int((B - D) / 30.6001)
        day = B - D - int(30.6001 * E) + F
        month = E - 1 if E < 14 else E - 13
        year = C - 4716 if month > 2 else C - 4715
        day_int = int(day)
        frac_day = day - day_int
        hour = int(frac_day * 24)
        minute = int((frac_day * 24 - hour) * 60)
        second = int(round((((frac_day * 24 - hour) * 60) - minute) * 60))
        return datetime(year, month, day_int, hour, minute, second)
    return None


def _parse_date_string(value_to_parse: str) -> datetime:
    """Parse a date string using multiple format parsers.
    
    Tries parsers in order:
    1. dateutil.parser (with dayfirst fallback)
    2. Ordinal date (YYYY-DDD)
    3. ISO week date (YYYY-Www-d)
    4. Compact date (YYYYMMDD)
    5. Year-month (YYYY-MM)
    6. Year only (YYYY)
    7. Relative dates (today, yesterday, tomorrow)
    8. Unix timestamp
    9. Julian Day Number
    
    Raises:
        ValueError: If no parser can handle the format
    """
    s = value_to_parse.strip()
    
    # Try dateutil first
    result = _parse_dateutil(s)
    if result:
        return result
    
    # Try specialized formats
    parsers = [
        _parse_ordinal_date,
        _parse_iso_week_date,
        _parse_compact_date,
        _parse_year_month,
        _parse_year_only,
        _parse_relative_date,
        _parse_unix_timestamp,
        _parse_julian_day,
    ]
    
    for parser in parsers:
        result = parser(s)
        if result:
            return result
    
    raise ValueError(f"Unrecognized date format: {value_to_parse}")


class Actual:
    """
    Universal holder for either a place or time object.
    Useful for normalizing user input and controlling shiftable dimensions in astrology.
    """

    def __init__(self, *args, t: str = "time") -> None:
        self.service = None
        self.value = None
        self.tz = None

        if t in {"time", "date"}:
            self._init_time(*args)
        elif t in {"place", "loc"}:
            self._init_place(*args)
        else:
            raise ValueError(f"Unsupported type flag: {t}")

    def _init_time(self, *args) -> None:
        """Initialize time value from various input formats."""
        if not args:
            self.value = now_utc()
        elif isinstance(args[0], (datetime, date, time)):
            self.value = args[0] if isinstance(args[0], datetime) else datetime.combine(date.today(), args[0])
        elif isinstance(args[0], (str, tuple)):
            try:
                # If it's a tuple, extract the first element and convert to string
                value_to_parse = args[0] if isinstance(args[0], str) else str(args[0][0])
                self.value = _parse_date_string(value_to_parse)
            except Exception as e:
                print(f"Failed to parse time: {args[0]} ({e}), fallback to current time")
                self.value = now_utc()
        else:
            self.value = now_utc()

    def _init_place(self, *args) -> None:
        # Support direct coordinates "lat,lon" to avoid any network call
        place_name = args[0] if args and isinstance(args[0], str) else None
        if isinstance(place_name, str):
            s = place_name.strip()
            m = match(r"^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$", s)
            if m:
                lat = float(m.group(1))
                lon = float(m.group(2))
                self.value = _QuickLoc(addr=s, lat=lat, lon=lon)
                self.tz = self._resolve_timezone()
                return
        # Otherwise, use Nominatim with short timeout and cache
        self.service = Nominatim(user_agent="astro-smrk", timeout=1)
        self.value = self._geocode(place_name) if place_name else None
        self.tz = self._resolve_timezone() if self.value else None

    def __str__(self) -> str:
        if isinstance(self.value, GeoLocation):
            return self.value.address
        return str(self.value)

    def add_time(self, delta: Union[int, timedelta, str]) -> None:
        if isinstance(delta, int):
            self.value += timedelta(days=delta)
        elif isinstance(delta, timedelta):
            self.value += delta
        elif isinstance(delta, str):
            self.value += parse(delta)

    def _geocode(self, name: str) -> Optional[GeoLocation]:
        if not name:
            return None
        key = name.strip().lower()
        if key in _GEOCODE_CACHE:
            return _GEOCODE_CACHE[key]
        try:
            result = self.service.geocode(name, language="en")
            _GEOCODE_CACHE[key] = result
            return result
        except GeopyError:
            _GEOCODE_CACHE[key] = None
            return None

    def _resolve_timezone(self) -> str:
        if not self.value:
            return "UTC"
        tf = TimezoneFinder()
        return tf.timezone_at(lat=self.value.latitude, lng=self.value.longitude) or "UTC"

    def assign_timezone(self, tz: Optional[str] = None) -> None:
        self.value = self.value.replace(tzinfo=pytz.timezone(tz or "UTC"))

    def to_model_location(self) -> Optional[Location]:
        if isinstance(self.value, (GeoLocation, _QuickLoc)):
            return Location(
                name=self.value.address,
                latitude=self.value.latitude,
                longitude=self.value.longitude,
                timezone=self.tz or "UTC"
            )
        return None


def prepare_horoscope(
    name: str = "",
    dt: datetime = None,
    loc: Location = None,
    engine: Optional[EngineType] = None,
    ephemeris_path: Optional[str] = None,
    zodiac: ZodiacType = ZodiacType.TROPICAL,
    house: HouseSystem = HouseSystem.PLACIDUS,
) -> ChartInstance:
    """Create a ChartInstance with basic configuration.
    
    Args:
        name: Chart subject name
        dt: Event datetime
        loc: Location for the chart
        engine: Optional computation engine
        ephemeris_path: Optional path to ephemeris file
        zodiac: Zodiac type, defaults to TROPICAL
        house: House system, defaults to PLACIDUS
        
    Returns:
        ChartInstance with configured ChartSubject and ChartConfig
    """
    return ChartInstance(
        id=name,
        subject=ChartSubject(
            id=name, name=name, event_time=dt, location=loc
        ),
        config=ChartConfig(
            mode=ChartMode.NATAL,
            house_system=house,
            zodiac_type=zodiac,
            included_points=[],
            aspect_orbs={'a': 1.5},
            display_style="",
            color_theme="",
            override_ephemeris=ephemeris_path,
            engine=engine,
        )
    )


def parse_sfs_content(content: str) -> Tuple[AstroModel, Dict[str, Any]]:
    """Parse the content of a StarFisher .sfs file and map to AstroModel.
    
    Parses StarFisher script format and extracts body definitions, aspect definitions,
    signs, and model settings into structured dataclasses.
    
    Args:
        content: String content of the .sfs file
        
    Returns:
        Tuple of (AstroModel, display_config_dict) where display_config_dict
        contains display-related settings from the .sfs file
    """
    bodies = []
    aspects = []
    signs = []
    model_settings = {}
    display_config = {}
    current_section = None
    current_obj = None
    obj_props = {}
    def flush_obj():
        nonlocal current_section, current_obj, obj_props
        if current_section == 'Body' and current_obj:
            bodies.append(BodyDefinition(
                id=current_obj,
                glyph=obj_props.get('Glyph', ''),
                formula=obj_props.get('Formula', ''),
                element=obj_props.get('Element'),
                avg_speed=float(obj_props.get('AvgSpeed', '0').replace(":", ".").replace("'", "")) if obj_props.get('AvgSpeed') else 0.0,
                max_orb=float(obj_props.get('MaxOrb', '0').replace(":", ".").replace("'", "")) if obj_props.get('MaxOrb') else 0.0,
                i18n={k: v for k, v in obj_props.items() if k in ('Caption', 'Abbreviation')}
            ))
        elif current_section == 'Aspect' and current_obj:
            aspects.append(AspectDefinition(
                id=current_obj,
                glyph=obj_props.get('Glyph', ''),
                angle=float(obj_props.get('Angle', '0').replace(":", ".").replace("'", "")) if obj_props.get('Angle') else 0.0,
                default_orb=float(obj_props.get('Orb', '0').replace(":", ".").replace("'", "")) if obj_props.get('Orb') else 0.0,
                i18n={k: v for k, v in obj_props.items() if k in ('Caption', 'Abbreviation')}
            ))
        elif current_section == 'Sign' and current_obj:
            signs.append(Sign(
                name=current_obj,
                glyph=obj_props.get('Glyph', ''),
                abbreviation=obj_props.get('Abbreviation', ''),
                element=obj_props.get('Element', ''),
                i18n={k: v for k, v in obj_props.items() if k in ('Caption',)}
            ))
        current_obj = None
        obj_props = {}

    # MAIN PARSING LOOP
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        # Section start
        m = match(r'_settings\.(Body|Aspect|Sign)\.New\((\w+)\);', line)
        if m:
            flush_obj()
            current_section, current_obj = m.group(1), m.group(2)
            obj_props = {}
            continue
        # Property assignment for object
        m = match(r'_settings\.(Body|Aspect|Sign)\.(\w+)\.(\w+) = "?(.*?)"?;', line)
        if m:
            section, obj, prop, value = m.groups()
            if section == current_section and obj == current_obj:
                obj_props[prop] = value
            continue
        # Model/Display/Other assignment
        m = match(r'_settings\.(Model|Display)\.(\w+) = "?(.*?)"?;', line)
        if m:
            section, key, value = m.groups()
            if section == 'Model':
                model_settings[key] = value
            elif section == 'Display':
                display_config[key] = value
            continue
    
    flush_obj()  # Final object
    # Map model_settings to ModelSettings dataclass (partial, extend as needed)
    ms = ModelSettings(
        default_house_system=HouseSystem(model_settings.get('DefaultHouseSystem', 'PLACIDUS')) if 'DefaultHouseSystem' in model_settings else HouseSystem.PLACIDUS,
        default_aspects=[],  # Could parse from model_settings if present
        default_bodies=[],   # Could parse from model_settings if present
        standard_orb=float(model_settings.get('StandardComparisonOrbCoef', 1.0)) if 'StandardComparisonOrbCoef' in model_settings else 1.0
    )
    model = AstroModel(
        name="content",
        body_definitions=bodies,
        aspect_definitions=aspects,
        signs=signs,
        settings=ms
    )
    return model, display_config


# Additional Utility Functions

def to_timezone(dt: datetime, tz_name: str) -> datetime:
    """Convert a timezone-aware datetime to the target timezone by name.
    
    Args:
        dt: Timezone-aware datetime to convert
        tz_name: Target timezone name (e.g., "UTC", "Europe/Prague")
        
    Returns:
        Datetime converted to target timezone
    """
    return dt.astimezone(pytz.timezone(tz_name))

def in_range(dt: datetime, dr: DateRange) -> bool:
    """Check if datetime lies within the inclusive DateRange.
    
    Args:
        dt: Datetime to check
        dr: DateRange with start and end datetimes
        
    Returns:
        True if dt is within [start, end] (inclusive), False otherwise
    """
    return dr.start <= dt <= dr.end

def expand_range(center: datetime, days: int) -> DateRange:
    """Create a DateRange centered on a datetime extending days on both sides.
    
    Args:
        center: Center datetime for the range
        days: Number of days to extend on each side
        
    Returns:
        DateRange from (center - days) to (center + days)
    """
    delta = timedelta(days=days)
    return DateRange(start=center - delta, end=center + delta)

def combine_date_time(input_date: date, input_time: time) -> datetime:
    """Combine a date and time into a naive datetime (no timezone).
    
    Args:
        input_date: Date object
        input_time: Time object
        
    Returns:
        Naive datetime combining date and time
    """
    return datetime.combine(input_date, input_time)

def location_from_coords(lat: float, lon: float, name: str = "") -> Location:
    """Build a Location from raw coordinates, inferring timezone via TimezoneFinder.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        name: Optional location name, defaults to coordinate string
        
    Returns:
        Location instance with inferred timezone
    """
    tf = TimezoneFinder()
    tz = tf.timezone_at(lat=lat, lng=lon) or "UTC"
    return Location(name=name or f"{lat},{lon}", latitude=lat, longitude=lon, timezone=tz)

def location_equals(loc1: Location, loc2: Location) -> bool:
    """Check approximate equality of two Location objects.
    
    Compares coordinates within ~1e-4 degrees and requires same timezone.
    
    Args:
        loc1: First location to compare
        loc2: Second location to compare
        
    Returns:
        True if locations are approximately equal, False otherwise
    """
    return (
        abs(loc1.latitude - loc2.latitude) < 0.0001 and
        abs(loc1.longitude - loc2.longitude) < 0.0001 and
        loc1.timezone == loc2.timezone
    )

def default_ephemeris_path() -> str:
    """Return the default path to the local JPL ephemeris file.
    
    Returns:
        Absolute path to de421.bsp file in source/ directory
    """
    base_dir = Path(__file__).resolve().parent.parent  # .../function-wrapper/module -> .../function-wrapper
    return str(base_dir / 'source' / 'de421.bsp')

def ensure_aware(dt: datetime, tz_name: Optional[str] = None) -> datetime:
    """Return a timezone-aware datetime.
    
    Args:
        dt: Datetime to make timezone-aware
        tz_name: Optional timezone name for localization, defaults to UTC
        
    Returns:
        Timezone-aware datetime. If dt is already aware, returns unchanged.
        If tz_name provided, localizes to that timezone. Otherwise uses UTC.
    """
    if getattr(dt, 'tzinfo', None) is not None and dt.tzinfo is not None:
        return dt
    try:
        if tz_name:
            return pytz.timezone(tz_name).localize(dt)
    except Exception:
        pass
    return pytz.UTC.localize(dt)


def _read_text_with_fallbacks(path: Path, encodings: List[str] | Tuple[str, ...] = ("utf-8", "utf-8-sig", "utf-16", "latin-1", "windows-1250")) -> Optional[str]:
    """Read a text file trying multiple encodings.
    
    Args:
        path: Path to text file
        encodings: List of encodings to try in order
        
    Returns:
        File content as string if successful, None if all encodings fail
    """
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return None


def load_sfs_models_from_dir(dir_path: Union[str, Path]) -> Dict[str, AstroModel]:
    """Scan a directory for StarFisher .sfs files and build AstroModel catalogs.
    
    Args:
        dir_path: Directory path to scan for .sfs files
        
    Returns:
        Dictionary mapping model name (from file stem or parsed model.name) to AstroModel.
        Files that cannot be decoded or parsed are skipped.
    """
    base = Path(dir_path).resolve()
    models: Dict[str, AstroModel] = {}
    if not base.exists() or not base.is_dir():
        return models
    for p in sorted(base.glob("*.sfs")):
        text = _read_text_with_fallbacks(p)
        if not text:
            continue
        try:
            model, display = parse_sfs_content(text)
            # Prefer parsed model name, fallback to file stem
            key = (getattr(model, 'name', None) or p.stem).strip() or p.stem
            models[key] = model
        except Exception:
            continue
    return models




# ─────────────────────
# YAML IMPORT/EXPORT HELPERS
# ─────────────────────

def resolve_under_base(base: Union[str, Path], rel_path: Union[str, Path]) -> Path:
    """Resolve rel_path against base and ensure the result stays within base.
    
    Args:
        base: Base directory path
        rel_path: Relative path to resolve
        
    Returns:
        Resolved Path that is contained within base
        
    Raises:
        ValueError: If path is absolute or attempts directory traversal outside base
    """
    base_p = Path(base).resolve()
    rel_p = Path(rel_path)
    if rel_p.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {rel_path}")
    full = (base_p / rel_p).resolve()
    try:
        full.relative_to(base_p)
    except Exception:
        raise ValueError(f"Path traversal detected: {rel_path}")
    return full

def read_yaml_file(path: Union[str, Path]) -> dict:
    """Read a YAML file and return a dict.
    
    Args:
        path: Path to YAML file
        
    Returns:
        Parsed YAML content as dictionary, or empty dict if file is empty
        
    Note:
        This is a thin wrapper around yaml.safe_load that always returns a dict.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def write_yaml_file(path: Union[str, Path], data: dict, *, sort_keys: bool = False, allow_unicode: bool = True) -> None:
    """Write a dict to a YAML file using yaml.safe_dump.
    
    Args:
        path: Destination file path
        data: Dictionary to write
        sort_keys: Whether to sort keys in output, defaults to False
        allow_unicode: Whether to allow unicode characters, defaults to True
        
    Note:
        Ensures parent directory exists. Callers should pass already-serialized
        primitives (e.g., via a to_primitive function) if the input data contains
        dataclasses, enums, or datetime objects.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=sort_keys, allow_unicode=allow_unicode)

def _to_primitive(obj: Any) -> Any:
    """Recursively convert dataclasses, Enums, and datetimes to YAML-serializable primitives.
    
    Args:
        obj: Object to convert (can be dataclass, Enum, datetime, dict, list, etc.)
        
    Returns:
        Primitive representation suitable for YAML/JSON serialization
    """
    if is_dataclass(obj):
        obj = asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_primitive(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_primitive(v) for v in obj]
    return obj

def parse_chart_yaml(data: dict) -> ChartInstance:
    """Construct a ChartInstance from a YAML-mapped dict with safe coercions.
    
    Args:
        data: Dictionary containing chart data (subject, config, id, tags)
        
    Returns:
        ChartInstance with parsed subject and config
        
    Raises:
        ValueError: If subject data is invalid
        
    Note:
        Removes 'computed_chart' if present (it's recomputable and shouldn't be loaded from YAML)
    """
    # Ignore computed_chart on load if present (recomputable)
    data.pop("computed_chart", None)
    
    # Subject
    subj_d = data.get('subject') or {}
    if not isinstance(subj_d, dict):
        raise ValueError('Invalid subject in chart YAML')
    name = subj_d.get('name') or data.get('id') or 'chart'
    # event_time
    et = subj_d.get('event_time')
    if isinstance(et, str):
        try:
            et = parse(et)
        except Exception:
            et = now_utc()
    elif not isinstance(et, (datetime, date, time)):
        et = now_utc()
    # location
    loc_d = subj_d.get('location') or {}
    if isinstance(loc_d, dict):
        loc = Location(
            name=loc_d.get('name') or '',
            latitude=float(loc_d.get('latitude') or 0.0),
            longitude=float(loc_d.get('longitude') or 0.0),
            timezone=loc_d.get('timezone') or 'UTC',
        )
    else:
        # allow free-text location; geocode to model
        loc = Actual(str(loc_d or ''), t='loc').to_model_location()

    subject = ChartSubject(
        id=subj_d.get('id') or name,
        name=name,
        event_time=et if isinstance(et, datetime) else datetime.combine(et, time.min),
        location=loc,
    )

    # Config
    cfg_d = data.get('config') or {}
    # enums with graceful fallback
    def _enum_or(val, enum_cls, default):
        if val is None:
            return default
        try:
            # allow direct value (e.g., "jpl")
            return enum_cls(val)
        except Exception:
            try:
                # allow by name (e.g., "PLACIDUS")
                return getattr(enum_cls, str(val).upper(), default)
            except Exception:
                return default

    cfg = ChartConfig(
        mode=_enum_or(cfg_d.get('mode', 'NATAL'), ChartMode, ChartMode.NATAL),
        house_system=_enum_or(cfg_d.get('house_system', 'PLACIDUS'), HouseSystem, HouseSystem.PLACIDUS),
        zodiac_type=_enum_or(cfg_d.get('zodiac_type', 'TROPICAL'), ZodiacType, ZodiacType.TROPICAL),
        included_points=list(cfg_d.get('included_points', []) or []),
        aspect_orbs=dict(cfg_d.get('aspect_orbs', {}) or {}),
        display_style=str(cfg_d.get('display_style', '') or ''),
        color_theme=str(cfg_d.get('color_theme', '') or ''),
        override_ephemeris=cfg_d.get('override_ephemeris'),
        model=cfg_d.get('model'),
        engine=_enum_or(cfg_d.get('engine'), EngineType, None),
        ayanamsa=_enum_or(cfg_d.get('ayanamsa'), Ayanamsa, None),
    )

    cid = data.get('id') or subject.id or name
    tags = [t for t in (data.get('tags') or []) if t]
    return ChartInstance(id=cid, subject=subject, config=cfg, tags=tags)

def import_chart_yaml(path: str) -> ChartInstance:
    """Read a chart YAML file from disk and parse into a ChartInstance.
    
    Args:
        path: Path to chart YAML file
        
    Returns:
        ChartInstance parsed from YAML file
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    return parse_chart_yaml(data)

def export_chart_yaml(chart: ChartInstance, dest_dir: str) -> str:
    """Export a ChartInstance as YAML into dest_dir.
    
    Args:
        chart: ChartInstance to export
        dest_dir: Destination directory for YAML file
        
    Returns:
        Absolute file path to exported YAML file
    """
    base = Path(dest_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    fname = f"{(getattr(chart, 'id', '') or 'chart').replace(' ', '-').lower()}.yml"
    out = base / fname
    data = _to_primitive(chart)
    with open(out, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return str(out)

def write_json_file(path: Union[str, Path], data: dict, *, indent: int = 2) -> None:
    """Write a dict to a JSON file.
    
    Args:
        path: Destination file path
        data: JSON-serializable data
        indent: Indentation level, defaults to 2
        
    Note:
        Ensures parent directory exists before writing.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)

def parse_yaml_content(data: Union[str, bytes]) -> dict:
    """Parse YAML from a string or bytes and return a dict.
    
    Args:
        data: YAML content as string or bytes
        
    Returns:
        Parsed YAML as dictionary, or empty dict if empty/invalid
        
    Note:
        Useful for handling uploaded files or in-memory YAML content uniformly.
    """
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except Exception:
            text = data.decode("utf-8", errors="ignore")
    else:
        text = data
    try:
        return yaml.safe_load(text) or {}
    except Exception:
        return {}

def export_workspace_yaml(ws: Workspace, dest_path: Union[str, Path]) -> Path:
    """Export a Workspace as YAML to dest_path.
    
    Args:
        ws: Workspace instance to export
        dest_path: Destination file path
        
    Returns:
        Resolved Path to exported YAML file
        
    Note:
        Uses the local serializer to convert dataclasses, enums, and datetimes
        to primitives. Ensures parent directory exists.
    """
    p = Path(dest_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    # Reuse local primitive conversion
    data = _to_primitive(ws)
    write_yaml_file(p, data, sort_keys=False, allow_unicode=True)
    return p

# Note: Workspace-related functions (validate_workspace, build_workspace_from_sfs, etc.)
# have been moved to workspace.py for better module organization

def _safe_get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object or dict.
    
    Handles both object attributes and dictionary keys, with graceful error handling.
    
    Args:
        obj: Object or dict to get attribute from
        attr: Attribute name or key
        default: Default value if attribute/key not found
        
    Returns:
        Attribute value or default
    """
    if obj is None:
        return default
    try:
        if hasattr(obj, attr):
            return getattr(obj, attr)
        if isinstance(obj, dict):
            return obj.get(attr, default)
    except Exception:
        pass
    return default



if __name__ == "__main__":
    # simple test
    if 1 == 1:
        # this module is responsible for displaying dates and places properly
        #print(Actual())  # default fallback - current date and time
        print(Actual("1700000000"))
        print(Actual("15.5.2020"))
        print(Actual("11/9/1982 11:59"))
        print(Actual("2023-348"))  # Gregorian date
        print(Actual(t="place"))  # default fallback for location
        print(Actual("Prague", t="place"))
        print(Actual("Praha", t="place"))  # supports multiple languages
        print(Actual("Kdesicosi", t="place"))  # should be none
        print("*"*50)
    else:
        # Test parse_sfs_content with encoding detection
        sfs_path = "/home/jav/Documents/Space/Kefer Astrology/function-wrapper/init.sfs"
        encodings = ["utf-8-sig", "utf-16", "latin-1", "windows-1250"]
        sfs_content = None
        for enc in encodings:
            try:
                with open(sfs_path, encoding=enc) as f:
                    sfs_content = f.read()
                break
            except Exception:
                continue
        if sfs_content is None:
            print(f"Could not decode {sfs_path} with utf-8, utf-16, windows-1250, or latin-1.")
        else:
            model, display = parse_sfs_content(sfs_content)
            print(f"AstroModel: {model}")
            print(f"Display config: {display}")