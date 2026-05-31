"""Storage collector – gathers disk, ZFS pool, and LVM facts."""

from __future__ import annotations

import json
import shutil
import subprocess

from collector.base import BaseCollector


class StorageCollector(BaseCollector):
    name = "storage"
    description = "Disk, ZFS pool, and LVM volume group facts"

    def collect(self) -> dict:
        return {
            "disks": self._collect_disks(),
            "zfs_pools": self._collect_zfs(),
            "lvm_volume_groups": self._collect_lvm(),
        }

    def _run(self, cmd: list[str], check: bool = True) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if check and result.returncode != 0:
            raise RuntimeError(f"{cmd[0]} failed: {result.stderr.strip()}")
        return result.stdout

    # ------------------------------------------------------------------

    def _collect_disks(self) -> list[dict]:
        if not shutil.which("lsblk"):
            return []
        try:
            raw = self._run([
                "lsblk", "--json", "--bytes", "--output",
                "NAME,MODEL,SERIAL,SIZE,ROTA,TYPE,TRAN,HCTL,WWN"
            ])
        except RuntimeError:
            return []

        data = json.loads(raw)
        disks = []
        for dev in data.get("blockdevices", []):
            if dev.get("type") != "disk":
                continue
            rota = dev.get("rota")
            if rota == "1":
                disk_type = "HDD"
            elif dev.get("tran") == "nvme":
                disk_type = "NVMe"
            else:
                disk_type = "SSD"

            disks.append({
                "name": dev.get("name", ""),
                "model": (dev.get("model") or "").strip(),
                "serial": (dev.get("serial") or "").strip(),
                "size_bytes": int(dev.get("size") or 0),
                "type": disk_type,
                "interface": (dev.get("tran") or "").upper(),
                "wwn": (dev.get("wwn") or "").strip(),
                "smart_status": self._smart_status(dev.get("name", "")),
            })
        return disks

    def _smart_status(self, dev_name: str) -> str:
        if not shutil.which("smartctl") or not dev_name:
            return "UNKNOWN"
        try:
            result = subprocess.run(
                ["smartctl", "-H", f"/dev/{dev_name}"],
                capture_output=True, text=True, timeout=15
            )
            output = result.stdout
            if "PASSED" in output:
                return "PASSED"
            if "FAILED" in output:
                return "FAILED"
        except Exception:
            pass
        return "UNKNOWN"

    def _collect_zfs(self) -> list[dict]:
        if not shutil.which("zpool"):
            return []
        try:
            raw = self._run(["zpool", "list", "-H", "-p", "-o",
                             "name,state,size,alloc,free,frag,dedup,health"])
        except RuntimeError:
            return []

        pools = []
        for line in raw.splitlines():
            parts = line.split("\t")
            if len(parts) < 8:
                continue
            name, state, size, alloc, free, frag, dedup, health = parts[:8]
            pools.append({
                "name": name,
                "state": state,
                "size_bytes": _to_int(size),
                "alloc_bytes": _to_int(alloc),
                "free_bytes": _to_int(free),
                "fragmentation_pct": _to_float(frag.rstrip("%")),
                "dedup_ratio": _to_float(dedup.rstrip("x")),
                "health": health,
            })
        return pools

    def _collect_lvm(self) -> list[dict]:
        if not shutil.which("vgs"):
            return []
        try:
            raw = self._run([
                "vgs", "--noheadings", "--units", "b", "--nosuffix",
                "-o", "vg_name,vg_size,vg_free,pv_count,lv_count"
            ])
        except RuntimeError:
            return []

        vgs = []
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            vgs.append({
                "name": parts[0],
                "size_bytes": _to_int(parts[1]),
                "free_bytes": _to_int(parts[2]),
                "pv_count": int(parts[3]),
                "lv_count": int(parts[4]),
            })
        return vgs


def _to_int(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def _to_float(s: str) -> float:
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0
