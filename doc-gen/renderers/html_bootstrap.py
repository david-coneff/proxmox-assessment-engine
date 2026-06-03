#!/usr/bin/env python3
"""
html_bootstrap.py — HTML bootstrap workbook and runbook renderers.

Produces self-contained HTML equivalents of the ODS/ODT bootstrap documents.
Checkbox behavior is universal: checked → " done" italic, no strikethrough.

Public API:
  build_bootstrap_workbook_html(manifest, generation_meta) → str
  build_bootstrap_runbook_html(manifest, generation_meta)  → str

Stdlib only.
"""

from html import escape as _e
from html_base import (
    html_page, h, p, pre, code, ul, dl, table, divider,
    callout, section, score_badge,
    checkbox_item, checkbox_list, reset_checkbox_counter, commands_block,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(manifest: dict, path: str, default=None):
    obj = manifest
    for part in path.split("."):
        if not isinstance(obj, dict):
            return default
        obj = obj.get(part, default)
    return obj


def _str(v) -> str:
    if v is None:
        return "[UNRESOLVED]"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) if v else "(none)"
    return str(v)


def _vm_row(vm: dict) -> list[str]:
    return [
        _e(str(vm.get("vmid") or "?")),
        _e(vm.get("name") or "?"),
        _e(vm.get("role") or "?"),
        _e(str(vm.get("memory_mb") or vm.get("ram_gb", "?"))),
        _e(str(vm.get("cores") or "?")),
    ]


# ---------------------------------------------------------------------------
# Bootstrap Workbook HTML
# ---------------------------------------------------------------------------

def _wb_section_overview(manifest: dict) -> str:
    hi = manifest.get("host_identity") or {}
    sc = manifest.get("storage_config") or {}
    nt = manifest.get("network_topology") or {}
    zfs = sc.get("zfs_pool") or {}

    pairs = [
        ("Cell ID",    manifest.get("cell_id") or "[UNRESOLVED]"),
        ("Hostname",   hi.get("hostname") or "[UNRESOLVED]"),
        ("Domain",     hi.get("domain") or "—"),
        ("FQDN",       hi.get("fqdn") or "—"),
        ("Timezone",   (manifest.get("vm_defaults") or {}).get("timezone") or "UTC"),
        ("Network",    _str(nt.get("management_cidr"))),
        ("Gateway",    _str(nt.get("gateway"))),
        ("ZFS Pool",   zfs.get("pool_name") or "—"),
        ("ZFS Topology", zfs.get("topology") or "—"),
    ]
    body = dl(pairs)
    return section("Overview", body, open_=True)


def _wb_section_vms(manifest: dict) -> str:
    vms = manifest.get("vms") or []
    if not vms:
        return section("VM Inventory", p("No VMs declared."), open_=True)

    rows = [_vm_row(vm) for vm in vms]
    body = table(["VMID", "Name", "Role", "RAM", "Cores"], rows)
    return section("VM Inventory", body, open_=True)


def _wb_section_network(manifest: dict) -> str:
    nt = manifest.get("network_topology") or {}
    bridges = (nt.get("bridges") or []) + (nt.get("network_topology_declared", {}) or {}).get("bridges", [])

    pairs = [
        ("Profile",         nt.get("profile") or "—"),
        ("Management CIDR", _str(nt.get("management_cidr"))),
        ("Gateway",         _str(nt.get("gateway"))),
        ("DNS Servers",     _str(nt.get("dns_servers") or nt.get("nameservers"))),
    ]
    wan = nt.get("wan_config") or {}
    if wan:
        pairs += [
            ("Headscale URL", _str(wan.get("headscale_url"))),
            ("DDNS Provider", _str(wan.get("dns_provider"))),
            ("TLS Provider",  _str(wan.get("tls_provider"))),
        ]

    body = dl(pairs)
    if bridges:
        bridge_rows = [
            [_e(b.get("name", "?")), _e(b.get("address") or "—"),
             "Yes" if b.get("vlan_aware") else "No"]
            for b in bridges
        ]
        body += table(["Bridge", "Address", "VLAN-aware"], bridge_rows)

    return section("Network Configuration", body, open_=True)


