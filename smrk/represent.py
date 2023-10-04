from datetime import datetime
from dateutil.parser import parse
from kerykeion import AstrologicalSubject, KerykeionChartSVG, Report


class Relation:
    def __init__(self, person1: object, person2: object) -> None:
        # Set the type, it can be Natal, Synastry or Transit
        type = "Synastry"
        complex = KerykeionChartSVG(person1, chart_type=type, second_obj=person2)
        complex.makeSVG()


class Subject:
    def __init__(self, name: str) -> None:
        self.name = name
        self.place = None
        self.time = None

    def at_place(self, location: str) -> None:
        if isinstance(location, str):
            self.place = location
        else:
            self.place = str(location)

    def at_time(self, time: str) -> None:
        if isinstance(time, str) and len(time) > 0:
            self.time = parse(time)
        elif isinstance(time, datetime):
            self.time = time
        else:
            self.time = datetime.now()
        self.computed = AstrologicalSubject(
            self.name,
            self.time.year,
            self.time.month,
            self.time.day,
            self.time.hour,
            self.time.minute,
            self.place,
        )

    def data(self):
        object_list = [x["name"] for x in self.computed.planets_list]
        label_list = [x["emoji"] for x in self.computed.planets_list]
        return object_list, self.computed.planets_degrees_ut, label_list

    def report(self):
        Report(self.computed).print_report()
