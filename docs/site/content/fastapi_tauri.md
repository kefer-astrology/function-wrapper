# FastAPI + React + Tauri Integration

## Overview

This guide describes the recommended way to use the Python package in a desktop application built from:

- React (or Svelte) frontend
- FastAPI backend
- Tauri packaging

The key idea is to treat the Python package as a reusable computation library, and to keep UI-specific modules optional.

Recommended runtime flow:

```text
Tauri shell
  -> React frontend
  -> HTTP calls to FastAPI on localhost
  -> FastAPI calls module.services / module.workspace / module.storage
```

Do not build the Tauri app around `module/ui_streamlit.py` or `module/ui_kivy.py`.
Those files are alternative Python frontends, not the ideal integration surface for Tauri.

## Recommended package split

Use the package in layers:

- `module.models`
  - dataclasses and enums shared by the backend
- `module.services`
  - chart computation and domain logic
- `module.workspace`
  - workspace loading and saving
- `module.storage`
  - optional DuckDB and Parquet support
- `module.cli`
  - existing JSON command contract, useful as a reference
- `module.ui_*`
  - optional developer-facing UIs, not required by FastAPI or Tauri

For the target architecture, prefer:

- core package install for shared astrology logic
- `api` extra for FastAPI
- optional `visuals` extra only if the backend needs Plotly/Matplotlib output

## Installation options

### Lean backend for Tauri

Install only the backend runtime:

```bash
pip install .
pip install .[api]
```

This is the preferred setup when:

- React renders the UI
- FastAPI exposes JSON endpoints
- the backend does not need Streamlit or Kivy

### Backend with chart rendering support

If the Python backend must generate Plotly figures or export images:

```bash
pip install .
pip install .[api]
pip install .[visuals]
```

### Optional developer UIs

Install only when those frontends are actually used:

```bash
pip install .[streamlit]
pip install .[kivy]
```

## Why this split matters

The repository contains multiple frontend styles:

- Streamlit
- Kivy
- CLI/TUI
- sidecar-style JSON commands

For a Tauri desktop app, shipping unnecessary frontend dependencies makes the Python environment larger and harder to maintain.

In particular:

- Streamlit should not be required by the FastAPI sidecar
- Kivy should not be required by the FastAPI sidecar
- visualization libraries should be optional unless the backend renders charts itself

## Existing integration surface

The current repo already has a useful contract in `module.cli`.

See:

- `cli_reference.md`
- `module/cli.py`

That CLI already exposes sidecar-style operations such as:

- `compute_chart`
- `compute_transit_series`
- `get_workspace_settings`
- `list_charts`
- `get_chart`

You can either:

1. Keep using the CLI as a subprocess contract from Tauri, or
2. Move that same contract behind FastAPI routes

For new work, FastAPI is usually the cleaner option because it gives you:

- typed request and response models
- easier debugging
- better error handling
- simpler integration from React
- cleaner long-term API evolution

## Recommended FastAPI structure

Create a dedicated API layer instead of putting HTTP concerns into `module.services`.

Suggested layout:

```text
module/
  api/
    __init__.py
    app.py
    schemas.py
    routes/
      charts.py
      workspace.py
      transits.py
```

Suggested responsibility split:

- `module.services`
  - pure domain logic
- `module.workspace`
  - file and workspace orchestration
- `module.storage`
  - persistence concerns
- `module.api.schemas`
  - Pydantic request and response models
- `module.api.routes.*`
  - HTTP request parsing and response shaping

## Example FastAPI adapter

Minimal example:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from module.workspace import load_workspace
from module.services import (
    compute_positions_for_chart,
    compute_aspects_for_chart,
    find_chart_by_name_or_id,
)


app = FastAPI()


class ComputeChartRequest(BaseModel):
    workspace_path: str
    chart_id: str
    include_physical: bool = False
    include_topocentric: bool = False


