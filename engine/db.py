"""
SQLite history layer.

Schema
------
assessments
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  hostname    TEXT NOT NULL
  timestamp   TEXT NOT NULL          -- ISO 8601 UTC from the assessment
  stored_at   TEXT NOT NULL          -- ISO 8601 UTC when row was inserted
  schema_ver  TEXT NOT NULL
  data        TEXT NOT NULL          -- full assessment JSON

changes
  id              INTEGER PRIMARY KEY AUTOINCREMENT
  assessment_id   INTEGER NOT NULL REFERENCES assessments(id)
  prev_id         INTEGER REFERENCES assessments(id)  -- NULL for first snapshot
  path            TEXT NOT NULL      -- dot-separated field path, e.g. "hardware.cpu.model"
  old_value       TEXT               -- JSON-encoded previous value
  new_value       TEXT               -- JSON-encoded new value
  stored_at       TEXT NOT NULL

guest_summaries
  id              INTEGER PRIMARY KEY AUTOINCREMENT
  assessment_id   INTEGER NOT NULL REFERENCES assessments(id)
  guest_count     INTEGER NOT NULL
  os_summary      TEXT               -- JSON: {distro: count, ...}
  service_count   INTEGER
  container_count INTEGER
  inventory_groups TEXT             -- JSON: [group, ...]
  collection_methods TEXT           -- JSON: {method: count, ...}
  configuration_methods TEXT        -- JSON: {method: count, ...}
  stored_at       TEXT NOT NULL

NOTE: guest_summaries never stores passwords, SSH keys, tokens, or secret values.

Usage
-----
    from engine.db import HistoryDB
    db = HistoryDB("/path/to/history.db")
    row_id = db.store(assessment_dict)
    rows   = db.list_assessments(hostname="pve01", limit=10)
    prev   = db.fetch(row_id - 1)
    diff   = db.changes_for(row_id)
    summary = db.guest_summary_for(row_id)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS assessments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname    TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    stored_at   TEXT    NOT NULL,
    schema_ver  TEXT    NOT NULL,
    data        TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assessments_hostname
    ON assessments (hostname, timestamp DESC);

CREATE TABLE IF NOT EXISTS changes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id   INTEGER NOT NULL REFERENCES assessments(id),
    prev_id         INTEGER REFERENCES assessments(id),
    path            TEXT    NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    stored_at       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_changes_assessment
    ON changes (assessment_id);

CREATE TABLE IF NOT EXISTS guest_summaries (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id       INTEGER NOT NULL REFERENCES assessments(id),
    guest_count         INTEGER NOT NULL DEFAULT 0,
    os_summary          TEXT,
    service_count       INTEGER NOT NULL DEFAULT 0,
    container_count     INTEGER NOT NULL DEFAULT 0,
    inventory_groups    TEXT,
    collection_methods  TEXT,
    configuration_methods TEXT,
    stored_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_guest_summaries_assessment
    ON guest_summaries (assessment_id);
"""


