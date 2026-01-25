# CLI Reference

## Overview

The Python sidecar provides a JSON-based CLI interface for the Tauri frontend. All commands accept JSON arguments and return JSON results.

## Usage

```bash
python -m module.cli <command> [args_json]
```

Or with JSON from stdin:

```bash
echo '{"workspace_path": "/path/to/workspace.yaml", "chart_id": "my-chart"}' | python -m module.cli compute_chart
```

## Commands

### 1. `compute_chart`

Compute positions and aspects for a chart.

**Arguments:**
```json
{
  "workspace_path": "/path/to/workspace.yaml",
  "chart_id": "chart-id",
  "include_physical": false,      // Optional: Include extended physical properties (JPL only)
  "include_topocentric": false   // Optional: Include altitude/azimuth (JPL with location)
}
```

**Response:**
```json
{
  "positions": {
    "sun": 45.5,  // Simple format (non-JPL) or
    "moon": {     // Extended format (JPL)
      "longitude": 120.3,
      "distance": 0.0025,
      "declination": 18.5,
      "right_ascension": 122.1,
      "latitude": 2.5,
      "speed": 13.2,
      "retrograde": false
    }
  },
  "aspects": [
    {
      "from": "sun",
      "to": "moon",
      "type": "trine",
      "angle": 119.5,
      "orb": 0.5,
      "exact_angle": 120.0,
      "applying": false,
      "separating": false
    }
  ],
  "chart_id": "chart-id"
}
```

**Error Response:**
```json
{
  "error": "Chart chart-id not found",
  "type": "ChartNotFound"
}
```

### 2. `compute_transit_series`

Compute transit series for a time range.

**Arguments:**
```json
{
  "workspace_path": "/path/to/workspace.yaml",
  "source_chart_id": "source-chart-id",
  "start_datetime": "2024-01-01T00:00:00+01:00",
  "end_datetime": "2024-01-01T12:00:00+01:00",
  "time_step": "1 hour",              // e.g., "1 second", "30 seconds", "1 minute", "1 hour", "1 day"
  "transiting_objects": ["sun", "moon"],  // Optional
  "transited_objects": ["sun", "moon"],    // Optional
  "aspect_types": ["conjunction", "square"], // Optional
  "include_physical": false,          // Optional
  "include_topocentric": false       // Optional
}
```

**Response:**
```json
{
  "source_chart_id": "source-chart-id",
  "time_range": {
    "start": "2024-01-01T00:00:00+01:00",
    "end": "2024-01-01T12:00:00+01:00"
  },
  "time_step": "1 hour",
  "results": [
    {
      "datetime": "2024-01-01T00:00:00+01:00",
      "transit_positions": { /* positions dict */ },
      "aspects": [ /* aspects list */ ]
    },
    // ... more time points
  ]
}
```

### 3. `get_workspace_settings`

Get workspace settings and defaults.

**Arguments:**
```json
{
  "workspace_path": "/path/to/workspace.yaml"
}
```

**Response:**
```json
{
  "owner": "user@example.com",
  "active_model": "western",
  "default": {
    "ephemeris_engine": "jpl",
    "ephemeris_backend": "de421",
    "default_house_system": "Placidus",
    "default_bodies": ["sun", "moon", "mercury", "venus", "mars"],
    "default_aspects": ["conjunction", "opposition", "trine", "square", "sextile"],
    "language": "en",
    "theme": "default"
  },
  "aspects": ["conjunction", "opposition", "trine", "square"]
}
```

### 4. `list_charts`

List all charts in workspace.

**Arguments:**
```json
{
  "workspace_path": "/path/to/workspace.yaml"
}
```

**Response:**
```json
{
  "charts": [
    {
      "id": "chart-1",
      "name": "John Doe",
      "event_time": "2024-01-01T12:00:00+01:00",
      "location": "Prague, CZ",
      "engine": "jpl",
      "house_system": "Placidus",
      "tags": ["natal", "person"]
    },
    // ... more charts
  ]
}
```

### 5. `get_chart`

Get chart details by ID.

**Arguments:**
```json
{
  "workspace_path": "/path/to/workspace.yaml",
  "chart_id": "chart-id"
}
```

**Response:**
```json
{
  "id": "chart-id",
  "subject": {
    "id": "subject-id",
    "name": "John Doe",
    "event_time": "2024-01-01T12:00:00+01:00",
    "location": {
      "name": "Prague, CZ",
      "latitude": 50.0875,
      "longitude": 14.4214,
      "timezone": "Europe/Prague"
    }
  },
  "config": {
    "mode": "NATAL",
    "house_system": "Placidus",
    "zodiac_type": "Tropical",
    "engine": "jpl",
    "override_ephemeris": null
  },
  "tags": ["natal", "person"]
}
```

## Error Types

- `InvalidArgument`: Missing or invalid arguments
- `ChartNotFound`: Chart ID not found in workspace
- `ComputationError`: Error during computation
- `LoadError`: Error loading workspace
- `InvalidCommand`: Unknown command
- `InternalError`: Unexpected internal error

## Testing

Run tests:

```bash
python -m pytest tests/test_cli.py -v
```

Or with unittest:

```bash
python -m unittest tests.test_cli
```

## Examples

### Compute chart positions

```bash
python -m module.cli compute_chart '{"workspace_path": "/path/to/workspace.yaml", "chart_id": "my-chart"}'
```

### Get workspace settings

```bash
python -m module.cli get_workspace_settings '{"workspace_path": "/path/to/workspace.yaml"}'
```

### List all charts

```bash
python -m module.cli list_charts '{"workspace_path": "/path/to/workspace.yaml"}'
```
