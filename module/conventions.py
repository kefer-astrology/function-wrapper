"""Calculation conventions (kefer-contracts ``conventions.json``).

``kefer-positions/1`` (mean equinox of date, GMST, mean obliquity) is the
default and never changes implicitly. ``kefer-positions/1-true-equinox`` adds
IAU 2000A nutation to exactly the same inputs. An unknown or unimplemented id
is computed with the default and always reported with a warning.
Mirrors tauri-application ``src-tauri/src/domain/conventions.rs``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

MEAN_EQUINOX = "kefer-positions/1"
TRUE_EQUINOX = "kefer-positions/1-true-equinox"
IMPLEMENTED = (MEAN_EQUINOX, TRUE_EQUINOX)


@dataclass(frozen=True)
class ResolvedConvention:
    id: str
    equinox: str  # "mean" | "true"
    warning: Optional[str] = None


def resolve(requested: Optional[str]) -> ResolvedConvention:
    value = (requested or "").strip()
    if value in ("", MEAN_EQUINOX):
        return ResolvedConvention(MEAN_EQUINOX, "mean")
    if value == TRUE_EQUINOX:
        return ResolvedConvention(TRUE_EQUINOX, "true")
    return ResolvedConvention(
        MEAN_EQUINOX,
        "mean",
        f"calculation_convention_unsupported: {value}; {MEAN_EQUINOX}_used",
    )


def for_chart(chart) -> ResolvedConvention:
    config = getattr(chart, "config", None)
    return resolve(getattr(config, "calculation_convention", None) if config else None)
