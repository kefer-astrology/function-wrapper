from context import Actual
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from display import generate_moon_dec, generate_planets_dec, generate_skyfield_data
import pandas as pd
from skyfield.api import load, Topos
from skyfield import timelib, almanac


# plt.rcParams["figure.figsize"] = (16, 6) # (w, h)


class Observation:
    def __init__(
            self, source_file: str = "de430.bsp", lat: str = "50.1 N", lon: str = "14.4 E"
    ):
        self.almanac = None
        self.system = load(f"./source/{source_file}")
        self.center_point = self.system["earth"] + Topos(lat, lon)
        self.ts = load.timescale()
        self.observed = None
        self.o = {
            "moon": self.system["moon"],
            "mercury": self.system[1],
            "venus": self.system[2],
            "earth": self.system[2],
            "mars": self.system[4],
            "jupiter": self.system[5],
            "saturn": self.system[6],
            "uran": self.system[7],
            "neptun": self.system[8],
            "pluto": self.system[9],
        }

    def where_is(self, t: object, of: str = "radec") -> object:
        if self.observed:
            return self.center_point.at(self.format_time(t)).observe(self.observed)
        elif of == "radec":
            return {
                planet: self.center_point.at(self.format_time(t)).observe(vector).radec()
                for planet, vector in self.o.items()
            }
        else:
            return {
                planet: self.center_point.at(self.format_time(t))
                .observe(vector)
                .apparent()
                .altaz()
                for planet, vector in self.o.items()
            }

    def degrees(self, t):
        # %t%: timestamp value
        if self.observed:
            return (
                self.center_point.at(self.format_time(t))
                .observe(self.observed)
                .radec()[1]
                .degrees
            )
        else:
            return {
                planet: self.center_point.at(self.format_time(t))
                .observe(vector)
                .radec()[1]
                .degrees
                for planet, vector in self.o.items()
            }

    def distance(self, t):
        # %t%: timestamp value
        return (
            self.center_point.at(self.format_time(t))
            .observe(self.observed)
            .radec()[-1]
            .au
        )

    def moon_phase(self, t):
        # %t%: timestamp value
        return almanac.moon_phase(self.system, self.center_point.at(self.format_time(t)))

    def format_time(self, ts_object: object, format: str = "%Y-%m-%d %H:%M") -> object:
        if isinstance(ts_object, timelib.Time):
            return ts_object.utc_strftime(format)
        elif isinstance(ts_object, (pd.Timestamp, datetime)):
            return self.ts.utc(
                ts_object.year,
                ts_object.month,
                ts_object.day,
                ts_object.hour,
                ts_object.minute,
            )
        else:
            return ts_object


class Almanac(Observation):
    def __init__(self, ts_from=Actual(), ts_to=Actual(), context=almanac.MOON_PHASES, atype="moon"):
        # days (+150 / -150)
        super().__init__()
        if atype == 'moon':
            ts_from, ts_to = self.span(days=30, start=ts_from, end=ts_to)
            self.observed = almanac.find_discrete(ts_from, ts_to, almanac.moon_phases(self.system))
            self.almanac = almanac.MOON_PHASES
        elif atype == "season":
            ts_from, ts_to = self.span(days=365, start=ts_from, end=ts_to)
            self.observed = almanac.find_discrete(ts_from, ts_to, almanac.seasons(self.system))
            self.almanac = almanac.SEASONS
        elif atype == "meridian":
            ts_from, ts_to = self.span(days=100, start=ts_from, end=ts_to)
            self.observed = almanac.find_discrete(ts_from, ts_to, almanac.meridian_transits(self.system))
            self.almanac = almanac.MERIDIAN_TRANSITS

    def report(self):
        o_o = {}
        for index in range(len(self.observed[0])):
            evt_time = self.observed[0][index].utc_strftime()
            o_o [evt_time] = self.almanac[self.observed[-1][index]]
        return o_o

    def span(self, days, start, end):
        start.add_some_time((-1)*days/2)
        start.assign_time_zone()
        end.add_some_time(days/2)
        end.assign_time_zone()
        return self.ts.from_datetime(start.value), self.ts.from_datetime(end.value)




def frequency(day=0, hour=0, minute=0):
    if minute:
        return f"{minute}min"
    elif hour:
        return f"{60 * hour}min"
    elif day:
        return f"{1440 * day}min"  # 1 day timestep


def observer(start, end, gran):
    """iteration that computes values for given parameters
    %c%: center point position (with Topos module or another)
    %start%: start date (pandas data frame row)
    %end%: end date (pandas dataframe row)
    %gran%: granularity (pandas dataframe row)
    returns pandas dataframe
    """
    comp = Observation()
    print(
        f"""from {start.strftime('%d/%m/%Y')} to {end.strftime('%d/%m/%Y')} at time step {gran.total_seconds() / 60} minutes"""
    )
    time_span = pd.date_range(start, end, freq=f"{int(gran.total_seconds() / 60)}min")
    obs = pd.DataFrame(time_span, columns=["date_time"])
    for obj in comp.o.keys():
        # print(dir(obj))
        comp.observed = comp.o[obj]
        obs[f"{obj}_dec"] = obs["date_time"].apply(comp.degrees)
        obs[f"{obj}_dist"] = obs["date_time"].apply(comp.distance)
        # if 'moon' in obj:  # moon phases are not valid for now
        #     obs['moon_phase'] = obs['date_time'].apply(comp.moon_phase)

    return obs


def simple_observe():
    look = Observation()
    planets = look.where_is(datetime.now())
    generate_skyfield_data(planets)


def time_frame_computation():
    start_point = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_point = start_point + relativedelta(days=1)
    granularity = timedelta(hours=1)

    print("Time settings verification:")
    print(f"  Start: {start_point.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  Finish: {end_point.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  Time step: {granularity} hours")
    o = observer(start_point, end_point, granularity)
    o.to_csv("./result/computed_current.csv", index=False, mode="w")

    # generate_moon_dec(o)

    generate_planets_dec(o)


if __name__ == "__main__":
    a = Almanac(atype="season")
    print(a.report())
    # simple_observe()
    # time_frame_computation()
