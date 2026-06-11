#!/usr/bin/env bash
# forge-velero-backup.sh — Phase 2.H: Trigger or schedule Velero backups
# KeePass gate required for restore (destructive).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/forge-lib.sh"

BROODFORGE_STATE_DIR="${BROODFORGE_STATE_DIR:-/var/lib/broodforge}"
CMD_="$1"; shift || true

case "${CMD_:-}" in
    backup)
        NAME="${1:-backup-$(date -u +%Y%m%d-%H%M%S)}"; shift || true
        python3 "${SCRIPT_DIR}/../proxmox-bootstrap/velero_manager.py" \
            --state-dir "${BROODFORGE_STATE_DIR}" backup --name "${NAME}" "$@"
        ;;
    restore)
        forge_keepass_gate "Velero restore (destructive)"
        BACKUP_NAME="${1:?Usage: $0 restore <backup-name>}"; shift
        python3 "${SCRIPT_DIR}/../proxmox-bootstrap/velero_manager.py" \
            --state-dir "${BROODFORGE_STATE_DIR}" restore --backup "${BACKUP_NAME}" "$@"
        ;;
    list)
        python3 "${SCRIPT_DIR}/../proxmox-bootstrap/velero_manager.py" \
            --state-dir "${BROODFORGE_STATE_DIR}" list
        ;;
    sync)
        python3 "${SCRIPT_DIR}/../proxmox-bootstrap/velero_manager.py" \
            --state-dir "${BROODFORGE_STATE_DIR}" sync
        ;;
    *)
        echo "Usage: $0 {backup|restore|list|sync} [args...]" >&2; exit 1 ;;
esac
