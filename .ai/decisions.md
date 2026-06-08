# Architecture Decisions

## AD-001: Two-tier assessment model
**Date:** 2026-05-30
**Decision:** Split assessment into Tier 1 (bootstrap, minimal deps) and Tier 2 (full engine).
**Rationale:** Tier 1 must run on unknown hardware with no tooling installed.
Conflating the two creates unnecessary complexity and dependency risk for the bootstrap case.

## AD-002: manifest.json as doc-gen contract
**Date:** 2026-05-30
**Decision:** The doc-gen layer reads only manifest.json, never raw collector files.
**Rationale:** Decouples collection format from documentation format.
Collector output format can change without breaking doc-gen.

## AD-003: UNRESOLVED is a first-class field state
**Date:** 2026-05-30
**Decision:** Missing data is always surfaced as UNRESOLVED with reason, collection guidance,
and readiness impact. Never silently omit.
**Rationale:** Silent gaps are worse than visible gaps. An operator who sees a blank field
may assume it doesn't matter. An UNRESOLVED field with impact rating forces a decision.

## AD-004: Workbook/runbook examples are style templates only
**Date:** 2026-05-30
**Decision:** The Stage 01-12 ODS/ODT files demonstrate structure and methodology but are
not final implementations. Generated documents will follow their structure but populate
fields from assessment data.
**Rationale:** The examples were manually authored. Treating them as authoritative would
perpetuate manual documentation maintenance.

## AD-005: Historical snapshot reproducibility is a hard requirement
**Date:** 2026-05-30
**Decision:** Any historical snapshot must regenerate the documentation current at that time.
**Rationale:** Recovery documentation must be trustworthy. If we cannot reproduce what we
said the infrastructure looked like at a given point, we cannot trust the documentation.

## AD-006: Cloud-Init elevated to first-class Bootstrap State
**Date:** 2026-05-30
**Decision:** Cloud-Init user-data, network-config, and snippets are tracked in a
dedicated Bootstrap State repository as versioned, hash-verified managed assets.
**Rationale:** Without Cloud-Init metadata in repository state, first-boot provisioning
cannot be replayed during reconstruction. The provisioning gap is the primary obstacle
to automated disaster recovery.

## AD-007: Service Contracts replace heuristics as primary dependency source
**Date:** 2026-05-30
**Decision:** Declared Service Contracts (YAML files per service) are the primary source
of dependency graph edges. Name-pattern heuristics are retained as a fallback only.
**Rationale:** Heuristics based on VM name patterns are unreliable for novel service
names and produce incorrect restore sequences. Declared contracts are authoritative.

## AD-008: Secret Registry tracks references, never values
**Date:** 2026-05-30
**Decision:** The Secret Registry is a YAML file in the Bootstrap State repository that
maps secret identifiers to KeePass paths. It never contains secret values.
**Rationale:** Enables automated gap detection and pre-populated recovery steps
(operator knows exactly which KeePass entry to open) without creating a secret-in-repo
security risk.

## AD-009: DNS Registry eliminates [VM_IP] placeholders
**Date:** 2026-05-30
**Decision:** A DNS Registry maps hostnames to IPs for all VMs. Doc-gen reads the
registry and pre-populates commands with actual IP addresses.
**Rationale:** `[VM_IP]` placeholders require operator lookup during recovery, which
adds time and creates opportunities for error. Known values should always be pre-filled.

## AD-010: Three documentation classes (bootstrap, operational, recovery)
**Date:** 2026-05-30
**Decision:** Documentation is produced in three independent classes from the same
metadata model: Bootstrap (construction), Operational (administration), Recovery
(reconstruction). Previously only Bootstrap and Recovery existed.
**Rationale:** Operational documentation is a distinct use case (running environment
administration) that cannot be served by either bootstrap or recovery documentation.
Drift summaries and capacity trends have no place in a recovery runbook.

## AD-011: Deployment Provenance Records enable reproducible reconstruction
**Date:** 2026-05-30
**Decision:** Each VM deployment creates a Provenance Record capturing: tofu workspace
commit, cloud-init snippet hashes, ansible playbook commit, ansible inventory commit,
base template checksum, deployment timestamp and operator.
**Rationale:** Without a build receipt, reconstruction cannot be validated as equivalent
to the original deployment. Provenance records are the "replay tape" for automation.

