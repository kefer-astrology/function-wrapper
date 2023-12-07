from context import Actual
# from datetime import datetime
# from dateutil.parser import parse
from kerykeion import AstrologicalSubject, KerykeionChartSVG, Report


class Relation:
    def __init__(self, person1: object, person2: object) -> None:
        # Set the type, it can be Natal, Synastry or Transit
        type = "Synastry"
        complex = KerykeionChartSVG(person1, chart_type=type, second_obj=person2)
        complex.makeSVG()


class Subject:
    def __init__(self, name: str) -> None:
        self.computed = None
        self.name = name
        self.place = None
        self.time = None

    def at_place(self, location: str) -> None:
        self.place = Actual(location, t="loc")

    def at_time(self, time: str) -> None:
        self.time = Actual(time, t="date")
        self.computed = AstrologicalSubject(
            self.name,
            self.time.value.year,
            self.time.value.month,
            self.time.value.day,
            self.time.value.hour,
            self.time.value.minute,
            lng=self.place.value.longitude if self.place.value else "",
            lat=self.place.value.latitude if self.place.value else "",
            tz_str=self.place.tz if self.place.value else "",
            city=self.place.value.address if self.place.value else "",
            nation="GB",
        )

    def data(self):
        object_list = [x["name"] for x in self.computed.planets_list]
        label_list = [x["emoji"] for x in self.computed.planets_list]
        return object_list, self.computed.planets_degrees_ut, label_list

    def report(self):
        return Report(self.computed)
