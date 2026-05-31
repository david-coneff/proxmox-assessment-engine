# Current State

Version: 0.8

## Completed

### Phase 1 – Foundation ✓
- Assessment schema, CLI, collector framework, parser framework, schema validation.

### Phase 2 – Node Parsers ✓
- Hardware, storage, network, Proxmox parsers.

### Phase 3 – SQLite History ✓
- HistoryDB (`assessments`, `changes`, `guest_summaries`), diff engine.
- CLI: `pae store`, `pae history`, `pae diff`.

### Phase 3b – Guest Inventory ✓
- `guest.schema.json`, guest inventory collection via Ansible, guest parser, guest report.
- CLI: `pae guest-collect`, `pae guest-report`.

### Phase 4 – Report Generation ✓
- Full node report, combined node+guest report.
- CLI: `pae report`, `pae full-report`.

### Phase 5 – History Repository Integration ✓
- `engine/repo.py` — push to GitHub / Forgejo via Contents API.
- CLI: `pae push`.

### Phase 6 – OpenTofu Declared State Ingestion ✓

- **`schemas/declared_resource.schema.json`** — per-resource schema: resource_type, resource_name, provider, module, instance_index, taint, status, attributes (name, target_node, vmid, cores, memory, disk_size, network_interfaces, tags, description).
- **`assessment.schema.json`** extended with `declared_resources[]` and enriched `state_sources.declared` (terraform_version, serial, resource_count).
- **`engine/opentofu.py`** — parses `terraform.tfstate` (format v3/v4):
  - `parse_state_file(path)` → `StateParseResult` with resources, meta, errors.
  - Normalises provider strings, extracts VM/LXC attributes, parses semicolon-separated tags, handles tainted/deposed instances.
  - Detects opentofu vs terraform from version string.
  - `ingest_state(assessment, path)` — merges declared_resources + state_sources.declared into assessment. Raises `RuntimeError` on unreadable/unparseable state files.
- **`engine/compare.py`** — `compare(assessment) → ComparisonResult`:
  - Maps declared resources → configured inventory → observed guests by normalised short hostname.
  - Produces `matches` (≥2 layers), `declared_only`, `observed_only`, `configured_only`.
  - FQDN-aware: `web01.lab.example.com` matches declared `web01`.
  - `ComparisonResult.summary()` returns counts.
- **`engine/report_compare.py`** — `generate_comparison_report(assessment)`:
  - Sections: State Layer Sources, Summary, Matched Resources, Declared but Not Observed, Observed but Not Declared, Configured but Not Observed or Declared, All Declared Resources.
  - No recommendations generated.
- **CLI** — `pae opentofu-ingest --state FILE [--input FILE] [--output FILE]` and `pae compare --input FILE [--output FILE]`.
- **58 tests** covering: state parsing, attribute normalisation, provider parsing, taint detection, error handling, tool detection, `ingest_state`, schema validation with declared resources, comparison engine (including FQDN matching), comparison report, CLI commands.

## Roadmap Status

| Phase | Status |
|-------|--------|
| 1 Foundation | ✓ |
| 2 Node Parsers | ✓ |
| 3 SQLite History | ✓ |
| 3b Guest Inventory | ✓ |
| 4 Report Generation | ✓ |
| 5 History Repository | ✓ |
| 6 OpenTofu Declared State | ✓ |

## Test Summary

| Module | Tests |
|--------|-------|
| CLI framework | 7 |
| Collector framework | 7 |
| Parser framework | 6 |
| Node/storage/network/PVE parsers | 29 |
| SQLite history + diff | 33 |
| Guest inventory + report | 65 |
| Node + combined reports | 43 |
| Repo push | 38 |
| OpenTofu / compare / compare report | 58 |
| **Total** | **286** |

## Remaining (Future)

- Multi-node cluster assessment
- Dynamic inventory improvements (cloud providers, custom scripts)
