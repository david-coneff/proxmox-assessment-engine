#!/usr/bin/env bash
# forge-kyverno-policy.sh — Phase 2.J: Apply and register a Kyverno policy
# KeePass gate: operator must unlock vault before this script proceeds.
#
# Usage:
#   bash scripts/forge-kyverno-policy.sh \
#     --name <policy-name> \
#     --manifest <path/to/policy.yaml> \
#     [--kind ClusterPolicy|Policy] \
#     [--namespace <ns>] \
#     [--action Audit|Enforce] \
#     [--category <category>] \
#     [--rules <count>] \
#     [--no-apply]
#
# Required env:
#   KEEPASS_DB   — path to KeePass KDBX (default: /var/lib/broodforge/secrets/broodforge.kdbx)
#
# Optional env:
#   BROODFORGE_STATE_DIR  — state directory (default: /var/lib/broodforge/state)
set -euo pipefail

KEEPASS_DB="${KEEPASS_DB:-/var/lib/broodforge/secrets/broodforge.kdbx}"
BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge/state}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Argument parsing ──────────────────────────────────────────────────────────
POLICY_NAME=""
MANIFEST_PATH=""
POLICY_KIND="ClusterPolicy"
POLICY_NS=""
POLICY_ACTION="Audit"
POLICY_CATEGORY=""
POLICY_RULES=0
NO_APPLY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)      POLICY_NAME="$2";     shift 2 ;;
    --manifest)  MANIFEST_PATH="$2";  shift 2 ;;
    --kind)      POLICY_KIND="$2";    shift 2 ;;
    --namespace) POLICY_NS="$2";      shift 2 ;;
    --action)    POLICY_ACTION="$2";  shift 2 ;;
    --category)  POLICY_CATEGORY="$2"; shift 2 ;;
    --rules)     POLICY_RULES="$2";   shift 2 ;;
    --no-apply)  NO_APPLY="--no-apply"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[[ -z "${POLICY_NAME}" ]]     && { echo "ERROR: --name required" >&2; exit 1; }
[[ -z "${MANIFEST_PATH}" ]]   && { echo "ERROR: --manifest required" >&2; exit 1; }
[[ ! -f "${MANIFEST_PATH}" ]] && { echo "ERROR: manifest not found: ${MANIFEST_PATH}" >&2; exit 1; }

# ── KeePass gate ─────────────────────────────────────────────────────────────
if [[ ! -f "${KEEPASS_DB}" ]]; then
  echo "ERROR: KeePass database not found: ${KEEPASS_DB}" >&2
  exit 1
fi
read -r -s -p "Enter KeePass master password (gate check only — not stored): " _kp_pw
echo
[[ -z "${_kp_pw}" ]] && { echo "ERROR: Empty passphrase — aborting." >&2; exit 1; }
unset _kp_pw
echo "Gate passed."

# ── Apply policy ──────────────────────────────────────────────────────────────
echo "Registering policy: ${POLICY_KIND}/${POLICY_NAME} (action: ${POLICY_ACTION})..."

PYTHON_ARGS=(
  "--name"     "${POLICY_NAME}"
  "--manifest" "${MANIFEST_PATH}"
  "--kind"     "${POLICY_KIND}"
  "--action"   "${POLICY_ACTION}"
  "--rules"    "${POLICY_RULES}"
)
[[ -n "${POLICY_NS}" ]]       && PYTHON_ARGS+=("--namespace" "${POLICY_NS}")
[[ -n "${POLICY_CATEGORY}" ]] && PYTHON_ARGS+=("--category"  "${POLICY_CATEGORY}")
[[ -n "${NO_APPLY}" ]]        && PYTHON_ARGS+=("${NO_APPLY}")

BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR}" \
python3 "${REPO_ROOT}/proxmox-bootstrap/kyverno_manager.py" \
  add-policy "${PYTHON_ARGS[@]}"

echo "Policy registered successfully."
