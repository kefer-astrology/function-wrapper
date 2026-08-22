import math
import urllib.parse
from typing import Optional
import plotly.graph_objs as go
import tempfile
from pathlib import Path


# ─────────────────────
# RADIX DISPLAY (Plotly)
# ─────────────────────

# Kept for any external callers/tests that still expect textual glyphs (e.g. a
# fallback table); the radix/synastry charts themselves render real SVG icons
# (see PLANET_SVG_GLYPHS/ZODIAC_SVG_GLYPHS below) instead of these characters.
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

# -----------------------------
# Real vector glyphs (SVG), used instead of Unicode astrological symbols \u2014
# those render as colorful "emoji-style" pictures in many browsers/fonts
# rather than plain line-art. Each entry is inner SVG markup (viewBox 0 0 100
# 100) wrapped by _svg_data_uri(); "{color}" is substituted at render time.
# -----------------------------
PLANET_SVG_GLYPHS = {
    "sun": '<circle cx="50" cy="50" r="28"/><circle cx="50" cy="50" r="5" fill="{color}" stroke="none"/>',
    "moon": '<path d="M62,15 A35,35 0 1 0 62,85 A25,25 0 1 1 62,15 Z" fill="{color}" stroke="none"/>',
    "mercury": '<path d="M35,18 a15,12 0 0 0 30,0"/><circle cx="50" cy="40" r="16"/>'
               '<line x1="50" y1="56" x2="50" y2="82"/><line x1="36" y1="72" x2="64" y2="72"/>',
    "venus": '<circle cx="50" cy="35" r="18"/><line x1="50" y1="53" x2="50" y2="82"/>'
             '<line x1="36" y1="70" x2="64" y2="70"/>',
    "mars": '<circle cx="42" cy="58" r="17"/><line x1="53" y1="47" x2="78" y2="22"/>'
            '<polyline points="58,22 78,22 78,42" fill="none"/>',
    "jupiter": '<path d="M28,30 Q28,55 52,55"/><line x1="58" y1="18" x2="58" y2="82"/>'
               '<line x1="36" y1="55" x2="72" y2="55"/>',
    "saturn": '<line x1="35" y1="18" x2="35" y2="72"/><line x1="20" y1="34" x2="50" y2="34"/>'
              '<path d="M35,58 Q58,58 58,74 Q58,88 40,84"/>',
    "uranus": '<line x1="30" y1="25" x2="30" y2="58"/><line x1="70" y1="25" x2="70" y2="58"/>'
              '<line x1="30" y1="42" x2="70" y2="42"/><line x1="50" y1="42" x2="50" y2="78"/>'
              '<circle cx="50" cy="85" r="7" fill="{color}" stroke="none"/>',
    "neptune": '<line x1="30" y1="20" x2="30" y2="52"/><line x1="70" y1="20" x2="70" y2="52"/>'
               '<path d="M30,36 Q50,58 70,36"/><line x1="50" y1="52" x2="50" y2="82"/>'
               '<line x1="36" y1="74" x2="64" y2="74"/>',
    "pluto": '<circle cx="50" cy="28" r="13"/><path d="M32,46 Q50,64 68,46"/>'
             '<line x1="50" y1="46" x2="50" y2="82"/><line x1="34" y1="66" x2="66" y2="66"/>',
    "north_node": '<path d="M22,62 a28,28 0 1 1 56,0"/><line x1="22" y1="62" x2="22" y2="78"/>'
                  '<line x1="78" y1="62" x2="78" y2="78"/>',
    "south_node": '<path d="M22,38 a28,28 0 1 0 56,0"/><line x1="22" y1="38" x2="22" y2="22"/>'
                  '<line x1="78" y1="38" x2="78" y2="22"/>',
    "chiron": '<circle cx="50" cy="30" r="13"/><line x1="50" y1="43" x2="50" y2="75"/>'
              '<line x1="38" y1="58" x2="62" y2="58"/><line x1="38" y1="75" x2="62" y2="75"/>',
    "lilith": '<path d="M58,15 A28,28 0 1 0 58,71 A20,20 0 1 1 58,15 Z" fill="{color}" stroke="none"/>'
              '<line x1="50" y1="71" x2="50" y2="88"/><line x1="40" y1="80" x2="60" y2="80"/>',
}

