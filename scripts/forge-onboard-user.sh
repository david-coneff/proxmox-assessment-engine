#!/usr/bin/env bash
# forge-onboard-user.sh — Register a user and generate their per-service credentials.
#
# This script:
#   1. Adds the user to config/user-registry.json (via user_registry.py)
#   2. For each enrolled service:
#      a. Generates a strong random password
#      b. Generates a TOTP secret (base32, compatible with Authenticator apps)
#      c. Stores both in the master KeePass under Broodforge/users/<user>/<svc>/
#   3. Prints an onboarding summary (or writes to a file with --output)
#
# The operator delivers the onboarding output to the user securely (e.g. encrypted
# email, Signal, printed in person).  After the user acknowledges receipt, the
# operator may optionally run forge-throw-away-key to discard the master copy.
#
# Zero-knowledge note:
#   Services store password hashes (bcrypt/argon2) — not plaintext.  Vaultwarden
#   additionally encrypts all vault contents client-side.  Once the key is thrown
#   away, the admin cannot impersonate the user or read their data.
#
# Usage:
#   bash scripts/forge-onboard-user.sh \
#       --user alice \
#       --display-name "Alice Smith" \
#       --email alice@example.com \
#       --services vaultwarden,headscale,gitea \
#       [--output /path/to/alice-onboarding.txt] \
#       [--dry-run]
#
# Exit codes:
#   0 — success
#   1 — error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LIB_SH="${REPO_ROOT}/lib/forge-lib.sh"
USER_REG_PY="${REPO_ROOT}/proxmox-bootstrap/user_registry.py"
REGISTRY_JSON="${REPO_ROOT}/config/user-registry.json"

# ---------------------------------------------------------------------------

die()  { echo "[onboard] ERROR: $*" >&2; exit 1; }
info() { echo "[onboard] $*"; }
warn() { echo "[onboard] WARN: $*" >&2; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

USERNAME=""
DISPLAY_NAME=""
EMAIL=""
SERVICES=""
OUTPUT_FILE=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)         USERNAME="$2";       shift 2 ;;
    --display-name) DISPLAY_NAME="$2";   shift 2 ;;
    --email)        EMAIL="$2";          shift 2 ;;
    --services)     SERVICES="$2";       shift 2 ;;
    --output)       OUTPUT_FILE="$2";    shift 2 ;;
    --dry-run)      DRY_RUN=1;           shift   ;;
    --help)
      grep '^#' "$0" | head -40 | sed 's/^# \?//'
      exit 0
      ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$USERNAME"  ]] || die "--user is required"
[[ -n "$SERVICES"  ]] || die "--services is required (comma-separated)"

# ---------------------------------------------------------------------------
# Load forge-lib and gate
# ---------------------------------------------------------------------------

[[ -f "$LIB_SH" ]] || die "forge-lib.sh not found at $LIB_SH"
# shellcheck source=../lib/forge-lib.sh
source "$LIB_SH"
forge_keepass_gate

# ---------------------------------------------------------------------------
# Credential generators
# ---------------------------------------------------------------------------

# Generate a strong random password (48 chars, mixed alphanum + symbols)
_gen_password() {
  python3 -c "
import secrets, string
alphabet = string.ascii_letters + string.digits + '!@#\$%^&*()-_=+[]{}|;:,.<>?'
print(''.join(secrets.choice(alphabet) for _ in range(48)))
"
}

# Generate a TOTP base32 secret (20 bytes = 160 bits, RFC 6238 minimum)
_gen_totp_secret() {
  python3 -c "
import secrets, base64
raw = secrets.token_bytes(20)
print(base64.b32encode(raw).decode().rstrip('='))
"
}

# Generate a TOTP URI for QR code rendering
# otpauth://totp/<label>?secret=<secret>&issuer=<issuer>
_gen_totp_uri() {
  local label="$1"  # e.g. "alice@vaultwarden"
  local secret="$2"
  local issuer="${3:-broodforge}"
  python3 -c "
import urllib.parse
label  = urllib.parse.quote('${label}')
issuer = urllib.parse.quote('${issuer}')
print(f'otpauth://totp/{label}?secret=${secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30')
"
}

# ---------------------------------------------------------------------------
# KeePass helpers
# ---------------------------------------------------------------------------

# Store a new credential entry in master KeePass.
# _keepass_store_entry <entry_path> <username> <password> [notes]
_keepass_store_entry() {
  local entry_path="$1"
  local entry_user="$2"
  local entry_pw="$3"
  local entry_notes="${4:-}"

  # Check if entry already exists
  if printf '%s\n' "$KEEPASS_MASTER_PASSWORD" | \
      keepassxc-cli show -q "$FORGE_KDBX_PATH" "$entry_path" >/dev/null 2>&1; then
    # Update existing
    printf '%s\n' "$KEEPASS_MASTER_PASSWORD" | \
      keepassxc-cli edit --quiet \
        --username "$entry_user" \
        --password "$entry_pw" \
        "$FORGE_KDBX_PATH" "$entry_path" >/dev/null
  else
    # Create new (group is created automatically by keepassxc-cli add)
    local add_args=(--quiet --username "$entry_user" --password "$entry_pw")
    [[ -n "$entry_notes" ]] && add_args+=(--notes "$entry_notes")
    printf '%s\n' "$KEEPASS_MASTER_PASSWORD" | \
      keepassxc-cli add "${add_args[@]}" "$FORGE_KDBX_PATH" "$entry_path" >/dev/null
  fi
}

