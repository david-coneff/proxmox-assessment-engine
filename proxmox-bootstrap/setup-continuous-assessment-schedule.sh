#!/usr/bin/env bash
# setup-continuous-assessment-schedule.sh — Install the broodforge continuous
# code health assessment systemd service + timer (runs every 6 hours).
#
# Usage:
#   sudo bash proxmox-bootstrap/setup-continuous-assessment-schedule.sh \
#     --manifest /opt/broodforge/proxmox-bootstrap/bootstrap-state.json \
#     --repo-root /opt/broodforge

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST=""
REPO_ROOT=""
PYTHON="${PYTHON:-python3}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --manifest)  MANIFEST="$2";  shift 2 ;;
        --repo-root) REPO_ROOT="$2"; shift 2 ;;
        --python)    PYTHON="$2";    shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

MANIFEST="${MANIFEST:-/opt/broodforge/proxmox-bootstrap/bootstrap-state.json}"
REPO_ROOT="${REPO_ROOT:-/opt/broodforge}"

echo "[setup] Creating broodforge-continuous-assessment systemd service + timer"
echo "[setup] Manifest:  ${MANIFEST}"
echo "[setup] Repo root: ${REPO_ROOT}"

cat > /etc/systemd/system/broodforge-continuous-assessment.service << EOF
[Unit]
Description=Broodforge Continuous Code Health Assessment
After=network-online.target

[Service]
Type=oneshot
ExecStart=${PYTHON} ${SCRIPT_DIR}/continuous_assessment.py --manifest ${MANIFEST} --repo-root ${REPO_ROOT}
StandardOutput=journal
StandardError=journal
SyslogIdentifier=broodforge-continuous-assessment
EOF

cat > /etc/systemd/system/broodforge-continuous-assessment.timer << EOF
[Unit]
Description=Broodforge Continuous Code Health Assessment (every 6 hours)

[Timer]
OnBootSec=10min
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now broodforge-continuous-assessment.timer

echo "[setup] Timer enabled: broodforge-continuous-assessment.timer"
echo "[setup] Check status:  systemctl status broodforge-continuous-assessment.timer"
echo "[setup] Force run:     systemctl start broodforge-continuous-assessment.service"
echo "[setup] View logs:     journalctl -u broodforge-continuous-assessment.service -n 20"
