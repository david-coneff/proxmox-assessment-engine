# PAP — populated as an analytical methodology for this project

This `pap/` tree is a populated instance of the **Protocol Architecture
Package (PAP)** — a methodology for durable project continuity,
systematic review, lineage-reconstruction/synthesis, and structured
self-state-tracking. It was copied here, by direct operator
instruction, from PAP's own canonical source repository (local path:
`software_development/PAP`, currently adopted at commit `3f8b12d`;
`PAP-Core` and the modules were last substantively changed at
`18f3657` — consult that repository's `CANONICAL_PROTOCOL_INDEX.md` for
the precise per-component provenance, and `git log --follow` on any
file here for its full history prior to this copy).

## What this is for, concretely

Broodforge can use the modules under `modules/` (and the always-loaded
`core/PAP-Core.md`) as **analytical tools** — to run systematic review
([PAP-AUDIT](modules/PAP-AUDIT/PAP-AUDIT.md)'s APDRP machinery), deep
lineage/gap analysis and synthesis
([PAP-X](modules/PAP-X/PAP-X.md)'s six-stage procedure), or
self-state-tracking lenses
([PAP-State](modules/PAP-State/PAP-State.md)'s Census/Continuity-Hygiene
and Governance-of-Substance machinery) **against broodforge's own
state** — its code, its `.ai/` governance corpus, its `docs/` history,
its assessment/remediation engines — to generate findings and
revision-recommendations for broodforge's own maintainers and governing
artifacts to consider.

`core/PAP-Core.manifest.yaml` names which module to load for which kind
of task (`load_when` triggers) — start there once you know what you're
trying to do; start at `core/PAP-Core.md` if you don't yet.

## The boundary this tree does **not** cross (read this before assuming anything)

Populating this tree does **not** put broodforge "under PAP governance"
the way PAP's own source repository operates under itself (a
*self-deployment*: PAP is both the methodology and its own subject
there — see that repository's `PAP_CHARTER.md` §2.1). That is one
specific, self-referential case — not the general one, and not this
one.

`PAP_CHARTER.md` §2.3 in PAP's source repository (added the same day
this tree was populated, specifically because preparing to do *this*
surfaced the gap that made it necessary to write — see this file's
Provenance, below) names the rule directly: PAP's
own constitutional authority is scoped to *PAP's own governance* — it
does not reach into the separate, internal governance of any project
that merely *uses* PAP analytically. Concretely, for broodforge:

- **[`.ai/PROJECT_CHARTER.md`](../.ai/PROJECT_CHARTER.md) remains
  broodforge's own sovereign top-level authority** — exactly as it was
  before this tree existed. So do `.ai/DESIGN_PRINCIPLES.md`,
  `.ai/IMPLEMENTATION_RULES.md`, `decisions.md`, and the rest of the
  `.ai/` governance corpus. Nothing in `pap/` outranks, supersedes, or
  governs them. Authority Hierarchy precedence
  ([PAP-Core §4](core/PAP-Core.md#4-authority-hierarchy-document-precedence))
  is a PAP-internal concern, scoped to PAP's own artifacts — it is not
  a claim about broodforge's artifacts.
- When PAP's modules are run against broodforge's state, their output
  is **findings and recommendations offered to** broodforge's own
  governance — for `.ai/decisions.md`, `NEXT_STEPS.md`,
  `.ai/PROJECT_CHARTER.md`, or whatever broodforge's maintainers
  determine is the right place to record a response — to accept,
  reject, adapt, or ignore by broodforge's own rules. They are never
  **directives issued by** PAP's authority, and PAP claims no authority
  to resolve them unilaterally (see, for instance, the
  charter/reality tension already visible between
  `.ai/PROJECT_CHARTER.md`'s "assessment only, no
  judgments/recommendations" framing and the platform's actual,
  completed Phase 26 Autonomous Remediation engine — a finding PAP's
  modules can register and reason about, but whose *resolution* is
  broodforge's call, not PAP's).

## A note on links inside the populated spec that may not resolve here

`core/PAP-Core.md` and the modules under `modules/` are copied
**verbatim** — unedited — from the canonical source, because editing
canonical PAP text as a side effect of *populating* it elsewhere would
itself be the kind of silent, unrecorded drift PAP's own governance
exists to prevent. Some of their internal cross-references (to a
`CANONICAL_PROTOCOL_INDEX.md`, a `PROJECT_CHARTER.md`/`PAP_CHARTER.md`,
a `SESSION_HANDOFF.md`, at conventional relative paths under and beside
`pap/`) describe the **self-deployment** case — a project that has
adopted PAP as its *own* constitutional operating methodology, and so
maintains its own instances of those artifacts at those locations.
Broodforge has not done that, and §2.3 says it need not: those links
may not resolve in this tree, and that is expected, not an error or a
sign of incomplete population. (`PAP_CHARTER.md` itself was
deliberately *not* copied here, for the same reason — it is PAP's own
constitution, scoped to PAP's own repository; see §2.3's Provenance for
why it is named distinctly from the generic `PROJECT_CHARTER.md`
slot-name this corpus's Authority Hierarchy template uses.)

`state/`, `audits/`, and `revisions/` are created here **empty**
(mirroring the canonical layout's "Runtime State Artifacts" pattern —
see the source repository's `Architecture-Overview.md` §"The shape")
as a place for **broodforge's own** future analytical-use records —
audit findings, revision-recommendation drafts, self-state snapshots —
generated by running PAP's modules against broodforge's state. These
would be records of *broodforge's use of PAP as a tool*, not a
constitutional index of "what PAP is" (the source repository already is
that, and remains the canonical reference for it).

## Provenance

Populated by direct operator instruction ("now, using the currently
adopted pap, populate pap/ in broodforge"), following an
operator-identified structural clarification in PAP itself — the
addition of `PAP_CHARTER.md` §2.3 in PAP's source repository (commit
`18f3657`), made *specifically because* the first attempt to reason
about this
population surfaced a load-bearing gap: PAP's corpus had never
distinguished "PAP's own governance" from "the governance of a project
that merely uses PAP as a methodology," because the only case it
described — PAP's own self-deployment — is the one case where those
two realms collapse into one. This tree is, in effect, the first
real-world test of that distinction: it exists to be *used*, not to be
*obeyed*.
