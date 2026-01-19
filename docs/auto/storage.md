---

title: storage Module

description: API documentation for storage module

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
    storage.store_aspects(relation_id, datetime, aspects)

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

- `export_to_parquet(self, output_dir: Union[str, pathlib._local.Path], chart_id: Optional[str] = None, partition_by_date: bool = True) -> List[pathlib._local.Path]`
  
  Export positions to Parquet files.

- `store_aspects(self, relation_id: str, datetime_str: str, aspects: List[Dict[str, Any]]) -> None`
  
  Store computed aspects in DuckDB.

- `store_positions(self, chart_id: str, datetime_str: str, positions: Dict[str, Union[float, Dict[str, float]]], engine: Optional[str] = None, ephemeris_file: Optional[str] = None) -> None`
  
  Store computed positions in DuckDB.
