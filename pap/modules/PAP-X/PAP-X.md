# PAP-X

Status: Canonical (realized from
[Deliverable 4](../../revisions/synthesis/04_Canonical_PAP_Revision.md) Part II;
procedural content added in the Era-4 self-audit revision — see
Provenance)
Operates under [PAP-Core](../../core/PAP-Core.md) authority. Loaded
when undertaking a multi-document synthesis or lineage-reconstruction
task analogous to the one that produced this revision.

**Scope**: Deep analysis and extended-reasoning procedures that go
beyond what PAP-Core's operating principles and PAP-AUDIT's review
machinery cover on their own — e.g., multi-session investigations,
cross-cutting architectural analyses (such as the synthesis that
produced this revision), or reconstructions of lineage from a
fragmented corpus.

## Why this module exists as a separate concern

This module's name appears in the prior corpus only as a one-line stub
("Deep analysis module" in one stub file, "Context management module"
in another — the package scaffold was internally inconsistent about
which name belonged to which concept). No prior document specified its
content; the synthesis that produced Deliverable 4 deliberately left it
as a *named, recorded* open item rather than inventing governance
beyond what the commissioning directive called for (an application of
Contradiction/Change-Impact discipline,
[PAP-State](../PAP-State/PAP-State.md) §6.4–6.5: a known gap, named,
beats an invented filling or a silent absence — see "Provenance" for
how that item was eventually closed).

PAP-X is scoped to hold *procedures for performing exactly the kind of
work that produced this very specification* — lineage reconstruction,
gap analysis, multi-document synthesis, architecture recommendation —
generalized into reusable method, so a future agent facing a similarly
fragmented corpus, or a similarly large analysis task, has a named
procedure to follow rather than having to reinvent one under pressure.

## Boundary rules

- **PAP-X shall not duplicate PAP-Core's operating principles.** It
  *uses* the Autonomous Execution Rule and Escalation Protocol
  ([PAP-Core](../../core/PAP-Core.md) §6); it does not redefine them.
- **PAP-X shall not duplicate PAP-AUDIT's review machinery.** A PAP-X
  analysis that constitutes a "major change" is still subject to
  APDRP — PAP-X supplies the *analysis method*, [PAP-AUDIT](../PAP-AUDIT/PAP-AUDIT.md)
  supplies the *review of its output*. §2 below names the handoff
  points explicitly so this boundary stays operational, not aspirational.
- **PAP-X shall not duplicate CBMF's escalation framework.** Multi-
  document synthesis routinely *triggers* CBMF escalation
  ([PAP-Core](../../core/PAP-Core.md) §5.2) — §1 below names exactly
  where — but PAP-X does not redefine what the levels are or how they
  escalate; it only names the points in its own procedure where an
  agent should check whether escalation has become necessary.

---

## 1. The Deep-Analysis / Synthesis Procedure

