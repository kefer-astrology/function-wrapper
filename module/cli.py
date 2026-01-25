"""
CLI interface for Tauri frontend integration.

This module provides a JSON-based command interface that can be called
from the Tauri application via subprocess. All commands read JSON from
stdin or command-line arguments and output JSON to stdout.

Usage:
    python -m module.cli <command> [args_json]
    
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
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dateutil.parser import parse

try:
    from module.workspace import load_workspace
    from module.services import (
        compute_positions_for_chart,
        compute_aspects_for_chart,
        build_chart_instance,
        find_chart_by_name_or_id
    )
    from module.models import ChartMode, EngineType
    from module.utils import _to_primitive
    try:
        from module.storage import DuckDBStorage, get_storage_path
        STORAGE_AVAILABLE = True
    except ImportError:
        STORAGE_AVAILABLE = False
except ImportError:
    from workspace import load_workspace
    from services import (
        compute_positions_for_chart,
        compute_aspects_for_chart,
        build_chart_instance,
        find_chart_by_name_or_id
    )
    from models import ChartMode, EngineType
    from utils import _to_primitive
    try:
        from storage import DuckDBStorage, get_storage_path
        STORAGE_AVAILABLE = True
    except ImportError:
        STORAGE_AVAILABLE = False


def _json_output(result: Dict[str, Any]) -> None:
    """Output JSON result to stdout."""
    # Convert to primitives for JSON serialization
    json_result = _to_primitive(result)
    print(json.dumps(json_result, indent=None, ensure_ascii=False))
    sys.stdout.flush()


def _json_error(message: str, error_type: str = "Error") -> None:
    """Output JSON error to stdout."""
    _json_output({"error": message, "type": error_type})


def cmd_compute_chart(args: Dict[str, Any]) -> Dict[str, Any]:
    """Compute positions and aspects for a chart.
    
    Args:
        args: dict with keys:
            - workspace_path: Path to workspace.yaml
            - chart_id: Chart ID to compute
            - include_physical: Include extended physical properties (JPL only, default: False)
            - include_topocentric: Include altitude/azimuth (JPL with location, default: False)
            - store_in_db: If True, store results in DuckDB (default: False)
    
    Returns:
        Dict with keys:
            - positions: Dict mapping object_id -> position data
            - aspects: List of aspect dictionaries
            - chart_id: Chart ID
            - stored: True if stored in DuckDB, False otherwise
    """
    workspace_path = args.get('workspace_path')
    chart_id = args.get('chart_id')
    include_physical = args.get('include_physical', False)
    include_topocentric = args.get('include_topocentric', False)
    store_in_db = args.get('store_in_db', False)
    
    if not workspace_path:
        return {"error": "workspace_path is required", "type": "InvalidArgument"}
    if not chart_id:
        return {"error": "chart_id is required", "type": "InvalidArgument"}
    
    try:
        # Load workspace
        ws = load_workspace(workspace_path)
        
        # Find chart
        chart = find_chart_by_name_or_id(ws, chart_id)
        if not chart:
            return {"error": f"Chart {chart_id} not found", "type": "ChartNotFound"}
        
        # Compute positions
        positions = compute_positions_for_chart(
            chart, 
            ws=ws,
            include_physical=include_physical,
            include_topocentric=include_topocentric
        )
        
        # Compute aspects
        aspects = compute_aspects_for_chart(chart, ws=ws)
        
        # Optionally store in DuckDB
        stored = False
        if store_in_db and STORAGE_AVAILABLE:
            try:
                db_path = get_storage_path(workspace_path)
                with DuckDBStorage(db_path) as storage:
                    # Get datetime from chart
                    subj = getattr(chart, 'subject', None)
                    if subj:
                        event_time = getattr(subj, 'event_time', None)
                        if event_time:
                            if isinstance(event_time, datetime):
                                dt_str = event_time.isoformat()
                            else:
                                dt_str = str(event_time)
                            
                            # Get engine info
                            cfg = getattr(chart, 'config', None)
                            engine = _enum_value(cfg.engine) if cfg and cfg.engine else None
                            eph_file = cfg.override_ephemeris if cfg else None
                            
                            storage.store_positions(
                                chart_id,
                                dt_str,
                                positions,
                                engine=engine,
                                ephemeris_file=eph_file
                            )
                            stored = True
            except Exception as e:
                # Don't fail if storage fails, just log
                print(f"Warning: Failed to store in DuckDB: {e}", file=sys.stderr)
        
        return {
            "positions": positions,
            "aspects": aspects,
            "chart_id": chart_id,
            "stored": stored
        }
    except Exception as e:
        return {"error": str(e), "type": "ComputationError"}


def cmd_compute_transit_series(args: Dict[str, Any]) -> Dict[str, Any]:
    """Compute transit series for a time range.
    
    Args:
        args: dict with keys:
            - workspace_path: Path to workspace.yaml
            - source_chart_id: Base chart ID
            - start_datetime: Start time (ISO format)
            - end_datetime: End time (ISO format)
            - time_step: Step size (e.g., '1 second', '1 minute', '1 hour', '1 day')
            - transiting_objects: Optional list of object IDs to compute
            - transited_objects: Optional list of object IDs in source chart
            - aspect_types: Optional list of aspect types to compute
            - include_physical: Include extended physical properties (default: False)
            - include_topocentric: Include altitude/azimuth (default: False)
    
    Returns:
        Dict with transit series results
    """
    workspace_path = args.get('workspace_path')
    source_chart_id = args.get('source_chart_id')
    start_str = args.get('start_datetime')
    end_str = args.get('end_datetime')
    time_step = args.get('time_step', '1 hour')
    transiting_objects = args.get('transiting_objects')
    transited_objects = args.get('transited_objects')
    aspect_types = args.get('aspect_types')
    include_physical = args.get('include_physical', False)
    include_topocentric = args.get('include_topocentric', False)
    
    if not workspace_path:
        return {"error": "workspace_path is required", "type": "InvalidArgument"}
    if not source_chart_id:
        return {"error": "source_chart_id is required", "type": "InvalidArgument"}
    if not start_str:
        return {"error": "start_datetime is required", "type": "InvalidArgument"}
    if not end_str:
        return {"error": "end_datetime is required", "type": "InvalidArgument"}
    
    try:
        # Load workspace
        ws = load_workspace(workspace_path)
        
        # Find source chart
        source_chart = find_chart_by_name_or_id(ws, source_chart_id)
        if not source_chart:
            return {"error": f"Source chart {source_chart_id} not found", "type": "ChartNotFound"}
        
        # Parse time range
        start_dt = parse(start_str)
        end_dt = parse(end_str)
        
        # Parse time step
        def parse_time_step(step_str: str) -> timedelta:
            """Parse time step string like '1 second', '30 seconds', '1 minute', etc."""
            parts = step_str.lower().strip().split()
            if len(parts) < 2:
                return timedelta(hours=1)
            
            value = int(parts[0])
            unit = parts[1]
            
            if 'second' in unit:
                return timedelta(seconds=value)
            elif 'minute' in unit:
                return timedelta(minutes=value)
            elif 'hour' in unit:
                return timedelta(hours=value)
            elif 'day' in unit:
                return timedelta(days=value)
            else:
                return timedelta(hours=1)
        
        step_delta = parse_time_step(time_step)
        
        # Generate time points
        time_points = []
        current = start_dt
        while current <= end_dt:
            time_points.append(current)
            current += step_delta
        
        # Optionally use DuckDB storage for batch operations
        use_storage = STORAGE_AVAILABLE and len(time_points) > 10  # Use storage for large batches
        storage = None
        if use_storage:
            try:
                db_path = get_storage_path(workspace_path)
                storage = DuckDBStorage(db_path)
                # Create relation_id for transit series
                relation_id = f"transit_{source_chart_id}_{start_dt.date()}_{end_dt.date()}"
            except Exception as e:
                print(f"Warning: DuckDB storage not available: {e}", file=sys.stderr)
                use_storage = False
        
        # Compute positions for each timepoint
        results = []
        source_positions = compute_positions_for_chart(
            source_chart, 
            ws=ws,
            include_physical=include_physical,
            include_topocentric=include_topocentric
        )
        
        # Get engine info for storage
        cfg = getattr(source_chart, 'config', None)
        engine = _enum_value(cfg.engine) if cfg and cfg.engine else None
        eph_file = cfg.override_ephemeris if cfg else None
        
        for tp in time_points:
            # Create temporary transit chart
            # Extract location from source chart
            subj = getattr(source_chart, 'subject', None)
            loc = getattr(subj, 'location', None) if subj else None
            
            if loc:
                # Try to get location name, or construct from lat/lon
                loc_str = getattr(loc, 'name', '') if hasattr(loc, 'name') else ''
                if not loc_str:
                    # Try to construct from coordinates
                    lat = getattr(loc, 'latitude', None) if hasattr(loc, 'latitude') else None
                    lon = getattr(loc, 'longitude', None) if hasattr(loc, 'longitude') else None
                    if lat is not None and lon is not None:
                        loc_str = f"{lat},{lon}"
                    else:
                        # Fallback to workspace default location
                        if ws and ws.default:
                            loc_str = getattr(ws.default, 'location_name', '') or 'Prague'
                        else:
                            loc_str = 'Prague'
            else:
                # Fallback to workspace default location
                if ws and ws.default:
                    loc_str = getattr(ws.default, 'location_name', '') or 'Prague'
                else:
                    loc_str = 'Prague'
            
            transit_chart = build_chart_instance(
                name=f"transit_{source_chart_id}",
                dt_str=tp.isoformat(),
                loc_text=loc_str,
                mode=ChartMode.EVENT,
                ws=ws
            )
            
            # Compute transit positions
            transit_positions = compute_positions_for_chart(
                transit_chart,
                ws=ws,
                include_physical=include_physical,
                include_topocentric=include_topocentric
            )
            
            # Store positions only - aspects are computed on-demand from positions via SQL
            # This avoids duplication and allows flexible aspect computation
            if use_storage and storage:
                try:
                    storage.store_positions(
                        f"transit_{source_chart_id}",
                        tp.isoformat(),
                        transit_positions,
                        engine=engine,
                        ephemeris_file=eph_file
                    )
                except Exception as e:
                    print(f"Warning: Failed to store in DuckDB: {e}", file=sys.stderr)
            
            # Compute aspects for return value (not stored - can be recomputed from positions)
            transit_aspects = compute_aspects_for_chart(transit_chart, ws=ws)
            
            results.append({
                "datetime": tp.isoformat(),
                "transit_positions": transit_positions,
                "aspects": transit_aspects  # Returned but not stored
            })
        
        # Close storage if used
        if storage:
            storage.close()
        
        return {
            "source_chart_id": source_chart_id,
            "time_range": {
                "start": start_str,
                "end": end_str
            },
            "time_step": time_step,
            "results": results,
            "stored_in_db": use_storage
        }
    except Exception as e:
        return {"error": str(e), "type": "ComputationError"}


def cmd_get_workspace_settings(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get workspace settings and defaults.
    
    Args:
        args: dict with keys:
            - workspace_path: Path to workspace.yaml
    
    Returns:
        Dict with workspace settings
    """
    workspace_path = args.get('workspace_path')
    
    if not workspace_path:
        return {"error": "workspace_path is required", "type": "InvalidArgument"}
    
    try:
        ws = load_workspace(workspace_path)
        
        return {
            "owner": ws.owner,
            "active_model": ws.active_model,
            "default": {
                "ephemeris_engine": _enum_value(ws.default.ephemeris_engine) if ws.default.ephemeris_engine else None,
                "ephemeris_backend": ws.default.ephemeris_backend,
                "default_house_system": _enum_value(ws.default.default_house_system) if ws.default.default_house_system else None,
                "default_bodies": ws.default.default_bodies,
                "default_aspects": ws.default.default_aspects,
                "language": ws.default.language,
                "theme": ws.default.theme,
            },
            "aspects": ws.aspects,
        }
    except Exception as e:
        return {"error": str(e), "type": "LoadError"}


