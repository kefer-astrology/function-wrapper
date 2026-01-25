## Overview

The architecture separates UI, computation, workspace management, and storage so multiple frontends can share the same backend behavior.

## Repository Structure (top level)

- cache: temporary files for computation
- module: all the program logic
- scripts: generators for documentation
- tests: scenario and functionality testing
- venv: python environment with libraries

## Core Layers

- **UI layer**: Streamlit, Kivy, or Tauri/Svelte call Python services directly.
- **Services layer**: `module.services` computes positions/aspects and builds charts.
- **Workspace layer**: `module.workspace` loads/saves modular YAML workspaces.
- **Storage layer**: `module.storage` persists positions to DuckDB and Parquet (positions-only).

## Data Flow

1. UI collects inputs and opens a workspace.
2. Services compute positions (and aspects on demand).
3. Storage writes positions to DuckDB and/or Parquet.
4. UI renders charts from computed positions.

## Storage Model

- **Positions-only**: aspects are computed on demand.
- **Dual engines**: Kerykeion (fast) and JPL/Skyfield (extended properties).
- **Radix support**: `radix_chart_id` + `is_radix` for transit comparisons.
- **Hybrid storage**: DuckDB for active queries, Parquet for time series.

## Storage (Backend)

### Strategy (Python vs Rust)

**Python storage** (batch):
- Transit series and large time ranges
- Background jobs and data migrations
- Avoids JSON transfer overhead

**Rust storage** (interactive):
- Single chart computations
- User-driven queries
- Small datasets and quick updates

Both Python and Rust use the same DuckDB schema.

### Schema (Positions-Only)

`computed_positions` stores:
- `chart_id`, `datetime`, `object_id`
- `longitude`, `latitude`
- `declination`, `right_ascension`, `distance`
- `altitude`, `azimuth`
- `apparent_magnitude`, `phase_angle`, `elongation`, `light_time`
- `speed`, `retrograde`
- `engine`, `ephemeris_file`
- `radix_chart_id`, `is_radix`
- `has_equatorial`, `has_topocentric`, `has_physical`

Aspects are computed on demand from positions.

### Current behavior

1. **Dual engine support**
   - Default: Kerykeion (Swisseph)
   - Optional: JPL (extended properties)

2. **Radix-relative storage**
   - `radix_chart_id` links transits to base charts
   - `is_radix` marks base vs transit rows

3. **Performance optimization**
   - Pre-initialized engine for batch series
   - No aspect storage (computed on demand)

4. **3D-ready fields**
   - `declination` and `distance` stored for JPL

### Storage paths

```
workspace/
├── workspace.yaml
└── data/
    ├── workspace.db
    └── parquet/
        └── chart_id_YYYY-MM-DD.parquet
```

## Layers by responsibility

| 🔹 Category       | 🌞 Horoscope | 📊 Chart | 🗂️ Workspace |
|------------------|--------------|----------|--------------|
| 🧱 Key Objects    | <ul><li>`Horoscope`</li><li>`CelestialBody`</li><li>`Aspect`</li><li>`House`</li></ul> | <ul><li>`ChartSubject`</li><li>`ChartInstance`</li><li>`ChartConfig`</li><li>`ChartPreset`</li></ul> | <ul><li>`Workspace`</li><li>`EphemerisSource`</li><li>`ModelOverrides`</li><li>`Annotation`</li></ul> |
| ⚙️ Core Functions | <ul><li>`compute_positions(...)`</li><li>`compute_aspects(...)`</li><li>`compute_positions_for_chart(...)`</li></ul> | <ul><li>`build_chart_instance(...)`</li><li>`prepare_horoscope(...)`</li></ul> | <ul><li>`load_workspace(...)`</li><li>`save_workspace_modular(...)`</li><li>`get_all_aspect_definitions(...)`</li></ul> |
| ✨ Features       | <ul><li>Immutable snapshot</li><li>Engine-specific (Western, Vedic, etc.)</li><li>Supports derived charts (e.g., progressed)</li><li>Custom points via overrides</li></ul> | <ul><li>Preset-driven config</li><li>Supports ChartMode (NATAL, TRANSIT, etc.)</li><li>Custom display and ephemeris override</li></ul> | <ul><li>Modular YAML structure</li><li>Per-user model customization</li><li>Annotations, media, layouts</li></ul> |

