# Testing Guide

## Overview

This guide covers testing strategies for the Kefer Astrology sidecar module, including CLI handlers, storage functionality, and core computation services.

## Test Structure

```
tests/
├── __init__.py
├── test_cli.py              # CLI command handlers
├── test_storage.py          # DuckDB storage (NEW)
├── test_workspace_flow.py   # Workspace operations
├── test_dates_places.py    # Date/location parsing
├── test_locations.py        # Location handling
├── test_starfisher.py      # Starfisher integration
├── test_polar.py           # Polar coordinates
└── test_docs.py            # Documentation generation
```

## Running Tests

### All Tests
```bash
python -m unittest discover tests
```

### Specific Test Suite
```bash
python -m unittest tests.test_cli
python -m unittest tests.test_storage
python -m unittest tests.test_workspace_flow
```

### With Coverage
```bash
pip install coverage
coverage run -m unittest discover tests
coverage report
coverage html  # Generate HTML report in htmlcov/
```

## Test Coverage Status

### ✅ Covered
- CLI handlers (`test_cli.py`)
  - `compute_chart` command
  - `get_workspace_settings` command
  - `list_charts` command
  - `get_chart` command
  - `compute_transit_series` command
  - Error handling

- Storage (`test_storage.py`) ⭐ NEW
  - Schema creation
  - Simple position storage
  - Extended position storage
  - Aspect storage
  - Position replacement
  - Parquet export
  - Context manager

- Workspace operations (`test_workspace_flow.py`)
  - Workspace initialization
  - Chart creation
  - Workspace settings

- Date/location parsing (`test_dates_places.py`, `test_locations.py`)

### ⚠️ Partially Covered
- Aspect computation - Basic tests needed
- Extended position format - JPL format tests needed
- CLI + storage integration - Combined tests needed

### ❌ Missing Tests
- `test_services_aspects.py` - Aspect computation edge cases
- `test_services_extended_positions.py` - JPL extended format
- `test_cli_storage_integration.py` - CLI with storage enabled

## Writing New Tests

### Test Template
```python
import unittest
import tempfile
from pathlib import Path

from module.services import compute_positions_for_chart
from module.models import EngineType

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.TemporaryDirectory()
        # ... setup code
    
    def tearDown(self):
        """Clean up."""
        self.tmpdir.cleanup()
    
    def test_feature_basic(self):
        """Test basic functionality."""
        # Arrange
        # Act
        # Assert
        pass
```

### CLI Test Pattern
```python
def test_cli_command(self):
    """Test CLI command via subprocess."""
    args = {
        "workspace_path": self.workspace_path,
        "chart_id": "test-chart",
    }
    
    result = self._run_cli("compute_chart", args)
    
    self.assertNotIn("error", result)
    self.assertIn("positions", result)
```

### Storage Test Pattern
```python
@unittest.skipUnless(STORAGE_AVAILABLE, "duckdb not available")
def test_storage_operation(self):
    """Test storage operation."""
    with DuckDBStorage(self.db_path) as storage:
        storage.store_positions(...)
    
    # Verify data
    storage2 = DuckDBStorage(self.db_path, create_schema=False)
    result = storage2.conn.execute("SELECT ...").fetchall()
    self.assertEqual(len(result), expected_count)
```

## Test Requirements

### Core Tests (Always Run)
- CLI handlers
- Workspace operations
- Date/location parsing

### Optional Tests (Skip if Dependencies Missing)
- Storage tests (requires `duckdb`)
- Parquet export (requires `pyarrow`)
- UI tests (requires `kivy`/`streamlit`)

### Test Markers
```python
@unittest.skipUnless(STORAGE_AVAILABLE, "duckdb not available")
class TestStorage(unittest.TestCase):
    pass
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements/base.txt
      - run: pip install duckdb pyarrow  # Optional deps
      - run: python -m unittest discover tests
```

## Test Data

### Sample Charts
Use `_make_sample_chart()` helper from `test_workspace_flow.py`:
```python
from tests.test_workspace_flow import _make_sample_chart

chart = _make_sample_chart(name="Test Chart")
```

### Sample Workspace
```python
from module.workspace import init_workspace

with tempfile.TemporaryDirectory() as tmpdir:
    base = Path(tmpdir) / "ws"
    manifest_path = init_workspace(
        base_dir=base,
        owner="Tester",
        active_model="default",
        default_ephemeris={"name": "de421", "backend": "jpl"},
    )
```

## Best Practices

1. **Use temporary directories** for file operations
2. **Clean up resources** in `tearDown()`
3. **Skip optional tests** if dependencies missing
4. **Test error cases** as well as success
5. **Use descriptive test names** that explain what's tested
6. **Keep tests independent** - no shared state between tests

## Debugging Failed Tests

### Run Single Test
```bash
python -m unittest tests.test_cli.TestCLI.test_compute_chart
```

### Verbose Output
```bash
python -m unittest tests.test_cli -v
```

### Debug Mode
```python
import pdb; pdb.set_trace()  # Add breakpoint
```

## Performance Testing

For large batch operations (transit series):
```python
def test_transit_series_performance(self):
    """Test transit series with many time points."""
    import time
    
    start = time.time()
    result = cmd_compute_transit_series({
        "workspace_path": self.workspace_path,
        "source_chart_id": "test-chart",
        "start_datetime": "2024-01-01T00:00:00",
        "end_datetime": "2024-01-31T23:59:59",
        "time_step": "1 hour",  # ~744 time points
    })
    elapsed = time.time() - start
    
    self.assertLess(elapsed, 60.0)  # Should complete in < 60s
```

## Next Steps

1. ✅ Add `test_storage.py` - Done
2. [ ] Add aspect computation tests
3. [ ] Add extended position format tests
4. [ ] Add CLI + storage integration tests
5. [ ] Add performance benchmarks
6. [ ] Set up CI/CD with test automation
