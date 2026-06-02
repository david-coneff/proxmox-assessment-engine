#!/usr/bin/env bash
# build-talos-template.sh — Download Talos ISO and create Proxmox template VMID 9001
#
# Usage:
#   ./build-talos-template.sh [--storage STORAGE] [--version VERSION] [--vmid VMID] [--dry-run]
#
# Defaults:
#   STORAGE  = local
#   VERSION  = latest stable from GitHub releases API
#   VMID     = 9001
#
# After the script completes, bootstrap-state.json should be updated with the
# talos-1x-base entry (see 9.T.4 — done by generate-talos-config.py or manually).

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
STORAGE="${STORAGE:-local}"
VMID="${VMID:-9001}"
TEMPLATE_NAME="talos-1x-base"
DRY_RUN=false

# ── Argument parsing ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --storage) STORAGE="$2"; shift 2 ;;
        --version) TALOS_VERSION="$2"; shift 2 ;;
        --vmid)    VMID="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--storage STORAGE] [--version VERSION] [--vmid VMID] [--dry-run]"
            exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Resolve Talos version ──────────────────────────────────────────────────────
if [[ -z "${TALOS_VERSION:-}" ]]; then
    echo "[talos-template] Fetching latest Talos version from GitHub..."
    TALOS_VERSION=$(curl -fsSL \
        "https://api.github.com/repos/siderolabs/talos/releases/latest" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")
fi
echo "[talos-template] Talos version: ${TALOS_VERSION}"

ISO_NAME="talos-${TALOS_VERSION}-nocloud-amd64.iso"
ISO_URL="https://factory.talos.dev/image/376567988ad370138ad8b2698212367b8edcb69b5fd68c80be1f2ec7d603b4b/${TALOS_VERSION}/nocloud-amd64.iso"
ISO_DIR="/var/lib/vz/template/iso"
ISO_PATH="${ISO_DIR}/${ISO_NAME}"
STORAGE_PATH="${STORAGE}:iso/${ISO_NAME}"

# ── Preflight checks ───────────────────────────────────────────────────────────
if [[ "${DRY_RUN}" == "false" ]]; then
    if ! command -v qm &>/dev/null; then
        echo "[talos-template] ERROR: qm not found — this script must run on a Proxmox host"
        exit 1
    fi
    if qm status "${VMID}" &>/dev/null; then
        echo "[talos-template] ERROR: VMID ${VMID} already exists"
        echo "[talos-template]   If you want to rebuild, run: qm destroy ${VMID}"
        exit 1
    fi
fi

echo ""
echo "[talos-template] Plan:"
echo "  ISO:      ${ISO_NAME}"
echo "  ISO URL:  ${ISO_URL}"
echo "  Storage:  ${STORAGE}"
echo "  VMID:     ${VMID}"
echo "  Template: ${TEMPLATE_NAME}"
echo ""

if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[talos-template] DRY RUN — no changes made"
    exit 0
fi

# ── Download ISO ───────────────────────────────────────────────────────────────
if [[ -f "${ISO_PATH}" ]]; then
    echo "[talos-template] ISO already present: ${ISO_PATH}"
else
    echo "[talos-template] Downloading Talos ISO..."
    mkdir -p "${ISO_DIR}"
    wget --progress=bar:force -O "${ISO_PATH}.tmp" "${ISO_URL}"
    mv "${ISO_PATH}.tmp" "${ISO_PATH}"
    echo "[talos-template] Download complete: ${ISO_PATH}"
fi

# ── Verify ISO checksum (best-effort) ─────────────────────────────────────────
# Talos publishes SHA256SUMS alongside each release; fetch and verify.
SHA256SUMS_URL="https://github.com/siderolabs/talos/releases/download/${TALOS_VERSION}/sha256sum.txt"
EXPECTED_SHA=""
if EXPECTED_SHA=$(curl -fsSL "${SHA256SUMS_URL}" 2>/dev/null | grep "nocloud-amd64.iso" | awk '{print $1}'); then
    ACTUAL_SHA=$(sha256sum "${ISO_PATH}" | awk '{print $1}')
    if [[ "${ACTUAL_SHA}" == "${EXPECTED_SHA}" ]]; then
        echo "[talos-template] ISO checksum verified: ${ACTUAL_SHA}"
    else
        echo "[talos-template] WARNING: ISO checksum mismatch!"
        echo "[talos-template]   Expected: ${EXPECTED_SHA}"
        echo "[talos-template]   Actual:   ${ACTUAL_SHA}"
        echo "[talos-template]   Delete ${ISO_PATH} and re-run to re-download"
        exit 1
    fi
else
    echo "[talos-template] NOTE: Could not fetch SHA256SUMS — skipping checksum verification"
fi

# ── Create Proxmox VM ──────────────────────────────────────────────────────────
echo "[talos-template] Creating VM ${VMID} (${TEMPLATE_NAME})..."

# Talos does not use BIOS/UEFI boot from ISO in the traditional sense;
# it boots a raw kernel from the ISO. UEFI mode is recommended.
qm create "${VMID}" \
    --name "${TEMPLATE_NAME}" \
    --memory 2048 \
    --cores 2 \
    --net0 "virtio,bridge=vmbr0" \
    --ide2 "${STORAGE_PATH},media=cdrom" \
    --boot "order=ide2" \
    --ostype "l26" \
    --bios "ovmf" \
    --machine "q35" \
    --efidisk0 "${STORAGE}:0,efitype=4m,pre-enrolled-keys=0" \
    --scsihw "virtio-scsi-pci" \
    --scsi0 "${STORAGE}:4" \
    --serial0 "socket" \
    --vga "serial0"

echo "[talos-template] VM ${VMID} created"

# ── Boot and apply minimal machine config ─────────────────────────────────────
# Talos boots into maintenance mode when no machine config is applied.
# We apply a minimal installer config, let it install to disk, then halt.

echo ""
echo "[talos-template] *** MANUAL STEP REQUIRED ***"
echo ""
echo "  The Talos VM (VMID ${VMID}) has been created and will boot from the ISO"
echo "  into maintenance mode. To complete the template:"
echo ""
echo "  1. Start the VM:   qm start ${VMID}"
echo "  2. Wait for boot (~30s), then apply installer config:"
echo ""
echo "     talosctl apply-config --insecure --nodes <VM_IP> \\"
echo "       --file talos-configs/installer-template.yaml"
echo ""
echo "     (Generate installer-template.yaml with generate-talos-config.py first.)"
echo ""
echo "  3. Wait for Talos to install (~2 min) and halt the VM."
echo "  4. Detach the ISO:   qm set ${VMID} --ide2 none"
echo "  5. Convert to template:"
echo "     qm template ${VMID}"
echo ""
echo "  After these steps, verify: qm config ${VMID} | grep 'template: 1'"
echo ""
echo "[talos-template] ISO and VM ready. Follow the steps above to complete the template."

echo ""
echo "[talos-template] Suggested talos-1x-base entry for bootstrap-state.json templates[]:"
echo "  {"
echo "    \"name\": \"talos-1x-base\","
echo "    \"base_image\": \"talos-1x-base-iso\","
echo "    \"proxmox_template_id\": ${VMID},"
echo "    \"os_variant\": \"talos\","
echo "    \"created_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
echo "    \"additional_packages\": [],"
echo "    \"build_notes\": \"Talos Linux ${TALOS_VERSION} — no cloud-init, no SSH, talosctl only\""
echo "  }"
echo ""
echo "[talos-template] Suggested talos-1x-base-iso entry for bootstrap-state.json base_images[]:"
echo "  {"
echo "    \"name\": \"talos-1x-base-iso\","
echo "    \"source_iso\": \"${ISO_NAME}\","
echo "    \"source_url\": \"${ISO_URL}\","
echo "    \"checksum\": \"sha256:${ACTUAL_SHA:-POPULATE}\","
echo "    \"created_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
echo "    \"notes\": \"Talos Linux ${TALOS_VERSION} nocloud amd64\""
echo "  }"
