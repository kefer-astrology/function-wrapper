from __future__ import annotations

import inspect
from dataclasses import is_dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, get_args, get_origin, get_type_hints
from enum import Enum
import typing

# Import the models module we want to reflect
from module import models as models


PRIMITIVES = {str, int, float, bool, datetime}


def _is_dataclass_type(t: Any) -> bool:
    return inspect.isclass(t) and is_dataclass(t)


def _is_enum_type(t: Any) -> bool:
    return inspect.isclass(t) and issubclass(t, Enum)


def _unwrap_optional(t: Any) -> Any:
    """If the type is Union[T, None], return T; otherwise return the original type."""
    origin = get_origin(t)
    # Optional[X] becomes Union[X, NoneType]
    is_union = origin is typing.Union
    # Support PEP 604 unions like X | Y on newer Python (UnionType)
    try:
        from types import UnionType  # type: ignore
        is_union = is_union or (origin is UnionType)
    except Exception:
        pass

    if is_union:
        args = [a for a in get_args(t) if a is not type(None)]  # noqa: E721
        if len(args) == 1:
            return args[0]
    return t


def _render_type(t: Any) -> str:
    # Attempt to render a Python type annotation into the Mermaid-friendly string
    original_t = t
    t = _unwrap_optional(t)
    origin = get_origin(t)
    args = get_args(t)

    if t in PRIMITIVES:
        return t.__name__
    if t is Any:
        return "any"

    if _is_enum_type(t):
        return f"{t.__name__}(Enum)"

    if origin in (list, List):
        inner = _render_type(args[0]) if args else "any"
        return f"List~{inner}~"
    if origin in (dict, Dict):
        key = _render_type(args[0]) if args else "any"
        val = _render_type(args[1]) if len(args) > 1 else "any"
        return f"Dict~{key},{val}~"
    if origin is tuple or origin is Tuple:
        inner = ",".join(_render_type(a) for a in args) if args else ""
        return f"Tuple~{inner}~"
    if inspect.isclass(t):
        return t.__name__

    # Fallback for ForwardRef or string annotations
    return str(original_t).replace("typing.", "")


def _collect_model_types() -> Tuple[List[type], List[type]]:
    """Collect dataclass and enum types from models module in a stable order."""
    dataclasses: List[type] = []
    enums: List[type] = []
    for name, obj in vars(models).items():
        if inspect.isclass(obj):
            if is_dataclass(obj):
                dataclasses.append(obj)
            elif issubclass(obj, Enum) and obj is not Enum:  # Exclude base Enum class
                enums.append(obj)
    dataclasses.sort(key=lambda c: c.__name__)
    enums.sort(key=lambda c: c.__name__)
    return dataclasses, enums


def _field_association_types(anno: Any) -> Iterable[type]:
    """Yield dataclass types referenced by an annotation. Enums are ignored for associations."""
    t = _unwrap_optional(anno)
    origin = get_origin(t)
    args = get_args(t)

    if inspect.isclass(t):
        if _is_dataclass_type(t):
            yield t
        return

    if origin in (list, List, tuple, Tuple):
        for a in args:
            if inspect.isclass(a) and _is_dataclass_type(a):
                yield a
        return

    if origin in (dict, Dict):
        for a in args:
            if inspect.isclass(a) and _is_dataclass_type(a):
                yield a
        return


def generate_mermaid() -> str:
    """Generate a Mermaid classDiagram representing models dataclasses and their links.

    - Emits classes for dataclasses with public fields and types.
    - Fields with enum types are rendered inline as "EnumName(Enum) field_name".
    - Enums are NOT emitted as separate classes; no associations to enums.
    - Emits association arrows only for fields that reference other dataclasses.
    """
    dcs, _enums = _collect_model_types()

    # Prepare type hints for all dataclasses to resolve ForwardRefs
    globalns = vars(models).copy()

    lines: List[str] = []
    lines.append("classDiagram")
    lines.append("")

    # Emit dataclass nodes
    for cls in dcs:
        lines.append("")
        lines.append(f"class {cls.__name__} {{")
        type_hints = get_type_hints(cls, globalns=globalns, localns=globalns)
        for f in fields(cls):
            anno = type_hints.get(f.name, f.type)
            rendered = _render_type(anno)
            # No '+' visibility marker
            lines.append(f"  {rendered} {f.name}")
        lines.append("}")
        lines.append("")

    # Emit associations only between dataclasses
    associations: Set[Tuple[str, str]] = set()
    for cls in dcs:
        type_hints = get_type_hints(cls, globalns=globalns, localns=globalns)
        for f in fields(cls):
            anno = type_hints.get(f.name, f.type)
            for target in _field_association_types(anno):
                associations.add((cls.__name__, target.__name__))

    for a, b in sorted(associations):
        lines.append(f"{a} --> {b}")

    return "\n".join(lines).rstrip() + "\n"


def write_mermaid(path: Path | str = "docs/models.mmd") -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    content = generate_mermaid()
    out.write_text(content, encoding="utf-8")
    return out


# ---- Enum overview (Markdown) ----

def generate_enum_overview_markdown() -> str:
    """Produce a Markdown table listing all Enums and their members with descriptions."""
    _dcs, enums = _collect_model_types()
    lines: List[str] = []
    lines.append("# Enum Overview\n")
    lines.append("This document lists all enumerations defined in `module.models`.\n\n")
    lines.append("| Enum | Description | Members |\n| --- | --- | --- |\n")
    for enum in enums:
        # Get enum docstring if available
        description = inspect.cleandoc(enum.__doc__) if enum.__doc__ else ""
        # If no docstring, try to infer from name
        if not description:
            # Remove common suffixes and format
            name = enum.__name__.replace("Type", "").replace("System", "").replace("Style", "")
            description = f"{name} enumeration"
        
        members = ", ".join(m.name for m in enum) or "(none)"
        # Escape pipe characters in description for markdown table
        description_escaped = description.replace("|", "\\|")
        lines.append(f"| `{enum.__name__}` | {description_escaped} | {members} |\n")
    return "".join(lines)


def write_enum_overview(path: Path | str = "docs/enums.md") -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    content = generate_enum_overview_markdown()
    out.write_text(content, encoding="utf-8")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Generate Mermaid classDiagram from models")
    parser.add_argument("--out", default="docs/models.mmd", help="Output file path")
    parser.add_argument("--enums-out", default=None, help="Optional: write enum overview markdown to this path")
    args = parser.parse_args(argv)
    p = write_mermaid(args.out)
    print(f"Wrote Mermaid diagram to {p}")
    if args.enums_out:
        pe = write_enum_overview(args.enums_out)
        print(f"Wrote Enum overview to {pe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
