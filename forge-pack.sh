#!/usr/bin/env bash
# forge-pack.sh — Assemble a forge package from the current repo state (Phase 1.F.1).
#
# Runs on the operator's workstation (not on the target hardware).
# Produces forge-package-{cell_id}-{timestamp}.tar.gz in ./dist/
#
# Usage:
#   bash forge-pack.sh                          # Interactive (asks for manifest)
#   bash forge-pack.sh --manifest forge-manifest.json
#   bash forge-pack.sh --manifest forge-manifest.json --embed-kdbx /path/to.kdbx
#   bash forge-pack.sh --manifest forge-manifest.json --output ./dist
#
# Prerequisites:
#   Python 3.11+, on PATH
#   forge-manifest.json (generate with: python3 proxmox-bootstrap/forge-planner.py)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/dist}"
MANIFEST=""
KDBX_PATH=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)   MANIFEST="$2";  shift 2 ;;
    --embed-kdbx) KDBX_PATH="$2"; shift 2 ;;
    --output)     OUTPUT_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: bash forge-pack.sh [--manifest PATH] [--embed-kdbx PATH] [--output DIR]"
      exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# If no manifest provided, check default location
if [ -z "$MANIFEST" ]; then
  if [ -f "$SCRIPT_DIR/forge-manifest.json" ]; then
    MANIFEST="$SCRIPT_DIR/forge-manifest.json"
    echo "[forge-pack] Using forge-manifest.json in current directory."
  else
    echo "[forge-pack] No forge-manifest.json found."
    echo "[forge-pack] Generate one first: python3 proxmox-bootstrap/forge-planner.py"
    exit 1
  fi
fi

# Validate manifest exists
if [ ! -f "$MANIFEST" ]; then
  echo "[forge-pack] Manifest not found: $MANIFEST" >&2
  exit 1
fi

echo "[forge-pack] Assembling forge package..."
echo "[forge-pack]   Manifest: $MANIFEST"
echo "[forge-pack]   Output:   $OUTPUT_DIR"
[ -n "$KDBX_PATH" ] && echo "[forge-pack]   KeePass:  $KDBX_PATH (will be embedded)"

mkdir -p "$OUTPUT_DIR"

"$PYTHON" - <<PYEOF
import sys, json
sys.path.insert(0, "$SCRIPT_DIR/proxmox-bootstrap")
from pathlib import Path
from assemble_forge_package import assemble_forge_package

manifest = json.load(open("$MANIFEST"))
kdbx = "$KDBX_PATH" or None
pkg = assemble_forge_package(
    manifest=manifest,
    output_dir=Path("$OUTPUT_DIR"),
    repo_dir=Path("$SCRIPT_DIR"),
    kdbx_path=Path(kdbx) if kdbx else None,
)
print(f"[forge-pack] Package: {pkg}")
print(f"[forge-pack] Size:    {pkg.stat().st_size // 1024} KiB")
PYEOF

echo "[forge-pack] Done."
echo "[forge-pack] Copy the .tar.gz to the target host and run: tar xzf <package> && bash forge.sh"
