from datetime import datetime
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from geopy.location import Location
from timezonefinder import TimezoneFinder


class Actual:
    # Universal holder for time & position
    # TODO: handle various data formats (d/m/y, y/m/d, ...)
    def __init__(self, content: str = "", t: str = "time") -> None:
        if t == "time" or t == "date":
            self.service = None
            if isinstance(content, str) and len(content) > 0:
                self.value = parse(content)
            elif isinstance(content, datetime):
                self.value = content
            else:
                self.value = datetime.now()
        elif t == "place" or t == "loc":
            self.service = Nominatim(user_agent="astro")
            self.value = self.move_around_globe(content)
            self.tz = self.what_time_zone()
        else:
            print(f"Unknown format of a context detected: {t}")

    def __str__(self):
        if isinstance(self.value, Location):
            return self.value.address
        else:
            return str(self.value)

    def add_some_time(self, of):
        if isinstance(of, str):
            self.value += parse(of)
        elif isinstance(of, datetime):
            self.value = datetime.combine(self.value, of)

    def move_around_globe(self, city: str):
        if not city:  # Default Fallback
            return self.service.geocode("Prague", language="en")
        elif isinstance(city, str):
            x = self.service.geocode(city, language="en")
            if not x:
                return self.service.geocode("Prague", language="en")
            else:
                return x
        else:
            print(f"What? {city}")
            return None

    def what_time_zone(self) -> None:
        if not self.value:
            return "Europe/Prague"
        else:
            tf = TimezoneFinder()
            return tf.timezone_at(lng=self.value.longitude, lat=self.value.latitude)


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
