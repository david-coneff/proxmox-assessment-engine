# FORGING.md — Operator Runbook

**Phase 1.F** | Last updated: 2026-06-01

Forging is the process of taking bare Proxmox hardware to a fully operational
broodforge hatchery using the forge package. This runbook covers the complete
forge workflow end-to-end.

Fill in the **Parameters** panel — every command on this page updates live, and each
**Copy** button copies the resolved command including your actual paths and values.

---

## Before you begin — record hatchery identity

Start here. These values are used throughout the runbook and auto-populate commands below.

@field[Cell identifier or codename (e.g. cell-1 or flying-bat)|CELL_ID=cell-1]
@field[Hatchery hostname (e.g. pve01)|HOSTNAME=pve01]
@field[Domain (e.g. home.example.com)|DOMAIN=home.example.com]
@field[Hatchery LAN IP|HATCHERY_IP=192.168.1.10]

---

## Working directory

All commands assume you are in the broodforge repo root. Set this once:

@dir[Broodforge repo root path]

```bash
cd {{broodforge-repo-root-path}}
```

---

## Prerequisites

### Hardware requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 16 GiB | 32 GiB |
| Disks (ZFS) | 2 × ≥32 GiB | 2-4 × ≥200 GiB SSD |
| NICs | 1 | 2 (management + VM traffic) |
| CPU cores | 2 | 4+ |

### Software requirements

- Proxmox VE installed on the target host (bare metal or nested virtualisation)
- Proxmox CE (community edition, no subscription) is fully supported
- Network access from your workstation to the target host (SSH on port 22)
- Python 3.11+ on your workstation (for generating the forge package)

### Network requirements

- Static IP assigned to the hatchery host (or DHCP reservation)
- Default gateway configured
- Internet access from the hatchery host (for apt, Let's Encrypt, Flux CD)

---

## Step 0 — Build pre-install media (optional)

**This step is optional.** The supported baseline remains: install Proxmox VE
on the target host yourself (official installer, an existing cluster,
hosting-provider-imaged hardware — whatever works for you), then start at
Step 1 below. Skip this section entirely if you already have Proxmox VE
installed.

For operators who want to collapse "install Proxmox" + "copy the forge
package over" + "SSH in and run forge.sh" into a single boot-and-walk-away
operation, the Image Builder (Phase 1.H, AD-057) generates a **bootstrap
image staging bundle** — a structured archive that documents and stages
everything you need to combine with the official Proxmox VE ISO to produce
bootable pre-install media.

> **Note:** Step 0 requires `forge-manifest.json`, which is generated in
> **Step 1** below. The recommended workflow is: complete Step 1 first
> (run `forge-planner.py`, review the manifest), then return here to build
> the pre-install media before proceeding to Step 2.

```bash
# Step 1 first — generates forge-manifest.json:
python3 proxmox-bootstrap/forge-planner.py
# Then build the pre-install media (Step 0):
python3 proxmox-bootstrap/generate-bootstrap-image.py --manifest forge-manifest.json \
    --interface enp3s0 --disk /dev/sda
```

This produces `bootstrap-image-{cell_id}-{timestamp}.tar.gz`, containing an
`iso-staging/` layout with:

- `answer.toml` — a Proxmox VE 8+ automated-installer answer file, **derived
  from `forge-manifest.json`** (hostname, domain, network, timezone) so you
  answer setup questions exactly once, not twice
- `forge-package.tar.gz` — the same forge package Step 2 below produces,
  embedded so the new host can forge itself without a second copy step
- `first-boot/` — a systemd oneshot unit + installer script that runs the
  embedded forge package's `forge.sh` automatically on the new host's first
  boot, replacing the manual "SSH in and run forge.sh" step (Step 4)
- `bootstrap-image-manifest.{json,html}` — a hash/contents manifest for the
  bundle (same SHA-256 verification pattern as the forge package, plus its
  AD-051 HTML twin)
- `README.md` — exact instructions for combining this bundle with the
  official Proxmox VE ISO

**Be clear about what this is.** broodforge cannot download, mount, or
remaster the official Proxmox VE ISO in an offline/stdlib-only environment
— and does not redistribute Proxmox's installer media. The generated bundle
is **staging content**, not a literal bootable ISO: you still combine it with
the official ISO yourself, using Proxmox's own documented tooling (e.g.
`proxmox-auto-install-assistant prepare-iso`). The bundle's `README.md`
documents those steps precisely — read it before proceeding.