## AD-012: Reconstruction Playbooks are generated artifacts
**Date:** 2026-05-30
**Decision:** Reconstruction Playbooks (executable shell scripts for full-destroy
reconstruction) are generated from the state model, not manually authored.
**Rationale:** Manually authored reconstruction scripts diverge from actual state.
Generated scripts are always consistent with the current state model.

## AD-013: Infrastructure Cell is the primary architectural object
**Date:** 2026-05-31
**Decision:** Infrastructure Cell replaces the implicit single-environment assumption.
Every schema carries `cell_id` as a mandatory field. Every assessment, every generated
output, every state document is cell-scoped.
**Rationale:** Single-environment assumptions cannot be patched into federation capability.
The cell concept must be foundational. Adding it as a retrofit creates a structural
discontinuity that breaks schema compatibility and forces re-architecture of all consumers.

## AD-014: Federation is a first-class object, not an extension
**Date:** 2026-05-31
**Decision:** Federation State, the capability index, the recovery relationship graph,
and the inter-cell trust model are managed as first-class architectural objects with
their own schemas (federation-state-schema.json), their own assessment tier (Tier 3),
and their own documentation class (Federation Workbook + Runbook).
**Rationale:** Federation relationships are too complex and too critical to model as
secondary attributes of cell state. The recovery graph, capability index, and trust
model each require independent query, update, and verification paths.

## AD-015: Recovery State removed from the state model
**Date:** 2026-05-31
**Decision:** Recovery State (workbooks, runbooks, readiness reports, reconstruction
playbooks) is reclassified from a state category to a documentation output class.
**Rationale:** Category error in v4.0. Infrastructure does not "have" recovery state
the way it has declared state. Recovery documentation is generated OUTPUT from the
seventeen genuine state categories. Conflating the two creates confusion about
authoritativeness (infrastructure state is authoritative; generated output is derived)
and about update mechanisms (state is collected; output is generated on demand).

## AD-016: Seventeen state categories replace seven
**Date:** 2026-05-31
**Decision:** The state model expands from seven to seventeen categories. New: Hardware
State, Platform State, Cluster State, Storage State, External Dependency State, Data
Protection State, Observability State, Secret Reference State (standalone), Capability
State, Federation State.
**Rationale:** The seven-category model cannot support hardware-level reconstruction
(no Hardware or Platform State), cluster-aware recovery (no Cluster State), external
dependency tracking (no External Dependency State), capability-based recovery planning
(no Capability State), or cross-cell recovery coordination (no Federation State).
Each gap represents a real scenario where the previous architecture produces incomplete
or incorrect recovery documentation.

## AD-017: Five dependency graph types with distinct semantics
**Date:** 2026-05-31
**Decision:** The architecture maintains five dependency graphs: Operational, Recovery,
Trust, Execution, and Failure Domain. Each is stored and traversed independently.
**Rationale:** Conflating operational dependencies with recovery dependencies produces
incorrect recovery sequencing. Cell A may operationally depend on Cell B's DNS while
Cell B holds Cell A's backups — these are different graphs with different traversal
requirements. Failure domain propagation requires a third graph that models blast radius,
not operational requirements. Trust and execution dependencies are required for federated
reconstruction planning and cannot be derived from operational graphs.

## AD-018: Capability State enables dynamic recovery planning
**Date:** 2026-05-31
**Decision:** Each cell declares its capabilities (compute, storage, execution, network,
assessment). Capabilities are verified at Tier 2 assessment. The capability index is
maintained at federation scope and used by reconstruction planners to identify which
available cell can assist recovery.
**Rationale:** Without a verified capability index, federated reconstruction planning
must assume capabilities or discover them dynamically during a disaster — the worst
possible time for discovery. Declared and verified capabilities enable recovery plans
to be generated and validated before they are needed.

