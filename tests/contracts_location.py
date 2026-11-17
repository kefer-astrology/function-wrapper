"""Locate and verify the shared kefer-contracts fixtures.

Resolution order:

1. `KEFER_CONTRACTS_DIR` (CI checks out kefer-astrology/kefer-contracts at the
   tag pinned in `kefer-contracts.lock` and points this at its `contracts/`);
2. a sibling checkout `<parent>/kefer-contracts/contracts`;
3. the verified copy vendored in `<parent>/tauri-application/contracts`.

The chosen directory must match `kefer-contracts.lock` (version and manifest
hash) and every file must match the manifest. A missing or drifted directory
is a hard failure, never a skip.
"""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = json.loads((REPO / "kefer-contracts.lock").read_text(encoding="utf-8"))


def _candidates():
    env = os.environ.get("KEFER_CONTRACTS_DIR")
    if env:
        yield Path(env)
    yield REPO.parent / "kefer-contracts" / "contracts"
    yield REPO.parent / "tauri-application" / "contracts"


def _verify(directory: Path) -> None:
    manifest_bytes = (directory / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest["version"] != LOCK["version"]:
        raise AssertionError(
            f"{directory}: kefer-contracts {manifest['version']} != pinned {LOCK['version']}"
        )
    if hashlib.sha256(manifest_bytes).hexdigest() != LOCK["manifest_sha256"]:
        raise AssertionError(f"{directory}: manifest.json does not match kefer-contracts.lock")
    for rel, digest in manifest["files"].items():
        if hashlib.sha256((directory / rel).read_bytes()).hexdigest() != digest:
            raise AssertionError(f"{directory}: {rel} does not match the manifest")


@lru_cache(maxsize=1)
def contracts_dir() -> Path:
    tried = []
    for candidate in _candidates():
        tried.append(str(candidate))
        if (candidate / "manifest.json").is_file():
            _verify(candidate)
            return candidate
    raise FileNotFoundError(
        "kefer-contracts not found. Set KEFER_CONTRACTS_DIR to a kefer-contracts "
        f"{LOCK['version']} 'contracts/' directory or check it out next to "
        f"function-wrapper. Tried: {', '.join(tried)}"
    )


def load(relative_path: str):
    return json.loads((contracts_dir() / relative_path).read_text(encoding="utf-8"))
