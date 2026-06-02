#!/usr/bin/env python3
"""
html_recovery_runbook.py — HTML recovery runbook renderer.

Produces a self-contained HTML file equivalent to the ODT recovery runbook.
All checkboxes use the universal broodforge checkbox behavior:
  - When checked: shows " done" in italics to the right
  - No strikethrough on label text

Public API:
  build_recovery_runbook_html(manifest, graph, readiness, generation_meta) → str

Stdlib only.
"""

from html import escape as _e
from html_base import (
    html_page, h, p, pre, code, ul, ol, dl, table,
    callout, divider, section, score_badge,
    checkbox_item, checkbox_list, reset_checkbox_counter,
    commands_block,
)

try:
    from readiness import SCORE_SYMBOLS
except Exception:
    SCORE_SYMBOLS = {"GREEN": "✓", "YELLOW": "▲", "ORANGE": "●", "RED": "✗", "BLOCKED": "⊘"}


# ---------------------------------------------------------------------------
# Manifest helpers (mirror recovery_runbook.py utilities)
# ---------------------------------------------------------------------------

def _get(manifest: dict, path: str, default=None):
    obj = manifest
    for p_ in path.split("."):
        if not isinstance(obj, dict):
            return default
        obj = obj.get(p_, default)
    return obj


def _resolve_vm_ip(vmid, manifest: dict) -> str:
    if vmid is None:
        return "[VM_IP]"
    for entry in (manifest.get("dns_registry") or []):
        try:
            if str(entry.get("vmid")) == str(vmid) or str(entry.get("ip")) == str(vmid):
                return entry.get("ip") or entry.get("address") or "[VM_IP]"
        except Exception:
            pass
    return "[VM_IP]"


def _fmt_cmds(cmds: list[str]) -> str:
    if not cmds:
        return ""
    return pre("\n".join(cmds))


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_warnings(readiness, graph) -> str:
    node_map = graph.node_map() if hasattr(graph, "node_map") else {}
    red_comps = [c for c in readiness.components if c.score == "RED"]
    blocked   = [c for c in readiness.components if c.score == "BLOCKED"]
    if not red_comps and not blocked:
        return ""

    items = []
    for c in red_comps:
        node = node_map.get(c.component_id)
        label = node.label if node else c.component_id
        items.append(callout("danger", f"<strong>RED:</strong> {_e(label)} — {_e(c.score_reason)}"))
    for c in blocked:
        node       = node_map.get(c.component_id)
        blocker    = node_map.get(c.blocked_by or "")
        lbl        = node.label if node else c.component_id
        blk_lbl    = blocker.label if blocker else (c.blocked_by or "?")
        items.append(callout("warn", f"<strong>BLOCKED:</strong> {_e(lbl)} — blocked by {_e(blk_lbl)}"))

    body = "".join(items)
    return section("⚠ Pre-Recovery Warnings", body, open_=True)


def _section_readiness_summary(readiness) -> str:
    rows = []
    for c in readiness.components:
        rows.append([score_badge(c.score), _e(c.component_id), _e(c.score_reason or "")])
    if not rows:
        return ""
    t = table(["Score", "Component", "Reason"], rows)
    return section("Readiness Summary", t, open_=False)


def _section_pre_recovery_checklist(manifest: dict) -> str:
    ext_backup = manifest.get("external_backup") or {}
    provider   = ext_backup.get("provider") or "unknown"

    items: list[str] = []

    if provider == "github":
        gh = ext_backup.get("github") or {}
        repos = gh.get("repos") or {}
        url   = repos.get("bootstrap") or repos.get("infrastructure") or "[HUMAN: GitHub URL]"
        items.append(f"Clone bootstrap repo: {_e(url)}")
        items.append("bootstrap-state.json present and readable")
        items.append("Secret registry loaded")
    elif provider == "encrypted-archive":
        arch = ext_backup.get("encrypted_archive") or {}
        dest = arch.get("destination") or "[HUMAN: archive location]"
        items.append(f"Download archive from: {_e(dest)}")
        items.append("Decrypt archive (passphrase from KeePass)")
        items.append("bootstrap-state.json present and readable")
    else:
        items.append("[HUMAN] Locate and restore bootstrap-state.json from backup")
        items.append("bootstrap-state.json readable")

    items += [
        "KeePass database unlocked (master password available)",
        "Replacement hardware meets minimum requirements (RAM, storage, NICs)",
        "Network connectivity confirmed (management CIDR reachable)",
    ]

    body = (
        p("Complete all items before beginning restore operations.") +
        checkbox_list(items, id_prefix="pre-rec")
    )
    return section("Pre-Recovery Checklist", body, open_=True)


