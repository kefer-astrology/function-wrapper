# Test Suite README

This directory contains the test suite for the Kefer Astrology function-wrapper module.

## Quick Start

### Run All Tests
```bash
# From project root
python -m unittest discover tests -v

# Or using unittest directly
python -m unittest discover . -v

# Or run specific test file
python -m unittest tests.test_comprehensive -v
```

### Run Specific Test Classes
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

### Run Specific Test Methods
```bash
# Run a single test method
python -m unittest tests.test_comprehensive.TestComprehensive.test_02_workspace_initialization -v
```

## Test Files

### Core Functionality Tests

- **`test_comprehensive.py`**: Comprehensive test suite covering all functionality
  - Date, place, location parsing
  - Engine functionality (Skyfield/JPL, Kerykeion)
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
  - JPL/Skyfield engine
  - Kerykeion engine
  - Engine comparison

- **`test_storage.py`**: DuckDB storage integration tests
  - Position storage
  - Aspect storage
  - Parquet export

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
- Standard library: `unittest`, `tempfile`, `pathlib`, `datetime`, `pytz`, `yaml`

### Optional Dependencies (for specific tests)
- **`skyfield`**: Required for JPL engine tests (`test_engines.py::TestJPLSkyfieldEngine`)
- **`kerykeion`**: Required for Kerykeion engine tests (`test_engines.py::TestKerykeionEngine`)
- **`duckdb`**: Required for storage tests (`test_storage.py`)
- **`pyarrow`**: Required for Parquet export tests (`test_storage.py`)

Tests that require optional dependencies are automatically skipped if the dependency is not available.

## Running Tests with Coverage

```bash
# Install coverage tool
pip install coverage

# Run tests with coverage
coverage run -m unittest discover tests -v

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
# Then open htmlcov/index.html in your browser
```

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
Some tests are skipped if dependencies are missing. This is expected behavior. To run all tests, install optional dependencies:
```bash
pip install skyfield kerykeion duckdb pyarrow
```

### Sample Workspace Already Exists
If `tests/sample/` already exists from a previous test run, the comprehensive tests will use it. To start fresh:
```bash
rm -rf tests/sample/
python -m unittest tests.test_comprehensive -v
```

## Test Structure

Tests follow the standard `unittest` pattern:
- Test classes inherit from `unittest.TestCase`
- Test methods start with `test_`
- Use `setUp()` and `tearDown()` for test fixtures
- Use `self.assert*()` methods for assertions

## Continuous Integration

These tests are designed to run in CI environments. Tests that require UI components (Kivy, Streamlit) or X server access are automatically skipped if dependencies are not available.

## See Also

- `docs/TESTING_GUIDE.md` - Detailed testing guide and strategies
- `docs/CLI_API_REFERENCE.md` - CLI command reference
- `docs/STORAGE_STRATEGY.md` - Storage architecture documentation
