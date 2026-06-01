#!/usr/bin/env python3
"""
external_dependencies.py — External dependency registry for doc-gen.

Provides:
  ExternalDependencyRegistry  — lookups and certificate expiry queries
  build_external_dependency_registry(manifest) — factory from manifest dict

Data is sourced from manifest["external_dependencies"] injected by engine.py
from bootstrap-state.json (external_dependencies array).
"""

from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Certificate expiry thresholds (days)
# ---------------------------------------------------------------------------
CERT_EXPIRY_RED_DAYS    = 7    # imminent — services will start failing soon
CERT_EXPIRY_ORANGE_DAYS = 30   # critical action required
CERT_EXPIRY_YELLOW_DAYS = 60   # plan renewal now


# ---------------------------------------------------------------------------
# ExternalDependencyRegistry
# ---------------------------------------------------------------------------

class ExternalDependencyRegistry:
    """
    Wrapper around the external_dependencies list for fast lookups
    and certificate expiry analysis.
    """

    def __init__(self, dependencies: list):
        self._deps = list(dependencies or [])
        self._by_id: dict[str, dict] = {}

        for d in self._deps:
            dep_id = d.get("id")
            if dep_id:
                self._by_id[dep_id] = d

    def available(self) -> bool:
        return bool(self._deps)

    def count(self) -> int:
        return len(self._deps)

    def all(self) -> list:
        return list(self._deps)

    def get(self, dep_id: str) -> Optional[dict]:
        return self._by_id.get(dep_id)

    def with_certificates(self) -> list:
        """Return dependencies that have certificate state declared."""
        return [d for d in self._deps if d.get("certificate")]

    def expiring_within_days(self, days: int, now: Optional[datetime] = None) -> list:
        """
        Return dependencies whose TLS certificate expires within `days` days.
        Entries without a certificate or with unparseable expiry are excluded.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        result = []
        for dep in self._deps:
            cert = dep.get("certificate")
            if not cert:
                continue
            expires_at = cert.get("expires_at")
            if not expires_at:
                continue
            try:
                exp_dt = datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )
                days_remaining = (exp_dt - now).days
                if days_remaining <= days:
                    result.append({**dep, "_days_remaining": days_remaining})
            except (ValueError, TypeError):
                pass
        return result

    def days_until_expiry(self, dep: dict, now: Optional[datetime] = None) -> Optional[int]:
        """
        Return the number of days until this dependency's certificate expires,
        or None if no certificate or unparseable date.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        cert = dep.get("certificate")
        if not cert:
            return None
        expires_at = cert.get("expires_at")
        if not expires_at:
            return None
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return (exp_dt - now).days
        except (ValueError, TypeError):
            return None


def build_external_dependency_registry(manifest: dict) -> ExternalDependencyRegistry:
    """Build an ExternalDependencyRegistry from a manifest dict."""
    deps = manifest.get("external_dependencies") or []
    return ExternalDependencyRegistry(deps)
