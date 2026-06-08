# Next Steps

All planned phases are complete.

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

## Future (unscoped)

- **Multi-node cluster assessment** — run assessment against all Proxmox cluster members in a single pass; aggregate into a cluster-level report.
- **Dynamic inventory improvements** — support cloud provider inventories (AWS EC2, GCP, Azure), custom inventory scripts.
- **OpenTofu remote state** — support S3/GCS/Azure remote state backends in addition to local state files.
- **Report index** — generate a chronological index of all stored reports in the private history repository.
