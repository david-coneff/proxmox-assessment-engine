"""
test_phase24_continuous_assessment.py — Phase 24: Continuous Assessment.

Covers:
  24.1  AssessmentSchedule, plan_assessment_schedule()
  24.2  RepoIngestionEvent, handle_repo_ingestion()
  24.3  DeploymentEvent, handle_deployment_event()
  24.4  StalenessAlert, check_staleness()
  24.5  TwinDiffEntry, TwinDiffReport, build_twin_diff_report()
  24.6  PbsJobStatus, collect_pbs_state_update()
  24.7  CertExpiryAlert, scan_cert_expiry()
"""

import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "proxmox-bootstrap"))

import continuous_assessment as _ca


def _now():
    return "2026-06-01T12:00:00+00:00"


# ===========================================================================
# 24.1 — AssessmentSchedule
# ===========================================================================

class TestAssessmentSchedule:
    def test_plan_due_when_no_last_run(self):
        sched = _ca.AssessmentSchedule(cell_id="pve01-cell")
        runs  = _ca.plan_assessment_schedule(sched, now_fn=_now)
        tiers = {r.tier for r in runs}
        assert 1 in tiers
        assert 2 in tiers
        assert 3 in tiers

    def test_not_due_when_recent(self):
        recent = "2026-06-01T11:30:00+00:00"  # 30 min ago
        sched  = _ca.AssessmentSchedule(
            cell_id="pve01-cell",
            tier1_interval_hours=1.0,
            last_tier1_at=recent,
        )
        runs  = _ca.plan_assessment_schedule(sched, now_fn=_now)
        tiers = {r.tier for r in runs}
        assert 1 not in tiers  # within 1h window

    def test_due_when_overdue(self):
        old    = "2026-05-30T12:00:00+00:00"  # 48h ago
        sched  = _ca.AssessmentSchedule(
            cell_id="pve01-cell",
            tier1_interval_hours=6.0,
            last_tier1_at=old,
        )
        runs  = _ca.plan_assessment_schedule(sched, now_fn=_now)
        tiers = {r.tier for r in runs}
        assert 1 in tiers

    def test_run_has_cell_id(self):
        sched = _ca.AssessmentSchedule(cell_id="pve01-cell")
        runs  = _ca.plan_assessment_schedule(sched, now_fn=_now)
        for r in runs:
            assert r.cell_id == "pve01-cell"

    def test_run_status_pending(self):
        sched = _ca.AssessmentSchedule(cell_id="pve01-cell")
        runs  = _ca.plan_assessment_schedule(sched, now_fn=_now)
        for r in runs:
            assert r.status == "pending"


# ===========================================================================
# 24.2 — Repo Ingestion Hook
# ===========================================================================

class TestRepoIngestionHook:
    def _event(self, files):
        return _ca.RepoIngestionEvent(
            event_id="evt-001", cell_id="pve01-cell",
            repo_url="https://forgejo.home.example.com/broodforge/bootstrap.git",
            branch="main", commit_sha="abc1234",
            pushed_at=_now(), changed_files=files,
        )

    def test_bootstrap_state_change_detected(self):
        r = _ca.handle_repo_ingestion(self._event(["bootstrap-state.json"]))
        assert "bootstrap_state" in r["categories_affected"]

    def test_terraform_file_change_detected(self):
        r = _ca.handle_repo_ingestion(self._event(["vms/forgejo/main.tf"]))
        assert "provisioning" in r["categories_affected"]

    def test_ansible_playbook_detected(self):
        r = _ca.handle_repo_ingestion(self._event(["ansible/k3s.yml"]))
        assert "configuration" in r["categories_affected"]

    def test_no_changes_no_update(self):
        r = _ca.handle_repo_ingestion(self._event(["README.md"]))
        assert r["update_required"] is False

    def test_update_required_when_changes(self):
        r = _ca.handle_repo_ingestion(self._event(["bootstrap-state.json"]))
        assert r["update_required"] is True

    def test_reason_includes_commit(self):
        r = _ca.handle_repo_ingestion(self._event(["bootstrap-state.json"]))
        assert "abc1234" in r["reason"] or "bootstrap" in r["reason"].lower()


# ===========================================================================
# 24.3 — Deployment Event Hook
# ===========================================================================

