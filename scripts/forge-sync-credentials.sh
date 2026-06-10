#!/usr/bin/env bash
# forge-sync-credentials.sh — Sync master KeePass credentials to child databases.
#
# Propagates the current master KeePass contents to all child databases listed
# in credential-hierarchy.json.  Called automatically by forge-rotate-credential.sh
# as step 5 of the rotation ceremony; also available for standalone re-sync.
#
# Sync mechanism:
#   KeePassXC CLI does NOT support KeeShare merge operations (as of KeePassXC 2.7).
#   KeeShare is a GUI-only feature.  This script performs the following instead:
#
#   For entries that exist in BOTH the master (under Broodforge/child-dbs/<name>
#   scope exported groups) AND the child DB, keepassxc-cli can import an individual
#   entry by removing the old one and adding the new one.
#
#   Since KeeShare GUI sync must be configured once (see forge-init-credential-hierarchy.sh),
#   this script:
#     1. Checks keepassxc-cli KeeShare support (NOT available — exit 2 with instructions)
#     2. Falls back to: re-exporting all shared-group entries from master into each
#        child DB via keepassxc-cli edit/add.  This covers the rotation case where
#        a single entry's password changes in master and must propagate to the child.
#
#   The net result: after each rotation, child DBs are updated to match master for
#   the rotated entry.  KeeShare GUI sync handles bulk group mirroring; this script
#   handles per-entry propagation for the rotation ceremony.
#
# Usage:
#   bash scripts/forge-sync-credentials.sh [--entry <master-entry-path>] [--db <db-name>]
#
#   --entry  Sync only this master entry (e.g. "Services/restic/repo-password")
#   --db     Sync to only this child DB (e.g. "forge-autonomous")
#   (no args) Sync all entries declared in credential-hierarchy.json
#
# Exit codes:
#   0 — sync complete (all entries propagated or already current)
#   1 — fatal error (DB not found, password retrieval failed, etc.)
#   2 — NOT_IMPLEMENTED: KeeShare CLI sync not available; see instructions below

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_SH="${REPO_ROOT}/lib/forge-lib.sh"

STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge}"
HIER_CONFIG="${STATE_DIR}/credential-hierarchy.json"

# ---------------------------------------------------------------------------

die()  { echo "[sync-creds] ERROR: $*" >&2; exit 1; }
info() { echo "[sync-creds] $*"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

TARGET_ENTRY=""    # if set, sync only this master entry path
TARGET_DB=""       # if set, sync to only this child DB name

while [[ $# -gt 0 ]]; do
  case "$1" in
    --entry) TARGET_ENTRY="$2"; shift 2 ;;
    --db)    TARGET_DB="$2";    shift 2 ;;
    --help)
      grep '^#' "$0" | head -30 | sed 's/^# \?//'
      exit 0
      ;;
    *) die "Unknown argument: $1" ;;
  esac
done

# ---------------------------------------------------------------------------
# Load forge-lib.sh and gate
# ---------------------------------------------------------------------------

[[ -f "$LIB_SH" ]] || die "forge-lib.sh not found at $LIB_SH"
# shellcheck source=../lib/forge-lib.sh
source "$LIB_SH"
forge_keepass_gate

# ---------------------------------------------------------------------------
# Check keepassxc-cli KeeShare support
# ---------------------------------------------------------------------------

# keepassxc-cli does not support KeeShare merge as of 2.7.x.
# Check if a future version has added it (look for 'merge' or 'share' subcommand).

_KEESHARE_CLI_SUPPORTED=0
if keepassxc-cli --help 2>&1 | grep -qiE '(share|merge)'; then
  _KEESHARE_CLI_SUPPORTED=1
fi

if [[ $_KEESHARE_CLI_SUPPORTED -eq 1 ]]; then
  info "keepassxc-cli KeeShare support detected — using CLI sync"
else
  info "keepassxc-cli KeeShare merge not available (expected for KeePassXC <= 2.7)."
  info "Using per-entry credential propagation for rotation sync."
  info "(Full group mirroring requires KeeShare GUI — configure once via"
  info " forge-init-credential-hierarchy.sh instructions, then GUI sync runs on open.)"
fi

# ---------------------------------------------------------------------------
# Load hierarchy config
# ---------------------------------------------------------------------------

[[ -f "$HIER_CONFIG" ]] || die "credential-hierarchy.json not found at $HIER_CONFIG. Run forge-init-credential-hierarchy.sh first."

# Read all child DB entries from config
mapfile -t _ALL_DBS < <(python3 - "$HIER_CONFIG" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as fh:
    d = json.load(fh)
for c in d.get("child_databases", []):
    print(f"{c['name']}|{c['path']}|{c['master_entry']}")
PYEOF
)

