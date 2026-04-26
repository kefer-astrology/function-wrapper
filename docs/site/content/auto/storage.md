---

title: storage Module

description: documentation for storage module

weight: 10

---


# `storage` module

DuckDB and Parquet storage helpers for computed astrological data.

This module provides optional storage functionality for Python to write
computed positions and aspects directly to DuckDB/Parquet, avoiding
large JSON transfers for batch operations like transit series.

Usage:
    from module.storage import DuckDBStorage
    
    storage = DuckDBStorage('/path/to/workspace/data/workspace.db')
    storage.store_positions(chart_id, datetime, positions, engine='jpl')
    
    # Optimized batch computation
    storage.compute_and_store_series(
        chart_id='transit_base',
        start_datetime=start_dt,
        end_datetime=end_dt,
        time_step=timedelta(minutes=1),
        location=location,
        engine='jpl',
        requested_objects=['sun', 'moon', ...],
        include_physical=True,
        include_topocentric=True
    )

## Functions

## `get_storage_path`

```python
get_storage_path(workspace_path: str | pathlib.Path) -> pathlib.Path
```

Get DuckDB storage path for a workspace.

#### Parameters

- **workspace_path**: Path to workspace.yaml


#### Returns

Path to workspace.db in data/ directory

## Classes

### class `DuckDBStorage` 

DuckDB storage for computed astrological data.

Provides methods to store positions and aspects directly in DuckDB,
avoiding large JSON transfers for batch operations.

#### Methods

- `close(self)`
  
  Close database connection.

- `compute_and_store_series(self, chart_id: str, start_datetime: datetime.datetime, end_datetime: datetime.datetime, time_step: datetime.timedelta, location: 'Location', engine: str = 'swisseph', ephemeris_file: str | None = None, requested_objects: List[str] | None = None, include_physical: bool = False, include_topocentric: bool = False, batch_size: int = 1000, radix_chart_id: str | None = None) -> int`
  
  Optimized: Compute and store time series with pre-initialized engines.

- `compute_aspects_from_positions(self, chart_id: str, datetime_str: str | None = None, aspect_definitions: List[Dict[str, float]] | None = None, max_orb: float = 10.0)`
  
  Compute aspects from stored positions using SQL.

- `export_to_parquet(self, output_dir: str | pathlib.Path, chart_id: str | None = None, partition_by_date: bool = True, partition_by_hour: bool = False, compression: str = 'snappy') -> List[pathlib.Path]`
  
  Export positions to Parquet files.

- `query_positions(self, chart_id: str | None = None, start_datetime: str | datetime.datetime | None = None, end_datetime: str | datetime.datetime | None = None, object_id: str | None = None, use_parquet: bool | None = None, parquet_dir: str | pathlib.Path | None = None, auto_route: bool = True)`
  
  Query positions with optional Parquet fallback and smart routing.

- `query_radix_relative_positions(self, transit_chart_id: str, radix_chart_id: str, datetime_str: str | None = None, start_datetime: str | datetime.datetime | None = None, end_datetime: str | datetime.datetime | None = None)`
  
  Query transit positions relative to radix positions.

- `store_positions(self, chart_id: str, datetime_str: str, positions: Dict[str, float | Dict[str, float]], engine: str | None = None, ephemeris_file: str | None = None, radix_chart_id: str | None = None) -> None`
  
  Store computed positions in DuckDB.

- `store_positions_batch(self, chart_id: str, positions_list: List[tuple], engine: str | None = None, ephemeris_file: str | None = None, auto_export_parquet: bool = True, parquet_threshold: int = 100, parquet_dir: str | pathlib.Path | None = None) -> List[pathlib.Path] | None`
  
  Store multiple positions in batch (for transit series).

- `store_radix_positions(self, radix_chart_id: str, datetime_str: str, positions: Dict[str, float | Dict[str, float]], engine: str | None = None, ephemeris_file: str | None = None) -> None`
  
  Store radix (base chart) positions.
