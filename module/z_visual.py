import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # Import the 3D plotting toolkit
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objs as go
import tempfile
from pathlib import Path


def display_radial(categories: list, values_degrees: list, labels: list) -> None:
    """Quick Matplotlib radial scatter demo for given categories and degrees.

    Parameters:
    - categories: labels for angular ticks
    - values_degrees: list of angles in degrees
    - labels: point labels to show as markers
    """
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
    """Build a Plotly polar figure for planetary positions and zodiac labels.

    `objects` is expected to be a mapping-like structure where each key is a
    planet name and value contains angular information (degrees).
    """
    fig = go.Figure()
    dictionary = {
        "planets": {
            "sun": {
                "pos": 120,  # Example: Sun in Taurus (30 degrees into Taurus),
                "symbol": "\u2609",
            },
            "moon": {
                "pos": 45,  # Example: Moon in Leo (15 degrees into Leo)
                "symbol": "\u263D",
            },
            "mercury": {
                "pos": 100,  # Example: Mercury in Aries (100 degrees into Aries)
                "symbol": "\u263F",
            },
            "venus": {
                "pos": 200,  # Example: Venus in Gemini (20 degrees into Gemini)
                "symbol": "\u2640",
            },
            "mars": {
                "pos": 300,  # Example: Mars in Scorpio (60 degrees into Scorpio)
                "symbol": "\u2642",
            },
            "jupiter": {
                "pos": 40,  # Example: Jupiter in Virgo (40 degrees into Virgo)
                "symbol": "\u2643",
            },
            "saturn": {
                "pos": 190,  # Example: Saturn in Libra (10 degrees into Libra)
                "symbol": "\u2644",
            },
            "uran": {
                "pos": 260,  # Example: Uranus in Sagittarius (20 degrees into Sagittarius)
                "symbol": "\u2645",
            },
            "neptun": {
                "pos": 310,  # Example: Neptune in Pisces (40 degrees into Pisces)
                "symbol": "\u2646",
            },
            "pluto": {
                "pos": 25,  # Example: Pluto in Capricorn (25 degrees into Capricorn)
                "symbol": "\u2647",
            },
        },
        "zodiac": {
            "Aries": {
                "pos": 15,  # align to the middle
                "symbol": "\u2648",
            },
            "Taurus": {
                "pos": 45,  # align to the middle
                "symbol": "\u2649",
            },
            "Gemini": {
                "pos": 75,  # align to the middle
                "symbol": "\u264A",
            },
            "Cancer": {
                "pos": 105,  # align to the middle
                "symbol": "\u264B",
            },
            "Leo": {
                "pos": 135,  # align to the middle
                "symbol": "\u264C",
            },
            "Virgo": {
                "pos": 165,  # align to the middle
                "symbol": "\u264D",
            },
            "Libra": {
                "pos": 195,  # align to the middle
                "symbol": "\u264E",
            },
            "Scorpio": {
                "pos": 225,  # align to the middle
                "symbol": "\u264F",
            },
            "Sagittarius": {
                "pos": 255,  # align to the middle
                "symbol": "\u2650",
            },
            "Capricorn": {
                "pos": 285,  # align to the middle
                "symbol": "\u2651",
            },
            "Aquarius": {
                "pos": 315,  # align to the middle
                "symbol": "\u2652",
            },
            "Pisces": {
                "pos": 345,  # align to the middle
                "symbol": "\u2653",
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
            continue  # Earth is omitted from topocentric marker plot
        # Convert altitude and azimuth to polar coordinates
        azimuth = (90 - objects[o][0].degrees) % 360
        altitude = 90 - objects[o][1].degrees
        # Create a scatter plot for each object
        fig.add_trace(
            go.Scatterpolar(
                r=[0.6],  # Fixed radius: altitude not encoded in this view
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
    """Render a simple Matplotlib 3D scatter plot for objects at given angles."""
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
    """Plot declination time series for all non-moon bodies in the DataFrame-like `o`."""
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
    """Plot moon declination time series from DataFrame-like `o`."""
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.title("Moon declination")
    plt.ylabel("declination [rad]")
    plt.plot(o["date_time"], o["moon_dec"])
    plt.gcf().autofmt_xdate()
    plt.show()


def generate_skyfield_data(sky_set: object):
    """Render a polar plot from a mapping of right ascension/declination tuples."""
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


# ─────────────────────
# RADIX DISPLAY (Plotly)
# ─────────────────────

PLANET_SYMBOLS = {
    "sun": "\u2609",
    "moon": "\u263D",
    "mercury": "\u263F",
    "venus": "\u2640",
    "mars": "\u2642",
    "jupiter": "\u2643",
    "saturn": "\u2644",
    "uranus": "\u2645",
    "neptune": "\u2646",
    "pluto": "\u2647",
}

ZODIAC_ORDER = [
    ("Aries", "\u2648"), ("Taurus", "\u2649"), ("Gemini", "\u264A"), ("Cancer", "\u264B"),
    ("Leo", "\u264C"), ("Virgo", "\u264D"), ("Libra", "\u264E"), ("Scorpio", "\u264F"),
    ("Sagittarius", "\u2650"), ("Capricorn", "\u2651"), ("Aquarius", "\u2652"), ("Pisces", "\u2653"),
]


def build_radix_figure(positions: dict) -> go.Figure:
    """Build a standardized polar (radix) chart figure from planet positions in degrees [0,360).
    positions: mapping of planet name (lowercase or mixed) -> ecliptic longitude in degrees
    """
    # Debug: Check if positions are all zeros or suspiciously clustered
    if positions:
        values = list(positions.values())
        coordinate_tolerance = 0.0001  # Default, ModelSettings can override
        all_zero = all(abs(v) < coordinate_tolerance for v in values)
        if all_zero:
            import warnings
            warnings.warn(f"All position values are near zero: {positions}")
    
    fig = go.Figure()
    # Base axes and ticks
    house_degrees = list(range(0, 361, 1))
    major_degrees = [str(i + 1) if i % 30 == 0 else "" for i in house_degrees]

    fig.update_layout(
        template=None,
        polar=dict(
            radialaxis=dict(showticklabels=False),
            angularaxis=dict(
                showticklabels=False,  # Hide degree labels, show only on hover
                tickvals=house_degrees,
                ticktext=major_degrees,
                tickwidth=2,
                tickcolor="lightgrey",
            ),
            sector=[0, 360],
        ),
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
    )

    # Outer ring
    fig.add_trace(go.Scatterpolar(r=[0.9], theta=house_degrees, mode="lines", line=dict(color="gray", width=0.5)))
    # Inner ring
    fig.add_trace(go.Scatterpolar(r=[0.7], theta=house_degrees, mode="lines", line=dict(color="blue", width=0.3)))

    # Zodiac labels at mid-sign (15 + 30k) - hidden, only show on hover
    for idx, (name, symbol) in enumerate(ZODIAC_ORDER):
        theta = 15 + idx * 30
        fig.add_trace(go.Scatterpolar(
            r=[0.85], 
            theta=[theta], 
            text="",  # Hide visible text
            mode="markers",
            marker=dict(size=8, color="rgba(0,0,0,0)", line=dict(width=0)),  # Invisible marker for hover
            hovertext=f"{symbol} {name}",
            hoverinfo="text",
            showlegend=False
        ))

    # Planets
    for key, deg in positions.items():
        pname = str(key).lower()
        symbol = PLANET_SYMBOLS.get(pname, pname.capitalize())
        
        # Ensure deg is a float and handle None/NaN values
        try:
            deg_float = float(deg)
        except (ValueError, TypeError):
            continue  # Skip invalid values
        
        # Normalize angle to [0, 360) range
        # Python's % operator handles negatives correctly: -2.9 % 360 = 357.1
        normalized_deg = deg_float % 360
        # Ensure it's in [0, 360) range (handle edge case where deg % 360 could be negative)
        if normalized_deg < 0:
            normalized_deg += 360
        
        # Only add trace if symbol is valid (not empty)
        if symbol:
            fig.add_trace(
                go.Scatterpolar(
                    r=[0.6],
                    theta=[normalized_deg],  # Plotly expects degrees for theta in polar plots
                    text=symbol,  # Show glyph symbol
                    mode="text",  # Text mode to display glyphs
                    textfont=dict(size=40, color="black"),  # Visible glyph
                    hovertext=f"{symbol} {pname.capitalize()} ({normalized_deg:.4f}°)",
                    hoverinfo="text",
                    showlegend=False,
                )
            )

    return fig


def write_plotly_html(fig: go.Figure, tmpname: str = "radix_chart.html") -> str:
    """Write a Plotly figure to a temporary HTML file and return its absolute path.

    Parameters:
    - fig: Plotly Figure to serialize to HTML
    - tmpname: filename to use within the system temporary directory
    """
    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    tmpdir = Path(tempfile.gettempdir())
    out_path = tmpname if isinstance(tmpname, Path) else tmpdir / tmpname
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return str(out_path)
