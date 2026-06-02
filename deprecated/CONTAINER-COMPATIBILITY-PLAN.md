# Container Compatibility Plan
## Post-Recovery Container Re-Setup for Podman and Docker

Date: 2026-05-31
Status: Planned — Phase 21 implementation
Architecture: v5.0 (Federated Infrastructure Digital Twin Platform)

---

## 1. Scope

This document covers the design of the post-recovery container compatibility
checker and the schema additions required to support deterministic re-setup
of containerized applications (Podman and Docker) after infrastructure recovery.

**In scope:**
- Container definition tracking (image digest, compose file, volumes, networks,
  env vars, secrets, resource requirements)
- Container data volume backup configuration (PBS, rclone, encrypted-archive)
- Compatibility checking: can this container start on the restored system?
- VM disk and data volume backup naming convention (extends backup.py)
- Setup flow integration (init wizard + external backup wizard)

**Out of scope:**
- Application-level data compatibility (database schema migration, internal
  config file updates) — this is application-specific and documented in
  per-service runbooks, not automated by this system
- Container orchestration (Kubernetes, Docker Swarm) — future Phase N
- Image scanning or vulnerability assessment

---

## 2. Core Principle: Infrastructure vs. Application Compatibility

The compatibility checker has a defined boundary:

```
Infrastructure layer (this system checks):
  ✓ Image digest pullable from registry
  ✓ Volume host paths exist on new system
  ✓ Resource requirements met (RAM, CPU)
  ✓ Network bridges exist and are routable
  ✓ All secret references still in registry
  ✓ All declared hostname env vars resolvable via DNS Registry
  ✓ Startup dependencies reachable in correct order

Application layer (NOT automated — runbook documents these):
  ✗ Data inside volumes compatible with restored image version
  ✗ Application-internal config files referencing old IPs
  ✗ Database schema migration requirements
  ✗ Application state consistency after partial restore
```

When infrastructure checks pass but application-level issues remain, the
compatibility score is NEEDS_REVIEW with specific flags, not BLOCKED.
The operator must consult the per-service runbook for application-level steps.

---

## 3. What Makes a Container Deterministically Re-Setupable

A container is deterministically re-setupable if the same inputs always
produce the same running service on equivalent hardware.

Required inputs:

```
Image:
  registry_url         Full registry URL (not just image name)
  image_digest         SHA256 digest of the image layer — NOT the tag.
                       Tags can move (`:latest`, `:stable`); digests are immutable.
                       Pinning the digest guarantees the exact same image bytes.
  tag                  Human-readable tag (informational only)

Configuration:
  compose_file_repo    Forgejo repo URL where compose/Quadlet file lives
  compose_file_path    Path within the repo
  compose_file_commit  Git commit hash at time of last deployment
  compose_file_digest  SHA256 of the file content (additional verification)

Networking:
  ports[]              host_port → container_port mappings
  networks[]           network name/bridge + hostname alias inside network
  exposed_hostname     How other services reach this container

Volumes:
  volumes[]            host_path → container_path, options
  data_volumes[]       Subset of volumes that contain persistent data
                       (these are what backup covers)

Environment:
  env_vars{}           Non-secret key→value pairs stored in config
  secret_references[]  Secret Registry IDs for secret env vars
                       (values retrieved from KeePass at runtime)

Resource requirements:
  minimum_ram_mb       Minimum RAM this container requires to run
  minimum_cpu_cores    Minimum CPU cores (fractional allowed)
  minimum_disk_gb      Minimum free disk on the volume host path

Ordering:
  runtime              podman | docker | podman-compose | docker-compose
  startup_after[]      Other containers/services that must be running first
  health_check         Command to verify the container is healthy post-start
```

---

## 4. Data Volume Backup Configuration

Container data volumes are backed up separately from the container
configuration itself. The backup method is declared per container.

### 4.1 Backup Methods

**PBS (Proxmox Backup Server)** — preferred for full VM coverage:
  - Captures the entire VM disk including all container volumes
  - Consistent backup via guest-agent quiescing
  - Offsite via rclone sync from PBS datastore
  - Recovery: restore VM from PBS, then start containers

