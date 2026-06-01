#!/usr/bin/env python3
"""
service_state_collector.py — Service State document builder for doc-gen.

Builds a service-state document (conforming to data-model/service-state-schema.json)
from bootstrap-state.json content and a list of observed VMs.

The service-state document captures:
  services          — one entry per known service; status derived from observed VMs
  dns_registrations — DNS registry entries with drift detection
  backup_assignments — declared backup jobs per VM from service contracts

This is the "Service State Collector" for Milestone 7.2. It is stdlib-only and
does not make network calls — all inputs come from bootstrap-state.json and
the observed VM list produced by the Tier 2 SSH collection.
"""

from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Service state document builder
# ---------------------------------------------------------------------------

def collect_service_state(
    bootstrap_state: dict,
    observed_vms: list,
    cell_id: Optional[str] = None,
    collected_at: Optional[str] = None,
) -> dict:
    """
    Build a service-state document from bootstrap-state content and observed VMs.

    bootstrap_state: dict from bootstrap-state.json (has service_contracts,
                     dns_registry, vms, cell_id, etc.)
    observed_vms:    list of {vmid, name, status} dicts from Tier 2 SSH collection
                     (parse_qm_list or collect_provenance_records output).
    cell_id:         override cell_id; defaults to bootstrap_state["cell_id"]
    collected_at:    ISO 8601 timestamp; defaults to now (UTC)

    Returns a dict conforming to service-state-schema.json.
    """
    if not cell_id:
        cell_id = bootstrap_state.get("cell_id", "unknown")
    if not collected_at:
        collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    contracts     = bootstrap_state.get("service_contracts") or []
    dns_registry  = bootstrap_state.get("dns_registry") or []
    declared_vms  = bootstrap_state.get("vms") or []

    # Index observed VMs for fast lookup
    obs_by_name:  dict[str, dict] = {}
    obs_by_vmid:  dict[int, dict] = {}
    for vm in observed_vms:
        name  = vm.get("name", "")
        vmid  = vm.get("vmid")
        if name:
            obs_by_name[name] = vm
        if vmid is not None:
            try:
                obs_by_vmid[int(vmid)] = vm
            except (TypeError, ValueError):
                pass

    return {
        "schema_version": "1.0",
        "cell_id":        cell_id,
        "collected_at":   collected_at,
        "collection_errors": [],
        "services":           _build_services(contracts, declared_vms, obs_by_name),
        "dns_registrations":  _build_dns_registrations(dns_registry),
        "backup_assignments": _build_backup_assignments(declared_vms, contracts, obs_by_vmid),
    }


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_services(
    contracts: list,
    declared_vms: list,
    obs_by_name: dict,
) -> list:
    """
    Build the services list.

    One entry per declared service contract. For VMs in declared_vms that have
    no contract, an entry with contract_declared=False is added so the service
    state document is complete regardless of contract coverage.
    """
    entries: list[dict] = []
    covered_vms: set[str] = set()

    # Contracts first — richer data
    for contract in contracts:
        svc_name = contract.get("service", "")
        vm_name  = contract.get("vm", "")
        vmid     = contract.get("vmid")
        if not vm_name:
            continue

        covered_vms.add(vm_name)
        obs = obs_by_name.get(vm_name, {})
        raw_status = obs.get("status", "unknown")
        status = _normalise_status(raw_status)

        # Primary provided interface (first entry with a port)
        primary_iface = _primary_interface(contract.get("provided_interfaces") or [])
        port         = primary_iface.get("port")
        protocol     = primary_iface.get("protocol")
        health_check = primary_iface.get("health_check") or primary_iface.get("health_check_url")

        # Build health_check_url from url_pattern + health_check if both present
        health_check_url = None
        url_pattern = primary_iface.get("url_pattern")
        if health_check and url_pattern:
            # health_check is like "GET /api/healthz" — extract path
            path = health_check.split(" ", 1)[-1] if " " in health_check else health_check
            health_check_url = url_pattern.rstrip("/") + "/" + path.lstrip("/")
        elif health_check and "://" in str(health_check):
            health_check_url = health_check

        entries.append({
            "name":              svc_name,
            "vm":                vm_name,
            "vmid":              vmid,
            "port":              port,
            "protocol":          protocol,
            "url":               url_pattern,
            "status":            status,
            "health_check_url":  health_check_url,
            "last_health_check": None,
            "contract_declared": True,
            "secret_references": list(contract.get("secret_references") or []),
            "owner":             contract.get("owner"),
            "notes":             contract.get("notes"),
        })

    # VMs declared in bootstrap-state but without a contract
    for vm in declared_vms:
        vm_name = vm.get("name", "")
        if not vm_name or vm_name in covered_vms:
            continue
        obs = obs_by_name.get(vm_name, {})
        status = _normalise_status(obs.get("status", "unknown"))
        entries.append({
            "name":              vm_name,
            "vm":                vm_name,
            "vmid":              vm.get("vmid"),
            "port":              None,
            "protocol":          None,
            "url":               None,
            "status":            status,
            "health_check_url":  None,
            "last_health_check": None,
            "contract_declared": False,
            "secret_references": [],
            "owner":             None,
            "notes":             "No service contract declared",
        })

    return entries


