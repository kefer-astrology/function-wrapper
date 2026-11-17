"""Build the standalone `kefer-backend` sidecar with PyInstaller.

Verified build (Phase 2): the resulting single file starts the FastAPI sidecar,
needs no network, and bundles the ephemeris data it reads at runtime.

    python -m venv .venv-build
    .venv-build/bin/python -m pip install -r requirements/api.txt -e . pyinstaller
    .venv-build/bin/python -m devtools.build_sidecar          # -> dist/kefer-backend

PyInstaller is GPL-2.0 with a bootloader exception that permits bundling
programs under any license; it is a build tool only and is not shipped.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Runtime data located relative to the package by module.utils
# (default_ephemeris_path / default_mpc_elements_path).
DATA_FILES = ("source/de440s.bsp", "source/mpc_bodies.dat")
ENTRY = "from module.api.__main__ import main\nraise SystemExit(main())\n"


def main() -> int:
    missing = [rel for rel in DATA_FILES if not (ROOT / rel).is_file()]
    if missing:
        print(f"missing runtime data: {missing}")
        return 1
    with tempfile.TemporaryDirectory(prefix="kefer-sidecar-") as tmp:
        entry = Path(tmp) / "kefer_backend.py"
        entry.write_text(ENTRY, encoding="utf-8")
        args = [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
            "--name", "kefer-backend",
            # uvicorn imports the app from a string, invisible to PyInstaller's analysis.
            "--hidden-import", "module.api.app",
            "--hidden-import", "module.api.schemas",
            "--paths", str(ROOT),
            "--distpath", str(ROOT / "dist"),
            "--workpath", str(Path(tmp) / "build"),
            "--specpath", tmp,
        ]
        for rel in DATA_FILES:
            args += ["--add-data", f"{ROOT / rel}{os.pathsep}{Path(rel).parent.as_posix()}"]
        args.append(str(entry))
        return subprocess.call(args, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
