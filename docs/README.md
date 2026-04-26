# Documentation

This directory contains documentation for using the Kefer Astrology sidecar module.

## User Documentation

### References
- **`docs/site/content/readme.md`** - Project overview and quickstart
- **`docs/site/content/installation.md`** - Environment setup and venv strategy
- **`docs/site/content/architecture.md`** - System architecture (includes storage responsibilities)
- **`docs/site/content/cli_reference.md`** - Complete CLI command reference
- **`docs/site/content/fastapi_tauri.md`** - Recommended integration for React + FastAPI + Tauri

### Auto-Generated Docs
- **`auto/`** - Module documentation generated from docstrings
  - `auto/cli.md` - CLI module
  - `auto/storage.md` - Storage module
  - `auto/services.md` - Services module
  - `auto/workspace.md` - Workspace module
  - etc.

## Developer Documentation

- **`docs/site/content/enums.md`** - Enumeration reference
- **`docs/site/content/models.mmd`** - Mermaid class diagram
- **`docs/site/content/testing_guide.md`** - How to write and run tests

## Generating Documentation

### Auto-Generate Docs
```bash
make docs
```

This generates:
- `docs/site/content/auto/*.md` - Module API documentation from docstrings
- `docs/site/content/models.mmd` - Class diagram
- `docs/site/content/enums.md` - Enum reference

`make docs` only refreshes Hugo content sources. It does not build or serve the
HTML site by itself.

### Serve Docs Locally (Hugo)
```bash
hugo server --source docs/site --config hugo.toml --baseURL http://localhost:1313/ --appendPort=false
```

Open `http://localhost:1313/function-wrapper/` in a browser when using the
configured `baseURL`.

If you build static files locally with plain `hugo`, the generated site will be
written to `docs/site/public/` by default. The repository-level `docs/README.md`
is just a guide for humans, not the rendered Hugo homepage.

### Build For GitHub Pages From `docs/`
```bash
make docs-build-pages
```

This builds the static site directly into `docs/` using the default Pages URL
for this repository:

`https://kefer-astrology.github.io/function-wrapper/`

If you need a different GitHub Pages URL, override it at build time:

```bash
make docs-build-pages PAGES_BASE_URL="https://your-user.github.io/your-repo/"
```

GitHub Pages uses a special build step that outputs the final site into `docs/`
for deployment, while preserving `docs/site/` as the Hugo source tree.
Full setup steps are in `installation.md` under "Generating Documentation".

### Manual Documentation
User guides and integration docs are maintained manually under
`docs/site/content/` so the Hugo site is the main documentation source of
truth.

When linking images from content pages, prefer `../example.png` so links resolve at the site root during local and hosted builds.

## Quick Links

- **For Project Overview**: See `docs/site/content/readme.md`
- **For Installation**: See `docs/site/content/installation.md`
- **For CLI Usage**: See `docs/site/content/cli_reference.md`
- **For React/FastAPI/Tauri Integration**: See `docs/site/content/fastapi_tauri.md`
- **For Storage**: See `docs/site/content/architecture.md`
- **For API Reference**: See `docs/site/content/auto/`
