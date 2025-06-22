# utils.py

from datetime import datetime, date, time, timedelta, UTC
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from geopy.location import Location as GeoLocation
from geopy.exc import GeopyError
import pytz
from timezonefinder import TimezoneFinder
from typing import Optional, Union

import re
from models import (
    AspectDefinition, AstroModel, BodyDefinition, DateRange, HouseSystem, ChartConfig, ChartInstance, ChartSubject, 
    Location, ModelSettings, Sign
)

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
            self.value = datetime.now()
        elif isinstance(args[0], (datetime, date, time)):
            self.value = args[0] if isinstance(args[0], datetime) else datetime.combine(date.today(), args[0])
        elif isinstance(args[0], str):
            self.value = parse(args[0])
        elif isinstance(args[0], tuple):
            self.value = parse(str(args[0][0]))
        else:
            self.value = datetime.now()

    def _init_place(self, *args) -> None:
        self.service = Nominatim(user_agent="astro")
        place_name = args[0] if args and isinstance(args[0], str) else "Prague"
        self.value = self._geocode(place_name)
        self.tz = self._resolve_timezone()

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
        try:
            return self.service.geocode(name, language="en")
        except GeopyError:
            return self.service.geocode("Prague", language="en")

    def _resolve_timezone(self) -> str:
        if not self.value:
            return "UTC"
        tf = TimezoneFinder()
        return tf.timezone_at(lat=self.value.latitude, lng=self.value.longitude) or "UTC"

    def assign_timezone(self, tz: Optional[str] = None) -> None:
        self.value = self.value.replace(tzinfo=pytz.timezone(tz or "UTC"))

    def to_model_location(self) -> Optional[Location]:
        if isinstance(self.value, GeoLocation):
            return Location(
                name=self.value.address,
                latitude=self.value.latitude,
                longitude=self.value.longitude,
                timezone=self.tz or "UTC"
            )
        return None


def prepare_horoscope(name: str='', dt: datetime=None, loc: Location=None) -> ChartInstance:
    return ChartInstance(
        id=name,
        subject=ChartSubject(
            id=name, name=name, event_time=dt, location=loc
        ),
        config=ChartConfig(
            mode="NATAL", house_system="PLACIDUS", zodiac_type="Tropical",
            included_points=[], aspect_orbs={'a':1.5}, display_style="",
            color_theme=''
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
        m = re.match(r'_settings\.(Body|Aspect|Sign)\.New\((\w+)\);', line)
        if m:
            flush_obj()
            current_section, current_obj = m.group(1), m.group(2)
            obj_props = {}
            continue
        # Property assignment for object
        m = re.match(r'_settings\.(Body|Aspect|Sign)\.(\w+)\.(\w+) = "?(.*?)"?;', line)
        if m:
            section, obj, prop, value = m.groups()
            if section == current_section and obj == current_obj:
                obj_props[prop] = value
            continue
        # Model/Display/Other assignment
        m = re.match(r'_settings\.(Model|Display)\.(\w+) = "?(.*?)"?;', line)
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
    return datetime.now(UTC).replace(tzinfo=pytz.utc)

def to_timezone(dt: datetime, tz_name: str) -> datetime:
    return dt.astimezone(pytz.timezone(tz_name))

def in_range(dt: datetime, dr: DateRange) -> bool:
    return dr.start <= dt <= dr.end

def expand_range(center: datetime, days: int) -> DateRange:
    delta = timedelta(days=days)
    return DateRange(start=center - delta, end=center + delta)

def combine_date_time(input_date, input_time) -> datetime:
    return datetime.combine(input_date, input_time)

def location_from_coords(lat: float, lon: float, name: str = "") -> Location:
    tf = TimezoneFinder()
    tz = tf.timezone_at(lat=lat, lng=lon) or "UTC"
    return Location(name=name or f"{lat},{lon}", latitude=lat, longitude=lon, timezone=tz)

def location_equals(loc1: Location, loc2: Location) -> bool:
    return (
        abs(loc1.latitude - loc2.latitude) < 0.0001 and
        abs(loc1.longitude - loc2.longitude) < 0.0001 and
        loc1.timezone == loc2.timezone
    )

if __name__ == "__main__":
    # simple test
    if 1 == 2:
        # this module is responsible for displaying dates and places properly
        print(Actual())  # default fallback - current date and time
        print(Actual("15.5.2020"))
        print(Actual("11/9/1982 11:59"))
        print(Actual(t="place"))  # default fallback for location
        print(Actual("Prague", t="place"))
        print(Actual("Praha", t="place"))  # supports multiple languages
        print(Actual("Kdesicosi", t="place"))  # also for unknown ones
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