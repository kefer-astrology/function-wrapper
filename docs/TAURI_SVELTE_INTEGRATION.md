# Tauri + Svelte Frontend Integration Guide

## Overview

This guide describes how to integrate the Python astrological computation sidecar with a Tauri + Svelte frontend application. The Python backend handles heavy computational tasks (position calculations, aspect detection, transit series), while the frontend manages UI, state, and data storage using DuckDB with Parquet files.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Tauri + Svelte Frontend                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   UI Layer   │  │  State Store │  │  DuckDB/     │      │
│  │  (Svelte)    │  │  (Svelte)    │  │  Parquet     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│         └─────────────────┴──────────────────┘              │
│                            │                                  │
│                    ┌───────▼────────┐                        │
│                    │  Tauri Commands │                        │
│                    │   (Rust Layer)  │                        │
│                    └───────┬────────┘                        │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             │ subprocess
                             │ JSON over stdout
                             │
┌────────────────────────────▼─────────────────────────────────┐
│              Python Sidecar (Computation Engine)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   CLI API    │  │  Services    │  │  Workspace  │      │
│  │  (module.cli)│  │  (compute_*) │  │  (YAML)      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **User Action** → Svelte component triggers action
2. **Tauri Command** → Rust command handler called
3. **Python Subprocess** → Tauri spawns Python CLI with JSON args
4. **Computation** → Python computes positions/aspects/transits
5. **JSON Response** → Python outputs JSON to stdout
6. **Store Results** → Frontend stores in DuckDB/Parquet
7. **UI Update** → Svelte components react to state changes

## Tauri Command Implementation

### 1. Rust Command Handlers

Create command handlers in `src-tauri/src/commands/compute.rs`:

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::Command;
use std::path::PathBuf;
use tauri::command;