def _enum_value(enum_obj):
    """Helper to safely get enum value (handles both enum objects and strings)."""
    if enum_obj is None:
        return None
    if isinstance(enum_obj, str):
        return enum_obj
    if hasattr(enum_obj, 'value'):
        return enum_obj.value
    return str(enum_obj)


def cmd_list_charts(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all charts in workspace.
    
    Args:
        args: dict with keys:
            - workspace_path: Path to workspace.yaml
    
    Returns:
        Dict with list of chart summaries
    """
    workspace_path = args.get('workspace_path')
    
    if not workspace_path:
        return {"error": "workspace_path is required", "type": "InvalidArgument"}
    
    try:
        ws = load_workspace(workspace_path)
        
        charts = []
        for chart in ws.charts or []:
            subj = getattr(chart, 'subject', None)
            cfg = getattr(chart, 'config', None)
            loc = getattr(subj, 'location', None) if subj else None
            
            charts.append({
                "id": getattr(chart, 'id', ''),
                "name": getattr(subj, 'name', '') if subj else '',
                "event_time": getattr(subj, 'event_time', '').isoformat() if subj and hasattr(getattr(subj, 'event_time', None), 'isoformat') else str(getattr(subj, 'event_time', '')) if subj else '',
                "location": getattr(loc, 'name', '') if loc else '',
                "engine": _enum_value(cfg.engine) if cfg and cfg.engine else None,
                "house_system": _enum_value(cfg.house_system) if cfg and cfg.house_system else None,
                "tags": list(getattr(chart, 'tags', []) or []),
            })
        
        return {"charts": charts}
    except Exception as e:
        return {"error": str(e), "type": "LoadError"}


def cmd_get_chart(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get chart details by ID.
    
    Args:
        args: dict with keys:
            - workspace_path: Path to workspace.yaml
            - chart_id: Chart ID
    
    Returns:
        Dict with chart details
    """
    workspace_path = args.get('workspace_path')
    chart_id = args.get('chart_id')
    
    if not workspace_path:
        return {"error": "workspace_path is required", "type": "InvalidArgument"}
    if not chart_id:
        return {"error": "chart_id is required", "type": "InvalidArgument"}
    
    try:
        ws = load_workspace(workspace_path)
        chart = find_chart_by_name_or_id(ws, chart_id)
        
        if not chart:
            return {"error": f"Chart {chart_id} not found", "type": "ChartNotFound"}
        
        subj = getattr(chart, 'subject', None)
        cfg = getattr(chart, 'config', None)
        loc = getattr(subj, 'location', None) if subj else None
        
        return {
            "id": getattr(chart, 'id', ''),
            "subject": {
                "id": getattr(subj, 'id', '') if subj else '',
                "name": getattr(subj, 'name', '') if subj else '',
                "event_time": getattr(subj, 'event_time', '').isoformat() if subj and hasattr(getattr(subj, 'event_time', None), 'isoformat') else str(getattr(subj, 'event_time', '')) if subj else '',
                "location": {
                    "name": getattr(loc, 'name', '') if loc else '',
                    "latitude": getattr(loc, 'latitude', None) if loc else None,
                    "longitude": getattr(loc, 'longitude', None) if loc else None,
                    "timezone": getattr(loc, 'timezone', None) if loc else None,
                } if loc else None,
            } if subj else None,
            "config": {
                "mode": _enum_value(cfg.mode) if cfg and cfg.mode else None,
                "house_system": _enum_value(cfg.house_system) if cfg and cfg.house_system else None,
                "zodiac_type": _enum_value(cfg.zodiac_type) if cfg and cfg.zodiac_type else None,
                "engine": _enum_value(cfg.engine) if cfg and cfg.engine else None,
                "override_ephemeris": cfg.override_ephemeris if cfg else None,
            } if cfg else None,
            "tags": list(getattr(chart, 'tags', []) or []),
        }
    except Exception as e:
        return {"error": str(e), "type": "LoadError"}


def cmd_sync_workspace(args: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronize workspace manifest with files on disk.
    
    Args:
        args: dict with keys:
            - workspace_path: Path to workspace.yaml
            - auto_import: If True, import new charts/subjects found on disk (default: True)
            - auto_remove: If True, remove references to missing files (default: False)
    
    Returns:
        Dict with sync results
    """
    workspace_path = args.get('workspace_path')
    
    if not workspace_path:
        return {"error": "workspace_path is required", "type": "InvalidArgument"}
    
    try:
        from module.workspace import sync_workspace
    except ImportError:
        from workspace import sync_workspace
    
    auto_import = args.get('auto_import', True)
    auto_remove = args.get('auto_remove', False)
    
    try:
        result = sync_workspace(workspace_path, auto_import=auto_import, auto_remove=auto_remove)
        return {
            "synced": True,
            "imported_charts": result.get('imported_charts', []),
            "imported_subjects": result.get('imported_subjects', []),
            "removed_charts": result.get('removed_charts', []),
            "removed_subjects": result.get('removed_subjects', []),
            "changes": result.get('changes', {}),
        }
    except Exception as e:
        return {"error": str(e), "type": "SyncError"}


def cmd_export_parquet(args: Dict[str, Any]) -> Dict[str, Any]:
    """Export stored positions to Parquet files.
    
    Args:
        args: dict with keys:
            - workspace_path: Path to workspace.yaml
            - chart_id: Optional chart ID to export (if not provided, exports all)
            - output_dir: Optional output directory (defaults to workspace/data/parquet)
            - partition_by_date: If True, partition by date (default: True)
    
    Returns:
        Dict with list of created Parquet file paths
    """
    workspace_path = args.get('workspace_path')
    
    if not workspace_path:
        return {"error": "workspace_path is required", "type": "InvalidArgument"}
    
    if not STORAGE_AVAILABLE:
        return {"error": "DuckDB storage not available. Install with: pip install duckdb pyarrow", "type": "StorageNotAvailable"}
    
    try:
        db_path = get_storage_path(workspace_path)
        
        if not db_path.exists():
            return {"error": f"DuckDB database not found: {db_path}. Run compute_chart with store_in_db=True first.", "type": "StorageNotFound"}
        
        chart_id = args.get('chart_id')
        output_dir = args.get('output_dir')
        partition_by_date = args.get('partition_by_date', True)
        
        # Default output directory
        if not output_dir:
            output_dir = db_path.parent / "parquet"
        
        with DuckDBStorage(db_path, create_schema=False) as storage:
            parquet_files = storage.export_to_parquet(
                output_dir,
                chart_id=chart_id,
                partition_by_date=partition_by_date
            )
        
        return {
            "parquet_files": [str(f) for f in parquet_files],
            "output_dir": str(output_dir),
            "count": len(parquet_files)
        }
    except Exception as e:
        return {"error": str(e), "type": "ExportError"}


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        _json_error("Command required", "InvalidArgument")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Parse JSON args from stdin or command line
    args = {}
    if len(sys.argv) > 2:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            _json_error(f"Invalid JSON in arguments: {sys.argv[2]}", "InvalidArgument")
            sys.exit(1)
    else:
        # Try reading from stdin
        try:
            stdin_input = sys.stdin.read()
            if stdin_input.strip():
                args = json.loads(stdin_input)
        except json.JSONDecodeError:
            pass  # No JSON in stdin, use empty args
    
    # Route to command handler
    handlers = {
        "compute_chart": cmd_compute_chart,
        "compute_transit_series": cmd_compute_transit_series,
        "get_workspace_settings": cmd_get_workspace_settings,
        "list_charts": cmd_list_charts,
        "get_chart": cmd_get_chart,
        "sync_workspace": cmd_sync_workspace,
        "export_parquet": cmd_export_parquet,
    }
    
    if command not in handlers:
        _json_error(f"Unknown command: {command}", "InvalidCommand")
        sys.exit(1)
    
    try:
        result = handlers[command](args)
        _json_output(result)
        
        # Exit with error code if result contains error
        if "error" in result:
            sys.exit(1)
    except Exception as e:
        _json_error(str(e), "InternalError")
        sys.exit(1)


if __name__ == "__main__":
    main()