## AD-019: Tier 3 Federation Assessment
**Date:** 2026-05-31
**Decision:** A Tier 3 assessment tier covers federation-scope state: trust relationship
verification, capability verification, cross-cell recovery relationship testing, and
federation readiness scoring. It runs from a designated assessment cell with
federation-scope trust relationships.
**Rationale:** Tier 1 and Tier 2 assess single cells. Neither can verify cross-cell
relationships. Federation readiness requires exercising trust and recovery relationships
to confirm they function — not merely that they are declared. A declared trust
relationship that fails in practice is worse than no relationship (it creates false confidence).

## AD-020: Digital Twin is the authoritative source for all generated outputs
**Date:** 2026-05-31
**Decision:** All documentation, all readiness reports, and all reconstruction playbooks
are generated from the Digital Twin. The twin is updated by assessment, repository
ingestion, deployment events, and operator declaration. No output is manually authored.
**Rationale:** Manually authored documentation diverges from reality. Generated
documentation is always consistent with the current twin state. Reproducibility (same
state → same output) is guaranteed by the twin's deterministic generation model. The
twin also provides a single query target for all consumer tools, eliminating the need
for each tool to aggregate state from multiple sources independently.

## AD-021: Staleness is a first-class field confidence level
**Date:** 2026-05-31
**Decision:** STALE is added as a field confidence level alongside DECLARED, OBSERVED,
DERIVED, INFERRED, HUMAN, and UNRESOLVED. Each state category has a declared staleness
threshold (Hardware: 30 days; Observed: 7 days; Data Protection: 1 day). Fields past
their threshold are marked STALE in the twin and in all generated outputs.
**Rationale:** UNRESOLVED means a field was never populated. STALE means it was
populated but may no longer be current. These require different remediation: UNRESOLVED
requires collection; STALE requires re-verification. An operator making recovery
decisions needs to know whether they are working with never-collected data (UNRESOLVED)
or potentially-outdated data (STALE). Conflating the two is a safety issue.

## AD-032: Infrastructure Assessment Engine as first-class subsystem
**Date:** 2026-05-31
**Decision:** The Assessment Engine is a separate k3s subsystem from the Documentation
Engine, with its own Deployment (API server), PostgreSQL StatefulSet, and five assessor
CronJobs. Five categories: Resource Health, Architectural Drift, Recovery Readiness,
Documentation Coverage, Placement Compliance.
**Rationale:** Documenting what is and evaluating whether what is is correct are
different concerns. Conflating them produces a system that does both poorly.

## AD-033: Five scoring dimensions with composite Platform Health Score
**Date:** 2026-05-31
**Decision:** ACS (Architecture Compliance), RRS (Recovery Readiness), DCS
(Documentation Coverage), CRS (Capacity Risk), OSS (Operational Stability) aggregate
into composite PHS. Scores use weighted averages with absolute blockers.
**Rationale:** Without scores and thresholds, the platform produces documentation
but provides no signal about whether anything needs attention.

## AD-034: Phase 1 rebalancing is detect/document/recommend only
**Date:** 2026-05-31
**Decision:** The Assessment Engine never takes autonomous infrastructure action.
Phase 2 automation is deferred to after Phase 12 and requires defined safeguards.
**Rationale:** Autonomous infrastructure actions can cause downtime, have cascading
effects, and must have tested rollback paths. These prerequisites take time to build.

**Amendment (2026-06-07 — see AD-040):** The line above ("never takes
autonomous infrastructure action") overstated the original intent and is
revised. **Operative phrasing, going forward:** *Broodforge MAY take
autonomous infrastructure action, provided it is bounded by defined
safeguards and recoverable* — i.e., exactly the two preconditions this
entry's own Rationale already named ("must have tested rollback paths,"
"these prerequisites take time to build") as the thing Phase 2 automation
was waiting on. Phase 26's policy-gated, opt-in, dry-run-comparing,
rollback-capable remediation engine is the realization of that
precondition being met — not a violation of this decision, properly read.
The original Date/Decision/Rationale lines above are left intact as the
historical record of what was decided on 2026-05-31 (and of the reasoning
that, followed through to its own conclusion, now licenses this amendment);
nothing here erases or contradicts them — it completes the thought they
left open ("requires defined safeguards" → safeguards now exist → action
is now licensed, exactly as this entry always said it would be once they did).

