from datetime import datetime, time, date, timedelta
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from geopy.location import Location
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
            else:
                print("Defaulting to current time stamp")
                self.value = datetime.now()
        elif t in {"place", "loc"}:
            self.service = Nominatim(user_agent="astro")
            self.value = self.move_around_globe(kwargs)
            self.tz = self.what_time_zone()
        else:
            print(f"Unknown format of a context detected: {t}")

    def __str__(self):
        if isinstance(self.value, Location):
            return self.value.address
        else:
            return str(self.value)

    def add_some_time(self, of):
        if isinstance(of, int):
            self.value += timedelta(days=of)
        elif isinstance(of, str):
            self.value += parse(of)
        elif isinstance(of, (datetime, date, time)):
            self.value = datetime.combine(self.value, of)

    def move_around_globe(self, city: str):
        if not city:  # Default Fallback
            return self.service.geocode("Prague", language="en")
        elif isinstance(city, str):
            x = self.service.geocode(city, language="en")
            return self.service.geocode("Prague", language="en") if not x else x
        else:
            print(f"What? {city}")
            return None

    def what_time_zone(self) -> None:
        if not self.value:
            return "Europe/Prague"
        tf = TimezoneFinder()
        return tf.timezone_at(lng=self.value.longitude, lat=self.value.latitude)

    def assign_time_zone(self, tz=None):
        # UTC by default, TODO: sanity check
        if not tz:
            self.value = self.value.replace(tzinfo=pytz.UTC)
        else:
            self.value = self.value.replace(tzinfo=tz)


def combine_date_time(input_date, input_time):
    return datetime.combine(input_date, input_time)


def now():
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
