# Ephemeris files

## Default file: de440s.bsp

The default JPL ephemeris was upgraded from `de421.bsp` to `de440s.bsp`.

`default_ephemeris_path()` in `module/utils.py` resolves the file in this order:

```python
source/de440s.bsp   # preferred
source/de421.bsp    # legacy fallback
```

The old `de421.bsp` remains in `source/` as a fallback for environments that have not yet received `de440s.bsp`. Once `de440s.bsp` is present, it is used automatically — no configuration change needed.

---

## What de440s actually provides

`de440s.bsp` contains the same set of **queryable bodies** as `de421.bsp`:

| Body | NAIF ID |
|------|---------|
| Sun | 10 |
| Moon | 301 |
| Mercury | 199 |
| Venus | 299 |
| Earth | 399 |
| Mars | 499 |
| Jupiter barycenter | 5 |
| Saturn barycenter | 6 |
| Uranus barycenter | 7 |
| Neptune barycenter | 8 |
| Pluto barycenter | 9 |

**The 343 asteroids integrated in DE440/441 are integration perturbers only.**
Their gravitational effects are baked into the planetary positions, but their own trajectories are **not stored as queryable SPK segments** in any of the DE planetary BSP files.
Querying Ceres (NAIF `2000001`) from `de440s.bsp` will raise a Skyfield `ValueError` — a dedicated asteroid SPK kernel is required (see below).

Why upgrade then? DE440 is a more accurate, more recent numerical solution (Park et al. 2021). For modern astrological dates it produces sub-arcsecond improvements over DE421, and it extends the reliable date range.

---

## Available BSP files and date ranges

| File | Size | Date range | Queryable bodies |
|------|------|-----------|-----------------|
| `de440s.bsp` | 32 MB | 1900 – 2050 | 10 planets + Moon |
| `de440.bsp` | 115 MB | 1550 – 2650 | 10 planets + Moon |
| `de441_part-1.bsp` | ~1.5 GB | −13 200 – 0 AD | 10 planets + Moon |
| `de441_part-2.bsp` | ~1.5 GB | 0 – 17 191 AD | 10 planets + Moon |
| `de421.bsp` | 17 MB | ~1899 – 2053 | 10 planets + Moon |

All files are publicly available from the NASA/JPL NAIF server:
`https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/`

---

## Date range overlaps

Some files cover the same epochs. This matters when choosing which file to load and when mixing files.

### Coverage map

```
              -13200       0     1550  1900   2050  2650       17191
                 │         │       │     │      │     │           │
de441_part-1  ───────────────┤      │     │      │     │           │
de441_part-2           │    ├───────────────────────────────────────┤
de440                  │    │       ├─────────────────────┤         │
de440s                 │    │       │     ├────────┤       │         │
de421 (~)              │    │       │     ├────────┤       │         │
```

### Overlap summary

| Pair | Overlapping range | Notes |
|------|-------------------|-------|
| de440s ∩ de441_part-2 | 1900 – 2050 | de440s is entirely inside de441_part-2 |
| de440 ∩ de441_part-2 | 1550 – 2650 | de440 is entirely inside de441_part-2 |
| de440s ∩ de440 | 1900 – 2050 | de440s is entirely inside de440 |
| de441_part-1 ∩ de440 | none | part-1 ends at year 0; de440 starts at 1550 |
| de441_part-1 ∩ de440s | none | same |
| de441_part-1 ∩ de421 | none | de421 starts ~1899 |

### Behaviour when overlapping files are loaded together

Skyfield (and the underlying SPICE convention) applies **last-loaded wins**: if two BSP files both contain a segment for the same body at the same time, the most recently loaded file takes effect.

```python
planets = load.open('de440s.bsp')     # loaded first
extended = load.open('de441_part-2.bsp')  # loaded last → wins for 1900-2050
```

For normal astrological work (1900–2050) this is acceptable: DE441 was derived from the same initial conditions as DE440 and the accuracy difference in the modern era is sub-arcsecond.

### When you need each file

| Use case | File |
|----------|------|
| Modern charts (1900–2050) | `de440s.bsp` — bundled, no download |
| Extended modern (1550–2650) | `de440.bsp` |
| Ancient / BC charts | `de441_part-1.bsp` |
| Far-future charts (after 2650) | `de441_part-2.bsp` |

You do **not** need `de441_part-2.bsp` for charts in the 1900–2050 window.

---

## is_de421 flag in services.py

`services.py` inspects the loaded filename to decide whether to use barycenters for outer planets:

```python
is_de421 = eph_file and "de421" in Path(eph_file).name.lower()
```

`de440s.bsp` does not match this check, so it follows the non-de421 path: direct planet names are tried first (`jupiter`, `saturn`, etc.) rather than barycenters. This is correct for DE440-series files, which expose individual planet objects directly.

No code change is needed in `services.py` when switching from `de421` to `de440s`.

---

## Asteroid bodies

### Current status

Asteroids (Ceres, Pallas, Juno, Vesta, Chiron) are **not available** from any of the DE planetary files. A dedicated asteroid SPK kernel is required:

| Option | Bodies | Source |
|--------|--------|--------|
| Individual files (`ceres_1900_2100.bsp` etc.) | one body per file | NAIF archive |
| `codes_300ast_20100725.bsp` (59 MB) | 300 main-belt asteroids | NAIF archive |
| JPL Horizons REST API | any numbered asteroid | on-demand query |

NAIF IDs for the main astrological asteroids:

| Body | NAIF ID |
|------|---------|
| Ceres | 2 000 001 |
| Pallas | 2 000 002 |
| Juno | 2 000 003 |
| Vesta | 2 000 004 |
| Chiron | 2 000 060 |

These are **not** in `de440s.bsp` despite the 343-asteroid integration — those asteroids improve planetary accuracy as perturbers but are not output as SPK segments.

### Workaround for computed points

- **Part of Fortune** — pure formula: `ASC + Moon - Sun` (day chart) or `ASC + Sun - Moon` (night chart); no BSP needed
- **Black Moon Lilith** — mean lunar apogee; derivable from Moon orbital elements
- **South Node** — North Node + 180°; already computed from the Mean Node formula

---

## Overriding the ephemeris file

Pass `ephemeris_path` explicitly to `compute_jpl_positions()` or set `chart.config.override_ephemeris`:

```python
from module.services import compute_jpl_positions

result = compute_jpl_positions(
    name="Test",
    dt_str="2000-01-01 12:00:00",
    loc_str="51.4779,0.0",
    ephemeris_path="/path/to/de441_part-2.bsp"
)
```

If `ephemeris_path` is `None`, `default_ephemeris_path()` is called, which returns `de440s.bsp` if present, otherwise `de421.bsp`.
