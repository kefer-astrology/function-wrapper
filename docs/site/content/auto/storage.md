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
get_storage_path(workspace_path: Union[str, pathlib._local.Path]) -> pathlib._local.Path
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

- `compute_and_store_series(self, chart_id: str, start_datetime: datetime.datetime, end_datetime: datetime.datetime, time_step: datetime.timedelta, location: 'Location', engine: str = 'swisseph', ephemeris_file: Optional[str] = None, requested_objects: Optional[List[str]] = None, include_physical: bool = False, include_topocentric: bool = False, batch_size: int = 1000, radix_chart_id: Optional[str] = None) -> int`
  
  Optimized: Compute and store time series with pre-initialized engines.

- `compute_aspects_from_positions(self, chart_id: str, datetime_str: Optional[str] = None, aspect_definitions: Optional[List[Dict[str, float]]] = None, max_orb: float = 10.0)`
  
  Compute aspects from stored positions using SQL.

- `export_to_parquet(self, output_dir: Union[str, pathlib._local.Path], chart_id: Optional[str] = None, partition_by_date: bool = True, partition_by_hour: bool = False, compression: str = 'snappy') -> List[pathlib._local.Path]`
  
  Export positions to Parquet files.

- `query_positions(self, chart_id: Optional[str] = None, start_datetime: Union[str, datetime.datetime, NoneType] = None, end_datetime: Union[str, datetime.datetime, NoneType] = None, object_id: Optional[str] = None, use_parquet: Optional[bool] = None, parquet_dir: Union[str, pathlib._local.Path, NoneType] = None, auto_route: bool = True)`
  
  Query positions with optional Parquet fallback and smart routing.

- `query_radix_relative_positions(self, transit_chart_id: str, radix_chart_id: str, datetime_str: Optional[str] = None, start_datetime: Union[str, datetime.datetime, NoneType] = None, end_datetime: Union[str, datetime.datetime, NoneType] = None)`
  
  Query transit positions relative to radix positions.

- `store_positions(self, chart_id: str, datetime_str: str, positions: Dict[str, Union[float, Dict[str, float]]], engine: Optional[str] = None, ephemeris_file: Optional[str] = None, radix_chart_id: Optional[str] = None) -> None`
  
  Store computed positions in DuckDB.

- `store_positions_batch(self, chart_id: str, positions_list: List[tuple], engine: Optional[str] = None, ephemeris_file: Optional[str] = None, auto_export_parquet: bool = True, parquet_threshold: int = 100, parquet_dir: Union[str, pathlib._local.Path, NoneType] = None) -> Optional[List[pathlib._local.Path]]`
  
  Store multiple positions in batch (for transit series).

- `store_radix_positions(self, radix_chart_id: str, datetime_str: str, positions: Dict[str, Union[float, Dict[str, float]]], engine: Optional[str] = None, ephemeris_file: Optional[str] = None) -> None`
  
  Store radix (base chart) positions.