#[derive(Debug, Serialize, Deserialize)]
pub struct ComputeChartArgs {
    pub workspace_path: String,
    pub chart_id: String,
    pub include_physical: Option<bool>,
    pub include_topocentric: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ComputeChartResult {
    pub positions: HashMap<String, serde_json::Value>,  // Can be float or dict
    pub aspects: Vec<AspectResult>,
    pub chart_id: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AspectResult {
    pub from: String,
    pub to: String,
    pub r#type: String,
    pub angle: f64,
    pub orb: f64,
    pub exact_angle: f64,
    pub applying: bool,
    pub separating: bool,
}

#[command]
pub async fn compute_chart(args: ComputeChartArgs) -> Result<ComputeChartResult, String> {
    let python_exe = find_python_executable()?;
    let module_path = get_module_path()?;
    
    let args_json = serde_json::to_string(&args)
        .map_err(|e| format!("Failed to serialize args: {}", e))?;
    
    let output = Command::new(&python_exe)
        .arg("-m")
        .arg("module.cli")
        .arg("compute_chart")
        .arg(&args_json)
        .current_dir(&module_path)
        .output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;
    
    if !output.status.success() {
        let error = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python error: {}", error));
    }
    
    let result: serde_json::Value = serde_json::from_slice(&output.stdout)
        .map_err(|e| format!("Failed to parse Python output: {}", e))?;
    
    if let Some(error) = result.get("error") {
        return Err(error.as_str()
            .unwrap_or("Unknown error")
            .to_string());
    }
    
    serde_json::from_value(result)
        .map_err(|e| format!("Failed to deserialize result: {}", e))
}

fn find_python_executable() -> Result<PathBuf, String> {
    let candidates = vec!["python3", "python", "py"];
    
    for cmd in candidates {
        if Command::new(cmd)
            .arg("--version")
            .output()
            .is_ok()
        {
            return Ok(PathBuf::from(cmd));
        }
    }
    
    Err("Python executable not found".to_string())
}

fn get_module_path() -> Result<PathBuf, String> {
    // In Tauri, you can use env::current_exe() and navigate to the module directory
    // For development, you might use a configurable path
    std::env::current_dir()
        .map_err(|e| format!("Failed to get current directory: {}", e))
        .map(|p| p.join("function-wrapper"))  // Adjust path as needed
}
```

### 2. Register Commands in Tauri

In `src-tauri/src/main.rs`:

```rust
use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            greet,
            compute_chart,
            compute_transit_series,
            get_workspace_settings,
            list_charts,
            get_chart,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Svelte Integration

### 1. Tauri API Wrapper

Create `src/lib/tauri-api.ts`:

```typescript
import { invoke } from '@tauri-apps/api/tauri';

export interface ComputeChartArgs {
  workspace_path: string;
  chart_id: string;
  include_physical?: boolean;
  include_topocentric?: boolean;
}

export interface PositionData {
  [objectId: string]: number | {
    longitude: number;
    distance?: number;
    declination?: number;
    right_ascension?: number;
    latitude?: number;
    altitude?: number;
    azimuth?: number;
    // ... other extended properties
  };
}

export interface AspectResult {
  from: string;
  to: string;
  type: string;
  angle: number;
  orb: number;
  exact_angle: number;
  applying: boolean;
  separating: boolean;
}

export interface ComputeChartResult {
  positions: PositionData;
  aspects: AspectResult[];
  chart_id: string;
}

export async function computeChart(args: ComputeChartArgs): Promise<ComputeChartResult> {
  return await invoke<ComputeChartResult>('compute_chart', { args });
}

export async function computeTransitSeries(args: {
  workspace_path: string;
  source_chart_id: string;
  start_datetime: string;
  end_datetime: string;
  time_step: string;
  transiting_objects?: string[];
  transited_objects?: string[];
  aspect_types?: string[];
  include_physical?: boolean;
  include_topocentric?: boolean;
}): Promise<any> {
  return await invoke('compute_transit_series', { args });
}

export async function getWorkspaceSettings(workspace_path: string): Promise<any> {
  return await invoke('get_workspace_settings', { args: { workspace_path } });
}

export async function listCharts(workspace_path: string): Promise<any> {
  return await invoke('list_charts', { args: { workspace_path } });
}

export async function getChart(workspace_path: string, chart_id: string): Promise<any> {
  return await invoke('get_chart', { args: { workspace_path, chart_id } });
}
```

### 2. DuckDB Storage Integration

Create `src/lib/storage.ts`:

```typescript
import * as duckdb from '@duckdb/duckdb-wasm';
import { computeChart } from './tauri-api';

export class ChartStorage {
  private db: duckdb.AsyncDuckDB | null = null;
  private parquetPath: string;

  constructor(parquetPath: string = './data/charts.parquet') {
    this.parquetPath = parquetPath;
  }

  async initialize() {
    // Initialize DuckDB
    const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
    const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);
    const worker = await duckdb.createWorker(bundle.mainWorker!);
    const logger = new duckdb.ConsoleLogger();
    this.db = new duckdb.AsyncDuckDB(logger, worker);
    await this.db.instantiate(bundle.mainModule, bundle.pthreadWorker);

    // Create table if it doesn't exist
    await this.db.registerFileURL(
      'charts.parquet',
      this.parquetPath,
      duckdb.DuckDBDataProtocol.HTTP,
      false
    );

    // Create table schema
    await this.db.query(`
      CREATE TABLE IF NOT EXISTS chart_positions (
        chart_id VARCHAR,
        datetime TIMESTAMP,
        object_id VARCHAR,
        longitude DOUBLE,
        distance DOUBLE,
        declination DOUBLE,
        right_ascension DOUBLE,
        latitude DOUBLE,
        altitude DOUBLE,
        azimuth DOUBLE,
        speed DOUBLE,
        retrograde BOOLEAN,
        PRIMARY KEY (chart_id, datetime, object_id)
      )
    `);
  }

  async storeChartComputation(
    chartId: string,
    datetime: Date,
    positions: PositionData
  ) {
    if (!this.db) throw new Error('Database not initialized');

    // Convert positions to rows
    const rows: any[] = [];
    for (const [objectId, posData] of Object.entries(positions)) {
      if (typeof posData === 'number') {
        // Simple longitude only
        rows.push({
          chart_id: chartId,
          datetime: datetime.toISOString(),
          object_id: objectId,
          longitude: posData,
          distance: null,
          declination: null,
          right_ascension: null,
          latitude: null,
          altitude: null,
          azimuth: null,
          speed: null,
          retrograde: null,
        });
      } else {
        // Extended format
        rows.push({
          chart_id: chartId,
          datetime: datetime.toISOString(),
          object_id: objectId,
          longitude: posData.longitude,
          distance: posData.distance ?? null,
          declination: posData.declination ?? null,
          right_ascension: posData.right_ascension ?? null,
          latitude: posData.latitude ?? null,
          altitude: posData.altitude ?? null,
          azimuth: posData.azimuth ?? null,
          speed: posData.speed ?? null,
          retrograde: posData.retrograde ?? null,
        });
      }
    }

    // Insert into DuckDB
    const conn = await this.db.connect();
    const stmt = await conn.prepare(`
      INSERT OR REPLACE INTO chart_positions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    for (const row of rows) {
      await stmt.query([
        row.chart_id,
        row.datetime,
        row.object_id,
        row.longitude,
        row.distance,
        row.declination,
        row.right_ascension,
        row.latitude,
        row.altitude,
        row.azimuth,
        row.speed,
        row.retrograde,
      ]);
    }

    await conn.close();
  }