def _section_wave0_network(manifest: dict) -> str:
    nt   = manifest.get("network_topology_declared") or {}
    bridges = nt.get("bridges") or []

    if not bridges:
        body = callout("warn", "Network topology not declared. Recreate bridges manually.")
        return section("Wave 0 — Network Reconstruction", body, open_=True)

    gw    = nt.get("gateway") or "[unknown]"
    drift = nt.get("drift_detected", False)

    parts = ""
    if drift:
        parts += callout("warn", "⚠ Network topology drift detected — verify bridges match expected configuration.")

    rows = []
    for b in bridges:
        rows.append([
            _e(b.get("name", "?")),
            _e(b.get("address") or "—"),
            "Yes" if b.get("vlan_aware") else "No",
            _e(", ".join(b.get("ports") or []) or "—"),
        ])
    parts += table(["Bridge", "Address", "VLAN-aware", "Ports"], rows)

    cmds = [
        "# Reconstruct from /etc/network/interfaces",
        "ifreload -a",
        "# Verify:",
        "ip link show",
        "ip addr show",
    ]
    parts += pre("\n".join(cmds))

    items = [
        f"Management bridge up (gateway {_e(gw)} reachable)",
        "All declared bridges active: ip link show",
        "No unexpected drift from declared topology",
    ]
    parts += checkbox_list(items, id_prefix="wave0")

    return section("Wave 0 — Network Reconstruction", parts, open_=True)


def _section_restore_wave(wave, manifest: dict, node_map: dict, idx: int) -> str:
    wave_label = f"Wave {idx} — {wave.name}"
    mins_hint  = f" (~{wave.estimated_minutes} min)" if getattr(wave, "estimated_minutes", None) else ""

    parts = ""
    if wave.prerequisites:
        prereq_str = ", ".join(wave.prerequisites)
        parts += p(f"Prerequisites: {_e(prereq_str)}")

    for node in wave.restore_order:
        parts += _vm_restore_block(node, manifest, node_map)

    return section(wave_label + mins_hint, parts, open_=True)


def _vm_restore_block(node, manifest: dict, node_map: dict) -> str:
    vm_ip   = _resolve_vm_ip(getattr(node, "vmid", None), manifest)
    vm_name = getattr(node, "label", "?")

    parts = h(3, f"{_e(vm_name)} ({_e(vm_ip)})")

    # Provenance
    prov_reg = manifest.get("provenance_records") or []
    prov = next((r for r in prov_reg if str(r.get("vmid")) == str(getattr(node, "vmid", ""))), None)
    if prov:
        pairs = []
        if prov.get("tofu_workspace"):
            pairs.append(("IaC workspace", prov["tofu_workspace"]))
        if prov.get("ansible_role"):
            pairs.append(("Ansible role", prov["ansible_role"]))
        if prov.get("source_commit"):
            pairs.append(("Source commit", prov["source_commit"]))
        if pairs:
            parts += dl(pairs)

    # Restore commands
    vmid = getattr(node, "vmid", None)
    if vmid:
        restore_cmds = [
            f"# Restore from PBS backup",
            f"qmrestore {vmid} --storage local-zfs --force",
            f"qm start {vmid}",
            f"# Wait for SSH readiness:",
            f"until ssh ubuntu@{vm_ip} 'echo ok'; do sleep 5; done",
        ]
        parts += pre("\n".join(restore_cmds))

    # Service contract block (from manifest)
    contract = _get_contract(vm_name, manifest)
    if contract:
        parts += _service_contract_block(contract, vm_ip)

    # Validation checkboxes
    items = [
        f"VM {_e(vm_name)} (VMID {vmid}) restored and running",
        f"SSH accessible: ssh ubuntu@{_e(vm_ip)}",
    ]
    if contract:
        for iface in (contract.get("provided_interfaces") or []):
            iface_type = iface.get("type", "")
            items.append(f"Health check: {_e(iface_type)} on {_e(vm_ip)}")
    items.append(f"Service healthy: logs clean, no ERROR entries")
    parts += checkbox_list(items, id_prefix=f"vm-{vm_name}")

    return parts


