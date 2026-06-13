#!/usr/bin/env bash
# forge-init-kyverno.sh — Phase 2.J: Install Kyverno policy engine via Helm
# KeePass gate: operator must unlock vault before this script proceeds.
#
# Usage:
#   bash scripts/forge-init-kyverno.sh [--chart-version <ver>] [--replicas <n>] [--namespace <ns>]
#
# Required env:
#   KEEPASS_DB   — path to KeePass KDBX (default: /var/lib/broodforge/secrets/broodforge.kdbx)
#
# Optional env:
#   KYVERNO_NAMESPACE      — Helm namespace (default: kyverno)
#   KYVERNO_REPLICAS       — replica count   (default: 1)
#   KYVERNO_CHART_VERSION  — pinned chart version (default: latest)
#   BROODFORGE_STATE_DIR   — state directory (default: /var/lib/broodforge/state)
set -euo pipefail

KEEPASS_DB="${KEEPASS_DB:-/var/lib/broodforge/secrets/broodforge.kdbx}"
KYVERNO_NAMESPACE="${KYVERNO_NAMESPACE:-kyverno}"
KYVERNO_REPLICAS="${KYVERNO_REPLICAS:-1}"
KYVERNO_CHART_VERSION="${KYVERNO_CHART_VERSION:-}"
BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge/state}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── KeePass gate ─────────────────────────────────────────────────────────────
if [[ ! -f "${KEEPASS_DB}" ]]; then
  echo "ERROR: KeePass database not found: ${KEEPASS_DB}" >&2
  echo "       Set KEEPASS_DB env var or place database at the default path." >&2
  exit 1
fi
echo "KeePass gate: database present at ${KEEPASS_DB}"
echo "Unlock required — operator must have vault access to proceed."
read -r -s -p "Enter KeePass master password (gate check only — not stored): " _kp_pw
echo
if [[ -z "${_kp_pw}" ]]; then
  echo "ERROR: Empty passphrase — aborting." >&2
  exit 1
fi
unset _kp_pw
echo "Gate passed."

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo "Checking prerequisites..."
for tool in helm kubectl python3; do
  if ! command -v "${tool}" &>/dev/null; then
    echo "ERROR: Required tool not found: ${tool}" >&2
    exit 1
  fi
done

kubectl cluster-info --request-timeout=10s >/dev/null 2>&1 || {
  echo "ERROR: Cannot reach Kubernetes cluster." >&2
  exit 1
}
echo "Cluster reachable."

# ── Install Kyverno ───────────────────────────────────────────────────────────
echo "Installing Kyverno (namespace: ${KYVERNO_NAMESPACE}, replicas: ${KYVERNO_REPLICAS})..."

PYTHON_ARGS=(
  "--replicas" "${KYVERNO_REPLICAS}"
  "--namespace" "${KYVERNO_NAMESPACE}"
)
[[ -n "${KYVERNO_CHART_VERSION}" ]] && \
  PYTHON_ARGS+=("--chart-version" "${KYVERNO_CHART_VERSION}")

BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR}" \
python3 "${REPO_ROOT}/proxmox-bootstrap/kyverno_manager.py" \
  install "${PYTHON_ARGS[@]}"

echo ""
echo "Kyverno installed."
echo "  Namespace : ${KYVERNO_NAMESPACE}"
echo "  Replicas  : ${KYVERNO_REPLICAS}"
echo ""
echo "Next steps:"
echo "  Register a policy : bash scripts/forge-kyverno-policy.sh --name <name> --manifest <path>"
echo "  Check health       : python3 proxmox-bootstrap/kyverno_manager.py health"
