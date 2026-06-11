#!/usr/bin/env bash
# forge-init-linkerd.sh — Phase 2.I: Install Linkerd service mesh
# KeePass gate required (AD-060): cluster-wide mTLS policy change.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/forge-lib.sh"

BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge}"
HA_MODE="${HA_MODE:-false}"
INSTALL_VIZ="${INSTALL_VIZ:-false}"
DRY_RUN="${DRY_RUN:-false}"

forge_keepass_gate "Linkerd service mesh installation"

echo "==> Phase 2.I: Installing Linkerd service mesh"
echo "    HA mode:     ${HA_MODE}"
echo "    Install viz: ${INSTALL_VIZ}"
[ "${DRY_RUN}" = "true" ] && echo "    DRY RUN — no changes will be applied"
echo ""

if ! command -v linkerd &>/dev/null; then
    echo "ERROR: linkerd CLI not found. Install it first:" >&2
    echo "  curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh" >&2
    exit 1
fi
if ! command -v kubectl &>/dev/null; then
    echo "ERROR: kubectl not found." >&2; exit 1
fi

echo "--> Running linkerd check --pre ..."
if ! linkerd check --pre; then
    echo "ERROR: pre-install checks failed. Resolve the issues above before installing." >&2
    exit 1
fi

echo "--> Installing Linkerd CRDs..."
CRD_CMD=(python3 "${SCRIPT_DIR}/../proxmox-bootstrap/linkerd_manager.py"
         --state-dir "${BROODFORGE_STATE_DIR}" install-crds)
[ "${DRY_RUN}" = "true" ] && CRD_CMD+=(--dry-run)
"${CRD_CMD[@]}"

echo "--> Installing Linkerd control plane..."
INSTALL_CMD=(python3 "${SCRIPT_DIR}/../proxmox-bootstrap/linkerd_manager.py"
             --state-dir "${BROODFORGE_STATE_DIR}" install)
[ "${HA_MODE}" = "true" ] && INSTALL_CMD+=(--ha)
[ "${DRY_RUN}" = "true" ] && INSTALL_CMD+=(--dry-run)
"${INSTALL_CMD[@]}"

if [[ "${INSTALL_VIZ}" = "true" ]]; then
    echo "--> Installing Linkerd viz extension..."
    VIZ_CMD=(python3 "${SCRIPT_DIR}/../proxmox-bootstrap/linkerd_manager.py"
             --state-dir "${BROODFORGE_STATE_DIR}" install-viz)
    [ "${DRY_RUN}" = "true" ] && VIZ_CMD+=(--dry-run)
    "${VIZ_CMD[@]}"
fi

if [[ "${DRY_RUN}" = "false" ]]; then
    echo "--> Running post-install health check..."
    sleep 10
    if ! linkerd check; then
        echo "WARNING: post-install check reported issues. Inspect above output." >&2
    fi
fi

echo ""
echo "==> Linkerd installation complete."
echo "    Enroll namespaces: bash scripts/forge-enroll-linkerd-ns.sh --namespace <ns>"
echo "    View mesh status:  linkerd viz dashboard (if viz installed)"
