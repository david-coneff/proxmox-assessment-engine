# Serialization Governance

Status: Canonical (realized from [Deliverable 4](../revisions/synthesis/04_Canonical_PAP_Revision.md) Part II)
Operates under [PAP-Core](../core/PAP-Core.md) authority.

**Scope**: Destination-aware governance of *when* and *how* to select
a serialization mechanism — distinct from any single wire format's
specification (the format itself lives in
[`UPCCP-CSP/UPCCP-CSP.md`](UPCCP-CSP/UPCCP-CSP.md)).

PAP-Serialize **transports** state; [PAP-State](../modules/PAP-State/PAP-State.md)
**manages** it. This module shall not define what gets tracked about a
project — only how an already-assembled state blob is packaged for
transport.

## 1. When to invoke serialization

Serialization is invoked only when CBMF escalation
([PAP-Core](../core/PAP-Core.md) §5.2) has genuinely reached **Level
5** — i.e., Levels 0–4 have been attempted and found insufficient for
the content and situation at hand. Reaching for serialization before
exhausting the lower levels is itself a CPP violation (preferring a
compact-but-opaque representation over a more transparent one that
would still have fit).

## 2. Destination-aware format selection

The chosen format must be one the intended recipient (a future
session, a different agent, a different platform) can actually decode.
Recording *which* combinations have been verified to interoperate is
[Compatibility](../compatibility/Platform-Compatibility-Profiles.md)'s
job — Serialization Governance consults that registry before
selecting a format for a given destination; it does not maintain its
own separate compatibility ledger (that would duplicate Compatibility's
scope).

## 3. Available mechanisms

| Mechanism | Specification |
|---|---|
| UPCCP-CSP | [`UPCCP-CSP/UPCCP-CSP.md`](UPCCP-CSP/UPCCP-CSP.md) |

Additional serialization mechanisms may be registered here as they are
specified — each entry in this table points to its own governing
specification rather than restating it (Module Governance,
[PAP-Core](../core/PAP-Core.md) §10, applied at sub-module granularity).

## Provenance

Realizes the "Serialization Governance" portion of Part II
("PAP-Serialize (UPCCP-CSP)") of
[Deliverable 4](../revisions/synthesis/04_Canonical_PAP_Revision.md) §1.
