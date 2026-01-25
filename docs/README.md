# Documentation

This directory contains documentation for using the Kefer Astrology sidecar module.

## User Documentation

### References
- **`cli_reference.md`** - Complete CLI command reference
- **`installation.md`** - Environment setup and venv strategy
- **`architecture.md`** - System architecture (includes storage responsibilities)

### Auto-Generated Docs
- **`auto/`** - Module documentation generated from docstrings
  - `auto/cli.md` - CLI module
  - `auto/storage.md` - Storage module
  - `auto/services.md` - Services module
  - `auto/workspace.md` - Workspace module
  - etc.

## Developer Documentation

- **`architecture.md`** - System architecture overview
- **`enums.md`** - Enumeration reference
- **`models.mmd`** - Mermaid class diagram
- **`installation.md`** - Environment setup and doc generation
- **`testing_guide.md`** - How to write and run tests

## Generating Documentation

### Auto-Generate Docs
```bash
make docs
```

This generates:
- `docs/site/content/auto/*.md` - Module API documentation from docstrings
- `docs/site/content/models.mmd` - Class diagram
- `docs/site/content/enums.md` - Enum reference

### Serve Docs Locally (Hugo)
```bash
hugo server --source docs/site --config hugo.toml --baseURL http://localhost:1313/ --appendPort=false
```

Hugo sources live under `docs/site/` and the built site is written to `docs/` via `--destination docs`.
Full setup steps are in `installation.md` under "Generating Documentation".

### Manual Documentation
User guides and integration docs are maintained manually in this directory.

When linking images from content pages, prefer `../example.png` so links resolve at the site root during local and hosted builds.

## Quick Links

- **For Installation**: See `installation.md`
- **For CLI Usage**: See `cli_reference.md`
- **For Storage**: See `architecture.md`
- **For Reference**: See `auto/` directory
