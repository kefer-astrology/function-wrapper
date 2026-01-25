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

# 3. Run the application
python3 -m module --streamlit  # Streamlit UI (browser)
python3 -m module --kivy  # Kivy UI (desktop)
python3 -m module --tui   # Text UI (terminal)
python3 -m module         # Default: TUI
```

For detailed setup instructions, troubleshooting, and advanced options, see the [Installation manual](./docs/site/content/installation.md).

You can also explore [Documentation](./docs/README.md) to see more detailed overview.

## How it works

All the heavy lifting is made by a module [g-battaglia/kerykeion](https://github.com/g-battaglia/kerykeion), manipulation layer over [astrorigin/pyswisseph](https://github.com/astrorigin/pyswisseph) (also known as [swiss ephemerides](https://www.astro.com/swisseph/swephinfo_e.htm)), thus the license is inherited (GNU Affero GPL v3.0). Other dependencies are mentioned in the [requirements file](./requirements/base.in).

For NASA JPL ephemerides we use [skyfielders/python-skyfield](https://github.com/skyfielders/python-skyfield) which comes with MIT license.


### High Level System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                             UI Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Streamlit UI │  │  Kivy UI     │  │   CLI/TUI    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
│                    ┌───────▼────────┐                            │
│                    │  module.* APIs │                            │
│                    │  - services    │                            │
│                    │  - workspace   │                            │
│                    │  - storage     │                            │
│                    └───────┬────────┘                            │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                             │ Python calls (in-process)
                             │
┌────────────────────────────▼──────────────────────────────────────┐
│                         Backend (Python)                           │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    Core Modules                             │   │
│  │  - module.services                                        │   │
│  │  - module.workspace                                       │   │
│  │  - module.storage (optional)                              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────┼──────────────────────────┐          │
│  │                          │                           │          │
│  │  ┌──────────────┐       │      ┌──────────────┐    │          │
│  │  │  DuckDB      │       │      │   YAML       │    │          │
│  │  │  Storage     │       │      │   Workspace  │    │          │
│  │  └──────┬───────┘       │      └──────┬───────┘    │          │
│  │         │               │             │              │          │
│  │  ┌──────▼──────────┐    │    ┌───────▼────────┐    │          │
│  │  │ workspace.db    │    │    │ workspace.yaml │    │          │
│  │  │ - positions     │    │    │ charts/*.yaml  │    │          │
│  │  │ - metadata      │    │    │ subjects/*.yaml│    │          │
│  │  └─────────────────┘    │    └────────────────┘    │          │
│  │         │               │                           │          │
│  │  ┌──────▼──────────┐    │                           │          │
│  │  │ parquet/        │    │                           │          │
│  │  │ - chart_*.parquet│    │                           │          │
│  │  └─────────────────┘    │                           │          │
│  └──────────────────────────┼──────────────────────────┘          │
└─────────────────────────────┼──────────────────────────────────────┘
                               │
                               │ Files on disk
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                         Local File System                            │
│                                                                       │
│  workspace/                                                          │
│  ├── workspace.yaml          (Metadata)                             │
│  ├── charts/                  (Chart definitions)                     │
│  │   ├── chart_001.yaml                                              │
│  │   └── chart_002.yaml                                              │
│  ├── subjects/                (Subject definitions)                  │
│  │   └── subject_001.yaml                                           │
│  └── data/                    (Computed data)                         │
│      ├── workspace.db        (DuckDB)                                │
│      └── parquet/            (Parquet files)                          │
│          ├── chart_001.parquet                                       │
│          └── chart_002.parquet                                       │
└───────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Chart Creation

```
User Input
    │
    ▼
┌─────────────────┐
│  UI/CLI Input   │  (Name, Date, Location, Settings)
└────────┬────────┘
         │
         │ build chart + workspace
         ▼
┌─────────────────┐
│  module.workspace│
│  - load/save     │
│  - chart config  │
└────────┬────────┘
         │
         ├──► module.services.compute_positions
         │
         └──► module.storage (optional)
              │
              ▼
         ┌─────────────────┐
         │  DuckDB/Parquet │
         │  - positions     │
         └────────┬────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  Return to UI   │
         │  - chart_id      │
         │  - positions     │
         └─────────────────┘
```

## Data Flow: Transit Computation

```
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

```
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