# Aliases sharing an existing glyph \u2014 e.g. mean/true variants of the same point.
_PLANET_GLYPH_ALIASES = {
    "mean_node": "north_node",
    "true_node": "north_node",
    "true_north_node": "north_node",
    "mean_south_node": "south_node",
    "true_south_node": "south_node",
    "mean_lilith": "lilith",
    "true_lilith": "lilith",
}

ZODIAC_SVG_GLYPHS = {
    "Aries": '<path d="M50,82 L50,52 Q50,22 32,22 Q18,22 18,36 Q18,46 27,46"/>'
             '<path d="M50,52 Q50,22 68,22 Q82,22 82,36 Q82,46 73,46"/>',
    "Taurus": '<path d="M32,20 Q32,38 50,38 Q68,38 68,20"/><circle cx="50" cy="60" r="20"/>',
    "Gemini": '<line x1="28" y1="24" x2="72" y2="24"/><line x1="28" y1="76" x2="72" y2="76"/>'
              '<line x1="38" y1="24" x2="38" y2="76"/><line x1="62" y1="24" x2="62" y2="76"/>',
    "Cancer": '<path d="M28,38 a14,14 0 1 0 14,14"/><circle cx="28" cy="32" r="5" fill="{color}" stroke="none"/>'
              '<path d="M72,62 a14,14 0 1 0 -14,-14"/><circle cx="72" cy="68" r="5" fill="{color}" stroke="none"/>',
    "Leo": '<circle cx="35" cy="62" r="18"/><path d="M50,52 Q70,52 70,32 Q70,18 56,18 Q46,18 46,28"/>',
    "Virgo": '<path d="M20,20 L20,68 M20,20 Q20,42 36,42 L36,68 M36,20 Q36,42 52,42 L52,68 M52,20 Q52,42 65,42"/>'
             '<path d="M65,42 Q84,42 84,60 Q84,76 66,72"/>',
    "Libra": '<path d="M24,36 Q50,14 76,36"/><line x1="18" y1="62" x2="82" y2="62"/>'
             '<line x1="50" y1="46" x2="50" y2="62"/>',
    "Scorpio": '<path d="M20,20 L20,68 M20,20 Q20,42 36,42 L36,68 M36,20 Q36,42 52,42 L52,68 M52,20 Q52,42 68,42 L78,58"/>'
               '<polyline points="70,50 84,60 72,66" fill="none"/>',
    "Sagittarius": '<line x1="20" y1="80" x2="80" y2="20"/><polyline points="54,20 80,20 80,46" fill="none"/>'
                    '<line x1="42" y1="42" x2="58" y2="58"/>',
    "Capricorn": '<path d="M20,20 Q20,52 42,52 Q58,52 58,36"/>'
                 '<path d="M58,36 Q58,64 78,64 Q92,64 90,48 Q88,37 76,40"/>',
    "Aquarius": '<path d="M16,38 Q26,26 36,38 Q46,50 56,38 Q66,26 76,38 Q86,50 96,38" transform="translate(-6,-6)"/>'
                '<path d="M16,66 Q26,54 36,66 Q46,78 56,66 Q66,54 76,66 Q86,78 96,66" transform="translate(-6,6)"/>',
    "Pisces": '<path d="M22,20 Q44,50 22,80"/><path d="M78,20 Q56,50 78,80"/>'
              '<line x1="22" y1="50" x2="78" y2="50"/>',
}


def _svg_data_uri(inner_svg_template: str, color: str) -> str:
    """Wrap inner SVG markup (with a "{color}" placeholder) into a data URI."""
    inner = inner_svg_template.replace("{color}", color)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<g fill="none" stroke="{color}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">{inner}</g>'
        '</svg>'
    )
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)


def _monogram_svg(body_id: str) -> str:
    """Fallback glyph for bodies without a hand-authored symbol: a circled monogram."""
    label = "".join(ch for ch in body_id if ch.isalpha())[:2].upper() or "?"
    return (
        '<circle cx="50" cy="50" r="30"/>'
        f'<text x="50" y="60" font-size="30" text-anchor="middle" '
        'font-family="sans-serif" fill="{color}" stroke="none">' + label + '</text>'
    )