## AD-035: intelligence/ namespace deploys before applications/ namespace
**Date:** 2026-05-31
**Decision:** All intelligence-layer workloads (documentation engine, assessment engine,
recovery generator) must be Running and healthy before any user application is deployed.
Enforced by Flux CD dependency declarations. Gate: PHS >= 80.
**Rationale:** The platform must understand itself before hosting workloads.
An undocumented platform cannot be recovered reliably.

## AD-036: Failure packages are generated before script exit
**Date:** 2026-05-31
**Decision:** failure-package.sh is sourced at the top of every recovery script.
Error traps fire failure package generation before exit. Failure analysis capability
must not itself fail.
**Rationale:** The failure package is the input to the self-improvement loop.
Losing it because the generation code ran after the error means losing the data
needed to fix the problem.

## AD-037: ODS updates are atomic with plaintext fallback
**Date:** 2026-05-31
**Decision:** Every ODS update creates a backup, modifies a temp file, validates the
temp file, then atomically replaces the original. If ODS update fails, recovery
continues and logs to recovery-fallback.log.
**Rationale:** The audit trail is important; recovery is more important.

## AD-038: Documentation commits are batched to reduce Git noise
**Date:** 2026-05-31
**Decision:** Documentation Engine batches commits with a minimum 10-minute interval.
Assessment reports have a dedicated repository (docs-assessments/) separate from
architectural documentation.
**Rationale:** Frequent automated commits to a shared repository create noise that
obscures human-authored changes and makes git log unusable for review.

## AD-039: Codebase-development session-continuity practice transitions to PAP
**Date:** 2026-06-07
**Decision:** Broodforge's own pre-PAP prototype mechanisms for tracking
codebase-development continuity — `.ai/AI_AGENT_BOOTSTRAP.md`'s hand-built
"read in this order" bootstrap and `docs/SESSION-HANDOFF.md`'s rolling
session-progress log — are retired in favor of PAP-State's formally-specified
equivalents (Startup Protocol §1, Project Resume Block §3, Session Handoff
Protocol §4), now instantiated at `pap/state/RESUME_BLOCK.md` and
`pap/state/SESSION_HANDOFF.md`. `docs/SESSION-HANDOFF.md` is moved (`git mv`,
full history preserved), not deleted, to `docs/deprecated/SESSION-HANDOFF.md`,
with an in-place banner pointing forward; `.ai/AI_AGENT_BOOTSTRAP.md` is
rewritten in place to route through the new artifacts and PAP's Startup
Protocol. Full rationale, evidence, and migration record:
[`pap/revisions/2026-06-07_session-continuity-transition-to-pap.md`](../pap/revisions/2026-06-07_session-continuity-transition-to-pap.md).
**Rationale:** Direct operator instruction, framed as a scope distinction:
broodforge's *revision protocol for its own codebase* (session-handoff,
progress-tracking — i.e., how development sessions on broodforge's source are
picked up and handed off) is a different concern from broodforge's
*remediation process for failing nodes and the general functions it
performs* (the platform's own product behavior — assessment, forging,
spawning, phoenix recovery, autonomous remediation). The former is exactly
the kind of durable-continuity practice PAP exists to formalize; the latter
remains entirely broodforge's own, governed by `.ai/PROJECT_CHARTER.md` and
the rest of the `.ai/` corpus, untouched by this decision
(`PAP_CHARTER.md` §2.3 — PAP's analytical reach does not extend into, and
this decision does not cede, broodforge's own constitutional authority over
its product). Verified before acting: neither retiring artifact's name or
content had crept into `.ai/PROJECT_CHARTER.md` itself (it is 269 bytes —
Purpose plus four SHALL / four SHALL-NOT lines — and names neither).
**Consequences:** Future codebase-development sessions read
`pap/state/RESUME_BLOCK.md` and `pap/state/SESSION_HANDOFF.md` (per the
rewritten `.ai/AI_AGENT_BOOTSTRAP.md`), not `docs/SESSION-HANDOFF.md`. The
full pre-transition session history (1142 lines, "Previous Session Work"
through "Architecture Notes") remains intact and readable at
`docs/deprecated/SESSION-HANDOFF.md` and via `git log --follow`.

