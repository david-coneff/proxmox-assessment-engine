"""
Parse a raw collector audit dict into a normalized assessment dict.

Each top-level key in the raw audit corresponds to a collector name.
Parsers are registered per-collector and return fragments of the
normalized assessment schema.
"""

from __future__ import annotations

import datetime
import socket
from typing import Any, Callable

_PARSERS: dict[str, Callable[[dict], dict]] = {}


def register_parser(collector_name: str) -> Callable:
    """Decorator: register a parser function for a collector."""
    def decorator(fn: Callable[[dict], dict]) -> Callable:
        _PARSERS[collector_name] = fn
        return fn
    return decorator


def parse_raw_audit(raw: dict) -> dict:
    """Convert a raw collector audit dict into a normalized assessment."""
    # Ensure all parser modules are loaded (registers @register_parser decorators).
    import engine.modules  # noqa: F401

    assessment: dict[str, Any] = {
        "schema_version": "1.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hostname": socket.getfqdn(),
    }

    for collector_name, data in raw.items():
        if isinstance(data, dict) and "error" in data:
            continue  # skip failed collectors
        parser = _PARSERS.get(collector_name)
        if parser is None:
            continue
        fragment = parser(data)
        _deep_merge(assessment, fragment)

    return assessment


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place (shallow for non-dict values)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
