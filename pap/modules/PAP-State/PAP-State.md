# PAP-State

Status: Canonical (realized from [Deliverable 4](../../revisions/synthesis/04_Canonical_PAP_Revision.md) Part II)
Operates under [PAP-Core](../../core/PAP-Core.md) authority. Loaded
whenever a task touches session continuity, runtime state, repository
memory, or the governance of tracked project understanding.

**Scope**: Session continuity, runtime state management, context
preservation, state export/import and portability, repository memory
structure, runtime artifact coordination, and coding-agent execution
context management — including governance of *what gets tracked about
project understanding* (evidence, decisions, assumptions,
contradictions, change-impact, dependencies).

PAP-State shall not duplicate governance already present in PAP-Core
(identity, lineage, hashing, Authority Hierarchy, CPP/CBMF, operating
principles — see [PAP-Core](../../core/PAP-Core.md) §10).

PAP-State is a **consumer** of serialization services
([PAP-Serialize / UPCCP-CSP](../../serialization/UPCCP-CSP/UPCCP-CSP.md)):
PAP-State manages *what* state is and what must be preserved about it;
PAP-Serialize defines *how* a state blob is packaged for transport
when CBMF reaches Level 5.

---

## 1. Startup Protocol

At the beginning of any session operating under PAP:

1. Scan repository status.
2. Detect uncommitted changes.
3. If uncommitted changes exist: assume the prior session may have
   terminated unexpectedly; preserve evidence of the prior state if
   required; revert to the last known committed state **unless**
   governance artifacts (e.g., an in-progress `SESSION_HANDOFF.md`)
   indicate the changes are intentional and should be continued. **If
   the uncommitted changes are to `PAP-Core` or any module itself**,
   make this determination per [PAP-Core §6.4](../../core/PAP-Core.md#64-operative-version-discipline-during-self-revision)
   — pin to the last *committed* version (not the working tree, which
   may be self-contradictory mid-edit by design) to decide whether to
   revert or continue, then read intent from `SESSION_HANDOFF.md` /
   the resume block, exactly as for any other uncommitted change.
4. Load governance and state artifacts: PAP-Core (always), the
   relevant lineage records, the current `SESSION_HANDOFF.md` /
   resume block, and any modules the apparent task requires.
5. Determine the current objective (from the resume block, the
   roadmap, or — if neither resolves it — by escalation per
   [PAP-Core](../../core/PAP-Core.md) §6.2).
6. Determine the next action.
7. Continue work.

## 2. Repository Memory Structure

A project repository operating under PAP-State maintains artifacts
across these categories — the structural backbone of "repository as
durable memory" ([PAP-Core](../../core/PAP-Core.md) §0):

| Category | Houses |
|---|---|
| Governance | charter, constitution, invariants, architecture, this protocol's own files |
| Decisions | Decision Records (rationale, alternatives, consequences, dependencies) |
| Evidence | supporting material for decisions and claims, kept separate from assumptions |
| Planning | roadmap, current sprint/milestone plans |
| State | resume blocks, session handoffs, runtime state instances |
| Risk | identified risks and their tracking |
| Debt | known technical/architectural debt |
| Research | exploratory findings not yet promoted to decisions |
| Assumptions | explicitly tracked, explicitly *not* facts |
| Contracts | interfaces, agreements, API/format commitments |
| Testing | test plans, results, coverage notes |
| Dependencies | ownership, trust level, lock-in risk, replacement complexity (§6.6) |
| Documentation | user- and operator-facing material |
| Oversight | audit records, review findings, compliance notes |

A repository need not have a literal directory per category — what
matters is that each concern is addressed *somewhere* discoverable,
and that the category-to-location mapping is itself recorded.

## 3. Project Resume Block

A portable project save-state, maintained continuously and updated at
minimum at every session boundary, containing: project identity,
active objective, active milestone, active risks, blockers, and a next
action concrete enough that a cold reader can start immediately.

Machine-form schema: [`schemas/resume-block.schema.yaml`](schemas/resume-block.schema.yaml).
`UPCCMP_PROTOCOL_RESUME_BLOCK.yaml` — part of the superseded source
corpus, removed during cleanup and recoverable only via git history
(see `SESSION_HANDOFF.md`'s "Source corpus" record) — was a worked
example of the *practice* this rule formalizes: direct evidence the
practice predated, and motivated, the rule.

## 4. Session Handoff Protocol

At the close of a session (or at any major milestone), preserve:
project state, governance state, the current resume block, and a
session handoff artifact — a durable, self-contained document a cold
reader can use to resume work, structured at minimum as: status,
objective, source materials to consult (with why), key decisions/
insights not to be re-derived, a milestone checklist with completion
state, the last completed step, the next action, and resume
instructions.

Machine-form schema: [`schemas/session-handoff.schema.yaml`](schemas/session-handoff.schema.yaml).
`SESSION_HANDOFF.md` (in the corpus root) is itself an instance of
this practice — written before this rule was canonically restored,
demonstrating that the practice survived the rule's absence.

## 5. Repository-Census and Continuity Hygiene

Periodically (at minimum, at session start and at major milestones)
confirm that the lineage artifacts ([PAP-Core](../../core/PAP-Core.md) §3),
the resume block, and the repository memory structure (§2) remain
mutually consistent — i.e., that no drift has occurred into a state
where one artifact claims something another contradicts without that
contradiction being recorded (§6.4).

## 6. Governance-of-Substance: tracked concerns

These six govern *what an agent tracks about its evolving
understanding of the project* — distinct from PAP-Core's concern with
artifact *identity*.

### 6.1 Evidence Governance
Maintain evidence separately from assumptions. Major decisions should
reference the evidence that supports them, by name or location.

### 6.2 Decision Governance
Maintain Decision Records containing: rationale, alternatives
considered, consequences, and dependencies. (Decision Records sit at
level 5 of the Authority Hierarchy — [PAP-Core](../../core/PAP-Core.md) §4.)

### 6.3 Assumption Governance
Assumptions shall be explicitly tracked and explicitly labeled as
assumptions. **Assumptions are not facts.**

### 6.4 Contradiction Governance
Contradictions — between artifacts, between stated intent and observed
reality, or between an assumption and new evidence — shall be resolved
*or* explicitly documented. Silence is not an acceptable resolution.

### 6.5 Change Impact Assessment
Before major changes, evaluate: affected components, affected
decisions, affected invariants, migration requirements, rollback
strategy, and testing impact. Record the assessment alongside the
change.

"Major" here is the same threshold [PAP-Core §3](../../core/PAP-Core.md#3-lineage-governance)
and [§6.3](../../core/PAP-Core.md#63-adversarial-review-governance-summary)
name for triggering an APDRP review and a dedicated revision record —
one threshold, three consequences, fired together rather than checked
separately.

### 6.6 Dependency Governance
Track, for every meaningful external dependency: ownership, trust
level, lock-in risk, and replacement complexity.

## 7. Schemas (Machine Form)

| Schema | Governs |
|---|---|
| [`resume-block.schema.yaml`](schemas/resume-block.schema.yaml) | The Project Resume Block (§3) |
| [`session-handoff.schema.yaml`](schemas/session-handoff.schema.yaml) | The Session Handoff artifact (§4) |
| [`governance-state.schema.yaml`](schemas/governance-state.schema.yaml) | A structured snapshot of "what governance is currently active, pending, or contested" |
| [`project-state.schema.yaml`](schemas/project-state.schema.yaml) | A structured snapshot of "what the project currently is" — suitable as a CBMF Level 5 serialization payload |

Each schema instance is namespaced distinctly from its template
(`*.state.yaml` for a live instance vs. `*.schema.yaml` for the shape
that governs it) — see [Architecture Recommendation](../../revisions/synthesis/03_Canonical_Architecture_Recommendation.md) §6.

## Provenance

Realizes Part II ("PAP-State") of
[Deliverable 4](../../revisions/synthesis/04_Canonical_PAP_Revision.md). Carries
forward — per the boundary table in
[Deliverable 3](../../revisions/synthesis/03_Canonical_Architecture_Recommendation.md) §3 —
UPCCMP 22-09's Startup Protocol, Repository Memory Structure, Project
Resume Block, Session Handoff Protocol, and the six
Evidence/Decision/Assumption/Contradiction/Change-Impact/Dependency
governance sections, none of which had migrated prior to this synthesis
(see [Gap Analysis](../../revisions/synthesis/02_Gap_Analysis.md) §1.2–1.4).
