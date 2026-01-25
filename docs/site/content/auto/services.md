---

title: services Module

description: documentation for services module

weight: 10

---


# `services` module

## Functions

## `build_chart_instance`

```python
build_chart_instance(name: str, dt_str: str, loc_text: str, mode: module.models.ChartMode, ws: Optional[module.models.Workspace] = None, ephemeris_path: Optional[str] = None) -> module.models.ChartInstance
```

Build a ChartInstance using workspace defaults when provided.
- Resolves engine and house system from ws if available.
- Uses utils.prepare_horoscope to produce a fully-typed ChartInstance.

## `build_radix_figure_for_chart`

```python
build_radix_figure_for_chart(chart: module.models.ChartInstance, engine_override: Optional[module.models.EngineType] = None, ephemeris_path_override: Optional[str] = None, ws: Optional[ForwardRef('Workspace')] = None) -> Any
```

Extract positions from a ChartInstance's computed_chart and return a Plotly Figure ready to render.

#### Parameters

- **chart**: ChartInstance to compute positions for

- **engine_override**: Optional engine to use instead of chart's stored engine

- **ephemeris_path_override**: Optional ephemeris path to use instead of chart's stored path

- **ws**: Optional workspace for resolving observable objects defaults


#### Returns

Plotly Figure object ready for rendering

## `compute_aspects`

```python
compute_aspects(bodies: List[module.models.CelestialBody], aspect_defs: List[module.models.AspectDefinition]) -> List[module.models.Aspect]
```

Compute aspects between celestial bodies using provided definitions.

#### Parameters

- **bodies**: List of celestial bodies to compute aspects for

- **aspect_defs**: List of aspect definitions to use for detection


#### Returns

List of Aspect objects representing detected aspects

## `compute_aspects_for_chart`

```python
compute_aspects_for_chart(chart: module.models.ChartInstance, aspect_definitions: Optional[List[module.models.AspectDefinition]] = None, ws: Optional[ForwardRef('Workspace')] = None) -> List[Dict[str, Any]]
```

Compute aspects between celestial bodies in a chart.

#### Parameters

- **chart**: ChartInstance to compute aspects for

- **aspect_definitions**: List of aspect definitions (orbs, types) If None, uses chart.config.aspect_orbs or workspace defaults

- **ws**: Optional workspace for default aspect definitions


#### Returns

List of aspect dictionaries, each with:
    {
        'from': str,  # Source object ID (e.g., 'sun')
        'to': str,    # Target object ID (e.g., 'moon')
        'type': str,  # Aspect type: 'conjunction', 'sextile', 'square', 'trine', 'opposition'
        'angle': float,  # Actual angle between objects (degrees)
        'orb': float,    # Orb (deviation from exact aspect, degrees)
        'exact_angle': float,  # Exact aspect angle (0, 60, 90, 120, 180)
        'applying': bool,  # True if aspect is applying (getting closer)
        'separating': bool  # True if aspect is separating
    }

## `compute_jpl_positions`

```python
compute_jpl_positions(name: str, dt_str: str, loc_str: str, ephemeris_path: Optional[str] = None, requested_objects: Optional[List[str]] = None, include_physical: bool = False, include_topocentric: bool = False, extended: bool = False) -> Dict[str, Union[float, Dict[str, float]]]
```

Compute planetary positions using Skyfield JPL ephemerides.

#### Parameters

- **name**: subject name (human-readable; not used in computation)

- **dt_str**: datetime string (parsed by utils.Actual)

- **loc_str**: location string (parsed by utils.Actual)

- **ephemeris_path**: optional path to a local BSP file; falls back to default

- **requested_objects**: optional list of object IDs to compute

- **include_physical**: if True, include magnitude/phase/elongation (extended mode only)

- **include_topocentric**: if True, include altitude/azimuth (extended mode only)

- **extended**: if True, return extended format with distance/declination/RA


#### Returns

- Mapping planet -&gt; ecliptic longitude (float) or extended dict
- Empty dict if computation is unavailable

## `compute_positions`

```python
compute_positions(engine: Optional[module.models.EngineType], name: str, dt_str: str, loc_str: str, ephemeris_path: Optional[str] = None, requested_objects: Optional[List[str]] = None) -> Dict[str, Union[float, Dict[str, float]]]
```

Dispatch position computation based on engine.
- For EngineType.JPL, returns a dict of ecliptic longitudes using Skyfield and a local ephemeris file.
- For other or None, returns Kerykeion observable object longitudes (degrees) as a dict.

#### Parameters

- **engine**: Computation engine to use

- **name**: Subject name

- **dt_str**: Datetime string

- **loc_str**: Location string

- **ephemeris_path**: Optional path to ephemeris file

- **requested_objects**: Optional list of object IDs to compute (filters results)


#### Returns

Dict mapping object_id -&gt; ecliptic_longitude (degrees) or extended dict.
    Empty dict on error or if no positions found.


#### Warnings

⚠️ ValueError: If datetime or location cannot be parsed
    FileNotFoundError: If ephemeris file is specified but not found

## `compute_positions_for_chart`

```python
compute_positions_for_chart(chart: module.models.ChartInstance, ws: Optional[ForwardRef('Workspace')] = None, include_physical: bool = False, include_topocentric: bool = False) -> Dict[str, Union[float, Dict[str, float]]]
```

Compute positions using a ChartInstance's engine and ephemeris settings.
Uses chart.subject.event_time and chart.subject.location.name for location lookup.
Handles both ChartInstance objects and dict-like structures safely.

#### Parameters

- **chart**: ChartInstance to compute positions for

- **ws**: Optional workspace for resolving observable objects defaults

- **include_physical**: If True, include magnitude/phase/elongation (JPL only)

- **include_topocentric**: If True, include altitude/azimuth (JPL with location)


