# Snippet Upload Procedure

Cell: proxmox-cell-a

This document describes how to prepare and upload Cloud-Init snippets to Proxmox
snippet storage so they can be referenced by VMs via the `cicustom` parameter.

**Network configuration values (gateway, subnet, nameservers, interface) are declared
once in `bootstrap-state.json` under `network_topology`. Do not edit the
`snippets/network-config/` files directly — regenerate them instead (Step 1 below).**

---

## Prerequisites

- Proxmox host is installed and accessible (SSH root access or API token)
- A Proxmox storage location with `snippets` content type enabled
  - Default: `local` storage at `/var/lib/vz/snippets/`
  - Verify: Proxmox UI → Datacenter → Storage → local → Content (must include "Snippets")
- SSH public keys have been retrieved from KeePass for each VM
- This repository is cloned on the operator workstation

---

## Step 1 — Regenerate Network-Config Snippets

If this is a new deployment or you have changed `network_topology` or any VM IP
in `bootstrap-state.json`, regenerate the network-config snippets before uploading:

```bash
# From the proxmox-bootstrap/ directory:
python3 generate-network-configs.py --bootstrap bootstrap-state.json

# Or from the repository root:
python3 proxmox-bootstrap/generate-network-configs.py --bootstrap proxmox-bootstrap/bootstrap-state.json
```

This reads `network_topology` (gateway, CIDR, nameservers, interface) and each VM's
`initial_ip` from `bootstrap-state.json` and writes all `snippets/network-config/*.yaml`
files. The generated files carry a `# GENERATED` header — do not edit them manually.

To preview without writing files:
```bash
python3 generate-network-configs.py --dry-run
```

Commit the regenerated files before uploading to Proxmox.

---

## Step 2 — Populate SSH Public Keys

Before uploading, replace the `POPULATE:` placeholder in each user-data file with
the actual SSH public key for that VM.

Retrieve public keys from KeePass using the paths in `secret-registry.yaml`:

| VM | KeePass Path (private key) | User-data file |
|---|---|---|
| infra-bootstrap | `Infrastructure/ssh/deploy-keys/infra-bootstrap` | `snippets/user-data/infra-bootstrap.yaml` |
| forgejo | `Infrastructure/ssh/deploy-keys/forgejo` | `snippets/user-data/forgejo.yaml` |
| inventory | `Infrastructure/ssh/deploy-keys/inventory` | `snippets/user-data/inventory.yaml` |
| assessment-engine | `Infrastructure/ssh/deploy-keys/assessment-engine` | `snippets/user-data/assessment-engine.yaml` |

In each user-data file, replace:
```yaml
ssh_authorized_keys:
  - "POPULATE: SSH public key — KeePass: <path>"
```

With the actual public key:
```yaml
ssh_authorized_keys:
  - "ssh-ed25519 AAAA... ubuntu@infra-bootstrap"
```

**Important:** The SSH *public* key is not a secret and is safe to include in the
snippet file. The SSH *private* key remains in KeePass and is never stored here.

---

## Step 3 — Upload Snippets to Proxmox

### Option A — Direct SCP (simplest)

```bash
# Upload all user-data snippets
scp snippets/user-data/*.yaml root@192.168.1.10:/var/lib/vz/snippets/

# Upload all network-config snippets
scp snippets/network-config/*.yaml root@192.168.1.10:/var/lib/vz/snippets/

# Upload vendor-data (infra-bootstrap only)
scp snippets/vendor-data/proxmox-hooks.yaml root@192.168.1.10:/var/lib/vz/snippets/
```

### Option B — Proxmox API (scriptable)

```bash
# Authenticate and upload via pvesm
# Run on the Proxmox host after SSH:
pvesm path local:snippets

# Or use the Proxmox API:
curl -X POST https://192.168.1.10:8006/api2/json/nodes/pve01/storage/local/upload \
  -H "Authorization: PVEAPIToken=root@pam!tofu=<token>" \
  -F "content=snippets" \
  -F "filename=@snippets/user-data/infra-bootstrap.yaml"
```

### Option C — Via Proxmox Web UI

Datacenter → Storage → local → Content → Upload → select file → set path to `snippets/`

