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
| Mars barycenter | 4 |
| Jupiter barycenter | 5 |
| Saturn barycenter | 6 |
| Uranus barycenter | 7 |
| Neptune barycenter | 8 |
| Pluto barycenter | 9 |

Unlike `de421.bsp`, `de440s.bsp` has **no direct `499 MARS` segment** — only `4 MARS_BARYCENTER`. `module/services.py`'s barycenter-fallback list (`outer_planets` in `_compute_single_planet_position`/`compute_jpl_positions`) includes `"mars"` for exactly this reason; the barycenter/body-center offset is negligible for ecliptic longitude.

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

`de440s.bsp` does not match this check, so it follows the non-de421 path: direct planet names are tried first (`mercury`, `venus`, etc.), falling back to `"{planet} barycenter"` on `KeyError` for any planet in the barycenter-fallback list (which includes Mars — see above — plus Jupiter/Saturn/Uranus/Neptune/Pluto).

No code change is needed in `services.py` when switching from `de421` to `de440s`.

---

## Asteroid bodies (Chiron, Ceres, Pallas, Juno, Vesta)

These are **not available** from any DE planetary BSP file — the 343 asteroids integrated in DE440/441 are integration perturbers only, not output as queryable SPK segments (see above).

Rather than adding a dedicated asteroid SPK kernel (`codes_300ast_20100725.bsp` or per-body files), these five bodies are computed via **MPC orbital elements** (Keplerian propagation), avoiding both kerykeion/pyswisseph and any extra multi-MB kernel:

- `source/mpc_bodies.dat` vendors the 5 relevant raw rows from MPC's `MPCORB.DAT` catalog (packed fixed-width format, ~1KB — not gitignored like the `.bsp` files, since it's tiny and not independently redownloadable at build time).
- `module/services.py::_load_mpc_orbits()` parses them via `skyfield.data.mpc.load_mpcorb_dataframe`/`mpc.mpcorb_orbit`, producing a heliocentric Kepler orbit per body, cached at module scope.
- `compute_jpl_positions()` builds each body as `eph["sun"] + orbit` and feeds it through the same `_compute_planet_ecliptic_longitude`/`_compute_planet_extended_position` pipeline used for the 10 classic planets — no separate extraction code.
- Regenerate the vendored elements (they're a snapshot, not live) with `python -m devtools.fetch_mpc_bodies`, which re-downloads the full `MPCORB.DAT.gz` (~90MB) once and extracts just these 5 rows.

### Black Moon Lilith (mean + true)

Same "no extra kernel needed" approach as the lunar nodes: `_mean_lilith_lon_deg()` (Meeus mean-perigee polynomial + 180°) and `_true_lilith_tropical_deg()` (osculating apogee from the Moon's geocentric position/velocity vectors, via the eccentricity/Laplace-Runge-Lenz vector rather than the angular-momentum vector nodes use) — both in `module/services.py`, next to the equivalent node functions.

### Other computed points

- **Part of Fortune** — pure formula: `ASC + Moon - Sun` (day chart) or `ASC + Sun - Moon` (night chart); no BSP needed
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