class HistoryDB:
    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, assessment: dict) -> int:
        """
        Persist an assessment.  Computes and stores field-level changes
        versus the most recent snapshot for the same hostname.
        Returns the new row id.
        """
        hostname = assessment.get("hostname", "unknown")
        timestamp = assessment.get("timestamp", _now())
        schema_ver = assessment.get("schema_version", "unknown")
        stored_at = _now()
        data_json = json.dumps(assessment, default=str)

        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO assessments (hostname, timestamp, stored_at, schema_ver, data)
                VALUES (?, ?, ?, ?, ?)
                """,
                (hostname, timestamp, stored_at, schema_ver, data_json),
            )
            new_id: int = cur.lastrowid

        # Find the previous snapshot for this host
        prev_row = self._conn.execute(
            """
            SELECT id, data FROM assessments
            WHERE hostname = ? AND id < ?
            ORDER BY id DESC LIMIT 1
            """,
            (hostname, new_id),
        ).fetchone()

        if prev_row:
            prev_id = prev_row["id"]
            prev_data = json.loads(prev_row["data"])
            changes = _compute_changes(prev_data, assessment)
            if changes:
                with self._conn:
                    self._conn.executemany(
                        """
                        INSERT INTO changes
                            (assessment_id, prev_id, path, old_value, new_value, stored_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (new_id, prev_id, path, old_v, new_v, stored_at)
                            for path, old_v, new_v in changes
                        ],
                    )

        # Store guest summary (never stores credential values)
        guests = assessment.get("guests") or []
        if guests is not None:  # store even when empty to track "no guests"
            summary = _compute_guest_summary(guests)
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO guest_summaries
                        (assessment_id, guest_count, os_summary, service_count,
                         container_count, inventory_groups, collection_methods,
                         configuration_methods, stored_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        summary["guest_count"],
                        json.dumps(summary["os_summary"]),
                        summary["service_count"],
                        summary["container_count"],
                        json.dumps(summary["inventory_groups"]),
                        json.dumps(summary["collection_methods"]),
                        json.dumps(summary["configuration_methods"]),
                        stored_at,
                    ),
                )

        return new_id

    def fetch(self, row_id: int) -> dict | None:
        """Return the assessment dict for a given row id, or None."""
        row = self._conn.execute(
            "SELECT data FROM assessments WHERE id = ?", (row_id,)
        ).fetchone()
        return json.loads(row["data"]) if row else None

    def list_assessments(
        self,
        hostname: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        Return summary rows (without full data blob) ordered newest first.
        Each row: {id, hostname, timestamp, stored_at, schema_ver}.
        """
        if hostname:
            rows = self._conn.execute(
                """
                SELECT id, hostname, timestamp, stored_at, schema_ver
                FROM assessments
                WHERE hostname = ?
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (hostname, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, hostname, timestamp, stored_at, schema_ver
                FROM assessments
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    def changes_for(self, row_id: int) -> list[dict]:
        """
        Return the change records computed when assessment row_id was stored.
        Each record: {path, old_value (decoded), new_value (decoded)}.
        """
        rows = self._conn.execute(
            """
            SELECT path, old_value, new_value
            FROM changes WHERE assessment_id = ?
            ORDER BY path
            """,
            (row_id,),
        ).fetchall()
        return [
            {
                "path": r["path"],
                "old_value": json.loads(r["old_value"]) if r["old_value"] is not None else None,
                "new_value": json.loads(r["new_value"]) if r["new_value"] is not None else None,
            }
            for r in rows
        ]

    def guest_summary_for(self, assessment_id: int) -> dict | None:
        """Return the guest summary row for an assessment, or None if not present."""
        row = self._conn.execute(
            "SELECT * FROM guest_summaries WHERE assessment_id = ?",
            (assessment_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "guest_count": row["guest_count"],
            "os_summary": json.loads(row["os_summary"]) if row["os_summary"] else {},
            "service_count": row["service_count"],
            "container_count": row["container_count"],
            "inventory_groups": json.loads(row["inventory_groups"]) if row["inventory_groups"] else [],
            "collection_methods": json.loads(row["collection_methods"]) if row["collection_methods"] else {},
            "configuration_methods": json.loads(row["configuration_methods"]) if row["configuration_methods"] else {},
        }

    def hostnames(self) -> list[str]:
        """Return sorted list of distinct hostnames in the database."""
        rows = self._conn.execute(
            "SELECT DISTINCT hostname FROM assessments ORDER BY hostname"
        ).fetchall()
        return [r["hostname"] for r in rows]

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(_DDL)


# ---------------------------------------------------------------------------
# Guest summary computation
# ---------------------------------------------------------------------------

def _compute_guest_summary(guests: list[dict]) -> dict:
    """
    Produce a compact summary of guest facts for history tracking.
    Never stores credential values.
    """
    from collections import Counter

    os_counter: Counter = Counter()
    collection_counter: Counter = Counter()
    config_counter: Counter = Counter()
    groups: set[str] = set()
    service_count = 0
    container_count = 0

    for g in guests:
        os = g.get("operating_system") or {}
        dist = os.get("distribution")
        ver = os.get("distribution_version", "")
        if dist:
            os_counter[f"{dist} {ver}".strip()] += 1

        method = g.get("collection_method", "unknown")
        collection_counter[method] += 1

        conf = g.get("configuration_method") or "unknown"
        config_counter[conf] += 1

        groups.update(g.get("groups") or [])
        service_count += len(g.get("running_services") or [])
        container_count += len(g.get("docker_containers") or [])
        container_count += len(g.get("podman_containers") or [])

    return {
        "guest_count": len(guests),
        "os_summary": dict(os_counter),
        "service_count": service_count,
        "container_count": container_count,
        "inventory_groups": sorted(groups),
        "collection_methods": dict(collection_counter),
        "configuration_methods": dict(config_counter),
    }


# ---------------------------------------------------------------------------
# Change computation
# ---------------------------------------------------------------------------

def _compute_changes(
    old: dict, new: dict
) -> list[tuple[str, str | None, str | None]]:
    """
    Recursively diff two dicts.  Returns list of (path, old_json, new_json).
    Only leaf-level scalar differences are recorded; entire sub-tree additions
    and removals are recorded at their root.

    Skips:
      - timestamp / stored_at (expected to change every run)
      - schema_version (structural, not factual)
    """
    SKIP_PATHS = {"timestamp", "stored_at", "schema_version"}
    results: list[tuple[str, str | None, str | None]] = []
    _diff_recursive(old, new, [], SKIP_PATHS, results)
    return results


def _diff_recursive(
    old: Any,
    new: Any,
    path: list[str],
    skip: set[str],
    out: list[tuple[str, str | None, str | None]],
) -> None:
    key = ".".join(path)

    if path and path[-1] in skip:
        return

    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = set(old) | set(new)
        for k in sorted(all_keys):
            if k in old and k in new:
                _diff_recursive(old[k], new[k], path + [k], skip, out)
            elif k in old:
                out.append((".".join(path + [k]), json.dumps(old[k], default=str), None))
            else:
                out.append((".".join(path + [k]), None, json.dumps(new[k], default=str)))
    elif isinstance(old, list) and isinstance(new, list):
        # Lists are compared as whole values at their parent path
        old_s = json.dumps(old, sort_keys=True, default=str)
        new_s = json.dumps(new, sort_keys=True, default=str)
        if old_s != new_s:
            out.append((key, old_s, new_s))
    else:
        if old != new:
            out.append((key, json.dumps(old, default=str), json.dumps(new, default=str)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