A named, repeatable six-stage sequence, generalized from the method
that actually produced [Deliverables 1–4 of this synthesis](../../revisions/synthesis/)
— this file is itself a worked instance of Stage 6 applied recursively
to PAP-X's own gap. Apply the stages **in order**; do not skip ahead
on the assumption that an early stage was "obvious" — the original
synthesis found that apparent obviousness (e.g., "UPCCMP is clearly
superseded") dissolved into more precise findings ("superseded by
*redirection*, not by a newer snapshot — and only after its richest
content was confirmed orphaned, not migrated") only because the
stages were performed in sequence rather than assumed.

### Stage 1 — Corpus Inventory

**Purpose**: Establish *what exists* before reasoning about what it
means. Treat the corpus as a single lineage, not a set of independent
files.

**Method**:
- Enumerate every artifact, in chronological order. Where no lineage
  metadata exists, dates/times in filenames or commit history are the
  authoritative ordering signal — record this assumption explicitly
  ([PAP-State](../PAP-State/PAP-State.md) §6.3, Assumption Governance).
- For each artifact, record its *type* (canonical snapshot, proposal,
  scaffold, worked example, resume/self-assessment artifact, directive,
  …) and its *role in the lineage* — not just its content summary.
- Where an artifact references material that is not itself present
  (e.g., a parent snapshot named but not included), record this as a
  **named GAP** in the inventory itself — do not silently omit the
  reference or silently assume the missing content's nature.

**Output**: A chronological inventory table (artifact / type / role),
annotated with explicit GAP markers for anything referenced-but-absent.

### Stage 2 — Supersession-Chain Mapping

**Purpose**: Determine *what superseded what*, and — critically —
*how* (a newer snapshot is not the only way something becomes
superseded).

**Method**:
- Build a lineage chain per sub-line (the original synthesis found
  three: a main-protocol line, a sibling-protocol line, and a
  serialization sub-line — do not assume there is exactly one chain).
- For each link in each chain, classify the supersession mechanism.
  Distinguish at minimum: *superseded by a newer canonical snapshot*
  (the ordinary case) vs. *superseded by redirection* (the lineage
  doesn't get a newer version of itself — it gets folded into a
  different protocol/module as an architectural decision). The
  original synthesis found UPCCMP's lineage was the second kind, and
  that distinction changed the entire disposition of its content
  (nothing in UPCCMP was "old" — it was *orphaned*, awaiting migration
  that never happened).
- Build a dependency map: which artifacts/concepts depend on which
  others, and which dependencies are currently *unsatisfiable* (e.g.,
  "CPP/CBMF depends on UPCCP-CSP, but UPCCP-CSP has no specification
  yet — only a worked example" — a dependency that is real but
  presently broken is itself a finding).
- Build a module/concept evolution table: for each major concept, its
  first appearance, subsequent revisions (if any), and current
  canonical status. This table is what Stage 3 classifies against.

**Output**: Per-sub-line supersession chains (as diagrams or ordered
lists), a dependency map naming unsatisfiable dependencies, and a
module/concept evolution table.

### Stage 3 — Gap Classification

**Purpose**: Turn "things that look unfinished" into a disciplined
account of *why* each one is unfinished, and *what should happen to
it* — distinguishing genuine gaps from things that only look like gaps.

**Method**:
- Classify every at-risk item into named categories that distinguish
  *why* it's at risk — the original synthesis used: incomplete
  synthesis (a merge was started but not finished), unresolved
  revision state (a newer proposal exists but was never adopted into a
  canonical snapshot), and new scope (named in a stub or aspiration but
  never specified anywhere). These categories matter because each
  implies a different disposition — an incomplete synthesis needs
  *completion*, an unresolved revision needs a *decision*, new scope
  needs *origination*. Conflating them produces a synthesis that
  either over-invents or under-delivers.
- For each classified item, cite the *evidence* for the classification
  (by artifact name/location — [PAP-State](../PAP-State/PAP-State.md)
  §6.1, Evidence Governance) and propose a *disposition* — but do not
  yet execute the disposition; Stage 3's job is the account, not the
  decision.
- Conclude with a **net assessment**: across everything classified,
  is there evidence of *intentional removal* anywhere, or is everything
  accounted for as omission, redirection, or incompleteness? This
  question matters because "intentional removal" would change how the
  synthesis must treat the gap (respect a decision already made) versus
  "omission" (recover what was lost). State the answer explicitly,
  with the evidence that supports it — do not leave it implicit.

**Output**: A gap register (item / classification / evidence /
proposed disposition) plus an explicit net-assessment statement.

### Stage 4 — Architecture / Disposition Recommendation

**Purpose**: Convert the gap register into *decisions* — concretely,
where does each piece of surviving content belong, and what should the
result look like structurally — before writing a word of the result
itself.

**Method**:
- Answer, explicitly, whatever framing questions the commissioning
  task poses (the original synthesis had to answer: should this be a
  workflow system, a governance/reasoning framework, or both? what are
  the PAP-Core/module scope boundaries? is self-deployment feasible,
  and what would it require?). An analysis that produces a
  specification without first answering its own framing questions
  produces something internally consistent but unmoored from its
  actual purpose.
- Produce a **concrete per-concept disposition table**: for every
  surviving concept identified in Stages 1–3, name exactly which
  destination module/section it belongs in, and why. This table is
  the single artifact Stage 5 executes against — if it's vague, Stage
  5 will improvise, and improvisation under CPP pressure tends toward
  either omission or invention, both of which Stage 3 was designed to
  prevent.
- Recommend a concrete structure (directory layout, module list,
  file organization) — and **explicitly justify every deviation** from
  any structure the commissioning task already sketched. A
  recommendation that silently changes a given sketch invites the
  question "was that an oversight or a decision?"; naming the
  deviation and its rationale answers that question before it's asked
  (this is also the Future-Reconstruction APDRP perspective, applied
  pre-emptively — [PAP-AUDIT](../PAP-AUDIT/PAP-AUDIT.md) §2's
  fourth, "future-reconstruction," perspective).

**Output**: Explicit answers to the task's framing questions, a
per-concept disposition table, and a recommended structure with named,
justified deviations from any prior sketch.

### Stage 5 — Full-Specification Synthesis

**Purpose**: Write the result — completely, not as a delta or a
pointer to "see the disposition table for details."

**Method**:
- Produce an **independently-usable, non-delta** specification: a
  reader with *only* this output and no access to Stages 1–4 should be
  able to operate from it without needing the prior corpus. (This is
  the Reconstruction Requirement, [PAP-Core](../../core/PAP-Core.md)
  §7, applied to the synthesis's own output — the output must satisfy
  the same standard it documents.)
- Execute every disposition from Stage 4's table — and where the
  result is large enough that it will not fit as a single direct
  artifact, this is precisely where **CBMF escalation** becomes live:
  check, in order, whether Level 1 (Structured Partitioning — multiple
  logically-separated documents, as Deliverables 1–4 themselves were)
  or Level 2 (Modular Packaging — a directory hierarchy, as `pap/`
  itself is) is the right mechanism *before* assuming the content must
  be compressed or summarized. CPP ([PAP-Core](../../core/PAP-Core.md)
  §5.1) is constitutional here: preserve completeness through structure,
  not through omission.
- Include a **complete supersession/adoption map**: trace every item
  from the Stage 1 inventory to its final disposition in the output —
  superseded-by-name, migrated-to-location, or originated-as-new. A
  synthesis that cannot show this full accounting cannot itself be
  checked for silent loss, which defeats the purpose of having
  performed Stages 1–3 at all.

**Output**: The complete specification/analysis artifact(s), plus a
full per-item supersession/adoption map proving nothing was silently
dropped.

### Stage 6 — Realization and Closure

**Purpose**: Where the task calls for it, turn the specification into
the structure it specifies — and close the loop on the analysis
itself.

**Method**:
- Populate the recommended structure (Stage 4) with the synthesized
  content (Stage 5) — this is where Level 1/2 CBMF escalation is most
  concretely exercised: deciding how to partition content across files
  and directories *is* performing Structured Partitioning and Modular
  Packaging, not merely describing them.
- Submit the result — both the specification and, if produced, its
  realization — to [PAP-AUDIT](../PAP-AUDIT/PAP-AUDIT.md)'s Adversarial
  Perspectives Deep Review Protocol as a major governance revision
  ([PAP-Core](../../core/PAP-Core.md) §6.3). This is the handoff point
  named in this module's boundary rules: PAP-X's job ends at producing
  a reviewable result; PAP-AUDIT's job is reviewing it.
- Update the lineage artifacts ([PAP-Core](../../core/PAP-Core.md) §3)
  to record the new synthesis as a milestone, and close out session
  continuity per [PAP-State](../PAP-State/PAP-State.md) §4 — a
  synthesis that is not recorded in lineage and handoff artifacts is,
  from a future operator's perspective, indistinguishable from one
  that never happened.

**Output**: The realized structure (where applicable), an audit record
or APDRP review reference, and updated lineage/handoff artifacts.

## 2. Handoff points to other modules (keeping the boundary rules operational)

| When | Hand off to | Why |
|---|---|---|
| A synthesis output is large enough that direct generation is insufficient | [PAP-Core](../../core/PAP-Core.md) §5.2 (CBMF) | PAP-X *triggers* escalation by producing large output; it does not define the levels — see Stage 5/6. |
| The synthesized result needs review before adoption | [PAP-AUDIT](../PAP-AUDIT/PAP-AUDIT.md) §2 (APDRP) | PAP-X supplies the analysis method; PAP-AUDIT supplies independent review of its output — conflating them would let an analysis grade its own work. |
| The procedure surfaces a genuinely ambiguous fork (e.g., two equally-supported dispositions for the same concept) | [PAP-Core](../../core/PAP-Core.md) §6.2 (Escalation Protocol) | "Multiple valid paths with no selection criteria and lasting consequences" is an escalation condition, not a Stage-4 judgment call to push through alone. |
| The result needs to persist across a session boundary mid-procedure | [PAP-State](../PAP-State/PAP-State.md) §3–4 (Resume Block / Session Handoff) | A six-stage procedure will routinely outlast a single session — this is exactly the "partial amnesia" scenario PAP-Core §0 names as the normal case, not the exception. |

## Provenance

Realizes Part II ("PAP-X") of
[Deliverable 4](../../revisions/synthesis/04_Canonical_PAP_Revision.md),
which explained the original scoping decision and recorded its
procedural content as an open item rather than inventing it under
directive pressure. That item was closed in the Era-4 self-deployment
revision (see [`PROTOCOL_HISTORY.md`](../../revisions/PROTOCOL_HISTORY.md)
and the [self-audit](../../audits/2026-06-07_pap-self-audit.md) Finding
F1) by generalizing — per the open item's own instruction — the exact
method that produced Deliverables 1–4: corpus inventory →
supersession-chain mapping → gap classification → architecture
recommendation → full-spec synthesis → realization and closure. §1 of
this file *is* that generalization; this file's own revision is its
first worked recursive application.
