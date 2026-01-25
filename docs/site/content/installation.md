# Installation and Venvs

This project uses multiple virtual environments so the core backend stays lean while UI wrappers remain optional.

## Recommended venvs

- `venv` (base): core backend only
- `venv-streamlit`: Streamlit UI
- `venv-kivy`: Kivy UI
- `venv-docs`: documentation export (imports UI modules)

## Makefile targets

Use the Makefile to create isolated environments with pinned dependencies:

- `make venv` (creates `venv` with `requirements/base.txt`)
- `make venv-streamlit` (creates `venv-streamlit` with `requirements/streamlit.txt`)
- `make venv-kivy` (creates `venv-kivy` with `requirements/kivy.txt`)
- `make venv-docs` (creates `venv-docs` with `.[docs]` extras)

## Notes

- A single venv cannot switch environments without uninstalling packages.
- Separate venvs avoid heavy or conflicting UI dependencies.

## Environment preparation

1) Create virtual environment:
```bash
python3 -m venv venv
```

2) Activate virtual environment:
- Windows: `venv\Scripts\activate`
- Linux: `source ./venv/bin/activate`

3) Install libraries:
- Using precompiled lockfiles (recommended):
  - Base only: `pip install -r requirements/base.txt`
  - Streamlit UI: `pip install -r requirements/streamlit.txt`
  - Kivy UI: `pip install -r requirements/kivy.txt`
  - Dev all‑in: `pip install -r requirements/dev.txt` (or top‑level `requirements.txt` if present)
- To (re)compile lockfiles with pip‑tools:
  - Base: `pip-compile requirements/base.in -o requirements/base.txt`
  - Streamlit: `pip-compile requirements/streamlit.in -o requirements/streamlit.txt`
  - Kivy: `pip-compile requirements/kivy.in -o requirements/kivy.txt`
  - Dev all‑in: create `requirements/dev.in` that includes `-r requirements/streamlit.in` and `-r requirements/kivy.in`, then:
    `pip-compile requirements/dev.in -o requirements/dev.txt`

4) Run the application:
- Default: `python3 -m module` (runs TUI)
- Streamlit UI: `python3 -m module --streamlit`
- Kivy UI: `python3 -m module --kivy`
- TUI explicitly: `python3 -m module --tui`

5) Run tests:
- See `docs/TESTING_GUIDE.md` for detailed instructions
- Quick start: `python3 -m unittest discover tests -v`
- Or use Makefile: `make run_tests`

6) Project structure (core modules):
- `services.py` — chart creation/selection and compute orchestration
- `utils.py` — utilities for date and location parsing
- `workspace.py` — workspace, chart and settings management
- `z_visual.py` — visualization

## Dependency management

- Dependency definitions live in `requirements/` as `.in` files:
  - `requirements/base.in` contains core runtime deps.
  - `requirements/streamlit.in` and `requirements/kivy.in` should start with `-r base.in`.
- Reproducible installs use compiled lockfiles in `requirements/*.txt`.
- Dev/all‑in: keep `requirements/dev.txt` under `requirements/`. Optionally provide a root `requirements.txt` that contains `-r requirements/dev.txt`.

### Environment strategy (one venv vs multiple)

- A single venv cannot "switch" environments without uninstalling packages; once installed, they persist.
- Recommended: use separate venvs per UI target (`base`, `streamlit`, `kivy`, `docs`) to avoid heavy or conflicting deps.
- If you still want one venv, install the base first, then add extras:
  - `pip install -e .` (core only)
  - `pip install -e ".[streamlit]"` or `pip install -e ".[kivy]"`
  - `pip install -e ".[docs]"` (includes UI deps so `make docs` can import UI modules)

### Sync pyproject from requirements

`pyproject.toml` is derived from `requirements/*.in` (not from the compiled `.txt` lockfiles).

To regenerate the dependency sections after updating `.in` files:

```bash
make sync-pyproject
```

## UI Quickstart

### Streamlit UI (interactive, in browser)

- Install dependencies (choose one):
  - Option A: using pip‑tools
    - `pip-compile requirements/streamlit.in -o requirements/streamlit.txt`
    - `pip install -r requirements/streamlit.txt`  # contains base via `-r base.in`
  - Option B: directly from the precompiled lockfile
    - `pip install -r requirements/streamlit.txt`

- Run Streamlit:
  - `python3 -m module --streamlit`

- Features:
  - Engine switcher (Kerykeion default vs JPL/Skyfield) in Advanced settings.
  - Default JPL ephemeris file: `source/de421.bsp` (override via the ephemeris path field).
  - Standardized Radix chart rendered with Plotly interactively.

### Kivy UI (desktop app)

- Install dependencies (choose one):
  - Option A: using pip‑tools
    - `pip-compile requirements/kivy.in -o requirements/kivy.txt`
    - `pip install -r requirements/kivy.txt`  # contains base via `-r base.in`
  - Option B: directly from the precompiled lockfile
    - `pip install -r requirements/kivy.txt`

- Enable embedded interactive Plotly inside Kivy (recommended):
  - Install Kivy Garden tooling and the WebView widget:
    - `pip install kivy-garden`
    - `garden install kivy_garden.webview`
  - If WebView is unavailable, the app falls back to opening the chart in the browser.

- Run Kivy:
  - `python3 -m module --kivy`

- Features:
  - JPL engine toggle in the top toolbar (JPL on/off).
  - Standardized Radix chart renderer.
  - Default JPL ephemeris file path: `source/de421.bsp`.

### Troubleshooting

- Unknown class `WebView` in KV:
  - Install the widget via Kivy Garden: `pip install kivy-garden` then `garden install kivy_garden.webview`.
  - Alternatively, rely on the browser fallback.

- Kerykeion Geonames warning:
  - Set a custom geonames username to avoid default shared rate limits. See the Kerykeion docs.

- JPL not active / ephemeris file not found:
  - Ensure `skyfield` is installed and that `source/de421.bsp` is present.
  - You can change the path in Advanced settings (Streamlit) or in Kivy code.

- Streamlit not updating:
  - Clear the browser cache or stop/restart the Streamlit server.

## Generating Documentation

The Hugo site sources live under `docs/site/` and the build output is written to `docs/`.

### 1) Generate auto-docs

```bash
# Create docs venv (includes extras needed for doc export)
make venv-docs
source venv-docs/bin/activate

# Generate docs/site/content/auto, docs/site/content/models.mmd, docs/site/content/enums.md
make docs
```

If you created `venv-docs` before syncing `pyproject.toml`, re-run
`make venv-docs` to force-reinstall dependencies (this installs new base deps
like `duckdb`).

### 2) Run Hugo locally

```bash
# From repo root
hugo server --source docs/site --config hugo.toml --baseURL http://localhost:1313/ --appendPort=false
```

This serves the docs site locally at http://localhost:1313.
If you skip the override, Hugo uses the GitHub Pages baseURL and you'll need
to open http://localhost:1313/function-wrapper/ instead.

### 3) Build static site

```bash
hugo --source docs/site --config hugo.toml --destination docs
```

The static site is generated in `docs/` (the GitHub Pages publishing root).

### 4) GitHub Pages checklist (docs folder hosting)

- Repository Settings → Pages → Source: **Deploy from a branch**
- Branch: `main` (or your default branch)
- Folder: `/docs`
- Save and wait for the Pages deployment to finish

Notes:
- `docs/` contains the built site; Hugo sources live in `docs/site/`.
- Because the source tree is under `docs/`, the raw source files are also publicly visible.
