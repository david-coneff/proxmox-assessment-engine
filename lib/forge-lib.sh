#!/usr/bin/env bash
# forge-lib.sh — Shared broodforge operator utilities.
#
# Source this file from any broodforge script that needs the KeePass gate
# or other shared helpers.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/../lib/forge-lib.sh"
#   forge_keepass_gate
#
# AD-042: KeePass gate enforces operator presence before any secret access.
# AD-065: No autonomous pathway may initiate migration (forge_keepass_gate
#         is the enforcement mechanism in forge-quiesce.sh).

# ---------------------------------------------------------------------------
# KeePass gate — operator presence check
# ---------------------------------------------------------------------------
# forge_keepass_gate()
#
# Verifies the operator is present by prompting for the KeePass master
# password exactly once per session. Subsequent calls within the same
# session resume from the cached tmpfs session file without re-prompting.
#
# Environment/variables used:
#   FORGE_SESSION_FILE  — override session file path (default: /run/broodforge-forge.session)
#   FORGE_KDBX_PATH     — path to the .kdbx database (discovered or operator-provided)
#   FORGE_KDBX_UNLOCKED — set to 1 after successful unlock
#   KEEPASS_MASTER_PASSWORD — shell-local (not exported); cleared by caller on exit

FORGE_KDBX_PATH=""
FORGE_KDBX_UNLOCKED=0
_FORGE_SESSION_FILE="${FORGE_SESSION_FILE:-/run/broodforge-forge.session}"

forge_keepass_find_db() {
  local embedded
  embedded="$(ls "${SCRIPT_DIR}"/kdbx/*.kdbx 2>/dev/null | head -1)"
  if [ -n "$embedded" ]; then
    FORGE_KDBX_PATH="$embedded"
    echo "[kdbx] Using embedded database: $FORGE_KDBX_PATH"
    return 0
  fi
  read -rp "[kdbx] Path to KeePass database (.kdbx): " FORGE_KDBX_PATH
  [ -f "$FORGE_KDBX_PATH" ] || { echo "[kdbx] Not found: $FORGE_KDBX_PATH" >&2; return 1; }
}

forge_keepass_gate() {
  [ "$FORGE_KDBX_UNLOCKED" -eq 1 ] && return 0

  # Check for session file written by a previous phase in this forge run.
  # The file is 0600 and lives in /run (tmpfs) — cleared when forge.sh exits.
  if [ -f "$_FORGE_SESSION_FILE" ]; then
    local _perm
    _perm="$(stat -c '%a' "$_FORGE_SESSION_FILE" 2>/dev/null || echo "000")"
    if [ "$_perm" = "600" ]; then
      # Session file format: line 1 = FORGE_KDBX_PATH, line 2 = KEEPASS_MASTER_PASSWORD
      FORGE_KDBX_PATH="$(sed -n '1p' "$_FORGE_SESSION_FILE")"
      KEEPASS_MASTER_PASSWORD="$(sed -n '2p' "$_FORGE_SESSION_FILE")"
      export FORGE_KDBX_PATH
      FORGE_KDBX_UNLOCKED=1
      echo "[kdbx] Session resumed from forge session file." >/dev/tty
      return 0
    fi
    echo "[kdbx] WARNING: session file has unexpected permissions $_perm — re-prompting." >/dev/tty
  fi

  # Write prompts to /dev/tty so they reach the operator regardless of log redirects
  echo "" >/dev/tty
  echo "=================================================================" >/dev/tty
  echo " KeePass Unlock Gate — operator presence required" >/dev/tty
  echo " The master password is required once. All subsequent secret" >/dev/tty
  echo " lookups in this session are automatic." >/dev/tty
  echo "=================================================================" >/dev/tty
  forge_keepass_find_db || { echo "[kdbx] Cannot locate database." >&2; exit 1; }

  # Read password from /dev/tty to guarantee it is not captured in logs
  read -rsp "[kdbx] Master password: " KEEPASS_MASTER_PASSWORD </dev/tty >/dev/tty
  echo "" >/dev/tty

  # Export only the database path; keep the password as a shell-local variable
  # so child processes do not inherit it via their environment
  export FORGE_KDBX_PATH
  FORGE_KDBX_UNLOCKED=1

  # Persist kdbx path + password to tmpfs session file (0600) so later sub-scripts
  # in the same session can resume without re-prompting the operator.
  install -m 600 /dev/null "$_FORGE_SESSION_FILE" 2>/dev/null && \
    printf '%s\n%s' "$FORGE_KDBX_PATH" "$KEEPASS_MASTER_PASSWORD" > "$_FORGE_SESSION_FILE" || \
    echo "[kdbx] WARNING: could not write session file — later phases will re-prompt." >/dev/tty

  echo "[kdbx] Unlocked. Secrets broker active." >/dev/tty
  echo "" >/dev/tty
}

