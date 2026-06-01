#!/usr/bin/env bash
# setup-operational-schedule.sh — Install broodforge operational report scheduler
#
# Creates a systemd service + timer that regenerates the Operational Status Report
# every hour using the latest assessment manifest.
#
# Usage:
#   sudo bash proxmox-bootstrap/setup-operational-schedule.sh \
#     --manifest /opt/broodforge/proxmox-bootstrap/bootstrap-state.json \
#     --engine   /opt/broodforge/doc-gen/engine.py

set -euo pipefail

MANIFEST=""
ENGINE=""
PYTHON="${PYTHON:-python3}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --manifest) MANIFEST="$2"; shift 2 ;;
        --engine)   ENGINE="$2";   shift 2 ;;
        --python)   PYTHON="$2";   shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

MANIFEST="${MANIFEST:-/opt/broodforge/proxmox-bootstrap/bootstrap-state.json}"
ENGINE="${ENGINE:-/opt/broodforge/doc-gen/engine.py}"

echo "[setup] Creating broodforge-operational systemd service + timer"
echo "[setup] Manifest: $MANIFEST"
echo "[setup] Engine:   $ENGINE"

cat > /etc/systemd/system/broodforge-operational.service << EOF
[Unit]
Description=Broodforge Operational Report Generation
After=network-online.target

[Service]
Type=oneshot
ExecStart=$PYTHON $ENGINE --mode operational --manifest $MANIFEST
StandardOutput=journal
StandardError=journal
SyslogIdentifier=broodforge-operational
EOF

cat > /etc/systemd/system/broodforge-operational.timer << EOF
[Unit]
Description=Broodforge Operational Report (hourly)

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now broodforge-operational.timer

echo "[setup] Timer enabled: broodforge-operational.timer"
echo "[setup] Check status:  systemctl status broodforge-operational.timer"
echo "[setup] Force run:     systemctl start broodforge-operational.service"
echo "[setup] View logs:     journalctl -u broodforge-operational.service -n 20"
