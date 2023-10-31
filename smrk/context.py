from datetime import datetime
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from geopy.location import Location


class Actual:
    # Universal holder for time & position
    def __init__(self, content: str = "", t: str = "time") -> None:
        if t == "time":
            self.service = None
            if isinstance(content, str) and len(content) > 0:
                self.value = parse(content)
            elif isinstance(content, datetime):
                self.value = content
            else:
                self.value = datetime.now()
        elif t == "place":
            self.service = Nominatim(user_agent="astro")
            if isinstance(content, str):
                self.move_around_globe(content)

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

    def move_around_globe(self, city: str = "Prague"):
        if isinstance(city, str):
            self.value = self.service.geocode(city)


if __name__ == "__main__":
    # simple test
    print(Actual("15.5.2020"))

    print(Actual("11/9/1982"))

    print(Actual("Prague", t="place"))
