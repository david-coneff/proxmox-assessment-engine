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
        drift_details = nt.get("drift_details") or ""
        drift_msg = "⚠ Network topology drift detected — verify bridges match expected configuration."
        if drift_details:
            drift_msg += f" Details: {drift_details}"
        parts += callout("warn", _e(drift_msg))

    rows = []
    for b in bridges:
        rows.append([
            _e(b.get("name", "?")),
            _e(b.get("address") or b.get("ip") or "—"),
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
    wave_note  = getattr(wave, "note", "") or f"Wave {idx}"
    wave_label = f"Wave {idx} — {wave_note}"
    mins_hint  = f" (~{wave.estimated_minutes} min)" if getattr(wave, "estimated_minutes", None) else ""

    parts = ""
    for cid in (getattr(wave, "component_ids", None) or []):
        node = node_map.get(cid)
        if node:
            parts += _vm_restore_block(node, manifest, node_map)

    return section(wave_label + mins_hint, parts, open_=True)


def _vm_restore_block(node, manifest: dict, node_map: dict) -> str:
    metadata = getattr(node, "metadata", {}) or {}
    vmid_val = metadata.get("vmid") or metadata.get("ctid")
    vm_ip    = _resolve_vm_ip(vmid_val, manifest)
    vm_name  = getattr(node, "label", "?")

    parts = h(3, f"{_e(vm_name)} ({_e(vm_ip)})")

    # Provenance
    prov_reg = manifest.get("provenance_registry") or []
    prov = None
    if vmid_val is not None:
        for r in prov_reg:
            try:
                if int(r.get("vmid", -1)) == int(vmid_val):
                    prov = r
                    break
            except (TypeError, ValueError):
                pass
    if prov:
        pairs = []
        if prov.get("tofu_workspace"):
            pairs.append(("IaC workspace", prov["tofu_workspace"]))
        if prov.get("tofu_commit"):
            tc = prov["tofu_commit"]
            pairs.append(("OpenTofu commit", tc[:12] + "..." if len(tc) > 12 else tc))
        if prov.get("template_name"):
            pairs.append(("Template", prov["template_name"]))
        if prov.get("deployed_at"):
            pairs.append(("Deployed at", prov["deployed_at"]))
        if pairs:
            parts += dl(pairs)
    else:
        parts += callout("warn", "NOT RECORDED — no provenance record found for this VM")

    # Restore commands
    vmid = vmid_val
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
    """
    Return the service contract for the given VM name, or None.
    Handles node labels like "forgejo (VM 101)" by also matching the bare name.
    """
    import re as _re
    bare = _re.sub(r'\s*\(VM\s+\d+\)\s*$', '', vm_name).strip()
    for sc in (manifest.get("service_contracts") or []):
        vm_field = sc.get("vm") or sc.get("vm_name") or sc.get("service") or ""
        if vm_field == vm_name or vm_field == bare:
            return sc
    return None


def _health_check_cmds(iface: dict, vm_ip: str) -> list[str]:
    """
    Generate executable health-check commands from a provided_interface entry.
    Returns a list of command strings (empty if no meaningful check can be derived).
    SSH interfaces are skipped — reachability is validated in the standard block.
    """
    protocol     = (iface.get("protocol") or "").lower()
    port         = iface.get("port")
    health_check = iface.get("health_check")
    url_pattern  = iface.get("url_pattern")
    host         = vm_ip if vm_ip != "[VM_IP]" else "HOST"

    if protocol == "ssh":
        return []

    if protocol == "postgresql":
        return [
            f"pg_isready -h {host} -p {port or 5432}",
            "# Expected: accepting connections",
        ]

    if protocol in ("smtp", "smtps"):
        return [
            f"nc -z -w 5 {host} {port or 25}",
            "# Expected: connection established (exit 0)",
        ]

    if health_check and health_check.upper().startswith("GET "):
        path = health_check[4:].strip()
        if url_pattern:
            url = url_pattern.rstrip("/") + path
        else:
            scheme = "https" if protocol == "https" else "http"
            url = f"{scheme}://{host}:{port}{path}"
        return [
            f"curl -sf --max-time 10 '{url}'",
            "# Expected: HTTP 2xx (exit 0)",
        ]

    if port and vm_ip != "[VM_IP]":
        return [
            f"nc -z -w 5 {vm_ip} {port}",
            f"# Expected: {protocol}:{port} reachable (exit 0)",
        ]

    return []


def _service_restart_cmds(contract: dict, vm_ip: str) -> list[str]:
    """
    Generate service restart and status commands. Assumes Ubuntu VM with systemd.
    """
    svc = contract.get("service", "unknown")
    if vm_ip == "[VM_IP]":
        prefix = f"ssh ubuntu@[VM_IP_{svc.upper().replace('-','_')}]"
    else:
        prefix = f"ssh ubuntu@{vm_ip}"
    return [
        f"# Restart and verify service: {svc}",
        f"{prefix} 'sudo systemctl restart {svc}'",
        f"{prefix} 'sudo systemctl status --no-pager {svc}'",
        "# Expected: Active: active (running)",
    ]


def _service_contract_block(contract: dict, vm_ip: str) -> str:
    svc = contract.get("service") or contract.get("service_name") or "?"
    parts = h(4, f"Service Contract: {_e(svc)}")

    provided = contract.get("provided_interfaces") or []
    if provided:
        all_cmds: list[str] = []
        for iface in provided:
            all_cmds.extend(_health_check_cmds(iface, vm_ip))
        if all_cmds:
            parts += p("Health check commands:")
            parts += pre("\n".join(all_cmds))

    # Required interfaces
    required = contract.get("required_interfaces") or []
    if required:
        rows = []
        for req in required:
            crit = "CRITICAL" if req.get("critical") else "optional"
            rows.append([
                _e(req.get("service", "?")),
                _e(req.get("protocol", "?")),
                _e(str(req.get("port", ""))),
                _e(crit),
            ])
        parts += p("Required interfaces:")
        parts += table(["Service", "Protocol", "Port", "Criticality"], rows)

    # Startup ordering
    startup = contract.get("startup_after") or []
    if startup:
        parts += p(f"Start after: {_e(', '.join(startup))}")

    # Secret references
    secrets = contract.get("secret_references") or []
    if secrets:
        parts += p("Secret references: " + _e(", ".join(secrets)))

    # Restart commands
    restart_cmds = _service_restart_cmds(contract, vm_ip)
    if restart_cmds:
        parts += p("Restart commands:")
        parts += pre("\n".join(restart_cmds))

    # Checkboxes
    parts += checkbox_list([
        f"All required interfaces ({len(required)}) verified reachable",
        "Service running and healthy after restart",
    ] + [f"Health check passed: {_e(iface.get('protocol','?'))}:{iface.get('port','?')}"
         for iface in provided if _health_check_cmds(iface, vm_ip)])

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
    node_map = graph.node_map() if hasattr(graph, "node_map") else {}
    for edge in (getattr(graph, "edges", None) or []):
        # Edge uses from_id/to_id/type (not source/target/edge_type)
        edge_type = getattr(edge, "type", getattr(edge, "edge_type", "?"))
        marker    = "★" if edge_type == "SERVICE" else ""
        from_id   = getattr(edge, "from_id", getattr(edge, "source", "?"))
        to_id     = getattr(edge, "to_id",   getattr(edge, "target",  "?"))
        src_node  = node_map.get(str(from_id))
        tgt_node  = node_map.get(str(to_id))
        src_lbl   = src_node.label if src_node else str(from_id)
        tgt_lbl   = tgt_node.label if tgt_node else str(to_id)
        edges.append(f"{_e(src_lbl)} →[{_e(edge_type)}{marker}]→ {_e(tgt_lbl)}")

    body = h(3, "Edge Type Legend") + legend + divider()
    if edges:
        body += h(3, "Dependency Edges") + pre("\n".join(edges))
    else:
        body += p("(no dependency edges in manifest)")

    return section("Appendix A — Dependency Graph", body, open_=False)


def _section_appendix_c_dns(manifest: dict) -> str:
    reg = manifest.get("dns_registry") or []
    if not reg:
        body = p("No DNS registry declared. Add entries to dns-registry.yaml.")
        return section("Appendix C — DNS Registry", body, open_=False)
    rows = []
    for e in reg:
        rows.append([
            _e(e.get("hostname") or "?"),
            _e(e.get("ip") or e.get("address") or "?"),
            _e(str(e.get("vmid") or "—")),
            _e(e.get("role") or "—"),
        ])
    body = table(["Hostname", "IP Address", "VMID", "Role"], rows)
    return section("Appendix C — DNS Registry", body, open_=False)


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
        if dep.get("failover"):
            pairs.append(("Failover", dep["failover"]))
        if dep.get("notes"):
            pairs.append(("Notes", dep["notes"]))
        parts += h(3, f"{_e(name)} ({_e(dep_type)})")
        parts += dl(pairs)

        if cert.get("expires_at"):
            parts += h(4, "TLS Certificate")
            days = dep.get("_days_remaining")
            if days is None:
                try:
                    from datetime import datetime, timezone as _tz
                    exp = datetime.fromisoformat(
                        cert["expires_at"].replace("Z", "+00:00"))
                    days = (exp - datetime.now(_tz.utc)).days
                except Exception:
                    pass
            if days is not None:
                if int(days) <= 7:
                    parts += callout("danger", f"EXPIRES IN {days} days — immediate renewal required!")
                elif int(days) <= 30:
                    parts += callout("warn", f"TLS certificate expires in {days} days — action required.")
                else:
                    parts += callout("tip", f"TLS certificate expires in {days} days.")
            cert_pairs = [
                ("Expires at", cert.get("expires_at") or "?"),
                ("Issuer",     cert.get("issuer") or "?"),
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
        body = callout("danger",
                       "No backup configuration declared. Run setup-backup.py "
                       "to configure KeePass DB, configuration state, and application data backups.")
        return section("Appendix H — Backup Configuration", body, open_=False)

    LAYER_LABELS = {
        "secrets": "Secrets (KeePass database)",
        "config":  "Configuration state",
        "appdata": "Application data volumes",
    }

    parts = p(
        "Backup is managed by restic (config/appdata layers) and rclone "
        "(secrets / KeePass layer). All restic repos use per-backup unique "
        "encryption keys stored in KeePass."
    )

    for layer_name, layer in (bc.get("layers") or {}).items():
        if not isinstance(layer, dict):
            continue
        label = LAYER_LABELS.get(layer_name, layer_name)
        enabled = layer.get("enabled", True)
        heading = f"{label} [DISABLED]" if not enabled else label
        parts += h(3, _e(heading))

        if not enabled:
            continue

        consec = layer.get("consecutive_all_fail_count", 0)
        if consec >= 2:
            parts += callout("danger",
                             f"ALL DESTINATIONS FAILED on {consec} consecutive runs — backup chain broken")
        elif consec == 1:
            parts += callout("warn",
                             "All destinations failed on last run — investigate before next run")

        last_ok = layer.get("last_backup_at") or layer.get("last_successful_backup")
        parts += dl([
            ("Last successful backup", _e(last_ok or "NEVER")),
            ("Consecutive all-fail count", str(consec)),
        ])

        dests = layer.get("destinations") or []
        if dests:
            rows = []
            for d in dests:
                dest_id = d.get("id") or d.get("rclone_remote") or d.get("path") or "?"
                dest_type = d.get("type") or "?"
                rows.append([_e(dest_type), _e(dest_id)])
            parts += table(["Type", "Destination ID"], rows)

    # Restore commands
    parts += h(3, "Restore Commands")
    parts += pre("\n".join([
        "# List available snapshot sets:",
        "python3 proxmox-bootstrap/restore-from-backup.py \\",
        "  --state proxmox-bootstrap/bootstrap-state.json --list",
        "",
        "# Restore config state (latest):",
        "python3 proxmox-bootstrap/restore-from-backup.py \\",
        "  --state proxmox-bootstrap/bootstrap-state.json \\",
        "  --layer config --latest --target /tmp/restore",
    ]))

    # KeePass backup note
    secrets_cfg  = (bc.get("layers") or {}).get("secrets") or {}
    secrets_dests = secrets_cfg.get("destinations") or []
    parts += h(3, "KeePass Database Backup")
    parts += p(
        "The KeePass database is backed up as a plain rclone file copy "
        f"(already AES-256 encrypted — no restic layer). "
        f"{len(secrets_dests)} destination(s) configured."
    )
    parts += p(
        "To retrieve: use the rclone credentials from forge-manifest.json "
        "(stored in the spawn/phoenix package, not in KeePass)."
    )

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
    body += _section_appendix_c_dns(manifest)
    body += _section_appendix_d_secrets(manifest)
    body += _section_appendix_e_provenance(manifest)
    body += _section_appendix_f_templates(manifest)
    body += _section_appendix_g_ext_deps(manifest)
    body += _section_appendix_h_backup(manifest)
    body += _section_appendix_i_os_migration(manifest)

    return html_page(title, body, doc_id=f"recovery-{cell_id}", meta=meta)
