#!/usr/bin/env python3
"""
assemble-spawn-package.py — CLI entry point for the spawn package assembler.

Usage:
    python3 assemble-spawn-package.py \\
        --plan spawn-plan.json \\
        --manifest spawn-manifest.json \\
        --artifacts /path/to/artifacts/ \\
        [--output-dir /opt/broodforge/spawn-packages] \\
        [--kdbx /path/to/cell.kdbx]

Produces:
    spawn-package-{cell_id}-{hostname}-{timestamp}.tar.gz
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from assemble_spawn_package import assemble_spawn_package


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble a spawn package for broodling provisioning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--plan", required=True,
        help="Path to spawn-plan.json",
    )
    parser.add_argument(
        "--manifest", required=True,
        help="Path to spawn-manifest.json",
    )
    parser.add_argument(
        "--artifacts", required=True,
        help="Directory containing generated artifacts (phase scripts, opentofu/, etc.)",
    )
    parser.add_argument(
        "--output-dir", default=".",
        help="Directory to write the package into (default: current directory)",
    )
    parser.add_argument(
        "--kdbx", default=None,
        help="Path to KeePass .kdbx to embed in the package (optional)",
    )
    args = parser.parse_args()

    plan_path = Path(args.plan)
    manifest_path = Path(args.manifest)
    artifacts_dir = Path(args.artifacts)

    for label, p in [("Plan", plan_path), ("Manifest", manifest_path), ("Artifacts", artifacts_dir)]:
        if not p.exists():
            print(f"[error] {label} not found: {p}", file=sys.stderr)
            sys.exit(1)

    with open(plan_path) as f:
        plan = json.load(f)
    with open(manifest_path) as f:
        manifest = json.load(f)

    kdbx_path = Path(args.kdbx) if args.kdbx else None
    if kdbx_path and not kdbx_path.exists():
        print(f"[error] KeePass database not found: {kdbx_path}", file=sys.stderr)
        sys.exit(1)

    pkg = assemble_spawn_package(
        plan=plan,
        manifest=manifest,
        artifacts_dir=artifacts_dir,
        output_dir=Path(args.output_dir),
        kdbx_path=kdbx_path,
    )

    cell_id  = plan.get("cell_id", "unknown")
    hostname = plan.get("hostname", "unknown")
    mode     = (plan.get("disposition") or {}).get("execution_mode", "unknown")

    print(f"\n{'=' * 64}")
    print(f"  Spawn Package Assembled")
    print(f"{'=' * 64}")
    print(f"  Package:  {pkg}")
    print(f"  Cell:     {cell_id}")
    print(f"  Broodling:{hostname}")
    print(f"  Mode:     {mode}")
    print(f"\n  Next steps:")
    print(f"    1. Copy {pkg.name} to {hostname}")
    print(f"    2. Extract: tar -xzf {pkg.name}")
    print(f"    3. Run:     bash spawn.sh")
    print()


if __name__ == "__main__":
    main()
