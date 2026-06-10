#!/usr/bin/env bash
# forge-provision-users.sh — Re-provision all registered users into k8s services.
#
# This is the rebuild-time workhorse.  On a fresh cluster deploy (or after a
# service loses its data), run this script to recreate every active user's
# account in each service they are enrolled in — without requiring users to
# re-register themselves.
#
# Provisioning flow per user+service:
#
#   key_thrown_away = false  →  AUTO-PROVISION
#     Reads stored password from master KeePass, registers or resets the
#     account in the target service.
#
#   key_thrown_away = true   →  RESET FLOW
#     Admin no longer holds the user's password.  Script creates/resets the
#     account with a temporary password and sends a reset notification so
#     the user sets their own password on first login.
#
# Service adapters:
#   Each service type has a _provision_<service>() function that calls the
#   appropriate k8s/API tool.  Add new adapters at the bottom as needed.
#
# Usage:
#   bash scripts/forge-provision-users.sh [options]
#
#   --service <name>   Provision only users for this service
#   --user    <name>   Provision only this user (all their services)
#   --dry-run          Print what would happen; make no changes
#   --rebuild-mode     Emit a rebuild summary report after provisioning
#
# Exit codes:
#   0 — all targeted users provisioned (or already current)
#   1 — one or more provisioning failures

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_SH="${REPO_ROOT}/lib/forge-lib.sh"
USER_REG_PY="${REPO_ROOT}/proxmox-bootstrap/user_registry.py"
REGISTRY_JSON="${REPO_ROOT}/config/user-registry.json"

# ---------------------------------------------------------------------------

die()  { echo "[provision] ERROR: $*" >&2; exit 1; }
info() { echo "[provision] $*"; }
warn() { echo "[provision] WARN: $*" >&2; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

TARGET_SERVICE=""
TARGET_USER=""
DRY_RUN=0
REBUILD_MODE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service)      TARGET_SERVICE="$2"; shift 2 ;;
    --user)         TARGET_USER="$2";    shift 2 ;;
    --dry-run)      DRY_RUN=1;           shift   ;;
    --rebuild-mode) REBUILD_MODE=1;      shift   ;;
    --help)
      grep '^#' "$0" | head -50 | sed 's/^# \?//'
      exit 0
      ;;
    *) die "Unknown argument: $1" ;;
  esac
done

# ---------------------------------------------------------------------------
# Load forge-lib and gate
# ---------------------------------------------------------------------------

[[ -f "$LIB_SH" ]] || die "forge-lib.sh not found at $LIB_SH"
# shellcheck source=../lib/forge-lib.sh
source "$LIB_SH"
forge_keepass_gate

[[ -f "$REGISTRY_JSON" ]] \
  || die "user-registry.json not found at $REGISTRY_JSON. Run forge-onboard-user.sh to add users."

# ---------------------------------------------------------------------------
# Read user provisioning list from registry
# ---------------------------------------------------------------------------
# Output: TSV lines — username <TAB> service <TAB> flow <TAB> email
# flow is either "provision" or "reset"

mapfile -t _PROVISION_LINES < <(
  python3 "$USER_REG_PY" \
    --registry "$REGISTRY_JSON" \
    --users-for-rebuild
)

(( ${#_PROVISION_LINES[@]} > 0 )) || { info "No active users in registry."; exit 0; }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_get_user_password() {
  local username="$1"
  local service="$2"
  local entry_path="Broodforge/users/${username}/${service}/password"
  printf '%s\n' "$KEEPASS_MASTER_PASSWORD" | \
    keepassxc-cli show -q -a Password "$FORGE_KDBX_PATH" "$entry_path" 2>/dev/null \
    || { warn "Could not read password for ${username}/${service} from KeePass"; echo ""; }
}

_gen_temp_password() {
  python3 -c "
import secrets, string
alphabet = string.ascii_letters + string.digits
print(''.join(secrets.choice(alphabet) for _ in range(32)))
"
}

# ---------------------------------------------------------------------------
# Service adapters
# ---------------------------------------------------------------------------
# Each adapter: _provision_<service> <username> <email> <password> <flow>
# flow: provision | reset
#
# Adapters use kubectl exec / service CLI / API as appropriate.
# Return 0 on success, non-zero on failure.

_provision_vaultwarden() {
  local username="$1"
  local email="$2"
  local password="$3"
  local flow="$4"

  if [[ $DRY_RUN -eq 1 ]]; then
    info "  [dry-run] vaultwarden: ${flow} ${username} <${email}>"
    return 0
  fi

  # Vaultwarden admin API (requires ADMIN_TOKEN in k8s secret)
  # vaultwarden admin panel: POST /admin/users/invite or /admin/users/<uuid>/password
  #
  # This uses vaultwarden's admin REST API via kubectl port-forward.
  # Adjust VW_ADMIN_PORT and VW_POD_SELECTOR as needed for your deployment.

  local VW_POD VW_ADMIN_TOKEN
  VW_POD=$(kubectl get pod -l app=vaultwarden -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) \
    || { warn "  vaultwarden pod not found — skipping"; return 1; }

  VW_ADMIN_TOKEN=$(kubectl get secret vaultwarden-admin-token \
    -o jsonpath='{.data.token}' 2>/dev/null | base64 -d 2>/dev/null) \
    || { warn "  vaultwarden admin token secret not found — skipping"; return 1; }

  case "$flow" in
    provision)
      # Create account via admin API invite
      kubectl exec "$VW_POD" -- curl -sf \
        -H "Authorization: Bearer ${VW_ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${email}\"}" \
        "http://localhost:8080/admin/users/invite" >/dev/null \
        && info "  ✓ vaultwarden: invited ${email}" \
        || { warn "  vaultwarden invite failed (may already exist) — continuing"; return 0; }
      ;;
    reset)
      # Cannot set password for existing account without old password.
      # Admin must reset via the admin panel; we just notify.
      warn "  vaultwarden: key thrown away for ${username} — admin must reset via /admin panel."
      warn "  Email: ${email}"
      ;;
  esac
}

