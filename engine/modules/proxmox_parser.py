"""
Proxmox parser – maps ProxmoxCollector raw output to normalized schema fields.

Raw shape (from collector/proxmox.py):
{
  "proxmox": {
    version, kernel, node_name,
    cluster_name (str|null), cluster_members ([str])
  },
  "vms": [
    { vmid, name, type, status, cpus (opt), memory_bytes (opt),
      disk_bytes (opt), template (opt), tags (opt) }
  ],
  "storage_pools": [
    { name, type, content:[str], enabled }
  ],
}
"""

from __future__ import annotations

from engine.parser import register_parser


@register_parser("proxmox")
def parse_proxmox(raw: dict) -> dict:
    pve_raw = raw.get("proxmox") or {}
    vms_raw = raw.get("vms") or []
    pools_raw = raw.get("storage_pools") or []

    virtualization: dict = {}

    # ---- proxmox node info ----
    if pve_raw:
        pve: dict = {}
        _copy_if(pve_raw, pve, [
            "version", "kernel", "node_name", "cluster_name", "cluster_members",
        ])
        if pve:
            virtualization["proxmox"] = pve

    # ---- VMs / containers ----
    vms = []
    for v in vms_raw:
        vm: dict = {}
        _copy_if(v, vm, [
            "vmid", "name", "type", "status", "cpus",
            "memory_bytes", "disk_bytes", "template", "tags",
        ])
        if vm:
            vms.append(vm)
    if vms:
        virtualization["vms"] = vms

    # ---- storage pools ----
    pools = []
    for p in pools_raw:
        pool: dict = {}
        _copy_if(p, pool, [
            "name", "type", "content", "total_bytes", "used_bytes", "enabled",
        ])
        if pool:
            pools.append(pool)
    if pools:
        virtualization["storage_pools"] = pools

    if not virtualization:
        return {}

    return {"virtualization": virtualization}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_if(src: dict, dst: dict, keys: list[str]) -> None:
    for key in keys:
        val = src.get(key)
        if val is not None:
            dst[key] = val
