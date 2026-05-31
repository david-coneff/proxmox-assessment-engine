"""
Network parser – maps NetworkCollector raw output to normalized schema fields.

Raw shape (from collector/network.py):
{
  "interfaces": [
    {
      name, mac, mtu, state, type, addresses:[{address, prefix_len, family}],
      driver (optional), bond_members (optional), bridge_members (optional),
      vlan_id (optional)
    }
  ]
}
"""

from __future__ import annotations

from engine.parser import register_parser

_LOOPBACK_NAMES = {"lo"}


@register_parser("network")
def parse_network(raw: dict) -> dict:
    ifaces_raw = raw.get("interfaces") or []
    if not ifaces_raw:
        return {}

    interfaces = []
    for iface_raw in ifaces_raw:
        iface: dict = {}

        _copy_if(iface_raw, iface, [
            "name", "mac", "type", "mtu", "state",
            "addresses", "driver", "bond_members", "bridge_members",
        ])

        # speed/duplex – collector may or may not include these
        _copy_if(iface_raw, iface, ["speed_mbps", "duplex"])

        # vlan_id: keep even if None so schema consumers can distinguish
        # "not a VLAN" from "unknown"
        if "vlan_id" in iface_raw:
            iface["vlan_id"] = iface_raw["vlan_id"]

        if iface:
            interfaces.append(iface)

    if not interfaces:
        return {}

    return {"network": {"interfaces": interfaces}}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_if(src: dict, dst: dict, keys: list[str]) -> None:
    for key in keys:
        val = src.get(key)
        if val is not None:
            dst[key] = val
