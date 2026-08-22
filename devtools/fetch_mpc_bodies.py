"""Regenerate source/mpc_bodies.dat from the live MPCORB.DAT catalog.

Not run automatically by any Makefile target or test — this is an offline,
occasional maintenance script. MPCORB.DAT is ~300MB uncompressed; this script
downloads it to a temp file, extracts the rows for the bodies function-wrapper
computes natively (Chiron + Ceres/Pallas/Juno/Vesta), and discards the rest.

Usage: python -m devtools.fetch_mpc_bodies
"""
from __future__ import annotations

import gzip
import re
import urllib.request
from pathlib import Path

MPCORB_URL = "https://www.minorplanetcenter.net/iau/MPCORB/MPCORB.DAT.gz"

# packed designation prefix -> human label, purely for the progress log below
_PACKED_DESIGNATIONS = {
    "00001": "Ceres",
    "00002": "Pallas",
    "00003": "Juno",
    "00004": "Vesta",
    "02060": "Chiron",
}

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "source" / "mpc_bodies.dat"


def main() -> int:
    print(f"Downloading {MPCORB_URL} ...")
    with urllib.request.urlopen(MPCORB_URL, timeout=120) as resp:
        raw = gzip.decompress(resp.read())

    text = raw.decode("ascii", errors="replace")
    pattern = re.compile(r"^(" + "|".join(_PACKED_DESIGNATIONS) + r")\s.*$", re.MULTILINE)
    matched_lines = [m.group(0) for m in pattern.finditer(text)]

    found = {line[:5] for line in matched_lines}
    missing = set(_PACKED_DESIGNATIONS) - found
    if missing:
        labels = ", ".join(_PACKED_DESIGNATIONS[m] for m in sorted(missing))
        raise RuntimeError(f"MPCORB.DAT did not contain expected rows for: {labels}")

    OUTPUT_PATH.write_text("\n".join(matched_lines) + "\n", encoding="ascii")
    print(f"Wrote {len(matched_lines)} rows to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