## AD-041: `new/` proposed-revision corpus analyzed and triaged; one item (Pre-Install Forge Package and Image Builder) integrated as proposed Phase 1.H

**Date:** 2026-06-07
**Decision:** The previously-untracked `new/` directory (~165 `.docx`/`.pdf`
documents — chapters, specifications, RFCs, and a separate formal
"axiomatic-kernel" proof series — flagged as ungoverned by PAP-AUDIT finding
F3) has been read, triaged, and selectively integrated, per direct operator
instruction: *"Analyze the `new/` directory ... and integrate relevant
content into the roadmap and architecture... Good candidates to integrate:
anything about pre-install forge package creation ..., any management
tooling, monitoring, orchestration, or documentation generation features
[...] Some sections get into highly speculative, philosophical territory
(e.g., cross-civilization knowledge transfer, 100-year planning scenarios).
Do NOT deeply integrate or analyze those — defer them."*

One concretely-implementable, additive gap surfaced cleanly: Chapter 16
("Bootstrap and First-Node Architecture"), Specification 70 ("Bootstrap Forge
Package and First-Node Deployment"), and Specification 148 ("Canonical
Bootstrap and First-Node Genesis Framework") all name the same unsolved case
— *"A BroodForge environment should be creatable without requiring an
existing BroodForge deployment"* and an "Image Builder Architecture" that
"may generate ISO images, USB installation media... derived from
infrastructure knowledge." Broodforge's actual `FORGING.md` still lists
"Proxmox VE installed on the target host" as a hard prerequisite — the forge
manifest is generated entirely on the operator's workstation, but the forge
package itself still requires an already-installed host to land on. This gap
is now recorded as proposed (not started) **Phase 1.H — Pre-Install Forge
Package and Image Builder** in `ROADMAP.md`'s new "Proposed Future Work —
from `new/` corpus analysis" section, and as **AD-057** in `ARCHITECTURE.md`
(architecture-level decision record with full proposed scope).

Three other named areas — Documentation Engine (Spec 60), Runbook Generation
(Spec 82), Reference UI/Knowledge Visualization (Spec 88), Reference API/CLI
(Spec 87) — were checked against the existing codebase (`doc-gen/`,
`dependencies.py`, `capability_state.py`, `failure_domain.py`, Phase 9/10)
and found already substantially implemented; recorded in `ROADMAP.md` as
"already covered, no gap" rather than silently dropped.

The remainder — federation/economic/marketplace/trust-scoring specifications
(138–145), knowledge-civilization/century-scale/succession specifications
(116–132), an entire parallel "RFC-graph self-governance" architecture series
(Coherence Dashboard, Master Control Plane, Unified System Orchestration
Kernel, Global Coherence Ledger, Bootstrap Order Generator, Post-Bootstrap
Verification Framework — these govern *the specification corpus itself as a
system*, a different problem than the one broodforge actually solves), and a
separate formal "axiomatic kernel" / category-theoretic proof PDF series
(v1.5–v1.27) — is **explicitly deferred**, named individually in `ROADMAP.md`
"What was deferred and why," not as a quality judgment on the material but
because it describes a substantially larger and differently-scoped system
than broodforge's charter (a Proxmox/k3s home-lab infrastructure platform).
Notably, `new/broodforge.json` itself frames the corpus as a
`fidelity_translation_only` handoff that forbids "architecture_simplification...
spec_rewrite... semantic_reinterpretation" — i.e., it asks to be implemented
verbatim as a parallel system, which is the opposite of "mine me for ideas
that fit the existing architecture," reinforcing that selective triage (not
wholesale adoption) was the correct posture.

**Rationale:** PAP-AUDIT finding F3 named two real risks in leaving `new/`
as an untracked, ungoverned directory: (a) **loss** — a `git clean` or
careless `.gitignore` edit could destroy ~165 documents with no recovery
path; (b) **silent scope ambiguity** — `.ai/NEXT_STEPS.md`'s "all phases
complete" claim and the corpus's much larger implied trajectory would diverge
further every day the question of "is this broodforge's future, or not?"
went unanswered. Direct operator instruction (with scoping criteria supplied
up front) resolved both: the corpus is now referenced from governed artifacts
(`ROADMAP.md`, `ARCHITECTURE.md`, `.ai/NEXT_STEPS.md`, this file, the audit's
F3 Resolution annotation, `pap/state/SESSION_HANDOFF.md`), and a durable,
named record now exists of exactly what in it is — and is not — part of
broodforge's forward direction, closing the ambiguity for any future reader.

