"""
Assessment diff helpers – public API for comparing two assessment dicts.

These functions are used both by engine/db.py (which stores changes) and
by the CLI 'diff' subcommand (which renders them for humans).

diff_assessments(old, new) -> list[Change]

Change is a dataclass:
    path      – dot-separated field path, e.g. "hardware.cpu.model"
    old_value – previous value (any JSON type), None if field was added
    new_value – new value (any JSON type), None if field was removed
    kind      – "changed" | "added" | "removed"
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

_SKIP_PATHS = {"timestamp", "stored_at", "schema_version", "collector_version"}


@dataclass
class Change:
    path: str
    old_value: Any
    new_value: Any
    kind: str  # "changed" | "added" | "removed"

    def summary(self) -> str:
        if self.kind == "added":
            return f"+ {self.path} = {_fmt(self.new_value)}"
        if self.kind == "removed":
            return f"- {self.path} (was {_fmt(self.old_value)})"
        return f"~ {self.path}: {_fmt(self.old_value)} → {_fmt(self.new_value)}"


def diff_assessments(old: dict, new: dict) -> list[Change]:
    """
    Return a list of Change objects describing every field-level difference
    between old and new assessments.

    Lists are compared as atomic values; only list-level changes are reported
    (not element-level) to keep output concise.
    """
    changes: list[Change] = []
    _recurse(old, new, [], changes)
    return changes


def format_diff(changes: list[Change], verbose: bool = False) -> str:
    """Render a human-readable diff string."""
    if not changes:
        return "No changes detected."

    lines = [f"{'PATH':<50}  {'OLD':<30}  NEW"]
    lines.append("-" * 100)
    for c in sorted(changes, key=lambda x: x.path):
        if c.kind == "added":
            lines.append(f"{'+ ' + c.path:<50}  {'(new)':<30}  {_fmt(c.new_value)}")
        elif c.kind == "removed":
            lines.append(f"{'- ' + c.path:<50}  {_fmt(c.old_value):<30}  (removed)")
        else:
            lines.append(f"{'~ ' + c.path:<50}  {_fmt(c.old_value):<30}  {_fmt(c.new_value)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _recurse(
    old: Any,
    new: Any,
    path: list[str],
    out: list[Change],
) -> None:
    if path and path[-1] in _SKIP_PATHS:
        return

    dot_path = ".".join(path)

    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            if k in old and k in new:
                _recurse(old[k], new[k], path + [k], out)
            elif k in old:
                out.append(Change(
                    path=".".join(path + [k]),
                    old_value=old[k],
                    new_value=None,
                    kind="removed",
                ))
            else:
                out.append(Change(
                    path=".".join(path + [k]),
                    old_value=None,
                    new_value=new[k],
                    kind="added",
                ))

    elif isinstance(old, list) and isinstance(new, list):
        # Normalise for stable comparison
        old_s = json.dumps(old, sort_keys=True, default=str)
        new_s = json.dumps(new, sort_keys=True, default=str)
        if old_s != new_s:
            out.append(Change(path=dot_path, old_value=old, new_value=new, kind="changed"))

    else:
        if old != new:
            out.append(Change(path=dot_path, old_value=old, new_value=new, kind="changed"))


def _fmt(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, (dict, list)):
        s = json.dumps(v, default=str)
        return s[:60] + "…" if len(s) > 60 else s
    return str(v)