**Rclone volume backup** — preferred for granular volume-level backup:
  - Backs up specific volume directories without full VM snapshot
  - Can run more frequently than full VM backup
  - Recovery: restore individual volumes, then start containers
  - Naming: `{cell_id}_{vmname}_{container}_{volume}_{timestamp}_{hash}.tar.gz.gpg`

**Encrypted archive** — same as general external backup:
  - Tarballs specific paths, GPG-encrypts, transfers to destination
  - Same naming convention as backup.py for config archives
  - Recovery: download, decrypt, extract, then start containers

### 4.2 Volume Backup Filename Convention

Extends the established backup.py naming scheme:

```
Config state archive:
  {cell_id}_{YYYY-MM-DD_HH_MM_SS}_{hash}.tar.gz.gpg

Container volume archive:
  {cell_id}_{vmname}_{container_name}_{volume_name}_{YYYY-MM-DD_HH_MM_SS}_{hash}.tar.gz.gpg

Example:
  proxmox-cell-a_forgejo_postgresql_data_2026-05-31_02_00_00_a3f7b2.tar.gz.gpg
  proxmox-cell-a_forgejo_forgejo-app_repos_2026-05-31_02_05_00_b4c8d1.tar.gz.gpg

PBS offsite sync (managed by rclone):
  {cell_id}_pbs_vm{vmid}_{vmname}_{YYYY-MM-DD_HH_MM_SS}_{hash}.tar.zst
  (tar.zst = PBS native format; hash computed from PBS chunk manifest)
```

The `{volume_name}` component is the declared volume name from the container
definition, not the full host path (paths may contain slashes that are
unsuitable for filenames).

---

## 5. Compatibility Check Algorithm

Runs after infrastructure restore, before container start.

### 5.1 Inputs

- `container_state_snapshot` — last known container state (from Historical State)
- `current_observed_state` — post-restore Observed State (Tier 1/2 assessment)
- `bootstrap_state` — declared configuration (DNS registry, secret registry)
- `recovery_system_capabilities` — RAM, CPU, disk of the restored system

### 5.2 Check Sequence (per container)

```
1. IMAGE CHECK
   Query registry: does digest {image_digest} exist?
   If registry unreachable:          NEEDS_REVIEW (flag: REGISTRY_UNREACHABLE)
   If digest not found:              INCOMPATIBLE (flag: IMAGE_DIGEST_MISSING)
   If tag moved to different digest: NEEDS_REVIEW (flag: IMAGE_TAG_DRIFT)
   If all match:                     PASS

2. VOLUME PATH CHECK
   For each data_volume.host_path:
     Does the path exist on the restored system?
     If no: does a backup exist to restore from?
       If backup exists:             NEEDS_REVIEW (flag: VOLUME_RESTORE_REQUIRED)
       If no backup:                 INCOMPATIBLE (flag: VOLUME_DATA_LOST)
     If path exists:                 PASS

3. RESOURCE CHECK
   current_ram >= container.minimum_ram_mb?
   current_cpu >= container.minimum_cpu_cores?
   volume_free_disk >= container.minimum_disk_gb?
   If any fail:                      INCOMPATIBLE (flag: INSUFFICIENT_RESOURCES)
   If all pass:                      PASS

4. NETWORK CHECK
   For each declared network:
     Does the bridge/network exist on restored system?
     If not:                         INCOMPATIBLE (flag: NETWORK_MISSING)
   For each exposed_hostname:
     Is it in DNS Registry and resolving to the correct IP?
     If IP changed:                  NEEDS_REVIEW (flag: HOSTNAME_IP_CHANGED)
   If all pass:                      PASS

5. SECRET CHECK
   For each secret_reference:
     Is the ID in the current Secret Registry?
     If not:                         INCOMPATIBLE (flag: SECRET_MISSING)
     Is the KeePass path accessible? (cannot verify remotely — documented assumption)
   If all pass:                      PASS

6. ENV VAR CHECK
   For each env_var value:
     Does it contain an IP or hostname from the old DNS Registry?
     If yes and that IP/hostname changed: NEEDS_REVIEW (flag: ENV_VAR_STALE)
     Recommendation: update env var or verify container handles hostname resolution
   If no stale references:           PASS

7. DEPENDENCY CHECK
   For each container in startup_after:
     Is that container itself COMPATIBLE or NEEDS_REVIEW?
     If INCOMPATIBLE:                BLOCKED (propagates)
   If all dependencies pass:         PASS

FINAL SCORE (worst of all checks):
  All PASS                          → COMPATIBLE
  Any NEEDS_REVIEW, no INCOMPATIBLE → NEEDS_REVIEW
  Any INCOMPATIBLE, no BLOCKED      → INCOMPATIBLE
  Any BLOCKED                       → BLOCKED
```

