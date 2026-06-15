# Node Spawning — Operator Runbook

**Phase 12.E — Hatchery Process**
Document date: 2026-06-01 | Review by: 2027-06-01

A broodling is a new Proxmox node that joins the hatchery's cluster via the
**hatchery process**. This runbook covers end-to-end spawning: from bare
hardware → cluster member with declared services running.

Fill in the **Parameters** panel — every command on this page updates live, and each
**Copy** button copies the resolved command including your actual paths and values.
> **Mise en place** — Confirm the broodling has Proxmox VE installed and is
> reachable from the hatchery before starting the planner. Know its intended
> hostname, IP address, and role (worker vs server). The KeePass master password
> for the hatchery must be on-hand — spawn.sh will prompt for it once on the
> broodling after the package is copied over.

---

## Before you begin — record broodling identity

@field[Hatchery hostname (where you run spawn-planner.py)|HATCHERY=pve01]
@field[Broodling hostname (new node being added)|BROODLING=pve02]
@field[Broodling LAN IP|BROODLING_IP=192.168.1.15]
@field[Cell identifier|CELL_ID=cell-1]

---

## Working directory

@dir[Broodforge repo / hatchery working directory]

```bash
cd {{broodforge-repo-root-path}}
```

---

## Overview

```
Hatchery (pve01)                    Broodling (pve02 — fresh Proxmox install)
  │                                    │
  │  1. Run spawn-planner.py           │
  │  2. Discover hardware ─────────────► SSH to broodling
  │  3. Select disposition             │
  │  4. Generate spawn package         │
  │  5. Copy package ─────────────────►│
  │                                    │  6. bash spawn.sh
  │                                    │     KeePass gate
  │                                    │     phase-00 preflight + host config
  │                                    │     phase-01 Proxmox join
  │                                    │     phase-02 VMs
  │                                    │     phase-03 Cloud-Init + VM start
  │                                    │     phase-04 k3s join
  │                                    │     [phase-05 HA promotion]
  │                                    │     phase-06 verify
  │  7. update-state-after-spawn.py ◄──┤
  │  8. Assessment Engine reassesses   │
```

---

## Prerequisites

### Hatchery side

- `bootstrap-state.json` is current (run `collect-tier2.py` if needed)
- Forgejo is running and accessible (phase scripts are committed there)
- KeePass database is accessible (on USB, local disk, or embedded in package)
- Python 3.8+ available: `python3 --version`
- Required modules in `proxmox-bootstrap/`:
  `hatchery_state.py`, `validate_spawn.py`, `spawn_hardware_discovery.py`,
  `spawn_iac_generator.py`, `spawn_scripts.py`, `assemble_spawn_package.py`

### Broodling side

- Bare Proxmox VE installed (community edition; subscription nag suppressed automatically)
- Root SSH access (temporary password set during installation)
- Network connectivity — either:
  - **LAN mode**: broodling reachable from hatchery via `ping {broodling-ip}`
  - **WAN mode**: Tailscale will be installed by `phase-00a` using the embedded auth key
- No existing ZFS pools, VMs, or custom bridges (factory state)
- Sufficient hardware for the planned disposition (see capacity guidance below)

---

## WAN mode prerequisites

WAN mode routes the broodling through the hatchery's Headscale tailnet instead
of a direct LAN connection. Before running `spawn-planner.py` in WAN mode, all
of the following must be in place on the **hatchery**:

1. **Headscale server running** — verify with `headscale version` and
   `systemctl is-active headscale`. The server must be reachable from the
   broodling (typically via a public IP or a reverse proxy).

2. **Pre-auth key obtained** — generate a single-use, expiring key:
   ```bash
   headscale preauthkeys create --expiration 1h --user broodforge
   ```
   Copy the key output. It is valid for one registration only. The spawn
   planner embeds this key in the spawn package; `phase-00a` uses it to register
   the broodling before any deployment steps run.

3. **`wan_auth_key` in the spawn plan** — pass the auth key when running the
   planner interactively (it prompts for it in WAN mode), or supply it via
   `--wan-auth-key` on the command line:
   ```bash
   python3 spawn-planner.py \
       --state bootstrap-state.json \
       --hardware hardware-profile-pve02.json \
       --wan-auth-key tskey-auth-xxxxxxxxxxxxx
   ```
   `build_spawn_plan()` raises `ValueError` if `wan_auth_key` is absent when
   `network_mode` is `"wan"` — this is the guard that enforces this requirement.

