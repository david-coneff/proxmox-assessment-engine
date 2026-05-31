# Architecture

## System Role

The assessment engine is an **observer and documentarian**.

It sits at the bottom of the infrastructure stack:

```
OpenTofu          →  Declared State    (infrastructure definition)
Inventory/Ansible →  Configured State  (infrastructure realization)
Assessment Engine →  Observed State    (infrastructure observation)
Assessment History→  Historical State  (change tracking over time)
```

The engine answers:
- What infrastructure currently exists?
- What capabilities and services exist?
- What software and containers exist?
- What has changed over time?

The engine does NOT: recommend upgrades, purchases, or replacements; make subjective judgments; manage secrets; or perform configuration.

## Data Flow

```
Ansible Inventory
       ↓
  GuestCollector  ──→  ansible-inventory + ansible facts
       ↓
  Raw Audit JSON
       ↓
  Parser Layer    ──→  hardware / storage / network / proxmox / guest parsers
       ↓
  Normalized Assessment (assessment.schema.json + guest.schema.json)
       ↓
  ┌────┴────┐
  │         │
SQLite    Markdown Reports
History   (guest-assessment.md, ...)
  │
  └──→  Private History Repository (reports + DB + audit archives)
```

## Secrets Architecture

The engine **never** retrieves or stores credentials.

```
Assessment Engine → Ansible → Guest
```

NOT:

```
Assessment Engine → KeePassXC → Guest
```

Ansible owns authentication and transport. The engine may document *which* secret store is used (name only), never the values.

## Repositories

**Public repository** (this repo):
- Source code
- Schemas (`schemas/`)
- Documentation

**Private repository** (separate):
- Assessment reports
- Raw audit archives
- SQLite history database

## Schema Design

Schemas support future Declared / Configured / Observed comparison without redesign.

`assessment.schema.json` — top-level node assessment:
- `hardware`, `firmware`, `storage`, `network`, `os` — Proxmox node facts
- `virtualization` — PVE version, VMs, LXC containers, storage pools
- `guests[]` — assessed guest hosts (via Ansible)
- `state_sources` — metadata about declared / configured / observed state layers

`guest.schema.json` — per-guest facts:
- Identity: `hostname`, `inventory_name`, `groups`
- OS: `operating_system` (distribution, kernel, architecture)
- Resources: `cpu_count`, `memory_mb`, `mounted_filesystems`, `ip_addresses`
- Services: `running_services`, `enabled_services`
- Containers: `docker_containers`, `podman_containers`
- Provenance: `collection_method`, `provisioning_method`, `configuration_method`, `secret_source`

## Module Layout

```
collector/
  base.py          BaseCollector ABC
  registry.py      CollectorRegistry
  hardware.py      dmidecode + /proc/cpuinfo
  storage.py       lsblk, smartctl, zpool, vgs
  network.py       ip(8)
  proxmox.py       pveversion, pvesh, qm, pct
  guests.py        ansible-inventory + ansible fact modules

engine/
  cli.py           pae CLI entry point
  parser.py        decorator-based parser registry + parse_raw_audit()
  schema.py        JSON Schema validation (local $ref resolution)
  db.py            SQLite history (assessments, changes, guest_summaries)
  diff.py          Field-level diff engine + Change dataclass
  report.py        Node assessment report stub (Phase 4)
  report_guest.py  Guest assessment Markdown report

  modules/
    hardware_parser.py
    storage_parser.py
    network_parser.py
    proxmox_parser.py
    guest_inventory.py   Ansible inventory loading + fact normalization
    guest_parser.py

schemas/
  assessment.schema.json
  guest.schema.json

tests/
  test_cli.py
  test_collector_framework.py
  test_parser.py
  test_parsers.py
  test_history.py
  test_guest.py
```
