import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # Import the 3D plotting toolkit
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


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
