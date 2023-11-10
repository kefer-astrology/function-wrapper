import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # Import the 3D plotting toolkit
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objs as go


def display_radial(categories: list, values_degrees: list, labels: list) -> None:
    # categories = ['Category A', 'Category B', 'Category C', 'Category D', 'Category E']
    # values_degrees = [45, 90, 135, 180, 225]
    # labels = ["A", "B", "C", "D", "E"]
    # Convert degrees to radians
    theta = np.radians(values_degrees)

    # Set a constant radius for simplicity (you can use variable radii based on your data)
    radius = 1.0

    # Plot the radial lines
    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.scatter(theta, np.ones_like(theta) * radius, marker="o", label=labels)

    # Set the labels for each category
    ax.set_xticks(theta)
    ax.set_xticklabels(categories)
    plt.show()


def figure_3d(objects: object):
    fig = go.Figure()
    dictionary = {
        "planets": {
            "sun": {
                "pos": 120,  # Example: Sun in Taurus (30 degrees into Taurus),
                "symbol": "☉",
            },
            "moon": {
                "pos": 45,  # Example: Moon in Leo (15 degrees into Leo)
                "symbol": "☽",
            },
            "mercury": {
                "pos": 100,  # Example: Mercury in Aries (100 degrees into Aries)
                "symbol": "☿",
            },
            "venus": {
                "pos": 200,  # Example: Venus in Gemini (20 degrees into Gemini)
                "symbol": "♀",
            },
            "mars": {
                "pos": 300,  # Example: Mars in Scorpio (60 degrees into Scorpio)
                "symbol": "♂",
            },
            "jupiter": {
                "pos": 40,  # Example: Jupiter in Virgo (40 degrees into Virgo)
                "symbol": "♃",
            },
            "saturn": {
                "pos": 190,  # Example: Saturn in Libra (10 degrees into Libra)
                "symbol": "♄",
            },
            "uran": {
                "pos": 260,  # Example: Uranus in Sagittarius (20 degrees into Sagittarius)
                "symbol": "♅",
            },
            "neptun": {
                "pos": 310,  # Example: Neptune in Pisces (40 degrees into Pisces)
                "symbol": "♆",
            },
            "pluto": {
                "pos": 25,  # Example: Pluto in Capricorn (25 degrees into Capricorn)
                "symbol": "♇",
            },
        },
        "zodiac": {
            "Aries": {
                "pos": 15,  # align to the middle
                "symbol": "♈",
            },
            "Taurus": {
                "pos": 45,  # align to the middle
                "symbol": "♉",
            },
            "Gemini": {
                "pos": 75,  # align to the middle
                "symbol": "♊",
            },
            "Cancer": {
                "pos": 105,  # align to the middle
                "symbol": "♋",
            },
            "Leo": {
                "pos": 135,  # align to the middle
                "symbol": "♌",
            },
            "Virgo": {
                "pos": 165,  # align to the middle
                "symbol": "♍",
            },
            "Libra": {
                "pos": 195,  # align to the middle
                "symbol": "♎",
            },
            "Scorpio": {
                "pos": 225,  # align to the middle
                "symbol": "♏",
            },
            "Sagittarius": {
                "pos": 255,  # align to the middle
                "symbol": "♐",
            },
            "Capricorn": {
                "pos": 285,  # align to the middle
                "symbol": "♑",
            },
            "Aquarius": {
                "pos": 315,  # align to the middle
                "symbol": "♒",
            },
            "Pisces": {
                "pos": 345,  # align to the middle
                "symbol": "♓",
            },
        },
    }
    # Create the circle show
    house_degrees = list(range(0, 361, 1))
    major_degrees = [str(i + 1) if i % 30 == 0 else "" for i in house_degrees]

    # Customize the chart
    fig.update_layout(
        template=None,
        polar=dict(
            radialaxis=dict(showticklabels=False),
            angularaxis=dict(
                showticklabels=True,
                tickvals=house_degrees,
                ticktext=major_degrees,
                tickwidth=2,
                tickcolor="lightgrey",  # Major tick color
            ),
            sector=[0, 360],
        ),
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[0.9],
            theta=house_degrees,
            mode="lines",
            line=dict(color="gray", width=0.5),
            showlegend=False,
        )
    )

    # Make the inner circle white
    fig.add_trace(
        go.Scatterpolar(
            r=[0.7],
            theta=list(house_degrees),
            mode="lines",
            line=dict(color="blue", width=0.3),
            showlegend=False,
        )
    )
    # Add custom zodiac signs to the outer circle (houses) in the middle of houses
    for sign, detail in dictionary["zodiac"].items():
        detail["pos"]
        detail["symbol"]
        fig.add_trace(
            go.Scatterpolar(
                r=[0.6],
                theta=[detail["pos"]],
                text=detail["symbol"],
                customdata=[detail["symbol"]],
                hoverinfo="all",  # Show only the planet name on hover
                mode="text",
                showlegend=False,
                textfont=dict(size=30),
            )
        )

    # Add planet positions
    for o in objects:
        if o == "earth":
            continue  # TODO: can be from anywhere (skip for now)
        # Convert altitude and azimuth to polar coordinates
        azimuth = (90 - objects[o][0].degrees) % 360
        altitude = 90 - objects[o][1].degrees
        # Create a scatter plot for each object
        fig.add_trace(
            go.Scatterpolar(
                r=[0.6],  # TODO: cope with altitude
                theta=[azimuth],
                text=dictionary["planets"][o]["symbol"],
                customdata=[dictionary["planets"][o]["symbol"]],
                hoverinfo="all",  # Show only the planet name on hover
                mode="text",
                showlegend=False,
                textfont=dict(size=40),
            )
        )
    #
    return fig