def _glyph_svg_for_body(body_id: str) -> str:
    key = body_id.lower()
    if key in PLANET_SVG_GLYPHS:
        return PLANET_SVG_GLYPHS[key]
    if key in _PLANET_GLYPH_ALIASES:
        return PLANET_SVG_GLYPHS[_PLANET_GLYPH_ALIASES[key]]
    return _monogram_svg(key)


def _polar_to_xy(r: float, theta_deg: float) -> tuple:
    """Convert (radius, angle-in-degrees) to cartesian (x, y), matching Plotly's
    default polar convention (0deg = +x axis, increasing counterclockwise)."""
    rad = math.radians(theta_deg)
    return r * math.cos(rad), r * math.sin(rad)


def _build_base_ring() -> go.Figure:
    """Build the shared chart skeleton: rings, sign spokes, and zodiac glyphs/hover.

    Uses a plain cartesian figure (not a Plotly polar subplot) so that real SVG
    glyph icons can be anchored at exact (x, y) positions via add_layout_image —
    Plotly's layout images don't support polar/theta-r coordinates directly.
    """
    fig = go.Figure()
    fig.update_layout(
        template=None,
        xaxis=dict(visible=False, range=[-1.25, 1.25], scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False, range=[-1.25, 1.25]),
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        height=585,  # 30% taller than Plotly's default 450px
    )

    ring_theta = list(range(0, 361, 2))
    outer_xy = [_polar_to_xy(0.9, t) for t in ring_theta]
    inner_xy = [_polar_to_xy(0.7, t) for t in ring_theta]
    fig.add_trace(go.Scatter(
        x=[p[0] for p in outer_xy], y=[p[1] for p in outer_xy],
        mode="lines", line=dict(color="gray", width=1), hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[p[0] for p in inner_xy], y=[p[1] for p in inner_xy],
        mode="lines", line=dict(color="royalblue", width=1), hoverinfo="skip",
    ))

    # Sign-boundary spokes every 30 degrees, between the two rings
    for k in range(12):
        theta = k * 30
        x0, y0 = _polar_to_xy(0.7, theta)
        x1, y1 = _polar_to_xy(0.9, theta)
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1],
            mode="lines", line=dict(color="lightgray", width=1), hoverinfo="skip",
        ))

    # Zodiac sign glyphs at mid-sign (15 + 30k), plus an invisible hover marker
    hover_x, hover_y, hover_text = [], [], []
    for idx, (name, symbol) in enumerate(ZODIAC_ORDER):
        theta = 15 + idx * 30
        x, y = _polar_to_xy(0.8, theta)
        hover_x.append(x)
        hover_y.append(y)
        hover_text.append(f"{symbol} {name}")
        svg_uri = _svg_data_uri(ZODIAC_SVG_GLYPHS.get(name, ""), "#555555")
        fig.add_layout_image(
            source=svg_uri, xref="x", yref="y", x=x, y=y,
            sizex=0.16, sizey=0.16, xanchor="center", yanchor="middle", layer="above",
        )
    fig.add_trace(go.Scatter(
        x=hover_x, y=hover_y, mode="markers",
        marker=dict(size=22, color="rgba(0,0,0,0)"),
        hovertext=hover_text, hoverinfo="text", showlegend=False,
    ))

    return fig