**Consequences:** `new/` remains in the working tree (untracked is now a
choice, not an oversight — the operator may commit it, archive it, or leave
it as reference material; that decision was not asked of this analysis and is
not made here). One new proposed roadmap item exists, **Phase 1.H**, ready
to be picked up in a future development session at the operator's discretion
— it is *not* queued or scheduled. PAP-AUDIT finding F3 is now CLOSED (see
`pap/audits/2026-06-07_broodforge-pap-audit.md`'s in-place Resolution
annotation and updated status banner). Full record:
`ROADMAP.md` "Proposed Future Work — from `new/` corpus analysis",
`ARCHITECTURE.md` AD-057, `.ai/NEXT_STEPS.md`, `pap/state/SESSION_HANDOFF.md`
and `pap/state/RESUME_BLOCK.md`.

## AD-040: Charter SHALL-NOT scope clarified; AD-034 phrasing amended to license safeguarded autonomous action
**Date:** 2026-06-07
**Decision:** Two coordinated clarifications of original intent — made
together because both resolve ambiguity the same review surfaced
(PAP-AUDIT findings F1 and F2,
[`pap/audits/2026-06-07_broodforge-pap-audit.md`](../pap/audits/2026-06-07_broodforge-pap-audit.md)),
and both are recorded *in place*, alongside the original text they clarify,
rather than as silent rewrites:

1. **`PROJECT_CHARTER.md`'s SHALL-NOT list gains a Scope note** (added
   in-place, original four items left intact): "Recommend upgrades /
   purchases / replacements" and "Make subjective judgments" name
   *specific-hardware* recommendations — what product or component to buy,
   add, or swap into a node — which would require granular product-and-
   pricing knowledge out of this project's scope. They do not bound the
   platform's own resource-provisioning / deployment-strategy decisions for
   infrastructure it manages (a broad function of its chartered deployment
   strategy — see AD-013/AD-014/AD-032 — not a "subjective judgment" in the
   excluded, hardware-specific sense).