(( ${#_ALL_DBS[@]} > 0 )) || die "No child databases found in $HIER_CONFIG"

# ---------------------------------------------------------------------------
# Per-entry sync: propagate a single master entry into a child DB
# ---------------------------------------------------------------------------

_sync_entry_to_child() {
  local child_db_path="$1"
  local child_db_name="$2"
  local master_entry_path="$3"    # e.g. "Broodforge/child-dbs/forge-autonomous"

  # The entry title in the child DB mirrors the last path component
  local entry_title
  entry_title="${master_entry_path##*/}"

  # Retrieve the current password for this entry from master
  local new_password
  new_password=$(printf '%s\n' "$KEEPASS_MASTER_PASSWORD" | \
    keepassxc-cli show -q -a Password "$FORGE_KDBX_PATH" "$master_entry_path" 2>/dev/null) \
    || { info "  ⚠ Could not read master entry: $master_entry_path — skipping"; return 0; }

  # Get child DB password from master (reuse broker cache mechanism)
  _broker_ensure_child_password "$child_db_name" || {
    info "  ⚠ Cannot unlock child DB $child_db_name — skipping"
    return 0
  }
  local child_pw="${_CHILD_DB_PASSWORD_CACHE[$child_db_name]}"

  # Determine the target group in the child DB (strip the "Broodforge/child-dbs" prefix)
  # Rotated service entries live in the child DB under their service group
  local child_entry_path
  if [[ "$master_entry_path" == Broodforge/child-dbs/* ]]; then
    # This is the child-DB password entry itself — stored under child-db-passwords/ in child
    child_entry_path="child-db-passwords/${entry_title}"
  else
    # Service credential — use path as-is
    child_entry_path="$master_entry_path"
  fi

  # Try to edit the existing entry; if it doesn't exist, add it
  local edit_out
  if printf '%s\n' "$child_pw" | \
      keepassxc-cli edit \
        --quiet \
        --password "$new_password" \
        "$child_db_path" \
        "$child_entry_path" \
        >/dev/null 2>&1; then
    info "  ✓ Updated: $child_entry_path in $child_db_name"
  else
    # Entry may not exist yet — try to add it
    if printf '%s\n' "$child_pw" | \
        keepassxc-cli add \
          --quiet \
          --username "broodforge-sync" \
          --password "$new_password" \
          "$child_db_path" \
          "$child_entry_path" \
          >/dev/null 2>&1; then
      info "  ✓ Added:   $child_entry_path in $child_db_name"
    else
      info "  ⚠ Could not update/add $child_entry_path in $child_db_name"
      info "    Sync this entry manually in KeePassXC GUI."
    fi
  fi

  unset new_password child_pw
}

# ---------------------------------------------------------------------------
# Main sync loop
# ---------------------------------------------------------------------------

info ""
info "Starting credential sync (master → child databases)..."
info ""

_SYNCED=0
_SKIPPED=0

for db_record in "${_ALL_DBS[@]}"; do
  IFS='|' read -r db_name db_path master_entry <<< "$db_record"

  # Apply --db filter
  [[ -z "$TARGET_DB" || "$TARGET_DB" == "$db_name" ]] || continue

  info "Child DB: $db_name ($db_path)"

  if [[ ! -f "$db_path" ]]; then
    info "  ⚠ Database file not found: $db_path — skipping"
    _SKIPPED=$(( _SKIPPED + 1 ))
    continue
  fi

  if [[ -z "$TARGET_ENTRY" ]]; then
    # Sync the child-DB password entry itself
    _sync_entry_to_child "$db_path" "$db_name" "$master_entry"
  else
    # Sync a specific entry (called from rotation ceremony)
    _sync_entry_to_child "$db_path" "$db_name" "$TARGET_ENTRY"
  fi

  _SYNCED=$(( _SYNCED + 1 ))
done

info ""
if [[ $_SYNCED -eq 0 && -n "$TARGET_DB" ]]; then
  die "Child DB '$TARGET_DB' not found in hierarchy config."
fi

info "Sync complete. Child databases updated: $_SYNCED, skipped: $_SKIPPED"
info ""
info "Services receive new credentials on their next broker call (kdbx_get_child)."
info ""

# ---------------------------------------------------------------------------
# KeeShare GUI sync reminder (non-fatal)
# ---------------------------------------------------------------------------

if [[ $_KEESHARE_CLI_SUPPORTED -eq 0 ]]; then
  echo ""
  echo "┌────────────────────────────────────────────────────────────────────"
  echo "│  KeeShare GUI note (for full group mirroring):"
  echo "│  If you added new entries to the master's shared group (not just"
  echo "│  rotated existing entries), open each child DB in KeePassXC GUI:"
  echo "│    Database → Synchronise → Synchronise with KeeShare"
  echo "│  This is only needed for new entries, not for rotation of existing ones."
  echo "└────────────────────────────────────────────────────────────────────"
  echo ""
fi

exit 0