def _add_position_markers(fig: go.Figure, positions: dict, radius: float, color: str, legend_label: str) -> None:
    """Add one subject's planet glyphs (real SVG icons) to an existing chart at the given ring radius."""
    hover_x, hover_y, hover_text = [], [], []
    for key, deg in positions.items():
        pname = str(key).lower()

        # Ensure deg is a float and handle None/NaN values (also unwraps extended {'longitude': ...} dicts)
        deg_value = deg.get("longitude") if isinstance(deg, dict) else deg
        try:
            deg_float = float(deg_value)
        except (ValueError, TypeError):
            continue  # Skip invalid values

        # Normalize angle to [0, 360) range
        # Python's % operator handles negatives correctly: -2.9 % 360 = 357.1
        normalized_deg = deg_float % 360
        # Ensure it's in [0, 360) range (handle edge case where deg % 360 could be negative)
        if normalized_deg < 0:
            normalized_deg += 360

        x, y = _polar_to_xy(radius, normalized_deg)
        hover_x.append(x)
        hover_y.append(y)
        label_prefix = f"{legend_label}: " if legend_label else ""
        hover_text.append(f"{label_prefix}{pname.capitalize()} ({normalized_deg:.4f}°)")

        svg_uri = _svg_data_uri(_glyph_svg_for_body(pname), color)
        fig.add_layout_image(
            source=svg_uri, xref="x", yref="y", x=x, y=y,
            sizex=0.11, sizey=0.11, xanchor="center", yanchor="middle", layer="above",
        )

    fig.add_trace(go.Scatter(
        x=hover_x, y=hover_y, mode="markers",
        marker=dict(size=20, color="rgba(0,0,0,0)"),
        hovertext=hover_text, hoverinfo="text", showlegend=False,
    ))


def _canonical_positions(positions: dict) -> dict:
    """Drop convenience aliases (mean_node/true_node/mean_south_node/mean_lilith/etc.)
    that duplicate a canonical catalog body at an identical longitude.

    A raw compute_positions() call with no observable_objects filter returns every
    alias alongside the canonical id, which otherwise draws 2-3 overlapping glyphs
    at the same degree on the wheel. Applied here (not per call site) so every
    consumer of build_radix_figure/build_synastry_figure - Streamlit's create-new
    preview and chart page, Kivy, and the CLI synastry command - renders the same
    deduplicated body set.
    """
    if not positions:
        return positions
    try:
        from module.model_catalog import builtin_standard_model
    except ImportError:
        from model_catalog import builtin_standard_model
    canonical_ids = {b.id for b in builtin_standard_model().body_definitions}
    return {k: v for k, v in positions.items() if k in canonical_ids}


_DEFAULT_ASPECT_COLORS = {
    "conjunction": "#888888",
    "opposition": "#d64545",
    "square": "#d64545",
    "trine": "#3b82c4",
    "sextile": "#3b82c4",
    "quincunx": "#8855bb",
    "semisextile": "#4caf50",
    "semisquare": "#e08a2b",
    "sesquiquadrate": "#e08a2b",
    "quintile": "#8855bb",
    "biquintile": "#8855bb",
}
_ANGULAR_HOUSE_INDICES = {0, 3, 6, 9}  # houses 1/4/7/10 -> Asc/IC/Dsc/MC


def _longitude_of(value) -> Optional[float]:
    """Unwrap a plain float or an extended {'longitude': ...} dict into a float degree."""
    raw = value.get("longitude") if isinstance(value, dict) else value
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _aspect_endpoint_longitude(point_id, positions: dict, axis_longitudes: Optional[dict]) -> Optional[float]:
    key = str(point_id).lower()
    if key in positions:
        return _longitude_of(positions[key])
    if axis_longitudes and key in axis_longitudes:
        return _longitude_of(axis_longitudes[key])
    return None


def _add_house_cusps(fig: go.Figure, house_cusps, inner_r: float = 0.55, outer_r: float = 0.68,
                      label_r: float = 0.615) -> None:
    """Draw 12 house-cusp lines at their real computed longitudes plus house numbers,
    with angular houses (1/4/7/10) emphasized -- mirrors React's Layer_HouseCusps."""
    if not house_cusps or len(house_cusps) != 12:
        return
    cusp_degs = [_longitude_of(c) for c in house_cusps]
    if any(c is None for c in cusp_degs):
        return
    for idx, cusp_deg in enumerate(cusp_degs):
        cusp_deg = cusp_deg % 360
        next_deg = cusp_degs[(idx + 1) % 12] % 360
        is_angular = idx in _ANGULAR_HOUSE_INDICES
        x0, y0 = _polar_to_xy(inner_r, cusp_deg)
        x1, y1 = _polar_to_xy(outer_r, cusp_deg)
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line=dict(color="#333333" if is_angular else "#999999", width=2 if is_angular else 1),
            hoverinfo="skip", showlegend=False,
        ))
        mid_deg = (cusp_deg + ((next_deg - cusp_deg) % 360) / 2) % 360
        lx, ly = _polar_to_xy(label_r, mid_deg)
        fig.add_annotation(
            x=lx, y=ly, text=str(idx + 1), showarrow=False,
            font=dict(size=13 if is_angular else 11, color="#333333"),
        )


