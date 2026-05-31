# Roadmap

## Phase 1 – Foundation ✓
- Assessment schema
- CLI framework
- Collector framework (hardware, storage, network, proxmox)
- Parser framework

## Phase 2 – Node Parsers ✓
- Hardware parsers (CPU, memory, DMI, BIOS, OS)
- Storage parsers (disks, ZFS, LVM)
- Network parsers (interfaces, bonds, bridges, VLANs)
- Proxmox parsers (PVE version, cluster, VMs, LXC, storage pools)

## Phase 3 – SQLite History ✓
- HistoryDB (assessments, changes tables)
- Field-level diff engine
- CLI: store, history, diff

## Phase 3b – Guest Inventory ✓
- Guest schema (guest.schema.json)
- Ansible inventory loading (YAML, INI, dynamic)
- Ansible fact collection (setup, service_facts, docker, podman)
- Guest normalization (OS, services, containers, provenance metadata)
- Guest parser + state_sources framework (Declared/Configured/Observed)
- Guest assessment report (guest-assessment.md)
- SQLite guest_summaries history table
- CLI: guest-collect, guest-report
- Secrets architecture enforced (no credentials stored or retrieved)

## Phase 4 – Report Generation ✓
- Full node assessment Markdown report (engine/report.py)
- Combined node + guest Markdown report (engine/report_combined.py)
- CLI: pae report, pae full-report

## Phase 5 – History Repository Integration
- GitHub / Forgejo push of reports and SQLite DB to private history repo
- Authentication delegated to external tools (SSH keys, tokens, SSH agent)
- Support both GitHub and Forgejo APIs
- CLI: pae push

## Phase 6 – OpenTofu Declared State Ingestion ✓
- Parse OpenTofu / Terraform state files (terraform.tfstate, format v3/v4)
- Normalize declared resources into assessment schema (declared_resources[])
- Populate state_sources.declared with version, serial, resource count
- Map declared VMs/containers → configured inventory → observed guests
- Produce Declared vs Configured vs Observed comparison report
- CLI: pae opentofu-ingest, pae compare

## Future (not yet scoped)
- Multi-node cluster assessment (assess all PVE cluster members)
- Dynamic inventory improvements (custom scripts, cloud providers)
