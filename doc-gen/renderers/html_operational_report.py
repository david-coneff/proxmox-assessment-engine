#!/usr/bin/env python3
"""
html_operational_report.py — HTML operational report renderer.

Produces a self-contained HTML equivalent of the ODT operational report.
Checkbox behavior: checked → " done" italic, no strikethrough.

Public API:
  build_operational_report_html(manifest, readiness, generation_meta) → str

Stdlib only.
"""

from html import escape as _e
from html_base import (
    html_page, h, p, pre, code, dl, table, divider,
    callout, section, score_badge,
    checkbox_list, reset_checkbox_counter,
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


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_overall_readiness(readiness, generation_meta: dict) -> str:
    overall = getattr(readiness, "overall_score", "?")
    reason  = getattr(readiness, "overall_score_reason", "")

    parts = p(f"Overall Readiness: {score_badge(overall)}"
              + (f" — {_e(reason)}" if reason else ""))

    rows = []
    for c in getattr(readiness, "components", []):
        rows.append([score_badge(c.score), _e(c.component_id), _e(c.score_reason or "")])

    if rows:
        parts += table(["Score", "Component", "Reason"], rows)

    gen_at = (generation_meta.get("generated_at_display")
              or generation_meta.get("generated_at") or "?")
    parts += p(f"Report generated: {_e(gen_at)}")
    return section("Overall Readiness", parts, open_=True)


def _section_drift_summary(manifest: dict) -> str:
    drift = manifest.get("drift") or {}
    if not drift:
        return section("Drift Summary", p("No drift data available. Run Tier 2 collection."), open_=False)

    detected = drift.get("drift_detected", False)
    if not detected:
        body = p("No drift detected — current state matches last assessment snapshot.")
        return section("Drift Summary", body, open_=True)

    changes = drift.get("changed_fields") or []
    from_snap = drift.get("from_snapshot") or "?"
    to_snap   = drift.get("to_snapshot") or "?"

    body = callout("warn", f"Drift detected between {_e(from_snap)} and {_e(to_snap)}.")
    if changes:
        rows = []
        for c in changes[:30]:
            severity = c.get("severity") or "?"
            field    = c.get("field") or "?"
            old_val  = str(c.get("from") or "—")[:60]
            new_val  = str(c.get("to") or "—")[:60]
            rows.append([score_badge(severity), _e(field), _e(old_val), _e(new_val)])
        body += table(["Severity", "Field", "Was", "Now"], rows)
        if len(changes) > 30:
            body += p(f"… and {len(changes) - 30} more changes.")

    return section("Drift Summary", body, open_=True)


def _section_capacity(manifest: dict) -> str:
    cap = manifest.get("capacity_model") or {}
    observed = cap.get("observed") or {}
    thresholds = cap.get("thresholds") or {}
    trend = cap.get("trend") or {}

    if not observed:
        return section("Capacity", p("No capacity data. Run capacity_collector.py."), open_=False)

    pairs = []
    ram_pct = observed.get("ram_usage_pct")
    if ram_pct is not None:
        warn_pct = thresholds.get("ram_warn_pct", 80)
        crit_pct = thresholds.get("ram_crit_pct", 90)
        label = "RAM Usage"
        if float(ram_pct) >= crit_pct:
            label = f"⚠ {label} (CRITICAL)"
        elif float(ram_pct) >= warn_pct:
            label = f"▲ {label} (WARNING)"
        pairs.append((label, f"{ram_pct}% of {observed.get('total_ram_gb', '?')} GB"))

    stor_pct = observed.get("storage_usage_pct")
    if stor_pct is not None:
        warn_pct = thresholds.get("storage_warn_pct", 80)
        crit_pct = thresholds.get("storage_crit_pct", 90)
        label = "Storage Usage"
        if float(stor_pct) >= crit_pct:
            label = f"⚠ {label} (CRITICAL)"
        elif float(stor_pct) >= warn_pct:
            label = f"▲ {label} (WARNING)"
        pairs.append((label, f"{stor_pct}% of {observed.get('total_storage_gb', '?')} GB"))

    direction = trend.get("direction") or "stable"
    days_to_full = trend.get("days_to_full")
    if days_to_full:
        pairs.append(("Trend", f"{direction} — {days_to_full} days until full"))
    else:
        pairs.append(("Trend", direction))

    body = dl(pairs)
    return section("Capacity", body, open_=True)


def _section_service_health(manifest: dict) -> str:
    ss = manifest.get("service_state") or {}
    services = ss.get("services") or []
    if not services:
        return section("Service Health", p("No service state data. Run Tier 2 collection."), open_=False)

    running  = [s for s in services if s.get("status") == "running"]
    stopped  = [s for s in services if s.get("status") == "stopped"]
    degraded = [s for s in services if s.get("status") == "degraded"]

    rows = []
    for svc in services:
        status = svc.get("status") or "unknown"
        badge  = score_badge("GREEN" if status == "running" else
                             ("RED" if status == "stopped" else
                              ("ORANGE" if status == "degraded" else "BLOCKED")))
        rows.append([badge, _e(svc.get("name") or "?"), _e(svc.get("vm_name") or "?"),
                     _e(svc.get("version") or "—")])

    body = (
        p(f"Running: {len(running)}  |  Degraded: {len(degraded)}  |  Stopped: {len(stopped)}") +
        table(["Status", "Service", "VM", "Version"], rows)
    )
    return section("Service Health", body, open_=True)


def _section_secret_completeness(manifest: dict) -> str:
    reg = manifest.get("secret_registry") or []
    if not reg:
        body = callout("warn", "No secrets declared. Run setup-secrets.py.")
        return section("Secret Completeness", body, open_=False)

    total  = len(reg)
    with_path  = sum(1 for e in reg if e.get("keepass_path"))
    missing    = [e for e in reg if not e.get("keepass_path")]

    body = p(f"Total: {total}  |  With KeePass path: {with_path}  |  Missing: {len(missing)}")
    if missing:
        rows = [[_e(e.get("id") or "?"), _e(e.get("name") or "?")] for e in missing]
        body += callout("warn", f"{len(missing)} secret(s) missing KeePass path.")
        body += table(["ID", "Name"], rows)

    return section("Secret Completeness", body, open_=True)


def _section_external_dependencies(manifest: dict) -> str:
    deps = manifest.get("external_dependencies") or []
    if not deps:
        return section("External Dependencies", p("No external dependencies declared."), open_=False)

    rows = []
    for dep in deps:
        cert = dep.get("certificate") or {}
        days = dep.get("_days_remaining")
        cert_info = "—"
        if cert.get("expires_at"):
            cert_info = f"Expires: {cert.get('expires_at')}"
            if days is not None:
                cert_info += f" ({days}d)"
        rows.append([
            score_badge("GREEN" if dep.get("status") == "ok" else
                        ("RED" if days is not None and int(days) <= 7 else
                         ("ORANGE" if days is not None and int(days) <= 30 else "YELLOW")
                         if days is not None else "BLOCKED")),
            _e(dep.get("name") or "?"),
            _e(dep.get("type") or "?"),
            _e(dep.get("endpoint") or "—"),
            _e(cert_info),
        ])

    body = table(["Status", "Name", "Type", "Endpoint", "Certificate"], rows)
    return section("External Dependencies", body, open_=True)


def _section_remediation_summary(manifest: dict) -> str:
    proposals = manifest.get("remediations") or []
    if not proposals:
        return section("Remediation Summary", p("No remediation proposals in queue."), open_=False)

    pending  = [pr for pr in proposals if pr.get("status") == "proposed"]
    approved = [pr for pr in proposals if pr.get("status") == "approved"]
    executed = [pr for pr in proposals if pr.get("status") == "resolved"]
    failed   = [pr for pr in proposals if pr.get("status") == "failed"]
    resisted = [pr for pr in proposals if pr.get("resisted")]
    auto_exec= [pr for pr in executed if pr.get("approval_channel") == "auto-policy"]

    body = ""

    if pending or approved:
        body += h(3, "Pending Approval")
        _svmap = {"RED": 3, "ORANGE": 2, "YELLOW": 1}
        sev_counts: dict = {}
        for pr in pending:
            s = pr.get("severity", "YELLOW")
            sev_counts[s] = sev_counts.get(s, 0) + 1
        rows = [[score_badge(s), str(c)] for s, c in
                sorted(sev_counts.items(), key=lambda x: _svmap.get(x[0], 0), reverse=True)]
        if rows:
            body += table(["Severity", "Count"], rows)
        if approved:
            body += callout("warn", f"{len(approved)} proposals approved and ready to execute. "
                            "Run <code>remediation-cli.py</code> or start the executor.")

    recent = sorted(
        [pr for pr in proposals if pr.get("status") in ("resolved", "rejected", "failed")],
        key=lambda x: x.get("resolved_at") or x.get("proposed_at") or "",
        reverse=True,
    )[:20]
    if recent:
        body += h(3, "Recent Executions (last 30 days)")
        rows = []
        for pr in recent:
            ts = (pr.get("resolved_at") or "")[:16]
            out = (pr.get("outcome") or "")[:60]
            resisted_flag = " ⚠ resisted" if pr.get("resisted") else ""
            rows.append([
                score_badge(pr.get("severity", "?")),
                _e(pr.get("action_type", "")),
                _e(pr.get("target", "")),
                _e(pr.get("status", "")),
                _e(ts),
                _e(out + resisted_flag),
            ])
        body += table(["Severity", "Action", "Target", "Outcome", "Time", "Detail"], rows)

    if failed:
        body += callout("error",
                        f"{len(failed)} remediation(s) failed and require operator attention.")

    if resisted:
        body += callout("error",
                        f"{len(resisted)} remediation(s) executed but issue persisted after reassessment. "
                        "Escalated for manual review.")

    if auto_exec:
        body += h(3, "Autonomous Executions")
        body += p(f"{len(auto_exec)} proposals executed automatically via auto-policy.")
        auto_rows = [[_e(pr.get("action_type", "")), _e(pr.get("target", "")),
                      _e((pr.get("resolved_at") or "")[:16])] for pr in auto_exec[:10]]
        body += table(["Action", "Target", "Resolved At"], auto_rows)

    return section("Remediation Summary", body, open_=bool(pending or failed or resisted))


def _section_renewal_actions(manifest: dict) -> str:
    deps = manifest.get("external_dependencies") or []
    actions: list[str] = []

    for dep in deps:
        cert = dep.get("certificate") or {}
        days = dep.get("_days_remaining")
        if days is not None:
            name = dep.get("name") or dep.get("id") or "?"
            if int(days) <= 7:
                actions.append(f"URGENT: Renew {name} cert — expires in {days} days")
            elif int(days) <= 30:
                actions.append(f"ACTION: Renew {name} cert — expires in {days} days")
            elif int(days) <= 60:
                actions.append(f"PLAN: Schedule {name} cert renewal — {days} days remaining")

    # Drill reminder
    drill = (manifest.get("reconstruction_drills") or [{}])[0]
    if drill:
        last = drill.get("started_at")
        if last:
            actions.append(f"Last reconstruction drill: {last} — schedule next if > 90 days")
        else:
            actions.append("No reconstruction drill on record — schedule tabletop drill")

    if not actions:
        body = p("No time-sensitive actions required.")
        return section("Time-Sensitive Actions", body, open_=True)

    body = "".join(callout("warn", _e(a)) for a in actions)
    return section("⚠ Time-Sensitive Actions", body, open_=True)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_operational_report_html(
    manifest:        dict,
    readiness,
    generation_meta: dict,
) -> str:
    """
    Build a self-contained HTML operational report.

    Same signature as build_operational_report() in operational_report.py.
    Returns an HTML string.
    """
    reset_checkbox_counter()

    cell_id  = manifest.get("cell_id") or "unknown"
    hostname = _get(manifest, "host.hostname") or "unknown"
    gen_at   = (generation_meta.get("generated_at_display")
                or generation_meta.get("generated_at") or "?")

    title = f"Operational Report — {cell_id}"
    meta  = f"Host: {hostname}  |  Generated: {gen_at}"

    body = ""
    body += p("Hourly operational status report. Generated automatically by the assessment engine.")
    body += divider()

    body += _section_overall_readiness(readiness, generation_meta)
    body += _section_renewal_actions(manifest)
    body += _section_drift_summary(manifest)
    body += _section_capacity(manifest)
    body += _section_service_health(manifest)
    body += _section_secret_completeness(manifest)
    body += _section_external_dependencies(manifest)
    body += _section_remediation_summary(manifest)

    return html_page(title, body, doc_id=f"operational-{cell_id}", meta=meta)