@app.post("/charts/compute")
def compute_chart(payload: ComputeChartRequest):
    ws = load_workspace(payload.workspace_path)
    chart = find_chart_by_name_or_id(ws, payload.chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    positions = compute_positions_for_chart(
        chart,
        ws=ws,
        include_physical=payload.include_physical,
        include_topocentric=payload.include_topocentric,
    )
    aspects = compute_aspects_for_chart(chart, ws=ws)

    return {
        "chart_id": payload.chart_id,
        "positions": positions,
        "aspects": aspects,
    }
```

This keeps the package reusable while giving the React app a clean HTTP API.

The repository now includes a scaffolded FastAPI adapter in:

- `module/api/app.py`
- `module/api/schemas.py`
- `module/api/__main__.py`

Run it locally with:

```bash
pip install .[api]
python -m module.api --host 127.0.0.1 --port 8765 --reload
```

Or:

```bash
make run-api
```

## Suggested React and Tauri responsibilities

### React frontend

The React app should handle:

- routing
- forms
- state management
- chart selection
- API calls to FastAPI
- rendering backend results

### Tauri shell

Tauri should handle:

- packaging
- starting and stopping the FastAPI sidecar
- native file dialogs if needed
- desktop-only capabilities

## Connecting the pieces together

The clean connection model is:

```text
Tauri
  -> starts Python sidecar
  -> loads React frontend
  -> React waits for GET /health
  -> React calls FastAPI routes on localhost
```

### Step 1: start the backend locally

During development, run:

```bash
pip install .[api]
python -m module.api --host 127.0.0.1 --port 8765 --reload
```

### Step 2: point React at the local API

Use a frontend API base URL such as:

```text
http://127.0.0.1:8765
```

Typical frontend calls:

- `GET /health`
- `GET /workspace/settings?workspace_path=...`
- `GET /charts?workspace_path=...`
- `GET /charts/{chart_id}?workspace_path=...`
- `POST /charts/compute`
- `POST /transits/compute-series`

Example fetch:

```ts
const API_BASE = "http://127.0.0.1:8765";

export async function computeChart(workspacePath: string, chartId: string) {
  const response = await fetch(`${API_BASE}/charts/compute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspace_path: workspacePath,
      chart_id: chartId,
      include_physical: false,
      include_topocentric: false,
      store_in_db: false,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}
```

### Step 3: let Tauri launch the sidecar

In the packaged desktop app, Tauri should launch the bundled backend executable on startup.

The frontend should not assume the backend is instantly ready.

Recommended flow:

1. Tauri starts the sidecar.
2. React polls `GET /health`.
3. When health is ready, the app unlocks the main UI.

### Step 4: keep the backend address configurable

In development:

- use a fixed localhost URL such as `http://127.0.0.1:8765`

In production:

- keep the same default if possible
- or inject the backend URL into the frontend on startup

### Step 5: pass workspace paths explicitly

The current API scaffold keeps workspace selection explicit.

That means React or Tauri should provide the `workspace_path` when calling endpoints that need it.

This is a good starting point because it avoids hidden global backend state.

## Exact Tauri integration checklist

Use this sequence when you open the Tauri project.

## Handoff checklist for the Tauri project

Use one of these two handoff modes.

### Option A: source-based handoff

Use this if the Tauri project or CI will build the Python sidecar itself.

Pass these:

- `module/`
- `pyproject.toml`
- `source/` if runtime assets such as ephemeris files are needed
- this document: `docs/site/content/fastapi_tauri.md`

Do not pass these:

- `build/`
- `.venv-build/`
- PyInstaller temporary caches

Optional:

- `kefer-backend.spec` if you want the Tauri project to reuse the same PyInstaller config

### Option B: artifact-based handoff

Use this if the Python backend is built outside the Tauri project and Tauri only bundles the finished sidecar.

Pass these:

- `dist/kefer-backend` or `dist/kefer-backend.exe`
- this document: `docs/site/content/fastapi_tauri.md`
- runtime asset files if the backend expects them beside the executable

Do not pass these:

- `build/`
- `.venv-build/`
- the full backend source tree, unless the Tauri project also needs to rebuild it

### Recommendation

If you want the cleanest Tauri repository, prefer:

- artifact-based handoff for packaging
- source-based handoff only if the Tauri repo is also responsible for backend builds

That keeps the Tauri app smaller and avoids mixing Python build machinery into the frontend project unless you really want one repository to own everything.

## Recommended folder strategy

You do not need to flatten everything into one folder.

In fact, that usually becomes harder to maintain.

The cleaner approach is to keep clear boundaries inside the Tauri repository.

Suggested shape:

```text
tauri-app/
  frontend/
  src-tauri/
  backend-python/
    module/
    pyproject.toml
    source/
```

Or, if the backend is only consumed as a built artifact:

```text
tauri-app/
  frontend/
  src-tauri/
    binaries/
      kefer-backend-...
```

### When to keep a separate backend folder

Prefer a separate backend folder when:

- Python is still evolving
- you want backend builds in CI
- you want to keep Python dependencies isolated
- you do not want Tauri frontend folders cluttered with Python files

### When artifact-only is better

Prefer artifact-only handoff when:

- the backend is built elsewhere
- the Tauri project should stay mostly frontend plus Rust
- you want the smallest possible mental overhead in the Tauri repo

### Recommendation for you

Based on your concern about clutter, I would not merge everything into one giant folder.

I would use one of these:

1. a dedicated `backend-python/` folder inside the Tauri repo
2. no backend source in the Tauri repo at all, only the packaged sidecar in `src-tauri/binaries/`

Both are cleaner than flattening the whole Python project into the Tauri app root.

## Recommended Tauri repo layout

If you plan to pass the backend source and sort it out inside the Tauri project, this is the layout I recommend.

### Option 1: keep backend source in the Tauri repo

```text
tauri-app/
  frontend/
    src/
    package.json
    vite.config.ts
  src-tauri/
    Cargo.toml
    tauri.conf.json
    binaries/
  backend-python/
    module/
    source/
    pyproject.toml
    Makefile
    docs/
```

Why this is good:

- frontend stays frontend
- Rust and Tauri stay in `src-tauri/`
- Python stays isolated in `backend-python/`
- CI can build the sidecar from `backend-python/` and copy the result into `src-tauri/binaries/`

### Option 2: keep only built backend artifacts in the Tauri repo

```text
tauri-app/
  frontend/
    src/
    package.json
  src-tauri/
    Cargo.toml
    tauri.conf.json
    binaries/
      kefer-backend-x86_64-pc-windows-msvc.exe
      kefer-backend-x86_64-unknown-linux-gnu
      kefer-backend-aarch64-apple-darwin
      kefer-backend-x86_64-apple-darwin
  docs/
    backend-handoff.md
```

Why this is good:

- smallest Tauri repo footprint
- no Python build tooling mixed into the desktop app
- Tauri only bundles and launches the sidecar

### Which option I recommend

If you are still actively changing the Python backend:

- use Option 1 first

If the backend becomes stable or is built in separate CI:

- move toward Option 2

### What I would do in your place

For now, since you plan to pass all of these things to the Tauri project:

1. create `backend-python/`
2. put `module/`, `source/`, `pyproject.toml`, `Makefile`, and this doc there
3. build the sidecar from `backend-python/`
4. copy the built executable into `src-tauri/binaries/`
5. let Tauri bundle only the executable, not the whole Python folder

That gives you a clean transition path:

- easy to work on now
- easy to slim down later

### Files to ignore in the Tauri project

Even if you pass everything over initially, I recommend not keeping these in the long-term packaged project:

- `backend-python/build/`
- `backend-python/dist/` except for the final sidecar you actually bundle
- `backend-python/.venv-build/`
- any temporary PyInstaller cache directories

### Minimal copy set into `backend-python/`

Best practical handoff:

- `module/`
- `source/`
- `pyproject.toml`
- `Makefile`
- `docs/site/content/fastapi_tauri.md`

Optional:

- `kefer-backend.spec`

### Step 1: copy or add the Python backend package

Make sure the Tauri app can build this Python project as part of the desktop build.

You need these pieces available to the desktop app build:

- `module/`
- `pyproject.toml`
- `source/` if ephemeris assets are needed at runtime
- any workspace/example data you want to ship

If the Tauri app lives in a different repository, either:

- include this repo as a submodule, or
- copy the backend into a dedicated `backend/` folder, or
- publish the backend package and install it during CI

### Step 2: create a backend build environment

For local development:

```bash
python -m venv .venv-build
.venv-build/bin/python -m pip install --upgrade pip
.venv-build/bin/python -m pip install -e ".[api]" pyinstaller
```

On Windows, use:

```powershell
python -m venv .venv-build
.venv-build\Scripts\python -m pip install --upgrade pip
.venv-build\Scripts\python -m pip install -e ".[api]" pyinstaller
```

### Step 3: verify the backend runs before packaging

Run the backend directly first:

```bash
.venv-build/bin/python -m module.api --host 127.0.0.1 --port 8765
```

Check:

- `http://127.0.0.1:8765/health`
- `http://127.0.0.1:8765/docs`

Do this before touching Tauri packaging.

### Step 4: build a backend sidecar executable

Start with PyInstaller.

Example command on Linux or macOS:

```bash
.venv-build/bin/pyinstaller \
  --name kefer-backend \
  --onefile \
  --collect-all kerykeion \
  --hidden-import module.api.app \
  --hidden-import module.api.schemas \
  -m module.api
```

On Windows:

```powershell
.venv-build\Scripts\pyinstaller `
  --name kefer-backend `
  --onefile `
  --collect-all kerykeion `
  --hidden-import module.api.app `
  --hidden-import module.api.schemas `
  -m module.api
```

Expected output:

- `dist/kefer-backend` on Linux or macOS
- `dist/kefer-backend.exe` on Windows

### Step 5: add the sidecar binary to the Tauri project

Inside the Tauri project, place the built backend into the sidecar/binaries area used by Tauri.

Typical layout:

```text
src-tauri/
  binaries/
    kefer-backend-x86_64-pc-windows-msvc.exe
    kefer-backend-x86_64-unknown-linux-gnu
    kefer-backend-aarch64-apple-darwin
    kefer-backend-x86_64-apple-darwin
```

The exact file names depend on your Tauri target configuration, but the important part is:

- one backend executable per platform target
- copied into the Tauri packaging inputs before the app build runs

### Step 6: start the sidecar from Tauri

In the Tauri app:

- start the sidecar on app startup
- pass `--host 127.0.0.1 --port 8765`
- capture stdout and stderr for debugging

The Tauri side should:

1. launch the bundled `kefer-backend`
2. wait until `GET /health` returns success
3. then allow the React app to use the backend

### Step 7: point React to the local API

In the React app, use:

```text
http://127.0.0.1:8765
```

Recommended pattern:

- centralize the base URL in one API client module
- wait for backend readiness before loading workspace-dependent screens
- show a loading or recovery state if the sidecar fails to start

### Step 8: wire workspace selection

Because the scaffolded backend is stateless with respect to workspace selection, React or Tauri must provide:

- a workspace file path

Good first implementation:

1. use a Tauri file dialog to select `workspace.yaml`
2. store that path in frontend state
3. send it on every API request that needs it

### Step 9: package the desktop installers

After the sidecar is wired in, build Tauri normally for each platform.

Expected final artifacts:

- Windows `.msi` or `.exe`
- Linux `.AppImage`
- macOS `.dmg`

Each installer should already contain the backend sidecar.

### Step 10: CI artifact strategy

Recommended CI pipeline:

1. build backend sidecar per platform
2. upload sidecar binaries as CI artifacts
3. build Tauri installers using those sidecars
4. upload installers as release artifacts

This gives you both:

- backend artifacts for debugging
- final app artifacts for users

### FastAPI backend

FastAPI should handle:

- workspace loading
- chart computation
- transit computation
- persistence requests
- normalization of Python exceptions into stable API responses

## Suggested endpoint groups

Useful endpoint groups for this project:

- `GET /health`
- `GET /workspace/settings`
- `GET /charts`
- `GET /charts/{chart_id}`
- `POST /charts/compute`
- `POST /transits/compute-series`
- `POST /storage/export-parquet`

These map naturally to the existing logic in `module.cli`.

Current scaffolded routes:

- `GET /health`
- `GET /workspace/settings`
- `GET /charts`
- `GET /charts/{chart_id}`
- `POST /charts/compute`
- `POST /transits/compute-series`
- `POST /workspace/sync`
- `POST /storage/export-parquet`

## Data model guidance

Avoid returning internal dataclasses directly over HTTP.

Instead:

- keep dataclasses in `module.models`
- map them to Pydantic schemas in `module.api.schemas`
- use JSON-friendly response shapes

This helps with:

- versioning
- frontend stability
- better OpenAPI docs
- clearer validation errors

## What to keep out of the backend core

Do not make the core computation modules depend on:

- Streamlit
- Kivy
- Tauri-specific code
- frontend rendering details

If you need chart visualization, keep it behind an optional boundary.

For example:

- pure position/aspect computation stays in `services`
- Plotly figure creation stays optional
- UI presentation logic stays in React or separate Python UI modules

## CLI vs FastAPI

Both are valid, but they serve different goals.

### Use CLI when

- you want the fastest possible integration
- Tauri launches Python subprocesses directly
- request volume is small

### Use FastAPI when

- you want a stable backend contract
- React should call normal HTTP endpoints
- you expect the integration to grow
- you want easier debugging and testing

For this project, FastAPI is the better long-term fit.

## Migration path from current repo

Recommended path:

1. Keep `module.services`, `module.workspace`, and `module.storage` as the core.
2. Treat `module.cli` as the source contract for the first API routes.
3. Add `module/api/` with Pydantic schemas and FastAPI routes.
4. Keep `module/ui_streamlit.py` and `module/ui_kivy.py` as optional tools for manual testing or demos.
5. Let Tauri start the FastAPI sidecar and point the React app at it.

## Bundling Python into the Tauri app

For shipped desktop builds, do not depend on a user-installed Python.

Instead, bundle the backend privately inside the application package.

There are two main approaches.

### Option A: bundle a Python runtime

In this approach, the packaged app contains:

- a Python interpreter
- your installed package
- your dependencies
- a small startup command such as `python -m module.api.app`

This works, but it is usually more operationally complex because you need to assemble a platform-specific embedded runtime for:

- Windows
- macOS
- Linux

It is better than requiring a system Python, but it is not the simplest Tauri integration path.

### Option B: freeze the Python backend into a standalone executable

In this approach, you build the backend into a self-contained binary with a tool such as:

- PyInstaller
- Nuitka

Tauri then ships that backend binary as a sidecar and starts it on launch.

For this project, this is the recommended approach.

Benefits:

- no dependency on system Python
- simpler installer behavior
- easier Tauri integration
- cleaner artifact story in CI

## Recommended approach for this repository

The most practical packaging model here is:

- React frontend inside Tauri
- FastAPI backend as a sidecar executable
- Python package kept normal during development
- frozen backend executable produced per platform during release builds

In development, use `venv`.

In release packaging, do not ship the development virtual environment directly.

## Why not ship the raw virtualenv

A virtual environment is mainly a development convenience.

It is not the best final artifact because:

- it is platform-specific
- it often contains unnecessary development files
- paths inside it can be brittle
- copying it between machines is unreliable
- it usually produces a messier installer than a real sidecar binary

So the typical workflow is:

1. develop in a `venv`
2. build a frozen backend executable for each platform
3. let Tauri bundle that executable into the final installer

## Suggested build artifacts

You will usually end up with two layers of artifacts.

### Backend artifacts

These are produced first, one per platform:

- `backend-windows-x64.zip`
  - contains `kefer-backend.exe`
- `backend-linux-x64.tar.gz`
  - contains `kefer-backend`
- `backend-macos-x64.tar.gz`
  - contains `kefer-backend`
- `backend-macos-aarch64.tar.gz`
  - contains `kefer-backend`

These are CI-friendly artifacts and can be reused by the desktop packaging job.

### Desktop installer artifacts

These are the final Tauri deliverables:

- Windows: `.msi` and/or `.exe`
- Linux: `.AppImage` and optionally `.deb`
- macOS: `.dmg`

These final installers should already contain the backend sidecar.

## Suggested CI flow

Recommended release pipeline:

1. Build frontend assets.
2. Build Python backend sidecar for each target platform.
3. Upload backend sidecars as CI artifacts.
4. Build Tauri app for each target platform.
5. Bundle the matching backend sidecar into the Tauri package.
6. Upload final installers as release artifacts.

This is a good fit if you want "artifacts will be available as artifacts" in CI, because it gives you:

- intermediate backend artifacts for debugging
- final installer artifacts for users

## Suggested repository layout for packaging

Once you add the Tauri app, a practical structure looks like this:

```text
function-wrapper/
  module/
  frontend/
  src-tauri/
    tauri.conf.json
    Cargo.toml
    binaries/
      kefer-backend-x86_64-pc-windows-msvc.exe
      kefer-backend-x86_64-unknown-linux-gnu
      kefer-backend-aarch64-apple-darwin
      kefer-backend-x86_64-apple-darwin
```

The exact sidecar naming depends on the Tauri version and configuration, but the main idea is the same:

- one backend binary per target
- checked into build outputs or copied there during CI
- bundled by Tauri into the final installer

## Runtime behavior inside the packaged app

At runtime:

1. Tauri launches the bundled backend sidecar.
2. The backend starts FastAPI on `127.0.0.1` and a fixed or negotiated port.
3. React calls the local HTTP API.
4. On app exit, Tauri stops the sidecar.

Good practice:

- wait for backend readiness before loading API-dependent screens
- expose a small `GET /health` endpoint
- log sidecar startup failures clearly

## Backend entrypoint recommendation

Create a tiny dedicated backend entrypoint for packaging.

For example:

```text
module/
  api/
    app.py
    __main__.py
```

That entrypoint should do one job:

- start the FastAPI app with the correct host and port

Keep packaging logic outside the domain modules.

This repository now provides that entrypoint through:

- `python -m module.api`
- `kefer-api`

## Tooling recommendation

For this repository, start with:

- FastAPI + Uvicorn for the backend
- PyInstaller for the first packaged sidecar
- Tauri sidecar bundling for the desktop app

PyInstaller is not perfect, but it is usually the fastest way to get to real artifacts.

If startup speed or binary size later becomes a problem, evaluate Nuitka after the integration is already working.

## Practical release plan

The simplest path to production-like artifacts is:

1. Add `module/api/app.py`
2. Add a minimal backend launcher
3. Build that backend with PyInstaller for each target platform
4. Add the Tauri app and configure it to start the sidecar
5. Produce installer artifacts per platform

That gets you to:

- reusable Python package in development
- private bundled backend in release builds
- downloadable CI artifacts for both sidecars and installers

## Practical recommendation

If you are building the new application now, the most maintainable setup is:

- Python package for business logic
- FastAPI as the backend adapter
- React as the only application UI
- Tauri as the desktop shell

That gives you one real UI, one real backend contract, and keeps the old Python UI modules optional instead of foundational.
