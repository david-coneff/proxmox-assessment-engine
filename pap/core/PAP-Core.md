# PAP-Core

Status: Canonical (realized from [Deliverable 4](../revisions/synthesis/04_Canonical_PAP_Revision.md) Part I)
Always loaded. Authoritative for identity, lineage, timestamp, and
authority governance; the Completeness Preference Principle and
Context Boundary Management Framework; cross-cutting operating
principles; the Reconstruction Requirement and Success Criterion;
the Human Form / Machine Form duality rule; and Module Governance.

No module may restate, redefine, or maintain its own copy of anything
in this file — see §10 (Module Governance).

---

## 0. Purpose and Primary Operating Principle

**Purpose**: Provide durable project continuity, governance,
reconstruction capability, auditability, and long-term architectural
coherence for coding-agent work, across sessions, models, repositories,
platforms, and execution environments — using the project's own
repository as the persistence mechanism.

**Primary Operating Principle**: *Assume every future session begins
with partial amnesia.* Repository artifacts are durable memory; the
agent is a temporary reasoning engine. Success is measured by the
preservation of the ability to understand, reconstruct, continue,
audit, recover, and improve the project — using repository artifacts
alone, with minimal loss of intent, reasoning, architecture, or
governance.

## 1. Identity Governance

### 1.1 Content Identity (CID)

```
CID = SHA-256(canonical hashing scope)
CID-SHORT = first 8 hexadecimal characters of CID
```

CID-SHORT length (8 hex characters) is normative.

### 1.2 Canonical Hashing Scope

A canonical artifact shall contain **exactly one**
`CONTENT HASHING SCOPE START` marker:

```
=====================================================================
CONTENT HASHING SCOPE START
=====================================================================
```

- Zero markers is invalid. More than one marker is invalid
  (Hashing Marker Uniqueness Rule).
- The hashing scope begins immediately after the terminating newline
  of the marker. The marker itself is excluded from the hash.
- There is no end marker — the scope extends to end-of-file.
- Hash input = all bytes from immediately after the marker through
  end-of-file. CID = SHA-256 of that input.

**Minimal Exclusion Principle**: only content required to avoid
self-referential identity dependencies may be excluded from the hash.

| Excluded (above/around the marker) | Included (the hashing scope) |
|---|---|
| filename | governance rules |
| CID field | protocol definitions |
| publication metadata | procedures |
| timestamp metadata | requirements |
| lineage metadata | examples |
| revision metadata | appendices |
| all content above the marker | operational content |

**Reference implementation** (normative procedure for computing CID):
1. Open the artifact.
2. Locate the unique `CONTENT HASHING SCOPE START` marker.
3. Begin reading immediately after the marker's terminating newline.
4. Read through end-of-file.
5. Compute SHA-256 over those bytes.
6. CID = the resulting digest; CID-SHORT = its first 8 hex characters.

### 1.3 Snapshot Lifecycle

Snapshots exist in exactly one of two states:

**DRAFT**
- The timestamp component of the snapshot identity may remain fixed
  across multiple content revisions within one drafting session.
- Each content revision recalculates the CID (and therefore, usually,
  the CID-SHORT and filename).
- Content is mutable; iterative revision is expected and allowed.
- Lineage metadata is updated with each draft revision.

**FINALIZED**
- Timestamp, CID, and filename are fixed and immutable.
- Content may not be modified.
- Any further change to the substance produces a **new** canonical
  snapshot (new timestamp and/or new CID-SHORT) — never an edit to a
  finalized one.

A snapshot becomes immutable only upon formal publication or adoption.

### 1.4 Canonical Filename Governance

```
<PROTOCOL_OR_MODULE_NAME>_<YYYY-MM-DD_HH-MM>_<CID-SHORT>.md
```

- Descriptive suffixes shall not be used in the canonical filename
  itself.
- The filename *identifies* the snapshot; the CID *verifies* it.

### 1.5 Snapshot Minimality and Independence Principles

**Minimality**: A canonical snapshot shall contain only active
governance, active procedures, active definitions, and required
metadata. Historical content is externalized to lineage artifacts
(§3). Context-window efficiency is itself a governance concern.

**Independence**: A snapshot shall be operationally complete without
requiring the contents of any prior snapshot. Historical versions may
be *referenced* through lineage metadata; they are never *required*.

