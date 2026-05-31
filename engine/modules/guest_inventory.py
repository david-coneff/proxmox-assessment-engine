"""
Guest inventory collection and normalization via Ansible.

This module is the canonical guest discovery mechanism.  It uses:
  - ansible-inventory  to discover hosts and groups from any supported
                       inventory format (YAML, INI, dynamic)
  - ansible            to collect facts (setup module), service facts,
                       and container inventory per host

Authentication and transport remain entirely Ansible's responsibility.
This module never reads credentials, SSH keys, or API tokens.

Public API
----------
    load_inventory(inventory_path) -> InventoryResult
    collect_guest_facts(host, inventory_path, timeout) -> dict
    normalize_guest(host, groups, raw_facts) -> dict
    collect_all_guests(inventory_path, limit, timeout) -> list[dict]
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class InventoryResult:
    """Parsed output from ansible-inventory --list."""

    hosts: list[str]                        # all non-meta host names
    groups: dict[str, list[str]]            # group_name -> [host_name, ...]
    host_vars: dict[str, dict]              # host_name -> hostvars dict
    meta: dict = field(default_factory=dict)

    def groups_for(self, hostname: str) -> list[str]:
        """Return all group names that contain this hostname."""
        return sorted(
            g for g, members in self.groups.items()
            if hostname in members and g not in ("all", "ungrouped")
        )


# ---------------------------------------------------------------------------
# Inventory loading
# ---------------------------------------------------------------------------

def load_inventory(inventory_path: str) -> InventoryResult:
    """
    Run ansible-inventory --list and parse the result.

    Supports YAML, INI, and dynamic inventories — anything
    ansible-inventory itself supports.

    Raises RuntimeError if ansible-inventory is not available or fails.
    """
    if not shutil.which("ansible-inventory"):
        raise RuntimeError("ansible-inventory not found in PATH")

    raw = _run(["ansible-inventory", "-i", inventory_path, "--list"])
    data = json.loads(raw)
    return _parse_inventory_json(data)


def _parse_inventory_json(data: dict) -> InventoryResult:
    """Parse the JSON output of `ansible-inventory --list`."""
    meta = data.get("_meta", {})
    hostvars = meta.get("hostvars", {})

    groups: dict[str, list[str]] = {}
    all_hosts: set[str] = set(hostvars.keys())

    for group_name, group_data in data.items():
        if group_name == "_meta":
            continue
        if not isinstance(group_data, dict):
            continue
        members = group_data.get("hosts", [])
        groups[group_name] = members
        all_hosts.update(members)

    return InventoryResult(
        hosts=sorted(all_hosts),
        groups=groups,
        host_vars=hostvars,
        meta=meta,
    )


# ---------------------------------------------------------------------------
# Per-host fact collection
# ---------------------------------------------------------------------------

def collect_guest_facts(
    host: str,
    inventory_path: str,
    timeout: int = 30,
) -> dict:
    """
    Collect Ansible facts for a single host.

    Runs:
      ansible <host> -i <inv> -m setup
      ansible <host> -i <inv> -m service_facts
      ansible <host> -i <inv> -m command -a "docker ps --format json --no-trunc" (if available)
      ansible <host> -i <inv> -m command -a "podman ps --format json --no-trunc" (if available)

    Returns a raw dict with keys: setup, service_facts, docker, podman.
    On connection/module failure the key contains {"error": "..."}.

    Never retrieves, stores, or logs credentials.
    """
    result: dict[str, Any] = {}

    result["setup"] = _run_ansible_module(host, inventory_path, "setup", timeout=timeout)
    result["service_facts"] = _run_ansible_module(
        host, inventory_path, "service_facts", timeout=timeout
    )
    result["docker"] = _run_ansible_command(
        host, inventory_path,
        "docker ps --format '{\"name\":\"{{.Names}}\",\"image\":\"{{.Image}}\",\"status\":\"{{.Status}}\"}'",
        timeout=timeout,
    )
    result["podman"] = _run_ansible_command(
        host, inventory_path,
        "podman ps --format '{\"name\":\"{{.Names}}\",\"image\":\"{{.Image}}\",\"status\":\"{{.Status}}\"}'",
        timeout=timeout,
    )

    return result


def _run_ansible_module(
    host: str,
    inventory_path: str,
    module: str,
    timeout: int = 30,
) -> dict:
    """Run an Ansible module and return parsed JSON output."""
    if not shutil.which("ansible"):
        return {"error": "ansible not found in PATH"}
    try:
        raw = _run(
            ["ansible", host, "-i", inventory_path, "-m", module, "--one-line"],
            timeout=timeout,
        )
        return _parse_ansible_output(host, raw)
    except Exception as exc:
        return {"error": str(exc)}


def _run_ansible_command(
    host: str,
    inventory_path: str,
    command: str,
    timeout: int = 30,
) -> dict:
    """Run an Ansible command module and return parsed output."""
    if not shutil.which("ansible"):
        return {"error": "ansible not found in PATH"}
    try:
        raw = _run(
            ["ansible", host, "-i", inventory_path, "-m", "command",
             "-a", command, "--one-line"],
            timeout=timeout,
        )
        return _parse_ansible_output(host, raw)
    except Exception as exc:
        return {"error": str(exc)}


def _parse_ansible_output(host: str, raw: str) -> dict:
    """
    Parse single-line ansible output.

    ansible --one-line emits:
      hostname | SUCCESS => {json}
      hostname | FAILED! => {json}
      hostname | UNREACHABLE! => {json}
    """
    # Find the JSON payload after " => "
    marker = " => "
    idx = raw.find(marker)
    if idx == -1:
        return {"error": f"Unexpected ansible output: {raw[:200]}"}
    payload_str = raw[idx + len(marker):].strip()
    try:
        return json.loads(payload_str)
    except json.JSONDecodeError:
        return {"error": f"JSON parse failed: {payload_str[:200]}"}


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_guest(
    hostname: str,
    inventory_name: str,
    groups: list[str],
    raw_facts: dict,
    host_vars: dict | None = None,
) -> dict:
    """
    Normalize raw Ansible fact output into a guest schema dict.

    Always produces a valid dict.  Fields that could not be collected
    are omitted rather than set to null, except collection_method and
    collection_timestamp which are always present.
    """
    setup = raw_facts.get("setup") or {}
    service_facts = raw_facts.get("service_facts") or {}
    docker_raw = raw_facts.get("docker") or {}
    podman_raw = raw_facts.get("podman") or {}

    ansible_facts = setup.get("ansible_facts") or {}

    collection_method = _determine_collection_method(setup)
    timestamp = datetime.now(timezone.utc).isoformat()

    guest: dict[str, Any] = {
        "hostname": hostname,
        "inventory_name": inventory_name,
        "groups": groups,
        "collection_timestamp": timestamp,
        "collection_method": collection_method,
    }

    if ansible_facts:
        # Operating system
        os_facts = _extract_os(ansible_facts)
        if os_facts:
            guest["operating_system"] = os_facts

        # IP addresses
        ips = _extract_ips(ansible_facts)
        if ips:
            guest["ip_addresses"] = ips

        # CPU and memory
        cpu = ansible_facts.get("ansible_processor_vcpus") or ansible_facts.get("ansible_processor_count")
        if cpu is not None:
            guest["cpu_count"] = int(cpu)

        mem = ansible_facts.get("ansible_memtotal_mb")
        if mem is not None:
            guest["memory_mb"] = int(mem)

        # Filesystems
        mounts = _extract_mounts(ansible_facts)
        if mounts:
            guest["mounted_filesystems"] = mounts

    # Services
    running, enabled = _extract_services(service_facts)
    if running:
        guest["running_services"] = running
    if enabled:
        guest["enabled_services"] = enabled

    # Containers
    docker_containers = _extract_containers(docker_raw)
    if docker_containers:
        guest["docker_containers"] = docker_containers

    podman_containers = _extract_containers(podman_raw)
    if podman_containers:
        guest["podman_containers"] = podman_containers

    # Provisioning metadata from host_vars (never expose values, only names)
    if host_vars:
        prov = host_vars.get("provisioning_method")
        if prov:
            guest["provisioning_method"] = str(prov)
        conf = host_vars.get("configuration_method")
        if conf:
            guest["configuration_method"] = str(conf)
        secret_src = host_vars.get("secret_source")
        if secret_src:
            guest["secret_source"] = str(secret_src)

    return guest


# ---------------------------------------------------------------------------
# Collect all guests
# ---------------------------------------------------------------------------

def collect_all_guests(
    inventory_path: str,
    limit: list[str] | None = None,
    timeout: int = 30,
) -> list[dict]:
    """
    Discover all hosts from the inventory and collect facts for each.

    limit: optional list of hostnames or patterns to restrict collection.
    Returns a list of normalized guest dicts.
    """
    inventory = load_inventory(inventory_path)
    hosts = inventory.hosts

    if limit:
        limit_set = set(limit)
        hosts = [h for h in hosts if h in limit_set]

    guests = []
    for host in hosts:
        groups = inventory.groups_for(host)
        host_vars = inventory.host_vars.get(host, {})
        raw_facts = collect_guest_facts(host, inventory_path, timeout=timeout)
        guest = normalize_guest(
            hostname=host,
            inventory_name=host,
            groups=groups,
            raw_facts=raw_facts,
            host_vars=host_vars,
        )
        guests.append(guest)

    return guests


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 60) -> str:
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (rc={result.returncode}): {' '.join(cmd)}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result.stdout


def _determine_collection_method(setup: dict) -> str:
    if "error" in setup:
        err = setup["error"].lower()
        if "unreachable" in err:
            return "unreachable"
        return "failed"
    if setup.get("ansible_facts"):
        return "ansible-facts"
    return "unknown"


def _extract_os(facts: dict) -> dict:
    os: dict = {}
    dist = facts.get("ansible_distribution")
    if dist:
        os["distribution"] = dist
    ver = facts.get("ansible_distribution_version")
    if ver:
        os["distribution_version"] = str(ver)
    rel = facts.get("ansible_distribution_release")
    if rel:
        os["distribution_release"] = rel
    kernel = facts.get("ansible_kernel")
    if kernel:
        os["kernel_version"] = kernel
    arch = facts.get("ansible_architecture")
    if arch:
        os["architecture"] = arch
    family = facts.get("ansible_os_family")
    if family:
        os["family"] = family
    return os


def _extract_ips(facts: dict) -> list[str]:
    ips: list[str] = []
    # ansible_all_ipv4_addresses / ansible_all_ipv6_addresses
    for key in ("ansible_all_ipv4_addresses", "ansible_all_ipv6_addresses"):
        val = facts.get(key)
        if isinstance(val, list):
            ips.extend(val)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result = []
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            result.append(ip)
    return result


def _extract_mounts(facts: dict) -> list[dict]:
    raw_mounts = facts.get("ansible_mounts") or []
    mounts = []
    for m in raw_mounts:
        entry: dict = {}
        if "mount" in m:
            entry["mount"] = m["mount"]
        if "device" in m:
            entry["device"] = m["device"]
        if "fstype" in m:
            entry["fstype"] = m["fstype"]
        size = m.get("size_total")
        if size is not None:
            entry["size_bytes"] = int(size)
        used = m.get("size_total") and m.get("size_available")
        used_bytes = None
        if m.get("size_total") is not None and m.get("size_available") is not None:
            used_bytes = int(m["size_total"]) - int(m["size_available"])
        if used_bytes is not None:
            entry["used_bytes"] = used_bytes
        avail = m.get("size_available")
        if avail is not None:
            entry["available_bytes"] = int(avail)
        if entry:
            mounts.append(entry)
    return mounts


def _extract_services(service_facts: dict) -> tuple[list[str], list[str]]:
    """Return (running_services, enabled_services) from ansible service_facts output."""
    facts = service_facts.get("ansible_facts") or {}
    services = facts.get("services") or {}

    running: list[str] = []
    enabled: list[str] = []

    for name, info in services.items():
        if not isinstance(info, dict):
            continue
        state = info.get("state", "")
        status = info.get("status", "")
        if state == "running":
            running.append(name)
        if status == "enabled":
            enabled.append(name)

    return sorted(running), sorted(enabled)


def _extract_containers(raw: dict) -> list[dict]:
    """
    Parse container output from ansible command module.

    Expects stdout with one JSON object per line (docker/podman --format json).
    """
    if "error" in raw or "stdout" not in raw:
        return []

    stdout = raw.get("stdout", "") or raw.get("stdout_lines", [])
    if isinstance(stdout, list):
        lines = stdout
    else:
        lines = stdout.splitlines()

    containers = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            entry: dict = {}
            # Normalise across docker/podman field naming
            name = obj.get("name") or obj.get("Names") or obj.get("Name")
            image = obj.get("image") or obj.get("Image")
            status = obj.get("status") or obj.get("Status") or obj.get("State")
            if name:
                entry["name"] = name
            if image:
                entry["image"] = image
            if status:
                entry["status"] = status
            if entry:
                containers.append(entry)
        except json.JSONDecodeError:
            continue

    return containers
