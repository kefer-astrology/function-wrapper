---
title: "Project Overview"
description: "Repository overview, quickstart, and high-level architecture"
weight: 2
---

# Function layer for Kefer Astrology

## Quickstart

Get up and running in 3 steps:

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
# alternatively use makefile
source ./venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# 2. Install dependencies (choose your UI)
pip install -r requirements/base.txt  # for base package
pip install -r requirements/streamlit.txt  # For Streamlit UI (browser)
pip install -r requirements/kivy.txt  # For Kivy UI (desktop)

# Or install by package extras
pip install .  # core computation/storage package
pip install .[api]  # FastAPI backend for Tauri/web frontends
pip install .[streamlit]  # Streamlit UI + chart rendering
pip install .[kivy]  # Kivy desktop UI + chart rendering

# 3. Run the application
python3 -m module --streamlit  # Streamlit UI (browser)
python3 -m module --kivy  # Kivy UI (desktop)
python3 -m module --tui   # Text UI (terminal)
python3 -m module         # Default: TUI
```

For detailed setup instructions, troubleshooting, and advanced options, see the
[Installation and Venvs](installation).

## Suggested Runtime Split

- `core`: install `pip install .` for computation, workspace, and storage helpers
- `api`: install `pip install .[api]` for a FastAPI sidecar/backend without UI dependencies
- `streamlit`: install `pip install .[streamlit]` for the browser UI
- `kivy`: install `pip install .[kivy]` for the native Python desktop UI

For a `React frontend from Figma + FastAPI backend + Tauri packaging` setup,
prefer `core + api` and keep the `ui_*` modules as optional developer-only
frontends. See [FastAPI + React + Tauri](fastapi_tauri).

## How it works

All the heavy lifting is made by
[g-battaglia/kerykeion](https://github.com/g-battaglia/kerykeion), a
manipulation layer over
[astrorigin/pyswisseph](https://github.com/astrorigin/pyswisseph) (also known
as [Swiss Ephemerides](https://www.astro.com/swisseph/swephinfo_e.htm)), thus
the license is inherited (GNU Affero GPL v3.0). Other dependencies are tracked
in `requirements/base.in`.

For NASA JPL ephemerides we use
[skyfielders/python-skyfield](https://github.com/skyfielders/python-skyfield),
which is MIT-licensed.

## High Level System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                             UI Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Streamlit UI │  │  Kivy UI     │  │   CLI/TUI    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                    ┌───────▼────────┐                           │
│                    │  module.* APIs │                           │
│                    │  - services    │                           │
│                    │  - workspace   │                           │
│                    │  - storage     │                           │
│                    └───────┬────────┘                           │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             │ Python calls (in-process)
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                         Backend (Python)                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Core Modules                           │  │
│  │  - module.services                                        │  │
│  │  - module.workspace                                       │  │
│  │  - module.storage (optional)                              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────┐         │
│  │                          │                           │         │
│  │  ┌──────────────┐        │      ┌──────────────┐    │         │
│  │  │  DuckDB      │        │      │   YAML       │    │         │
│  │  │  Storage     │        │      │   Workspace  │    │         │
│  │  └──────┬───────┘        │      └──────┬───────┘    │         │
│  │         │                │             │            │         │
│  │  ┌──────▼──────────┐     │    ┌───────▼────────┐    │         │
│  │  │ workspace.db    │     │    │ workspace.yaml │    │         │
│  │  │ - positions     │     │    │ charts/*.yaml  │    │         │
│  │  │ - metadata      │     │    │ subjects/*.yaml│    │         │
│  │  └─────────────────┘     │    └────────────────┘    │         │
│  │         │                │                           │         │
│  │  ┌──────▼──────────┐     │                           │         │
│  │  │ parquet/        │     │                           │         │
│  │  │ - chart_*.parquet│    │                           │         │
│  │  └─────────────────┘     │                           │         │
│  └──────────────────────────┼───────────────────────────┘         │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
                              │ Files on disk
                              │
┌─────────────────────────────▼─────────────────────────────────────┐
│                         Local File System                         │
│                                                                   │
│  workspace/                                                       │
│  ├── workspace.yaml          (Metadata)                           │
│  ├── charts/                  (Chart definitions)                 │
│  │   ├── chart_001.yaml                                           │
│  │   └── chart_002.yaml                                           │
│  ├── subjects/                (Subject definitions)               │
│  │   └── subject_001.yaml                                         │
│  └── data/                    (Computed data)                     │
│      ├── workspace.db        (DuckDB)                             │
│      └── parquet/            (Parquet files)                      │
│          ├── chart_001.parquet                                    │
│          └── chart_002.parquet                                    │
└───────────────────────────────────────────────────────────────────┘
```

## Data Flow: Chart Creation

```text
User Input
    │
    ▼
┌─────────────────┐
│  UI/CLI Input   │  (Name, Date, Location, Settings)
└────────┬────────┘
         │
         │ build chart + workspace
         ▼
┌──────────────────┐
│ module.workspace │
│ - load/save      │
│ - chart config   │
└────────┬─────────┘
         │
         ├──► module.services.compute_positions
         │
         └──► module.storage (optional)
              │
              ▼
         ┌─────────────────┐
         │  DuckDB/Parquet │
         │  - positions    │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Return to UI   │
         │  - chart_id     │
         │  - positions    │
         └─────────────────┘
```

## Data Flow: Transit Computation

```text
User Input
    │
    ▼
┌─────────────────┐
│  Transit Panel  │  (Source chart, Time range, Objects)
└────────┬────────┘
         │
         │ compute series
         ▼
┌─────────────────┐
│ module.services │
│ - series loop   │
│ - positions     │
│ - aspects (on   │
│   demand)       │
└────────┬────────┘
         │
         │ batch store (optional)
         ▼
┌─────────────────┐
│  DuckDB/Parquet │
│  - positions    │
└────────┬────────┘
         │
         │ query results
         ▼
┌─────────────────┐
│  UI Updates     │
│  - Progress     │
│  - Results      │
└─────────────────┘
```

## Storage Schema Relationships

```text
┌──────────────────────────────┐
│  computed_positions          │
│                              │
│  - chart_id                  │
│  - datetime                  │
│  - object_id                 │
│  - longitude/latitude        │
│  - speed/retrograde          │
│  - engine/ephemeris_file     │
│  - ... (optional fields)     │
└──────────────────────────────┘

Aspects are computed on demand from positions (not stored by default).
```
