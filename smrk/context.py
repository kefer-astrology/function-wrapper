from datetime import datetime, time, date, timedelta
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from geopy.location import Location
from geopy.exc import GeopyError
import pytz
from timezonefinder import TimezoneFinder


class Actual:
    # Universal holder for time & position
    # TODO: 1/ handle various data formats (d/m/y, y/m/d, ...)
    # TODO: 2/ adjust for multiple items passed (kwargs)
    def __init__(self, *kwargs, t: str = "time") -> None:
        if t in {"time", "date"}:
            self.service = None
            if isinstance(kwargs, str) and kwargs:
                self.value = parse(kwargs)
            elif isinstance(kwargs, (datetime, date, time)):
                self.value = kwargs
            elif isinstance(kwargs, tuple):
                if len(kwargs) < 2:
                    self.value = parse(str(kwargs[0]))
                else:
                    self.value = parse(str(kwargs[0]))
            else:
                print("Defaulting to current time stamp")
                self.value = datetime.now()
        elif t in {"place", "loc"}:
            self.service = Nominatim(user_agent="astro")
            self.value = self.move_around_globe(*kwargs)
            self.tz = self.what_time_zone()
        else:
            print(f"Unknown format of a context detected: {t}")

    def __str__(self) -> str:
        if isinstance(self.value, Location):
            return self.value.address
        else:
            return str(self.value)

    def add_some_time(self, of) -> None:
        if isinstance(of, int):
            self.value += timedelta(days=of)
        elif isinstance(of, str):
            self.value += parse(of)
        elif isinstance(of, (datetime, date, time)):
            self.value = datetime.combine(self.value, of)

    def move_around_globe(self, place_name: str):
        if not place_name:  # Default Fallback
            return self.service.geocode("Prague", language="en")
        elif isinstance(place_name, str):
            try:
                x = self.service.geocode(place_name, language="en")
            except GeopyError:
                x = self.service.geocode("Prague", language="en")
            finally:
                return x
        else:
            print(f"What? {place_name}, case for lat/lng movement?")
            return None

    def what_time_zone(self) -> str:
        tf = TimezoneFinder()
        if not self.value:
            return "Europe/Prague"  # tf.timezone_at(lat=50, lng=14.5)
        else:
            return tf.timezone_at(lat=self.value.latitude, lng=self.value.longitude)

    def assign_time_zone(self, tz=None) -> None:
        # UTC by default, TODO: sanity check
        if not tz:
            self.value = self.value.replace(tzinfo=pytz.UTC)
        else:
            self.value = self.value.replace(tzinfo=tz)


def combine_date_time(input_date, input_time) -> datetime:
    return datetime.combine(input_date, input_time)


def now() -> datetime:
    return datetime.now()


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