---

## Step 4 — Verify Upload

After uploading, verify all snippets are present on the Proxmox host:

```bash
ssh root@192.168.1.10 ls -la /var/lib/vz/snippets/
```

Expected output — the following files must be present:

```
infra-bootstrap.yaml         (user-data)
forgejo.yaml                 (user-data)
inventory.yaml               (user-data)
assessment-engine.yaml       (user-data)
network-config-infra-bootstrap.yaml   ← renamed on upload (see note below)
network-config-forgejo.yaml
network-config-inventory.yaml
network-config-assessment-engine.yaml
proxmox-hooks.yaml           (vendor-data)
```

**Naming note:** Network-config files may share names with user-data files in the
same storage directory. Prefix network-config files with `network-config-` when
uploading to avoid collisions:

```bash
# Rename on upload:
scp snippets/network-config/infra-bootstrap.yaml \
    root@192.168.1.10:/var/lib/vz/snippets/network-config-infra-bootstrap.yaml
```

If you rename files on upload, update the `network_config_path` entries in
`bootstrap-state.json` to match the actual storage paths.

---

## Step 5 — Reference Snippets in VM Configuration

Snippets are referenced in OpenTofu VM resource definitions via the `cicustom`
attribute, or manually via `qm set`:

### Via OpenTofu (preferred)

```hcl
resource "proxmox_vm_qemu" "forgejo" {
  # ...
  cicustom = join(",", [
    "user=local:snippets/forgejo.yaml",
    "network=local:snippets/network-config-forgejo.yaml"
  ])
}
```

### Via qm (manual)

```bash
qm set 101 --cicustom "user=local:snippets/forgejo.yaml,network=local:snippets/network-config-forgejo.yaml"
```

### infra-bootstrap (includes vendor-data)

```bash
qm set 100 --cicustom "user=local:snippets/infra-bootstrap.yaml,network=local:snippets/network-config-infra-bootstrap.yaml,vendor=local:snippets/proxmox-hooks.yaml"
```

---

## Step 6 — Record Hashes in Bootstrap State

After uploading, record the SHA-256 hash of each uploaded file in `bootstrap-state.json`
under each VM's `cloudinit.user_data_hash` and `cloudinit.network_config_hash` fields.

```bash
sha256sum snippets/user-data/infra-bootstrap.yaml
sha256sum snippets/network-config/infra-bootstrap.yaml
```

These hashes allow the Tier 2 assessment to detect if deployed snippets have drifted
from the repository versions.

---

## Snippet Reference Table

| VM | VMID | user-data | network-config | vendor-data |
|---|---|---|---|---|
| infra-bootstrap | 100 | `local:snippets/infra-bootstrap.yaml` | `local:snippets/network-config-infra-bootstrap.yaml` | `local:snippets/proxmox-hooks.yaml` |
| forgejo | 101 | `local:snippets/forgejo.yaml` | `local:snippets/network-config-forgejo.yaml` | — |
| inventory | 102 | `local:snippets/inventory.yaml` | `local:snippets/network-config-inventory.yaml` | — |
| assessment-engine | 103 | `local:snippets/assessment-engine.yaml` | `local:snippets/network-config-assessment-engine.yaml` | — |

---

## Troubleshooting

**Cloud-Init did not run on first boot**
- Check: `sudo cat /var/log/cloud-init.log` on the VM
- Check: `qm config <vmid> | grep cicustom` — must show snippet paths

**Wrong IP assigned**
- Cloud-Init network-config may not have applied. Check: `ip addr`
- Verify the network-config file was uploaded and referenced in `cicustom`

**SSH connection refused**
- qemu-guest-agent may not have reported first-boot completion yet — wait 60s
- Check: `qm guest cmd <vmid> ping` from the Proxmox host

**Cloud-Init re-runs on every boot**
- This is expected unless `proxmox-hooks.yaml` vendor-data is applied
- Only infra-bootstrap uses vendor-data by default; other VMs rely on the
  `cloud-init.disabled` file being created by their own `runcmd`
- Add `- touch /etc/cloud/cloud-init.disabled` to any VM's `runcmd` to disable re-runs