#### Returns

Dict mapping object_id -&gt; position data.
    Empty dict on error or if no positions found:
    - For non-JPL engines: float (longitude in degrees)
    - For JPL engine: dict with keys:
        - 'longitude': float (degrees) - always present
        - 'latitude': float (degrees) - if available
        - 'distance': float (AU) - always present for JPL
        - 'declination': float (degrees) - always present for JPL
        - 'right_ascension': float (degrees) - always present for JPL
        - 'altitude': float (degrees) - if include_topocentric and location available
        - 'azimuth': float (degrees) - if include_topocentric and location available
        - 'apparent_magnitude': float - if include_physical
        - 'phase_angle': float (degrees) - if include_physical
        - 'elongation': float (degrees) - if include_physical
        - 'light_time': float (seconds) - if include_physical
        - 'speed': float (degrees/day) - if available
        - 'retrograde': bool - if available


#### Warnings

⚠️ ValueError: If chart is missing required subject or location data

## `compute_positions_for_inputs`

```python
compute_positions_for_inputs(engine: Optional[module.models.EngineType], name: str, dt_str: str, loc_text: str, ephemeris_path: Optional[str] = None, requested_objects: Optional[List[str]] = None) -> Dict[str, float]
```

Thin wrapper over compute_positions to normalize/forward parameters from UI layers.

## `compute_subject`

```python
compute_subject(name: str, dt_str: str, loc_str: str, zodiac: str = 'Tropic') -> kerykeion.backword.AstrologicalSubject
```

Construct a Kerykeion AstrologicalSubject from strings.

#### Parameters

- **name**: Subject name (human-readable identifier)

- **dt_str**: Datetime string (parsed by utils.Actual)

- **loc_str**: Location string (parsed by utils.Actual)

- **zodiac**: Zodiac type, defaults to "Tropic"


#### Returns

AstrologicalSubject instance with computed positions

## `create_relation_svg`

```python
create_relation_svg(subject1: kerykeion.backword.AstrologicalSubject, subject2: kerykeion.backword.AstrologicalSubject, chart_type: str = 'Synastry') -> kerykeion.backword.KerykeionChartSVG
```

Create a Kerykeion SVG chart for relation/composite types.

#### Parameters

- **subject1**: First astrological subject

- **subject2**: Second astrological subject

- **chart_type**: Type of relation chart (e.g., "Synastry", "Composite"), defaults to "Synastry"


#### Returns

KerykeionChartSVG instance with generated SVG chart

## `extract_kerykeion_points`

```python
extract_kerykeion_points(obj: Any) -> pandas.core.frame.DataFrame
```

Extract KerykeionPointModel attributes from an object into a DataFrame.

#### Parameters

- **obj**: Object containing KerykeionPointModel attributes


#### Returns

DataFrame with one row per KerykeionPointModel attribute found

## `find_chart_by_name_or_id`

```python
find_chart_by_name_or_id(ws: Optional[module.models.Workspace], name_or_id: str) -> Optional[module.models.ChartInstance]
```

Find a chart in the workspace by subject name or chart ID.

#### Parameters

- **ws**: Workspace to search in

- **name_or_id**: Subject name or chart ID to search for


#### Returns

ChartInstance if found, None otherwise

## `get_active_model`

```python
get_active_model(ws: Optional[ForwardRef('Workspace')]) -> Optional[module.models.AstroModel]
```

Resolve the currently active AstroModel instance from a Workspace, if available.

#### Parameters

- **ws**: Workspace instance to get active model from


#### Returns

Active AstroModel instance, or None if no models available

## `list_open_view_rows`

```python
list_open_view_rows(ws: Optional[module.models.Workspace]) -> List[Dict[str, str]]
```

Produce table rows for Open view display.

#### Parameters

- **ws**: Workspace containing charts


#### Returns

List of dictionaries with keys: name, event_time, location, tags, search_text

## `merge_model_with_overrides`

```python
merge_model_with_overrides(model: module.models.AstroModel, overrides: Optional[module.models.ModelOverrides]) -> module.models.AstroModel
```

Return a new AstroModel with selective overrides applied.

#### Parameters

- **model**: Base AstroModel to apply overrides to

- **overrides**: Optional ModelOverrides containing override definitions


#### Returns

New AstroModel instance with overrides applied

## `resolve_effective_defaults`

```python
resolve_effective_defaults(ws: 'Workspace', model: Optional[module.models.AstroModel]) -> Dict[str, object]
```

Resolve effective defaults merging workspace overrides on top of AstroModel settings.

#### Parameters

- **ws**: Workspace containing default overrides

- **model**: Optional AstroModel with base settings


#### Returns

Dictionary with keys: house_system, bodies, aspects, standard_orb, engine,
    zodiac_type, ayanamsa, aspect_orbs, observable_objects

## `search_charts`

```python
search_charts(ws: Optional[module.models.Workspace], query: str) -> List[module.models.ChartInstance]
```

Search charts in workspace using case-insensitive text matching.

#### Parameters

- **ws**: Workspace to search in

- **query**: Search query string


#### Returns

List of ChartInstance objects matching the query

## Classes

### class `Subject` 

Lightweight wrapper around Kerykeion's AstrologicalSubject builder.

Usage:
- Call at_place() then at_time() to prepare `self.computed`.
- Use data() to extract names, degrees, and labels for plotting.

#### Methods

- `at_place(self, location: object) -> None`
  
  Set place from a free-text location or coordinates string.

- `at_time(self, time: str) -> None`
  
  Set event time from a free-text datetime string and build computed subject.

- `data(self)`
  
  Return (object_names, degrees, labels) extracted from computed planets list.

- `report(self)`
  
  Build a Kerykeion textual Report for the computed subject.