def _wb_section_storage(manifest: dict) -> str:
    sc = manifest.get("storage_config") or {}
    zfs = sc.get("zfs_pool") or {}
    disks = sc.get("disks") or []

    pairs = [
        ("Pool Name",    zfs.get("pool_name") or "—"),
        ("Topology",     zfs.get("topology") or "—"),
        ("Datastore",    zfs.get("datastore_name") or "—"),
    ]
    body = dl(pairs)

    if disks:
        disk_rows = [
            [_e(d.get("id") or d.get("name") or "?"),
             _e(str(d.get("size_gb") or "?")),
             _e(d.get("role") or "data")]
            for d in disks
        ]
        body += table(["Disk ID", "Size (GB)", "Role"], disk_rows)

    return section("Storage Configuration", body, open_=True)


def _wb_section_k3s(manifest: dict) -> str:
    k3s = manifest.get("k3s_cluster") or {}
    pairs = [
        ("Pod CIDR",     _str(k3s.get("pod_cidr"))),
        ("Service CIDR", _str(k3s.get("service_cidr"))),
        ("CNI Plugin",   _str(k3s.get("cni"))),
        ("Server nodes", _str(len(k3s.get("server_nodes") or []))),
        ("Worker nodes", _str(len(k3s.get("worker_nodes") or []))),
    ]
    return section("k3s Cluster", dl(pairs), open_=False)


def _wb_section_dns_registry(manifest: dict) -> str:
    reg = manifest.get("dns_registry") or []
    if not reg:
        return section("DNS Registry", p("No DNS registry entries."), open_=False)
    rows = []
    for e in reg:
        rows.append([
            _e(e.get("hostname") or "?"),
            _e(e.get("ip") or e.get("address") or "?"),
            _e(e.get("role") or "?"),
        ])
    return section("DNS Registry", table(["Hostname", "IP", "Role"], rows), open_=False)


def _wb_section_secrets(manifest: dict) -> str:
    reg = manifest.get("secret_registry") or []
    if not reg:
        return section("Secret Registry", callout("warn", "No secrets declared. Run setup-secrets.py."), open_=False)
    rows = []
    for e in reg:
        rows.append([
            _e(e.get("id") or "?"),
            code(e.get("keepass_path") or "—"),
            "Yes" if e.get("required_for_recovery") else "No",
        ])
    return section("Secret Registry",
                   table(["ID", "KeePass Path", "Required for Recovery"], rows),
                   open_=False)


def _wb_section_backup(manifest: dict) -> str:
    bc = manifest.get("backup_config") or {}
    if not bc:
        return section("Backup Configuration",
                       callout("danger", "No backup configured. Run setup-backup.py."),
                       open_=False)
    parts = ""
    for layer_name, layer in (bc.get("layers") or {}).items():
        if not isinstance(layer, dict):
            continue
        parts += h(3, f"Layer: {_e(layer_name)}")
        dests = layer.get("destinations") or []
        if dests:
            rows = [[_e(d.get("type") or "?"), _e(d.get("rclone_remote") or d.get("path") or "—")]
                    for d in dests]
            parts += table(["Type", "Destination"], rows)
    return section("Backup Configuration", parts, open_=False)


def registry_ip_for_bootstrap_vm(manifest: dict) -> str | None:
    """
    Look up the IP for the infra-bootstrap VM from the DNS registry in manifest.
    Returns the IP string if found, None otherwise.
    Tries: role "infra-bootstrap", then hostname starting with "infra-bootstrap",
    then VMID 100 as conventional fallback.
    """
    dns_entries = manifest.get("dns_registry") or []
    for entry in dns_entries:
        role = entry.get("role", "")
        hostname = entry.get("hostname", "")
        if role == "infra-bootstrap" or hostname.startswith("infra-bootstrap"):
            ip = entry.get("ip") or entry.get("address")
            if ip:
                return ip
    for entry in dns_entries:
        try:
            if int(entry.get("vmid", -1)) == 100:
                ip = entry.get("ip") or entry.get("address")
                if ip:
                    return ip
        except (TypeError, ValueError):
            pass
    return None