4. **Tailscale installed on the spawning machine** — the hatchery must have
   Tailscale installed and joined to the same tailnet so it can reach the
   broodling's tailnet IP (`100.64.x.x`) after `phase-00a` completes:
   ```bash
   apt install tailscale
   tailscale up --login-server https://<headscale-host> --authkey <key>
   tailscale status  # broodling should appear after phase-00a
   ```

5. **`wan_endpoint` reachable** — confirm the broodling can reach the Headscale
   control plane before running the spawn package. The `wan_endpoint` field in
   the spawn plan is derived from the hatchery's FQDN/IP; ensure DNS resolves
   or use a direct IP.

**Summary checklist:**
```
[ ] headscale is running on the hatchery
[ ] headscale preauthkeys create --expiration 1h --user broodforge  → key noted
[ ] tailscale is installed and joined on the hatchery
[ ] wan_auth_key supplied to spawn-planner.py (--wan-auth-key flag)
[ ] broodling has network path to Headscale control plane
```

---

## Step 1 — Discover Hardware

Run from the hatchery. Produces `hardware-profile-{hostname}.json`.

```bash
cd {{broodforge-repo-root-path}}

# LAN mode (password-based SSH)
python3 proxmox-bootstrap/spawn_hardware_discovery.py \
    --host {{BROODLING_IP}} \
    --user root \
    --password-prompt \
    --output hardware-profile-{{BROODLING}}.json

# WAN mode (Headscale tailnet — after the broodling has joined via phase-00a)
python3 proxmox-bootstrap/spawn_hardware_discovery.py \
    --host 100.64.0.5 \   # tailnet IP
    --user root \
    --password-prompt \
    --output hardware-profile-{{BROODLING}}.json
```

> **Note:** `--password-prompt` (and `--password`) use `sshpass` for non-interactive
> password SSH to a fresh broodling — install it on the hatchery/workstation
> (`apt install sshpass`). Once the broodling has an SSH key (after spawn), use
> `--key` instead. The password is passed via the `SSHPASS` env var, never on the
> command line, so it does not appear in `ps`/process listings.

**Discovery output** — `hardware-profile-pve02.json`:
```json
{
  "hostname": "pve02",
  "cpu_model": "AMD Ryzen 5600",
  "cpu_cores": 6,
  "ram_gb": 32,
  "disks": [
    {"name": "/dev/sda", "size_gb": 500, "rotational": false},
    {"name": "/dev/sdb", "size_gb": 500, "rotational": false}
  ],
  "nics": [
    {"name": "eno1", "mac": "AA:BB:CC:DD:EE:FF", "speed_mbps": 1000}
  ],
  "derived": {
    "usable_disks": 2,
    "ssd_count": 2,
    "hdd_count": 0,
    "zfs_topology": "mirror"
  }
}
```

**ZFS topology auto-selected from usable disk count:**
| Disks | Topology |
|-------|----------|
| 1     | stripe (no redundancy — WARNING shown) |
| 2     | mirror |
| 3     | raidz1 |
| 4–6   | raidz2 |
| 7+    | raidz3 |

Record discovery results:

@radio[ZFS topology auto-selected|stripe (1 disk — no redundancy)|mirror (2 disks)|raidz1 (3 disks)|raidz2 (4–6 disks)]
@field[Hardware profile filename written|hardware-profile-{{BROODLING}}.json]
@field[Available RAM on broodling (from discovery output)]
@area[Any hardware warnings printed by the discovery tool]

---

## Step 2 — Run Spawn Planner

```bash
cd {{broodforge-repo-root-path}}
python3 proxmox-bootstrap/spawn-planner.py \
    --state proxmox-bootstrap/bootstrap-state.json \
    --hardware hardware-profile-{{BROODLING}}.json
```

The planner walks through three steps interactively:

### Step 0 — Network Mode

```
Is the broodling on the same LAN as the hatchery?
[auto-detecting — trying 192.168.1.15... timeout 5s]

  1. Same LAN  — direct SSH using temporary root password
  2. WAN       — Headscale tailnet (generates auth key)
  3. Specify   — enter broodling IP/hostname manually

> _
```