def display_3d(categories: list, values_degrees: list, labels: list) -> None:
    # categories = ['Category A', 'Category B', 'Category C', 'Category D', 'Category E']
    # values_degrees = [45, 90, 135, 180, 225]
    # labels = ["A", "B", "C", "D", "E"]
    # Convert degrees to radians
    theta = np.radians(values_degrees)

    # Set a constant radius for simplicity (you can use variable radii based on your data)
    radius = 1.0

    # Calculate 3D coordinates
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    z = np.zeros_like(theta)  # Set all points at z=0 for simplicity

    # Create a 3D plot
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    # Plot the observer
    ax.scatter(0, 0, 0, color="red", marker="o", label="Observer")

    # Plot the planets
    ax.scatter(x, y, z, marker="o", label=labels)

    # Set labels for each planet
    for label, xi, yi, zi in zip(labels, x, y, z):
        ax.text(xi, yi, zi, label, ha="center", va="center")

    # Set labels for axes
    ax.set_xlabel("X (East-West)")
    ax.set_ylabel("Y (North-South)")
    ax.set_zlabel("Z (Up-Down)")

    plt.legend()
    plt.show()


def generate_planets_dec(o: object) -> None:
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.title("Planets declination")
    plt.ylabel("declination [rad]")
    series = []
    for column in o:
        if "_dec" in column and "moon" not in column:
            series.append(column)
            plt.plot(o["date_time"], o[column])
    plt.gcf().autofmt_xdate()
    plt.legend(series, loc="best")
    plt.show()


def generate_moon_dec(o: object) -> None:
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.title("Moon declination")
    plt.ylabel("declination [rad]")
    plt.plot(o["date_time"], o["moon_dec"])
    plt.gcf().autofmt_xdate()
    plt.show()


def generate_skyfield_data(sky_set: object):
    ra_values, dec_values, au_values = zip(*sky_set.values())

    # Create a scatter plot
    fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
    ax.scatter(
        [ra.radians for ra in ra_values],
        [dec.radians for dec in dec_values],
        label="Planets",
    )

    # Set labels and title
    ax.set_xlabel("Right Ascension (RA)")
    ax.set_ylabel("Declination (Dec)")
    ax.set_title("Skyfield Planet Positions in 3D")

    # Add a legend
    ax.legend()

    # Show the plot
    plt.show()
