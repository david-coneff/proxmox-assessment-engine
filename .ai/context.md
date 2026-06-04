# Project AI Context

## What this project is

Broodforge is a self-managing infrastructure platform for home-lab Proxmox + k3s environments.
It covers the full lifecycle: hardware assessment, cell forging, node spawning, phoenix recovery,
continuous health monitoring, and autonomous remediation.

Primary objectives:
- Complete destroy-and-recreate reconstruction from repository state alone
- Self-documenting: every operation produces human-readable HTML artefacts
- Self-assessing: continuous security scanning, readiness scoring, drift detection
- Self-recovering: autonomous remediation proposals with policy-gated execution

## Architecture version

v7.1 — see ARCHITECTURE.md and docs/DESIGN-HISTORY.md for full detail.

Seventeen-state model. Six-layer lifecycle. Three assessment tiers. Five dependency graphs.
Four intelligence tracks complete: Forging Foundation, Cell-Scoped Foundation,
Expanded State Model, Digital Twin + Federation, and Autonomous Operations.

## Six lifecycle phases

1. **Forge** — hardware assessment → forge-manifest.json → forge package → Proxmox + k3s base
2. **Spawn** — hatchery plans new broodling nodes → spawn package → bare-metal k3s join
3. **Phoenix** — full or partial cell recovery from phoenix playbook + KeePass-gated scripts
4. **Assess** — Tier 1/2/3 collectors feed bootstrap-state.json; readiness scorer (ACS/RRS/DCS/CRS/OSS)
5. **Monitor** — continuous assessment, security scanning, capacity model, drift detection
6. **Remediate** — autonomous remediation engine with planner → queue → executor → policy loop

## Current milestone

**Audit findings resolution complete** (all HIGH, MEDIUM, LOW items resolved as of 2026-06-02).

Next milestone: Deploy to hardware — run `python3 proxmox-bootstrap/forge-planner.py` on a
real Proxmox host and forge the first cell.

## Key design decisions

- manifest.json is the contract between assessment layer and doc-gen layer
- doc-gen never reads raw collector files directly
- Field classification: AUTO / DERIVED / HUMAN / UNRESOLVED
- UNRESOLVED fields are never silently omitted (reason + guidance + impact always present)
- All HTML output is self-contained dark-theme (no external dependencies)
- Tier 1 assessment uses Python 3 stdlib only (no pip installs)
- Historical snapshots must be reproducible (same manifest → same docs)
- Service Contracts replace heuristics as primary dependency source
- Secret Registry tracks KeePass path references, never secret values
- DNS Registry eliminates [VM_IP] placeholders in recovery docs
- Every machine-readable manifest has a human-readable HTML counterpart (AD-047)
- Autonomous remediation requires explicit opt-in ("enable autonomous") + policy gate
- KeePass-gated actions (rotate-join-token, run-backup) require keepass_unlocked = True

## Observe → Decide → Act → Record → Validate

All generated documentation follows this methodology.