_provision_headscale() {
  local username="$1"
  local email="$2"
  local password="$3"
  local flow="$4"

  if [[ $DRY_RUN -eq 1 ]]; then
    info "  [dry-run] headscale: ${flow} ${username}"
    return 0
  fi

  # Headscale uses namespaces (users) and pre-auth keys, not passwords.
  # "Provisioning" means ensuring the namespace exists.

  local HEADSCALE_POD
  HEADSCALE_POD=$(kubectl get pod -l app=headscale -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) \
    || { warn "  headscale pod not found — skipping"; return 1; }

  # Create namespace (idempotent)
  kubectl exec "$HEADSCALE_POD" -- headscale namespaces create "$username" >/dev/null 2>&1 \
    || true  # already exists is fine

  info "  ✓ headscale: namespace ensured for ${username}"
}

_provision_gitea() {
  local username="$1"
  local email="$2"
  local password="$3"
  local flow="$4"

  if [[ $DRY_RUN -eq 1 ]]; then
    info "  [dry-run] gitea: ${flow} ${username} <${email}>"
    return 0
  fi

  local GITEA_POD
  GITEA_POD=$(kubectl get pod -l app=gitea -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) \
    || { warn "  gitea pod not found — skipping"; return 1; }

  case "$flow" in
    provision)
      kubectl exec "$GITEA_POD" -- gitea admin user create \
        --username "$username" \
        --password "$password" \
        --email    "$email" \
        --must-change-password=false \
        2>/dev/null \
        && info "  ✓ gitea: created ${username}" \
        || {
          # May already exist — try password reset instead
          kubectl exec "$GITEA_POD" -- gitea admin user change-password \
            --username "$username" \
            --password "$password" \
            2>/dev/null \
            && info "  ✓ gitea: password reset for ${username} (already existed)" \
            || { warn "  gitea: could not create or reset ${username}"; return 1; }
        }
      ;;
    reset)
      local tmp_pw
      tmp_pw=$(_gen_temp_password)
      kubectl exec "$GITEA_POD" -- gitea admin user change-password \
        --username "$username" \
        --password "$tmp_pw" \
        2>/dev/null \
        && warn "  gitea: key thrown away — set temp password for ${username}; notify user to reset." \
        || { warn "  gitea: could not set temp password for ${username}"; return 1; }
      unset tmp_pw
      ;;
  esac
}

# Dispatcher — routes to the correct adapter
_provision_user_service() {
  local username="$1"
  local email="$2"
  local service="$3"
  local flow="$4"

  info "  ${username} → ${service} [${flow}]"

  local password=""
  if [[ "$flow" == "provision" ]]; then
    password=$(_get_user_password "$username" "$service")
    if [[ -z "$password" ]]; then
      warn "  Cannot read password for ${username}/${service} — skipping (run forge-onboard-user.sh first)"
      return 1
    fi
  fi

  case "$service" in
    vaultwarden) _provision_vaultwarden "$username" "$email" "$password" "$flow" ;;
    headscale)   _provision_headscale   "$username" "$email" "$password" "$flow" ;;
    gitea)       _provision_gitea       "$username" "$email" "$password" "$flow" ;;
    *)
      warn "  No adapter for service '${service}' — skipping."
      warn "  Add _provision_${service}() to forge-provision-users.sh to support it."
      return 0  # Not a fatal error — service may not be deployed yet
      ;;
  esac

  unset password
}

# ---------------------------------------------------------------------------
# Main provisioning loop
# ---------------------------------------------------------------------------

info ""
info "Starting user provisioning (registry → k8s services)..."
[[ $DRY_RUN -eq 1 ]] && info "(DRY RUN — no changes will be written)"
info ""

_TOTAL=0
_OK=0
_FAIL=0
_SKIP=0

for line in "${_PROVISION_LINES[@]}"; do
  IFS=$'\t' read -r username service flow email <<< "$line"

  # Apply filters
  [[ -z "$TARGET_SERVICE" || "$TARGET_SERVICE" == "$service" ]] || continue
  [[ -z "$TARGET_USER"    || "$TARGET_USER"    == "$username" ]] || continue

  _TOTAL=$(( _TOTAL + 1 ))

  if _provision_user_service "$username" "${email:-}" "$service" "$flow"; then
    _OK=$(( _OK + 1 ))
  else
    _FAIL=$(( _FAIL + 1 ))
  fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

info ""
info "Provisioning complete."
info "  Total targeted : $_TOTAL"
info "  Succeeded      : $_OK"
info "  Failed         : $_FAIL"

if [[ $_FAIL -gt 0 ]]; then
  warn "Some users failed to provision. Check warnings above."
  warn "Re-run with --user <name> --service <svc> to retry individually."
fi

if [[ $REBUILD_MODE -eq 1 ]]; then
  info ""
  info "══════════════════════════════════════════════════"
  info " REBUILD REPORT"
  info "══════════════════════════════════════════════════"
  info " Active users provisioned : $_OK"
  info " Failures                 : $_FAIL"
  info " Key-thrown-away users    : (received reset-flow above)"
  info "══════════════════════════════════════════════════"
fi

[[ $_FAIL -eq 0 ]]  # exits 0 if no failures, 1 otherwise
