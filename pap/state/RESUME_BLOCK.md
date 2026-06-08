# Project Resume Block — broodforge

Instance of [PAP-State §3](../modules/PAP-State/PAP-State.md#3-project-resume-block)
(Project Resume Block), conforming to
[`resume-block.schema.yaml`](../modules/PAP-State/schemas/resume-block.schema.yaml).
This is **broodforge's own** resume block — a record of *broodforge's
codebase-development continuity*, governed going forward by PAP per
[`pap/revisions/2026-06-07_session-continuity-transition-to-pap.md`](../revisions/2026-06-07_session-continuity-transition-to-pap.md).
It is not, and does not describe, broodforge's *infrastructure remediation*
function (planner/queue/executor/policy) — that is the platform's product
behavior, not its development process, and is out of scope for this artifact
(see that transition record's "What this transition is — and is not" section).

---

- **project_identity**: Broodforge — a self-managing infrastructure platform
  for home-lab Proxmox + k3s environments (hardware assessment, cell forging,
  node spawning, phoenix recovery, continuous health monitoring, autonomous
  remediation). Six-layer lifecycle, seventeen-state model, three assessment
  tiers, five dependency-graph types. Architecture v7.1+. (Source:
  `.ai/context.md`, `.ai/CURRENT_STATE.md`.)

- **active_objective**: No implementation work is currently active. Per
  `.ai/NEXT_STEPS.md` and `.ai/CURRENT_STATE.md`, all roadmap milestones and
  all four planned intelligence tracks (through Phase 26 — Autonomous
  Operations) are complete, and the last `docs/SESSION-HANDOFF.md` entry
  (now superseded — see the transition record) named the platform's own next
  action as **"deploy to hardware"** (`python3 proxmox-bootstrap/forge-planner.py`
  on a real Proxmox host; see `FORGING.md`). One *proposed* (not-started)
  development item now exists in `ROADMAP.md`: **Phase 1.H — Pre-Install
  Forge Package and Image Builder** — surfaced by the (now-completed) `new/`
  corpus analysis. Three more items exist at an earlier stage — **draft
  sketches** (not yet scoped phases): "Recovery-Readiness Conformance"
  (reframing the formal axiomatic-kernel/proof-system series the operator
  partially un-deferred), "Hypervisor Recovery Credentials" (the operator's
  requested thorough evaluation of permanent Proxmox-root-password storage —
  written up as a recommendation against an autonomous full-root pathway,
  with a constrained-account/break-glass/pre-generated-media middle path),
  and "Granular Secret Access Silos for Human Operators" (the operator's
  question about tiered, hierarchically-scoped secret access for humans —
  "god mode" confirmed as the right homelab default, with a sketch of how
  scoped sub-vaults could be derived from the canonical KeePass DB for a
  larger-org future). See `active_risks` and `key_decisions_and_insights` in
  `SESSION_HANDOFF.md` for the full record of all four. All are candidates
  for a future session, not mandates — the three draft sketches additionally
  await operator reaction before any can become a candidate phase.

- **active_milestone**: Post-Phase-26, pre-hardware-deployment, post-`new/`-
  analysis, **mid-draft-sketch-thread** (three sketches now written —
  Recovery-Readiness Conformance, Hypervisor Recovery Credentials, Granular
  Secret Access Silos — all awaiting operator reaction). A
  doc-self-consistency gap the operator spotted by inspection (`ROADMAP.html`
  / `docs/ARCHITECTURE.html` stale relative to their `.md` sources, by up to
  five days) was also closed this session via a new drift-detection test,
  `tests/unit/test_meta_doc_sync.py`. The intelligence/development side of
  the project is feature-complete per its own governance corpus; the next
  milestone named in that corpus is an *operational* one (a real hardware
  run), not a development one — though `ROADMAP.md` now also names one
  *proposed* development item (Phase 1.H) and three *draft* items (the
  sketches above) for whenever the operator chooses to engage with them.

- **active_risks**:
  - **(Updated 2026-06-07, second milestone — F1 and F2 now CLOSED):** The
    `pap`-driven audit recorded in
    [`pap/audits/2026-06-07_broodforge-pap-audit.md`](../audits/2026-06-07_broodforge-pap-audit.md)
    originally named three open, non-blocking findings. Two are now resolved
    by direct operator clarification of original intent, recorded as in-place
    annotations (nothing silently rewritten — originals preserved):
    - ~~F1 (Charter Purpose/SHALL-NOT text reads as broader than the system
      that exists)~~ — **CLOSED**. The operator clarified the SHALL-NOT
      list's "subjective judgments"/"recommendations" language always meant
      *specific-hardware* recommendations (product/pricing-database-grade
      calls, out of scope), not the platform's own resource-provisioning /
      deployment-strategy decisions for infrastructure it manages. Recorded
      as an in-place Scope note on `.ai/PROJECT_CHARTER.md` and `AD-040`.
    - ~~F2 (AD-034's "never takes autonomous action" boundary reads as
      crossed by Phase 26, with no decision record marking the crossing)~~ —
      **CLOSED**. The operator clarified autonomous action was always meant
      to be acceptable *when bounded by safeguards and recoverability* —
      AD-034's phrasing was under-specified, not the system's behavior wrong.
      Recorded as an in-place Amendment on `AD-034` and `AD-040`.
    - Both were genuine **textual ambiguities**, not real contradictions
      between governing text and built system — resolvable only by the
      documents' own author stating original intent, exactly as the audit's
      own Falsification perspective had hedged might be the case. See
      `pap/state/SESSION_HANDOFF.md`'s `key_decisions_and_insights` for the
      fuller account, and the audit record's own "Status update" banner and
      per-finding "Resolution" annotations for the canonical record.
  - **F3 — initially deferred, now CLOSED.** The untracked `new/` directory
    (~165 proposed-revision documents, not ~25 — the smaller count was an
    early estimate from filenames alone) was first explicitly deferred by
    the operator ("this is deferred for the moment"), then **explicitly
    un-deferred** by a later, separate, scoped instruction ("Analyze the
    `new/` directory ... and integrate relevant content into the roadmap and
    architecture" — with built-in guidance on what to integrate vs. defer).
    That analysis is done: **one** concrete, additive item was integrated
    (proposed **Phase 1.H — Pre-Install Forge Package and Image Builder**,
    in `ROADMAP.md` + `ARCHITECTURE.md` AD-057); three other named areas were
    checked and found already implemented; the rest — federation/
    civilization/century-scale specs and a parallel "RFC-graph
    self-governance" architecture series plus a formal axiomatic-kernel proof
    series — was explicitly named and deferred as out of scope for
    broodforge's actual product. See `SESSION_HANDOFF.md`'s third
    `milestone_checklist` block and the audit's F3 "Resolution" annotation
    for the full record. **Do not re-run this analysis** — read its output.
  - **(Added same day, follow-up to F3 closure — not itself a finding, an
    open thread):** The operator partially walked back the formal
    axiomatic-kernel deferral above — not asking to implement it, but
    observing that beneath its category-theoretic framing it names two real
    concerns (provable recovery readiness; observed-state ↔ intent-manifest
    conformance) and asking for a draft of "what to do with these." A
    **DRAFT SKETCH** ("Recovery-Readiness Conformance") now lives in
    `ROADMAP.md`'s "Proposed Future Work" section: a translation table
    mapping each formal construct to the broodforge mechanism that already
    plays its role informally, plus identification of **one** genuinely new
    artifact worth scoping further (a `recovery-readiness-certificate.json`
    composing existing scores/hashes/drill results). It is explicitly marked
    draft / not a phase / not an AD — **awaiting operator reaction** before
    promotion. Re-running the 13-PDF read is unnecessary; the sketch is the
    distilled output.
  - F4 (an OBSERVATION, not a finding requiring action) stands as recorded —
    see the audit's status banner.
  - One deferred technical item from the prior (now-superseded)
    `docs/SESSION-HANDOFF.md`: "(A1) sys.path coupling in html workbooks +
    collect_tier2 that import from doc-gen/renderers via sys.path.insert —
    requires package restructure into a proper Python package. Low urgency —
    works correctly today."

- **blockers**: None known. (No BLOCKER-classified finding exists in the most
  recent PAP-AUDIT of broodforge; broodforge's own `docs/AUDIT-FINDINGS.md`
  cycles likewise show no open blocking item as of the last entry.)

- **next_action**: **(Updated — three draft sketches now written;
  awaiting operator reaction; this supersedes earlier framing for the
  *draft-sketch* thread.)** `ROADMAP.md` "Proposed Future Work" now holds
  three sketches — Recovery-Readiness Conformance, Hypervisor Recovery
  Credentials, and Granular Secret Access Silos for Human Operators — each
  written because the operator asked a specific question and invited a
  draft/evaluation. The correct next move for all three is the same: **let
  the operator react**, not pre-emptively promote any of them to a phase or
  an AD. If the operator confirms a direction on one (e.g., "scope the
  certificate idea," "build the constrained recovery accounts," "the silo
  idea is worth keeping on the roadmap for later"), write *that one* up the
  same way Phase 1.H was (scoped roadmap entry + AD in `ARCHITECTURE.md` +
  `.ai/decisions.md`) — without touching the others. If the operator
  redirects or narrows any sketch, edit it in place rather than starting a
  parallel one. Separately — and already done, not a pending action — a
  **doc-self-consistency gap** the operator spotted by inspection
  (`ROADMAP.html` / `docs/ARCHITECTURE.html` stale by up to five days
  relative to their `.md` sources, plus `ARCHITECTURE.md`'s own header
  stale relative to its body) was closed via a new test,
  `tests/unit/test_meta_doc_sync.py`, which now keeps this honest going
  forward — a resuming agent does not need to re-check this by hand; trust
  the test. Beyond that thread: for whoever picks up broodforge's
  *codebase-development* thread generally (as distinct from its
  *operational* deployment thread, which `FORGING.md` already governs) —
  there is no other mandatory development action, and no open audit finding
  remains that requires one (F1/F2/F3 closed, committed; F4 is an observation
  requiring no action). **Phase 1.H, Pre-Install Forge Package and Image
  Builder** also remains a **proposed** (not mandatory) candidate. A
  resuming agent should: (a) wait for/follow new operator direction (which
  may be reaction to the draft sketch, "start Phase 1.H," "deploy to
  hardware," or something else entirely), or (b) — only if asked to find
  something to do — offer the draft sketch's open question, Phase 1.H, or
  the platform's own named *operational* next step, "deploy to hardware"
  (see `active_objective`, above, and `FORGING.md`).
  ~~triage the three open audit findings above (F1–F3)~~ — superseded: all
  three are closed.

---

## Provenance

Created as part of
[`pap/revisions/2026-06-07_session-continuity-transition-to-pap.md`](../revisions/2026-06-07_session-continuity-transition-to-pap.md) —
the transition that moved broodforge's own session-continuity practice from
its pre-PAP prototype mechanisms (`.ai/AI_AGENT_BOOTSTRAP.md`,
`docs/SESSION-HANDOFF.md`) onto PAP-State's formally-specified Resume Block
and Session Handoff Protocol. Update this block at minimum at every session
boundary and at every major milestone, per the schema's `update_trigger`.