## 2. Timestamp Governance

### 2.1 Authority Hierarchy for Timestamp Sources

In order of authority:

1. **Trusted Clock Source** — operating-system clock, a time service or
   tool-provided timestamp, repository commit timestamp.
2. **Active Governance Timestamp** — the current protocol session's
   established timestamp, or a previously-established project timestamp.
3. **Human-Supplied Timestamp** — an explicit operator-provided
   date/time.
4. **Derived Timestamp** — inferred from context or relative-date
   interpretation.

### 2.2 Governance Rule

When a trusted clock source is available, it is authoritative. A
human-supplied timestamp is used only when: trusted-clock access is
unavailable, governance requires historical reconstruction, or the
operator explicitly overrides the timestamp source.

### 2.3 Session Timestamp Rule

- Shorthand times inherit the active governing date.
- The governing date remains active until explicitly changed.
- An explicit operator-supplied date supersedes any inferred date.
- When trusted clock access *is* available, timestamps are obtained
  from it directly.

## 3. Lineage Governance

Maintain three durable lineage artifacts (under `pap/revisions/` —
see [Architecture Overview](../docs/Architecture-Overview.md)):

- `PROTOCOL_HISTORY.md` — narrative chronicle of the protocol family.
- `CANONICAL_PROTOCOL_INDEX.md` — authoritative current-snapshot index.
- `PROTOCOL_REVISION_RECORDS/` — one record per published revision,
  preserving: version, timestamp, filename, CID, parent version, and
  revision summary.

Lineage is preserved through metadata, not embedded historical
content — the Minimality Principle (§1.5) applied repository-wide.

**When a DRAFT-state revision needs its own record**: a living
canonical document (§1.3 DRAFT state) is expected to change repeatedly
under active self-deployment. Not every such change is a "published
revision" requiring a new entry under `PROTOCOL_REVISION_RECORDS/` —
ordinary DRAFT-state iteration is already recorded through git history
plus `CANONICAL_PROTOCOL_INDEX.md`'s per-component commit anchors (its
Maintenance Rule keeps that current). A dedicated revision record is
warranted specifically when a change is **major** in §6.3's sense (the
same trigger that invokes Adversarial Review) or when a snapshot is
formally finalized/published (§1.3) — not for every commit that
touches a living document. Recording every iteration would itself
violate Minimality (§1.5); recording none would leave "what changed
and why, at a scale worth a future operator's attention" undiscoverable
without replaying git log. This clause exists to name the line between
those two failure modes explicitly, rather than leaving it to be
inferred — or, worse, to drift either direction unnoticed.

## 4. Authority Hierarchy (document precedence)

When governance artifacts conflict, precedence is — highest to lowest:

1. `PROJECT_CHARTER.md`
2. `PROJECT_CONSTITUTION.md`
3. `INVARIANTS.md`
4. `SYSTEM_ARCHITECTURE.md`
5. Decision Records (governed in [PAP-State](../modules/PAP-State/PAP-State.md) §6.2)
6. `ROADMAP.md`
7. `CURRENT_SPRINT.md`
8. `SESSION_HANDOFF.md`

These are **generic slot-names** — the role each level names, not a
literal filename every project must use. A project's actual artifact
occupying a level may be named differently; what governs is the *role*
(and where that project records which artifact occupies it), not
whether the name matches this template. This repository's own level-1
artifact, for instance, is deliberately named
[`PAP_CHARTER.md`](../../PAP_CHARTER.md) rather than
`PROJECT_CHARTER.md` — see its §2.3 for why, and for the broader point
this hierarchy governs *this* repository, not the separate internal
governance of any project PAP is used analytically to examine (a
distinction that same clause names explicitly).

**Lower authority may not override higher authority.**

**Authority Conflict Resolution Procedure**:
1. Identify the precedence levels of the conflicting artifacts.
2. The higher-precedence artifact governs.
3. If both are at the same level, the more-recently-finalized snapshot
   governs (§1 determines "more recent" via timestamp; CID is the
   integrity tie-breaker).
4. Record the conflict and its resolution in Contradiction Governance
   (PAP-State §6.4) — resolution does not erase the record.
5. If no precedence difference resolves it, this is an Escalation
   condition (§6.2).

