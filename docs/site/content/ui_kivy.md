---
title: "Kivy UI"
description: "Desktop application for native chart rendering"
weight: 6
---

# Kivy UI

The Kivy UI provides a native desktop application for astrological chart visualization with embedded interactive charts.

![Kivy UI Example](../example_kivy.png)

## How to Run

### Prerequisites

Install Kivy and required dependencies:

```bash
pip install -r requirements/kivy.txt
```

For embedded interactive Plotly charts, install the WebView widget:

```bash
pip install kivy-garden
garden install kivy_garden.webview
```

### Starting the Application

Run the Kivy interface:

```bash
python -m module --kivy
```

### Features

- Native desktop application
- Embedded interactive Plotly charts (with WebView)
- JPL engine toggle
- Standardized Radix chart renderer
- Cross-platform support (Windows, macOS, Linux)

### Configuration

- Default JPL ephemeris file: `source/de421.bsp`
- Chart files are saved to the workspace directory
- If WebView is unavailable, charts open in the default browser

### Troubleshooting

- **Unknown class `WebView`**: Install via `garden install kivy_garden.webview`
- **JPL not active**: Ensure `skyfield` is installed and `source/de421.bsp` exists
- **Chart opens in browser**: WebView widget not installed (this is a fallback behavior)
