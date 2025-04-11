# utils.py

from datetime import datetime, date, time, timedelta, UTC
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from geopy.location import Location as GeoLocation
from geopy.exc import GeopyError
import pytz
from timezonefinder import TimezoneFinder
from typing import Optional, Union
from models import Location, DateRange


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
    # this module is responsible for displaying dates and places properly
    print(Actual())  # default fallback - current date and time
    print(Actual("15.5.2020"))
    print(Actual("11/9/1982 11:59"))
    print(Actual(t="place"))  # default fallback for location
    print(Actual("Prague", t="place"))
    print(Actual("Praha", t="place"))  # supports multiple languages
    print(Actual("Kdesicosi", t="place"))  # also for unknown ones