def _get_contract(vm_name: str, manifest: dict) -> dict | None:
    for sc in (manifest.get("service_contracts") or []):
        if sc.get("vm_name") == vm_name or sc.get("service") == vm_name:
            return sc
    return None


def _service_contract_block(contract: dict, vm_ip: str) -> str:
    svc = contract.get("service") or contract.get("service_name") or "?"
    parts = h(4, f"Service Contract: {_e(svc)}")

    provided = contract.get("provided_interfaces") or []
    if provided:
        cmds = []
        for iface in provided:
            itype = iface.get("type", "")
            if itype == "http":
                port = iface.get("port", 80)
                cmds.append(f"curl -sf http://{vm_ip}:{port}/health || curl -sf http://{vm_ip}:{port}/")
            elif itype == "https":
                port = iface.get("port", 443)
                cmds.append(f"curl -skf https://{vm_ip}:{port}/")
            elif itype == "postgresql":
                cmds.append(f"pg_isready -h {vm_ip} -U postgres")
            elif itype == "smtp":
                port = iface.get("port", 25)
                cmds.append(f"nc -z -w5 {vm_ip} {port}")
        if cmds:
            parts += p("Health check commands:")
            parts += pre("\n".join(cmds))

    # Service restart
    if contract.get("systemd_service"):
        svc_name = contract["systemd_service"]
        parts += p("Restart command:")
        parts += pre(f"ssh ubuntu@{vm_ip} 'sudo systemctl restart {svc_name} && sudo systemctl status {svc_name}'")

    return parts


def _section_appendix_a_edges(graph) -> str:
    edge_types = {
        "SERVICE": "★ declared service dependency (service-contracts.yaml)",
        "DEPENDS_ON": "startup ordering or structural dependency",
        "STORAGE": "storage pool dependency",
        "NETWORK": "network infrastructure dependency",
        "BACKUP": "backup relationship",
    }
    rows = [[f"[{_e(k)}]", _e(v)] for k, v in edge_types.items()]
    legend = table(["Edge Type", "Meaning"], rows)

    edges = []
    for edge in (getattr(graph, "edges", None) or []):
        edge_type = getattr(edge, "edge_type", "?")
        marker    = "★" if edge_type == "SERVICE" else ""
        src_lbl   = getattr(edge.source, "label", str(edge.source))
        tgt_lbl   = getattr(edge.target, "label", str(edge.target))
        edges.append(f"{_e(src_lbl)} →[{_e(edge_type)}{marker}]→ {_e(tgt_lbl)}")

    body = h(3, "Edge Type Legend") + legend + divider()
    if edges:
        body += h(3, "Dependency Edges") + pre("\n".join(edges))
    else:
        body += p("(no dependency edges in manifest)")

    return section("Appendix A — Dependency Graph", body, open_=False)


def _section_appendix_d_secrets(manifest: dict) -> str:
    reg = manifest.get("secret_registry") or []
    if not reg:
        body = callout("warn", "No secret registry declared. Run setup-secrets.py to populate.")
        return section("Appendix D — Secret Registry", body, open_=False)

    rows = []
    for e in reg:
        rows.append([
            _e(e.get("id") or "?"),
            code(e.get("keepass_path") or "[no path]"),
            _e(", ".join(e.get("services") or e.get("used_by") or [])),
        ])
    body = table(["ID", "KeePass Path", "Used By"], rows)
    return section("Appendix D — Secret Registry", body, open_=False)


def _section_appendix_e_provenance(manifest: dict) -> str:
    records = manifest.get("provenance_records") or []
    if not records:
        return section("Appendix E — Deployment Provenance",
                       p("No provenance records declared."), open_=False)
    rows = []
    for r in records:
        rows.append([
            _e(str(r.get("vmid") or "?")),
            _e(r.get("vm_name") or "?"),
            code(r.get("tofu_workspace") or "—"),
            _e(r.get("ansible_role") or "—"),
            _e(r.get("source_commit") or "—"),
        ])
    body = table(["VMID", "VM Name", "IaC Workspace", "Ansible Role", "Commit"], rows)
    return section("Appendix E — Deployment Provenance", body, open_=False)


