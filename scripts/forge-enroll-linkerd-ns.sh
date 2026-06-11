#!/usr/bin/env bash
# forge-enroll-linkerd-ns.sh — Phase 2.I: Enroll a namespace into Linkerd mesh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge}"

usage() {
    cat <<EOF
Usage: forge-enroll-linkerd-ns.sh --namespace NS [--no-inject] [--no-mtls] [--dry-run]

  --namespace NS   Kubernetes namespace to enroll
  --no-inject      Skip setting linkerd.io/inject=enabled annotation
  --no-mtls        Do not apply default-deny Server CR (mTLS not enforced)
  --dry-run        Validate only; no state changes

Examples:
  forge-enroll-linkerd-ns.sh --namespace apps
  forge-enroll-linkerd-ns.sh --namespace monitoring --no-mtls
EOF
    exit 1
}

NAMESPACE="" INJECT_FLAG="" MTLS_FLAG="" DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --namespace)   NAMESPACE="$2"; shift 2 ;;
        --no-inject)   INJECT_FLAG="--no-inject"; shift ;;
        --no-mtls)     MTLS_FLAG="--no-enforce-mtls"; shift ;;
        --dry-run)     DRY_RUN=true; shift ;;
        -h|--help)     usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "${NAMESPACE}" ]] && usage

CMD=(python3 "${SCRIPT_DIR}/../proxmox-bootstrap/linkerd_manager.py"
     --state-dir "${BROODFORGE_STATE_DIR}" enroll
     --namespace "${NAMESPACE}")
[ -n "${INJECT_FLAG}" ] && CMD+=("${INJECT_FLAG}")
[ -n "${MTLS_FLAG}" ]   && CMD+=("${MTLS_FLAG}")
[[ "${DRY_RUN}" = "true" ]] && CMD+=(--dry-run)

echo "--> Enrolling namespace '${NAMESPACE}' into Linkerd mesh..."
"${CMD[@]}"
echo "--> Done. Existing pods need to be restarted to get sidecar injection."
