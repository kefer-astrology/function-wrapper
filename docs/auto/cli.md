---

title: cli Module

description: API documentation for cli module

weight: 10

---


# `cli` module

CLI interface for Tauri frontend integration.

This module provides a JSON-based command interface that can be called
from the Tauri application via subprocess. All commands read JSON from
stdin or command-line arguments and output JSON to stdout.

Usage:
    python -m module.cli &lt;command&gt; [args_json]
    
Commands:
- compute_chart: Compute positions and aspects for a chart
- compute_transit_series: Compute transit series for a time range
- get_workspace_settings: Get workspace settings and defaults
- list_charts: List all charts in workspace
- get_chart: Get chart details by ID
- sync_workspace: Synchronize workspace manifest with files on disk
- export_parquet: Export stored positions to Parquet files
    
Storage:
- DuckDB database: workspace_dir/data/workspace.db
- Parquet files: workspace_dir/data/parquet/*.parquet
- Enable storage: Set store_in_db=True in compute_chart args

## Functions

## `cmd_compute_chart`

```python
cmd_compute_chart(args: Dict[str, Any]) -> Dict[str, Any]
```

Compute positions and aspects for a chart.

#### Parameters

- **workspace_path**: Path to workspace.yaml

- **chart_id**: Chart ID to compute

- **include_physical**: Include extended physical properties (JPL only, default: False)

- **include_topocentric**: Include altitude/azimuth (JPL with location, default: False)

- **store_in_db**: If True, store results in DuckDB (default: False)


#### Returns

Dict with keys:
        - positions: Dict mapping object_id -&gt; position data
        - aspects: List of aspect dictionaries
        - chart_id: Chart ID
        - stored: True if stored in DuckDB, False otherwise

## `cmd_compute_transit_series`

```python
cmd_compute_transit_series(args: Dict[str, Any]) -> Dict[str, Any]
```

Compute transit series for a time range.

#### Parameters

- **workspace_path**: Path to workspace.yaml

- **source_chart_id**: Base chart ID

- **start_datetime**: Start time (ISO format)

- **end_datetime**: End time (ISO format)

- **time_step**: Step size (e.g., '1 second', '1 minute', '1 hour', '1 day')

- **transiting_objects**: Optional list of object IDs to compute

- **transited_objects**: Optional list of object IDs in source chart

- **aspect_types**: Optional list of aspect types to compute

- **include_physical**: Include extended physical properties (default: False)

- **include_topocentric**: Include altitude/azimuth (default: False)


#### Returns

Dict with transit series results

## `cmd_export_parquet`

```python
cmd_export_parquet(args: Dict[str, Any]) -> Dict[str, Any]
```

Export stored positions to Parquet files.

#### Parameters

- **workspace_path**: Path to workspace.yaml

- **chart_id**: Optional chart ID to export (if not provided, exports all)

- **output_dir**: Optional output directory (defaults to workspace/data/parquet)

- **partition_by_date**: If True, partition by date (default: True)


#### Returns

Dict with list of created Parquet file paths

## `cmd_get_chart`

```python
cmd_get_chart(args: Dict[str, Any]) -> Dict[str, Any]
```

Get chart details by ID.

#### Parameters

- **workspace_path**: Path to workspace.yaml

- **chart_id**: Chart ID


#### Returns

Dict with chart details

## `cmd_get_workspace_settings`

```python
cmd_get_workspace_settings(args: Dict[str, Any]) -> Dict[str, Any]
```

Get workspace settings and defaults.

#### Parameters

- **workspace_path**: Path to workspace.yaml


#### Returns

Dict with workspace settings

## `cmd_list_charts`

```python
cmd_list_charts(args: Dict[str, Any]) -> Dict[str, Any]
```

List all charts in workspace.

#### Parameters

- **workspace_path**: Path to workspace.yaml


#### Returns

Dict with list of chart summaries

## `cmd_sync_workspace`

```python
cmd_sync_workspace(args: Dict[str, Any]) -> Dict[str, Any]
```

Synchronize workspace manifest with files on disk.

#### Parameters

- **workspace_path**: Path to workspace.yaml

- **auto_import**: If True, import new charts/subjects found on disk (default: True)

- **auto_remove**: If True, remove references to missing files (default: False)


#### Returns

Dict with sync results

## `main`

```python
main()
```

Main CLI entry point.
