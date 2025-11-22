from __future__ import annotations

import inspect
from dataclasses import is_dataclass, fields
from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Any
import importlib
import sys
import re

ModuleSpec = Tuple[str, object]


def _ensure_import_compat():
    """Ensure 'module' package is available in sys.modules.
    
    The actual module aliasing is done in _load_target_modules() in dependency order.
    """
    # Ensure 'module' package itself is available
    try:
        import module
        sys.modules.setdefault("module", module)
    except Exception:
        pass


def _load_target_modules() -> List[ModuleSpec]:
    """Load target modules using the same import pattern as workspace.py:
    try 'module.X' first, then fall back to 'X' if that fails.
    
    We import in dependency order and set up aliases immediately so that
    modules can use 'from utils import ...' style imports.
    """
    targets: List[ModuleSpec] = []
    
    # Import in dependency order: models -> utils -> z_visual -> services -> workspace -> others
    # This ensures dependencies are available when needed
    # Note: services depends on z_visual, so z_visual must come before services
    # Skip ui_kivy in CI environments where X server is not available
    # It will be handled gracefully by the import error handling below
    dependency_order = ["models", "utils", "z_visual", "services", "workspace", "ui_streamlit", "ui_kivy"]
    
    # Helper to create a stub module
    def _create_stub_module(module_name):
        """Create a stub module that allows imports to proceed."""
        class _StubObject:
            """Stub object that can be used as a placeholder for any attribute."""
            def __getattr__(self, attr):
                return _StubObject()
            def __call__(self, *args, **kwargs):
                return _StubObject()
        
        class _StubModule:
            """Stub module to allow fallback imports to work."""
            __name__ = module_name
            __file__ = f"<stub for {module_name}>"
            __path__ = []
            __package__ = module_name
            __spec__ = None
            __loader__ = None
            
            def __getattr__(self, attr):
                # Return a stub object for any attribute access
                # This allows 'from utils import Actual' to work
                return _StubObject()
        
        return _StubModule()
    
    for name in dependency_order:
        mod = None
        error = None
        
        # Try module.X first (like workspace.py does)
        first_error = None
        error = None
        
        try:
            mod = importlib.import_module(f"module.{name}")
            # Immediately set up alias so 'from X import ...' works in other modules
            sys.modules[name] = mod
        except (ImportError, ModuleNotFoundError, OSError) as e1:
            # Store the first error - this is more likely to have the real dependency issue
            # OSError catches kivy initialization failures (X server, libmtdev, etc.)
            first_error = e1
            error = first_error  # Set error in case both imports fail
            
            # Fall back to X (for when running as package or direct import)
            # Try this BEFORE creating stub, so we don't interfere with the import
            try:
                real_mod = importlib.import_module(name)
                # If this succeeds, use the real module
                sys.modules[name] = real_mod
                mod = real_mod
                error = None  # Clear error since import succeeded
            except Exception as e2:
                # Both failed, create stub so other modules can import it
                stub = _create_stub_module(name)
                sys.modules[name] = stub
                mod = stub
                error = first_error  # Keep first error
        
        # Check if we successfully imported a real module (not a stub)
        is_stub = mod is not None and hasattr(mod, '__file__') and isinstance(mod.__file__, str) and mod.__file__.startswith("<stub")
        if mod is not None and not is_stub:
            targets.append((name, mod))
        elif error is not None:
            # Represent missing module with a stub message
            # Extract the root cause error (often a missing dependency)
            error_msg = str(error)
            
            # For ModuleNotFoundError, extract the missing module name
            import re
            match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_msg)
            if match:
                missing_module = match.group(1)
                # Only show as "missing dependency" if it's not the module itself
                # (e.g., if importing module.utils fails because geopy is missing, show geopy)
                if missing_module not in (name, f"module.{name}"):
                    error_msg = f"Missing dependency: {missing_module}"
            
            class _Stub:
                __name__ = f"module.{name}"
                __doc__ = f"Failed to import module.{name}: {error_msg}"
            targets.append((name, _Stub))
    
    return targets


# Expose a stable list of target modules for consumers like tests
TARGET_MODULES: List[ModuleSpec] = _load_target_modules()