2. **AD-034 gains an in-place Amendment** (original Date/Decision/Rationale
   left intact as the historical record): its absolute phrasing ("never
   takes autonomous infrastructure action") overstated original intent.
   Operative rule, going forward: autonomous infrastructure action is
   licensed *provided it is bounded by defined safeguards and recoverable* —
   precisely the precondition AD-034's own Rationale already named as the
   thing "Phase 2 automation" was waiting on, and precisely what Phase 26's
   policy-gated, opt-in, dry-run-comparing, rollback-capable remediation
   engine now provides.

**Rationale:** Direct operator clarification of original intent, given
verbatim in response to PAP-AUDIT F1/F2 (quoted in full in
[`pap/audits/2026-06-07_broodforge-pap-audit.md`](../pap/audits/2026-06-07_broodforge-pap-audit.md)'s
Resolution annotations): *"the subjective judgements language was regarding
any suggestions of hardware changes or upgrades, or what to put into a
second node, etc., since this is outside the scope of the project... [an
auto-suggest mechanism for] how to provision resources within an existing
node or a new node... is more a broad function of its deployment strategy,
not a suggestion mechanism for specific hardware (which would require very
granular information about specific pc products, pricing databases, etc.
that is outside the scope of what this project should do)"* and *"autonomous
action is ok in some cases, as long as bounded by safeguards and
recoverability for autonomous actions that might go wrong. if the exact
phrasing needs revision, then do so to account for this."*
**Consequences:** Closes PAP-AUDIT findings F1 and F2 — both were genuine
*ambiguities* in the governing text (confirmed directly by the document's
own author/owner, who is the only authority able to resolve what its
original intent was), not contradictions between the text and the system;
the text, not the system, needed correcting, and now has been — in place,
annotated, with the original wording preserved as the historical record of
what was first written and why it needed this clarification.

## AD-059/AD-060/AD-061: Three Roadmap draft sketches promoted to scoped phases (Recovery-Readiness Conformance, Hypervisor Recovery Credentials, Granular Secret Access Silos)
**Date:** 2026-06-08
**Decision:** The operator reacted to all three draft sketches recorded in
`ROADMAP.md` "Proposed Future Work" (added 2026-06-07) with explicit,
scoped decisions, promoting each from "draft for discussion" to a numbered
phase plus an architecture decision record:

1. **Recovery-Readiness Conformance → Phase 1.I**, AD-059. Scope: a
   `recovery-readiness-certificate.json`/HTML generator bundling manifest
   hash, graph hash, readiness score, drift summary, and latest drill result
   — built as additive extensions to existing `readiness.py`, `drift.py`,
   `dependencies.py`, the snapshot/provenance store, and Phase 12 drills. No
   cryptographic root-of-trust apparatus or formal certification levels.
2. **Hypervisor Recovery Credentials → Phase 1.J**, AD-060. The operator
   **explicitly ruled out any autonomous pathway that can read and wield
   full root credentials against live hypervisors** — recorded as a firm
   architectural constraint (a SHALL-NOT, not a negotiable middle ground),
   because root has no boundary by definition and an autonomous pathway
   wielding it would convert any compromise of that one pathway into root on
   every hypervisor in the cell at once. Two narrow exceptions are explicitly
   allowed, both bounded to a single node's *temporary*, soon-discarded
   credential: (a) node spawning (already in place via Cloud-Init), and
   (b) phoenix recovery packages — extending the same temporary-credential
   pattern to the phoenix setup phase, with a hard requirement (recorded in
   the generated runbook) that the operator rotates the credential once the
   session completes. The three-part middle path from the original sketch
   (forced-command recovery accounts, human-unlock break-glass root,
   pre-generated spawn-media credentials with human authorization) is
   **accepted as stated** and recorded as Phase 1.J's implementation targets.
3. **Granular Secret Access Silos → Phase 1.K**, AD-061. The
   "multiple derived vaults" design is kept as sketched, expanded with two
   operator-directed refinements: (a) higher-tier vaults must record the
   access credentials for lower-tier scopes, so a god-mode operator can
   always recover a scoped vault's passphrase from their own vault (a "vault
   of vaults," generalizing the AD-044 per-backup unique-secret bookkeeping
   pattern); (b) a mechanism for creating users at the VM level and the
   Proxmox level, with default templates corresponding to the proposed scope
   divisions, each provisioned with access to its scoped vault.

**Rationale:** Each sketch was written specifically to be reacted to —
"draft for discussion / not yet a phase / not yet an AD," explicitly awaiting
operator direction before promotion (see `pap/state/RESUME_BLOCK.md`'s
`next_action`, fifth/sixth milestones: "let the operator react, not
pre-emptively promote any of them"). The operator's direct, itemized
decisions on all three close that open thread cleanly — each sketch is
promoted to exactly the scope the operator specified, with the same
phase-plus-AD pattern Phase 1.H/AD-057 established, and with the operator's
own expansions (vault-of-vaults recordkeeping, user-provisioning templates,
the firm root-credential constraint and its two named exceptions) folded in
verbatim rather than re-interpreted.

**Consequences:** `ROADMAP.md` "Proposed Future Work" now contains three
scoped, numbered, *proposed-but-not-started* phases (1.I, 1.J, 1.K) alongside
the existing Phase 1.H, each with a "Proposed scope" checklist and a
reference to its AD; `ARCHITECTURE.md` gains AD-059, AD-060, and AD-061
(placed in sequence after AD-058, ahead of the closing rationale line).
AD-060 in particular establishes a constraint binding on *all* future
development, not just Phase 1.J's own scope — any later proposal for an
autonomous pathway touching hypervisor root credentials must be evaluated
against it, and the two named exceptions (node spawning, phoenix) are the
only ones currently sanctioned. None of the three phases is started; all
remain candidates for a future development session at the operator's
discretion, the same as Phase 1.H.
