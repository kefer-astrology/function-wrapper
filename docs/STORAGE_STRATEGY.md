# Storage Strategy: Python vs Rust

## Overview

The architecture supports **hybrid storage** where both Python and Rust can write to DuckDB/Parquet. This document explains when to use each approach.

## Architecture Decision

Based on the prompt files (`ARCHITECTURE_PROPOSAL.md`, `DISCUSSION_SUMMARY.md`), the architecture supports:

1. **Python storage helpers** (optional) - For batch operations
2. **Rust storage** (primary) - For frontend-driven operations

## When to Use Python Storage

### ✅ Use Python Storage For:

1. **Large Batch Operations**
   - Transit series with many time points (>10)
   - Revolution series computation
   - Background computation jobs
   - Bulk data export/import

2. **Performance Optimization**
   - Avoid transferring large JSON payloads
   - Direct database writes from computation loop
   - Reduce memory usage in Rust layer

3. **Standalone Python Scripts**
   - Data migration scripts
   - Batch computation scripts
   - Data analysis scripts

### Example: Transit Series

```python
# Python computes and stores directly
storage = DuckDBStorage('/path/to/workspace.db')
for timepoint in time_range:
    positions = compute_positions(...)
    aspects = compute_aspects(...)
    storage.store_positions(chart_id, timepoint, positions)
    storage.store_aspects(relation_id, timepoint, aspects)
# No JSON transfer needed!
```

## When to Use Rust Storage

### ✅ Use Rust Storage For:

1. **Frontend-Driven Operations**
   - Single chart computations
   - User-initiated queries
   - Real-time updates

2. **Small Data Sets**
   - <10 time points
   - Single chart positions
   - Quick lookups

3. **Frontend Integration**
   - Direct Svelte store updates
   - UI state management
   - Query optimization

### Example: Single Chart

```rust
// Rust receives JSON, stores in DuckDB
let result = compute_chart(args).await?;
storage.store_positions(result.positions)?;
// Frontend can query immediately
```

## Storage Path Convention

Both Python and Rust use the same storage path:

```
workspace/
├── workspace.yaml
├── data/
│   └── workspace.db    # Shared DuckDB database
└── data/
    └── positions/      # Parquet files (optional)
        └── chart_*.parquet
```

Python helper function:
```python
from module.storage import get_storage_path

db_path = get_storage_path('/path/to/workspace.yaml')
# Returns: /path/to/workspace/data/workspace.db
```

## CLI Integration

The CLI supports optional storage via `store_in_db` flag:

```bash
# Store results in DuckDB
python -m module.cli compute_chart '{
  "workspace_path": "/path/to/workspace.yaml",
  "chart_id": "my-chart",
  "store_in_db": true
}'
```

For transit series, storage is automatically used for large batches (>10 time points).

## Schema Compatibility

Both Python and Rust use the **same DuckDB schema**:

```sql
CREATE TABLE computed_positions (
    chart_id TEXT NOT NULL,
    datetime TIMESTAMP NOT NULL,
    object_id TEXT NOT NULL,
    longitude REAL NOT NULL,
    -- ... extended properties
    PRIMARY KEY (chart_id, datetime, object_id)
);
```

This ensures:
- ✅ No data conflicts
- ✅ Consistent queries
- ✅ Shared indexes

## Performance Comparison

### Python Storage (Batch)
- **Pros**: Direct writes, no JSON overhead, efficient loops
- **Cons**: Requires Python runtime, less frontend control
- **Use**: Transit series, bulk operations

### Rust Storage (Interactive)
- **Pros**: Frontend control, immediate queries, type safety
- **Cons**: JSON transfer overhead, multiple round-trips
- **Use**: Single charts, real-time updates

## Best Practices

1. **Batch Operations**: Use Python storage
   ```python
   # Transit series: Python stores directly
   storage = DuckDBStorage(db_path)
   for timepoint in time_range:
       # Compute and store in one loop
   ```

2. **Interactive Operations**: Use Rust storage
   ```rust
   // Single chart: Rust receives JSON, stores
   let result = compute_chart(args).await?;
   storage.store(result)?;
   ```

3. **Hybrid Approach**: Python computes, Rust queries
   ```python
   # Python: Background job stores data
   storage.store_positions(...)
   ```
   ```rust
   // Rust: Frontend queries stored data
   let positions = storage.query_positions(...)?;
   ```

## Migration Path

1. **Phase 1**: Rust storage only (current)
2. **Phase 2**: Add Python storage helpers (optional)
3. **Phase 3**: Use Python for batch operations
4. **Phase 4**: Optimize based on usage patterns

## Dependencies

### Python Storage
```bash
pip install duckdb pyarrow
```

### Rust Storage
```toml
[dependencies]
duckdb = "0.10"
```

Both are optional - the system works with either or both.

## Example: Transit Series with Python Storage

```python
from module.cli import cmd_compute_transit_series
from module.storage import DuckDBStorage, get_storage_path

args = {
    "workspace_path": "/path/to/workspace.yaml",
    "source_chart_id": "natal-chart",
    "start_datetime": "2024-01-01T00:00:00",
    "end_datetime": "2024-12-31T23:59:59",
    "time_step": "1 hour",
}

# CLI automatically uses storage for large batches
result = cmd_compute_transit_series(args)

# Results are stored in DuckDB
# Frontend can query directly:
# SELECT * FROM computed_positions WHERE chart_id = 'transit_natal-chart_...'
```

## Summary

- **Python storage**: Optional, recommended for batch operations
- **Rust storage**: Primary, recommended for interactive operations
- **Shared schema**: Both use same DuckDB schema
- **Automatic selection**: CLI chooses storage based on operation size
- **Performance**: Python storage avoids JSON overhead for large batches
