# UPCCP-CSP

Status: Canonical (realized from [Deliverable 4](../../revisions/synthesis/04_Canonical_PAP_Revision.md) Part II)
Operates under [PAP-Core](../../core/PAP-Core.md) authority and
[Serialization Governance](../Serialization-Governance.md). Loaded
when CBMF escalation has reached Level 5, or when decoding/producing a
UPCCP-CSP envelope.

**Scope**: The UPCCP-CSP wire format itself — "Universal Project
Continuity & Context Protocol — Compact State Protocol": a compact,
hashed, self-describing envelope for serialized runtime/working-memory
state. The CBMF Level 5 mechanism named (but not specified) by CPP/CBMF.

This is the first canonical specification for a format that previously
existed only as a worked example
([`examples/sample.upccp`](examples/sample.upccp), relocated here from
`sample_upccp.artifact` in the corpus root) — see
[Lineage Analysis](../../revisions/synthesis/01_Protocol_Lineage_Analysis.md) §2.3
for the "example before specification" history this resolves.

---

## 1. Envelope structure

```
<Format-ID>-<Format-Version>

<Header: key-value lines>
Encoding: <e.g. JSON>
Compression: <e.g. zlib>
Schema-ID: <registry identifier for the payload's schema>
Schema-Hash: SHA256:<hash of the schema definition>
Interpreter: <name of the canonical decoder contract>
Version: <envelope/schema version>
Payload-Hash: SHA256:<hash of the decompressed, decoded payload>

<Instructions: ordered decode steps, in prose, for portability>

-----BEGIN PAYLOAD-----
<binary/compressed payload, opaque at this layer>
-----END PAYLOAD-----
<Integrity footer: JSON object>
{
  "payload_sha256": "<must equal Payload-Hash above>",
  "bootstrap_sha256": "<hash of the minimal bootstrap/decoder reference>"
}
```

## 2. Header field contract

| Field | Meaning | Normative requirement |
|---|---|---|
| `Encoding` | logical format of the decompressed payload | must name a format the decoder can parse without external lookup (e.g. `JSON`) |
| `Compression` | compression applied before encoding into the envelope | must name a widely-available algorithm (e.g. `zlib`) — itself a [Compatibility](../../compatibility/Platform-Compatibility-Profiles.md) concern |
| `Schema-ID` | identifier into the **schema registry** | resolvable to a concrete schema definition (e.g. `PAP-RUNTIME-3` — see [`project-state.schema.yaml`](../../modules/PAP-State/schemas/project-state.schema.yaml)) |
| `Schema-Hash` | hash of that schema definition | lets a decoder verify it has the *correct version* of the schema before mapping state IDs |
| `Interpreter` | name of the canonical decoder contract | identifies which decode procedure governs (e.g. `UPCCP-Decoder`) — see §3 |
| `Version` | envelope/format version | governs which version of *this specification* applies |
| `Payload-Hash` | SHA-256 of the decompressed, decoded payload | integrity check — must match the footer's `payload_sha256` |

## 3. Schema registry

`Schema-ID` values (e.g. `PAP-RUNTIME-3`) resolve to schema
definitions that map opaque state identifiers in the payload to
meaningful structure — e.g.,
[PAP-State's `project-state.schema.yaml`](../../modules/PAP-State/schemas/project-state.schema.yaml)
or `governance-state.schema.yaml`. The registry is the bridge between
"this payload is well-formed" and "this payload means something": a
decoder with the envelope but not the registry entry can verify
integrity but cannot reconstruct meaning.

## 4. Decoder Contract (`UPCCP-Decoder`)

A conforming decoder shall, in order:

1. Parse the header and validate that all required fields are present.
2. Decompress the payload using the algorithm named in `Compression`.
3. Decode the decompressed bytes using the format named in `Encoding`.
4. Verify `SHA256(decoded payload) == Payload-Hash == footer.payload_sha256`
   — **abort and report integrity failure** on any disagreement; never
   proceed with an unverified payload.
5. Resolve `Schema-ID` in the schema registry and verify
   `SHA256(resolved schema) == Schema-Hash` — **abort and report a
   schema-mismatch** on disagreement (prevents misinterpreting state
   under the wrong schema version).
6. Map state identifiers in the payload through the resolved schema.
7. Reconstruct session/project state from the mapped structure.

## 5. Versioning rules

- The leading `<Format-ID>-<Format-Version>` line (e.g. `UPCCP-1.0`)
  governs which revision of *this specification* applies to
  interpreting the rest of the envelope.
- A change to the envelope's *structure* (header fields, footer shape,
  payload framing) requires a Format-Version increment.
- A change to a *referenced schema* requires only a `Schema-Hash`
  update — not a Format-Version change, because envelope structure is
  unaffected. This separation lets the wire format remain stable while
  the state shapes it carries evolve.

## 6. Reference example

[`examples/sample.upccp`](examples/sample.upccp) is the canonical
worked instance of this format and shall be kept consistent with this
specification as it evolves. If the two diverge, that divergence is a
finding to be raised through [PAP-AUDIT](../../modules/PAP-AUDIT/PAP-AUDIT.md) §3
— not silently resolved in either direction.

## Provenance

Realizes the wire-format-specification portion of Part II
("PAP-Serialize (UPCCP-CSP)") of
[Deliverable 4](../../revisions/synthesis/04_Canonical_PAP_Revision.md) §2,
derived entirely from the header fields, structure, and instructions
observed in the worked example artifact (no prior specification
existed — see [Gap Analysis](../../revisions/synthesis/02_Gap_Analysis.md) §2.1).
