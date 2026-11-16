"""Locate the shared Rust/Python contract fixtures.

The fixtures live in `tauri-application/contracts/`. Resolution order:

1. `KEFER_CONTRACTS_DIR` (set by CI after checking out tauri-application);
2. a sibling checkout: `<parent>/tauri-application/contracts`.

A missing directory is a hard failure, never a skip: parity tests that do
not run must not look green (they errored silently-by-design in CI before).
"""

import os
from pathlib import Path


def contracts_dir() -> Path:
    candidates = []
    env = os.environ.get("KEFER_CONTRACTS_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(Path(__file__).resolve().parents[2] / "tauri-application" / "contracts")
    for candidate in candidates:
        if (candidate / "event-time.json").is_file():
            return candidate
    raise FileNotFoundError(
        "Shared contract fixtures not found. Set KEFER_CONTRACTS_DIR to "
        "tauri-application/contracts or check tauri-application out next to "
        f"function-wrapper. Tried: {', '.join(str(c) for c in candidates)}"
    )
