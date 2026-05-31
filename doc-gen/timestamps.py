"""
Timestamp formatting utilities for documentation generation.

Two formats are maintained:
  Machine-readable (JSON storage, drift records, schema fields):
      ISO 8601 UTC  →  "2026-05-31T14:05:41Z"
      Use: now_utc_iso()

  Human-readable (markdown reports, ODT runbooks, ODS workbooks):
      Dual-timezone  →  "2026-05-31 14:05:41 UTC (2026-05-31 08:05:41 MDT)"
      Use: format_doc_timestamp()

The local timezone component is configured via environment variables:

    LOCAL_TZ_OFFSET   Integer UTC offset in hours, e.g. -6 for MDT, -7 for MST
    LOCAL_TZ_NAME     Timezone abbreviation to display, e.g. MDT or MST

Both must be set for the local time to appear. If either is absent, the
output falls back to UTC only: "2026-05-31 14:05:41 UTC"

Typical setup in bootstrap.sh or assessment-engine service unit:
    export LOCAL_TZ_OFFSET=-6
    export LOCAL_TZ_NAME=MDT
"""

import os
from datetime import datetime, timedelta, timezone


def now_utc_iso() -> str:
    """Return the current UTC time as an ISO 8601 string for machine-readable storage."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_doc_timestamp(dt: datetime | None = None) -> str:
    """
    Format a datetime for display in generated documentation.

    Returns "YYYY-MM-DD HH:MM:SS UTC (YYYY-MM-DD HH:MM:SS TZ)" when
    LOCAL_TZ_OFFSET and LOCAL_TZ_NAME env vars are set, otherwise
    returns "YYYY-MM-DD HH:MM:SS UTC".

    Parameters
    ----------
    dt : datetime, optional
        The datetime to format. Defaults to now (UTC).
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    utc_str = dt.strftime("%Y-%m-%d %H:%M:%S") + " UTC"

    offset_str = os.environ.get("LOCAL_TZ_OFFSET", "").strip()
    tz_name = os.environ.get("LOCAL_TZ_NAME", "").strip()

    if offset_str and tz_name:
        try:
            offset_hours = int(offset_str)
            local_dt = dt + timedelta(hours=offset_hours)
            local_str = local_dt.strftime("%Y-%m-%d %H:%M:%S")
            return f"{utc_str} ({local_str} {tz_name})"
        except ValueError:
            pass  # malformed offset — fall back to UTC only

    return utc_str


def format_doc_timestamp_from_iso(iso_str: str) -> str:
    """
    Format an existing ISO 8601 UTC string for display in documentation.

    Parses the ISO string and applies the same dual-timezone formatting
    as format_doc_timestamp(). Useful when displaying a stored timestamp
    that was captured at collection time.

    Parameters
    ----------
    iso_str : str
        ISO 8601 string, e.g. "2026-05-31T14:05:41Z" or "2026-05-31T14:05:41"
    """
    try:
        # Handle both Z suffix and no suffix
        clean = iso_str.rstrip("Z").replace("T", " ")
        dt = datetime.strptime(clean[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return format_doc_timestamp(dt)
    except (ValueError, AttributeError):
        return iso_str  # return as-is if unparseable
