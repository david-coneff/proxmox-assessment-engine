"""
Tests for Phase 1.L: assess_code_health() and dashboard Code Health card.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "proxmox-bootstrap"))

from continuous_assessment import assess_code_health, CodeHealthScore, _score_code_health


class TestScoreCodeHealth:
    def test_perfect_score(self):
        score = _score_code_health(0, 0, 0, 0.0, 95.0)
        assert score == 100

    def test_high_bandit_penalized(self):
        score = _score_code_health(0, 2, 0, 0.0, 95.0)
        assert score <= 70

    def test_low_coverage_penalized(self):
        score = _score_code_health(0, 0, 0, 0.0, 50.0)
        assert score < 100

    def test_score_clamped_to_zero(self):
        score = _score_code_health(100, 10, 10, 50.0, 0.0)
        assert score == 0

    def test_score_not_negative(self):
        score = _score_code_health(999, 999, 999, 100.0, 0.0)
        assert score >= 0

    def test_shellcheck_penalty(self):
        # 10 shellcheck findings → -30 (capped)
        score_many = _score_code_health(10, 0, 0, 0.0, 95.0)
        score_none = _score_code_health(0, 0, 0, 0.0, 95.0)
        assert score_many < score_none

    def test_medium_bandit_penalty(self):
        score_with = _score_code_health(0, 0, 3, 0.0, 95.0)
        score_without = _score_code_health(0, 0, 0, 0.0, 95.0)
        assert score_with < score_without

    def test_vulture_penalty(self):
        score_with = _score_code_health(0, 0, 0, 20.0, 95.0)
        score_without = _score_code_health(0, 0, 0, 0.0, 95.0)
        assert score_with < score_without

    def test_coverage_at_80_no_penalty(self):
        score = _score_code_health(0, 0, 0, 0.0, 80.0)
        assert score == 100

    def test_coverage_below_80_penalized(self):
        # 60% coverage → penalty = int((80-60)*0.5) = 10
        score = _score_code_health(0, 0, 0, 0.0, 60.0)
        assert score < 100


class TestAssessCodeHealth:
    def _make_run_fn(self, shellcheck_findings=None, bandit_results=None, vulture_lines=None):
        """Factory for a mock subprocess.run that returns test data."""
        def run_fn(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if isinstance(cmd, list) and cmd and "shellcheck" in cmd[0]:
                result.stdout = json.dumps(shellcheck_findings or [])
            elif isinstance(cmd, list) and cmd and "bandit" in cmd[0]:
                data = {"results": bandit_results or []}
                result.stdout = json.dumps(data)
            elif isinstance(cmd, list) and cmd and "vulture" in cmd[0]:
                lines = vulture_lines or []
                result.stdout = "\n".join(lines)
            else:
                result.stdout = ""
            return result
        return run_fn

    def test_returns_code_health_score(self):
        run_fn = self._make_run_fn()
        result = assess_code_health(".", run_fn=run_fn)
        assert isinstance(result, CodeHealthScore)

    def test_counts_shellcheck_findings(self):
        findings = [
            {"level": "error", "message": "foo", "line": 1, "code": "SC2034"},
            {"level": "warning", "message": "bar", "line": 2, "code": "SC2035"},
        ]
        run_fn = self._make_run_fn(shellcheck_findings=findings)
        result = assess_code_health(".", run_fn=run_fn)
        assert result.shellcheck_findings == 2

    def test_counts_bandit_high_and_medium(self):
        bandit_results = [
            {"issue_severity": "HIGH", "issue_text": "Use of exec"},
            {"issue_severity": "MEDIUM", "issue_text": "Use of assert"},
            {"issue_severity": "LOW", "issue_text": "Trivial"},
        ]
        run_fn = self._make_run_fn(bandit_results=bandit_results)
        result = assess_code_health(".", run_fn=run_fn)
        assert result.bandit_high_count == 1
        assert result.bandit_medium_count == 1

    def test_overall_score_decreases_with_findings(self):
        bandit_results = [{"issue_severity": "HIGH", "issue_text": "foo"}] * 3
        run_fn = self._make_run_fn(bandit_results=bandit_results)
        result = assess_code_health(".", run_fn=run_fn)
        assert result.overall < 60

    def test_shellcheck_not_installed_does_not_crash(self):
        def run_fn(cmd, **kwargs):
            if isinstance(cmd, list) and cmd and "shellcheck" in cmd[0]:
                raise FileNotFoundError("shellcheck not found")
            result = MagicMock()
            result.stdout = json.dumps({"results": []})
            return result
        result = assess_code_health(".", run_fn=run_fn)
        assert isinstance(result, CodeHealthScore)
        assert result.shellcheck_findings == 0

    def test_bandit_not_installed_does_not_crash(self):
        def run_fn(cmd, **kwargs):
            if isinstance(cmd, list) and cmd and "bandit" in cmd[0]:
                raise FileNotFoundError("bandit not found")
            result = MagicMock()
            result.stdout = "[]"
            return result
        result = assess_code_health(".", run_fn=run_fn)
        assert isinstance(result, CodeHealthScore)
        assert result.bandit_high_count == 0

    def test_assessed_at_is_set(self):
        run_fn = self._make_run_fn()
        result = assess_code_health(".", run_fn=run_fn)
        assert result.assessed_at != ""

    def test_no_high_findings_high_score(self):
        run_fn = self._make_run_fn(shellcheck_findings=[], bandit_results=[])
        result = assess_code_health(".", run_fn=run_fn)
        # No shellcheck/bandit HIGH findings — overall should be at least 50
        # (coverage_pct will be 0.0 since no .audit/coverage.json exists in test CWD,
        # which applies a coverage penalty, so we can't assert 100)
        assert result.overall >= 50
        assert result.bandit_high_count == 0
        assert result.shellcheck_findings == 0

    def test_custom_now_fn(self):
        run_fn = self._make_run_fn()
        result = assess_code_health(".", run_fn=run_fn, now_fn=lambda: "2026-06-08T00:00:00+00:00")
        assert result.assessed_at == "2026-06-08T00:00:00+00:00"

    def test_bandit_json_decode_error_does_not_crash(self):
        def run_fn(cmd, **kwargs):
            result = MagicMock()
            result.stdout = "not valid json {"
            return result
        result = assess_code_health(".", run_fn=run_fn)
        assert isinstance(result, CodeHealthScore)

    def test_bandit_low_not_counted(self):
        bandit_results = [
            {"issue_severity": "LOW", "issue_text": "Trivial"},
            {"issue_severity": "LOW", "issue_text": "Minor"},
        ]
        run_fn = self._make_run_fn(bandit_results=bandit_results)
        result = assess_code_health(".", run_fn=run_fn)
        assert result.bandit_high_count == 0
        assert result.bandit_medium_count == 0


class TestCodeHealthRemediationCandidates:
    def test_high_bandit_produces_candidates(self):
        """HIGH bandit findings should surface as remediation candidates."""
        from broodforge_dashboard import _code_health_to_remediation_candidates
        score = CodeHealthScore(bandit_high_count=2, bandit_medium_count=0, overall=60)
        candidates = _code_health_to_remediation_candidates(score)
        assert len(candidates) > 0
        assert any(
            "bandit" in c.get("description", "").lower()
            or "security" in c.get("description", "").lower()
            or "HIGH" in c.get("description", "")
            for c in candidates
        )

    def test_clean_codebase_no_candidates(self):
        from broodforge_dashboard import _code_health_to_remediation_candidates
        score = CodeHealthScore(bandit_high_count=0, shellcheck_findings=0, overall=95)
        candidates = _code_health_to_remediation_candidates(score)
        assert len(candidates) == 0

    def test_high_shellcheck_produces_candidates(self):
        from broodforge_dashboard import _code_health_to_remediation_candidates
        score = CodeHealthScore(bandit_high_count=0, shellcheck_findings=10, overall=70)
        candidates = _code_health_to_remediation_candidates(score)
        assert len(candidates) > 0

    def test_low_shellcheck_no_candidate(self):
        from broodforge_dashboard import _code_health_to_remediation_candidates
        # threshold is >= 5 findings for a remediation candidate
        score = CodeHealthScore(bandit_high_count=0, shellcheck_findings=3, overall=91)
        candidates = _code_health_to_remediation_candidates(score)
        assert len(candidates) == 0

    def test_candidate_has_required_keys(self):
        from broodforge_dashboard import _code_health_to_remediation_candidates
        score = CodeHealthScore(bandit_high_count=1, overall=70)
        candidates = _code_health_to_remediation_candidates(score)
        assert len(candidates) >= 1
        c = candidates[0]
        assert "type" in c
        assert "severity" in c
        assert "description" in c
        assert "source" in c
        assert "proposed_at" in c


class TestDashboardCodeHealthCard:
    def test_code_health_card_renders(self):
        """Dashboard Code Health card should render without errors."""
        from broodforge_dashboard import _build_code_health_card
        score = CodeHealthScore(
            shellcheck_findings=2,
            bandit_high_count=1,
            bandit_medium_count=3,
            vulture_dead_pct=5.0,
            coverage_pct=75.0,
            overall=65,
            assessed_at="2026-06-08T00:00:00+00:00",
        )
        html = _build_code_health_card(score)
        assert "Code Health" in html or "overall" in html.lower() or "65" in html
        assert "65" in html  # overall score
        assert "<div" in html

    def test_code_health_card_handles_error(self):
        from broodforge_dashboard import _build_code_health_card
        score = CodeHealthScore(error="shellcheck not found", overall=0)
        html = _build_code_health_card(score)
        assert "<div" in html
        assert "shellcheck" in html.lower() or "unavailable" in html.lower() or "error" in html.lower()

    def test_code_health_card_shows_bandit_tip(self):
        from broodforge_dashboard import _build_code_health_card
        score = CodeHealthScore(bandit_high_count=2, overall=70)
        html = _build_code_health_card(score)
        assert "bandit" in html.lower()

    def test_code_health_card_shows_shellcheck_tip(self):
        from broodforge_dashboard import _build_code_health_card
        score = CodeHealthScore(shellcheck_findings=5, overall=85)
        html = _build_code_health_card(score)
        assert "shellcheck" in html.lower()

    def test_code_health_card_green_score(self):
        from broodforge_dashboard import _build_code_health_card
        score = CodeHealthScore(overall=95)
        html = _build_code_health_card(score)
        assert "95" in html
        # green color used for high scores
        assert "green" in html

    def test_code_health_card_shows_coverage(self):
        from broodforge_dashboard import _build_code_health_card
        score = CodeHealthScore(coverage_pct=82.5, overall=100)
        html = _build_code_health_card(score)
        assert "82.5" in html

    def test_generate_dashboard_html_includes_code_health(self):
        """generate_dashboard_html should accept and render code_health kwarg."""
        from broodforge_dashboard import generate_dashboard_html, DashboardConfig
        cfg = DashboardConfig()
        score = CodeHealthScore(overall=88, bandit_high_count=0, shellcheck_findings=0)
        html = generate_dashboard_html(
            state={}, scores={}, nodes=[], failures=[], backup={},
            cfg=cfg, code_health=score,
        )
        assert "Code Health" in html
        assert "88" in html
