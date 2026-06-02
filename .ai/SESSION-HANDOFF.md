# Session Handoff

Date: 2026-06-02 UTC
Status: **Full-stack review complete, all roadmap phases done, ODS→HTML migration complete. Tests: 3434 total (3430 passed, 4 skipped).**
Next: Phase 9.T (Talos alternative) if desired, or begin deploying to hardware.

---

## Project Identity

Project: **broodforge** — Self-Documenting, Self-Recovering Infrastructure Platform

| Term | Meaning |
|---|---|
| **Forging** | Initial deployment of the first node — bare hardware → hatchery |
| **Forge package** | Self-contained archive for forging the first hatchery |
| **Hatchery** | The operational first node (what forging produces) |
| **Hatchery process** | Phase A subsequent: produces spawn packages for broodlings |
| **Broodling** | A newly spawned node joining the hatchery |
| **Spawn package** | Self-contained archive for deploying a broodling (new identity) |
| **Stargate process** | Produces phoenix packages for failed-node resurrection |
| **Phoenix package** | Self-contained archive for reconstituting a failed node (identity preserved) |

---

## Work Completed This Session

### Security fixes (5 items)
- `forge_keepass_init.py`: Added `__main__` CLI; fixed single-quoted `'$KEEPASS_MASTER_PASSWORD'` bug and switched all `keepassxc-cli` invocations to stdin piping
- `forge_scripts.py` phase-05: k3s join token written to temp vars file (`-e @file`), never exposed on ansible command line (`ps aux`)
- `network_topology_collector.py`: `StrictHostKeyChecking=no` → `accept-new`
- `keepass_mfa.py` + `forge_scripts.py`: TOTP secret redirected to `/dev/tty` (new `print_totp_setup_to_tty()`); forge gate prompts use `/dev/tty`
- `forge_scripts.py` `FORGE_KEEPASS_GATE_SH`: Removed `export KEEPASS_MASTER_PASSWORD`

### Architecture / doc cleanup
- Retired `docs/ARCHITECTURE-REVIEW-v4/v5/v6.md`, `docs/MILESTONE-5-DESIGN.md` → `deprecated/`
- Moved `docs/SESSION-HANDOFF.md` → `.ai/SESSION-HANDOFF.md`; deleted `docs/DNS-UPDATE-SETUP.md`
- Bumped `docs/ARCHITECTURE-REVIEW-v7.md` to v7.1; removed stale "Architecture Gaps" table from `.ai/CURRENT_STATE.md`
- Added naming-convention section to `proxmox-bootstrap/README.md`

### Checkbox behavior fix
- `docs/SETUP-GUIDE.html`: `text-decoration: line-through` → `font-style: italic`

### New HTML documentation guides (6 files in `docs/`)
- `CLOUDFLARE-SETUP.html`, `DUCKDNS-SETUP.html`, `CLOUD-STORAGE-SETUP.html`
- `TALOS-ALTERNATIVE.html` (localStorage checklist), `CONTAINER-COMPATIBILITY-PLAN.html`
- `ARCHITECTURE.html` (comprehensive design reference with collapsible AD-022–AD-050)

### Broodforge sidecar dashboard — Approach A
- `proxmox-bootstrap/broodforge_dashboard.py`: Stdlib HTTP server on port 9322
  - Live HTML dashboard, API endpoints, doc proxy, auto-detects Proxmox TLS cert
  - `--install-service` prints systemd unit

### ODS → HTML workbook migration
- New `doc-gen/renderers/html_recovery_workbook.py`: 5-section recovery workbook HTML
- `engine.py`: HTML-only output (no more `.ods`/`.odt` files written)
- `assemble_spawn_package.py` + `assemble_forge_package.py`: HTML workbooks
- Architecture docs updated; assembler tests updated

### Roadmap completion
- 124 previously unchecked items marked `[x]` (Phases 1.F, 6.B, 7.1/7.2, 12.E.3/7-12, 13–25)
- ROADMAP.md version 7.1; only 9.T (Talos) remains

### Phase 1.F.8 — Service password compatibility detector (NEW)
- `proxmox-bootstrap/service_password_compat.py`: detect/record/regenerate credential format
- `spawn_planner.py`: `ServiceCatalog.password_format()`, `alphanumeric_services()`, `credential_format_overrides` in spawn plan
- `CREDENTIAL_COMPAT_SH` bash library for embedding in phase scripts
- 29 new tests

---

## Current Test Count: 3434 (3430 passed, 4 skipped)

Pre-existing failures (~14) excluded: legacy `engine/schema.py` + `tests/test_guest.py` BOM issue (UTF-8 BOM in `schemas/assessment.schema.json` causes `json.loads()` to fail on Windows). Unrelated to all work done.

---

## Remaining Work

### Phase 9.T — Talos Linux Alternative (optional, not started)
Design in `docs/TALOS-ALTERNATIVE.html`. Scripts needed:
- `proxmox-bootstrap/build-talos-template.sh`
- `proxmox-bootstrap/generate-talos-config.py`
- `proxmox-bootstrap/migrate-k3s-to-talos.py` + `migrate-k3s-to-ubuntu.py`
- `proxmox-bootstrap/migrate_k3s_lib.py`

### Dashboard enhancements
- Approach B: Proxmox UI iframe integration via JS patch extension of `pve-suppress-nag.sh`
- KeePass-gated action endpoints (forge/spawn/phoenix triggers) as browser session flow

---

## Architecture Version: v7.1

All three files consistent: `ARCHITECTURE.md`, `docs/ARCHITECTURE-REVIEW-v7.md`, `docs/ARCHITECTURE.html`

---

## Key File Locations

| Purpose | File |
|---|---|
| Bootstrap state | `proxmox-bootstrap/bootstrap-state.json` |
| Forge planner (CLI) | `proxmox-bootstrap/forge-planner.py` |
| Spawn planner (CLI) | `proxmox-bootstrap/spawn-planner.py` |
| Phoenix planner (CLI) | `proxmox-bootstrap/phoenix-planner.py` |
| Forge package assembler | `proxmox-bootstrap/assemble_forge_package.py` |
| Spawn package assembler | `proxmox-bootstrap/assemble_spawn_package.py` |
| Doc-gen engine | `doc-gen/engine.py` |
| Broodforge dashboard | `proxmox-bootstrap/broodforge_dashboard.py` |
| Service password compat | `proxmox-bootstrap/service_password_compat.py` |
| HTML recovery workbook | `doc-gen/renderers/html_recovery_workbook.py` |
