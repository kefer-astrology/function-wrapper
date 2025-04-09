from models import (
    Location, DateRange, CelestialBody, Aspect, AstroModel,
    ChartConfig, ModelOverrides, BodyDefinition, AspectDefinition, Sign
)
from kerykeion import AstrologicalSubject, KerykeionChartSVG, Report, KerykeionPointModel
from pandas import DataFrame
from typing import Dict, List, Optional
from utils import Actual
try:
    from skyfield.api import load, Topos
    JPL = True
except ImportError:
    JPL = False
    print("NASA JPL Ephemeris deactivated")


# ─────────────────────
# 🪐 POSITION CALCULATIONS (Skyfield-based for JPL)
# ─────────────────────

def compute_jpl_positions(name: str, dt_str: str, loc_str: str) -> Dict[str, float]:
    if JPL:
        ts = load.timescale()
        time = Actual(dt_str, t="date")
        place = Actual(loc_str, t="loc")

        t = ts.from_datetime(time.value)
        eph = load("de421.bsp")
        observer = Topos(latitude_degrees=place.value.latitude, longitude_degrees=place.value.longitude)

        planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]
        positions = {}

        for planet in planets:
            body = eph[planet]
            astrometric = (eph["earth"] + observer).at(t).observe(body).apparent()
            lon, lat, distance = astrometric.ecliptic_latlon()
            positions[planet] = lon.degrees

        return positions
    else:
        return "JPL Ephemeris not implemented yet"


# ─────────────────────
# 🪐 POSITION CALCULATIONS (Kerykeion-based)
# ─────────────────────
# TO-DO: decide between class and a method

class Subject:
    def __init__(self, s_name: str, s_type: str = "Tropic") -> None:
        self.computed = None
        self.name = s_name
        self.place = None
        self.time = None
        self.type = s_type

    def at_place(self, location: object) -> None:
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
            zodiac_type=self.type,
            nation="GB",
        )

    def data(self):
        object_list = [x["name"] for x in self.computed.planets_list]
        label_list = [x["emoji"] for x in self.computed.planets_list]
        return object_list, self.computed.planets_degrees_ut, label_list

    def report(self):
        return Report(self.computed)


def compute_subject(name: str, dt_str: str, loc_str: str, zodiac: str = "Tropic") -> AstrologicalSubject:
    time = Actual(dt_str, t="date")
    place = Actual(loc_str, t="loc")
    return AstrologicalSubject(
        name,
        time.value.year,
        time.value.month,
        time.value.day,
        time.value.hour,
        time.value.minute,
        lng=place.value.longitude if place.value else 0.0,
        lat=place.value.latitude if place.value else 0.0,
        tz_str=place.tz if place.value else "UTC",
        city=place.value.address if place.value else "",
        zodiac_type=zodiac,
        nation="GB"
    )

def extract_kerykeion_points(obj) -> DataFrame:
    data = []
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        if isinstance(attr, KerykeionPointModel):
            data.append(attr.__dict__)
    return DataFrame(data)


# ─────────────────────
# 🔁 COMPOSITE / RELATION CHART
# ─────────────────────

def create_relation_svg(subject1: AstrologicalSubject, subject2: AstrologicalSubject, chart_type: str = "Synastry") -> KerykeionChartSVG:
    chart = KerykeionChartSVG(subject1, chart_type=chart_type, second_obj=subject2)
    chart.makeSVG()
    return chart


# ─────────────────────
# 🔺 ASPECT DETECTION
# ─────────────────────

def compute_aspects(bodies: List[CelestialBody], aspect_defs: List[AspectDefinition]) -> List[Aspect]:
    return []  # To be implemented


# ─────────────────────
# 🧬 MODEL MERGING
# ─────────────────────

def merge_model_with_overrides(model: AstroModel, overrides: Optional[ModelOverrides]) -> AstroModel:
    if not overrides:
        return model
    return model


# Example usage:
# subject = compute_subject("John", "1990-05-01 14:30", "New York")
# svg = create_relation_svg(subject1, subject2)
# jpl_positions = compute_jpl_positions("John", "1990-05-01 14:30", "New York")