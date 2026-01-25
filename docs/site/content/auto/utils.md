---

title: utils Module

description: documentation for utils module

weight: 10

---


# `utils` module

## Functions

## `combine_date_time`

```python
combine_date_time(input_date: datetime.date, input_time: datetime.time) -> datetime.datetime
```

Combine a date and time into a naive datetime (no timezone).

#### Parameters

- **input_date**: Date object

- **input_time**: Time object


#### Returns

Naive datetime combining date and time

## `compute_vernal_equinox_offset`

```python
compute_vernal_equinox_offset(year: int, eph, observer, ts) -> float
```

Compute the vernal equinox offset for tropical astrology adjustment.

#### Parameters

- **year**: The year to compute the vernal equinox for

- **eph**: Skyfield ephemeris object

- **observer**: Skyfield Topos observer object

- **ts**: Skyfield timescale object


#### Returns

The ecliptic longitude offset in degrees [0, 360)

## `default_ephemeris_path`

```python
default_ephemeris_path() -> str
```

Return the default path to the local JPL ephemeris file.

#### Returns

Absolute path to de421.bsp file in source/ directory

## `ensure_aware`

```python
ensure_aware(dt: datetime.datetime, tz_name: Optional[str] = None) -> datetime.datetime
```

Return a timezone-aware datetime.

#### Parameters

- **dt**: Datetime to make timezone-aware

- **tz_name**: Optional timezone name for localization, defaults to UTC


#### Returns

Timezone-aware datetime. If dt is already aware, returns unchanged.
    If tz_name provided, localizes to that timezone. Otherwise uses UTC.

## `expand_range`

```python
expand_range(center: datetime.datetime, days: int) -> module.models.DateRange
```

Create a DateRange centered on a datetime extending days on both sides.

#### Parameters

- **center**: Center datetime for the range

- **days**: Number of days to extend on each side


#### Returns

DateRange from (center - days) to (center + days)

## `export_chart_yaml`

```python
export_chart_yaml(chart: module.models.ChartInstance, dest_dir: str) -> str
```

Export a ChartInstance as YAML into dest_dir.

#### Parameters

- **chart**: ChartInstance to export

- **dest_dir**: Destination directory for YAML file


#### Returns

Absolute file path to exported YAML file

## `export_workspace_yaml`

```python
export_workspace_yaml(ws: module.models.Workspace, dest_path: Union[str, pathlib._local.Path]) -> pathlib._local.Path
```

Export a Workspace as YAML to dest_path.

#### Parameters

- **ws**: Workspace instance to export

- **dest_path**: Destination file path


#### Returns

Resolved Path to exported YAML file


#### Notes

Uses the local serializer to convert dataclasses, enums, and datetimes
    to primitives. Ensures parent directory exists.

## `find_vernal_equinox_datetime`

```python
find_vernal_equinox_datetime(year: int) -> datetime.datetime
```

Find the approximate datetime of the vernal equinox for a given year.

#### Parameters

- **year**: The year to find the vernal equinox for


#### Returns

A timezone-aware UTC datetime for the approximate vernal equinox

## `import_chart_yaml`

```python
import_chart_yaml(path: str) -> module.models.ChartInstance
```

Read a chart YAML file from disk and parse into a ChartInstance.

#### Parameters

- **path**: Path to chart YAML file


#### Returns

ChartInstance parsed from YAML file

## `in_range`

```python
in_range(dt: datetime.datetime, dr: module.models.DateRange) -> bool
```

Check if datetime lies within the inclusive DateRange.

#### Parameters

- **dt**: Datetime to check

- **dr**: DateRange with start and end datetimes


#### Returns

True if dt is within [start, end] (inclusive), False otherwise

## `load_sfs_models_from_dir`

```python
load_sfs_models_from_dir(dir_path: Union[str, pathlib._local.Path]) -> Dict[str, module.models.AstroModel]
```

Scan a directory for StarFisher .sfs files and build AstroModel catalogs.

#### Parameters

- **dir_path**: Directory path to scan for .sfs files


#### Returns

Dictionary mapping model name (from file stem or parsed model.name) to AstroModel.
    Files that cannot be decoded or parsed are skipped.

## `location_equals`

```python
location_equals(loc1: module.models.Location, loc2: module.models.Location) -> bool
```

Check approximate equality of two Location objects.

#### Parameters

- **loc1**: First location to compare

- **loc2**: Second location to compare


#### Returns

True if locations are approximately equal, False otherwise

## `location_from_coords`

```python
location_from_coords(lat: float, lon: float, name: str = '') -> module.models.Location
```

Build a Location from raw coordinates, inferring timezone via TimezoneFinder.

#### Parameters

- **lat**: Latitude in degrees

- **lon**: Longitude in degrees

- **name**: Optional location name, defaults to coordinate string


#### Returns

Location instance with inferred timezone

## `now_utc`

```python
now_utc() -> datetime.datetime
```

Return current time as a timezone-aware UTC datetime.