- **LAN**: generates a suggested temporary root password (`Ready.to.spawn.7` format).
  Use this password when installing Proxmox on the broodling.
  The planner holds it in memory for hardware discovery — not stored in KeePass.
  Record it here for the duration of Proxmox installation:

@credential[Temporary broodling root password — discard after Proxmox install]

- **WAN**: calls `headscale authkeys generate --expiration 1h --user broodforge`.
  The auth key is embedded in the spawn package. `phase-00a` installs Tailscale
  and registers the broodling before any deployment begins.

### Step 1 — Execution Mode

```
How should the spawn package run on the broodling?

  1. Autonomous (default)  — finalise service selection now; spawn.sh runs
                             without prompting after KeePass unlock
  2. Interactive            — service menu evaluated on the broodling at runtime

> _
```

- **Autonomous** (recommended): you select services now; locked into package.
  Only the KeePass master password is required before fully automated execution.
- **Interactive**: no service selection needed now. `spawn.sh` presents the
  service menu on the broodling, evaluated against actual hardware at runtime.

### Step 2 — Service Selection (Autonomous Only)

```
Select services to deploy:

  Mode 1: Full mirror      — all services that fit this hardware
  Mode 2: Select by group  — Infrastructure / Platform / Intelligence / Monitoring / Apps
  Mode 3: Select individually

> _
```

**Hardware fit display:**
```
  [✓] k3s-worker          fits  (RAM: 4 GB required; 26 GB available)
  [✓] longhorn             fits  (RAM: 2 GB, disk: 50 GB)
  [!] prometheus           marginal (RAM: 6 GB; reduced to 4 GB)
  [✗] pbs-datastore        no fit (requires 16 GB RAM, only 8 GB available)
```

Services marked `[✗]` are excluded automatically. The planner records them
in `disposition.excluded` with the reason.

**Intelligence baseline is always included** (cannot be deselected):
Proxmox cluster membership, k3s worker node, assessment visibility.

### Planner Output — `spawn-plan-pve02.json`

```json
{
  "cell_id": "cell-alpha",
  "hostname": "pve02",
  "domain": "home.example.com",
  "lan_ip": "192.168.1.15",
  "package_id": "spawn-cell-alpha-pve02-2026-06-01_12_00_00",
  "generated_at": "2026-06-01T12:00:00Z",
  "disposition": {
    "execution_mode": "autonomous",
    "network_mode": "lan",
    "services": ["k3s-worker", "longhorn"],
    "excluded": [
      {"service": "pbs-datastore", "reason": "requires 16 GB RAM; host has 8 GB"}
    ]
  },
  "storage": {
    "pool_name": "rpool",
    "topology": "mirror",
    "disk_ids": ["/dev/sda", "/dev/sdb"],
    "datastore_name": "local-rpool"
  },
  "network": {
    "bridge": "vmbr0",
    "gateway": "192.168.1.1",
    "nameservers": ["192.168.1.1"]
  },
  "vms": [
    {"vmid": 200, "name": "k3s-worker-01", "ip": "192.168.1.50", "memory_mb": 4096},
    {"vmid": 201, "name": "longhorn-01",   "ip": "192.168.1.51", "memory_mb": 2048}
  ],
  "k3s": {
    "role": "worker",
    "server_url": "https://k3s-server-01.home.example.com:6443",
    "node_labels": ["worker=true"]
  }
}
```

**Review the plan** — pay attention to:
- `disposition.excluded` — services the planner dropped. If a service you want
  is excluded, the reason tells you exactly what hardware is needed.
- `vms[].vmid` — confirm no conflicts with your existing VMID allocation.
- `storage.disk_ids` — confirm these are the correct physical disks.
- `k3s.role` — worker (default) or server (HA promotion if 3rd server node).

Record the planner decisions:

@radio[Network mode selected|LAN — direct SSH|WAN — Headscale tailnet]
@radio[Execution mode selected|Autonomous (services locked in now)|Interactive (service menu at runtime)]
@radio[k3s role assigned|worker|server (HA promotion — 3rd server node)]
@field[Services included in disposition (from spawn-plan.json)]
@area[Services excluded and reasons (from disposition.excluded)]
@field[VMID block allocated (from spawn-plan.json vms[])]
@field[IP addresses allocated]

---

## Step 3 — Generate Spawn Package

To embed the KeePass database in the package for offline recovery, record the path here first:

@filename[KeePass database path (optional — leave blank to skip embedding)]

```bash
cd {{broodforge-repo-root-path}}
python3 proxmox-bootstrap/assemble-spawn-package.py \
    --plan spawn-plan-{{BROODLING}}.json \
    --state proxmox-bootstrap/bootstrap-state.json \
    --kdbx {{KDBX=}}
```

Omit `--kdbx {{KDBX=}}` if you left the KeePass path blank above.

The assembler prints the package path and its SHA-256. **Paste the full assembler
output into the field below** — the filename and hash will be extracted automatically.

@parse[Paste assembler output here — extracts spawn package filename|Package written:\s*(\S+\.tar\.gz)|spawn-package-filename]
@parse[Paste assembler output here — extracts SHA-256|SHA-256:\s*([0-9a-f]{64})|spawn-package-sha256]

Then record (or override) the extracted values:

@filename[Spawn package filename|spawn-package-{{CELL_ID}}-{{BROODLING}}-{{STAMP}}]
@field[Package SHA-256]

**Package contents:**
```
spawn-package-cell-alpha-pve02-2026-06-01_12_00_00.tar.gz
├── spawn-manifest.json        hatchery reservation snapshot
├── spawn-plan.json            broodling-specific plan
├── spawn.sh                   orchestrated entry point
├── [tailscale-join.sh]        WAN mode only: Headscale/Tailscale join (phase-00a)
├── phase-00-preflight.sh      hardware pre-flight verification
├── phase-00-host.sh           hostname + bridges + ZFS + datastore
├── phase-01-proxmox.sh        pvecm join
├── phase-02-vms.sh            tofu apply
├── phase-03-cloudinit.sh      cloud-init install + VM start
├── phase-04-k3s.sh            ansible k3s role
├── [phase-05-ha.sh]           HA promotion (3rd server only)
├── phase-06-verify.sh         post-spawn health check
├── spawn-workbook-pve02.html  HTML tracking workbook
├── opentofu/                  Proxmox VM tfvars
├── cloud-init/snippets/       user-data + network-config per VM
├── ansible/                   inventory + k3s role vars
├── lib/checkpoint.sh          resumable execution library
├── lib/keepass-gate.sh        KeePass master password gate
└── [kdbx/vault.kdbx]          optional embedded KeePass database
```

**Security note:** The package **never contains secret values**. It contains
only KeePass path references (e.g. `Infrastructure/k3s/worker-join-token`).
The KeePass database can be embedded (optional) but still requires the master
password at the gate — it cannot auto-unlock.

---

## Step 4 — Copy Package to Broodling

```bash
scp {{note:spawn-package-filename}} root@{{BROODLING_IP}}:/root/

# Verify on the broodling
ssh root@{{BROODLING_IP}} "sha256sum /root/{{note:spawn-package-filename}}"
```

Compare the SHA-256 above against the value recorded in Step 3.

@radio[Integrity check result|✓ Hashes match — proceed|✗ Hashes differ — do not proceed, re-copy package]

If the KeePass database is **not** embedded in the package, copy it separately:
```bash
scp {{KDBX=}} root@{{BROODLING_IP}}:/root/vault.kdbx
```

---

## Step 5 — Execute Spawn Package

SSH to the broodling and extract + run:

```bash
ssh root@{{BROODLING_IP}}

cd /root
tar -xzf {{note:spawn-package-filename}}
cd $(basename {{note:spawn-package-filename}} .tar.gz)/
bash spawn.sh
```

### KeePass Unlock Gate (runs first)

```
=================================================================
 KeePass Unlock Gate
 The master password is required once before any secrets are
 accessed. All subsequent lookups are automatic.
=================================================================
[kdbx] Using embedded database: ./kdbx/vault.kdbx
[kdbx] Master password: _
[kdbx] Database unlocked. Secrets broker active.
```

In **autonomous mode**, this is the **only prompt** before fully automated execution.
In **interactive mode**, the service selection menu follows after unlock.

### Phase Execution

Phases run sequentially. Each phase prints timestamped checkpoint progress:

```
[12:01:15] START: hostname
[12:01:16] DONE:  hostname
[12:01:16] START: bridge
[12:01:18] DONE:  bridge
[12:01:18] START: zpool
[12:01:45] DONE:  zpool
...
```

