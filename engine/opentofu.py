"""
OpenTofu / Terraform state file parser.

Reads a terraform.tfstate (JSON) file and normalises resource instances
into DeclaredResource dicts that match declared_resource.schema.json.

The engine is an observer.  It reads the state file as a fact source —
it does NOT execute Terraform/OpenTofu, manage state, or modify anything.

Public API
----------
    parse_state_file(path)         -> StateParseResult
    ingest_state(assessment, path) -> dict   (merged assessment)

    StateParseResult.resources     list[dict]   normalised DeclaredResource dicts
    StateParseResult.meta          dict         version, serial, workspace
    StateParseResult.errors        list[str]    non-fatal parse warnings
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class StateParseResult:
    resources: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def parse_state_file(path: str | Path) -> StateParseResult:
    """
    Parse an OpenTofu / Terraform state file and return normalised resources.

    Supports state format version 4 (current as of Terraform 0.14+).
    Older formats are attempted on a best-effort basis.
    """
    result = StateParseResult()
    state_path = Path(path)

    try:
        raw = json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        result.errors.append(f"Failed to read state file: {exc}")
        return result

    # Top-level metadata
    result.meta = {
        "terraform_version": raw.get("terraform_version"),
        "serial": raw.get("serial"),
        "lineage": raw.get("lineage"),
        "format_version": raw.get("version"),
        "workspace": _extract_workspace(raw),
    }

    fmt = raw.get("version")
    if fmt not in (3, 4, None):
        result.errors.append(
            f"Unexpected state format version {fmt}; attempting best-effort parse"
        )

    # Format 4: resources are a flat list at top level
    raw_resources = raw.get("resources") or []

    for raw_res in raw_resources:
        rtype = raw_res.get("type", "")
        rname = raw_res.get("name", "")
        provider = raw_res.get("provider", "")
        module = raw_res.get("module")  # e.g. "module.vms" or absent

        instances = raw_res.get("instances") or []
        if not instances:
            # Resource with no instances (e.g. count = 0)
            result.resources.append(_make_resource(
                rtype, rname, provider, module, None, {}, False
            ))
            continue

        for inst in instances:
            index_key = inst.get("index_key")  # count index or for_each key
            attrs = inst.get("attributes") or {}
            taint = inst.get("status") == "tainted" or inst.get("deposed") is not None

            result.resources.append(_make_resource(
                rtype, rname, provider, module, index_key, attrs, taint
            ))

    return result


def ingest_state(assessment: dict, path: str | Path) -> dict:
    """
    Parse a state file and merge declared_resources + state_sources.declared
    into a copy of the assessment dict.

    Raises RuntimeError if the state file cannot be read or parsed.
    """
    result = parse_state_file(path)
    if result.errors and not result.resources:
        raise RuntimeError("\n".join(result.errors))

    assessment = dict(assessment)  # shallow copy

    assessment["declared_resources"] = result.resources

    # Update state_sources.declared
    state_sources = dict(assessment.get("state_sources") or {})
    state_sources["declared"] = {
        "tool": _detect_tool(result.meta),
        "state_path": str(path),
        "terraform_version": result.meta.get("terraform_version"),
        "serial": result.meta.get("serial"),
        "resource_count": len(result.resources),
        "collected": True,
    }
    assessment["state_sources"] = state_sources

    return assessment


# ---------------------------------------------------------------------------
# Internal normalisation
# ---------------------------------------------------------------------------

def _make_resource(
    rtype: str,
    rname: str,
    provider: str,
    module: str | None,
    index_key: Any,
    attrs: dict,
    taint: bool,
) -> dict:
    """Build a DeclaredResource dict from raw state data."""
    resource: dict = {
        "resource_type": rtype,
        "resource_name": rname,
        "provider": _normalise_provider(provider),
        "module": module,
        "instance_index": index_key,
        "taint": taint,
        "status": "tainted" if taint else "declared",
        "attributes": _extract_attributes(rtype, attrs),
    }
    return resource


def _extract_attributes(rtype: str, attrs: dict) -> dict:
    """
    Extract the infrastructure-relevant subset of resource attributes.

    We only capture what the engine can observe and compare — not secrets,
    not internal Terraform metadata (id, timeouts, etc.).
    """
    out: dict = {}

    # Name — varies by resource type
    name = (
        attrs.get("name")
        or attrs.get("hostname")
        or attrs.get("vmid")
        and str(attrs["vmid"])
    )
    if name:
        out["name"] = str(name)

    # Proxmox-specific
    if attrs.get("target_node"):
        out["target_node"] = attrs["target_node"]
    if attrs.get("vmid") is not None:
        try:
            out["vmid"] = int(attrs["vmid"])
        except (ValueError, TypeError):
            pass
    if attrs.get("cores") is not None:
        try:
            out["cores"] = int(attrs["cores"])
        except (ValueError, TypeError):
            pass
    if attrs.get("memory") is not None:
        try:
            out["memory"] = int(attrs["memory"])
        except (ValueError, TypeError):
            pass

    # Disk
    disk_size = _extract_disk_size(rtype, attrs)
    if disk_size:
        out["disk_size"] = disk_size

    # Network interfaces
    nics = _extract_nics(rtype, attrs)
    if nics:
        out["network_interfaces"] = nics

    # Tags
    tags = attrs.get("tags")
    if isinstance(tags, str) and tags:
        out["tags"] = [t.strip() for t in tags.split(";") if t.strip()]
    elif isinstance(tags, list):
        out["tags"] = [str(t) for t in tags if t]

    # Description / notes
    desc = attrs.get("desc") or attrs.get("description") or attrs.get("notes")
    if desc:
        out["description"] = str(desc)

    return out


def _extract_disk_size(rtype: str, attrs: dict) -> str | None:
    """Extract primary disk size from various Proxmox provider attribute shapes."""
    # proxmox_vm_qemu: disk block list or single disk attribute
    disks = attrs.get("disk") or []
    if isinstance(disks, list) and disks:
        first = disks[0]
        if isinstance(first, dict):
            size = first.get("size") or first.get("disk_size")
            if size:
                return str(size)
    elif isinstance(disks, dict):
        size = disks.get("size") or disks.get("disk_size")
        if size:
            return str(size)
    # proxmox_lxc: rootfs block
    rootfs = attrs.get("rootfs")
    if isinstance(rootfs, dict):
        return str(rootfs.get("size", "")) or None
    if isinstance(rootfs, list) and rootfs:
        return str(rootfs[0].get("size", "")) or None
    return None


def _extract_nics(rtype: str, attrs: dict) -> list[dict]:
    """Extract network interface declarations."""
    nics = []
    # proxmox_vm_qemu: network block list
    network = attrs.get("network") or []
    if isinstance(network, list):
        for nic in network:
            if not isinstance(nic, dict):
                continue
            entry: dict = {}
            if nic.get("model"):
                entry["model"] = nic["model"]
            if nic.get("bridge"):
                entry["bridge"] = nic["bridge"]
            if entry:
                nics.append(entry)
    # proxmox_lxc: network block
    lxc_net = attrs.get("network") if not network else []
    if isinstance(lxc_net, list):
        for nic in lxc_net:
            if isinstance(nic, dict) and nic.get("bridge"):
                nics.append({"bridge": nic["bridge"]})
    return nics


def _normalise_provider(provider: str) -> str:
    """Strip provider: prefix used in some state versions."""
    if provider.startswith("provider["):
        # e.g. provider["registry.terraform.io/telmate/proxmox"]
        inner = provider[len("provider["):].rstrip("]").strip('"')
        return inner
    return provider


def _detect_tool(meta: dict) -> str:
    """Best-effort detection of opentofu vs terraform from version string."""
    ver = (meta.get("terraform_version") or "").lower()
    if "opentofu" in ver:
        return "opentofu"
    if ver:
        return "terraform"
    return "opentofu"  # default assumption for new projects


def _extract_workspace(raw: dict) -> str | None:
    """Extract workspace name if present (not standard in format v4)."""
    return raw.get("workspace") or raw.get("env") or None