## `parse_chart_yaml`

```python
parse_chart_yaml(data: dict) -> module.models.ChartInstance
```

Construct a ChartInstance from a YAML-mapped dict with safe coercions.

#### Parameters

- **data**: Dictionary containing chart data (subject, config, id, tags)


#### Returns

ChartInstance with parsed subject and config


#### Notes

Removes 'computed_chart' if present (it's recomputable and shouldn't be loaded from YAML)


#### Warnings

⚠️ ValueError: If subject data is invalid

## `parse_sfs_content`

```python
parse_sfs_content(content: str) -> Tuple[module.models.AstroModel, Dict[str, Any]]
```

Parse the content of a StarFisher .sfs file and map to AstroModel.

#### Parameters

- **content**: String content of the .sfs file


#### Returns

Tuple of (AstroModel, display_config_dict) where display_config_dict
    contains display-related settings from the .sfs file

## `parse_yaml_content`

```python
parse_yaml_content(data: Union[str, bytes]) -> dict
```

Parse YAML from a string or bytes and return a dict.

#### Parameters

- **data**: YAML content as string or bytes


#### Returns

Parsed YAML as dictionary, or empty dict if empty/invalid


#### Notes

Useful for handling uploaded files or in-memory YAML content uniformly.

## `prepare_horoscope`

```python
prepare_horoscope(name: str = '', dt: datetime.datetime = None, loc: module.models.Location = None, engine: Optional[module.models.EngineType] = None, ephemeris_path: Optional[str] = None, zodiac: module.models.ZodiacType = <ZodiacType.TROPICAL: 'Tropical'>, house: module.models.HouseSystem = <HouseSystem.PLACIDUS: 'Placidus'>) -> module.models.ChartInstance
```

Create a ChartInstance with basic configuration.

#### Parameters

- **name**: Chart subject name

- **dt**: Event datetime

- **loc**: Location for the chart

- **engine**: Optional computation engine

- **ephemeris_path**: Optional path to ephemeris file

- **zodiac**: Zodiac type, defaults to TROPICAL

- **house**: House system, defaults to PLACIDUS


#### Returns

ChartInstance with configured ChartSubject and ChartConfig

## `read_yaml_file`

```python
read_yaml_file(path: Union[str, pathlib._local.Path]) -> dict
```

Read a YAML file and return a dict.

#### Parameters

- **path**: Path to YAML file


#### Returns

Parsed YAML content as dictionary, or empty dict if file is empty


#### Notes

This is a thin wrapper around yaml.safe_load that always returns a dict.

## `resolve_under_base`

```python
resolve_under_base(base: Union[str, pathlib._local.Path], rel_path: Union[str, pathlib._local.Path]) -> pathlib._local.Path
```

Resolve rel_path against base and ensure the result stays within base.

#### Parameters

- **base**: Base directory path

- **rel_path**: Relative path to resolve


#### Returns

Resolved Path that is contained within base


#### Warnings

⚠️ ValueError: If path is absolute or attempts directory traversal outside base

### `to_timezone`

```python
resolve_user_path(path: Union[str, pathlib._local.Path], *, base_dir: Union[str, pathlib._local.Path, NoneType] = None) -> pathlib._local.Path
```

Resolve a user-provided path safely.

## `to_timezone`

```python
to_timezone(dt: datetime.datetime, tz_name: str) -> datetime.datetime
```

Convert a timezone-aware datetime to the target timezone by name.

#### Parameters

- **dt**: Timezone-aware datetime to convert

- **tz_name**: Target timezone name (e.g., "UTC", "Europe/Prague")


#### Returns

Datetime converted to target timezone

## `write_json_file`

```python
write_json_file(path: Union[str, pathlib._local.Path], data: dict, *, indent: int = 2) -> None
```

Write a dict to a JSON file.

#### Parameters

- **path**: Destination file path

- **data**: JSON-serializable data

- **indent**: Indentation level, defaults to 2


#### Notes

Ensures parent directory exists before writing.

## `write_yaml_file`

```python
write_yaml_file(path: Union[str, pathlib._local.Path], data: dict, *, sort_keys: bool = False, allow_unicode: bool = True) -> None
```

Write a dict to a YAML file using yaml.safe_dump.

#### Parameters

- **path**: Destination file path

- **data**: Dictionary to write

- **sort_keys**: Whether to sort keys in output, defaults to False

- **allow_unicode**: Whether to allow unicode characters, defaults to True


#### Notes

Ensures parent directory exists. Callers should pass already-serialized
    primitives (e.g., via a to_primitive function) if the input data contains
    dataclasses, enums, or datetime objects.

## Classes

### class `Actual` 

Universal holder for either a place or time object.
Useful for normalizing user input and controlling shiftable dimensions in astrology.

#### Methods

- `add_time(self, delta: Union[int, datetime.timedelta, str]) -> None`

- `assign_timezone(self, tz: Optional[str] = None) -> None`

- `to_model_location(self) -> Optional[module.models.Location]`