kdbx_get() {
  local path="$1"
  if command -v keepassxc-cli &>/dev/null; then
    # Pipe password via stdin — never passed as a command-line argument
    printf '%s\n' "$KEEPASS_MASTER_PASSWORD" | \
      keepassxc-cli show -q -a Password "$FORGE_KDBX_PATH" "$path" 2>/dev/null
  else
    echo "[kdbx] keepassxc-cli not found — retrieve '$path' manually" >&2
    echo "MANUAL_ENTRY_REQUIRED"
  fi
}

# ---------------------------------------------------------------------------
# Secrets broker — child database access (Phase 1.P)
# ---------------------------------------------------------------------------
#
# Reference format: child://<db-name>/<group>/<entry-title>
# Examples:
#   child://forge-autonomous/restic/repo-password
#   child://forge-autonomous/k8s/service-account-token
#   child://forge-spawn/cloud-init/node-keypair
#
# Security properties:
#   - Child DB passwords fetched from master and held in _CHILD_DB_PASSWORD_CACHE
#     (in-memory associative array — never written to disk, env, argv, or logs)
#   - forge_keepass_gate() must be called before any broker function
#   - kdbx_get_child / kdbx_totp output ONLY the requested secret value
#
# Config: ${BROODFORGE_STATE_DIR:-/var/lib/broodforge}/credential-hierarchy.json

# _CHILD_DB_PASSWORD_CACHE: db_name → password (session memory only)
declare -A _CHILD_DB_PASSWORD_CACHE 2>/dev/null || true

_BROKER_STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge}"

# _broker_hier_config: path to hierarchy config JSON
_broker_hier_config() {
  printf '%s/credential-hierarchy.json' "${BROODFORGE_STATE_DIR:-/var/lib/broodforge}"
}

