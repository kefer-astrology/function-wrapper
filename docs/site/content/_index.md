---
title: "Kefer Astrology Documentation"
description: "Complete documentation for Kefer Astrology function-wrapper"
weight: 1
mermaid: true
---

Welcome to the auto-generated documentation for the Kefer Astrology function-wrapper project.

## Documentation Structure

- **[Project Overview](readme/)** - Quickstart, runtime split, and high-level system view
- **[Installation and Venvs](installation/)** - Environment setup and multi-venv workflow
- **[Architecture](architecture/)** - Backend responsibilities and storage model
- **[Ephemeris files](ephemeris/)** - BSP catalog, date range overlaps, de440s upgrade, asteroid limitations
- **[FastAPI + React + Tauri](fastapi_tauri/)** - Recommended integration for the target desktop/web stack
- **[Models Overview](models.mmd)** - Generated Mermaid class diagram for all dataclasses and relationships
- **[Enums Overview](enums/)** - Generated enumeration reference
- **User Interfaces**
  - [Streamlit UI](ui_streamlit/) - Web-based interface for interactive chart creation
  - [Kivy UI](ui_kivy/) - Desktop application for native chart rendering
- **Module Documentation**
  - [cli](auto/cli/) - Command-line interface
  - [models](auto/models/) - Data models and types
  - [services](auto/services/) - Core service functions
  - [storage](auto/storage/) - Storage management
  - [utils](auto/utils/) - Utility functions
  - [workspace](auto/workspace/) - Workspace management
  - [z_visual](auto/z_visual/) - Visualization utilities

## Model Class Diagram

The canonical generated diagram is maintained in [models.mmd](models.mmd).
Keeping one generated copy prevents the landing page from drifting from the
Python model reference.
