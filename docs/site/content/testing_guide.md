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

---

## Unittest Quick Start
```bash
# From project root
python -m unittest discover tests -v

# Or using unittest directly
python -m unittest discover . -v

# Or run specific test file
python -m unittest tests.test_comprehensive -v
```

## Specific Test Suites
```bash
# Run comprehensive test suite
python -m unittest tests.test_comprehensive.TestComprehensive -v

# Run workspace flow tests
python -m unittest tests.test_workspace_flow -v

# Run CLI tests
python -m unittest tests.test_cli -v

# Run engine tests
python -m unittest tests.test_engines -v
```

## Specific Test Methods
```bash
# Run a single test method
python -m unittest tests.test_comprehensive.TestComprehensive.test_02_workspace_initialization -v
```

## Test Files

### Core Functionality Tests

- **`test_comprehensive.py`**: Comprehensive test suite covering all functionality
  - Date, place, location parsing
  - Engine functionality
  - Workspace flow (including StarFisher import)
  - CLI accessibility
  - Chart computation with timestamps
  - Sample workspace creation (creates `tests/sample/` directory)

- **`test_workspace_flow.py`**: Workspace initialization and management
  - Workspace creation
  - Chart addition and saving
  - Workspace settings

- **`test_cli.py`**: Command-line interface tests
  - Chart computation via CLI
  - Workspace settings retrieval
  - Chart listing and retrieval
  - Transit series computation

- **`test_engines.py`**: Astrological computation engine tests
  - JPL engine
  - Kerykeion engine
  - Engine comparison

- **`test_storage.py`**: Storage integration tests
  - Position storage
  - Aspect storage
  - Parquet export

### Storage Stress Test

- **`test_storage_stress.py`**: High-frequency storage stress test
  - 5 days at 1-minute intervals (~7,200 timestamps)
  - 10 standard planets (~72,000 rows)
  - All extended attributes enabled (physical + topocentric)

Run with unittest:
```bash
python -m unittest tests.test_storage_stress.TestStorageStress.test_minute_interval_5_days_max_attributes -v
```

Expected runtime:
- Computation: ~5-15 minutes
- Storage: ~1-2 minutes
- Parquet export: ~10-30 seconds
- Total: ~10-20 minutes

Output location:
```
tests/sample_stress/
```

Workspace contents (high level):
- `workspace.yaml`
- `charts/`
- `data/workspace.db`
- `data/parquet/` (partitioned by date)

Clean up:
```bash
rm -rf tests/sample_stress/
```

### Utility Tests

- **`test_dates_places.py`**: Date and place parsing utilities
- **`test_locations.py`**: Location parsing and geocoding
- **`test_starfisher.py`**: StarFisher file import
- **`test_polar.py`**: Polar coordinate calculations

## Test Sample Workspace

The comprehensive test suite creates a sample workspace in `tests/sample/` that you can inspect after running tests. This directory is automatically added to `.gitignore`.

**Note**: The sample workspace is created during test execution and contains:
- `workspace.yaml` - Workspace manifest
- `charts/` - Chart YAML files
- `subjects/` - Subject definitions
- `layouts/`, `annotations/`, `presets/` - Other workspace components

## Test Requirements

### Required Dependencies
- Python 3.7+
- Standard library `unittest`

## Test Output

### Verbose Output
Use `-v` flag for verbose output showing each test as it runs:
```bash
python -m unittest discover tests -v
```

### Quiet Output
Omit `-v` for minimal output (only failures):
```bash
python -m unittest discover tests
```

### Stop on First Failure
```bash
python -m unittest discover tests -v --failfast
```

## Common Issues

### Import Errors
If you get import errors, make sure you're running from the project root:
```bash
cd /path/to/function-wrapper
python -m unittest discover tests -v
```

### Missing Dependencies
Some tests are skipped if optional dependencies are missing. This is expected behavior.

### Sample Workspace Already Exists
If `tests/sample/` already exists from a previous test run, the comprehensive tests will use it. To start fresh:
```bash
rm -rf tests/sample/
python -m unittest tests.test_comprehensive -v
```
