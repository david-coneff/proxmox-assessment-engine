# Session Handoff

Last updated: 2026-06-02 UTC

## What Was Done This Session

### Phase 26 — Autonomous Remediation (complete)

All seven sub-phases implemented:

| Sub-phase | Files | Tests |
|---|---|---|
| 26.1 Planner | `proxmox-bootstrap/remediation_planner.py` | 18 |
| 26.2 Queue + CLI | `proxmox-bootstrap/remediation_queue.py`, `remediation-cli.py` | 22 |
| 26.3 Executor | `proxmox-bootstrap/remediation_executor.py` | 15 |
| 26.4 Dashboard | `proxmox-bootstrap/broodforge_dashboard.py` (extended) | 4 |
| 26.5 Op Report S8 | `doc-gen/renderers/html_operational_report.py` (extended) | 3 |
| 26.6 Policy Engine | `proxmox-bootstrap/remediation_policy.py` | 14 |
| 26.7 Autonomous Mode | `remediation_policy.py` (extended), `remediation-cli.py` (extended) | 18 |
| Schema | `data-model/bootstrap-state-schema.json` (added remediation_proposal, remediation_policy) | — |

Test file: `tests/unit/test_remediation.py` — 94 tests, all passing.

### Security Analyzer (complete)

New `proxmox-bootstrap/security_analyzer.py` module:
- Log file scanning (8 patterns: TOTP seeds, private keys, passwords, k3s tokens, API keys, restic passwords, bearer tokens)
- Shell script scanning (7 patterns: StrictHostKeyChecking=no, passwords on cmdlines, exported secrets, echo-pipe, bearer in curl, set -x, /dev/null known hosts)
- Manifest/state file scanning (plaintext password/secret fields, private key material)
- One-shot audit mode
- HTML security report (same dark-theme style as dashboard)
- `security_posture_score()` → GREEN/YELLOW/ORANGE/RED
- `doc-gen/readiness.py` extended with `_score_security_posture()` — new "Security Posture" scoring dimension
- `broodforge_dashboard.py` extended with Security section and `/api/security` endpoint
- `bootstrap-state.json` `security_scan.last_result` field stores scan results for readiness integration

Test file: `tests/unit/test_security_analyzer.py` — 56 tests, all passing.

## What's Left (in priority order)

1. **Security analyzer** — continuous log scanner + HTML report + readiness score dimension.
   - Scan for plaintext secrets in forge.log, spawn.log etc.
   - Scan shell scripts for unsafe patterns (StrictHostKeyChecking=no, passwords on cmdlines)
   - Scan bootstrap-state.json / manifests for plaintext secret fields
   - Continuous + one-shot audit modes
   - HTML report (same dark-theme style as existing docs)
   - New "Security Posture" score in readiness scorer
   - Security tab in broodforge_dashboard.py
   - Tests

2. **Setup Guide manifest import explainer** — add a clear section to the bottom of
   `docs/SETUP-GUIDE.html` explaining: what the import does, how to use it (drag-and-drop /
   paste), what fields it auto-fills, what the user must still fill in manually.

3. **Readable passphrase generation** — investigate keepassxc-cli diceware support
   (`keepassxc-cli generate --words`). If available, wire it in. If not, implement a
   stdlib-only EFF wordlist generator (`lib/passphrase_eff.py`) producing "correct-horse-battery-staple"
   style passphrases and integrate as an alternative to the existing Capital.word.phrase.9 format.

4. **HTML manifests for package exports** — for forge, spawn, and phoenix packages, produce
   a self-contained HTML file explaining package contents. Establish as a mandatory architecture
   pattern in ARCHITECTURE.md: every machine-readable manifest must have a human-readable HTML
   counterpart.

## Test Counts

- Tests at Phase 26 completion: 3528 total (3398 passed, 37 skipped, 3 pre-existing env failures)
- Pre-existing failures: `test_phase18_capability_secret.py` and `test_service_state_collector.py`
  — all `ModuleNotFoundError: No module named 'jsonschema'`, not related to broodforge code

## Architecture Notes

- All Phase 26 modules live in `proxmox-bootstrap/` and use stdlib only
- `bootstrap-state.json` gains two new optional top-level fields: `remediations` (array) and
  `remediation_policy` (object)
- Dashboard now accepts `remediations=` kwarg in `generate_dashboard_html()`
- The autonomous mode enabling ceremony requires literal input "enable autonomous"
- KeePass-gated actions (rotate-join-token, run-backup) cannot execute unless
  `executor.keepass_unlocked = True`
- The `dry_run_differs()` check compares original vs current dry-run; >50% line change
  triggers re-approval requirement before execution
