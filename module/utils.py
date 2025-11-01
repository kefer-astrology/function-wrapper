# utils.py

from datetime import datetime, date, time, timedelta
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from geopy.location import Location as GeoLocation
from geopy.exc import GeopyError
import pytz
from re import match
from timezonefinder import TimezoneFinder
from typing import Optional, Union
from pathlib import Path
import yaml

try:
    # For running as part of the package (e.g. from root or in tests)
    from module.models import (
        AspectDefinition, AstroModel, BodyDefinition, DateRange, HouseSystem, ChartConfig, ChartInstance, ChartSubject,
        Location, ModelSettings, Sign, ChartMode, EngineType, ZodiacType, Ayanamsa
    )
except ImportError:
    # For running directly (e.g. python3 module/utils.py)
    from models import (
        AspectDefinition, AstroModel, BodyDefinition, DateRange, HouseSystem, ChartConfig, ChartInstance, ChartSubject,
        Location, ModelSettings, Sign, ChartMode, EngineType, ZodiacType, Ayanamsa
    )

# simple in-process cache to avoid repeated geocoding of same string
_GEOCODE_CACHE: dict[str, Optional[GeoLocation]] = {}

class _QuickLoc:
    """Lightweight stand-in for geopy's Location with address/latitude/longitude."""
    def __init__(self, addr: str, lat: float, lon: float):
        self.address = addr
        self.latitude = lat
        self.longitude = lon

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
        if not args:
            self.value = datetime.now(pytz.UTC)
        elif isinstance(args[0], (datetime, date, time)):
            self.value = args[0] if isinstance(args[0], datetime) else datetime.combine(date.today(), args[0])
        elif isinstance(args[0], (str, tuple)):
            try:
                # If it's a tuple, extract the first element and convert to string
                value_to_parse = args[0] if isinstance(args[0], str) else str(args[0][0])
                # Try dateutil.parser first (default, then dayfirst)
                try:
                    self.value = parse(value_to_parse)
                    return
                except ValueError as ve:
                    # If error is about month > 12, try dayfirst
                    if "month must be in 1..12" in str(ve) or "month out of range" in str(ve):
                        try:
                            self.value = parse(value_to_parse, dayfirst=True)
                            return
                        except Exception:
                            pass
                    else:
                        pass
                except Exception:
                    pass
                s = value_to_parse.strip()
                # Ordinal date: YYYY-DDD (day-of-year)
                m = match(r"^(\d{4})-(\d{3})$", s)
                if m:
                    year, day_of_year = int(m.group(1)), int(m.group(2))
                    self.value = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
                    return
                # ISO week date: YYYY-Www-d
                m = match(r"^(\d{4})-W(\d{2})-(\d)$", s)
                if m:
                    self.value = datetime.strptime(s, "%G-W%V-%u")
                    return
                # Compact date: YYYYMMDD
                m = match(r"^(\d{4})(\d{2})(\d{2})$", s)
                if m:
                    self.value = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    return
                # Year and month only: YYYY-MM
                m = match(r"^(\d{4})-(\d{2})$", s)
                if m:
                    self.value = datetime(int(m.group(1)), int(m.group(2)), 1)
                    return
                # Year only: YYYY
                m = match(r"^(\d{4})$", s)
                if m:
                    self.value = datetime(int(m.group(1)), 1, 1)
                    return
                # Relative dates
                if s.lower() == "today":
                    self.value = datetime.now(pytz.UTC)
                    return
                if s.lower() == "yesterday":
                    self.value = datetime.now(pytz.UTC) - timedelta(days=1)
                    return
                if s.lower() == "tomorrow":
                    self.value = datetime.now(pytz.UTC) + timedelta(days=1)
                    return
                # Unix timestamp (>=10 digits)
                if s.isdigit() and len(s) >= 10:
                    self.value = datetime.fromtimestamp(int(s), tz=pytz.UTC)
                    return
                # Julian Day Number (JD2451545.0 or 2451545.0)
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
                    self.value = datetime(year, month, day_int, hour, minute, second)
                    return
                # Fallback: raise error
                raise ValueError(f"Unrecognized date format: {value_to_parse}")
            except Exception as e:
                print(f"Failed to parse time: {args[0]} ({e}), fallback to current time")
                self.value = datetime.now(pytz.UTC)
        else:
            self.value = datetime.now(pytz.UTC)

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


