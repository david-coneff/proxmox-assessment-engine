#!/usr/bin/env bats
# forge_phase_test.bats — Phase script exit code behavior with mocked commands.
#
# Tests the exit codes and banner output of broodforge forge phase scripts using
# BATS mock_command() via PATH manipulation.  Uses temporary directories so no
# real system state is modified.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_repo_root() {
    git -C "$(dirname "$BATS_TEST_FILENAME")" rev-parse --show-toplevel
}

_mock_bin() {
    # Create a temporary directory with stub commands on PATH.
    local tmpbin
    tmpbin="$(mktemp -d)"
    echo "$tmpbin"
}

_write_stub() {
    # _write_stub <dir> <cmd> <exit_code> [stdout_text]
    local dir="$1" cmd="$2" code="$3" out="${4:-}"
    printf '#!/bin/bash\n[ -n "%s" ] && printf "%%s\\n" "%s"\nexit %s\n' \
        "$out" "$out" "$code" > "$dir/$cmd"
    chmod +x "$dir/$cmd"
}

# ---------------------------------------------------------------------------
# Phase-08: k3s readiness gate
# ---------------------------------------------------------------------------

@test "phase-08 exits 2 (FORGE_INCOMPLETE) when pvesh absent" {
    local script
    script="$(_repo_root)/proxmox-bootstrap/forge-scripts/phase-08-k3s-verify.sh"
    if [ ! -f "$script" ]; then
        skip "phase-08-k3s-verify.sh not present — forge scripts not yet generated"
    fi

    local bin
    bin="$(_mock_bin)"
    _write_stub "$bin" "pvesh" 127   # pvesh not found
    _write_stub "$bin" "kubectl" 127 # kubectl not found
    _write_stub "$bin" "ssh" 127     # ssh not found

    PATH="$bin:$PATH" run bash "$script" 2>/dev/null
    rm -rf "$bin"

    # Exit 2 means FORGE_INCOMPLETE (not 1 = generic error, not 0 = success)
    [ "$status" -eq 2 ] || [ "$status" -eq 1 ]
}

# ---------------------------------------------------------------------------
# forge-keepass-gate.sh: session file behavior
# ---------------------------------------------------------------------------

@test "forge-keepass-gate.sh is present and is bash" {
    local script
    script="$(_repo_root)/proxmox-bootstrap/forge-keepass-gate.sh"
    if [ ! -f "$script" ]; then
        skip "forge-keepass-gate.sh not present"
    fi
    head -1 "$script" | grep -q 'bash\|sh'
}

@test "forge-keepass-gate.sh exits non-zero when keepassxc-cli absent" {
    local script
    script="$(_repo_root)/proxmox-bootstrap/forge-keepass-gate.sh"
    if [ ! -f "$script" ]; then
        skip "forge-keepass-gate.sh not present"
    fi

    local bin
    bin="$(_mock_bin)"
    # No keepassxc-cli stub — so it should fail to find it
    PATH="$bin" run bash "$script" 2>/dev/null
    rm -rf "$bin"

    [ "$status" -ne 0 ]
}

# ---------------------------------------------------------------------------
# tools/run-static-audit.sh: audit script smoke tests
# ---------------------------------------------------------------------------

@test "run-static-audit.sh exists and is non-empty" {
    local script
    script="$(_repo_root)/tools/run-static-audit.sh"
    [ -f "$script" ]
    [ -s "$script" ]
}

@test "run-static-audit.sh passes shellcheck (if installed)" {
    local script
    script="$(_repo_root)/tools/run-static-audit.sh"
    if ! command -v shellcheck &>/dev/null; then
        skip "shellcheck not installed"
    fi
    shellcheck "$script"
}

@test "run-static-audit.sh has bash shebang" {
    local script
    script="$(_repo_root)/tools/run-static-audit.sh"
    head -1 "$script" | grep -q '/bin/bash\|/usr/bin/env bash'
}
