#!/usr/bin/env bash
# schedule-reconstruction-drill.sh — Install quarterly drill reminder timer
#
# Creates a systemd timer that logs a reminder every 90 days.
# The drill itself requires operator involvement — this script only provides
# the reminder, not automated execution.
#
# Usage: sudo bash proxmox-bootstrap/schedule-reconstruction-drill.sh

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/opt/broodforge}"

cat > /etc/systemd/system/broodforge-drill-reminder.service << EOF
[Unit]
Description=Broodforge Reconstruction Drill Reminder

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo "[broodforge] RECONSTRUCTION DRILL REMINDER: Run a reconstruction drill using docs/RECONSTRUCTION-DRILL.md. Run: python3 $REPO_ROOT/proxmox-bootstrap/reconstruction-drill.py --help"'
StandardOutput=journal
SyslogIdentifier=broodforge-drill
EOF

cat > /etc/systemd/system/broodforge-drill-reminder.timer << EOF
[Unit]
Description=Broodforge Quarterly Reconstruction Drill Reminder

[Timer]
OnBootSec=10min
OnUnitActiveSec=90d
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now broodforge-drill-reminder.timer

echo "[schedule] Drill reminder timer enabled: broodforge-drill-reminder.timer"
echo "[schedule] Reminder fires every 90 days."
echo "[schedule] Check: systemctl status broodforge-drill-reminder.timer"
echo "[schedule] Logs:  journalctl -u broodforge-drill-reminder.service"
echo ""
echo "[schedule] Drill guide: $REPO_ROOT/docs/RECONSTRUCTION-DRILL.md"
