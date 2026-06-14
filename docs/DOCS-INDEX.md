# Broodforge Documentation Index

This index is the sysadmin-facing entry point for all broodforge documentation.
It is intended for integration with the Control Nexus operator dashboard.

All documents listed here are generated from Markdown source files via
`proxmox-bootstrap/md_to_html.py`. To regenerate any document (or all documents)
after a style update or source change, run:

```bash
python3 proxmox-bootstrap/regenerate_docs.py
```

The document manifest at `proxmox-bootstrap/doc-manifest.json` is the authoritative
registry of all registered documents, their source paths, output paths, and generation flags.

---

## Runbooks

These are interactive walkthrough documents for operational procedures. Each provides
structured input fields, live parameter injection into commands, encrypted export for
audit records, and session notes. Runbooks should be executed with the operator working
through the document top-to-bottom, filling in each field as they go.

**[PHOENIX — Stargate Process](PHOENIX.html)**

The procedure for recovering a failed broodforge node onto new hardware. PHOENIX
guides the operator through disconnecting the failed node from the cluster, forging
its replacement, migrating state, and promoting the new node to full membership.
This is the primary disaster recovery runbook. Every operator should be familiar
with this process before it is needed. Pair with the Reconstruction Drill (below)
to validate readiness.

**[FORGING — Hatchery Build](FORGING.html)**

The procedure for building the first broodforge hatchery node from bare hardware.
This is the starting point for a new broodforge deployment. It covers hardware
preparation, Proxmox installation, initial bootstrap configuration, DDNS setup,
TLS certificate issuance, and k3s cluster initialisation. This runbook is executed
once per hatchery and then archived.

**[NODE-SPAWNING — Hatchery Process](NODE-SPAWNING.html)**

The procedure for adding a new broodling node to an existing hatchery. Covers
network boot setup, Proxmox configuration, k3s worker join, and state synchronisation.
Run this whenever a new physical machine is added to an existing cluster.

**[Reconstruction Drill](RECONSTRUCTION-DRILL.html)**

A guided drill that validates the full stargate recovery process without requiring an
actual hardware failure. The drill walks the operator through simulating a node failure,
executing selected PHOENIX steps in a controlled manner, and verifying that recovery
procedures work as expected. This should be run periodically (recommended: quarterly)
to maintain readiness and catch documentation or process drift before it matters.

**[Tier 2 State Collection](TIER2-COLLECTION.html)**

SSH-based state collection from cluster nodes. Used when a node's local collection
agent is not running (e.g. during bootstrap or following a partial failure). Provides
commands and field inputs for collecting, validating, and submitting node state to
the broodforge state registry.

---

## Setup Guides

Step-by-step configuration guides for platform components. Unlike runbooks, setup
guides are referenced during initial deployment and may be consulted again when
reconfiguring a component. They include parameter injection for site-specific values.

**[DuckDNS Setup](DUCKDNS-SETUP.html)**

Configuration guide for operators using DuckDNS as their DDNS provider. Covers
subdomain creation, token management, broodforge DDNS auto-update timer, acme.sh
installation, Let's Encrypt DNS-01 certificate issuance for `*.yourhatchery.duckdns.org`,
and cert sync into Kubernetes secrets. Use this if you do not have your own domain.
See the Cloudflare Setup guide if you have your own domain.

**[Cloudflare Setup](CLOUDFLARE-SETUP.html)**

Configuration guide for operators using Cloudflare for DNS and DDNS. Covers API
token creation, Cloudflare DNS record setup, broodforge DDNS auto-update, certbot
with the Cloudflare DNS-01 plugin, cert-manager ClusterIssuer configuration, and
wildcard certificate management. Preferred over DuckDNS if you have your own domain.

**[Cloud Storage Setup](CLOUD-STORAGE-SETUP.html)**

Setup guides for all supported backup storage destinations: Backblaze B2, AWS S3,
Cloudflare R2, Google Drive, and MinIO. Each section covers bucket/credential creation,
IAM policy, restic repository initialisation, and connection testing. The broodforge
backup agent supports any combination of these destinations simultaneously.

