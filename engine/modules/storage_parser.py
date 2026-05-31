"""
Storage parser – maps StorageCollector raw output to normalized schema fields.

Raw shape (from collector/storage.py):
{
  "disks": [
    { name, model, serial, size_bytes, type, interface, wwn, smart_status }
  ],
  "zfs_pools": [
    { name, state, size_bytes, alloc_bytes, free_bytes,
      fragmentation_pct, dedup_ratio, health }
  ],
  "lvm_volume_groups": [
    { name, size_bytes, free_bytes, pv_count, lv_count }
  ],
}
"""

from __future__ import annotations

from engine.parser import register_parser


@register_parser("storage")
def parse_storage(raw: dict) -> dict:
    fragment: dict = {"storage": {}}
    storage = fragment["storage"]

    disks_raw = raw.get("disks") or []
    zfs_raw = raw.get("zfs_pools") or []
    lvm_raw = raw.get("lvm_volume_groups") or []

    # ---- disks ----
    disks = []
    for d in disks_raw:
        disk: dict = {}
        _copy_if(d, disk, [
            "name", "model", "serial", "firmware_rev", "size_bytes",
            "type", "rotation_rpm", "interface", "smart_status",
            "smart_attributes", "wwn",
        ])
        if disk:
            disks.append(disk)
    if disks:
        storage["disks"] = disks

    # ---- ZFS pools ----
    pools = []
    for p in zfs_raw:
        pool: dict = {}
        _copy_if(p, pool, [
            "name", "state", "size_bytes", "alloc_bytes", "free_bytes",
            "fragmentation_pct", "dedup_ratio", "health", "vdevs",
        ])
        if pool:
            pools.append(pool)
    if pools:
        storage["zfs_pools"] = pools

    # ---- LVM volume groups ----
    vgs = []
    for v in lvm_raw:
        vg: dict = {}
        _copy_if(v, vg, ["name", "size_bytes", "free_bytes", "pv_count", "lv_count"])
        if vg:
            vgs.append(vg)
    if vgs:
        storage["lvm_volume_groups"] = vgs

    # Drop empty storage key
    if not storage:
        return {}

    return fragment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_if(src: dict, dst: dict, keys: list[str]) -> None:
    """Copy keys that exist and are not None from src to dst."""
    for key in keys:
        val = src.get(key)
        if val is not None:
            dst[key] = val
