---

title: z_visual Module

description: documentation for z_visual module

weight: 10

---


# `z_visual` module

## Functions

## `build_radix_figure`

```python
build_radix_figure(positions: dict) -> plotly.graph_objs._figure.Figure
```

Build a standardized polar (radix) chart figure from planet positions in degrees [0,360).
positions: mapping of planet name (lowercase or mixed) -&gt; ecliptic longitude in degrees

## `display_3d`

```python
display_3d(categories: list, values_degrees: list, labels: list) -> None
```

Render a simple Matplotlib 3D scatter plot for objects at given angles.

## `display_radial`

```python
display_radial(categories: list, values_degrees: list, labels: list) -> None
```

Quick Matplotlib radial scatter demo for given categories and degrees.

#### Parameters

- **categories**: labels for angular ticks

- **values_degrees**: list of angles in degrees

- **labels**: point labels to show as markers

## `figure_3d`

```python
figure_3d(objects: object)
```

Build a Plotly polar figure for planetary positions and zodiac labels.

## `generate_moon_dec`

```python
generate_moon_dec(o: object) -> None
```

Plot moon declination time series from DataFrame-like `o`.

## `generate_planets_dec`

```python
generate_planets_dec(o: object) -> None
```

Plot declination time series for all non-moon bodies in the DataFrame-like `o`.

## `generate_skyfield_data`

```python
generate_skyfield_data(sky_set: object)
```

Render a polar plot from a mapping of right ascension/declination tuples.

## `write_plotly_html`

```python
write_plotly_html(fig: plotly.graph_objs._figure.Figure, tmpname: str = 'radix_chart.html') -> str
```

Write a Plotly figure to a temporary HTML file and return its absolute path.

#### Parameters

- **fig**: Plotly Figure to serialize to HTML

- **tmpname**: filename to use within the system temporary directory
