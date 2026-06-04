# PHOENIX.md — Stargate Process Operator Runbook

**The stargate process** rebuilds a failed node back to its original identity on new
hardware. This runbook covers generating and executing a **phoenix package**
end-to-end. It is the recovery counterpart to `FORGING.md` (first node) and
`NODE-SPAWNING.md` (additional nodes).

Set the paths once in the **Parameters** panel at the top — every command on this
page then uses your values, and each command's **Copy** button copies the resolved
text.

---

## When to use this

A node — the hatchery or any broodling — has suffered catastrophic hardware failure
and you are rebuilding it on replacement hardware. The phoenix package **preserves
identity** (same VMIDs, IPs, hostnames, k8s node name, cluster role) while **adapting
the physical layer** (ZFS topology, bridges) to the new hardware.

For a *new* node that should not conflict with existing identity, use the hatchery
process (`NODE-SPAWNING.md`) instead.

---

## Prerequisites

- A current `bootstrap-state.json` for the cell (any node holds the full cell state).
- PBS backups of the failed node's VMs reachable from the recovery environment.
- The KeePass database (embedded in the package or on a known path) + master password.
- Replacement hardware with bare Proxmox installed.

---

## Step 1 — Generate the phoenix playbook from cell state

The playbook is the machine-readable reconstruction plan. Generate the base playbook
directly from `bootstrap-state.json`:

```bash
python3 proxmox-bootstrap/phoenix-planner.py \
  --state {{STATE=proxmox-bootstrap/bootstrap-state.json}} \
  --hardware {{HARDWARE=hardware-profile-replacement.json}} \
  --output {{PLAYBOOK=phoenix-playbook.json}}
```

Omit `--hardware` if you do not yet have a replacement hardware profile — the planner
will plan against the original topology and adapt at run time. If you already have a
playbook to refine, pass it with `--playbook` instead of generating a new one.

The planner prints the restoration scope and wave count. Record them:

@field[Restoration scope (full / partial)]
@field[Number of waves in the playbook]
@field[Target node hostname (identity being restored)]

---

## Step 2 — Assemble the phoenix package

```bash
python3 proxmox-bootstrap/assemble-phoenix-package.py \
  --playbook {{PLAYBOOK=phoenix-playbook.json}} \
  --output-dir .
```

To embed the KeePass database for offline recovery, add `--kdbx /path/to/cell.kdbx`.

The assembler prints the package path and its **SHA-256**. Record the hash so you can
verify the copy on the replacement host:

@field[Phoenix package filename]
@field[Package SHA-256 (from the assembler output)]

---

## Step 3 — Copy to the replacement hardware and verify

```bash
scp phoenix-package-*.tar.gz root@{{HATCHERY_IP=192.168.1.20}}:/root/
```

On the replacement host, verify integrity before extracting:

```bash
sha256sum phoenix-package-*.tar.gz   # compare against the hash from Step 2
```

---

## Step 4 — Execute the waves

On the **replacement host**:

```bash
cd /root
tar xzf phoenix-package-*.tar.gz
bash run-all.sh
```

`run-all.sh` sources the KeePass gate (one master-password prompt), then runs each
wave in order, checkpointing as it goes. If a wave fails, fix the cause and re-run
`bash run-all.sh` — completed waves are skipped automatically.

The waves (generated per node; see ARCHITECTURE.md for the model):

| Wave | What it restores |
|---|---|
| 0 | Network reconstruction (bridges from declared topology) |
| 1 | ZFS pool restore/create (topology adapted to replacement disks) |
| 2 | Proxmox host configuration (hostname, /etc/hosts, datastores) |
| 2.5 | Template rebuild (conditional) |
| 3 | VM restore from PBS (identity-preserving; RECREATE where flagged) |
| 4 | k3s cluster membership (certs + node name preserved — rejoins) |
| 5 | Post-restore validation |

Record per-wave timing and anything unexpected:

@area[Per-wave actual time + any deviations from the playbook]

---

## Step 5 — Verify identity restored

```bash
qm list                          # original VMIDs present and running
kubectl get nodes                # restored node Ready under its ORIGINAL name
flux get kustomizations          # workloads reconciling
```

@field[Restored node shows Ready under original hostname? (y/n)]

After Wave 4 the node rejoins under its original identity; Flux then reconciles its
disposition-appropriate workloads automatically.

---

## If a wave fails

Every wave step failure writes a **failure package** (structured logs + a pre-composed
LLM analysis prompt). Attach it when asking for help, or feed it to an LLM to diagnose.
Fix the root cause, then resume with `bash run-all.sh`.

---

## Notes

@area[Anything that did not fit the steps above — unexpected prompts, hardware quirks, manual interventions]

---

*Broodforge PHOENIX.md — Stargate Process | Architecture v7.1*