def parse_sfs_content(content):
    """
    Parse the content of a StarFisher .sfs file and map its sections to AstroModel, using BodyDefinition, AspectDefinition, Sign, ModelSettings, etc.
    Returns (AstroModel, display_config_dict)
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

def now_utc() -> datetime:
    """Return current time as a timezone-aware UTC datetime."""
    return datetime.utcnow().replace(tzinfo=pytz.utc)

def to_timezone(dt: datetime, tz_name: str) -> datetime:
    """Convert a timezone-aware datetime to the target timezone by name."""
    return dt.astimezone(pytz.timezone(tz_name))

def in_range(dt: datetime, dr: DateRange) -> bool:
    """Return True if dt lies within the inclusive DateRange [start, end]."""
    return dr.start <= dt <= dr.end

def expand_range(center: datetime, days: int) -> DateRange:
    """Create a DateRange centered on `center` extending `days` on both sides."""
    delta = timedelta(days=days)
    return DateRange(start=center - delta, end=center + delta)

def combine_date_time(input_date, input_time) -> datetime:
    """Combine a date and time into a naive datetime (no timezone)."""
    return datetime.combine(input_date, input_time)

def location_from_coords(lat: float, lon: float, name: str = "") -> Location:
    """Build a Location from raw coordinates, inferring timezone via TimezoneFinder."""
    tf = TimezoneFinder()
    tz = tf.timezone_at(lat=lat, lng=lon) or "UTC"
    return Location(name=name or f"{lat},{lon}", latitude=lat, longitude=lon, timezone=tz)

def location_equals(loc1: Location, loc2: Location) -> bool:
    """Approximate equality check for two Location objects (coords ~1e-4, same tz)."""
    return (
        abs(loc1.latitude - loc2.latitude) < 0.0001 and
        abs(loc1.longitude - loc2.longitude) < 0.0001 and
        loc1.timezone == loc2.timezone
    )

def default_ephemeris_path() -> str:
    """Return the default path to the local JPL ephemeris file (de421.bsp) under source/."""
    base_dir = Path(__file__).resolve().parent.parent  # .../function-wrapper/module -> .../function-wrapper
    return str(base_dir / 'source' / 'de421.bsp')

def ensure_aware(dt: datetime, tz_name: Optional[str] = None) -> datetime:
    """Return a timezone-aware datetime.
    - If dt is already aware, return it unchanged.
    - If tz_name is provided, localize to that timezone (pytz style).
    - Otherwise, assume UTC.
    """
    if getattr(dt, 'tzinfo', None) is not None and dt.tzinfo is not None:
        return dt
    try:
        if tz_name:
            return pytz.timezone(tz_name).localize(dt)
    except Exception:
        pass
    return pytz.UTC.localize(dt)


# ─────────────────────
# YAML IMPORT/EXPORT HELPERS
# ─────────────────────

def resolve_under_base(base: Union[str, Path], rel_path: Union[str, Path]) -> Path:
    """Resolve rel_path against base and ensure the result stays within base.

    Disallows absolute paths and prevents directory traversal outside of base.
    Returns the resolved Path on success.
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
    """Read a YAML file and return a dict (or empty dict if file is empty).

    This is a thin wrapper around yaml.safe_load that always returns a dict.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def write_yaml_file(path: Union[str, Path], data: dict, *, sort_keys: bool = False, allow_unicode: bool = True) -> None:
    """Write a dict to a YAML file using yaml.safe_dump. Ensures parent directory exists.

    Callers should pass already-serialized primitives (e.g., via a to_primitive function)
    if the input data contains dataclasses, enums, or datetime objects.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=sort_keys, allow_unicode=allow_unicode)

def _to_primitive_local(obj):
    """Recursively convert dataclasses, Enums, and datetimes to YAML-serializable primitives."""
    from dataclasses import asdict, is_dataclass
    from enum import Enum
    if is_dataclass(obj):
        obj = asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_primitive_local(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [ _to_primitive_local(v) for v in obj ]
    return obj

def parse_chart_yaml(data: dict) -> ChartInstance:
    """Construct a ChartInstance from a YAML-mapped dict with safe coercions."""
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
            et = datetime.utcnow().replace(tzinfo=pytz.UTC)
    elif not isinstance(et, (datetime, date, time)):
        et = datetime.utcnow().replace(tzinfo=pytz.UTC)
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
    """Read a chart YAML file from disk and parse into a ChartInstance."""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    return parse_chart_yaml(data)

def export_chart_yaml(chart: ChartInstance, dest_dir: str) -> str:
    """Export a ChartInstance as YAML into dest_dir; return absolute file path."""
    base = Path(dest_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    fname = f"{(getattr(chart, 'id', '') or 'chart').replace(' ', '-').lower()}.yml"
    out = base / fname
    data = _to_primitive_local(chart)
    with open(out, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return str(out)

def write_json_file(path: Union[str, Path], data: dict, *, indent: int = 2) -> None:
    """Write a dict to a JSON file. Ensures parent directory exists.

    Parameters:
    - path: destination file path
    - data: JSON-serializable data
    - indent: indentation level (default 2)
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)

def parse_yaml_content(data: Union[str, bytes]) -> dict:
    """Parse YAML from a string or bytes and return a dict (empty dict if empty).

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