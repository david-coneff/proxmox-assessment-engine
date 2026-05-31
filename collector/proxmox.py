"""Proxmox VE collector – gathers PVE version, VM/CT inventory, and storage pools."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from collector.base import BaseCollector


class ProxmoxCollector(BaseCollector):
    name = "proxmox"
    description = "Proxmox VE version, VM/CT inventory, and storage pool facts"

    def is_available(self) -> bool:
        return shutil.which("pvesh") is not None or Path("/etc/pve").exists()

    def collect(self) -> dict:
        return {
            "proxmox": self._collect_pve_info(),
            "vms": self._collect_guests(),
            "storage_pools": self._collect_storage(),
        }

    def _run(self, cmd: list[str]) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"{cmd} failed: {result.stderr.strip()}")
        return result.stdout

    def _collect_pve_info(self) -> dict:
        info: dict = {}

        # Version
        try:
            ver = self._run(["pveversion"]).strip()
            # e.g. "pve-manager/8.1.4/..."
            if "/" in ver:
                info["version"] = ver.split("/")[1]
            else:
                info["version"] = ver
        except (RuntimeError, FileNotFoundError):
            pass

        # Kernel
        try:
            info["kernel"] = self._run(["uname", "-r"]).strip()
        except RuntimeError:
            pass

        # Node name
        try:
            info["node_name"] = self._run(["hostname", "-s"]).strip()
        except RuntimeError:
            pass

        # Cluster
        try:
            raw = self._run(["pvesh", "get", "/cluster/status", "--output-format", "json"])
            cluster_data = json.loads(raw)
            members = []
            cluster_name = None
            for item in cluster_data:
                if item.get("type") == "cluster":
                    cluster_name = item.get("name")
                elif item.get("type") == "node":
                    members.append(item.get("name", ""))
            info["cluster_name"] = cluster_name
            info["cluster_members"] = members
        except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
            info["cluster_name"] = None
            info["cluster_members"] = []

        return info

    def _collect_guests(self) -> list[dict]:
        guests = []

        # QEMu VMs
        try:
            raw = self._run(["qm", "list", "--full"])
            for line in raw.splitlines()[1:]:  # skip header
                parts = line.split()
                if len(parts) < 3:
                    continue
                vmid = int(parts[0])
                name = parts[1]
                status = parts[2]
                guests.append({
                    "vmid": vmid,
                    "name": name,
                    "type": "qemu",
                    "status": status,
                })
        except (RuntimeError, FileNotFoundError):
            pass

        # LXC containers
        try:
            raw = self._run(["pct", "list"])
            for line in raw.splitlines()[1:]:
                parts = line.split()
                if len(parts) < 3:
                    continue
                vmid = int(parts[0])
                status = parts[1]
                name = parts[2]
                guests.append({
                    "vmid": vmid,
                    "name": name,
                    "type": "lxc",
                    "status": status,
                })
        except (RuntimeError, FileNotFoundError):
            pass

        return guests

    def _collect_storage(self) -> list[dict]:
        try:
            raw = self._run(["pvesh", "get", "/storage", "--output-format", "json"])
            pools_raw = json.loads(raw)
        except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
            return []

        pools = []
        for p in pools_raw:
            content = p.get("content", "").split(",") if p.get("content") else []
            pools.append({
                "name": p.get("storage", ""),
                "type": p.get("type", ""),
                "content": [c.strip() for c in content if c.strip()],
                "enabled": not p.get("disable", False),
            })
        return pools
