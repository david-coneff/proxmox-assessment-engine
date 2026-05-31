"""Network collector – gathers interface facts via ip(8)."""

from __future__ import annotations

import json
import shutil
import subprocess

from collector.base import BaseCollector


class NetworkCollector(BaseCollector):
    name = "network"
    description = "Network interface facts via ip(8)"

    def is_available(self) -> bool:
        return shutil.which("ip") is not None

    def collect(self) -> dict:
        return {"interfaces": self._collect_interfaces()}

    def _run(self, cmd: list[str]) -> str:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise RuntimeError(f"{cmd} failed: {result.stderr.strip()}")
        return result.stdout

    def _collect_interfaces(self) -> list[dict]:
        try:
            raw = self._run(["ip", "-j", "-d", "addr"])
        except RuntimeError:
            return []

        data = json.loads(raw)
        interfaces = []

        for iface in data:
            name = iface.get("ifname", "")
            link_type = iface.get("link_type", "")
            flags = iface.get("flags", [])

            iface_dict: dict = {
                "name": name,
                "mac": iface.get("address", ""),
                "mtu": iface.get("mtu"),
                "state": "UP" if "UP" in flags else "DOWN",
                "type": _classify_interface(name, iface),
                "addresses": [],
            }

            for addr_info in iface.get("addr_info", []):
                iface_dict["addresses"].append({
                    "address": addr_info.get("local", ""),
                    "prefix_len": addr_info.get("prefixlen"),
                    "family": addr_info.get("family", ""),
                })

            # Driver (best-effort via ethtool or linkinfo)
            linkinfo = iface.get("linkinfo", {})
            driver = linkinfo.get("info_kind") or _ethtool_driver(name)
            if driver:
                iface_dict["driver"] = driver

            # Bond / bridge members
            if "bond_slave" in str(linkinfo.get("info_slave_kind", "")):
                iface_dict["bond_members"] = []
            if linkinfo.get("info_kind") == "bond":
                iface_dict["bond_members"] = _bond_members(name)
            if linkinfo.get("info_kind") == "bridge":
                iface_dict["bridge_members"] = _bridge_members(name)

            interfaces.append(iface_dict)

        return interfaces


def _classify_interface(name: str, data: dict) -> str:
    linkinfo = data.get("linkinfo", {})
    kind = linkinfo.get("info_kind", "")
    if kind == "bond":
        return "bond"
    if kind == "bridge":
        return "bridge"
    if kind == "vlan":
        return "vlan"
    if name == "lo":
        return "loopback"
    return "physical"


def _ethtool_driver(name: str) -> str:
    if not shutil.which("ethtool"):
        return ""
    try:
        result = subprocess.run(
            ["ethtool", "-i", name], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if line.startswith("driver:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""


def _bond_members(bond_name: str) -> list[str]:
    try:
        import os
        path = f"/sys/class/net/{bond_name}/bonding/slaves"
        return open(path).read().split()
    except OSError:
        return []


def _bridge_members(bridge_name: str) -> list[str]:
    try:
        import os
        path = f"/sys/class/net/{bridge_name}/brif"
        return os.listdir(path)
    except OSError:
        return []