def _add_axis_lines(fig: go.Figure, axis_longitudes: Optional[dict], radius: float = 0.95) -> None:
    """Draw ASC-DSC and MC-IC diameters plus angle labels -- mirrors React's Layer_AxisLines."""
    if not axis_longitudes:
        return
    asc = _longitude_of(axis_longitudes.get("asc"))
    dsc = _longitude_of(axis_longitudes.get("desc", axis_longitudes.get("dsc")))
    mc, ic = _longitude_of(axis_longitudes.get("mc")), _longitude_of(axis_longitudes.get("ic"))
    for a, b, dash in ((asc, dsc, "dash"), (mc, ic, "dot")):
        if a is None or b is None:
            continue
        xa, ya = _polar_to_xy(radius, a)
        xb, yb = _polar_to_xy(radius, b)
        fig.add_trace(go.Scatter(
            x=[xa, xb], y=[ya, yb], mode="lines",
            line=dict(color="#666666", width=1.25, dash=dash),
            hoverinfo="skip", showlegend=False,
        ))
    for key, lon in (("asc", asc), ("dsc", dsc), ("mc", mc), ("ic", ic)):
        if lon is None:
            continue
        x, y = _polar_to_xy(radius, lon)
        svg_uri = _svg_data_uri(_glyph_svg_for_body(key), "#333333")
        fig.add_layout_image(
            source=svg_uri, xref="x", yref="y", x=x, y=y,
            sizex=0.12, sizey=0.12, xanchor="center", yanchor="middle", layer="above",
        )


def _add_aspect_lines(fig: go.Figure, aspects, positions: dict, axis_longitudes: Optional[dict],
                       radius: float = 0.43, aspect_colors: Optional[dict] = None) -> None:
    """Draw radix aspect chords at a fixed inner radius -- mirrors React's Layer_AspectLines."""
    if not aspects:
        return
    colors = {**_DEFAULT_ASPECT_COLORS, **(aspect_colors or {})}
    for aspect in aspects:
        a_id, b_id, a_type = aspect.get("from"), aspect.get("to"), aspect.get("type")
        a_lon = _aspect_endpoint_longitude(a_id, positions, axis_longitudes)
        b_lon = _aspect_endpoint_longitude(b_id, positions, axis_longitudes)
        if a_lon is None or b_lon is None:
            continue
        xa, ya = _polar_to_xy(radius, a_lon)
        xb, yb = _polar_to_xy(radius, b_lon)
        orb = abs(aspect.get("orb") or 0)
        width = 2.0 if orb <= 1.5 else 1.3 if orb <= 3.5 else 0.8
        fig.add_trace(go.Scatter(
            x=[xa, xb], y=[ya, yb], mode="lines",
            line=dict(color=colors.get(a_type, "#aaaaaa"), width=width),
            opacity=0.45,
            hovertext=f"{str(a_id).capitalize()} {a_type} {str(b_id).capitalize()} (orb {orb:.2f}°)",
            hoverinfo="text", showlegend=False,
        ))