## 5. Completeness Preference Principle (CPP) and Context Boundary Management Framework (CBMF)

### 5.1 CPP — Principle Statement

When confronted with context limitations, PAP **shall** prioritize
preservation of full information over brevity, summarization, or
omission. CPP mandates *preservation first*, using structural or
transport mechanisms to manage size — never silent loss. This
principle is **constitutional**: it applies to artifact generation,
specification authoring, state export and handoff, audit reports, and
module revision alike.

### 5.2 CBMF — Escalation Levels

Apply in order; do not skip ahead without first determining the lower
level is genuinely insufficient:

| Level | Name | Mechanism |
|---|---|---|
| 0 | Direct Completion | Generate the full content directly — it fits. |
| 1 | Structured Partitioning | Split into multiple logically-separated files/modules. |
| 2 | Modular Packaging | Organize an over-large module into a directory hierarchy. |
| 3 | Archive Generation | Package multiple files into a single archive for transfer/versioning. |
| 4 | Multi-Artifact Continuation | Multiple sequential artifacts with deterministic, explicit assembly instructions. |
| 5 | State Serialization | Serialize runtime/working state into a compact transport artifact ([UPCCP-CSP](../serialization/UPCCP-CSP/UPCCP-CSP.md)). |

#### 5.2.1 Operational anchors — where each level is concretely illustrated

The table above names *what* each level is. This names *where to find
how to actually perform one* — pointers to worked examples and
governing specs, not restatements of them (Minimality, §1.5: a
mechanism this simple does not need its own constitutional procedure
when a worked instance already demonstrates it).