**[Snippet Upload](SNIPPET-UPLOAD.html)**

How to upload and manage Cloud-Init snippets in the Proxmox snippet store. Used
during node spawning and recovery. Covers Proxmox storage configuration, snippet
upload via the web UI and API, and troubleshooting common upload errors.

---

## Reference Documents

Technical references, decision records, and system documentation. These documents
explain how broodforge is designed, why decisions were made, and what the current
system inventory looks like.

**[Broodforge README](README.html)**

Primary overview of the broodforge project: what it is, how it is structured,
the hardware model (hatchery + broodlings), the key processes (spawning, stargate,
sentinel), design constraints, naming conventions, and the spawn workflow step-by-step.
Start here if you are new to the project.

**[Broodforge Architecture](ARCHITECTURE.html)**

Architecture decision records (ADs) for the key structural choices in broodforge.
Each entry documents the decision, the options that were considered, the rationale
for the choice made, and the consequences. Covers cluster topology, state model,
backup strategy, networking model, and service architecture.

**[Broodforge Roadmap](ROADMAP.html)**

The full development roadmap with phase milestones and current status. Describes
what has been built (Phase 0 and Phase 1 bootstrap), what is in progress (Phase 2
cluster services), and what is planned (Phase 3 portal, Phase 4 multi-hatchery).

**[User Registry](USER-REGISTRY.html)**

User lifecycle management reference. Covers operator and end-user account models,
onboarding and offboarding procedures, service adapter conventions (how broodforge
provisioning hooks into each hosted service), and the expectations engine for user
operations (how long each lifecycle event takes to propagate).

**[Talos Alternative](TALOS-ALTERNATIVE.html)**

Evaluation of Talos Linux as a potential alternative Kubernetes substrate to k3s.
Documents the comparison of Talos against broodforge's design constraints, the
trade-offs considered, and the rationale for continuing with k3s + Proxmox rather
than switching. Retained as a decision record in case the evaluation needs to be
revisited.

**[Feature History](FEATURE-HISTORY.html)**

Chronological log of significant feature additions to the broodforge platform.
Each entry records what was added, why, and when. Useful for understanding the
evolution of the system and for tracking when a given capability became available.

**[Design History](DESIGN-HISTORY.html)**

Historical record of key design decisions and architecture evolution. Complements
the Architecture ADs by providing the narrative and chronology of how the design
arrived at its current state, including approaches that were tried and abandoned.

**[Audit Findings](AUDIT-FINDINGS.html)**

Recorded audit findings from PAP conformance reviews and internal architecture
audits. Each finding documents what was observed, severity, the resolution or
accepted risk, and the date resolved. Open findings are highlighted at the top
of the document.

---

## Meta Documentation

**[About This Documentation](ABOUT-DOCS.html)**

How the interactive documentation system works. Explains every field type, the
session notes panel, parameter injection, collapsible sections, the export package,
inline editing, attachments, and how to regenerate docs. Read this if you are
authoring new documentation or helping operators understand the interface.

**[Documentation Index](DOCS-INDEX.html)**

This page.

---

## Document Pipeline

All HTML documentation in this index is generated by the same pipeline:

```
Markdown source (.md)
      ↓
proxmox-bootstrap/md_to_html.py
      ↓
Self-contained HTML output (.html)
```

The manifest (`proxmox-bootstrap/doc-manifest.json`) registers every document. To add
a new document:

1. Create the Markdown source file
2. Add an entry to `doc-manifest.json` with the source path, output path, title, flags, type, and description
3. Run `python3 proxmox-bootstrap/regenerate_docs.py --id your-new-doc-id`

To check conformance (all registered sources exist, no stale outputs):

```bash
python3 proxmox-bootstrap/regenerate_docs.py --check
```

Hand-authored HTML is not permitted. All HTML documents must have a registered Markdown source.
