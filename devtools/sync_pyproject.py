from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
REQ_DIR = ROOT / "requirements"
PYPROJECT = ROOT / "pyproject.toml"

SKIP_DEPS = {"pip-tools", "wheel"}


def _read_in(path: Path) -> List[str]:
    deps: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            continue
        deps.append(line)
    return deps


def _dep_name(req: str) -> str:
    if " @ " in req:
        name = req.split(" @ ", 1)[0].strip()
    else:
        match = re.match(r"^([A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?)", req)
        name = match.group(1) if match else req
    return name


def _dedupe(deps: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for dep in deps:
        name = _dep_name(dep)
        base_name = name.split("[", 1)[0].lower()
        if base_name in SKIP_DEPS:
            continue
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        result.append(dep)
    return result


def _find_section(text: str, header: str) -> Tuple[int, int] | None:
    pattern = rf"(?m)^\[{re.escape(header)}\]\s*$"
    match = re.search(pattern, text)
    if not match:
        return None
    start = match.start()
    next_match = re.search(r"(?m)^\[[^\]]+\]\s*$", text[match.end():])
    end = match.end() + (next_match.start() if next_match else len(text) - match.end())
    return start, end


def _render_list(key: str, deps: List[str]) -> str:
    lines = [f"{key} = ["]
    for dep in deps:
        lines.append(f'    "{dep}",')
    lines.append("]")
    return "\n".join(lines)


def _render_optional_section(optional: Dict[str, List[str]]) -> str:
    lines = ["[project.optional-dependencies]"]
    for extra, deps in optional.items():
        lines.append(_render_list(extra, deps))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _split_req(req: str) -> Tuple[str, str | Dict[str, str]]:
    if " @ " in req:
        name, spec = req.split(" @ ", 1)
        spec = spec.strip()
        if spec.startswith("git+"):
            spec = spec[len("git+"):]
        if "@" in spec:
            url, ref = spec.rsplit("@", 1)
            return name.strip(), {"git": url, "branch": ref}
        return name.strip(), {"git": spec}
    match = re.match(r"^([A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?)(.*)$", req)
    if not match:
        return req, "*"
    name = match.group(1).strip()
    version = match.group(2).strip()
    return name, (version if version else "*")


def _render_poetry_deps(deps: List[str], python_spec: str) -> str:
    lines = ["[tool.poetry.dependencies]", f"python = {python_spec}"]
    for dep in deps:
        name, spec = _split_req(dep)
        if isinstance(spec, dict):
            kv = ", ".join(f'{k} = "{v}"' for k, v in spec.items())
            lines.append(f"{name} = {{{kv}}}")
        else:
            lines.append(f'{name} = "{spec}"')
    return "\n".join(lines) + "\n"


def _render_poetry_group(group: str, deps: List[str]) -> str:
    lines = [f"[tool.poetry.group.{group}.dependencies]"]
    for dep in deps:
        name, spec = _split_req(dep)
        if isinstance(spec, dict):
            kv = ", ".join(f'{k} = "{v}"' for k, v in spec.items())
            lines.append(f"{name} = {{{kv}}}")
        else:
            lines.append(f'{name} = "{spec}"')
    return "\n".join(lines) + "\n"


def _replace_section(text: str, header: str, new_section: str) -> str:
    found = _find_section(text, header)
    if not found:
        return text.rstrip() + "\n\n" + new_section
    start, end = found
    return text[:start] + new_section + text[end:]


def _replace_project_dependencies(text: str, deps: List[str]) -> str:
    found = _find_section(text, "project")
    if not found:
        raise RuntimeError("Missing [project] section in pyproject.toml")
    start, end = found
    section = text[start:end]
    dep_block = _render_list("dependencies", deps)
    pattern = r"(?ms)^\s*dependencies\s*=\s*\[.*?\]\s*"
    if re.search(pattern, section):
        section = re.sub(pattern, dep_block + "\n", section, count=1)
    else:
        section = section.rstrip() + "\n" + dep_block + "\n"
    return text[:start] + section + text[end:]


def sync_pyproject() -> None:
    base = _dedupe(_read_in(REQ_DIR / "base.in"))
    streamlit = _dedupe(_read_in(REQ_DIR / "streamlit.in"))
    kivy = _dedupe(_read_in(REQ_DIR / "kivy.in"))

    # Optional extras should not include base includes.
    streamlit = [d for d in streamlit if _dep_name(d).lower() not in {_dep_name(b).lower() for b in base}]
    kivy = [d for d in kivy if _dep_name(d).lower() not in {_dep_name(b).lower() for b in base}]

    optional = {
        "streamlit": streamlit,
        "kivy": kivy,
        "docs": streamlit + kivy,
    }

    text = PYPROJECT.read_text(encoding="utf-8")
    text = _replace_project_dependencies(text, base)
    text = _replace_section(text, "project.optional-dependencies", _render_optional_section(optional))

    poetry_section = _find_section(text, "tool.poetry.dependencies")
    python_spec = '">=3.10,<4"'
    if poetry_section:
        start, end = poetry_section
        current = text[start:end]
        match = re.search(r"(?m)^\s*python\s*=\s*(.+)$", current)
        if match:
            python_spec = match.group(1).strip()

    text = _replace_section(text, "tool.poetry.dependencies", _render_poetry_deps(base, python_spec))
    text = _replace_section(text, "tool.poetry.group.streamlit.dependencies", _render_poetry_group("streamlit", streamlit))
    text = _replace_section(text, "tool.poetry.group.kivy.dependencies", _render_poetry_group("kivy", kivy))

    PYPROJECT.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    sync_pyproject()
    print("Synced pyproject.toml from requirements/*.in")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
