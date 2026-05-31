# Tier 2 Bootstrap State Collection

The Tier 2 collector (`collect-tier2.py`) connects to the live Proxmox host over
SSH and populates `bootstrap-state.json` with discovered system state. It is safe
to run repeatedly — existing entries are never overwritten.

---

## What It Collects

| Array | Source | Fields auto-populated | Fields requiring manual entry |
|---|---|---|---|
| `templates` | `qm list` + `qm config` for template VMIDs | `name`, `proxmox_template_id`, `created_at`, `base_image`, `build_notes` | `additional_packages` |
| `base_images` | Inferred from template ISO name (in description/notes or CD-ROM drive config) | `name`, `source_iso`, `created_at` | `source_url`, `checksum`, `included_packages` |
| `provenance_records` | `qm list` + `qm config` for non-template VMIDs | `vmid`, `name`, `deployed_at` (config file mtime), `template_name` (if recorded in VM description) | `tofu_workspace`, `tofu_commit`, `ansible_commit`, `cloudinit_*_hash`, `deployed_by` |

**Important:** `base_images[].checksum` is never auto-populated — it must be entered
manually from the verified ISO download. This is intentional: automatic checksum
collection would require reading the ISO off the host, which is slow and unreliable.

---

## Prerequisites

- SSH access to the Proxmox host as `root` (or a user with `qm` and `pvesm` permissions)
- SSH key-based authentication (password auth not supported)
- Python 3.10+ on the machine running the collector (stdlib only — no pip install)

---

## Usage

### Basic run (auto-detect bootstrap-state.json)

```bash
python3 proxmox-bootstrap/collect-tier2.py --host 192.168.1.10
```

### Dry run — see what would be written without modifying anything

```bash
python3 proxmox-bootstrap/collect-tier2.py --host 192.168.1.10 --dry-run
```

### Non-root SSH user

```bash
python3 proxmox-bootstrap/collect-tier2.py \
    --host 192.168.1.10 \
    --user dave \
    --key ~/.ssh/proxmox_key
```

### Explicit state file path

```bash
python3 proxmox-bootstrap/collect-tier2.py \
    --host 192.168.1.10 \
    --state /path/to/bootstrap-state.json
```

### Verbose (shows raw SSH command output)

```bash
python3 proxmox-bootstrap/collect-tier2.py --host 192.168.1.10 --verbose
```

---

## Merge Behaviour

The collector uses a **merge-only** strategy:

- **Existing entries are never modified.** If `vmid: 101` already has a
  `provenance_records` entry with `tofu_commit` filled in, that record is left
  untouched even if the collector finds the same VMID on the host.
- **Only absent entries are appended.** VMIDs, template IDs, and base image names
  not yet in `bootstrap-state.json` are added.
- **Keys used for deduplication:**
  - `provenance_records` → `vmid`
  - `templates` → `proxmox_template_id`
  - `base_images` → `name`

This means you can run the collector immediately after provisioning a new VM and it
will add a skeleton provenance record — then fill in deployment fields by hand or
via the provenance recorder in `proxmox-bootstrap/provenance/`.

---

## After Collection

### 1. Verify the output

```bash
python3 proxmox-bootstrap/collect-tier2.py --host 192.168.1.10 --dry-run | python3 -m json.tool
```

### 2. Fill in manual fields

Open `bootstrap-state.json` and complete:

- `base_images[*].source_url` — download URL for the ISO
- `base_images[*].checksum` — verified SHA256 of the ISO
- `base_images[*].included_packages` — packages baked into the base image
- `provenance_records[*].tofu_workspace` — OpenTofu workspace name
- `provenance_records[*].tofu_commit` — git commit of the OpenTofu state
- `provenance_records[*].ansible_commit` — git commit of the Ansible run
- `provenance_records[*].deployed_by` — who provisioned the VM

### 3. Commit the updated state

```bash
git add proxmox-bootstrap/bootstrap-state.json
git commit -m "Tier 2 collection run $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

---

## ISO Name Inference

The collector derives base image names from ISO filenames using these rules:

| ISO filename | Derived base_image name |
|---|---|
| `ubuntu-22.04.4-live-server-amd64.iso` | `ubuntu-2204-base` |
| `debian-12.5.0-amd64-netinst.iso` | `debian-12-base` |
| `talos-v1.7.0-metal-amd64.iso` | `talos-17-base` |
| anything else | `<first-segment>-base` |

If the ISO name cannot be inferred from the template config, the base image entry
is omitted and `base_image` in the template entry is set to the template name.

---

## Troubleshooting

**SSH connection refused**
- Confirm the host IP is reachable: `ping 192.168.1.10`
- Confirm SSH is running on the Proxmox host: `ssh root@192.168.1.10`
- If using a non-standard port: add `--port <port>`

**`qm: command not found`**
- The SSH user does not have access to Proxmox tools. Use `--user root` or
  ensure the user is in the `PVEAuditor` role.

**Template detected but no base_image entry created**
- The template's qm config has no ISO reference in description, notes, or CD-ROM
  drive slots. Add a `notes: template: ubuntu-2204-base` line to the template's
  description in Proxmox, then re-run the collector.

**Provenance record missing `template_name`**
- The VM's qm config notes don't contain a `template:` line. Add
  `template: ubuntu-2204-base` to the VM's description in Proxmox, then re-run.
  Or populate `template_name` manually in `bootstrap-state.json`.
