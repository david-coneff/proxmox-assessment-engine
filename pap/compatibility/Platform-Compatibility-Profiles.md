# Platform Compatibility Profiles

Status: Canonical (realized from [Deliverable 4](../revisions/synthesis/04_Canonical_PAP_Revision.md) Part II)
Operates under [PAP-Core](../core/PAP-Core.md) authority. Loaded when
selecting a serialization format or evaluating whether a given
execution environment has known compatibility issues.

**Scope**: A registry — **not a dependency** — of *empirically
verified* combinations of (protocol version, module version, execution
environment, agent/tool) known to interoperate correctly.

This module exists to satisfy [PAP-Core](../core/PAP-Core.md) §8's
promise that PAP "depends on nothing beyond a repository," while still
letting operators ask, practically: *has this combination been tried,
and did it work?*

## Profile entry contract

Each profile entry records:

- the combination tested (protocol/module versions, execution
  environment, agent or tool),
- the date and method of verification,
- the result — including any caveats or partial-compatibility notes,
- a pointer to supporting evidence (Evidence Governance,
  [PAP-State](../modules/PAP-State/PAP-State.md) §6.1).

## Boundary rule

Compatibility records *facts about what has been observed to work*. It
does not, and may not, become a place where platform-specific
*requirements* creep into the specification layer — doing so would
violate implementation independence
([Architecture Recommendation](../revisions/synthesis/03_Canonical_Architecture_Recommendation.md) §2.3).

If a compatibility finding suggests the *specification itself* should
change (e.g., "this rule is impossible to satisfy on platform X"),
that is a Decision Record ([PAP-State](../modules/PAP-State/PAP-State.md) §6.2)
and possibly an Escalation ([PAP-Core](../core/PAP-Core.md) §6.2) — not
a silent edit to this registry.

## Current profile records

None recorded yet. This file is the registry's home; entries are added
as combinations are actually verified during real operation (per the
instance/schema distinction — see [Architecture Recommendation](../revisions/synthesis/03_Canonical_Architecture_Recommendation.md) §6,
"schema-template confusion" risk and its mitigation).

## Provenance

Realizes the "Compatibility" portion of Part II of
[Deliverable 4](../revisions/synthesis/04_Canonical_PAP_Revision.md). Named
only as a one-line stub ("PCP Registry — Verified platform
compatibility records") in the prior modular package scaffold; this
file gives that stub its first governing content.