**Security note — the `answer.toml` root password.** The installer's answer
file requires *some* root credential, and KeePass does not exist on the host
yet at install time, so there is no reference-only option here. The Image
Builder generates a **fresh, single-use discovery passphrase** (the exact
pattern Cloud-Init already uses for spawned nodes — AD-039/AD-043), prints it
once at build time, and embeds it in `answer.toml`. It is *not* a permanent
credential and is never written to KeePass: the embedded forge package's
phase-03 replaces it with a KeePass-managed credential during the automated
forge run. **Note the passphrase down when the builder prints it — you cannot
recover it from the bundle afterward — and rotate or discard it once forging
completes.**

If this step doesn't fit your situation (different hardware, different
install method, you just prefer doing it by hand), skip it — Step 1 below is
where every forge starts either way.

---

## Step 1 — Generate the forge manifest

On your **workstation**, generate the forge manifest using the interactive planner:

```bash
cd {{broodforge-repo-root-path}}
python3 proxmox-bootstrap/forge-planner.py
```

The planner will ask you to:
1. Choose a setup mode (autonomous recommended for first forge)
2. Set the hatchery hostname and domain
3. Choose a network profile (LAN only or WAN-capable with Headscale)
4. Confirm your timezone
5. Configure at least one backup destination

The planner writes `forge-manifest.json` in the current directory.

**Review the manifest:**
```bash
cat forge-manifest.json
```

Record the key values the planner confirmed:

@radio[Network profile selected|LAN only (no Headscale)|WAN-capable (Headscale + DDNS)|LAN with future WAN upgrade planned]
@field[Timezone configured]
@field[Backup destination(s) configured]

---

## Step 2 — Assemble the forge package

On your **workstation**, generate the self-contained forge package:

To embed the KeePass database in the package for offline use, record the path here first:

@filename[KeePass database path (optional — leave blank to skip embedding)]

```bash
cd {{broodforge-repo-root-path}}
python3 proxmox-bootstrap/assemble-forge-package.py \
    --manifest forge-manifest.json \
    --kdbx {{KDBX=}}
```

Omit `--kdbx {{KDBX=}}` if you left the KeePass path blank above.

This produces a package in the current directory:
```
forge-package-{cell_id}-{timestamp}.tar.gz
```

**Security note:** The forge package never contains secret values — only KeePass paths
(references). If you embed the KeePass database, it requires the master password to
unlock. Without the database, the KeePass gate will prompt for the path at runtime.

The assembler prints the package path and its SHA-256. **Paste the full assembler
output into the field below** — the filename and hash will be extracted automatically.

@parse[Paste assembler output here — extracts package filename|Package written:\s*(\S+\.tar\.gz)|forge-package-filename]
@parse[Paste assembler output here — extracts SHA-256|SHA-256:\s*([0-9a-f]{64})|forge-package-sha256]

Then record (or override) the extracted values:

@filename[Forge package filename|forge-package-{{CELL_ID}}-{{STAMP}}]
@field[Package SHA-256]

---

## Step 3 — Copy the forge package to the target host

```bash
cd {{broodforge-repo-root-path}}
scp {{note:forge-package-filename}} root@{{HATCHERY_IP}}:/root/
```

**Verify integrity after transfer.** Compare the SHA-256 on the target host against
the value recorded in Step 2:

```bash
# On the target host:
sha256sum /root/{{note:forge-package-filename}}
```

@radio[Integrity check result|✓ Hashes match — proceed|✗ Hashes differ — do not proceed, re-copy package]