def registry_iso_path(manifest: dict) -> str | None:
    """
    Derive the Proxmox ISO path from the template registry and storage config.
    Returns e.g. "local:iso/ubuntu-22.04.4-live-server-amd64.iso" or None.
    """
    base_images = manifest.get("base_images") or []
    if not base_images:
        return None
    source_iso = base_images[0].get("source_iso") or base_images[0].get("path", "")
    if not source_iso:
        return None
    storage_cfg = (manifest.get("bootstrap_state_storage")
                   or manifest.get("storage_config") or {})
    isos_store = storage_cfg.get("isos", "local:iso")
    return f"{isos_store}/{source_iso}"


def _wb_section_stage_03(manifest: dict) -> str:
    dns_reg = manifest.get("dns_registry") or []
    base_images = manifest.get("base_images") or []

    items = [
        "Proxmox host installed and accessible",
        "SSH key added to authorized_keys",
        "dnsmasq configured and running",
        "Headscale installed and running (WAN profile only)",
    ]

    # Infra-bootstrap VM IP from registry
    bootstrap_ip = registry_ip_for_bootstrap_vm(manifest)
    if bootstrap_ip:
        items.append(f"Infra-bootstrap VM — IP: {_e(bootstrap_ip)}")
        items.append(f"SSH check: ssh ubuntu@{_e(bootstrap_ip)} 'echo ok'")
    else:
        items.append("Infra-bootstrap VM — IP: [VM_IP] (populate dns-registry.yaml)")
        items.append("SSH check: ssh ubuntu@[VM_IP] 'echo ok'")

    # Per-VM IPs from dns_registry (all VMs)
    for vm in (manifest.get("vms") or []):
        ip = next(
            (e.get("ip") or e.get("address") for e in dns_reg
             if str(e.get("vmid")) == str(vm.get("vmid"))),
            "[IP]"
        )
        items.append(f"VM {_e(vm.get('name', '?'))} (VMID {vm.get('vmid', '?')}) — IP: {_e(str(ip))}")

    # ISO path from template registry
    iso = registry_iso_path(manifest)
    if iso:
        items.append(f"Base ISO: {_e(iso)}")
    else:
        iso_path = next((b.get("path") for b in base_images if b), None)
        if iso_path:
            items.append(f"Base ISO: {_e(iso_path)}")

    body = checkbox_list(items, id_prefix="stage03")
    return section("Stage 03 — VM Provisioning", body, open_=True)


def build_bootstrap_workbook_html(manifest: dict, generation_meta: dict) -> str:
    """Build a self-contained HTML bootstrap workbook."""
    reset_checkbox_counter()

    cell_id = manifest.get("cell_id") or "unknown"
    gen_at  = (generation_meta.get("generated_at_display")
               or generation_meta.get("generated_at") or "?")

    title = f"Bootstrap Workbook — {cell_id}"
    meta  = f"Generated: {gen_at}"

    body = ""
    body += p("This workbook tracks infrastructure setup progress. "
              "Check each item as it completes. "
              "State is saved in your browser (localStorage).")
    body += divider()
    body += _wb_section_overview(manifest)
    body += _wb_section_network(manifest)
    body += _wb_section_storage(manifest)
    body += _wb_section_vms(manifest)
    body += _wb_section_k3s(manifest)
    body += _wb_section_stage_03(manifest)
    body += _wb_section_dns_registry(manifest)
    body += _wb_section_secrets(manifest)
    body += _wb_section_backup(manifest)

    return html_page(title, body, doc_id=f"bootstrap-workbook-{cell_id}", meta=meta)


# ---------------------------------------------------------------------------
# Bootstrap Runbook HTML
# ---------------------------------------------------------------------------

