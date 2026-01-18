# Documentation

This directory contains documentation for using the Kefer Astrology sidecar module.

## User Documentation

### API References
- **`CLI_API_REFERENCE.md`** - Complete CLI command reference
- **`TAURI_SVELTE_INTEGRATION.md`** - How to integrate with Tauri + Svelte frontend
- **`STORAGE_STRATEGY.md`** - When and how to use Python vs Rust storage

### Auto-Generated API Docs
- **`auto/`** - Module documentation generated from docstrings
  - `auto/cli.md` - CLI module API
  - `auto/storage.md` - Storage module API
  - `auto/services.md` - Services module API
  - `auto/workspace.md` - Workspace module API
  - etc.

## Developer Documentation

- **`TESTING_GUIDE.md`** - How to write and run tests
- **`architecture.md`** - System architecture overview
- **`models.mmd`** - Mermaid class diagram
- **`enums.md`** - Enumeration reference

## Generating Documentation

### Auto-Generate API Docs
```bash
make docs
```

This generates:
- `docs/auto/*.md` - Module API documentation from docstrings
- `docs/models.mmd` - Class diagram
- `docs/enums.md` - Enum reference

### Manual Documentation
User guides and integration docs are maintained manually in this directory.

## Quick Links

- **For Tauri Integration**: See `TAURI_SVELTE_INTEGRATION.md`
- **For CLI Usage**: See `CLI_API_REFERENCE.md`
- **For Storage**: See `STORAGE_STRATEGY.md`
- **For API Reference**: See `auto/` directory