# ---------------------------------------------------------------------------
# Main onboarding logic
# ---------------------------------------------------------------------------

info ""
info "Starting onboarding for user: $USERNAME"
[[ $DRY_RUN -eq 1 ]] && info "(DRY RUN — no changes will be written)"
info ""

# Collect services list
IFS=',' read -ra SERVICE_LIST <<< "$SERVICES"

# Register user in registry (unless dry-run)
if [[ $DRY_RUN -eq 0 ]]; then
  python3 "$USER_REG_PY" \
    --registry "$REGISTRY_JSON" \
    --add \
    --username   "$USERNAME" \
    --display-name "${DISPLAY_NAME:-$USERNAME}" \
    --email      "${EMAIL:-}" \
    --services   "$SERVICES" \
    || die "Failed to add user to registry (user may already exist)"
fi

# Build onboarding package content
declare -A _CREDS_PW
declare -A _CREDS_TOTP
declare -A _CREDS_URI

for svc in "${SERVICE_LIST[@]}"; do
  svc="$(echo "$svc" | tr -d ' ')"
  [[ -z "$svc" ]] && continue

  pw_path="Broodforge/users/${USERNAME}/${svc}/password"
  totp_path="Broodforge/users/${USERNAME}/${svc}/totp-secret"

  pw=$(  _gen_password)
  totp=$(  _gen_totp_secret)
  uri=$( _gen_totp_uri "${USERNAME}@${svc}" "$totp" "broodforge-${svc}")

  _CREDS_PW["$svc"]="$pw"
  _CREDS_TOTP["$svc"]="$totp"
  _CREDS_URI["$svc"]="$uri"

  if [[ $DRY_RUN -eq 0 ]]; then
    info "  Storing credentials for $svc in KeePass..."
    _keepass_store_entry "$pw_path"   "$USERNAME" "$pw"
    _keepass_store_entry "$totp_path" "$USERNAME" "$totp" \
      "TOTP URI: $uri"
    info "  ✓ $svc"
  else
    info "  [dry-run] Would store: $pw_path"
    info "  [dry-run] Would store: $totp_path"
  fi

  unset pw totp
done

# ---------------------------------------------------------------------------
# Render onboarding package
# ---------------------------------------------------------------------------

_render_onboarding_package() {
  local width=72
  local border
  border=$(printf '%*s' "$width" '' | tr ' ' '─')

  echo "┌${border}┐"
  echo "│$(printf '%-*s' $width "  BROODFORGE ONBOARDING PACKAGE — ${USERNAME^^}")│"
  echo "│$(printf '%-*s' $width "  Generated: $(date -u '+%Y-%m-%d %H:%M UTC')")│"
  echo "├${border}┤"
  echo "│$(printf '%-*s' $width "  Keep this document secure. Do not share it.")│"
  echo "│$(printf '%-*s' $width "  Store in your personal password manager immediately.")│"
  echo "└${border}┘"
  echo ""

  for svc in "${SERVICE_LIST[@]}"; do
    svc="$(echo "$svc" | tr -d ' ')"
    [[ -z "$svc" ]] && continue

    echo "  ══ Service: ${svc} ══"
    echo "  Username : ${USERNAME}"
    echo "  Password : ${_CREDS_PW[$svc]}"
    echo ""
    echo "  TOTP setup:"
    echo "    Secret : ${_CREDS_TOTP[$svc]}"
    echo "    URI    : ${_CREDS_URI[$svc]}"
    echo ""
    echo "  Scan the URI with Google Authenticator, Aegis, or any TOTP app."
    echo "  Or enter the secret manually (SHA1, 6 digits, 30s period)."
    echo ""
    echo "  ─────────────────────────────────────────────────────────────────"
    echo ""
  done

  echo "  IMPORTANT — ZERO-KNOWLEDGE SERVICES:"
  echo "  Your Vaultwarden vault is encrypted with your master password."
  echo "  Broodforge admins cannot read your vault contents even with server"
  echo "  access. Your data is yours alone."
  echo ""
  echo "  Once you have saved these credentials, inform the administrator so"
  echo "  they can acknowledge onboarding and optionally discard their copy."
  echo ""
}

info ""
info "═══════════════════════════════════════════════"
info " ONBOARDING PACKAGE"
info "═══════════════════════════════════════════════"
info ""

if [[ -n "$OUTPUT_FILE" && $DRY_RUN -eq 0 ]]; then
  _render_onboarding_package > "$OUTPUT_FILE"
  info "Onboarding package written to: $OUTPUT_FILE"
  info "Deliver this file to $USERNAME via a secure channel."
else
  _render_onboarding_package
fi

# Clear credential arrays from memory
for svc in "${!_CREDS_PW[@]}"; do
  _CREDS_PW["$svc"]=""
  _CREDS_TOTP["$svc"]=""
  _CREDS_URI["$svc"]=""
done
unset _CREDS_PW _CREDS_TOTP _CREDS_URI

info ""
info "Next steps:"
info "  1. Deliver the onboarding package to $USERNAME via secure channel."
info "  2. Confirm they have saved their credentials."
info "  3. Run:  python3 proxmox-bootstrap/user_registry.py --registry config/user-registry.json"
info "           --disposition $USERNAME active"
info "     (already active by default)"
info "  4. Optional: once user confirms receipt, run forge-throw-away-key to"
info "     discard the master copy and achieve zero-knowledge admin access."
info ""

exit 0