class TestDeploymentEventHook:
    def test_tofu_success_triggers_update(self):
        evt = _ca.DeploymentEvent("e1", "pve01-cell", "tofu", workspace="vms/forgejo",
                                   exit_code=0)
        r   = _ca.handle_deployment_event(evt)
        assert r["update_required"] is True
        assert "bootstrap_state" in r["categories_affected"]

    def test_tofu_failure_no_update(self):
        evt = _ca.DeploymentEvent("e1", "pve01-cell", "tofu", exit_code=1)
        r   = _ca.handle_deployment_event(evt)
        assert r["update_required"] is False

    def test_ansible_success_updates_service_state(self):
        evt = _ca.DeploymentEvent("e2", "pve01-cell", "ansible", playbook="k3s.yml",
                                   exit_code=0)
        r   = _ca.handle_deployment_event(evt)
        assert "service_state" in r["categories_affected"]

    def test_ansible_k3s_also_updates_cluster(self):
        evt = _ca.DeploymentEvent("e2", "pve01-cell", "ansible", playbook="k3s.yml",
                                   exit_code=0)
        r   = _ca.handle_deployment_event(evt)
        assert "cluster_state" in r["categories_affected"]


# ===========================================================================
# 24.4 — Staleness Alerting
# ===========================================================================

class TestStalenessAlerting:
    def _state_docs(self, age_offset_hours: float = 0) -> dict:
        from datetime import datetime, timezone, timedelta
        t = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc) - timedelta(hours=age_offset_hours)
        ts = t.isoformat()
        return {
            "cluster_state":   {"collected_at": ts},
            "service_state":   {"collected_at": ts},
        }

    def test_fresh_data_no_alerts(self):
        alerts = _ca.check_staleness("cell", self._state_docs(0.5), now_fn=_now)
        # Only check the categories we provided (not all defaults)
        provided_alerts = [a for a in alerts if a.category in ("cluster_state", "service_state")]
        assert len(provided_alerts) == 0

    def test_old_data_yellow_alert(self):
        alerts = _ca.check_staleness(
            "cell",
            {"cluster_state": {"collected_at": "2026-05-31T00:00:00+00:00"}},
            max_age_hours={"cluster_state": 6.0},
            now_fn=_now,
        )
        cluster_alerts = [a for a in alerts if a.category == "cluster_state"]
        assert len(cluster_alerts) >= 1
        assert cluster_alerts[0].severity in ("YELLOW", "ORANGE", "RED")

    def test_missing_category_alert(self):
        alerts = _ca.check_staleness(
            "cell", {},
            max_age_hours={"hardware_state": 24.0},
            now_fn=_now,
        )
        hw_alerts = [a for a in alerts if a.category == "hardware_state"]
        assert len(hw_alerts) >= 1
        assert hw_alerts[0].last_updated_at is None

    def test_very_old_data_red(self):
        alerts = _ca.check_staleness(
            "cell",
            {"cluster_state": {"collected_at": "2026-01-01T00:00:00+00:00"}},
            max_age_hours={"cluster_state": 6.0},
            now_fn=_now,
        )
        cl = [a for a in alerts if a.category == "cluster_state"]
        assert cl[0].severity == "RED"

    def test_alert_has_reason(self):
        alerts = _ca.check_staleness(
            "cell",
            {},
            max_age_hours={"cluster_state": 6.0},
            now_fn=_now,
        )
        for a in alerts:
            assert a.reason


# ===========================================================================
# 24.5 — Twin Diff Report
# ===========================================================================

class TestTwinDiffReport:
    def test_no_changes_empty_report(self):
        state = {"service_state": {"collected_at": _now(), "status": "ok"}}
        r = _ca.build_twin_diff_report("cell", state, state.copy(), now_fn=_now)
        assert r.total_changes == 0

    def test_detects_value_change(self):
        old = {"service_state": {"collected_at": _now(), "status": "ok"}}
        new = {"service_state": {"collected_at": _now(), "status": "degraded"}}
        r   = _ca.build_twin_diff_report("cell", old, new, now_fn=_now)
        assert r.total_changes >= 1
        entries = [e for e in r.entries if e.field == "status"]
        assert entries[0].old_value == "ok"
        assert entries[0].new_value == "degraded"

    def test_detects_new_key(self):
        old = {"service_state": {}}
        new = {"service_state": {"new_field": "value"}}
        r   = _ca.build_twin_diff_report("cell", old, new, now_fn=_now)
        assert r.total_changes >= 1

    def test_by_category_grouping(self):
        old = {"svc": {"x": 1}, "hw": {"y": 2}}
        new = {"svc": {"x": 2}, "hw": {"y": 3}}
        r   = _ca.build_twin_diff_report("cell", old, new, now_fn=_now)
        assert "svc" in r.by_category
        assert "hw" in r.by_category

    def test_schema_version_ignored(self):
        old = {"svc": {"schema_version": "1.0", "x": 1}}
        new = {"svc": {"schema_version": "2.0", "x": 1}}
        r   = _ca.build_twin_diff_report("cell", old, new, now_fn=_now)
        assert r.total_changes == 0   # schema_version filtered


