#!/usr/bin/env python3
"""
operational_report.py — Operational Status Report renderer (Phase 10).

Generates a living operational status document from current assessment state.
Unlike the recovery runbook (how to fix things) or bootstrap workbook (how to
build things), the operational report answers: "how is the system doing right now?"

Sections:
  1. Overall Readiness     — score, component counts, registry gaps
  2. Drift Summary         — field-level changes since last assessment
  3. Current Capacity      — CPU, RAM, storage utilization
  4. Service Health        — running services, up/down status
  5. Secret Completeness   — secret registry, missing KeePass paths
  6. External Dependencies — reachability, certificate expiry
  7. Renewal Actions       — time-sensitive items requiring operator attention

Generated as an ODT document via RunbookBuilder.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from runbook import RunbookBuilder
from timestamps import format_doc_timestamp_from_iso

SCORE_SYMBOLS = {
    "GREEN":   "✓ GREEN",
    "YELLOW":  "⚠ YELLOW",
    "ORANGE":  "⚠ ORANGE",
    "RED":     "✗ RED",
    "BLOCKED": "⛔ BLOCKED",
    "UNKNOWN": "? UNKNOWN",
}

CERT_WARN_DAYS = 60   # YELLOW
CERT_CRIT_DAYS = 30   # ORANGE


def _get(manifest: dict, path: str, default=None):
    parts = path.split(".")
    obj = manifest
    for p in parts:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(p, default)
    return obj


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_overall_readiness(rb: RunbookBuilder, readiness, generation_meta: dict):
    """Section 1 — Overall Readiness."""
    rb.h1("1. Overall Readiness")
    generated = format_doc_timestamp_from_iso(generation_meta.get("generated_at", ""))
    rb.body(f"Report generated: {generated}")
    rb.spacer()

    score_sym = SCORE_SYMBOLS.get(readiness.overall_score, "?")
    rb.field("Overall Score", score_sym,
             "AUTO" if readiness.overall_score == "GREEN" else "UNRESOLVED",
             readiness.overall_score_reason)

    # Component score distribution
    from collections import Counter
    sc = Counter(c.score for c in readiness.components)
    rb.body(f"Components: {len(readiness.components)} total")
    for label in ("GREEN", "YELLOW", "ORANGE", "RED", "BLOCKED"):
        n = sc.get(label, 0)
        if n:
            rb.body(f"  {SCORE_SYMBOLS[label]}: {n}")

    # Registry gaps summary
    reg_gaps = getattr(readiness, "registry_gaps", [])
    if reg_gaps:
        rb.spacer()
        rb.body(f"Infrastructure gaps: {len(reg_gaps)}")
        for gap in reg_gaps:
            sym = SCORE_SYMBOLS.get(gap.severity, gap.severity)
            rb.body(f"  {sym}  {gap.component_id} — {gap.description[:100]}")
    else:
        rb.body("Infrastructure gaps: none")
    rb.spacer()


def _section_drift_summary(rb: RunbookBuilder, manifest: dict):
    """Section 2 — Drift Summary."""
    rb.h1("2. Drift Summary")

    drift = manifest.get("drift")
    if not drift:
        rb.body("No drift data available — compare against a previous assessment snapshot to detect changes.")
        rb.body("Run: python3 doc-gen/engine.py --mode operational --manifest <path>")
        rb.spacer()
        return

    from_snap = drift.get("from_snapshot", "?")
    to_snap   = drift.get("to_snapshot", "?")
    severity  = drift.get("drift_severity", "none")
    diffs     = drift.get("diffs") or []

    rb.field("Compared", f"{from_snap}  →  {to_snap}", "AUTO", "")
    rb.field("Drift severity", severity.upper(), "AUTO", "")
    rb.field("Changed fields", str(len(diffs)), "AUTO", "")
    rb.spacer()

    if not diffs:
        rb.body("✓ No field changes detected since last assessment.")
    else:
        for d in diffs[:30]:
            path  = d.get("path", "?")
            from_ = str(d.get("from_value", ""))[:60]
            to_   = str(d.get("to_value", ""))[:60]
            sev   = d.get("severity", "").upper()
            rb.body(f"  [{sev}]  {path}")
            rb.body(f"         {from_!r}  →  {to_!r}")
        if len(diffs) > 30:
            rb.note(f"... and {len(diffs) - 30} more changed fields (see Restore-Sequence.md)")
    rb.spacer()


def _section_capacity(rb: RunbookBuilder, manifest: dict):
    """Section 3 — Current Capacity."""
    rb.h1("3. Current Capacity")

    hostname = _get(manifest, "host.hostname", "unknown")
    cpu_threads = _get(manifest, "cpu.total_threads")
    cpu_model   = _get(manifest, "cpu.model", "(unknown)")
    mem_total   = _get(manifest, "memory.total_gb")
    mem_avail   = _get(manifest, "memory.available_gb")

    rb.h2("Compute")
    if cpu_model:
        rb.field("CPU", cpu_model, "AUTO", "")
    if cpu_threads:
        rb.field("Logical CPUs", str(cpu_threads), "AUTO", "")
    if mem_total is not None:
        mem_used = (mem_total - mem_avail) if mem_avail is not None else None
        mem_str  = f"{mem_total} GB total"
        if mem_used is not None:
            pct = int(mem_used / mem_total * 100) if mem_total else 0
            mem_str += f"  |  {mem_used:.1f} GB used ({pct}%)  |  {mem_avail:.1f} GB free"
            if pct >= 90:
                rb.warning(f"RAM usage critical: {pct}% — consider adding capacity")
            elif pct >= 75:
                rb.note(f"RAM usage elevated: {pct}%")
        rb.field("RAM", mem_str, "AUTO", "")

    rb.h2("Storage")
    block_devs = _get(manifest, "storage.block_devices") or []
    zfs_pools  = _get(manifest, "storage.zfs_pools") or []
    if zfs_pools:
        for pool in zfs_pools:
            name     = pool.get("name", "?")
            state    = pool.get("state", "?")
            free_gb  = pool.get("free_gb")
            total_gb = pool.get("size_gb")
            pool_str = f"state={state}"
            if total_gb and free_gb is not None:
                used_gb = total_gb - free_gb
                pct     = int(used_gb / total_gb * 100) if total_gb else 0
                pool_str += f"  {used_gb:.0f}/{total_gb:.0f} GB used ({pct}%)"
                if pct >= 90:
                    rb.warning(f"Pool '{name}' storage critical: {pct}% full")
                elif pct >= 80:
                    rb.note(f"Pool '{name}' storage elevated: {pct}%")
            rb.field(f"ZFS pool: {name}", pool_str,
                     "AUTO" if state == "ONLINE" else "UNRESOLVED", "")
    elif block_devs:
        for dev in block_devs:
            rb.body(f"  {dev.get('name','?')}: {dev.get('size_gb','?')} GB  {dev.get('model','')}")
    else:
        rb.body("No storage data available — run Tier 2 assessment")

    # VMs
    vms = _get(manifest, "vms") or []
    if vms:
        rb.h2("VMs")
        running = sum(1 for v in vms if v.get("status") == "running")
        rb.field("VMs", f"{len(vms)} total  |  {running} running", "AUTO", "")
    rb.spacer()


def _section_service_health(rb: RunbookBuilder, manifest: dict):
    """Section 4 — Service Health."""
    rb.h1("4. Service Health")

    service_state = manifest.get("service_state") or {}
    services      = service_state.get("services") or []

    if not services:
        contracts = manifest.get("service_contracts") or []
        if contracts:
            rb.body(f"{len(contracts)} service contract(s) declared, but no observed service state.")
            rb.body("Run Tier 2 collection to populate service health data.")
            rb.body("  python3 proxmox-bootstrap/collect-tier2.py --state proxmox-bootstrap/bootstrap-state.json")
        else:
            rb.body("No service contracts or observed service state available.")
        rb.spacer()
        return

    running   = [s for s in services if s.get("status") == "running"]
    stopped   = [s for s in services if s.get("status") == "stopped"]
    degraded  = [s for s in services if s.get("status") == "degraded"]
    unknown   = [s for s in services if s.get("status") not in ("running", "stopped", "degraded")]

    rb.field("Services", f"{len(services)} total", "AUTO", "")
    rb.field("Running",  str(len(running)),  "AUTO", "")
    if stopped:
        rb.field("Stopped",  str(len(stopped)),  "UNRESOLVED", "")
    if degraded:
        rb.field("Degraded", str(len(degraded)), "UNRESOLVED", "")
    rb.spacer()

    for svc in services:
        name   = svc.get("name", "?")
        vm     = svc.get("vm", "?")
        vmid   = svc.get("vmid", "?")
        status = svc.get("status", "unknown")
        url    = svc.get("url") or svc.get("health_check_url") or ""
        sym    = "✓" if status == "running" else ("⚠" if status == "degraded" else "✗")
        rb.body(f"  {sym} {name:<30} vm={vm} (vmid={vmid})  {status}")
        if url:
            rb.body(f"    Health: {url}")
    rb.spacer()


def _section_secret_completeness(rb: RunbookBuilder, manifest: dict):
    """Section 5 — Secret Registry Completeness."""
    rb.h1("5. Secret Registry Completeness")

    secrets = (manifest.get("secret_registry") or
               _get(manifest, "secrets") or [])

    if not secrets:
        rb.body("No secret registry available — run proxmox-bootstrap/setup-secrets.py")
        rb.spacer()
        return

    total     = len(secrets)
    with_path = sum(1 for s in secrets if s.get("keepass_path"))
    missing   = [s for s in secrets if not s.get("keepass_path")]

    rb.field("Secrets declared", str(total), "AUTO", "")
    rb.field("With KeePass path", f"{with_path}/{total}", "AUTO", "")
    if missing:
        rb.field("Missing KeePass path", str(len(missing)), "UNRESOLVED",
                 "These secrets will show as [KEEPASS_PATH] in recovery runbook")
        for s in missing:
            rb.body(f"  ✗ {s.get('id','?')}  ({s.get('secret_type','?')})")
    else:
        rb.body("✓ All secrets have KeePass paths recorded.")
    rb.spacer()


def _section_external_dependencies(rb: RunbookBuilder, manifest: dict):
    """Section 6 — External Dependencies."""
    rb.h1("6. External Dependencies")

    from datetime import datetime, timezone
    now      = datetime.now(timezone.utc)
    ext_deps = manifest.get("external_dependencies") or []

    if not ext_deps:
        rb.body("No external dependencies declared. Add external_dependencies to bootstrap-state.json.")
        rb.spacer()
        return

    rb.body(f"{len(ext_deps)} external service(s) declared")
    rb.spacer()

    for dep in ext_deps:
        dep_id   = dep.get("id", "?")
        dep_name = dep.get("name", dep_id)
        status   = dep.get("status", "unknown")
        sym      = "✓" if status == "reachable" else ("⚠" if status == "degraded" else "✗")
        cert     = dep.get("certificate")

        line = f"  {sym} {dep_name:<35} {status}"
        if cert and cert.get("expires_at"):
            try:
                exp_dt = datetime.fromisoformat(cert["expires_at"].replace("Z", "+00:00"))
                days   = (exp_dt - now).days
                if days <= 7:
                    line += f"  ✗ CERT EXPIRES IN {days}d"
                elif days <= 30:
                    line += f"  ⚠ cert expires in {days}d"
                elif days <= 60:
                    line += f"  ℹ cert expires in {days}d"
                else:
                    line += f"  ✓ cert valid {days}d"
            except (ValueError, TypeError):
                pass
        rb.body(line)
    rb.spacer()


def _section_renewal_actions(rb: RunbookBuilder, manifest: dict):
    """Section 7 — Time-sensitive actions requiring operator attention."""
    rb.h1("7. Actions Required")

    from datetime import datetime, timezone
    now       = datetime.now(timezone.utc)
    ext_deps  = manifest.get("external_dependencies") or []
    actions   = []

    # Certificate expiry actions
    for dep in ext_deps:
        cert = dep.get("certificate")
        if not cert:
            continue
        try:
            exp_dt = datetime.fromisoformat(cert["expires_at"].replace("Z", "+00:00"))
            days   = (exp_dt - now).days
            if days <= 7:
                actions.append(("RED",    f"URGENT: Renew TLS cert for '{dep.get('name','?')}' — expires in {days} day(s)"))
            elif days <= 30:
                actions.append(("ORANGE", f"Renew TLS cert for '{dep.get('name','?')}' — expires in {days} day(s)"))
            elif days <= 60:
                actions.append(("YELLOW", f"Schedule TLS cert renewal for '{dep.get('name','?')}' — expires in {days} day(s)"))
        except (ValueError, TypeError):
            pass

    # Stopped services
    service_state = manifest.get("service_state") or {}
    for svc in (service_state.get("services") or []):
        if svc.get("status") in ("stopped", "degraded"):
            name = svc.get("name", "?")
            actions.append(("RED", f"Service '{name}' is {svc['status']} — investigate immediately"))

    # Backup all-fail
    bc = manifest.get("backup_config") or {}
    for layer_name, layer in (bc.get("layers") or {}).items():
        if layer.get("consecutive_all_fail_count", 0) >= 2:
            actions.append(("RED", f"Backup layer '{layer_name}': all destinations failed on {layer['consecutive_all_fail_count']} consecutive runs"))
        elif layer.get("consecutive_all_fail_count", 0) == 1:
            actions.append(("ORANGE", f"Backup layer '{layer_name}': all destinations failed on last run"))

    if not actions:
        rb.body("✓ No time-sensitive actions required.")
    else:
        for severity, msg in sorted(actions, key=lambda x: {"RED": 0, "ORANGE": 1, "YELLOW": 2}.get(x[0], 3)):
            sym = {"RED": "✗", "ORANGE": "⚠", "YELLOW": "ℹ"}.get(severity, "·")
            rb.body(f"  {sym} [{severity}] {msg}")
    rb.spacer()

    # Scheduled refresh note
    rb.h2("Scheduled Refresh")
    rb.body("This report is generated on-demand. To automate generation:")
    rb.code("# Add to crontab (regenerate every hour):")
    rb.code("0 * * * * python3 /opt/broodforge/doc-gen/engine.py \\")
    rb.code("  --mode operational \\")
    rb.code("  --manifest /opt/broodforge/proxmox-bootstrap/bootstrap-state.json \\")
    rb.code("  2>&1 | tee -a /var/log/broodforge-operational.log")
    rb.spacer()
    rb.note("For systemd timer setup, run: proxmox-bootstrap/setup-operational-schedule.sh")


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_operational_report(
    manifest: dict,
    readiness,
    generation_meta: dict,
) -> bytes:
    """
    Build the operational status report as an ODT document.

    Args:
        manifest:        bootstrap manifest with all registries injected
        readiness:       ReadinessReport from score_graph()
        generation_meta: dict with generated_at, collected_at, tier

    Returns:
        ODT bytes
    """
    rb = RunbookBuilder()
    hostname  = _get(manifest, "host.hostname", "unknown")
    pve_ver   = _get(manifest, "host.proxmox_version", "unknown")
    collected = manifest.get("collected_at", "unknown")
    gen_iso   = generation_meta.get("generated_at", "")
    generated = format_doc_timestamp_from_iso(gen_iso) if gen_iso else generation_meta.get("generated_at_display", "unknown")

    # Cover
    rb.h1("Operational Status Report")
    rb.body(f"Host: {hostname}  |  Proxmox {pve_ver}  |  Assessment: {collected}")
    rb.body(f"Generated: {generated}")
    rb.body(
        "This report shows the current operational state of the cell. "
        "For recovery procedures see Recovery-Runbook.odt. "
        "For bootstrap procedures see Bootstrap-Workbook.ods."
    )
    rb.spacer()
    rb.body(f"Overall: {SCORE_SYMBOLS.get(readiness.overall_score, '?')}  — {readiness.overall_score_reason}")
    rb.spacer()

    _section_overall_readiness(rb, readiness, generation_meta)
    _section_drift_summary(rb, manifest)
    _section_capacity(rb, manifest)
    _section_service_health(rb, manifest)
    _section_secret_completeness(rb, manifest)
    _section_external_dependencies(rb, manifest)
    _section_renewal_actions(rb, manifest)

    return rb.build_odt()