def _add_transit_ring(fig: go.Figure, transit_positions: Optional[dict], inner_r: float = 1.0,
                       outer_r: float = 1.15, glyph_r: float = 1.08, color: str = "#c2410c") -> None:
    """Draw an additional ring beyond the natal zodiac band for transit bodies -- mirrors React's
    Layer_TransitRing. Only appears when transit positions are actually supplied: computing a
    transit adds this extra wheel on the chart's outer border, on top of the natal radix.
    """
    if not transit_positions:
        return
    ring_theta = list(range(0, 361, 4))
    for r, width, op in ((outer_r, 1.1, 0.55), (inner_r, 0.9, 0.3)):
        xy = [_polar_to_xy(r, t) for t in ring_theta]
        fig.add_trace(go.Scatter(
            x=[p[0] for p in xy], y=[p[1] for p in xy], mode="lines",
            line=dict(color=color, width=width), opacity=op, hoverinfo="skip", showlegend=False,
        ))
    hover_x, hover_y, hover_text = [], [], []
    for key, deg in transit_positions.items():
        deg_float = _longitude_of(deg)
        if deg_float is None:
            continue
        deg_float %= 360
        x, y = _polar_to_xy(glyph_r, deg_float)
        hover_x.append(x)
        hover_y.append(y)
        hover_text.append(f"Tranzit {str(key).capitalize()} ({deg_float:.4f}°)")
        svg_uri = _svg_data_uri(_glyph_svg_for_body(str(key).lower()), color)
        fig.add_layout_image(
            source=svg_uri, xref="x", yref="y", x=x, y=y,
            sizex=0.10, sizey=0.10, xanchor="center", yanchor="middle", layer="above",
        )
    fig.add_trace(go.Scatter(
        x=hover_x, y=hover_y, mode="markers",
        marker=dict(size=18, color="rgba(0,0,0,0)"),
        hovertext=hover_text, hoverinfo="text", showlegend=False,
    ))


def build_radix_figure(positions: dict, house_cusps: Optional[list] = None,
                        axis_longitudes: Optional[dict] = None, aspects: Optional[list] = None,
                        aspect_colors: Optional[dict] = None,
                        transit_positions: Optional[dict] = None) -> go.Figure:
    """Build a standardized polar (radix) chart figure from planet positions in degrees [0,360).

    positions: mapping of planet name (lowercase or mixed) -> ecliptic longitude in degrees
        (plain float or extended {'longitude': ...} dict).
    house_cusps: optional 12 real computed house-cusp longitudes (not generic 30-degree spokes) --
        draws a house ring with house numbers, angular houses (1/4/7/10) emphasized.
    axis_longitudes: optional {'asc','dsc','mc','ic'} longitudes -- draws axis diameters + labels.
    aspects: optional list of {'from','to','type','orb'} dicts (e.g. from
        compute_normalized_chart_aspects) -- draws aspect chords on an inner ring.
    transit_positions: optional second positions dict -- draws an additional outer ring beyond
        the zodiac band for transit bodies (a bi-wheel). Only appears when supplied.
    """
    positions = _canonical_positions(positions)
    if transit_positions:
        transit_positions = _canonical_positions(transit_positions)

    # Debug: Check if positions are all zeros or suspiciously clustered
    if positions:
        longitudes = [lon for lon in (_longitude_of(v) for v in positions.values()) if lon is not None]
        coordinate_tolerance = 0.0001  # Default, ModelSettings can override
        if longitudes and all(abs(v) < coordinate_tolerance for v in longitudes):
            import warnings
            warnings.warn(f"All position values are near zero: {positions}")

    fig = _build_base_ring()
    _add_transit_ring(fig, transit_positions)
    _add_house_cusps(fig, house_cusps)
    _add_axis_lines(fig, axis_longitudes)
    _add_aspect_lines(fig, aspects, positions, axis_longitudes, aspect_colors=aspect_colors)
    _add_position_markers(fig, positions, radius=0.6, color="#111111", legend_label="")
    return fig


def build_synastry_figure(positions1: dict, positions2: dict, name1: str, name2: str) -> go.Figure:
    """Build a two-subject overlay (synastry) chart on a shared zodiac ring.

    Subject 1's planets render at the outer ring in black; subject 2's at an
    inner ring in blue, so the two sets stay visually distinct on hover.
    """
    fig = _build_base_ring()
    _add_position_markers(fig, _canonical_positions(positions1), radius=0.6, color="#111111", legend_label=name1)
    _add_position_markers(fig, _canonical_positions(positions2), radius=0.45, color="#1f5fbf", legend_label=name2)
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


def write_plotly_svg(fig: go.Figure, tmpname: str = "radix_chart.svg") -> str:
    """Write a Plotly figure to a static SVG file (via kaleido) and return its absolute path.

    Parameters:
    - fig: Plotly Figure to export
    - tmpname: filename to use within the system temporary directory
    """
    tmpdir = Path(tempfile.gettempdir())
    out_path = tmpname if isinstance(tmpname, Path) else tmpdir / tmpname
    fig.write_image(str(out_path), format="svg")
    return str(out_path)
