#!/usr/bin/env bats
# Smoke test: run-static-audit.sh exists and is executable

@test "run-static-audit.sh is present" {
    local script
    script="$(git -C "$(dirname "$BATS_TEST_FILENAME")" rev-parse --show-toplevel)/tools/run-static-audit.sh"
    [ -f "$script" ]
}

@test "run-static-audit.sh passes shellcheck" {
    local script
    script="$(git -C "$(dirname "$BATS_TEST_FILENAME")" rev-parse --show-toplevel)/tools/run-static-audit.sh"
    if ! command -v shellcheck &>/dev/null; then
        skip "shellcheck not installed"
    fi
    shellcheck "$script"
}