**Resuming after failure:** If a phase fails, fix the issue and re-run
`bash spawn.sh`. Completed checkpoints are skipped automatically — the
package is fully idempotent.

**Pre-flight gate (phase-00-preflight):** Runs read-only checks before any
changes are made:
- Disk IDs from spawn plan exist and have expected capacity
- NIC names/MACs match embedded hardware profile
- Available RAM ≥ sum of VM RAM + 10% overhead
- No existing ZFS pool name conflict
- No existing bridge name conflict
- No VMID/IP/hostname conflicts against live hatchery snapshot

If **any pre-flight check fails**, phase-00-preflight exits immediately with a
clear error. No changes are made to the broodling. Report the mismatch to the
hatchery operator to regenerate the spawn package.

### Expected Phase Duration

| Phase | Expected Time | Notes |
|-------|--------------|-------|
| phase-00-preflight | < 30s | Read-only checks |
| phase-00-host | 2–5 min | ZFS pool creation depends on disk count |
| phase-01-proxmox | 1–2 min | pvecm join requires cluster quorum |
| phase-02-vms | 3–10 min | Depends on number of VMs |
| phase-03-cloudinit | 5–15 min | Cloud-Init runs inside each VM |
| phase-04-k3s | 3–8 min | Ansible k3s role |
| phase-05-ha (if present) | 5–10 min | etcd migration quiesces cluster briefly |
| phase-06-verify | < 2 min | Health checks |

### Per-phase outcome tracking

Record actual completion time and any deviations for each phase:

@table[Per-phase actual times and notes|Phase|Actual completion time|Deviations / observations](phase-00-preflight,phase-00-host,phase-01-proxmox,phase-02-vms,phase-03-cloudinit,phase-04-k3s,phase-05-ha (if present),phase-06-verify)

@radio[Overall spawn execution result|✓ All phases completed on first run|↺ Some phases required retry — see table|✗ Spawn halted — unresolved failure]
@field[Total spawn execution time (wall clock)]

### phase-06-verify Output (Success)

```
[spawn] All nodes Ready:
  pve01/k3s-server-01     Ready   v1.29.0
  pve02/k3s-worker-01     Ready   v1.29.0

[spawn] All VMs running:
  VMID 200  k3s-worker-01    running
  VMID 201  longhorn-01      running

[spawn] Spawn complete — pve02 is a cluster member.
Flux CD will schedule workloads automatically.
Assessment Engine will reassess on next collection cycle.
```

---

## Step 6 — Update Hatchery State

**Automatic path (recommended):** `phase-06-verify.sh` (the last phase in `spawn.sh`)
automatically POSTs to the hatchery's `/api/spawn-complete` endpoint. If the hatchery
is running `hatchery_receiver.py`, it processes the event and updates
`bootstrap-state.json` without any manual intervention.

**Manual fallback** (when the hatchery receiver is not reachable):

```bash
cd {{broodforge-repo-root-path}}
python3 proxmox-bootstrap/update_state_after_spawn.py \
    --state proxmox-bootstrap/bootstrap-state.json \
    --plan spawn-plan-{{BROODLING}}.json \
    --hardware hardware-profile-{{BROODLING}}.json \
    --spawned-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

This merges the new broodling VMs, DNS entries, provenance records, and spawn event
into `bootstrap-state.json`. Then commit:

```bash
git -C {{broodforge-repo-root-path}} add proxmox-bootstrap/bootstrap-state.json
git -C {{broodforge-repo-root-path}} commit -m "spawn: {{BROODLING}} joined"
git -C {{broodforge-repo-root-path}} push
```

@radio[State update method used|Automatic — hatchery receiver handled it|Manual — ran update_state_after_spawn.py|Manual — committed state update via bf-commit]

---

## Step 7 — Verify Cluster Health

```bash
# On the hatchery or any cluster member:
kubectl get nodes -o wide

# Expected:
NAME           STATUS   ROLES    AGE
{{HATCHERY}}          Ready    master   30d
{{BROODLING}}          Ready    worker   2m

# Proxmox Datacenter:
pvecm nodes
# Should show both {{HATCHERY}} and {{BROODLING}}

# Assessment Engine:
python3 doc-gen/engine.py --mode bootstrap \
    --manifest proxmox-bootstrap/bootstrap-state.json
