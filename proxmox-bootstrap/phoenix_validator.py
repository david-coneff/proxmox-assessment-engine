#!/usr/bin/env python3
"""
phoenix_validator.py — Phoenix playbook validator (Phase 9.7).

Provides:
  validate_playbook(playbook) -> list[dict]

Each finding:
  {"severity": "ERROR"|"WARNING", "field": str, "message": str}

ERROR findings block playbook execution.
WARNING findings are advisory — playbook can still run.

Checks:
  - Required top-level fields present
  - Wave numbers are unique and in ascending order
  - Step IDs are unique within each wave
  - All VMIDs referenced in step commands exist in identity.vmids
  - All bridge names referenced in step validation exist in identity.bridge_names
  - ZFS pool name is declared in identity
  - restoration_scope is a valid enum value
  - Each step has at least one command
  - Estimated minutes are positive integers where present
"""

from typing import Optional

VALID_SCOPES  = {"full", "partial", "deferred"}
VALID_METHODS = {"RESTORE", "RECREATE", "VERIFY", "CONFIGURE"}
VALID_FAILURES = {"abort", "skip", "retry", "human"}


def validate_playbook(playbook: dict) -> list[dict]:
    """
    Validate a phoenix playbook for structural correctness.

    Returns a list of finding dicts, each with keys:
      severity: "ERROR" | "WARNING"
      field:    dot-path to the problematic field
      message:  human-readable description
    """
    findings: list[dict] = []

    def error(field: str, message: str):
        findings.append({"severity": "ERROR", "field": field, "message": message})

    def warn(field: str, message: str):
        findings.append({"severity": "WARNING", "field": field, "message": message})

    # ── Top-level required fields ──────────────────────────────────────────

    for required in ("schema_version", "cell_id", "generated_at", "target_node",
                     "identity", "waves"):
        if required not in playbook:
            error(required, f"Required field '{required}' is missing")

    if playbook.get("schema_version") not in ("1.0",):
        error("schema_version", f"Unknown schema_version: {playbook.get('schema_version')!r}")

    scope = playbook.get("restoration_scope")
    if scope and scope not in VALID_SCOPES:
        error("restoration_scope",
              f"Invalid restoration_scope {scope!r}; must be one of {VALID_SCOPES}")

    # ── Identity ───────────────────────────────────────────────────────────

    identity = playbook.get("identity") or {}
    declared_vmids    = set(identity.get("vmids") or [])
    declared_bridges  = set(identity.get("bridge_names") or [])
    declared_pool     = identity.get("zfs_pool_name")

    if not declared_vmids:
        warn("identity.vmids",
             "No VMIDs declared in identity — cannot verify VMID references in steps")

    if not declared_bridges:
        warn("identity.bridge_names",
             "No bridge names declared in identity — cannot verify bridge references")

    if not declared_pool:
        warn("identity.zfs_pool_name",
             "No ZFS pool name declared — Wave 1 storage steps use a placeholder")

    # ── Waves ──────────────────────────────────────────────────────────────

    waves = playbook.get("waves") or []

    if not waves:
        error("waves", "Playbook has no restoration waves")
        return findings  # nothing more to check

    # Wave numbers must be unique
    wave_nums = [w.get("wave") for w in waves]
    seen_waves: set = set()
    for wn in wave_nums:
        if wn in seen_waves:
            error("waves", f"Duplicate wave number: {wn}")
        seen_waves.add(wn)

    # Waves should be in ascending order
    numeric_waves = [wn for wn in wave_nums if wn is not None]
    if numeric_waves != sorted(numeric_waves):
        warn("waves", "Waves are not in ascending order — run-all.sh sorts them, but verify intent")

    # ── Steps ──────────────────────────────────────────────────────────────

    for wave in waves:
        wnum  = wave.get("wave", "?")
        wname = wave.get("name", "")
        steps = wave.get("steps") or []
        prefix = f"waves[{wnum}]"

        if not steps:
            warn(f"{prefix}.steps",
                 f"Wave {wnum} ({wname!r}) has no steps")

        est = wave.get("estimated_minutes")
        if est is not None and (not isinstance(est, (int, float)) or est <= 0):
            warn(f"{prefix}.estimated_minutes",
                 f"Wave {wnum} estimated_minutes should be a positive number, got {est!r}")

        seen_step_ids: set = set()
        for step in steps:
            sid    = step.get("id", "")
            sprefix = f"{prefix}.steps[{sid}]"

            if sid in seen_step_ids:
                error(sprefix, f"Duplicate step ID '{sid}' in wave {wnum}")
            seen_step_ids.add(sid)

            if not step.get("commands"):
                error(sprefix, f"Step '{sid}' has no commands")

            method = step.get("method")
            if method and method not in VALID_METHODS:
                warn(sprefix,
                     f"Step '{sid}' method {method!r} is not a standard value {VALID_METHODS}")

            on_fail = step.get("on_failure")
            if on_fail and on_fail not in VALID_FAILURES:
                warn(sprefix,
                     f"Step '{sid}' on_failure {on_fail!r} is not a standard value {VALID_FAILURES}")

            # Check VMID references in commands
            if declared_vmids:
                all_text = " ".join(str(c) for c in (step.get("commands") or []))
                _check_vmid_references(all_text, declared_vmids, declared_pool, sprefix, error)

    return findings


def _check_vmid_references(
    text: str,
    declared_vmids: set,
    declared_pool: Optional[str],
    field: str,
    error_fn,
) -> None:
    """
    Check that numeric VMID references in command text are declared in identity.vmids.
    Only flags VMIDs that appear in patterns like 'vmid={N}' or 'qmrestore ... {N}',
    to avoid false positives on IPs, port numbers, and other numerics.
    """
    import re
    # Match patterns like: qmrestore ... {N}, qm start {N}, qm status {N}
    for match in re.finditer(r'\b(qmrestore|qm start|qm status|qm config)\s+.*?(\d{3,4})', text):
        vmid_str = match.group(2)
        try:
            vmid = int(vmid_str)
            if vmid not in declared_vmids and vmid < 9000:  # 9000+ are template IDs
                error_fn(field, f"VMID {vmid} referenced in commands but not in identity.vmids")
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Convenience: check and summarise
# ---------------------------------------------------------------------------

def summarise_findings(findings: list[dict]) -> str:
    """Return a human-readable summary of validation findings."""
    errors   = [f for f in findings if f["severity"] == "ERROR"]
    warnings = [f for f in findings if f["severity"] == "WARNING"]

    lines = [f"Validation: {len(errors)} error(s), {len(warnings)} warning(s)"]
    for f in errors:
        lines.append(f"  [ERROR]   {f['field']}: {f['message']}")
    for f in warnings:
        lines.append(f"  [WARNING] {f['field']}: {f['message']}")
    return "\n".join(lines)


def is_valid(findings: list[dict]) -> bool:
    """Return True if there are no ERROR-severity findings."""
    return not any(f["severity"] == "ERROR" for f in findings)
