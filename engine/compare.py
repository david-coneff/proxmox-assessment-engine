"""
Declared vs Configured vs Observed comparison engine.

Compares three layers of infrastructure state:
  - Declared   – what OpenTofu / Terraform says should exist
  - Configured – what Ansible inventory says is managed
  - Observed   – what the assessment engine actually found

All output is factual.  No recommendations are generated.

Public API
----------
    compare(assessment) -> ComparisonResult

    ComparisonResult.declared_resources    list[dict]
    ComparisonResult.configured_hosts      list[str]
    ComparisonResult.observed_guests       list[dict]
    ComparisonResult.matches               list[Match]
    ComparisonResult.declared_only         list[dict]   in declared, not observed
    ComparisonResult.observed_only         list[dict]   in observed, not declared
    ComparisonResult.configured_only       list[str]    in configured, not observed
    ComparisonResult.summary()             dict
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Match:
    """A resource present in two or more layers."""
    name: str
    declared: dict | None = None       # DeclaredResource dict
    configured: str | None = None      # inventory hostname
    observed: dict | None = None       # guest dict
    layers: list[str] = field(default_factory=list)  # which layers matched

    def layer_string(self) -> str:
        return " + ".join(sorted(self.layers))


@dataclass
class ComparisonResult:
    declared_resources: list[dict] = field(default_factory=list)
    configured_hosts: list[str] = field(default_factory=list)
    observed_guests: list[dict] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)
    declared_only: list[dict] = field(default_factory=list)
    observed_only: list[dict] = field(default_factory=list)
    configured_only: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "declared_count": len(self.declared_resources),
            "configured_count": len(self.configured_hosts),
            "observed_count": len(self.observed_guests),
            "matched_count": len(self.matches),
            "declared_only_count": len(self.declared_only),
            "observed_only_count": len(self.observed_only),
            "configured_only_count": len(self.configured_only),
        }


# ---------------------------------------------------------------------------
# Main comparison function
# ---------------------------------------------------------------------------

def compare(assessment: dict) -> ComparisonResult:
    """
    Compare the three state layers in an assessment dict.

    Returns a ComparisonResult.  All content is factual; no judgments made.
    """
    declared = assessment.get("declared_resources") or []
    guests = assessment.get("guests") or []
    state_sources = assessment.get("state_sources") or {}
    configured_meta = state_sources.get("configured") or {}
    # Configured hosts come from the guest list (they were loaded from inventory)
    # plus any explicitly listed inventory hosts. We derive from guests' inventory_name.
    configured_hosts: list[str] = sorted({
        g.get("inventory_name") or g.get("hostname", "")
        for g in guests
        if g.get("inventory_name") or g.get("hostname")
    })

    result = ComparisonResult(
        declared_resources=declared,
        configured_hosts=configured_hosts,
        observed_guests=guests,
    )

    # Build lookup tables by normalised name
    declared_by_name: dict[str, dict] = {}
    for r in declared:
        key = _resource_key(r)
        if key:
            declared_by_name[key] = r

    observed_by_name: dict[str, dict] = {}
    for g in guests:
        key = _guest_key(g)
        if key:
            observed_by_name[key] = g

    configured_set: set[str] = set(configured_hosts)

    # Find matches (present in declared AND observed)
    matched_declared: set[str] = set()
    matched_observed: set[str] = set()

    for dec_key, dec in declared_by_name.items():
        obs = observed_by_name.get(dec_key)
        conf = dec_key if dec_key in configured_set else None

        if obs or conf:
            layers = ["declared"]
            if conf:
                layers.append("configured")
            if obs:
                layers.append("observed")
            result.matches.append(Match(
                name=dec_key,
                declared=dec,
                configured=conf,
                observed=obs,
                layers=layers,
            ))
            matched_declared.add(dec_key)
            if obs:
                matched_observed.add(dec_key)
        else:
            result.declared_only.append(dec)

    # Observed guests with no corresponding declared resource
    for obs_key, obs in observed_by_name.items():
        if obs_key not in matched_observed:
            # Check if at least configured
            if obs_key in configured_set:
                result.matches.append(Match(
                    name=obs_key,
                    declared=None,
                    configured=obs_key,
                    observed=obs,
                    layers=["configured", "observed"],
                ))
            else:
                result.observed_only.append(obs)

    # Configured hosts not in declared or observed
    for host in configured_hosts:
        in_declared = host in declared_by_name
        in_observed = host in observed_by_name
        in_matches = any(m.name == host for m in result.matches)
        if not in_declared and not in_observed and not in_matches:
            result.configured_only.append(host)

    return result


# ---------------------------------------------------------------------------
# Key extraction helpers
# ---------------------------------------------------------------------------

def _resource_key(resource: dict) -> str | None:
    """
    Derive a normalised comparison key from a DeclaredResource.

    Priority: attributes.name > resource_name (with index if present).
    Always lowercased and stripped.
    """
    attrs = resource.get("attributes") or {}
    name = attrs.get("name")
    if name:
        return str(name).strip().lower()
    rname = resource.get("resource_name", "")
    index = resource.get("instance_index")
    if index is not None:
        return f"{rname}[{index}]".lower()
    return rname.strip().lower() if rname else None


def _guest_key(guest: dict) -> str | None:
    """
    Derive a normalised comparison key from an observed guest.

    Priority: inventory_name > hostname, both normalised to short hostname
    (strip domain if FQDN) and lowercased.
    """
    name = guest.get("inventory_name") or guest.get("hostname") or ""
    if not name:
        return None
    # Use short hostname for matching (strip domain)
    short = name.split(".")[0]
    return short.strip().lower()
