"""
Node assessment report generator (Phase 4).

Produces a Markdown report of the Proxmox node's observed state:
  - Node summary
  - Hardware (CPU, memory, system board)
  - Firmware / BIOS
  - Storage (disks, ZFS pools, LVM VGs)
  - Network interfaces
  - Operating system
  - Proxmox VE (version, cluster, VM/CT inventory, storage pools)

All content is factual.  No recommendations are generated.
"""

from __future__ import annotations

import json
from collections import Counter


def generate_report(assessment: dict, fmt: str = "markdown") -> str:
    """Generate a node assessment report.  fmt: 'markdown' or 'json'."""
    if fmt == "json":
        return json.dumps(assessment, indent=2, default=str)
    return _markdown_report(assessment)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

def _markdown_report(a: dict) -> str:
    sections = [
        _header(a),
        _node_summary(a),
        _hardware(a),
        _firmware(a),
        _storage(a),
        _network(a),
        _os(a),
        _proxmox(a),
    ]
    return "\n\n".join(s for s in sections if s)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _header(a: dict) -> str:
    return (
        f"# Node Assessment Report\n\n"
        f"**Hostname:** {a.get('hostname', 'unknown')}  \n"
        f"**Assessment timestamp:** {a.get('timestamp', 'unknown')}  \n"
        f"**Schema version:** {a.get('schema_version', 'unknown')}"
    )


def _node_summary(a: dict) -> str:
    hw = a.get("hardware") or {}
    cpu = hw.get("cpu") or {}
    mem = hw.get("memory") or {}
    sys = hw.get("system") or {}
    pve = (a.get("virtualization") or {}).get("proxmox") or {}
    os_facts = a.get("os") or {}
    vms = (a.get("virtualization") or {}).get("vms") or []
    guests = a.get("guests") or []

    rows = []
    if sys.get("manufacturer"):
        rows.append(("System", f"{sys.get('manufacturer', '')} {sys.get('product_name', '')}".strip()))
    if cpu.get("model"):
        rows.append(("CPU", cpu["model"]))
    if cpu.get("total_cores"):
        cores = cpu["total_cores"]
        threads = cpu.get("total_threads", "")
        rows.append(("Cores / Threads", f"{cores} / {threads}" if threads else str(cores)))
    if mem.get("total_bytes") is not None:
        rows.append(("Memory", _bytes(mem["total_bytes"])))
    if os_facts.get("kernel_version"):
        rows.append(("Kernel", os_facts["kernel_version"]))
    if pve.get("version"):
        rows.append(("Proxmox VE", pve["version"]))
    if pve.get("cluster_name"):
        rows.append(("Cluster", pve["cluster_name"]))
    rows.append(("VMs / containers", str(len(vms))))
    rows.append(("Assessed guests", str(len(guests))))

    lines = ["## Node Summary", "", "| Property | Value |", "|----------|-------|"]
    for prop, val in rows:
        lines.append(f"| {prop} | {val} |")
    return "\n".join(lines)


def _hardware(a: dict) -> str:
    hw = a.get("hardware") or {}
    if not hw:
        return ""

    sections = []

    # CPU
    cpu = hw.get("cpu") or {}
    if cpu:
        rows = []
        if cpu.get("model"):    rows.append(("Model", cpu["model"]))
        if cpu.get("vendor"):   rows.append(("Vendor", cpu["vendor"]))
        if cpu.get("architecture"): rows.append(("Architecture", cpu["architecture"]))
        if cpu.get("sockets"):  rows.append(("Sockets", str(cpu["sockets"])))
        if cpu.get("total_cores"): rows.append(("Total cores", str(cpu["total_cores"])))
        if cpu.get("total_threads"): rows.append(("Total threads", str(cpu["total_threads"])))
        if cpu.get("flags"):    rows.append(("Key flags", ", ".join(cpu["flags"][:20])))
        lines = ["### CPU", "", "| Property | Value |", "|----------|-------|"]
        for p, v in rows:
            lines.append(f"| {p} | {v} |")
        sections.append("\n".join(lines))

    # Memory
    mem = hw.get("memory") or {}
    if mem:
        rows = []
        if mem.get("total_bytes") is not None:
            rows.append(("Total", _bytes(mem["total_bytes"])))
        if mem.get("ecc_enabled") is not None:
            rows.append(("ECC", "yes" if mem["ecc_enabled"] else "no"))
        dimms = mem.get("dimms") or []
        rows.append(("DIMM slots populated", str(len(dimms))))

        lines = ["### Memory", "", "| Property | Value |", "|----------|-------|"]
        for p, v in rows:
            lines.append(f"| {p} | {v} |")

        if dimms:
            lines += ["", "| Slot | Size | Type | Speed | Manufacturer | ECC |",
                      "|------|------|------|-------|--------------|-----|"]
            for d in dimms:
                lines.append(
                    f"| {d.get('slot','')} "
                    f"| {_bytes(d['size_bytes']) if d.get('size_bytes') else ''} "
                    f"| {d.get('type','')} "
                    f"| {str(d['speed_mhz'])+' MHz' if d.get('speed_mhz') else ''} "
                    f"| {d.get('manufacturer','')} "
                    f"| {'yes' if d.get('ecc') else 'no'} |"
                )
        sections.append("\n".join(lines))

    # System board
    sys = hw.get("system") or {}
    bb = hw.get("baseboard") or {}
    if sys or bb:
        lines = ["### System Board", "", "| Property | Value |", "|----------|-------|"]
        if sys.get("manufacturer"):  lines.append(f"| System manufacturer | {sys['manufacturer']} |")
        if sys.get("product_name"):  lines.append(f"| System model | {sys['product_name']} |")
        if sys.get("serial_number"): lines.append(f"| System serial | {sys['serial_number']} |")
        if bb.get("manufacturer"):   lines.append(f"| Board manufacturer | {bb['manufacturer']} |")
        if bb.get("product_name"):   lines.append(f"| Board model | {bb['product_name']} |")
        if bb.get("version"):        lines.append(f"| Board version | {bb['version']} |")
        sections.append("\n".join(lines))

    if not sections:
        return ""
    return "## Hardware\n\n" + "\n\n".join(sections)