def _rb_section_hardware_discovery(manifest: dict) -> str:
    hw = manifest.get("hardware") or {}
    pairs = [
        ("CPU",     hw.get("cpu_model") or "[HUMAN: run discovery]"),
        ("RAM",     str(hw.get("ram_gb") or hw.get("total_memory_gb") or "[HUMAN]") + " GB"),
        ("Disks",   str(len(hw.get("disks") or []))),
        ("NICs",    str(len(hw.get("nics") or []))),
    ]
    cmds = [
        "# Run hardware discovery on bare Proxmox host:",
        "python3 discover-hardware.py --host <proxmox-ip> --password-prompt",
        "# Output: hardware-profile.json",
    ]
    body = dl(pairs) + pre("\n".join(cmds))
    items = [
        "Hardware discovery complete (hardware-profile.json written)",
        "CPU meets minimum requirements (x86-64, VT-x enabled)",
        f"RAM meets minimum requirements (≥{hw.get('ram_gb', 16)} GB available)",
        "Storage meets minimum requirements",
    ]
    body += checkbox_list(items, id_prefix="hw-disc")
    return section("Stage 01 — Hardware Discovery", body, open_=True)


def _rb_section_planning(manifest: dict) -> str:
    hi = manifest.get("host_identity") or {}
    nt = manifest.get("network_topology") or {}
    sc = manifest.get("storage_config") or {}
    zfs = sc.get("zfs_pool") or {}

    pairs = [
        ("Hostname",          hi.get("hostname") or "[HUMAN]"),
        ("Domain",            hi.get("domain") or "[HUMAN]"),
        ("Cell ID",           manifest.get("cell_id") or "[HUMAN]"),
        ("Management CIDR",   _str(nt.get("management_cidr"))),
        ("Gateway",           _str(nt.get("gateway"))),
        ("ZFS Pool topology", zfs.get("topology") or "[HUMAN]"),
        ("Network profile",   nt.get("profile") or "lan"),
        ("Setup mode",        manifest.get("setup_mode") or "autonomous"),
    ]
    cmds = [
        "# Run forge planner on bare Proxmox host:",
        "python3 forge-planner.py --mode autonomous",
        "# Output: forge-manifest.json",
    ]
    body = dl(pairs) + pre("\n".join(cmds))
    items = [
        "forge-manifest.json created",
        "Cell ID confirmed",
        "Network configuration reviewed",
        "Storage topology matches hardware",
    ]
    body += checkbox_list(items, id_prefix="planning")
    return section("Stage 02 — Planning", body, open_=True)


def _rb_section_host_config(manifest: dict) -> str:
    nt  = manifest.get("network_topology") or {}
    wan = nt.get("wan_config") or {}

    cmds = [
        "# Run forge.sh on the target host:",
        "bash forge.sh",
        "# Phases: 00-discover → 01-plan → 02-validate → 03-host → 04-vms",
        "#         05-k3s → 06-flux → 07-intelligence → 08-verify",
    ]
    items = [
        "forge.sh phase-03 complete (host configuration)",
        "Hostname and /etc/hosts correct",
        "Network bridges active: ip link show",
        "ZFS pool created: zpool list",
        "dnsmasq running: systemctl status dnsmasq",
    ]
    if wan.get("headscale_url"):
        items.append("Headscale running: systemctl status headscale")
        items.append("Hatchery registered with its own Headscale")
    items += [
        "KeePass database initialised",
        "Proxmox subscription nag suppressed",
    ]
    body = pre("\n".join(cmds)) + checkbox_list(items, id_prefix="host-cfg")
    return section("Stage 03 — Host Configuration", body, open_=True)


def _rb_section_vm_provisioning(manifest: dict) -> str:
    vms = manifest.get("vms") or []

    cmds = [
        "# Phase 04 — VM provisioning via OpenTofu:",
        "cd opentofu/ && tofu init && tofu apply",
    ]
    items = ["OpenTofu apply succeeded — all VMs created"]
    for vm in vms:
        items.append(f"VM {_e(vm.get('name', '?'))} (VMID {vm.get('vmid', '?')}) running")

    body = pre("\n".join(cmds)) + checkbox_list(items, id_prefix="vm-prov")
    return section("Stage 04 — VM Provisioning", body, open_=True)


