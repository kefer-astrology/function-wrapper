"""Canonical event-time parsing shared by persistence and compute boundaries."""

from datetime import date, datetime, time, timedelta, timezone
import re
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
        parsed = _parse_event_time_string(raw)
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


# Grammar mirrors `src-tauri/src/event_time.rs` (chrono `parse_from_rfc3339`
# plus three legacy naive formats and a bare date). `datetime.fromisoformat`
# is deliberately not used: since Python 3.11 it also accepts forms the
# shared contract rejects (`2024-01-01T12:30`, `20240101`, `2024-W01-1`,
# `+0100` offsets, ...), which let the two implementations diverge.
_RFC3339 = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?"
    r"(?:([Zz])|([+-])(\d{2}):(\d{2}))$"
)
_LEGACY_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def _parse_event_time_string(raw: str) -> datetime:
    match = _RFC3339.match(raw)
    if match:
        year, month, day, hour, minute, second, fraction, zulu, sign, off_h, off_m = match.groups()
        try:
            if zulu:
                tz = timezone.utc
            else:
                offset = timedelta(hours=int(off_h), minutes=int(off_m))
                tz = timezone(-offset if sign == "-" else offset)
            micro = int((fraction or "0")[:6].ljust(6, "0"))
            return datetime(
                int(year), int(month), int(day),
                int(hour), int(minute), int(second), micro, tzinfo=tz,
            )
        except ValueError as exc:
            raise _invalid_event_time(raw) from exc
    for fmt in _LEGACY_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise _invalid_event_time(raw)


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
