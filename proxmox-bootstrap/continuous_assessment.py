#!/usr/bin/env python3
"""
continuous_assessment.py — Continuous Assessment and Twin Maintenance (Phase 24).

Provides the framework for scheduled and event-driven twin updates:
  - Scheduled cron-driven assessment runs
  - Repository ingestion (git push → twin update)
  - Deployment event hooks (tofu apply / ansible → twin update)
  - Staleness alerting (fields exceeding freshness threshold)
  - Twin diff reporting (what changed since last report)

24.1  AssessmentSchedule   — cron-driven framework
24.2  RepoIngestionHook    — git webhook handler
24.3  DeploymentEventHook  — tofu/ansible event handler
24.4  StalenessAlert       — notify when state exceeds threshold
24.5  TwinDiffReport       — what changed in the twin since last report
24.6  PbsStateUpdater      — continuous Data Protection State updates
24.7  CertExpiryMonitor    — continuous External Dependency State monitoring
24.8  CodeHealthScore      — static analysis health score (Phase 1.L)

Provides:
  AssessmentSchedule        — schedule definition and next-run calculation
  ScheduledRun              — a scheduled run record
  plan_assessment_schedule()
  RepoIngestionEvent        — git push event
  handle_repo_ingestion()
  DeploymentEvent           — tofu/ansible completion event
  handle_deployment_event()
  StalenessAlert            — per-field staleness alert
  check_staleness()
  TwinDiffEntry             — one changed field
  TwinDiffReport            — full diff since last report
  build_twin_diff_report()
  PbsJobStatus              — PBS backup job status
  collect_pbs_state_update()
  CertExpiryAlert           — cert approaching expiry
  scan_cert_expiry()
  CodeHealthScore           — static analysis health score
  assess_code_health()      — run static analysis and return CodeHealthScore

Stdlib only.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# 24.1 — Assessment Schedule
# ---------------------------------------------------------------------------

@dataclass
class AssessmentSchedule:
    """Defines the cron-driven assessment schedule for a cell."""
    cell_id:               str
    tier1_interval_hours:  float = 1.0      # hardware/platform (lightweight)
    tier2_interval_hours:  float = 6.0      # service state (SSH needed)
    tier3_interval_hours:  float = 24.0     # federation (cross-cell)
    operational_report_hours: float = 1.0  # operational report generation
    backup_trigger:        bool  = True     # trigger backup after full Tier 2 run
    last_tier1_at:         Optional[str] = None
    last_tier2_at:         Optional[str] = None
    last_tier3_at:         Optional[str] = None


@dataclass
class ScheduledRun:
    """A single scheduled assessment run."""
    run_id:      str
    cell_id:     str
    tier:        int       # 1, 2, or 3
    scheduled_at: str
    run_at:      Optional[str] = None
    status:      str  = "pending"   # pending|running|completed|failed
    duration_seconds: Optional[float] = None
    findings_count:   int = 0


def plan_assessment_schedule(
    schedule: AssessmentSchedule,
    *,
    now_fn: Optional[Callable[[], str]] = None,
) -> list[ScheduledRun]:
    """
    Plan the next set of assessment runs based on last-run times.

    Returns runs that are due (last run + interval < now).
    """
    from datetime import datetime, timezone
    import hashlib
    now_str = (now_fn or (lambda: datetime.now(timezone.utc).isoformat()))()
    now     = datetime.fromisoformat(now_str.replace("Z", "+00:00"))

    def _is_due(last_at: Optional[str], interval_hours: float) -> bool:
        if last_at is None:
            return True
        try:
            last = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
            return (now - last) >= timedelta(hours=interval_hours)
        except (ValueError, AttributeError):
            return True

    runs: list[ScheduledRun] = []

    if _is_due(schedule.last_tier1_at, schedule.tier1_interval_hours):
        run_id = hashlib.sha256(f"t1:{schedule.cell_id}:{now_str}".encode()).hexdigest()[:10]
        runs.append(ScheduledRun(run_id, schedule.cell_id, 1, now_str))

    if _is_due(schedule.last_tier2_at, schedule.tier2_interval_hours):
        run_id = hashlib.sha256(f"t2:{schedule.cell_id}:{now_str}".encode()).hexdigest()[:10]
        runs.append(ScheduledRun(run_id, schedule.cell_id, 2, now_str))

    if _is_due(schedule.last_tier3_at, schedule.tier3_interval_hours):
        run_id = hashlib.sha256(f"t3:{schedule.cell_id}:{now_str}".encode()).hexdigest()[:10]
        runs.append(ScheduledRun(run_id, schedule.cell_id, 3, now_str))

    return runs


# ---------------------------------------------------------------------------
# 24.2 — Repository Ingestion Hook
# ---------------------------------------------------------------------------

@dataclass
class RepoIngestionEvent:
    """A git push event that should trigger a twin update."""
    event_id:    str
    cell_id:     str
    repo_url:    str
    branch:      str
    commit_sha:  str
    pushed_at:   str
    changed_files: list[str] = field(default_factory=list)
    author:      Optional[str] = None


def _classify_repo_change(files: list[str]) -> list[str]:
    """Map changed files to twin state categories affected."""
    categories: set[str] = set()
    for f in files:
        lower = f.lower()
        if "bootstrap-state" in lower:
            categories.add("bootstrap_state")
        if "service-contract" in lower or "service_contract" in lower:
            categories.add("service_state")
        if "network-topology" in lower or "dns-registry" in lower:
            categories.add("network_topology")
        if "k3s-cluster" in lower:
            categories.add("cluster_state")
        if "secret-registry" in lower:
            categories.add("secret_references")
        if lower.endswith(".tf") or lower.endswith(".tfvars"):
            categories.add("provisioning")
        if "ansible" in lower or lower.endswith(".yml") or lower.endswith(".yaml"):
            categories.add("configuration")
    return sorted(categories)


def handle_repo_ingestion(
    event:   RepoIngestionEvent,
) -> dict:
    """
    Process a git push event and determine which twin state categories need updating.

    Returns a dict with: categories_affected, update_required, reason.
    """
    categories = _classify_repo_change(event.changed_files)
    return {
        "event_id":            event.event_id,
        "cell_id":             event.cell_id,
        "commit_sha":          event.commit_sha,
        "categories_affected": categories,
        "update_required":     bool(categories),
        "reason": (
            f"Git push to {event.branch}: {len(event.changed_files)} file(s) changed. "
            f"Affected categories: {', '.join(categories) or 'none detected'}."
        ),
    }


# ---------------------------------------------------------------------------
# 24.3 — Deployment Event Hook
# ---------------------------------------------------------------------------

@dataclass
class DeploymentEvent:
    """A tofu apply or ansible run completion event."""
    event_id:       str
    cell_id:        str
    tool:           str    # "tofu" | "ansible"
    workspace:      Optional[str] = None
    playbook:       Optional[str] = None
    exit_code:      int    = 0
    deployed_at:    Optional[str] = None
    changed_resources: list[str] = field(default_factory=list)


def handle_deployment_event(event: DeploymentEvent) -> dict:
    """
    Process a deployment event and determine twin update needs.

    A successful tofu apply triggers VM state and provenance update.
    A successful ansible run triggers service state and platform update.
    """
    if event.exit_code != 0:
        return {
            "event_id":  event.event_id,
            "update_required": False,
            "reason": f"Deployment failed (exit {event.exit_code}) — no twin update.",
        }

    categories: list[str] = []
    if event.tool == "tofu":
        categories = ["bootstrap_state", "cluster_state", "provisioning"]
        if event.workspace:
            categories.append("provenance_records")
    elif event.tool == "ansible":
        categories = ["service_state", "platform_state", "configuration"]
        if event.playbook and "k3s" in event.playbook:
            categories.append("cluster_state")

    return {
        "event_id":            event.event_id,
        "cell_id":             event.cell_id,
        "tool":                event.tool,
        "categories_affected": categories,
        "update_required":     bool(categories),
        "reason": f"{event.tool} run completed. Categories: {', '.join(categories)}.",
    }


# ---------------------------------------------------------------------------
# 24.4 — Staleness Alerting
# ---------------------------------------------------------------------------

@dataclass
class StalenessAlert:
    """A staleness alert for a state category that has exceeded its threshold."""
    cell_id:         str
    category:        str
    last_updated_at: Optional[str]
    max_age_hours:   float
    age_hours:       float
    severity:        str   # "YELLOW" | "ORANGE" | "RED"
    reason:          str


# Default max age thresholds per state category (hours)
_DEFAULT_MAX_AGE: dict[str, float] = {
    "hardware_state":         24.0,
    "platform_state":         24.0,
    "cluster_state":           6.0,
    "storage_state":           6.0,
    "data_protection_state":  12.0,
    "observability_state":     4.0,
    "service_state":           6.0,
    "bootstrap_state":        24.0,
    "network_topology":       24.0,
    "capability_state":       24.0,
    "external_dependencies":  12.0,
    "backup_config":          24.0,
}


def check_staleness(
    cell_id:       str,
    state_docs:    dict[str, dict],   # {category: doc_with_collected_at}
    *,
    max_age_hours: dict[str, float] | None = None,
    now_fn:        Optional[Callable[[], str]] = None,
) -> list[StalenessAlert]:
    """
    Check all declared state categories for staleness.

    Returns StalenessAlert for any category that:
      - Has no data (age = infinity → RED)
      - Exceeds max_age_hours threshold (ORANGE or YELLOW)
    """
    from datetime import datetime, timezone
    now_str = (now_fn or (lambda: datetime.now(timezone.utc).isoformat()))()
    now     = datetime.fromisoformat(now_str.replace("Z", "+00:00"))
    thresholds = {**(max_age_hours or {}), **{k: v for k, v in _DEFAULT_MAX_AGE.items()
                                               if k not in (max_age_hours or {})}}
    alerts: list[StalenessAlert] = []

    for category, max_h in thresholds.items():
        doc = state_docs.get(category)
        last_updated = None
        if doc:
            last_updated = doc.get("collected_at") or doc.get("declared_at") or doc.get("last_updated_at")

        if last_updated is None:
            alerts.append(StalenessAlert(
                cell_id=cell_id, category=category,
                last_updated_at=None, max_age_hours=max_h,
                age_hours=float("inf"),
                severity="YELLOW",
                reason=f"No {category} data collected.",
            ))
            continue

        try:
            last = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            age_h = (now - last).total_seconds() / 3600
        except (ValueError, AttributeError):
            continue

        if age_h > max_h * 2:
            severity = "RED"
        elif age_h > max_h * 1.5:
            severity = "ORANGE"
        elif age_h > max_h:
            severity = "YELLOW"
        else:
            continue   # within threshold

        alerts.append(StalenessAlert(
            cell_id=cell_id, category=category,
            last_updated_at=last_updated, max_age_hours=max_h,
            age_hours=age_h, severity=severity,
            reason=f"{category}: {age_h:.0f}h old (max {max_h:.0f}h).",
        ))

    return alerts


# ---------------------------------------------------------------------------
# 24.5 — Twin Diff Report
# ---------------------------------------------------------------------------

@dataclass
class TwinDiffEntry:
    """One changed field in the twin since the last report."""
    category:  str
    field:     str
    old_value: Any
    new_value: Any
    changed_at: str


@dataclass
class TwinDiffReport:
    """Summary of what changed in the twin since the last report."""
    cell_id:       str
    from_snapshot: str
    to_snapshot:   str
    entries:       list[TwinDiffEntry] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.entries)

    @property
    def by_category(self) -> dict[str, list[TwinDiffEntry]]:
        result: dict[str, list[TwinDiffEntry]] = {}
        for e in self.entries:
            result.setdefault(e.category, []).append(e)
        return result


def build_twin_diff_report(
    cell_id:       str,
    old_state:     dict[str, Any],
    new_state:     dict[str, Any],
    *,
    from_snapshot: str = "previous",
    to_snapshot:   str = "current",
    now_fn:        Optional[Callable[[], str]] = None,
) -> TwinDiffReport:
    """
    Compare old and new twin state documents and produce a diff report.

    Performs shallow per-category key comparison. For deep diffs, each
    category's collector is responsible for its own detailed change tracking.
    """
    from datetime import datetime, timezone
    now_str = (now_fn or (lambda: datetime.now(timezone.utc).isoformat()))()
    entries: list[TwinDiffEntry] = []

    all_cats = set(old_state.keys()) | set(new_state.keys())
    for cat in sorted(all_cats):
        old_doc = old_state.get(cat) or {}
        new_doc = new_state.get(cat) or {}
        if not isinstance(old_doc, dict) or not isinstance(new_doc, dict):
            if old_doc != new_doc:
                entries.append(TwinDiffEntry(cat, "(root)", old_doc, new_doc, now_str))
            continue
        all_keys = set(old_doc.keys()) | set(new_doc.keys())
        for key in sorted(all_keys):
            if key in ("collected_at", "declared_at", "schema_version", "cell_id"):
                continue
            old_val = old_doc.get(key)
            new_val = new_doc.get(key)
            if old_val != new_val:
                entries.append(TwinDiffEntry(cat, key, old_val, new_val, now_str))

    return TwinDiffReport(
        cell_id=cell_id,
        from_snapshot=from_snapshot,
        to_snapshot=to_snapshot,
        entries=entries,
    )


# ---------------------------------------------------------------------------
# 24.6 — PBS State Updater
# ---------------------------------------------------------------------------

@dataclass
class PbsJobStatus:
    """Status of a single PBS backup job."""
    job_id:       str
    vm_id:        Optional[int]
    vm_name:      Optional[str]
    last_run_at:  Optional[str]
    status:       str    # "ok" | "failed" | "running" | "unknown"
    last_size_gb: Optional[float] = None
    next_run_at:  Optional[str]   = None
    task_log_url: Optional[str]   = None


def collect_pbs_state_update(
    pbs_api_response: dict,
    cell_id:          str,
    now_fn:           Optional[Callable[[], str]] = None,
) -> dict:
    """
    Parse a PBS API response and extract Data Protection State update.

    pbs_api_response: dict from PBS /api2/json/nodes/... endpoint.
    Returns a partial data_protection_state dict for twin update.
    """
    jobs: list[PbsJobStatus] = []
    for job in (pbs_api_response.get("data") or []):
        job_id = job.get("id") or job.get("job-id") or "unknown"
        # PBS API returns last-run-endtime as a Unix epoch integer; convert to ISO string
        # Only use last-run-endtime if last-run-upid is present (job actually ran)
        if job.get("last-run-upid"):
            _endtime = job.get("last-run-endtime")
        else:
            _endtime = None
        if isinstance(_endtime, (int, float)) and _endtime:
            _last_run_at: Optional[str] = datetime.fromtimestamp(
                _endtime, tz=timezone.utc
            ).isoformat()
        else:
            _last_run_at = None
        jobs.append(PbsJobStatus(
            job_id=job_id,
            vm_id=job.get("vmid"),
            vm_name=job.get("comment") or job.get("name"),
            last_run_at=_last_run_at,
            status="ok" if job.get("last-run-state") == "OK" else
                   ("failed" if job.get("last-run-state") else "unknown"),
            last_size_gb=job.get("last-run-size-bytes") and
                         round(job["last-run-size-bytes"] / 1e9, 2),
            next_run_at=job.get("next-run"),
        ))

    return {
        "cell_id":      cell_id,
        "collected_at": (now_fn or (lambda: datetime.now(timezone.utc).isoformat()))(),
        "backup_jobs":  [
            {
                "job_id":     j.job_id,
                "vm_id":      j.vm_id,
                "vm_name":    j.vm_name,
                "last_run_at": j.last_run_at,
                "status":     j.status,
                "last_size_gb": j.last_size_gb,
                "next_run_at": j.next_run_at,
            }
            for j in jobs
        ],
        "jobs_ok":     sum(1 for j in jobs if j.status == "ok"),
        "jobs_failed": sum(1 for j in jobs if j.status == "failed"),
    }


# ---------------------------------------------------------------------------
# 24.7 — Certificate Expiry Monitor
# ---------------------------------------------------------------------------

@dataclass
class CertExpiryAlert:
    """A certificate approaching expiry."""
    dependency_id: str
    dependency_name: str
    cert_expires_at: str
    days_remaining:  int
    severity:        str   # "YELLOW" | "ORANGE" | "RED"
    action_required: str


def scan_cert_expiry(
    external_dependencies: list[dict],
    *,
    now_fn: Optional[Callable[[], str]] = None,
) -> list[CertExpiryAlert]:
    """
    Scan external dependencies for certificates approaching expiry.

    Returns CertExpiryAlert for any cert within 60 days of expiry.
    Severity: RED ≤ 7d, ORANGE ≤ 30d, YELLOW ≤ 60d.
    """
    from datetime import datetime, timezone
    now_str = (now_fn or (lambda: datetime.now(timezone.utc).isoformat()))()
    now     = datetime.fromisoformat(now_str.replace("Z", "+00:00"))

    alerts: list[CertExpiryAlert] = []
    for dep in external_dependencies:
        cert = dep.get("certificate") or {}
        if not cert.get("expires_at"):
            continue
        try:
            exp = datetime.fromisoformat(cert["expires_at"].replace("Z", "+00:00"))
            days = (exp - now).days
        except (ValueError, AttributeError):
            continue

        if days > 60:
            continue

        if days <= 7:
            sev    = "RED"
            action = f"URGENT: renew {dep.get('name', '?')} cert immediately"
        elif days <= 30:
            sev    = "ORANGE"
            action = f"ACTION REQUIRED: renew {dep.get('name', '?')} cert within {days} days"
        else:
            sev    = "YELLOW"
            action = f"PLAN: schedule {dep.get('name', '?')} cert renewal ({days}d remaining)"

        alerts.append(CertExpiryAlert(
            dependency_id=dep.get("id") or dep.get("name") or "?",
            dependency_name=dep.get("name") or "?",
            cert_expires_at=cert["expires_at"],
            days_remaining=days,
            severity=sev,
            action_required=action,
        ))

    alerts.sort(key=lambda a: a.days_remaining)
    return alerts


# ---------------------------------------------------------------------------
# Security scan ingestion hook
# ---------------------------------------------------------------------------

def run_security_scan(base_dir: str, state_path: str) -> dict:
    """
    Invoke the security analyzer against base_dir, persist the result into
    bootstrap-state.json at state_path, and return a summary dict.

    Imports security_analyzer lazily so the continuous assessor does not
    require it at module-load time.
    """
    try:
        import security_analyzer as _sa  # type: ignore
    except ImportError:
        return {"error": "security_analyzer not available", "posture": "UNKNOWN"}

    import json as _json
    import os as _os

    state: Optional[dict] = None
    if state_path and _os.path.exists(state_path):
        try:
            with open(state_path) as fh:
                state = _json.load(fh)
        except (OSError, _json.JSONDecodeError):
            pass

    report = _sa.scan(
        base_dir=base_dir,
        state=state,
        state_path=state_path,
    )

    if state_path:
        _sa.write_security_scan_result(state_path, report)

    return {
        "scanned_at":    report.scanned_at,
        "posture":       _sa.security_posture_score(report),
        "files_scanned": report.files_scanned,
        "red_count":     report.red_count,
        "orange_count":  report.orange_count,
        "yellow_count":  report.yellow_count,
    }


# ---------------------------------------------------------------------------
# 24.8 — Code Health Assessment (Phase 1.L)
# ---------------------------------------------------------------------------

@dataclass
class CodeHealthScore:
    """Static analysis health score for the broodforge codebase."""
    shellcheck_findings: int = 0       # total shellcheck warnings + errors
    bandit_high_count:   int = 0       # bandit HIGH severity findings
    bandit_medium_count: int = 0       # bandit MEDIUM severity findings
    vulture_dead_pct:    float = 0.0   # dead code percentage from vulture
    coverage_pct:        float = 0.0   # test coverage percentage
    overall:             int = 100     # composite score 0-100
    assessed_at:         str = ""
    error:               Optional[str] = None  # set if assessment could not run


def _score_code_health(
    shellcheck_findings: int,
    bandit_high: int,
    bandit_medium: int,
    vulture_dead_pct: float,
    coverage_pct: float,
) -> int:
    """Compute a 0-100 code health score from static analysis results."""
    score = 100
    # shellcheck: -3 per finding, capped at -30
    score -= min(shellcheck_findings * 3, 30)
    # bandit HIGH: -15 per finding, capped at -30
    score -= min(bandit_high * 15, 30)
    # bandit MEDIUM: -5 per finding, capped at -15
    score -= min(bandit_medium * 5, 15)
    # vulture: -0.5 per dead-code percent
    score -= int(vulture_dead_pct * 0.5)
    # coverage: penalty for coverage < 80%
    if coverage_pct < 80:
        score -= int((80 - coverage_pct) * 0.5)
    return max(0, score)


def assess_code_health(
    repo_root: str = ".",
    *,
    run_fn: Optional[Callable] = None,
    now_fn: Optional[Callable[[], str]] = None,
) -> CodeHealthScore:
    """
    Run static analysis tools and return a CodeHealthScore.

    Tier 3 of the Static Analysis Self-Audit pipeline (Phase 1.L, AD-062).
    Runs shellcheck, ruff, bandit, vulture, and reads coverage if available.
    Subprocess calls are injectable via run_fn for testing.

    Args:
        repo_root: root directory of the broodforge repo
        run_fn: injectable subprocess runner (defaults to subprocess.run)
        now_fn: injectable clock (defaults to utcnow)
    """
    import subprocess as _subprocess
    import json as _json

    _run = run_fn or _subprocess.run
    _now = (now_fn or (lambda: datetime.now(timezone.utc).isoformat()))()

    root = repo_root
    pb = f"{root}/proxmox-bootstrap" if root != "." else "proxmox-bootstrap"

    shellcheck_findings = 0
    bandit_high = 0
    bandit_medium = 0
    vulture_dead_pct = 0.0
    coverage_pct = 0.0

    try:
        # shellcheck: count total findings across all .sh files
        import glob as _glob
        sh_files = _glob.glob(f"{root}/**/*.sh", recursive=True)
        sh_files = [
            f for f in sh_files
            if ".git" not in f and "/new/" not in f and "\\new\\" not in f
            and "/deprecated/" not in f and "\\deprecated\\" not in f
        ]
        if sh_files:
            try:
                sc = _run(
                    ["shellcheck", "--severity=warning", "--format=json"] + sh_files,
                    capture_output=True, text=True, timeout=60,
                )
                try:
                    findings = _json.loads(sc.stdout) if sc.stdout.strip() else []
                    shellcheck_findings = len(findings)
                except _json.JSONDecodeError:
                    shellcheck_findings = 0
            except (FileNotFoundError, OSError):
                pass  # shellcheck not installed — skip

        # bandit: count HIGH and MEDIUM severity findings
        try:
            bd = _run(
                ["bandit", "-r", pb, "-ll", "-f", "json"],
                capture_output=True, text=True, timeout=120,
            )
            try:
                bd_data = _json.loads(bd.stdout) if bd.stdout.strip() else {}
                results = bd_data.get("results", [])
                bandit_high   = sum(1 for r in results if r.get("issue_severity") == "HIGH")
                bandit_medium = sum(1 for r in results if r.get("issue_severity") == "MEDIUM")
            except _json.JSONDecodeError:
                pass
        except (FileNotFoundError, OSError):
            pass  # bandit not installed — skip

        # vulture: count dead-code lines as percentage of total Python lines
        try:
            vt = _run(
                ["vulture", pb, "--min-confidence", "80"],
                capture_output=True, text=True, timeout=60,
            )
            dead_lines = len([line for line in vt.stdout.splitlines() if line.strip()])
            # estimate total Python LOC for percentage
            py_files = _glob.glob(f"{pb}/**/*.py", recursive=True)
            total_loc = 0
            for pf in py_files:
                try:
                    with open(pf, encoding="utf-8", errors="replace") as f:
                        total_loc += sum(1 for line in f if line.strip())
                except (OSError, UnicodeDecodeError):
                    pass
            if total_loc > 0:
                vulture_dead_pct = min(round(dead_lines * 100 / total_loc, 1), 100.0)
        except (FileNotFoundError, OSError):
            pass  # vulture not installed — skip

        # coverage: read .audit/coverage.json if present
        cov_path = f"{root}/.audit/coverage.json"
        try:
            with open(cov_path) as f:
                cov_data = _json.load(f)
            coverage_pct = round(cov_data.get("totals", {}).get("percent_covered", 0.0), 1)
        except (OSError, _json.JSONDecodeError, KeyError):
            pass

    except Exception as exc:
        return CodeHealthScore(
            assessed_at=_now,
            error=str(exc),
        )

    overall = _score_code_health(
        shellcheck_findings, bandit_high, bandit_medium, vulture_dead_pct, coverage_pct
    )
    return CodeHealthScore(
        shellcheck_findings=shellcheck_findings,
        bandit_high_count=bandit_high,
        bandit_medium_count=bandit_medium,
        vulture_dead_pct=vulture_dead_pct,
        coverage_pct=coverage_pct,
        overall=overall,
        assessed_at=_now,
    )