def _section_appendix_f_templates(manifest: dict) -> str:
    templates = manifest.get("templates") or []
    base_images = manifest.get("base_images") or []
    if not templates and not base_images:
        return section("Appendix F — Template Registry",
                       p("No templates declared."), open_=False)
    rows = []
    for t in base_images:
        rows.append([_e(t.get("name") or "?"), "base image",
                     _e(t.get("path") or "—"), _e(t.get("checksum") or "—")])
    for t in templates:
        rows.append([_e(t.get("name") or "?"), _e(t.get("type") or "template"),
                     _e(t.get("vmid") or "—"), _e(t.get("base_image") or "—")])
    body = table(["Name", "Type", "Path/VMID", "Details"], rows)
    return section("Appendix F — Template Registry", body, open_=False)


def _section_appendix_g_ext_deps(manifest: dict) -> str:
    deps = manifest.get("external_dependencies") or []
    if not deps:
        body = p("No external dependencies declared.")
        return section("Appendix G — External Dependencies", body, open_=False)

    parts = ""
    for dep in deps:
        name     = dep.get("name") or dep.get("id") or "?"
        dep_type = dep.get("type") or "?"
        endpoint = dep.get("endpoint") or "—"
        status   = dep.get("status") or "unknown"
        cert     = dep.get("certificate") or {}

        pairs = [
            ("ID",        dep.get("id") or "?"),
            ("Endpoint",  endpoint),
            ("Status",    status),
            ("Type",      dep_type),
            ("Required by", ", ".join(dep.get("required_by") or []) or "—"),
        ]
        parts += h(3, f"{_e(name)} ({_e(dep_type)})")
        parts += dl(pairs)

        if cert.get("expires_at"):
            days = dep.get("_days_remaining")
            if days is not None:
                if int(days) <= 7:
                    parts += callout("danger", f"TLS certificate expires in {days} days!")
                elif int(days) <= 30:
                    parts += callout("warn", f"TLS certificate expires in {days} days — action required.")
                else:
                    parts += callout("tip", f"TLS certificate expires in {days} days.")
            cert_pairs = [
                ("Expires",  cert.get("expires_at") or "?"),
                ("Issuer",   cert.get("issuer") or "?"),
                ("Auto-renew", "Yes" if cert.get("auto_renew") else "No"),
            ]
            parts += dl(cert_pairs)

    return section("Appendix G — External Dependencies", parts, open_=False)


def _section_appendix_i_os_migration(manifest: dict) -> str:
    migration_history = manifest.get("migration_history") or []
    if not migration_history:
        return ""

    parts = p(
        "Records all OS-variant migrations on cluster nodes (Ubuntu↔Talos). "
        "See <a href='../TALOS-ALTERNATIVE.md'>docs/TALOS-ALTERNATIVE.md</a> "
        "for the full procedure and rollback steps."
    )

    OUTCOME_CLASS = {
        "success":     "success",
        "rolled_back": "warning",
        "failed":      "danger",
        "aborted":     "warning",
    }

    for rec in migration_history:
        m_id      = _e(rec.get("migration_id") or "?")
        node_name = _e(rec.get("node_vm_name") or "?")
        from_v    = _e(rec.get("from_variant") or "?")
        to_v      = _e(rec.get("to_variant") or "?")
        started   = _e((rec.get("started_at") or "?")[:19])
        completed = _e((rec.get("completed_at") or "—")[:19])
        outcome   = rec.get("outcome") or "?"
        snap_vmid = rec.get("snapshot_vmid")
        dry_run   = rec.get("dry_run", False)
        error_msg = rec.get("error")

        oc = OUTCOME_CLASS.get(outcome, "")
        badge_cls = f"score-badge score-{oc.upper()}" if oc else "score-badge"
        outcome_badge = f'<span class="{badge_cls}">{_e(outcome.upper())}</span>'

        parts += h(3, f"{node_name}: {from_v} → {to_v}  {outcome_badge}")
        pairs = [
            ("Migration ID", m_id),
            ("Started",      started),
            ("Completed",    completed),
        ]
        if dry_run:
            pairs.append(("Mode", "DRY RUN — no changes were made"))
        if snap_vmid is not None:
            pairs.append(("Pre-migration snapshot VMID", _e(str(snap_vmid))))
        parts += dl(pairs)
        if error_msg:
            parts += callout("danger", f"Error: {_e(error_msg)}")

    # Rollback reference
    parts += h(3, "Manual Rollback Procedure")
    parts += p(
        "If automated rollback did not fire or needs to be re-run, restore "
        "the pre-migration snapshot VMID listed above:"
    )
    rollback_cmds = [
        "# Stop the current VM (if running)",
        "qm stop <CURRENT_VMID>",
        "",
        "# Roll back to the pre-migration snapshot",
        "qm rollback <SNAPSHOT_VMID> <SNAPSHOT_NAME>",
        "",
        "# Or re-run migration dry-run to verify plan:",
        "python3 proxmox-bootstrap/migrate-k3s-to-talos.py \\",
        "  --node <NODE_NAME> --dry-run",
    ]
    parts += commands_block(rollback_cmds)

    return section("Appendix I — OS Variant Migration History", parts, open_=False)