def _build_dns_registrations(dns_registry: list) -> list:
    """
    Build the dns_registrations list from the DNS registry entries.

    Each entry is in_dns_registry=True by definition (it came from the registry).
    drift_from_registry is False — Tier 2 SSH collection does not currently
    compare observed DNS against declared registry; this flag is for future use.
    """
    entries = []
    for entry in dns_registry:
        hostname = entry.get("hostname", "")
        ip       = entry.get("ip", "")
        if not hostname or not ip:
            continue
        entries.append({
            "hostname":           hostname,
            "ip":                 ip,
            "ttl":                entry.get("ttl"),
            "record_type":        entry.get("record_type", "A"),
            "in_dns_registry":    True,
            "drift_from_registry": False,
        })
    return entries


def _build_backup_assignments(
    declared_vms: list,
    contracts: list,
    obs_by_vmid: dict,
) -> list:
    """
    Build the backup_assignments list.

    One entry per declared VM. backup_job_id and in_contract are derived from
    the service contract for this VM (if any). Live backup status fields
    (last_run_at, last_run_status) are null — they require PBS API access
    which is not available in stdlib-only Tier 2 collection.
    """
    # Build contract lookup by VM name
    contract_by_vm: dict[str, dict] = {
        c.get("vm"): c for c in contracts if c.get("vm")
    }

    entries = []
    for vm in declared_vms:
        vmid    = vm.get("vmid")
        vm_name = vm.get("name", "")
        if not vm_name:
            continue

        contract    = contract_by_vm.get(vm_name)
        backup_job  = contract.get("backup_job") if contract else None
        in_contract = backup_job is not None

        entries.append({
            "vmid":                    vmid,
            "vm_name":                 vm_name,
            "backup_job_id":           backup_job,
            "schedule":                None,
            "datastore":               None,
            "pbs_host":                None,
            "last_run_at":             None,
            "last_run_status":         "never",
            "last_successful_backup_at": None,
            "backup_age_hours":        None,
            "in_contract":             in_contract,
        })

    return entries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_status(raw: str) -> str:
    """Map Proxmox VM status strings to service-state-schema status values."""
    mapping = {
        "running": "running",
        "stopped": "stopped",
        "paused":  "stopped",
        "unknown": "unknown",
    }
    return mapping.get(str(raw).lower(), "unknown")


def _primary_interface(interfaces: list) -> dict:
    """Return the first non-SSH interface, or the first interface, or {}."""
    non_ssh = [i for i in interfaces if i.get("protocol", "").lower() != "ssh"]
    if non_ssh:
        return non_ssh[0]
    return interfaces[0] if interfaces else {}