def _rb_section_k3s_bootstrap(manifest: dict) -> str:
    k3s = manifest.get("k3s_cluster") or {}
    cmds = [
        "# Phase 05 — k3s cluster bootstrap via Ansible:",
        "ansible-playbook -i inventory/ playbooks/k3s.yml",
        "# Verify:",
        "kubectl get nodes",
    ]
    items = [
        "k3s server nodes joined cluster",
        "k3s worker nodes joined cluster",
        "All nodes in Ready state: kubectl get nodes",
        f"Pod CIDR: {_str(k3s.get('pod_cidr'))}",
        f"Service CIDR: {_str(k3s.get('service_cidr'))}",
    ]
    body = pre("\n".join(cmds)) + checkbox_list(items, id_prefix="k3s-boot")
    return section("Stage 05 — k3s Cluster Bootstrap", body, open_=True)


def _rb_section_flux_gitops(manifest: dict) -> str:
    cmds = [
        "# Phase 06 — Flux CD bootstrap:",
        "flux bootstrap github --owner=<org> --repository=<repo>",
        "# Or from Forgejo:",
        "flux bootstrap git --url=https://<forgejo-fqdn>/<repo>",
        "# Verify reconciliation:",
        "flux get all",
    ]
    items = [
        "Flux bootstrap complete",
        "All Flux Kustomizations reconciled",
        "Forgejo running and accessible",
    ]
    body = pre("\n".join(cmds)) + checkbox_list(items, id_prefix="flux-boot")
    return section("Stage 06 — Flux GitOps Bootstrap", body, open_=True)


def _rb_section_intelligence_layer(manifest: dict) -> str:
    cmds = [
        "# Phase 07 — Intelligence layer bootstrap:",
        "python3 engine.py --mode bootstrap",
        "# Generates: Bootstrap-Workbook.html, Bootstrap-Runbook.html",
        "python3 engine.py --mode recovery",
        "# Generates: Recovery-Runbook.html",
    ]
    items = [
        "Assessment engine running",
        "Documentation engine generating reports",
        "Initial readiness score GREEN",
        "Commit bootstrap-state.json to Forgejo",
    ]
    body = pre("\n".join(cmds)) + checkbox_list(items, id_prefix="intel-layer")
    return section("Stage 07 — Intelligence Layer", body, open_=True)


def build_bootstrap_runbook_html(manifest: dict, generation_meta: dict) -> str:
    """Build a self-contained HTML bootstrap runbook."""
    reset_checkbox_counter()

    cell_id = manifest.get("cell_id") or "unknown"
    gen_at  = (generation_meta.get("generated_at_display")
               or generation_meta.get("generated_at") or "?")

    title = f"Bootstrap Runbook — {cell_id}"
    meta  = f"Generated: {gen_at}"

    body = ""
    body += p(
        "This runbook guides the forging process: from bare hardware to operational "
        "broodforge hatchery. Check each item as it completes."
    )
    body += p("Sequence: Discover → Plan → Validate → Host Config → VMs → k3s → Flux → Intelligence → Verify")
    body += divider()

    body += _rb_section_hardware_discovery(manifest)
    body += _rb_section_planning(manifest)
    body += _rb_section_host_config(manifest)
    body += _rb_section_vm_provisioning(manifest)
    body += _rb_section_k3s_bootstrap(manifest)
    body += _rb_section_flux_gitops(manifest)
    body += _rb_section_intelligence_layer(manifest)

    # Final validation
    final_items = [
        "All VMs running and accessible",
        "k3s cluster healthy: kubectl get nodes",
        "Flux reconciling: flux get all",
        "Assessment engine reporting GREEN",
        "bootstrap-state.json committed to Forgejo",
        "Recovery runbook generated and reviewed",
        "Backup configured and tested",
        "KeePass database backed up to configured destinations",
    ]
    body += section("Stage 08 — Final Verification",
                    checkbox_list(final_items, id_prefix="final-verify"),
                    open_=True)

    return html_page(title, body, doc_id=f"bootstrap-runbook-{cell_id}", meta=meta)