### 5.3 Score Meanings

| Score | Meaning | Action |
|---|---|---|
| COMPATIBLE | All infrastructure checks pass. Container should start. | Start it. |
| NEEDS_REVIEW | Infrastructure looks OK but something changed. Container may work. | Review flags, then start. Check application-level issues per runbook. |
| INCOMPATIBLE | At least one infrastructure check failed. Container will not start. | Resolve flagged issues first. |
| BLOCKED | A dependency is INCOMPATIBLE. Resolve that first. | Fix dependency chain from bottom up. |

---

## 6. Setup Flow Integration

### 6.1 Per-VM Container Declaration (init-bootstrap-state.py)

During cell initialization, for each VM that runs containers:

```
Does this VM run containerized applications? [y/N]

If yes:
  Container runtime: [podman / docker / podman-compose / docker-compose]

  For each container:
    Container name:
    Image (with registry URL):         e.g. registry.hub.docker.com/library/postgres
    Image tag:                         e.g. 15-alpine
    Compose file location (Forgejo):   e.g. https://forgejo.internal/infra/bootstrap/containers/postgresql/compose.yaml
    
    Data volumes (paths on host that contain persistent data):
      Enter paths one per line, empty line to finish:
      /opt/forgejo/data
      /opt/forgejo/repos
      
    Backup method for data volumes:
      [1] PBS (full VM snapshot — recommended if PBS is configured)
      [2] Rclone volume backup (granular, can run more frequently)
      [3] Encrypted archive (same as config backup — good for small volumes)
      
    Minimum resources:
      Minimum RAM (MB):   [512]
      Minimum CPU cores:  [1]
      Minimum disk (GB):  [10]
```

This populates the `containers` list in each VM's bootstrap-state entry.

### 6.2 Image Digest Pinning (setup-secrets.py / Tier 2 assessment)

When containers are first deployed, the Tier 2 assessment:
1. Queries running containers for their image digests
2. Records the digest in bootstrap-state.json alongside the tag
3. Future assessments detect if the digest has changed (image rebuilt or tag moved)

The operator can also manually pin a digest in the bootstrap-state before
deployment to ensure the exact image is used.

### 6.3 Compose File Registration

Compose files and Quadlets are stored in Forgejo (in the bootstrap or
configuration repo). The bootstrap-state records:
- The Forgejo URL and file path
- The commit hash at time of last deployment
- The SHA256 of the file content

On restore, the compatibility checker verifies the compose file in Forgejo
matches the recorded hash. If it doesn't, the file was changed after the last
deployment — the operator needs to decide which version to use.

---

## 7. New Schema Components

### 7.1 container-state-schema.json (new — Tier 2 assessment output)

Collected by Tier 2 assessment via:
- Podman: `podman inspect`, `podman volume ls`, `podman ps --format json`
- Docker: `docker inspect`, `docker volume ls`, `docker ps --format json`

Key fields:
- cell_id, vmid, vm_name
- container_runtime
- containers[]: observed container state (running/stopped, actual image digest,
  actual port bindings, actual volume mounts, actual resource usage)
- compose_files[]: detected compose files with their current hashes

### 7.2 bootstrap-state-schema.json additions

`containers` list added to vm_bootstrap definition:
- declared container configurations
- compose file Forgejo references
- data volume definitions with backup method
- minimum capability requirements
- secret references for container env vars

### 7.3 Volume Backup Archive Naming (backup.py extension)

New function: `volume_archive_filename(cell_id, vm_name, container_name, volume_name, dt)`
New function: `pbs_offsite_filename(cell_id, vmid, vm_name, dt)`

Both follow the established `{parts}_{YYYY-MM-DD_HH_MM_SS}_{6-char-hash}` pattern.

---

## 8. Implementation Phases

### Phase 21.5 — Container State Schema and Declaration

**Prerequisites:** Phase 21 (Failure Domain Modeling) complete.