def _section_appendix_h_backup(manifest: dict) -> str:
    bc = manifest.get("backup_config") or {}
    if not bc:
        body = callout("danger", "No backup configuration declared. Run setup-backup.py.")
        return section("Appendix H — Backup Configuration", body, open_=False)

    parts = ""
    for layer_name, layer in (bc.get("layers") or {}).items():
        if not isinstance(layer, dict):
            continue
        parts += h(3, f"Layer: {_e(layer_name)}")
        dests = layer.get("destinations") or []
        if dests:
            rows = []
            for d in dests:
                rows.append([
                    _e(d.get("type") or "?"),
                    _e(d.get("rclone_remote") or d.get("path") or "—"),
                ])
            parts += table(["Type", "Destination"], rows)
        last_run = layer.get("last_successful_backup")
        if last_run:
            parts += p(f"Last successful backup: {_e(str(last_run))}")

    return section("Appendix H — Backup Configuration", parts, open_=False)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_recovery_runbook_html(
    manifest:        dict,
    graph,
    readiness,
    generation_meta: dict,
) -> str:
    """
    Build a self-contained HTML recovery runbook.

    Same signature as build_recovery_runbook() in recovery_runbook.py.
    Returns an HTML string (not bytes).
    """
    reset_checkbox_counter()

    hostname = _get(manifest, "host.hostname") or "unknown"
    cell_id  = manifest.get("cell_id") or "unknown"
    gen_at   = generation_meta.get("generated_at_display") or generation_meta.get("generated_at") or "?"
    coll_at  = manifest.get("collected_at") or "?"

    overall  = getattr(readiness, "overall_score", "?")
    ov_reason = getattr(readiness, "overall_score_reason", "")

    node_map = graph.node_map() if hasattr(graph, "node_map") else {}

    title = f"Recovery Runbook — {cell_id}"
    meta  = f"Host: {hostname}  |  Assessment: {coll_at}  |  Generated: {gen_at}"

    body = ""

    # Cover summary
    body += p(
        f"Overall Readiness: {score_badge(overall)}"
        + (f" — {_e(ov_reason)}" if ov_reason else "")
    )
    body += p(
        "This runbook is generated from observed infrastructure state. "
        "Commands are pre-populated from the assessment. "
        "Fields marked [HUMAN] require operator input at recovery time."
    )
    body += p("Methodology: Observe → Decide → Act → Record → Validate")

    # Restore sequence summary
    waves = getattr(graph, "restore_waves", [])
    total_mins = sum(getattr(w, "estimated_minutes", 0) or 0 for w in waves)
    body += p(f"Restore sequence: {len(waves)} wave(s), estimated {total_mins} minutes total.")

    body += divider()

    # Warnings
    body += _section_warnings(readiness, graph)

    # Readiness summary
    body += _section_readiness_summary(readiness)

    # Pre-recovery checklist
    body += _section_pre_recovery_checklist(manifest)

    # Wave 0: Network
    body += _section_wave0_network(manifest)

    # Restore waves
    for i, wave in enumerate(waves, 1):
        body += _section_restore_wave(wave, manifest, node_map, i)

    body += divider()

    # Appendices
    body += h(1, "Appendices")
    body += _section_appendix_a_edges(graph)
    body += _section_appendix_d_secrets(manifest)
    body += _section_appendix_e_provenance(manifest)
    body += _section_appendix_f_templates(manifest)
    body += _section_appendix_g_ext_deps(manifest)
    body += _section_appendix_h_backup(manifest)
    body += _section_appendix_i_os_migration(manifest)

    return html_page(title, body, doc_id=f"recovery-{cell_id}", meta=meta)