  async queryChartPositions(
    chartId: string,
    startTime?: Date,
    endTime?: Date
  ): Promise<any[]> {
    if (!this.db) throw new Error('Database not initialized');

    let query = `
      SELECT * FROM chart_positions
      WHERE chart_id = ?
    `;
    const params: any[] = [chartId];

    if (startTime) {
      query += ' AND datetime >= ?';
      params.push(startTime.toISOString());
    }
    if (endTime) {
      query += ' AND datetime <= ?';
      params.push(endTime.toISOString());
    }

    query += ' ORDER BY datetime, object_id';

    const conn = await this.db.connect();
    const result = await conn.query(query, params);
    await conn.close();

    return result.toArray();
  }

  async exportToParquet() {
    if (!this.db) throw new Error('Database not initialized');
    
    await this.db.query(`
      COPY (SELECT * FROM chart_positions) 
      TO '${this.parquetPath}' (FORMAT PARQUET)
    `);
  }
}
```

### 3. Svelte Store for Chart Data

Create `src/lib/stores/chartStore.ts`:

```typescript
import { writable, derived } from 'svelte/store';
import { computeChart } from '../tauri-api';
import { ChartStorage } from '../storage';

export interface ChartState {
  chartId: string | null;
  positions: PositionData | null;
  aspects: AspectResult[] | null;
  loading: boolean;
  error: string | null;
}

const chartStorage = new ChartStorage();

function createChartStore() {
  const { subscribe, set, update } = writable<ChartState>({
    chartId: null,
    positions: null,
    aspects: null,
    loading: false,
    error: null,
  });

  return {
    subscribe,
    
    async loadChart(workspacePath: string, chartId: string) {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        // Check cache first
        const cached = await chartStorage.queryChartPositions(chartId);
        if (cached.length > 0) {
          // Reconstruct positions from cached data
          const positions: PositionData = {};
          for (const row of cached) {
            if (row.distance !== null) {
              // Extended format
              positions[row.object_id] = {
                longitude: row.longitude,
                distance: row.distance,
                declination: row.declination,
                right_ascension: row.right_ascension,
                latitude: row.latitude,
                altitude: row.altitude,
                azimuth: row.azimuth,
                speed: row.speed,
                retrograde: row.retrograde,
              };
            } else {
              // Simple format
              positions[row.object_id] = row.longitude;
            }
          }
          
          update(state => ({
            ...state,
            chartId,
            positions,
            loading: false,
          }));
          return;
        }
        
        // Compute from Python sidecar
        const result = await computeChart({
          workspace_path: workspacePath,
          chart_id: chartId,
          include_physical: true,
          include_topocentric: true,
        });
        
        // Store in DuckDB
        await chartStorage.storeChartComputation(
          chartId,
          new Date(),
          result.positions
        );
        
        update(state => ({
          ...state,
          chartId,
          positions: result.positions,
          aspects: result.aspects,
          loading: false,
        }));
      } catch (error) {
        update(state => ({
          ...state,
          loading: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        }));
      }
    },
    
    clear() {
      set({
        chartId: null,
        positions: null,
        aspects: null,
        loading: false,
        error: null,
      });
    },
  };
}

