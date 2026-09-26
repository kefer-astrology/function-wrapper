---

title: z_visual Module

description: documentation for z_visual module

weight: 10

---


# `z_visual` module

## Functions

## `build_radix_figure`

```python
build_radix_figure(positions: dict, house_cusps: list | None = None, axis_longitudes: dict | None = None, aspects: list | None = None, aspect_colors: dict | None = None, transit_positions: dict | None = None) -> plotly.graph_objs._figure.Figure
```

Build a standardized polar (radix) chart figure from planet positions in degrees [0,360).

## `build_synastry_figure`

```python
build_synastry_figure(positions1: dict, positions2: dict, name1: str, name2: str) -> plotly.graph_objs._figure.Figure
```

Build a two-subject overlay (synastry) chart on a shared zodiac ring.

## `write_plotly_html`

```python
write_plotly_html(fig: plotly.graph_objs._figure.Figure, tmpname: str = 'radix_chart.html') -> str
```

Write a Plotly figure to a temporary HTML file and return its absolute path.

#### Parameters

- **fig**: Plotly Figure to serialize to HTML

- **tmpname**: filename to use within the system temporary directory

## `write_plotly_svg`

```python
write_plotly_svg(fig: plotly.graph_objs._figure.Figure, tmpname: str = 'radix_chart.svg') -> str
```

Write a Plotly figure to a static SVG file (via kaleido) and return its absolute path.

#### Parameters

- **fig**: Plotly Figure to export

- **tmpname**: filename to use within the system temporary directory
