# Next Steps

All planned phases are complete.

## Implemented this session (2026-06-08 UTC) — operator-directed, see AD-058

- **Second-factor authentication is now the default for the KeePass unlock
  gate** (was opt-in/off). Per direct operator instruction, `keepass_mfa.py`
  (already implemented: RFC 6238 TOTP + YubiKey HMAC-SHA1, 49 tests, never
  offered SMS/email OTP) is now reached by default —
  `KeePassInitConfig.mfa_method` / `forge_keepass_init.py --mfa` flipped
  `"none"` → `"totp"`. See `ARCHITECTURE.md` AD-058 for the full record,
  including the **named, not-yet-closed gap**: `guided_setup.py`/
  `forge_planner.py` don't yet prompt for MFA interactively (candidate for
  a future scoped item, much like Phase 1.H).
- **`ROADMAP.html` and `docs/FEATURE-HISTORY.html` regenerated with
  collapsible (`<details>`/`<summary>`) sections** via the existing
  `proxmox-bootstrap/md_to_html.py --collapsible`, per direct operator
  request ("the roadmap... is quite lengthy"). Regeneration also closed a
  content-drift gap (missing `<h3>` sections) that the stamp-only
  `test_meta_doc_sync.py` could not detect.

## Proposed (scoped, not started)

- **Phase 1.H — Pre-Install Forge Package and Image Builder** — surfaced by
  analysis of the `new/` proposed-revision corpus (PAP-AUDIT finding F3,
  now closed). Closes the gap between today's only supported path
  ("operator already has Proxmox VE installed on the target host," per
  `FORGING.md`'s prerequisites) and a true bare-metal start: a workstation
  Image Builder that bundles an unattended Proxmox VE installer, the forge
  package, and a first-boot automation hook into a single bootable ISO/USB
  image. Additive — the existing path remains the supported baseline. See
  `ROADMAP.md` "Proposed Future Work — from `new/` corpus analysis" and
  `ARCHITECTURE.md` AD-057 for the full scope and rationale.

## Draft sketches (awaiting operator reaction — not yet scoped phases)

- **Recovery-Readiness Conformance** — reframes the formal axiomatic-kernel/
  proof-system slice of the `new/` corpus (which the operator partially
  un-deferred) around two concrete concerns: provable recovery readiness, and
  observed-state-vs-intent-manifest conformance. Names one new artifact worth
  scoping further: a `recovery-readiness-certificate.json`/HTML composing
  existing readiness/drift/drill outputs into one timestamped record. See
  `ROADMAP.md` "Proposed Future Work → DRAFT SKETCH — Recovery-Readiness
  Conformance."
- **Hypervisor Recovery Credentials** — operator asked for a thorough
  evaluation of permanently storing Proxmox root passwords in KeePass (vs.
  today's discard-after-spawn temporary passphrase). Recommends against an
  *autonomous* pathway that can wield full root against live hypervisors
  (unbounded blast-radius risk), and instead sketches: (1) constrained
  forced-command recovery accounts for routine diagnostics, (2) full root as
  break-glass behind the *existing* human-unlock gate (AD-042) — no new
  autonomous pathway, (3) pre-generated spawn-media credentials with
  human-gated joining (the operator's own proposed safeguard, and cheap to
  build). **Operator endorsed this "middle path" (2026-06-08 UTC: "the
  middle path you suggest ... seems like the reasonable approach rather
  than storing root permanently in keepass")** — confirmation recorded;
  the sketch itself is not yet promoted to a scoped phase/AD (would need a
  follow-up "go ahead and scope this" to do so). See `ROADMAP.md` "Proposed
  Future Work → DRAFT SKETCH — Hypervisor Recovery Credentials."
- **Granular Secret Access Silos for Human Operators** — operator asked
  whether tiered, hierarchically-scoped human access to secrets is feasible
  (service operator vs. "god-mode" sysadmin; scoped to a cell/node/VM).
  "God mode" remains the correct default for the operator's homelab; this is
  framed for a hypothetical larger org. Sketches a design that fits
  broodforge's KeePass-centric, offline-first model with no new dependency:
  derive scoped sub-vaults from the canonical database using the hierarchy
  `secret-registry.yaml` already encodes (`owning_cell`, `required_by:
  [host:X]/[vm:X]`), each with its own generated passphrase, mintable only by
  holders of the canonical "god mode" vault. Names "revocation = rotate +
  reissue, not real-time removal" as an explicit, honest non-guarantee. See
  `ROADMAP.md` "Proposed Future Work → DRAFT SKETCH — Granular Secret Access
  Silos for Human Operators."

## Future (unscoped)

- **Multi-node cluster assessment** — run assessment against all Proxmox cluster members in a single pass; aggregate into a cluster-level report.
- **Dynamic inventory improvements** — support cloud provider inventories (AWS EC2, GCP, Azure), custom inventory scripts.
- **OpenTofu remote state** — support S3/GCS/Azure remote state backends in addition to local state files.
- **Report index** — generate a chronological index of all stored reports in the private history repository.
