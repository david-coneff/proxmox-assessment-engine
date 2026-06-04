# Broodforge Design History

**Status: durable record — not versioned.** This document replaces the versioned
`ARCHITECTURE-REVIEW-vN.md` series that the project iterated through during its
formative design phase (v4 → v7). Rather than continue minting a new full-text
review document at every architectural shift — each of which then had to be
deprecated and replaced — this single durable record traces *how* the design
arrived where it is and *why*, so future audits have the rationale trail without
the churn.

For the **authoritative current architecture**, see
[`ARCHITECTURE.md`](../ARCHITECTURE.md) and its Architecture Decision (AD-022…AD-056)
table. This document is history and rationale; `ARCHITECTURE.md` is truth.

The full text of each historical review is preserved verbatim in
[`deprecated/`](../deprecated/) for deep audits:
`ARCHITECTURE-REVIEW-v4.md`, `-v5.md`, `-v6.md`, `-v7.md`.

---

## Why the design evolved as it did

Broodforge began as a fairly conventional "provision some VMs with IaC" idea and
was deliberately reframed four times. Each reframe sharpened a single question:
*what is the platform's actual product?* The answer settled on **reconstruction**
— the ability to rebuild any component, or the whole cell, from repository state
after total loss. Every later decision is downstream of that answer.

---

## The four reviews — what each introduced and why

### v4.0 — Infrastructure Lifecycle & Reproducible Reconstruction *(2026-05-30)*

The first reframe. The prior thinking modeled infrastructure primarily as a set of
running VMs. v4 reframed it as a **reproducible lifecycle**: Cloud-Init for
first-boot identity, declarative state, and the explicit goal that the environment
be reconstructable rather than merely runnable. This is the origin of the
"reconstruction is the objective" principle.

### v5.0 — Federated Infrastructure Digital Twin *(2026-05-31)*

Commissioned with an explicit instruction not to assume the existing design was
correct. v5 introduced two ideas that survived everything after it:

- **Digital twin** — the platform maintains a continuously-updated model of its own
  state (later realized as `bootstrap-state.json` + the assessment engine).
- **Federation / cell scope** — `cell_id` as a universal, mandatory key on every
  schema document, so a federation layer can be added *above* without retrofitting
  *below*. This is why `cell_id` is a hard design constraint today.

### v6.0 — Self-Documenting, Self-Recovering Platform *(2026-05-31)*

A complete reset rather than an increment. v6 established the framing the project
still uses in its tagline and crystallized:

- **Documentation captures intent, not just state** — "3 control-plane nodes
  *because* HA policy requires etcd quorum at ≥3 hosts," not just the count.
- **Recovery packages** — self-contained, offline-capable, checkpoint-resumable
  archives as the unit of reconstruction (the seed of forge / spawn / phoenix).
- **Failure packages** — structured, LLM-optimized artifacts emitted on any script
  step failure, feeding a continuous-improvement loop.

### v7.0 → v7.1 — Self-Documenting, Self-Assessing, Self-Recovering *(2026-05-31 → 2026-06-02)*

v7 added the word **assessing** to the identity and made it concrete:

- **Assessment Engine as a first-class subsystem** with five scored dimensions
  (ACS, RRS, DCS, CRS, OSS) aggregating into a Platform Health Score (PHS).
- **The assessment engine recommends; humans act** — no autonomous infrastructure
  action without an explicit governance review (the safeguard later partially
  implemented in Phase 26's remediation policy).
- **Twelve-phase implementation roadmap** (now tracked in `ROADMAP.md`).
- **v7.1** added the three-process vocabulary that defines the platform today:
  **Forging** (bare metal → hatchery), the **Hatchery process** (spawn packages
  for broodlings), and the **Stargate process** (phoenix packages for resurrection),
  plus the Phase 12.E spawn-bootstrap that lets a broodling join after a bare
  Proxmox install without querying the hatchery API.

---

## Throughlines that survived every iteration

These are the invariants — present from the version that introduced them through to
the current implementation:

| Throughline | Introduced | Status today |
|---|---|---|
| Reconstruction is the objective | v4 | Core design principle #1 |
| `cell_id` mandatory; federation above, not retrofitted below | v5 | Hard schema constraint |
| Digital twin of own state | v5 | `bootstrap-state.json` + assessment engine |
| Documentation captures intent (what + why + policy) | v6 | doc-engine output requirement |
| Self-contained, checkpoint-resumable recovery packages | v6 | forge / spawn / phoenix packages |
| Failure packages feed an improvement loop | v6 | `failure_package_analyzer.py` + hatchery receiver |
| Assessment recommends; humans act | v7 | Phase 26 remediation governance gate |
| Forge / Hatchery / Stargate three-process model | v7.1 | The platform's operating model |

---

## Subsequent decisions that superseded parts of the reviews

A few decisions made *after* v7 was written supersede portions of its text. These
live in `ARCHITECTURE.md`'s AD table and take precedence over anything in the
deprecated review documents:

- **AD-055 — HTML is the sole generated-document format.** The reviews (notably v7)
  describe ODS/ODT workbooks and an `ods-update.sh` flow. That design was retired;
  the codebase generates self-contained HTML only. ODS/ODT renderers are preserved
  under `doc-gen/renderers/deprecated/` for reference.
- **AD-051 — every machine-readable manifest has an HTML equivalent.** Formalized the
  human-readable-companion pattern the reviews only gestured at.
- **AD-039 through AD-056** — the spawn/forge/phoenix package mechanics, network
  profiles, guided setup, backup architecture, and spawn-completion reporting were
  all specified in detail after the v7 prose and are authoritative in `ARCHITECTURE.md`.

---

*When the architecture next shifts, update `ARCHITECTURE.md`'s AD table and add a
short entry to this file — do not start `ARCHITECTURE-REVIEW-v8.md`.*
