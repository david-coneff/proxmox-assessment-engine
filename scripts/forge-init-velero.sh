#!/usr/bin/env bash
# forge-init-velero.sh — Phase 2.H: Deploy Velero workload backup
# KeePass gate required (AD-060): Velero has access to all namespace data.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/forge-lib.sh"

BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge}"
VELERO_PROVIDER="${VELERO_PROVIDER:-aws}"
VELERO_BUCKET="${VELERO_BUCKET:-}"
VELERO_REGION="${VELERO_REGION:-}"
VELERO_CREDENTIAL_SECRET="${VELERO_CREDENTIAL_SECRET:-velero-credentials}"
VELERO_NAMESPACE="${VELERO_NAMESPACE:-velero}"
CHART_VERSION="${CHART_VERSION:-}"
DRY_RUN="${DRY_RUN:-false}"

forge_keepass_gate "Velero workload backup deployment"

[[ -z "${VELERO_BUCKET}" ]] && { echo "ERROR: VELERO_BUCKET must be set" >&2; exit 1; }
for bin in helm kubectl; do
    command -v "$bin" &>/dev/null || { echo "ERROR: $bin not found" >&2; exit 1; }
done

echo "==> Phase 2.H: Deploying Velero"
echo "    Provider:  ${VELERO_PROVIDER}"
echo "    Bucket:    ${VELERO_BUCKET}"
echo "    Region:    ${VELERO_REGION:-<none>}"
echo "    Secret:    ${VELERO_CREDENTIAL_SECRET}"
echo "    Namespace: ${VELERO_NAMESPACE}"
[ "${DRY_RUN}" = "true" ] && echo "    DRY RUN"
echo ""
echo "NOTE: Ensure k8s secret '${VELERO_CREDENTIAL_SECRET}' exists in"
echo "      namespace '${VELERO_NAMESPACE}' before running this script."
echo "      Retrieve credentials from KeePass — never pass them as args."
echo ""

CMD=(python3 "${SCRIPT_DIR}/../proxmox-bootstrap/velero_manager.py"
     --state-dir "${BROODFORGE_STATE_DIR}" deploy
     --provider "${VELERO_PROVIDER}" --bucket "${VELERO_BUCKET}"
     --credential-secret "${VELERO_CREDENTIAL_SECRET}"
     --namespace "${VELERO_NAMESPACE}")
[ -n "${VELERO_REGION}" ] && CMD+=(--region "${VELERO_REGION}")
[ -n "${CHART_VERSION}" ] && CMD+=(--chart-version "${CHART_VERSION}")
[ "${DRY_RUN}" = "true" ] && CMD+=(--dry-run)

if "${CMD[@]}"; then
    echo "==> Velero deployed. Verify: velero backup-location get"
else
    echo "ERROR: Velero deployment failed" >&2; exit 1
fi