def _md_escape(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _parse_docstring(doc: str) -> Dict[str, Any]:
    """Parse a docstring into structured sections.
    
    Extracts:
    - Summary (first paragraph)
    - Parameters section
    - Returns section
    - Examples section
    - Notes/Warnings sections
    - Full description
    """
    if not doc:
        return {}
    
    doc = inspect.cleandoc(doc)
    lines = doc.splitlines()
    
    result = {
        "summary": "",
        "description": "",
        "parameters": [],
        "returns": "",
        "examples": [],
        "notes": [],
        "warnings": [],
        "full": doc
    }
    
    # Extract summary (first paragraph)
    summary_lines = []
    for line in lines:
        if line.strip() and not line.strip().startswith(("Parameters:", "Returns:", "Examples:", "Example:", "Note:", "Notes:", "Warning:", "Warnings:", "Args:", "Returns:", "Raises:")):
            summary_lines.append(line)
        else:
            break
    result["summary"] = "\n".join(summary_lines).strip()
    result["description"] = doc  # Full docstring as description
    
    # Parse structured sections
    current_section = None
    current_content = []
    summary_done = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        
        # Detect section headers (must be at start of line or after summary)
        if line_lower.startswith(("parameters:", "args:", "arguments:")):
            if current_section == "parameters" and current_content:
                result["parameters"] = _parse_parameters_section("\n".join(current_content))
            current_section = "parameters"
            current_content = []
            summary_done = True
            continue
        elif line_lower.startswith(("returns:", "return:")):
            # Stop parameter parsing if we're in parameters section
            if current_section == "parameters" and current_content:
                result["parameters"] = _parse_parameters_section("\n".join(current_content))
            elif current_section == "returns" and current_content:
                result["returns"] = "\n".join(current_content).strip()
            current_section = "returns"
            current_content = []
            summary_done = True
            # Handle case where "Returns" text appears on same line as last parameter
            if ":" in line_stripped and len(line_stripped.split(":", 1)) > 1:
                # Extract the returns text after the colon
                returns_text = line_stripped.split(":", 1)[1].strip()
                if returns_text:
                    current_content.append(returns_text)
            continue
        elif line_lower.startswith(("examples:", "example:")):
            if current_section == "parameters" and current_content:
                result["parameters"] = _parse_parameters_section("\n".join(current_content))
            elif current_section == "returns" and current_content:
                result["returns"] = "\n".join(current_content).strip()
            current_section = "examples"
            current_content = []
            summary_done = True
            continue
        elif line_lower.startswith(("notes:", "note:")):
            if current_section and current_content:
                _flush_section(result, current_section, current_content)
            current_section = "notes"
            current_content = []
            summary_done = True
            continue
        elif line_lower.startswith(("warnings:", "warning:", "raises:")):
            if current_section and current_content:
                _flush_section(result, current_section, current_content)
            current_section = "warnings"
            current_content = []
            summary_done = True
            continue
        
        if current_section:
            current_content.append(line)
        elif not summary_done:
            # Still building summary - stop at first section header or blank line followed by section
            if line_stripped and not line_stripped.lower().startswith(("parameters:", "returns:", "examples:", "notes:", "warnings:")):
                # Continue building summary
                pass
            elif not line_stripped and i + 1 < len(lines):
                # Check if next line is a section header
                next_line_lower = lines[i + 1].strip().lower()
                if next_line_lower.startswith(("parameters:", "returns:", "examples:", "notes:", "warnings:")):
                    summary_done = True
                    continue
    
    # Flush last section
    if current_section and current_content:
        _flush_section(result, current_section, current_content)
    
    return result


def _flush_section(result: Dict[str, Any], section: str, content: List[str]):
    """Flush accumulated content to the appropriate result section."""
    content_str = "\n".join(content).strip()
    if section == "parameters":
        result["parameters"] = _parse_parameters_section(content_str)
    elif section == "returns":
        result["returns"] = content_str
    elif section == "examples":
        result["examples"].append(content_str)
    elif section == "notes":
        result["notes"].append(content_str)
    elif section == "warnings":
        result["warnings"].append(content_str)


def _parse_parameters_section(content: str) -> List[Dict[str, str]]:
    """Parse a Parameters/Args section into a list of parameter dicts.
    
    Handles formats like:
    - name: description
    - name (type): description
    - name: description (with multiple lines)
    - - name: description (with dash prefix)
    """
    params = []
    import re
    
    lines = content.splitlines()
    current_param = None
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            if current_param:
                # Empty line might separate parameters, but continue current if it looks incomplete
                pass
            continue
        
        # Check if this looks like a parameter definition
        # Format: "- name: description" (most common in docstrings)
        # Also: "name: description" or "name (type): description"
        # Pattern: optional dash/bullet, param name, optional (type), colon, description
        match = re.match(r'^[-*]?\s*(\w+)(?:\s*\(([^)]+)\))?\s*:\s*(.+)$', line_stripped)
        if match:
            # Save previous param if exists
            if current_param:
                params.append(current_param)
            # Start new param
            param_name = match.group(1)
            param_type = match.group(2) if match.group(2) else ""
            param_desc = match.group(3).strip()
            current_param = {"name": param_name, "description": param_desc, "type": param_type}
        elif current_param and line_stripped:
            # Continuation of current parameter description
            # Stop if we hit a section header (must have colon, like "Returns:" not just "Returns")
            line_lower = line_stripped.lower()
            if line_lower.startswith(("returns:", "return:", "examples:", "example:", "notes:", "note:", "warnings:", "warning:", "raises:")):
                # Save current param and stop parsing
                params.append(current_param)
                break
            # Also stop if line starts with "Returns" (without colon) and doesn't look like a parameter
            # This handles cases like "Returns a mapping: ..."
            if line_lower.startswith("returns") and not re.match(r'^[-*]?\s*\w+\s*[:\(]', line_stripped):
                # Save current param and stop parsing
                params.append(current_param)
                break
            # Only continue if it doesn't look like a new parameter
            if not re.match(r'^[-*]?\s*\w+\s*[:\(]', line_stripped):
                current_param["description"] += " " + line_stripped
            else:
                # Looks like a new parameter, save current and start new
                params.append(current_param)
                current_param = None
                # Try to parse this line as a new parameter
                match = re.match(r'^[-*]?\s*(\w+)(?:\s*\(([^)]+)\))?\s*:\s*(.+)$', line_stripped)
                if match:
                    param_name = match.group(1)
                    param_type = match.group(2) if match.group(2) else ""
                    param_desc = match.group(3).strip()
                    current_param = {"name": param_name, "description": param_desc, "type": param_type}
        else:
            # Might be a different format, try to parse
            # Format: "param_name - description"
            alt_match = re.match(r'^[-*]?\s*(\w+)\s*-\s*(.+)$', line_stripped)
            if alt_match:
                if current_param:
                    params.append(current_param)
                current_param = {"name": alt_match.group(1), "description": alt_match.group(2), "type": ""}
    
    # Only append if we haven't already (check if last param is different)
    if current_param:
        # Avoid duplicates - check if this is the same as the last param
        if not params or params[-1]["name"] != current_param["name"]:
            params.append(current_param)
    
    return params


def _render_signature(obj) -> str:
    try:
        sig = inspect.signature(obj)
        return f"`{obj.__name__}{sig}`"
    except Exception:
        return f"`{obj.__name__}()`"


def _render_function_detailed(func) -> str:
    """Render a function with full docstring details."""
    parts = []
    parts.append(f"### `{func.__name__}`\n")
    
    # Get signature without backticks for code block
    try:
        sig = inspect.signature(func)
        sig_str = f"{func.__name__}{sig}"
    except Exception:
        sig_str = f"{func.__name__}()"
    
    parts.append(f"```python\n{sig_str}\n```\n")
    
    doc = inspect.getdoc(func)
    if doc:
        parsed = _parse_docstring(doc)
        
        # Summary/Description
        if parsed.get("summary"):
            parts.append(f"{_md_escape(parsed['summary'])}\n")
        elif parsed.get("full"):
            # Use first paragraph as summary
            first_para = parsed["full"].split("\n\n")[0]
            parts.append(f"{_md_escape(first_para)}\n")
        
        # Parameters
        if parsed.get("parameters"):
            parts.append("#### Parameters\n")
            for param in parsed["parameters"]:
                param_type = f" ({param['type']})" if param.get("type") else ""
                parts.append(f"- **{param['name']}**{param_type}: {_md_escape(param['description'])}\n")
            parts.append("")
        
        # Returns
        if parsed.get("returns"):
            parts.append("#### Returns\n")
            parts.append(f"{_md_escape(parsed['returns'])}\n\n")
        
        # Examples
        if parsed.get("examples"):
            parts.append("#### Examples\n")
            for example in parsed["examples"]:
                parts.append(f"```python\n{_md_escape(example)}\n```\n")
            parts.append("")
        
        # Notes
        if parsed.get("notes"):
            parts.append("#### Notes\n")
            for note in parsed["notes"]:
                parts.append(f"{_md_escape(note)}\n")
            parts.append("")
        
        # Warnings
        if parsed.get("warnings"):
            parts.append("#### Warnings\n")
            for warning in parsed["warnings"]:
                parts.append(f"⚠️ {_md_escape(warning)}\n")
            parts.append("")
    
    return "\n".join(parts).rstrip() + "\n"


def _iter_public_functions(mod) -> Iterable[object]:
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("_"):
            continue
        if getattr(obj, "__module__", None) != getattr(mod, "__name__", None):
            continue
        yield obj


def _iter_public_classes(mod) -> Iterable[type]:
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if name.startswith("_"):
            continue
        if getattr(obj, "__module__", None) != getattr(mod, "__name__", None):
            continue
        yield obj


def _render_class(cls: type) -> str:
    parts: List[str] = []
    bases = [b.__name__ for b in cls.__bases__ if b is not object]
    base_str = f"({', '.join(bases)})" if bases else ""
    parts.append(f"### class `{cls.__name__}` {base_str}\n")
    if cls.__doc__:
        parts.append(_md_escape(inspect.cleandoc(cls.__doc__)) + "\n")
    # Methods
    methods = [
        m for _, m in inspect.getmembers(cls, inspect.isfunction)
        if not m.__name__.startswith("_") and m.__qualname__.split(".")[0] == cls.__name__
    ]
    if methods:
        parts.append("#### Methods\n")
        for m in sorted(methods, key=lambda o: o.__name__):
            parts.append(f"- {_render_signature(m)}")
            doc = inspect.getdoc(m)
            if doc:
                parts.append(f"  \n  {_md_escape(doc.splitlines()[0])}")
            parts.append("")
    # Dataclass fields
    if is_dataclass(cls):
        parts.append("#### Dataclass fields\n")
        for f in fields(cls):
            parts.append(f"- `{f.name}: {getattr(f.type, '__name__', f.type)}`")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def generate_module_markdown(name: str, mod, add_frontmatter: bool = False) -> str:
    """Produce a Markdown overview for a module: intro, functions, classes.
    
    Args:
        name: Module name
        mod: Module object
        add_frontmatter: If True, add Hugo frontmatter
    """
    lines: List[str] = []
    
    # Hugo frontmatter
    if add_frontmatter:
        lines.append("---\n")
        lines.append(f"title: {name} Module\n")
        lines.append(f"description: API documentation for {name} module\n")
        lines.append("weight: 10\n")
        lines.append("---\n\n")
    
    lines.append(f"# `{name}` module\n")
    if getattr(mod, "__doc__", None):
        mod_doc = inspect.cleandoc(mod.__doc__)
        lines.append(_md_escape(mod_doc) + "\n")

    # Functions
    funcs = sorted(list(_iter_public_functions(mod)), key=lambda o: o.__name__)
    if funcs:
        lines.append("## Functions\n")
        for f in funcs:
            lines.append(_render_function_detailed(f))

    # Classes
    classes = sorted(list(_iter_public_classes(mod)), key=lambda c: c.__name__)
    if classes:
        lines.append("## Classes\n")
        for cls in classes:
            lines.append(_render_class(cls))

    # Cross-reference note for UI modules
    if name in ("ui_kivy", "ui_streamlit"):
        lines.append("## How the UI is invoked\n")
        entry = None
        # Heuristic: prefer 'run' or 'main'
        for cand in ("run", "main"):
            if hasattr(mod, cand) and inspect.isfunction(getattr(mod, cand)):
                entry = getattr(mod, cand)
                break
        if entry is not None:
            lines.append(f"Entry point: {_render_signature(entry)}\n")
        else:
            lines.append("Entry point: not detected\n")

    return "\n".join(lines).rstrip() + "\n"


def write_all(out_dir: Path | str = "docs/auto", add_frontmatter: bool = False) -> List[Path]:
    """Write all module documentation to files.
    
    Args:
        out_dir: Output directory for markdown files
        add_frontmatter: If True, add Hugo frontmatter to each file
    """
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for name, mod in TARGET_MODULES:
        content = generate_module_markdown(name, mod, add_frontmatter=add_frontmatter)
        p = out_root / f"{name}.md"
        p.write_text(content, encoding="utf-8")
        written.append(p)
    return written


def main(argv: List[str] | None = None) -> int:
    import argparse
    import os
    
    # Set KIVY_NO_ARGS=1 to prevent Kivy from intercepting command-line arguments
    # This is needed because ui_kivy.py imports Kivy, which has its own argument parser
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    
    parser = argparse.ArgumentParser(description="Export Markdown docs for selected modules")
    parser.add_argument("--out", default="docs/auto", help="Output directory (default: docs/auto)")
    parser.add_argument("--hugo", action="store_true", help="Add Hugo frontmatter to generated files")
    args = parser.parse_args(argv)
    written = write_all(args.out, add_frontmatter=args.hugo)
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