def _firmware(a: dict) -> str:
    fw = a.get("firmware") or {}
    bios = fw.get("bios") or {}
    if not bios:
        return ""

    lines = ["## Firmware", "", "| Property | Value |", "|----------|-------|"]
    if bios.get("vendor"):       lines.append(f"| BIOS vendor | {bios['vendor']} |")
    if bios.get("version"):      lines.append(f"| BIOS version | {bios['version']} |")
    if bios.get("release_date"): lines.append(f"| BIOS date | {bios['release_date']} |")
    if fw.get("uefi") is not None:
        lines.append(f"| UEFI | {'yes' if fw['uefi'] else 'no'} |")
    if fw.get("secure_boot") is not None:
        lines.append(f"| Secure Boot | {'yes' if fw['secure_boot'] else 'no'} |")
    return "\n".join(lines)


def _storage(a: dict) -> str:
    st = a.get("storage") or {}
    if not st:
        return ""

    sections = []

    # Disks
    disks = st.get("disks") or []
    if disks:
        lines = [
            "### Disks", "",
            "| Device | Model | Type | Interface | Size | SMART |",
            "|--------|-------|------|-----------|------|-------|",
        ]
        for d in disks:
            lines.append(
                f"| {d.get('name','')} "
                f"| {d.get('model','')} "
                f"| {d.get('type','')} "
                f"| {d.get('interface','')} "
                f"| {_bytes(d['size_bytes']) if d.get('size_bytes') else ''} "
                f"| {d.get('smart_status','UNKNOWN')} |"
            )
        sections.append("\n".join(lines))

    # ZFS pools
    pools = st.get("zfs_pools") or []
    if pools:
        lines = [
            "### ZFS Pools", "",
            "| Pool | State | Health | Size | Allocated | Free | Frag% |",
            "|------|-------|--------|------|-----------|------|-------|",
        ]
        for p in pools:
            lines.append(
                f"| {p.get('name','')} "
                f"| {p.get('state','')} "
                f"| {p.get('health','')} "
                f"| {_bytes(p['size_bytes']) if p.get('size_bytes') else ''} "
                f"| {_bytes(p['alloc_bytes']) if p.get('alloc_bytes') else ''} "
                f"| {_bytes(p['free_bytes']) if p.get('free_bytes') else ''} "
                f"| {p.get('fragmentation_pct', '')} |"
            )
        sections.append("\n".join(lines))

    # LVM VGs
    vgs = st.get("lvm_volume_groups") or []
    if vgs:
        lines = [
            "### LVM Volume Groups", "",
            "| VG | Size | Free | PVs | LVs |",
            "|----|------|------|-----|-----|",
        ]
        for v in vgs:
            lines.append(
                f"| {v.get('name','')} "
                f"| {_bytes(v['size_bytes']) if v.get('size_bytes') else ''} "
                f"| {_bytes(v['free_bytes']) if v.get('free_bytes') else ''} "
                f"| {v.get('pv_count','')} "
                f"| {v.get('lv_count','')} |"
            )
        sections.append("\n".join(lines))

    if not sections:
        return ""
    return "## Storage\n\n" + "\n\n".join(sections)


