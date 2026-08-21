"""Canonical event-time parsing shared by persistence and compute boundaries."""

from datetime import date, datetime, time, timezone
from typing import Any, Optional

import pytz


def parse_event_time(
    value: Any,
    timezone_name: Optional[str] = None,
) -> datetime:
    """Return an aware UTC datetime or raise a stable validation error.

    RFC3339 values with offsets are canonical. Legacy naive ISO timestamps and
    dates remain readable; they use the supplied IANA timezone, or UTC when the
    persistence format has no separate timezone context.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date) and not isinstance(value, datetime):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise _invalid_event_time(raw)
        try:
            parsed = datetime.fromisoformat(
                raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
            )
        except ValueError as exc:
            raise _invalid_event_time(raw) from exc
    else:
        raise _invalid_event_time(str(value))

    if parsed.tzinfo is None:
        zone = validate_timezone_name(timezone_name or "UTC")
        try:
            parsed = zone.localize(parsed, is_dst=None)
        except (pytz.AmbiguousTimeError, pytz.NonExistentTimeError) as exc:
            raise ValueError(
                f"invalid_event_time: local time '{parsed.isoformat()}' is "
                f"ambiguous or nonexistent in timezone '{zone.zone}'"
            ) from exc
    return parsed.astimezone(timezone.utc)


def validate_timezone_name(value: str):
    """Resolve an IANA timezone name or raise a stable validation error."""
    name = str(value or "").strip()
    if not name:
        raise ValueError("invalid_timezone: timezone must not be empty")
    try:
        return pytz.timezone(name)
    except pytz.UnknownTimeZoneError as exc:
        raise ValueError(f"invalid_timezone: unknown IANA timezone '{name}'") from exc


def _invalid_event_time(value: str) -> ValueError:
    return ValueError(
        f"invalid_event_time: '{value}' must be RFC3339 with an offset; "
        "legacy YYYY-MM-DD[ HH:MM[:SS]] values require an explicit timezone "
        "context or are interpreted as UTC"
    )
