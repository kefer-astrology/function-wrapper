# Documentation

This directory contains auto-generated API documentation for the Kefer Astrology function-wrapper project.

## Files

- **`auto/`** - Module documentation with Hugo frontmatter
- **`models.mmd`** - Mermaid class diagram showing all dataclasses
- **`enums.md`** - Complete enumeration overview
- **`_index.md`** - Hugo index page

## Hugo Integration

### Mermaid Diagrams

To embed the Mermaid diagram in Hugo, you have several options:

1. **Direct inclusion** (if Hugo theme supports Mermaid):
   ```markdown
   ```mermaid
   {{< readfile "docs/models.mmd" >}}
   ```
   ```

2. **Using Hugo shortcode** (create `layouts/shortcodes/mermaid.html`):
   ```html
   {{ $content := .Inner }}
   <div class="mermaid">
   {{ $content }}
   </div>
   ```

3. **Using external Mermaid renderer**:
   - Install a Hugo theme that supports Mermaid (e.g., `hugo-theme-techdoc`)
   - Or use a JavaScript library like `mermaid.js` in your theme

### GitHub Pages Deployment

The GitHub Action automatically:
1. Generates all documentation on push to `main`
2. Commits the generated files back to the repository
3. Files are ready for Hugo to process

To deploy with Hugo:
1. Configure GitHub Pages to use Hugo
2. Set the source to `/docs` directory
3. Hugo will process all `.md` files with frontmatter

## Manual Generation

To generate documentation locally:

```bash
# Activate your venv
source venv/bin/activate

# Generate all docs
make docs

# Or manually:
KIVY_NO_ARGS=1 python -m devtools.docs_export --out docs/auto --hugo
python -m devtools.diagram_export --out docs/models.mmd --enums-out docs/enums.md
```