def _network(a: dict) -> str:
    ifaces = (a.get("network") or {}).get("interfaces") or []
    if not ifaces:
        return ""

    lines = [
        "## Network", "",
        "| Interface | Type | State | Speed | MTU | MAC | Addresses |",
        "|-----------|------|-------|-------|-----|-----|-----------|",
    ]
    for iface in ifaces:
        addrs = ", ".join(
            f"{addr.get('address','')}/{addr.get('prefix_len','')}"
            for addr in (iface.get("addresses") or [])
        )
        speed = f"{iface['speed_mbps']} Mbps" if iface.get("speed_mbps") else ""
        lines.append(
            f"| {iface.get('name','')} "
            f"| {iface.get('type','')} "
            f"| {iface.get('state','')} "
            f"| {speed} "
            f"| {iface.get('mtu','')} "
            f"| {iface.get('mac','')} "
            f"| {addrs} |"
        )
    return "\n".join(lines)


def _os(a: dict) -> str:
    os_facts = a.get("os") or {}
    if not os_facts:
        return ""

    lines = ["## Operating System", "", "| Property | Value |", "|----------|-------|"]
    for label, key in [
        ("Name", "name"), ("Version", "version"), ("Kernel", "kernel_version"),
        ("Architecture", "architecture"),
    ]:
        val = os_facts.get(key)
        if val:
            lines.append(f"| {label} | {val} |")
    uptime = os_facts.get("uptime_seconds")
    if uptime is not None:
        lines.append(f"| Uptime | {_uptime(uptime)} |")
    return "\n".join(lines)


def _proxmox(a: dict) -> str:
    virt = a.get("virtualization") or {}
    pve = virt.get("proxmox") or {}
    vms = virt.get("vms") or []
    pools = virt.get("storage_pools") or []
    if not pve and not vms and not pools:
        return ""

    sections = []

    # PVE info
    if pve:
        lines = ["### Proxmox VE", "", "| Property | Value |", "|----------|-------|"]
        if pve.get("version"):      lines.append(f"| Version | {pve['version']} |")
        if pve.get("kernel"):       lines.append(f"| Kernel | {pve['kernel']} |")
        if pve.get("node_name"):    lines.append(f"| Node name | {pve['node_name']} |")
        cluster = pve.get("cluster_name")
        if cluster:
            lines.append(f"| Cluster | {cluster} |")
            members = pve.get("cluster_members") or []
            if members:
                lines.append(f"| Cluster members | {', '.join(members)} |")
        sections.append("\n".join(lines))

    # VM / LXC inventory
    if vms:
        qemu = [v for v in vms if v.get("type") == "qemu"]
        lxc  = [v for v in vms if v.get("type") == "lxc"]

        status_counter: Counter = Counter(v.get("status", "unknown") for v in vms)
        summary_rows = [f"Total: {len(vms)}"]
        for status, count in sorted(status_counter.items()):
            summary_rows.append(f"{status}: {count}")

        lines = [
            "### Guests (VMs and Containers)", "",
            f"*{', '.join(summary_rows)}*", "",
        ]
        if qemu:
            lines += [
                "**QEMU VMs**", "",
                "| VMID | Name | Status |",
                "|------|------|--------|",
            ]
            for v in sorted(qemu, key=lambda x: x.get("vmid", 0)):
                lines.append(f"| {v.get('vmid','')} | {v.get('name','')} | {v.get('status','')} |")
            lines.append("")
        if lxc:
            lines += [
                "**LXC Containers**", "",
                "| VMID | Name | Status |",
                "|------|------|--------|",
            ]
            for v in sorted(lxc, key=lambda x: x.get("vmid", 0)):
                lines.append(f"| {v.get('vmid','')} | {v.get('name','')} | {v.get('status','')} |")
        sections.append("\n".join(lines))

    # Storage pools
    if pools:
        lines = [
            "### Storage Pools", "",
            "| Pool | Type | Content | Enabled |",
            "|------|------|---------|---------|",
        ]
        for p in pools:
            content = ", ".join(p.get("content") or [])
            lines.append(
                f"| {p.get('name','')} "
                f"| {p.get('type','')} "
                f"| {content} "
                f"| {'yes' if p.get('enabled', True) else 'no'} |"
            )
        sections.append("\n".join(lines))

    if not sections:
        return ""
    return "## Proxmox VE\n\n" + "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bytes(n: int) -> str:
    """Human-readable byte size."""
    if n is None:
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _uptime(seconds: int) -> str:
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    parts = []
    if days:  parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if mins:  parts.append(f"{mins}m")
    return " ".join(parts) if parts else "0m"