- [ ] `data-model/container-state-schema.json` — Tier 2 assessment output
- [ ] `containers` list added to `vm_bootstrap` in bootstrap-state-schema.json
- [ ] `data_backup` config per container (method, destination, schedule)
- [ ] `volume_archive_filename()` added to backup.py
- [ ] `pbs_offsite_filename()` added to backup.py
- [ ] Container declaration prompts in init-bootstrap-state.py
- [ ] Schema validation tests

### Phase 21.6 — Container State Collection (Tier 2)

- [ ] `assessment/tier2/collectors/container_state.py`
  - Detects container runtime (podman/docker)
  - Collects running container list with image digests
  - Collects volume mounts
  - Collects compose files and hashes
  - Integrates into Tier 2 manifest
- [ ] Tests

### Phase 21.7 — Container Compatibility Checker

- [ ] `doc-gen/container_compat.py` — compatibility check engine
  - `check_image()` — registry reachability + digest validation
  - `check_volumes()` — host path existence + backup availability
  - `check_resources()` — RAM/CPU/disk against hardware state
  - `check_network()` — bridge existence + DNS registry consistency
  - `check_secrets()` — secret registry completeness
  - `check_env_vars()` — stale IP/hostname detection via DNS Registry diff
  - `check_dependencies()` — startup_after dependency chain
  - `score_container()` — COMPATIBLE | NEEDS_REVIEW | INCOMPATIBLE | BLOCKED
  - `score_vm()` — worst score across all containers
- [ ] Integration with recovery workbook renderer (container compatibility section)
- [ ] Integration with readiness scorer (ORANGE if any NEEDS_REVIEW, RED if INCOMPATIBLE)
- [ ] Tests (35+ covering all check types and score combinations)

### Phase 21.8 — Container Compatibility Report

- [ ] New report type: Container Compatibility Report
  - Per-container score and flag list
  - For each NEEDS_REVIEW flag: specific guidance and runbook reference
  - Volume restore steps (which backup to use, decrypt/extract commands)
  - Image pull commands (with digest pinning)
  - Env var update checklist (stale values identified, new values from DNS registry)
- [ ] Integration with recovery runbook (container section after VM restore section)
- [ ] Integration with engine.py (--mode container-compat)

---

## 9. Relationship to Existing Architecture

```
Tier 2 Assessment
    → container-state-schema.json   NEW
    → service-state-schema.json     EXTENDED (service contracts link to containers)

Historical State
    → stores container state snapshots
    → enables before/after diff for compatibility checking

Drift Detector (drift.py)
    → detects container state drift between assessments
    → feeds compatibility checker with what changed

DNS Registry
    → provides current vs. historical hostname→IP mapping
    → env var stale detection queries this

Secret Registry
    → validates all container secret_references still exist

Readiness Scorer (readiness.py)
    → EXTENDED: container compatibility scores feed cell readiness
    → INCOMPATIBLE container → ORANGE cell score
    → BLOCKED container → RED cell score

Recovery Workbook Renderer
    → EXTENDED: container compatibility section after VM restore waves

backup.py
    → EXTENDED: volume_archive_filename(), pbs_offsite_filename()
```

---

## 10. Design Decisions

### D-001: Digest pinning is required, tags are informational
Tags can be reassigned. Only the image digest provides a stable reference to
an exact image. The system records digests at deployment time and flags drift.

### D-002: Application-level compatibility is out of scope for automation
Database schema migration, application config file updates, and internal state
consistency after restore are application-specific. The system flags that review
is needed but does not attempt automated resolution. Per-service runbooks document
the manual steps.

### D-003: PBS is the preferred data backup for VMs with large disks
PBS is more efficient (incremental, compressed, deduplication) than per-volume
archives for large data sets. Per-volume rclone/encrypted-archive backup is
better for frequently-changed small volumes where fine-grained recovery is needed.

### D-004: Compose files live in Forgejo, not in bootstrap-state.json
Compose files can be large and contain complex configuration. Only the reference
(repo URL, path, commit hash, file digest) is stored in bootstrap-state.json.
The actual file is in Forgejo, making it version-controlled and diff-able.

### D-005: Container minimum_capability feeds cell readiness
If the restored hardware cannot meet the declared minimum_capability of any
container, that container scores INCOMPATIBLE, which propagates to the cell's
readiness score. This ensures capacity issues surface in the recovery readiness
report before recovery is attempted.