## Key entry points

- `module.services.compute_positions(...)`
- `module.services.compute_positions_for_chart(...)`
- `module.services.compute_aspects_for_chart(...)`
- `module.services.build_chart_instance(...)`
- `module.workspace.load_workspace(...)`
- `module.workspace.save_workspace_modular(...)`

## Schéma

[editor](https://mermaid.live/edit#pako:eNqtV0tv4zYQ_iuCrk0CO04Tx4cCaRKgBbJosV60wMKAQEtjmY1ECiSVXceIf3uHFEVSlJLuoSeRHHIe3zx1THNeQLpK84pI-UBJKUi9YRtm9snfXDzLhuSQHDcsSX6SSiT8GwNhdo_NHmoQVK55K_BOATvSViqD_ty9IbmiL5DVKKsyh09UqtP9ngj1pwAJ6pTkepM1ZiejO-t2-w_keEl2i5j-O5OKsBwsl4D8F4VvT-TAW3xcmW9AvGOMK6IoZ6eEuHV34ZNW9Y8XEIIWIBOjecb7vblyh5Zxcy8hetmb9-bxCywMEGSkBrMx5HvOdrRMcvMZvI7xneCgN1uSPwMrxoItbME7WoxZFESBojUk8AJMZXrZQcRzg0dS2cVYgFX96I3RcBiwzNFvvJWwPkgFdbLX60yajSF-5QUl-ZdDA8mrWWYK1947qOQpoSiuLaDIGk6Z9d0DzQ31bFdxgn4lskErMy62PuAKKhv0dybVofJI5bziIlMaVR_O1qcTUevD9ZGVlIHRFcyyC4ADQRQlSYhdjBHqI3Psg4GHbFy_GxQGS8FlzlGDnNdNqxATE-wDmf7Scejbnbb7A8-6dIIKpKKk-pUXh1OyRcdAkDHGoafOl2EiGQ_0npBDGEKO06GIdYMyqhXJ7KnxLJ6XArynJC07TbecV4kATDmsVjbUuhcoH4oIEVTVisUISlhbb2356p7krWyySUkBl87AQHsXqua6Sc8ssEgRUYIaWkNYWYW6YrxGMlw5mUh0g7OG8MGBZdxzyDx6I4-Ed22WTN5eo70nY3VQ_NagFGWlTKRdfJAJH-Tyx0kytGg6PMrq0OzdDiO5bivi9hheNdatEOiXMrOB4M5q8j0zgIf1o6sw8-WUr39cqWnv9r3wB4VqD7xX34f2k-1WwAv1eRuD8B-Shr49jup0r_ioXvui3F9x6T5JDWqHTU6shAURRRZHftRrj55hf_jIlMByFDSBKXKoT9wkXJnv2kQgfcDk_3G2B4Oz6pBhyL7rmb6c9UV9oJqfXiZLgqGsdYezs03Q7rwK3WBFbSOKR6fPUNkJSNhVND2hc9oKa35tvnLc4noOVsV-a4rBRJmMaqRvtqD2vIP8AbvWZ8QY32PLwlwmbARLp5aV6Q-GUjXgU4OVH_zCkk7VYFRgqs8o10VzAUSBjwvSos5iyFopku91Mgasd7SCQUq3oopaScDCtecJn3fxphFW7aDzVRyrsTvr7KnhlbMhbw9tNCBgdIjIWj9T-t-A8_NfwqF2krTuh5kJWj8PxUQf6THF-yqmDMvG6J1rpzElGqu1gcNZbWzJO_R7G1pjshvENHc_lZmX4UAUE00ljg-7jqQ5BTOCJgy754gcd7LRhbWZc6LDQYPQQoMq5Czvs3xE9aloYXHlQVNd-FliP_9q2pMbRsMJ2En8ZH4qYlLQucZEP5WMaX6OGdPu3KSSnqUlRle6UqKFsxSjpiZ6m5rs2aTdr0S6wiV2tudNigmDb7BgfeW87p8J3pb7dLUjlcRd2-gMs7_a_RWsJHx9YLl7gskH4p63TKWr6_nC8ExXx_R7ujq_vbqYL25ub65vlpeX8-Xy6iw9pKvF8mJ5OZ9d3s4Wi_n1_Obnt7P01Wgxv5gtrq6ub_H6Yjm7mc2Wb_8CtUrF3A)

[![](https://mermaid.ink/img/pako:eNqtV0tv4zYQ_iuCrk0CO04Tx4cCaRKgBbJosV60wMKAQEtjmY1ECiSVXceIf3uHFEVSlJLuoSeRHHIe3zx1THNeQLpK84pI-UBJKUi9YRtm9snfXDzLhuSQHDcsSX6SSiT8GwNhdo_NHmoQVK55K_BOATvSViqD_ty9IbmiL5DVKKsyh09UqtP9ngj1pwAJ6pTkepM1ZiejO-t2-w_keEl2i5j-O5OKsBwsl4D8F4VvT-TAW3xcmW9AvGOMK6IoZ6eEuHV34ZNW9Y8XEIIWIBOjecb7vblyh5Zxcy8hetmb9-bxCywMEGSkBrMx5HvOdrRMcvMZvI7xneCgN1uSPwMrxoItbME7WoxZFESBojUk8AJMZXrZQcRzg0dS2cVYgFX96I3RcBiwzNFvvJWwPkgFdbLX60yajSF-5QUl-ZdDA8mrWWYK1947qOQpoSiuLaDIGk6Z9d0DzQ31bFdxgn4lskErMy62PuAKKhv0dybVofJI5bziIlMaVR_O1qcTUevD9ZGVlIHRFcyyC4ADQRQlSYhdjBHqI3Psg4GHbFy_GxQGS8FlzlGDnNdNqxATE-wDmf7Scejbnbb7A8-6dIIKpKKk-pUXh1OyRcdAkDHGoafOl2EiGQ_0npBDGEKO06GIdYMyqhXJ7KnxLJ6XArynJC07TbecV4kATDmsVjbUuhcoH4oIEVTVisUISlhbb2356p7krWyySUkBl87AQHsXqua6Sc8ssEgRUYIaWkNYWYW6YrxGMlw5mUh0g7OG8MGBZdxzyDx6I4-Ed22WTN5eo70nY3VQ_NagFGWlTKRdfJAJH-Tyx0kytGg6PMrq0OzdDiO5bivi9hheNdatEOiXMrOB4M5q8j0zgIf1o6sw8-WUr39cqWnv9r3wB4VqD7xX34f2k-1WwAv1eRuD8B-Shr49jup0r_ioXvui3F9x6T5JDWqHTU6shAURRRZHftRrj55hf_jIlMByFDSBKXKoT9wkXJnv2kQgfcDk_3G2B4Oz6pBhyL7rmb6c9UV9oJqfXiZLgqGsdYezs03Q7rwK3WBFbSOKR6fPUNkJSNhVND2hc9oKa35tvnLc4noOVsV-a4rBRJmMaqRvtqD2vIP8AbvWZ8QY32PLwlwmbARLp5aV6Q-GUjXgU4OVH_zCkk7VYFRgqs8o10VzAUSBjwvSos5iyFopku91Mgasd7SCQUq3oopaScDCtecJn3fxphFW7aDzVRyrsTvr7KnhlbMhbw9tNCBgdIjIWj9T-t-A8_NfwqF2krTuh5kJWj8PxUQf6THF-yqmDMvG6J1rpzElGqu1gcNZbWzJO_R7G1pjshvENHc_lZmX4UAUE00ljg-7jqQ5BTOCJgy754gcd7LRhbWZc6LDQYPQQoMq5Czvs3xE9aloYXHlQVNd-FliP_9q2pMbRsMJ2En8ZH4qYlLQucZEP5WMaX6OGdPu3KSSnqUlRle6UqKFsxSjpiZ6m5rs2aTdr0S6wiV2tudNigmDb7BgfeW87p8J3pb7dLUjlcRd2-gMs7_a_RWsJHx9YLl7gskH4p63TKWr6_nC8ExXx_R7ujq_vbqYL25ub65vlpeX8-Xy6iw9pKvF8mJ5OZ9d3s4Wi_n1_Obnt7P01Wgxv5gtrq6ub_H6Yjm7mc2Wb_8CtUrF3A?type=png)](https://mermaid.live/edit#pako:eNqtV0tv4zYQ_iuCrk0CO04Tx4cCaRKgBbJosV60wMKAQEtjmY1ECiSVXceIf3uHFEVSlJLuoSeRHHIe3zx1THNeQLpK84pI-UBJKUi9YRtm9snfXDzLhuSQHDcsSX6SSiT8GwNhdo_NHmoQVK55K_BOATvSViqD_ty9IbmiL5DVKKsyh09UqtP9ngj1pwAJ6pTkepM1ZiejO-t2-w_keEl2i5j-O5OKsBwsl4D8F4VvT-TAW3xcmW9AvGOMK6IoZ6eEuHV34ZNW9Y8XEIIWIBOjecb7vblyh5Zxcy8hetmb9-bxCywMEGSkBrMx5HvOdrRMcvMZvI7xneCgN1uSPwMrxoItbME7WoxZFESBojUk8AJMZXrZQcRzg0dS2cVYgFX96I3RcBiwzNFvvJWwPkgFdbLX60yajSF-5QUl-ZdDA8mrWWYK1947qOQpoSiuLaDIGk6Z9d0DzQ31bFdxgn4lskErMy62PuAKKhv0dybVofJI5bziIlMaVR_O1qcTUevD9ZGVlIHRFcyyC4ADQRQlSYhdjBHqI3Psg4GHbFy_GxQGS8FlzlGDnNdNqxATE-wDmf7Scejbnbb7A8-6dIIKpKKk-pUXh1OyRcdAkDHGoafOl2EiGQ_0npBDGEKO06GIdYMyqhXJ7KnxLJ6XArynJC07TbecV4kATDmsVjbUuhcoH4oIEVTVisUISlhbb2356p7krWyySUkBl87AQHsXqua6Sc8ssEgRUYIaWkNYWYW6YrxGMlw5mUh0g7OG8MGBZdxzyDx6I4-Ed22WTN5eo70nY3VQ_NagFGWlTKRdfJAJH-Tyx0kytGg6PMrq0OzdDiO5bivi9hheNdatEOiXMrOB4M5q8j0zgIf1o6sw8-WUr39cqWnv9r3wB4VqD7xX34f2k-1WwAv1eRuD8B-Shr49jup0r_ioXvui3F9x6T5JDWqHTU6shAURRRZHftRrj55hf_jIlMByFDSBKXKoT9wkXJnv2kQgfcDk_3G2B4Oz6pBhyL7rmb6c9UV9oJqfXiZLgqGsdYezs03Q7rwK3WBFbSOKR6fPUNkJSNhVND2hc9oKa35tvnLc4noOVsV-a4rBRJmMaqRvtqD2vIP8AbvWZ8QY32PLwlwmbARLp5aV6Q-GUjXgU4OVH_zCkk7VYFRgqs8o10VzAUSBjwvSos5iyFopku91Mgasd7SCQUq3oopaScDCtecJn3fxphFW7aDzVRyrsTvr7KnhlbMhbw9tNCBgdIjIWj9T-t-A8_NfwqF2krTuh5kJWj8PxUQf6THF-yqmDMvG6J1rpzElGqu1gcNZbWzJO_R7G1pjshvENHc_lZmX4UAUE00ljg-7jqQ5BTOCJgy754gcd7LRhbWZc6LDQYPQQoMq5Czvs3xE9aloYXHlQVNd-FliP_9q2pMbRsMJ2En8ZH4qYlLQucZEP5WMaX6OGdPu3KSSnqUlRle6UqKFsxSjpiZ6m5rs2aTdr0S6wiV2tudNigmDb7BgfeW87p8J3pb7dLUjlcRd2-gMs7_a_RWsJHx9YLl7gskH4p63TKWr6_nC8ExXx_R7ujq_vbqYL25ub65vlpeX8-Xy6iw9pKvF8mJ5OZ9d3s4Wi_n1_Obnt7P01Wgxv5gtrq6ub_H6Yjm7mc2Wb_8CtUrF3A)