# Readiness score should be GREEN or improve
```

@radio[Broodling shows Ready in kubectl get nodes|✓ Yes — joined successfully|✗ No — check spawn phase-04 and k3s logs]
@field[Broodling node name and STATUS from kubectl output]
@radio[pvecm nodes shows both hosts|✓ Yes — Proxmox cluster intact|✗ No — check pvecm join logs from phase-01]
@radio[Assessment Engine result after spawn|GREEN — improved or maintained|ORANGE — minor new findings|RED — new blocking findings]
@area[Anything that didn't go as expected — unexpected prompts, failures, manual steps]

Use **Export**, top-right, to save this record and any attached logs as a timestamped package.

---

## Troubleshooting

### Pre-flight fails: "disk /dev/sda not found"
The disk name changed after Proxmox installation (kernel update or hardware change).
Re-run hardware discovery on the hatchery and regenerate the spawn package.

### Pre-flight fails: "stale manifest — VMID 200 now in use"
Another spawn happened between package generation and execution. Re-run the
spawn planner on the hatchery to allocate a fresh VMID block.

### pvecm join fails: "totem RAFT protocol error"
Time synchronisation issue. Verify `chronyc tracking` shows < 1s offset on
both nodes. Proxmox cluster requires accurate time.

### k3s join fails: "token mismatch"
The k3s join token in KeePass may have been rotated. Retrieve the current token:
```bash
# On hatchery k3s server:
cat /var/lib/rancher/k3s/server/node-token
```
Update the KeePass entry and re-run phase-04-k3s.sh.

### Resuming a failed spawn
Fix the issue, then re-run:
```bash
bash spawn.sh
```
Completed checkpoints are skipped. Only failed/incomplete phases re-run.

### Resetting all checkpoints (fresh start)
```bash
source lib/checkpoint.sh
checkpoint_reset
bash spawn.sh
```

---

## Spawn History

After each successful spawn, `bootstrap-state.json` records:
```json
{
  "spawn_history": [
    {
      "broodling_hostname": "pve02",
      "broodling_fqdn": "pve02.home.example.com",
      "spawn_package_id": "spawn-cell-alpha-pve02-2026-06-01_12_00_00",
      "execution_mode": "autonomous",
      "disposition_services": ["k3s-worker", "longhorn"],
      "disposition_excluded": [{"service": "pbs-datastore", "reason": "..."}],
      "k3s_role": "worker",
      "spawned_at": "2026-06-01T13:45:00+00:00",
      "vmids_allocated": [200, 201],
      "ips_allocated": ["192.168.1.15", "192.168.1.50", "192.168.1.51"],
      "broodling_lan_ip": "192.168.1.15",
      "broodling_tailnet_ip": "100.64.0.5",
      "hardware_profile": {"cpu_cores": 8, "ram_gb": 32, "disk_count": 2}
    }
  ]
}
```

The Assessment Engine reads `spawn_history` to build disposition compliance
scoring: a node with `k3s-worker` in `disposition_services` that is not running
a k3s worker → RED finding. A node without `pbs-datastore` is not scored
against backup target requirements.

---

## Hardware Capacity Guidelines

| Disposition | Minimum RAM | Minimum Disks | k3s Role |
|-------------|-------------|---------------|----------|
| Baseline    | 8 GB        | 2             | worker   |
| Compute     | 16 GB       | 2             | worker   |
| Storage     | 16 GB       | 3+            | worker   |
| Control plane | 32 GB     | 2             | server   |
| Full peer   | 64 GB       | 4+            | server   |

The planner enforces a 90% RAM headroom limit:
`sum(VM RAM) ≤ host RAM × 0.90`

---

## Key Files

| File | Description |
|------|-------------|
| `spawn-planner.py` | Interactive planner — generates spawn-plan.json |
| `spawn_hardware_discovery.py` | SSH hardware discovery library |
| `spawn_iac_generator.py` | Generates OpenTofu tfvars + Cloud-Init + Ansible |
| `spawn_scripts.py` | Generates phase-00 through phase-06 bash scripts |
| `assemble_spawn_package.py` | Bundles everything into a tar.gz |
| `html_spawn_workbook.py` | Generates HTML tracking workbook |
| `validate_spawn.py` | Conflict validator (VMID/IP/hostname/capacity) |
| `hatchery_state.py` | Reads hatchery state → spawn manifest |
| `update_state_after_spawn.py` | Merges broodling back into bootstrap-state.json |
