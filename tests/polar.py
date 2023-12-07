import plotly.graph_objects as go

dictionary = {
    "planets": {
        "Sun": {
            "pos": 120,  # Example: Sun in Taurus (30 degrees into Taurus),
            "symbol": "☉",
        },
        "Moon": {
            "pos": 45,  # Example: Moon in Leo (15 degrees into Leo)
            "symbol": "☽",
        },
        "Mercury": {
            "pos": 100,  # Example: Mercury in Aries (100 degrees into Aries)
            "symbol": "☿",
        },
        "Venus": {
            "pos": 200,  # Example: Venus in Gemini (20 degrees into Gemini)
            "symbol": "♀",
        },
        "Mars": {
            "pos": 300,  # Example: Mars in Scorpio (60 degrees into Scorpio)
            "symbol": "♂",
        },
        "Jupiter": {
            "pos": 40,  # Example: Jupiter in Virgo (40 degrees into Virgo)
            "symbol": "♃",
        },
        "Saturn": {
            "pos": 190,  # Example: Saturn in Libra (10 degrees into Libra)
            "symbol": "♄",
        },
        "Uranus": {
            "pos": 260,  # Example: Uranus in Sagittarius (20 degrees into Sagittarius)
            "symbol": "♅",
        },
        "Neptune": {
            "pos": 310,  # Example: Neptune in Pisces (40 degrees into Pisces)
            "symbol": "♆",
        },
        "Pluto": {
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

# Create the polar chart
fig = go.Figure()

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
            r=[0.85],
            theta=[detail["pos"]],
            text=detail["symbol"],
            mode="text",
            showlegend=False,
            textfont=dict(size=30),
        )
    )

# Add planet positions
for sign, detail in dictionary["planets"].items():
    fig.add_trace(
        go.Scatterpolar(
            r=[0.6],
            theta=[detail["pos"]],
            text=detail["symbol"],  # Display planet name on hover
            customdata=[detail["symbol"]],
            hoverinfo="all",  # Show only the planet name on hover
            mode="text",
            showlegend=False,
            textfont=dict(size=40),
        )
    )


# Show the chart
fig.show()