# ===========================================================================
# 24.6 — PBS State Updater
# ===========================================================================

class TestPbsStateUpdater:
    def _response(self):
        return {"data": [
            {"id": "job-01", "vmid": 101, "comment": "forgejo",
             "last-run-state": "OK", "last-run-size-bytes": 2_000_000_000,
             "next-run": "2026-06-02T03:00:00Z"},
            {"id": "job-02", "vmid": 102, "comment": "k3s-server",
             "last-run-state": "FAILED"},
        ]}

    def test_returns_dict(self):
        d = _ca.collect_pbs_state_update(self._response(), "pve01-cell")
        assert isinstance(d, dict)

    def test_jobs_present(self):
        d = _ca.collect_pbs_state_update(self._response(), "pve01-cell")
        assert len(d["backup_jobs"]) == 2

    def test_jobs_ok_count(self):
        d = _ca.collect_pbs_state_update(self._response(), "pve01-cell")
        assert d["jobs_ok"] == 1

    def test_jobs_failed_count(self):
        d = _ca.collect_pbs_state_update(self._response(), "pve01-cell")
        assert d["jobs_failed"] == 1

    def test_cell_id_preserved(self):
        d = _ca.collect_pbs_state_update(self._response(), "pve01-cell")
        assert d["cell_id"] == "pve01-cell"


# ===========================================================================
# 24.7 — Certificate Expiry Monitor
# ===========================================================================

class TestCertExpiryMonitor:
    def _deps(self):
        return [
            {"id": "cloudflare", "name": "Cloudflare DNS",
             "certificate": {"expires_at": "2026-06-05T00:00:00+00:00"}},   # 4d → RED
            {"id": "letsencrypt", "name": "Let's Encrypt",
             "certificate": {"expires_at": "2026-06-20T00:00:00+00:00"}},   # 19d → ORANGE
            {"id": "internal", "name": "Internal CA",
             "certificate": {"expires_at": "2026-07-15T00:00:00+00:00"}},   # 44d → YELLOW
            {"id": "distant", "name": "Distant Cert",
             "certificate": {"expires_at": "2027-01-01T00:00:00+00:00"}},   # >60d → no alert
        ]

    def test_returns_alerts(self):
        alerts = _ca.scan_cert_expiry(self._deps(), now_fn=_now)
        assert len(alerts) == 3   # 4d, 19d, 44d — not distant

    def test_red_for_urgent(self):
        alerts = _ca.scan_cert_expiry(self._deps(), now_fn=_now)
        red = [a for a in alerts if a.severity == "RED"]
        assert len(red) == 1
        assert "Cloudflare" in red[0].dependency_name

    def test_orange_for_imminent(self):
        alerts = _ca.scan_cert_expiry(self._deps(), now_fn=_now)
        orange = [a for a in alerts if a.severity == "ORANGE"]
        assert len(orange) == 1
        assert "Encrypt" in orange[0].dependency_name

    def test_yellow_for_approaching(self):
        alerts = _ca.scan_cert_expiry(self._deps(), now_fn=_now)
        yellow = [a for a in alerts if a.severity == "YELLOW"]
        assert len(yellow) >= 1

    def test_sorted_by_days_remaining(self):
        alerts = _ca.scan_cert_expiry(self._deps(), now_fn=_now)
        days   = [a.days_remaining for a in alerts]
        assert days == sorted(days)

    def test_no_cert_no_alert(self):
        deps   = [{"id": "x", "name": "X", "certificate": {}}]
        alerts = _ca.scan_cert_expiry(deps, now_fn=_now)
        assert alerts == []

    def test_action_required_set(self):
        alerts = _ca.scan_cert_expiry(self._deps(), now_fn=_now)
        for a in alerts:
            assert a.action_required