---

## Step 4 — Execute the forge package

On the **target host** (SSH in or use the Proxmox console):

```bash
cd /root
tar xzf {{note:forge-package-filename}}
bash forge.sh
```

### What forge.sh does

The forge orchestrator runs 9 phases in order. Completed phases are checkpointed —
if forge.sh fails or is interrupted, re-run it to resume from where it left off:

| Phase | Script | Action |
|---|---|---|
| 00 | `phase-00-discover.sh` | Hardware discovery (disks, NICs, RAM, CPU) |
| 01 | `phase-01-plan.sh` | Identity planning (hostname, domain, cell_id) |
| 02 | `phase-02-validate.sh` | Hardware validation — RED findings block forge |
| 03 | `phase-03-host.sh` | Host config: hostname, ZFS pool, dnsmasq, KeePass init |
| 04 | `phase-04-vms.sh` | VM provisioning (OpenTofu — minimum viable stack) |
| 05 | `phase-05-k3s.sh` | k3s cluster init (Ansible k3s-server role) |
| 06 | `phase-06-gitops.sh` | Flux CD bootstrap → Forgejo |
| 07 | `phase-07-intelligence.sh` | Assessment + documentation engine init |
| 08 | `phase-08-verify.sh` | Cluster health check + state commit |

### Per-phase outcome tracking

Record the result of each phase as it completes:

@table[Per-phase completion status|Phase|Started at|Completed at|Result / notes](Phase 00 — Discover,Phase 01 — Plan,Phase 02 — Validate,Phase 03 — Host config,Phase 04 — VMs,Phase 05 — k3s,Phase 06 — Flux CD,Phase 07 — Intelligence,Phase 08 — Verify)

@radio[Overall forge execution result|✓ All phases completed on first run|↺ Some phases required --from resume — see table|✗ Forge halted — unresolved failure]
@field[Total forge execution time (wall clock)]
@field[KeePass master password hint / entry path (do not record the password itself)]

### Resuming after failure

```bash
# Resume from a specific phase (e.g. phase 3 if phase-03 failed)
bash forge.sh --from 3

# Start completely fresh
bash forge.sh --reset
```

---

## Step 5 — Forge phase details

### Phase 00 — Discover

Scans the hardware using `lsblk`, `ip link`, and `/proc/meminfo`. Writes
`hardware-profile.json`. No changes are made to the system.

### Phase 01 — Plan

Re-reads `forge-manifest.json`. If the manifest was generated on a different machine,
this step adapts the plan to the actual discovered hardware.

### Phase 02 — Validate

Runs `forge_validator.py` against `hardware-profile.json`. RED findings block the
forge. Review the output and resolve issues before re-running.

Common RED findings:
- **RAM too low**: add RAM or use a machine with ≥16 GiB
- **Insufficient disks**: add a second disk for ZFS mirror
- **No NICs**: check that the NIC is detected by the kernel

### Phase 03 — Host configuration

This is the longest phase. It:
1. Sets the hostname and /etc/hosts
2. Suppresses the Proxmox CE subscription nag
3. Creates the ZFS pool (topology derived from disk count)
4. Installs and configures dnsmasq (split-horizon DNS)
5. Initialises the KeePass database (master password prompt)
6. If WAN profile: installs Headscale, issues TLS cert, configures DDNS

**KeePass gate:** Phase 03 prompts for the KeePass master password once.
All subsequent secret lookups during forging use this unlocked session —
you will not be prompted again.

**Master password selection:**
- forge.sh suggests a readable passphrase (e.g. `Forest.amber.glide.8`)
- Accept the suggestion, enter your own, or use KeePass's built-in generator
- This is the single most important secret — choose carefully and record it safely

### Phase 03 — WAN profile only

If you selected the WAN network profile:

- **Headscale** is installed and configured as the hatchery's own tailnet coordinator
- **TLS certificate** is issued via Let's Encrypt (Cloudflare or DuckDNS path)
- **DDNS** timer is configured to update the external A record every 5 minutes