| Level | Concretely means, in a repository | Worked example / governing spec |
|---|---|---|
| 1 — Structured Partitioning | Multiple sibling files, each independently coherent, cross-referenced rather than duplicated. | [PAP-X §1](../modules/PAP-X/PAP-X.md#1-the-deep-analysis--synthesis-procedure) Stage 5; [Deliverables 1–4](../revisions/synthesis/) of the canonical synthesis are a worked instance. |
| 2 — Modular Packaging | A directory hierarchy with its own internal orientation document, so a reader can navigate it without holding the whole thing in context at once. | [PAP-X §1](../modules/PAP-X/PAP-X.md#1-the-deep-analysis--synthesis-procedure) Stage 6; [`pap/`](../docs/Architecture-Overview.md) itself, oriented by `Architecture-Overview.md`, is the worked instance. |
| 3 — Archive Generation | A single compressed wrapper (e.g. `.zip` — a widely-available format, itself a [Compatibility](../compatibility/Platform-Compatibility-Profiles.md) concern) around an existing directory, named to match it, recorded in lineage metadata as a **transfer convenience only** — the directory remains canonical; the archive is never the sole copy of anything. | One historical precedent exists in this repository's own corpus (`2026-06-07_08-28_..._Modular_Architecture_Package/` + a matching `.zip` "wrapper around the identical content — no unique material," per [Lineage Analysis](../revisions/synthesis/01_Protocol_Lineage_Analysis.md) row 7) — superseded and recoverable only via git history (see [SESSION_HANDOFF.md](../../SESSION_HANDOFF.md#source-corpus)). No living worked example exists yet; the principle above is generalized directly from that precedent's evidenced shape, not invented. |
| 4 — Multi-Artifact Continuation | Sequential artifacts, each carrying an explicit manifest: total part count, this part's index, the exact reassembly order, and a per-part integrity hash — generalizing UPCCP-CSP's own header-and-integrity-footer discipline across *several* artifacts instead of one. | [UPCCP-CSP §1–2](../serialization/UPCCP-CSP/UPCCP-CSP.md) — the pattern to generalize *from*, not duplicate; no dedicated multi-artifact spec exists, because the generalization is small enough that restating UPCCP-CSP's discipline here would itself violate Module Governance (§10). |
| 5 — State Serialization | A self-describing, hashed, schema-registered envelope. | [UPCCP-CSP](../serialization/UPCCP-CSP/UPCCP-CSP.md) — fully specified; the only level with a dedicated module, because the wire format itself needed independent, evolvable governance the others don't. |

(Level 0 needs no anchor: it is the absence of a mechanism, not the
presence of one.)

### 5.3 Governance Rules

1. **Preference hierarchy**: attempt preservation via Level 0–5
   escalation before resorting to summarization or compression.
2. **Evidence of compliance**: when content spans multiple messages or
   files, include explicit indicators of full coverage (manifests,
   "part N of M" markers, assembly instructions).
3. **CBMF structurally motivates the modular architecture**: Levels 1
   and 2 are *why* PAP is organized as Core + Modules — a monolithic
   protocol cannot honor CPP at scale.

### 5.4 Example Workflow (illustrative, non-normative)

```text
1. Attempt direct generation (Level 0).
2. If a context limit is reached → split into multiple files (Level 1).
3. If a single module is still too large → package as a hierarchy (Level 2).
4. If the hierarchy is still too large → archive it (Level 3).
5. If the archive still exceeds limits → multi-artifact continuation (Level 4).
6. If textual representation remains impractical → serialize state (Level 5).
```

## 6. Operating Principles (agent behavior under PAP)

### 6.1 Autonomous Execution Rule

Continue work autonomously while it remains charter-compliant
(consistent with Authority Hierarchy levels 1–4), architecture-
compliant (consistent with `SYSTEM_ARCHITECTURE.md` and adopted
Decision Records), and evidence-supported (grounded in what the
repository shows — see Evidence Governance, PAP-State §6.1).

### 6.2 Escalation Protocol

Escalate when: requirements are genuinely ambiguous; governance
artifacts conflict in a way §4 does not resolve; evidence is
insufficient; or multiple valid paths exist with no selection criteria
**and** the choice would have lasting architectural or product
consequences. Routine implementation choices within an
already-authorized direction do not require escalation.

### 6.3 Adversarial Review Governance (summary)

Major governance revisions and major changes shall be reviewed from
multiple perspectives — validation, falsification, alternative
solution, and future reconstruction (full procedure: [PAP-AUDIT](../modules/PAP-AUDIT/PAP-AUDIT.md) §2,
APDRP). **Unresolved disagreements shall be preserved rather than
hidden** — this governs how *all* modules treat disagreement.

### 6.4 Operative-Version Discipline During Self-Revision

When a task revises this file or any module — the self-referential
case §6.3 and Finding F7 of the
[self-audit](../audits/2026-06-07_pap-self-audit.md) name — an agent
risks conflating two things that must stay distinct: *the governance
currently in force* (which it must keep following while it works) and
*the draft text it is producing* (which is not yet in force).

**Rule**: For the duration of such a task, the operative version is
the most recently committed/adopted content — anchored by git commit
hash, exactly as
[`CANONICAL_PROTOCOL_INDEX.md`](../revisions/CANONICAL_PROTOCOL_INDEX.md)
and [`PAP_CHARTER.md`](../../PAP_CHARTER.md) §2.2 already anchor
identity for living/DRAFT documents (§1.3). In-progress working-tree
edits are a *draft* and do not govern conduct — including the revising
agent's own — until committed and the index is updated to point at the
new commit.

**Procedure**:
1. At the start of the task, note the current commit hash — this is
   the pinned operative reference for the revision's duration.
2. If, mid-revision, a question arises about what the *current* rule
   says (as distinct from what it should say after the change), answer
   it from the pinned commit (e.g. `git show <hash>:<path>`) — not from
   the working tree, which may be self-contradictory mid-edit by design.
3. The draft becomes operative only when committed *and*
   `CANONICAL_PROTOCOL_INDEX.md` is updated to point at the new commit
   (its existing Maintenance Rule) — never silently, never before that.

This reuses infrastructure the repository already treats as trusted
(§8, Repository-Centric Operation; the index's commit-anchoring
pattern) rather than introducing a parallel draft directory or a
duplicate copy of governance — the Minimality Principle (§1.5)
counsels against adding a mechanism when a stable, content-addressed
one already exists for exactly this distinction.

This narrows, but does not close, Finding F7: who reviews a revision
to the review machinery itself remains a named open constitutional
question. What this resolves is the more immediate operational risk —
an agent conflating draft and operative text *while performing* such a
revision — which is answerable now, with infrastructure already at hand.

## 7. Reconstruction Requirement and Success Criterion

**Reconstruction Requirement**: A future operator shall be able to
reconstruct the project using repository artifacts alone. This is a
*standing* requirement — every governance act should be performed as
if the next reader has no other context.

**Success Criterion**: A future operator, using only repository
artifacts and PAP guidance, can understand, reconstruct, continue,
audit, recover, and improve the project, with minimal loss of intent,
reasoning, architecture, governance, or continuity.

## 8. Repository-Centric Operation

- The agent has access to a project repository, treated as
  **available protocol infrastructure**.
- No proprietary platform feature or vendor-specific capability is
  assumed — every governance act PAP requires must be performable with
  ordinary repository operations (files, directories, commits).
- **One specific property is relied on, and should be named honestly
  rather than left implicit**: §3 (Lineage Governance), §6.4
  (Operative-Version Discipline), and `CANONICAL_PROTOCOL_INDEX.md`'s
  identity model all anchor to commits *as content-addressed,
  cryptographically verifiable identities* — a Trusted Clock/Identity
  Source under §2.1's ordering. That property belongs to git (and
  similar DAG-based, content-addressed VCSs); it is not guaranteed by
  "files, directories, commits" in the generic sense — a centralized
  VCS that identifies revisions by sequential integer would satisfy
  the letter of that phrase while providing no content-addressed
  identity at all, and could not actually serve as this protocol's
  identity anchor. PAP does not require git *by name*; it requires
  whatever VCS is in use to provide *this specific guarantee*.
- [Compatibility](../compatibility/Platform-Compatibility-Profiles.md)
  is a registry of what has been *verified*, never a *dependency*.

## 9. Human Form / Machine Form Duality

- **Human Form** (Markdown): authoritative statement of intent,
  rationale, governance.
- **Machine Form** (YAML/JSON): a *projection* of the parts an agent
  must act on programmatically — manifests, schemas, thresholds.

**Precedence rule**: Human Form governs intent; Machine Form is
subordinate. On disagreement, the Human Form governs and the
disagreement is a Contradiction (PAP-State §6.4) requiring the Machine
Form to be regenerated.

**Scope rule**: Machine Form is *mandatory* for module manifests,
state/resume/handoff/audit schemas, and CBMF thresholds. It is
*optional and discouraged* for rationale, principles, and narrative
governance.

## 10. Module Governance

A **module** is a self-contained, independently-loadable unit of PAP
governance with a single clear responsibility, operating under
PAP-Core's authority.

1. **No duplication of Core.** A module shall not restate, redefine,
   or maintain its own copy of any governance in this file. It depends
   on Core and references it by name.
2. **Single responsibility.** A module's scope statement names what it
   governs and, where useful, what it explicitly does not.
3. **Registered in the manifest.** [`PAP-Core.manifest.yaml`](PAP-Core.manifest.yaml)
   lists every module, its location, scope, and load triggers. Adding,
   removing, or rescoping a module updates the manifest in the same
   revision.
4. **Loaded on demand.** Core is always loaded; modules load only when
   the active task's scope intersects their stated responsibility.
5. **Each module may carry Human Form and/or Machine Form** per §9.

---

## Active modules

See [`PAP-Core.manifest.yaml`](PAP-Core.manifest.yaml) for the
authoritative, machine-readable module registry. Currently registered:
[PAP-State](../modules/PAP-State/PAP-State.md),
[PAP-AUDIT](../modules/PAP-AUDIT/PAP-AUDIT.md),
[PAP-X](../modules/PAP-X/PAP-X.md),
[PAP-Serialize / UPCCP-CSP](../serialization/UPCCP-CSP/UPCCP-CSP.md),
[Compatibility](../compatibility/Platform-Compatibility-Profiles.md).

## Provenance

This file realizes Part I of
[Deliverable 4 — Canonical PAP Revision Proposal](../revisions/synthesis/04_Canonical_PAP_Revision.md).
It supersedes `PAP_2026-06-06_22-39_db890ad4.md`,
`UPCCMP_2026-06-06_22-09_6f0d84e1.md` (its cross-cutting governance —
Authority Hierarchy, Reconstruction Requirement/Success Criterion,
Autonomous Execution/Escalation), and
`PAP-Core_Completeness-Preference-Principle_2026-06-07-08-28.md` (now
adopted, no longer proposed). See Deliverable 4 Part IV for the full
supersession map and the Gap Analysis cross-reference.
