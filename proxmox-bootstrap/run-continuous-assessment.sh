#!/usr/bin/env bash
# run-continuous-assessment.sh — Run continuous code health assessment
# and submit findings to the remediation queue.
#
# Usage:
#   bash proxmox-bootstrap/run-continuous-assessment.sh \
#     [--manifest /path/to/bootstrap-state.json] \
#     [--repo-root /path/to/broodforge]
#
# Add to cron (every 6 hours):
#   0 */6 * * * /opt/broodforge/proxmox-bootstrap/run-continuous-assessment.sh \
#       --manifest /opt/broodforge/proxmox-bootstrap/bootstrap-state.json \
#       --repo-root /opt/broodforge
#
# Or use setup-continuous-assessment-schedule.sh to install as a systemd timer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${MANIFEST:-${SCRIPT_DIR}/bootstrap-state.json}"
REPO_ROOT="${REPO_ROOT:-$(dirname "${SCRIPT_DIR}")}"
PYTHON="${PYTHON:-python3}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --manifest)  MANIFEST="$2";  shift 2 ;;
        --repo-root) REPO_ROOT="$2"; shift 2 ;;
        --python)    PYTHON="$2";    shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

echo "[run-continuous-assessment] $(date -u +%Y-%m-%dT%H:%M:%SZ) manifest=${MANIFEST} repo-root=${REPO_ROOT}"

"${PYTHON}" "${SCRIPT_DIR}/continuous_assessment.py" \
    --manifest "${MANIFEST}" \
    --repo-root "${REPO_ROOT}"
