---
title: "Streamlit UI"
description: "Web-based interface for interactive chart creation"
weight: 5
---

# Streamlit UI

The Streamlit UI provides a web-based interface for creating and visualizing astrological charts.

![Streamlit UI Example](../example_streamlit.png)

## How to Run

### Prerequisites

Install Streamlit and required dependencies:

```bash
pip install -r requirements/streamlit.txt
```

### Starting the Application

Run the Streamlit interface:

```bash
python -m module --streamlit
```

Or directly:

```bash
streamlit run module/ui_streamlit.py
```

### Features

- Interactive chart creation
- Real-time position calculations
- Aspect visualization
- Workspace management
- Chart export capabilities

### Configuration

The Streamlit UI uses the workspace configuration from `workspace.yaml`. You can customize settings through the UI's advanced options panel.