**Before running phase 03 in WAN mode:**
1. Ensure your domain's A record or DDNS is set up (see `docs/CLOUDFLARE-SETUP.md` or `docs/DUCKDNS-SETUP.md`)
2. If using Cloudflare: have your API token ready (will be stored in KeePass)
3. If using DuckDNS: have your token ready
4. Configure port forwarding: 8080 → hatchery LAN IP (for Headscale)

### Phase 04 — VMs

Provisions the minimum viable stack VMs (Forgejo + operations) using OpenTofu,
from an `opentofu/` directory in the package. VM IDs, IPs, and roles are derived
from `forge-manifest.json`.

### Phase 05 — k3s

Runs the Ansible `k3s-server` playbook (`ansible/playbooks/04-k3s.yaml`) against
the provisioned VMs, using the generated inventory at `ansible/inventory/hosts.yaml`.
The k3s join token is retrieved from KeePass automatically.

### Forge provisioning status — what is automated today

> **Implementation status — read before forging on real hardware.** `forge.sh` runs
> end-to-end, but several phases are part of the active *deploy-to-hardware* milestone
> and currently self-skip or require manual completion rather than failing silently.

| Phase | Step | Status today |
|---|---|---|
| 00–02 | discover / plan / validate | ✅ Automated (read-only Python; no host changes) |
| 03 | hostname, ZFS pool, apt repos | ✅ Automated |
| 03 | KeePass DB init | ✅ Automated (`forge_keepass_init.py` has a CLI) |
| 03 | dnsmasq / Headscale / TLS | ✅ Config generated — `setup_dnsmasq.py` / `setup_headscale.py` / `setup_tls.py` now write the dnsmasq conf, Headscale `config.yaml` + unit, and TLS cert-sync script. The `apt`/`systemctl` install + Let's Encrypt issuance run on the host (Headscale/TLS via `--run`; see `docs/CLOUDFLARE-SETUP.md` / `docs/DUCKDNS-SETUP.md`) |
| 03 | DDNS | ✅ Automated (`setup_ddns.py` CLI) |
| 04 | VM provisioning (OpenTofu) | ⚠️ **Manual for now** — no `opentofu/` modules in the package yet; provision the Forgejo + operations VMs yourself |
| 05 | k3s (Ansible) | ⚠️ **Manual for now** — needs a generated `ansible/inventory/hosts.yaml` (roles/playbooks are bundled) |
| 06 | Flux CD bootstrap | ✅ Scripted |
| 07 | bootstrap-state init + first docs | ✅ Automated (seeds `bootstrap-state.json` from the forge manifest, non-interactively) |
| 08 | verify + commit | ✅ Scripted |

> **To forge a working hatchery today:** run `bash forge.sh` through phase-03 (host +
> KeePass), complete dnsmasq/Headscale/TLS and the Forgejo + operations VMs + k3s
> server manually (or supply your own `opentofu/` + `ansible/inventory/`), then resume
> with `bash forge.sh --from 6` for GitOps → intelligence → verify.
>
> The **spawn** flow, by contrast, generates its IaC fully (`spawn_iac_generator.py`)
> and provisions broodling VMs without these gaps.

### Phase 06 — Flux CD bootstrap

Bootstraps Flux CD against the Forgejo git server. Flux will continuously reconcile
the GitOps repository to deploy application workloads.

**After forging:** push your application manifests to the Forgejo repository. Flux CD
will deploy them automatically without further manual intervention.

### Phase 07 — Intelligence layer

Initialises `bootstrap-state.json` from the forge manifest and generates the first
set of broodforge documentation (Bootstrap Workbook, Recovery Runbook, Readiness Report).

### Phase 08 — Verify and commit

- Verifies all k3s nodes are Ready
- Checks Flux CD reconciliation status
- Commits `bootstrap-state.json` and `forge-manifest.json` to the Forgejo repository

---

## Step 6 — Verify the hatchery is operational

After forge.sh completes:

```bash
# Check k3s cluster health
kubectl get nodes
kubectl get pods -A

# Check Flux CD
flux get kustomizations

# Check assessment engine
python3 doc-gen/engine.py --mode bootstrap --manifest proxmox-bootstrap/bootstrap-state.json

# Access Forgejo web UI
open https://forgejo.{{DOMAIN}}
```

Expected output from `kubectl get nodes`:
```
NAME         STATUS   ROLES                  AGE   VERSION
{{HOSTNAME}}-k3s    Ready    control-plane,master   5m    v1.28.x
```

Record the outcome of this forge (use **Export**, top-right, to save these notes and
any attached logs as a timestamped package):

@field[Hatchery FQDN]
@field[k3s node name and STATUS from kubectl get nodes]
@field[Flux reconciliation status (from flux get kustomizations)]
@radio[Assessment engine result|GREEN — all findings resolved|ORANGE — minor findings remain|RED — blocking findings require action]
@area[Any phase that needed --from resume, manual steps, or deviations from this runbook]

---

## Troubleshooting

### Phase 02 fails with "hardware mismatch"

The hardware does not meet minimum requirements. Review `hardware-profile.json`
and the validator output. Common causes:
- Not enough disks: `lsblk` shows only 1 disk ≥32 GiB
- Too little RAM: `/proc/meminfo MemTotal` shows < 16 GiB
- No physical NICs: `ip link` shows only loopback and virtual interfaces

### Phase 03 fails with "ZFS pool create failed"

Common causes:
- Disk already has a ZFS pool from a previous attempt: `zpool import -a` then `zpool destroy rpool`
- Disk is in use by the OS (boot disk): ensure the ZFS member disks are not the Proxmox boot disk

### Phase 05 fails with "Ansible unreachable"

The k3s VMs are not yet accessible via SSH. Wait for Cloud-Init to complete (usually 1-3 minutes).
Check VM status in the Proxmox web UI. Re-run `bash forge.sh --from 5`.

### Phase 06 fails with "Flux bootstrap failed"

Common causes:
- Forgejo is not yet running: check VM health in phase 04
- Git repository not pre-created: forge.sh will attempt to create it automatically,
  but if Forgejo credentials aren't in KeePass yet, it may fail

### Headscale not accessible from WAN

1. Verify port forwarding: router → 8080 → hatchery LAN IP
2. Verify external DNS A record: `dig hatchery.{domain} @8.8.8.8`
3. Check Headscale service: `systemctl status headscale`
4. Check TLS cert: `openssl s_client -connect hatchery.{domain}:8080`

---

## Key files after forge

| File | Location | Purpose |
|---|---|---|
| `forge-manifest.json` | `/root/` | Cell identity snapshot |
| `hardware-profile.json` | `/root/` | Discovered hardware |
| `bootstrap-state.json` | `proxmox-bootstrap/` | Authoritative cell state |
| `dns-registry.yaml` | `proxmox-bootstrap/` | DNS records for all nodes |
| KeePass database | `/etc/broodforge/keepass.kdbx` | All service credentials |
| dnsmasq config | `/etc/dnsmasq.d/broodforge.conf` | Split-horizon DNS |
| Headscale config | `/etc/headscale/config.yaml` | Tailnet coordinator |
| TLS cert (WAN) | `/etc/broodforge/ssl/` | Let's Encrypt wildcard cert |

---

## Next steps after forging

1. **Push GitOps repository** to Forgejo — Flux CD will deploy application workloads
2. **Spawn broodlings** — run `python3 proxmox-bootstrap/spawn-planner.py` on the hatchery
   to generate spawn packages for additional nodes
3. **Run reconstruction drill** — validate the hatchery can be reconstructed from state
   (`docs/RECONSTRUCTION-DRILL.md`)
4. **Review the Bootstrap Workbook** — generated in `reports/` by the intelligence layer
5. **Set up monitoring** — deploy Prometheus agent via Flux GitOps

---

*Broodforge FORGING.md | Phase 1.F | Architecture v7.1*
