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

- **active_milestone**: (Updated — sixth milestone, new session, 2026-06-08.)
  Resumed per the operator's "continue using PAP-state" instruction; found a
  prior session had left the AD-058 guided-setup gap (named at the end of the
  fifth milestone, below) **mid-flight as uncommitted edits** — completed it:
  `security.mfa_method` is now wired end-to-end, **guided setup → forge
  manifest → `KeePassInitConfig`** (`guided_setup.py` suggest/check_conflicts,
  `forge_planner.py build_forge_manifest()`, `forge_keepass_init.py
  generate_keepass_init_config()` — the last of which had computed the value
  but never passed it to the returned config; that one missing line was the
  whole remaining gap). Added full test coverage
  (`test_guided_setup.py`/`test_forge_planner.py`, 6 new cases). While running
  the full suite to verify (standing practice before declaring done), found
  **one pre-existing failure unrelated to this work** —
  `test_phase19_federation.py::test_expiring_soon_still_valid` — confirmed via
  `git stash` it failed identically on untouched `main` (not a regression):
  `verify_trust()` in `federation_state.py` compared a real-wall-clock
  property (`relationship.is_expired` → `datetime.now(timezone.utc)`) against
  its own injected `now_fn`, so a fixture pinned to "now = 2026-06-01" with
  expiry "2026-06-08" started failing the moment real UTC crossed that date.
  Fixed it to compare against the injected `now` consistently (mirroring the
  correct pattern already used two lines below it for re-verification age).
  Recorded the full cycle in `docs/FEATURE-HISTORY.md`
  (`2026-06-08_12_36_41 UTC`) and regenerated its HTML twin. **Full suite:
  3844 passed** (was 3843 + 1 pre-existing failure — both now green, no
  regressions). See `SESSION_HANDOFF.md`'s `last_completed_step` for the
  complete account, including the named-but-deliberately-not-chased
  `datetime.now(`/`datetime.utcnow(` sweep candidate this surfaced.

  **Before this (fifth milestone, prior session, same day):** The
  operator reacted to the "Hypervisor Recovery Credentials" sketch
  (endorsing its constrained-recovery-account "middle path") and, in the
  same message, issued two further direct instructions, both now closed:
  (1) **AD-058** — second-factor auth (TOTP-authenticator or YubiKey only,
  *never* SMS/email) is now the **default**, not opt-in, for the KeePass
  unlock gate (`KeePassInitConfig.mfa_method` / `--mfa` flipped `"none"` →
  `"totp"`; the mechanism — `keepass_mfa.py` — already existed, fully
  tested, and already excluded SMS/email by design; only the *default* and
  documentation needed to change); one gap is named and deliberately left
  open — `guided_setup.py`/`forge_planner.py` don't yet prompt for MFA
  interactively. (2) `ROADMAP.html` (and, finding similar drift,
  `docs/FEATURE-HISTORY.html`) **regenerated** via
  `md_to_html.py --collapsible` — satisfying the operator's "revise the
  roadmap to use collapsible sections, it's quite lengthy" request *and*
  closing a content-drift gap worse than the one the prior milestone's new
  `test_meta_doc_sync.py` checks for (that test compares date stamps only;
  the hand-synced `ROADMAP.html` was actually missing entire `<h3>`
  sections that exist in `ROADMAP.md` — true regeneration fixes content
  drift, not just stamp drift). Both changes, plus AD-058's stamp-sync
  follow-through in `ARCHITECTURE.md`/`docs/ARCHITECTURE.html`, are recorded
  in a new dated cycle in `docs/FEATURE-HISTORY.md`
  (`2026-06-08_04_54_51 UTC`). All tests green
  (`test_meta_doc_sync.py`, `test_html_base_sync.py`, and the
  `keepass or mfa or forge_init or secrets or meta_doc or html_base or
  roadmap or feature_history` sweep — 156 passed). The three draft sketches
  from the fourth milestone (Recovery-Readiness Conformance, Hypervisor
  Recovery Credentials, Granular Secret Access Silos) remain in
  `ROADMAP.md` "Proposed Future Work," still awaiting promotion to
  phase/AD status. The intelligence/development side of the project remains
  feature-complete per its own governance corpus; the next milestone named
  in that corpus is an *operational* one (a real hardware run), not a
  development one — though `ROADMAP.md` now also names one *proposed*
  development item (Phase 1.H), three *draft* items (the sketches above),
  and one newly-named *gap* (AD-058's guided-setup MFA prompt) for whenever
  the operator chooses to engage with any of them.

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

- **next_action**: **(Updated — sixth milestone: AD-058 guided-setup gap now
  CLOSED; commit/push is the remaining mechanical step.)** The MFA-method
  wiring (guided setup → forge manifest → `KeePassInitConfig`) is complete,
  tested (6 new cases across `test_guided_setup.py`/`test_forge_planner.py`),
  and documented (`docs/FEATURE-HISTORY.md` `2026-06-08_12_36_41 UTC`); the
  `federation_state.py` clock-injection bug found along the way is fixed and
  tested too. **Commit and push** this milestone's files (see
  `SESSION_HANDOFF.md`'s `next_action` for the full list) — the one concrete
  mechanical step remaining, if it has not already happened by the time you
  are reading this. **AD-058 now has no open gap** — both the default-flip
  (fifth milestone) and the "seen and confirmed at forge time" wiring (this
  milestone) are done. One thing worth surfacing if the operator asks "what
  did you notice": the **clock-injection bug class** named in
  `SESSION_HANDOFF.md` — one instance fixed, a codebase-wide
  `datetime.now(`/`datetime.utcnow(` sweep (outside `now_fn` plumbing) named
  as a reasonable scoped GAP-FILL candidate but **not done**, per scope
  discipline. Beyond that: `ROADMAP.md` "Proposed Future Work" still holds
  three sketches — Recovery-Readiness Conformance, Hypervisor Recovery
  Credentials (its constrained-account "middle path" was *endorsed* this
  milestone, but the sketch itself is not yet promoted to phase/AD), and
  Granular Secret Access Silos for Human Operators — each written because
  the operator asked a specific question and invited a draft/evaluation.
  The correct next move for all three remains the same: **let the operator
  react**, not pre-emptively promote any of them to a phase or an AD. If
  the operator confirms a direction on one (e.g., "scope the certificate
  idea," "build the constrained recovery accounts," "the silo idea is worth
  keeping on the roadmap for later"), write *that one* up the same way
  Phase 1.H was (scoped roadmap entry + AD in `ARCHITECTURE.md` +
  `.ai/decisions.md`) — without touching the others. If the operator
  redirects or narrows any sketch, edit it in place rather than starting a
  parallel one. Beyond all of the above: there is no other mandatory
  development action, and no open audit finding remains that requires one
  (F1/F2/F3 closed, committed; F4 is an observation requiring no action).
  **Phase 1.H, Pre-Install Forge Package and Image Builder** also remains a
  **proposed** (not mandatory) candidate. A resuming agent should: (a) wait
  for/follow new operator direction, or (b) — only if asked to find
  something to do — offer the AD-058 guided-setup gap, a draft sketch,
  Phase 1.H, or the platform's own named *operational* next step, "deploy
  to hardware" (see `active_objective`, above, and `FORGING.md`).

---

## Provenance

Created as part of
[`pap/revisions/2026-06-07_session-continuity-transition-to-pap.md`](../revisions/2026-06-07_session-continuity-transition-to-pap.md) —
the transition that moved broodforge's own session-continuity practice from
its pre-PAP prototype mechanisms (`.ai/AI_AGENT_BOOTSTRAP.md`,
`docs/SESSION-HANDOFF.md`) onto PAP-State's formally-specified Resume Block
and Session Handoff Protocol. Update this block at minimum at every session
boundary and at every major milestone, per the schema's `update_trigger`.