# _broker_resolve_ref <ref>
# Parses "child://forge-autonomous/restic/repo-password"
# Outputs three newline-separated values: db_name, group, entry_title
# Returns 1 on malformed input.
_broker_resolve_ref() {
  local ref="$1"
  if [[ "$ref" != child://* ]]; then
    echo "[broker] not a child:// reference: $ref" >&2; return 1
  fi
  local without_scheme="${ref#child://}"
  local db_name="${without_scheme%%/*}"
  local remainder="${without_scheme#*/}"
  local group entry_title
  group="${remainder%%/*}"
  entry_title="${remainder#*/}"
  if [[ -z "$db_name" || -z "$group" || -z "$entry_title" || "$entry_title" == "$remainder" ]]; then
    echo "[broker] malformed reference (need child://db/group/entry): $ref" >&2; return 1
  fi
  printf '%s\n%s\n%s\n' "$db_name" "$group" "$entry_title"
}

# _broker_query_hier <db_name> <field>
# Reads a field ("path" or "master_entry") for a named child DB from the
# hierarchy config JSON.  Returns 1 if not found.
_broker_query_hier() {
  local db_name="$1" field="$2"
  local config
  config="$(_broker_hier_config)"
  if [[ ! -f "$config" ]]; then
    echo "[broker] credential-hierarchy.json not found: $config" >&2; return 1
  fi
  local result
  result=$(python3 - "$config" "$db_name" "$field" <<'PYEOF'
import json, sys
cfg, db_name, field = sys.argv[1], sys.argv[2], sys.argv[3]
with open(cfg) as fh:
    d = json.load(fh)
for child in d.get("child_databases", []):
    if child.get("name") == db_name:
        v = child.get(field, "")
        if v:
            print(v)
            sys.exit(0)
print(f"[broker] child DB not found in hierarchy: {db_name}", file=sys.stderr)
sys.exit(1)
PYEOF
) || return 1
  printf '%s' "$result"
}

# _broker_ensure_child_password <db_name>
# Populates _CHILD_DB_PASSWORD_CACHE[$db_name] from the master KeePass entry.
# forge_keepass_gate must have been called first (sets KEEPASS_MASTER_PASSWORD
# and FORGE_KDBX_PATH).  The password is NEVER echoed to stdout or stderr.
_broker_ensure_child_password() {
  local db_name="$1"
  # Already cached for this session — nothing to do
  [[ -n "${_CHILD_DB_PASSWORD_CACHE[$db_name]:-}" ]] && return 0

  local master_entry
  master_entry=$(_broker_query_hier "$db_name" "master_entry") \
    || { echo "[broker] cannot resolve master entry for child DB: $db_name" >&2; return 1; }

  local child_pw
  child_pw=$(printf '%s\n' "$KEEPASS_MASTER_PASSWORD" | \
    keepassxc-cli show -q -a Password "$FORGE_KDBX_PATH" "$master_entry" 2>/dev/null) \
    || { echo "[broker] failed to retrieve child DB password from master: $master_entry" >&2; return 1; }

  _CHILD_DB_PASSWORD_CACHE["$db_name"]="$child_pw"
  # Unset the local copy immediately — the password now lives only in the array
  unset child_pw
}

# kdbx_get_child <reference-path>
# Retrieve a credential from a child KeePass database.
# The child DB password is sourced from the master (cached after first call).
# Only the requested secret value is written to stdout.
#
# Requires: forge_keepass_gate called in the same session.
#
# Example:
#   secret=$(kdbx_get_child "child://forge-autonomous/restic/repo-password")
kdbx_get_child() {
  local ref="$1"

  local parsed
  parsed=$(_broker_resolve_ref "$ref") \
    || { echo "[broker] kdbx_get_child: invalid reference: $ref" >&2; return 1; }
  local db_name group entry_title
  db_name=$(printf '%s' "$parsed" | sed -n '1p')
  group=$(printf '%s' "$parsed"   | sed -n '2p')
  entry_title=$(printf '%s' "$parsed" | sed -n '3p')

  local child_db_path
  child_db_path=$(_broker_query_hier "$db_name" "path") \
    || { echo "[broker] kdbx_get_child: unknown child DB: $db_name" >&2; return 1; }

  [[ -f "$child_db_path" ]] \
    || { echo "[broker] kdbx_get_child: child DB file not found: $child_db_path" >&2; return 1; }

  _broker_ensure_child_password "$db_name" \
    || { echo "[broker] kdbx_get_child: cannot unlock child DB: $db_name" >&2; return 1; }

  local secret
  secret=$(printf '%s\n' "${_CHILD_DB_PASSWORD_CACHE[$db_name]}" | \
    keepassxc-cli show -q -a Password "$child_db_path" "${group}/${entry_title}" 2>/dev/null) \
    || { echo "[broker] kdbx_get_child: entry not found: ${group}/${entry_title} in $db_name" >&2; return 1; }

  printf '%s' "$secret"
}

# kdbx_totp <reference-path>
# Retrieve a current TOTP code from a child KeePass database entry.
# The TOTP seed must be configured in the KeePassXC entry's TOTP field.
# Uses the same broker session — child DB password never exposed.
#
# Example:
#   code=$(kdbx_totp "child://forge-autonomous/admin-ui/totp")
kdbx_totp() {
  local ref="$1"

  local parsed
  parsed=$(_broker_resolve_ref "$ref") \
    || { echo "[broker] kdbx_totp: invalid reference: $ref" >&2; return 1; }
  local db_name group entry_title
  db_name=$(printf '%s' "$parsed" | sed -n '1p')
  group=$(printf '%s' "$parsed"   | sed -n '2p')
  entry_title=$(printf '%s' "$parsed" | sed -n '3p')

  local child_db_path
  child_db_path=$(_broker_query_hier "$db_name" "path") \
    || { echo "[broker] kdbx_totp: unknown child DB: $db_name" >&2; return 1; }

  [[ -f "$child_db_path" ]] \
    || { echo "[broker] kdbx_totp: child DB file not found: $child_db_path" >&2; return 1; }

  _broker_ensure_child_password "$db_name" \
    || { echo "[broker] kdbx_totp: cannot unlock child DB: $db_name" >&2; return 1; }

  local totp_code
  totp_code=$(printf '%s\n' "${_CHILD_DB_PASSWORD_CACHE[$db_name]}" | \
    keepassxc-cli totp -q "$child_db_path" "${group}/${entry_title}" 2>/dev/null) \
    || { echo "[broker] kdbx_totp: TOTP entry not found: ${group}/${entry_title} in $db_name" \
              "(ensure TOTP seed is configured in KeePassXC)" >&2; return 1; }

  printf '%s' "$totp_code"
}