export const chartStore = createChartStore();
```

### 4. Svelte Component Example

Create `src/lib/components/ChartViewer.svelte`:

```svelte
<script lang="ts">
  import { chartStore } from '../stores/chartStore';
  import { onMount } from 'svelte';
  
  export let workspacePath: string;
  export let chartId: string;
  
  let positions: PositionData | null = null;
  let aspects: AspectResult[] | null = null;
  let loading = false;
  let error: string | null = null;
  
  $: {
    const unsubscribe = chartStore.subscribe(state => {
      positions = state.positions;
      aspects = state.aspects;
      loading = state.loading;
      error = state.error;
    });
    
    return unsubscribe;
  }
  
  onMount(() => {
    chartStore.loadChart(workspacePath, chartId);
  });
</script>

<div class="chart-viewer">
  {#if loading}
    <p>Loading chart...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if positions}
    <h2>Chart: {chartId}</h2>
    
    <div class="positions">
      <h3>Positions</h3>
      <table>
        <thead>
          <tr>
            <th>Object</th>
            <th>Longitude</th>
            <th>Distance (AU)</th>
            <th>Declination</th>
            <th>RA</th>
          </tr>
        </thead>
        <tbody>
          {#each Object.entries(positions) as [objectId, posData]}
            <tr>
              <td>{objectId}</td>
              {#if typeof posData === 'number'}
                <td>{posData.toFixed(2)}°</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
              {:else}
                <td>{posData.longitude.toFixed(2)}°</td>
                <td>{posData.distance?.toFixed(4) ?? '-'}</td>
                <td>{posData.declination?.toFixed(2) ?? '-'}°</td>
                <td>{posData.right_ascension?.toFixed(2) ?? '-'}°</td>
              {/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    
    {#if aspects && aspects.length > 0}
      <div class="aspects">
        <h3>Aspects</h3>
        <ul>
          {#each aspects as aspect}
            <li>
              {aspect.from} {aspect.type} {aspect.to} 
              (angle: {aspect.angle.toFixed(2)}°, orb: {aspect.orb.toFixed(2)}°)
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  {/if}
</div>

<style>
  .chart-viewer {
    padding: 1rem;
  }
  
  .error {
    color: red;
  }
  
  table {
    border-collapse: collapse;
    width: 100%;
  }
  
  th, td {
    border: 1px solid #ddd;
    padding: 0.5rem;
    text-align: left;
  }
  
  th {
    background-color: #f2f2f2;
  }
</style>
```

## Error Handling

The Python CLI returns errors in a consistent format:

```json
{
  "error": "Error message",
  "type": "ErrorType"
}
```

Common error types:
- `InvalidArgument`: Missing or invalid arguments
- `ChartNotFound`: Chart ID not found in workspace
- `ComputationError`: Error during computation
- `LoadError`: Error loading workspace
- `InvalidCommand`: Unknown command

Handle errors in Svelte:

```typescript
try {
  const result = await computeChart(args);
  // Handle success
} catch (error) {
  if (error instanceof Error) {
    // Parse error JSON if available
    try {
      const errorData = JSON.parse(error.message);
      console.error(`Error type: ${errorData.type}, Message: ${errorData.error}`);
    } catch {
      console.error(error.message);
    }
  }
}
```

## Performance Considerations

1. **Caching**: Always check DuckDB cache before calling Python sidecar
2. **Batch Operations**: For transit series, compute in batches and store incrementally
3. **Lazy Loading**: Only compute extended properties when needed
4. **Background Processing**: Use web workers for long-running computations

## Testing

Test the integration:

```typescript
// src/lib/__tests__/tauri-api.test.ts
import { computeChart } from '../tauri-api';

describe('Tauri API', () => {
  it('should compute chart positions', async () => {
    const result = await computeChart({
      workspace_path: '/path/to/workspace.yaml',
      chart_id: 'test-chart',
    });
    
    expect(result.positions).toBeDefined();
    expect(result.aspects).toBeDefined();
    expect(result.chart_id).toBe('test-chart');
  });
});
```

## Deployment

1. **Bundle Python**: Include Python sidecar in Tauri app bundle
2. **Parquet Files**: Store Parquet files in app data directory
3. **Workspace Path**: Use absolute paths for workspace.yaml
4. **Error Logging**: Log Python subprocess errors for debugging

## Next Steps

- Implement transit series computation UI
- Add chart comparison features
- Implement time navigation controls
- Add export/import functionality for Parquet files
