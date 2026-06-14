#!/usr/bin/env python3
"""
regenerate_docs.py — Rebuild all broodforge HTML documentation from source Markdown.

Reads proxmox-bootstrap/doc-manifest.json and regenerates every registered
HTML file using md_to_html.py. Run this any time md_to_html.py is updated
to propagate styling changes across all docs without drift.

Usage (from repo root):
    python3 proxmox-bootstrap/regenerate_docs.py            # regenerate all
    python3 proxmox-bootstrap/regenerate_docs.py --check    # report stale files only
    python3 proxmox-bootstrap/regenerate_docs.py --id phoenix  # single doc by id
    python3 proxmox-bootstrap/regenerate_docs.py --type runbook  # filter by type

Stdlib only — no pip dependencies.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.resolve()
MANIFEST_PATH = Path(__file__).parent / "doc-manifest.json"
GENERATOR = Path(__file__).parent / "md_to_html.py"


def load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def is_stale(source: Path, output: Path) -> bool:
    """Return True if output doesn't exist or is older than source or generator."""
    if not output.exists():
        return True
    out_mtime = output.stat().st_mtime
    if source.exists() and source.stat().st_mtime > out_mtime:
        return True
    if GENERATOR.exists() and GENERATOR.stat().st_mtime > out_mtime:
        return True
    return False


def regenerate(doc: dict, force: bool = False, check_only: bool = False) -> tuple[bool, str]:
    """
    Regenerate a single doc entry.
    Returns (success, message).
    """
    src = REPO_ROOT / doc["source"]
    out = REPO_ROOT / doc["output"]

    if not src.exists():
        return False, f"MISSING SOURCE: {doc['source']}"

    stale = force or is_stale(src, out)
    if not stale:
        return True, f"up-to-date"

    if check_only:
        return False, f"STALE"

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(GENERATOR),
        "--title", doc.get("title", ""),
        "--manifest", str(MANIFEST_PATH),
    ] + doc.get("flags", []) + [str(src), str(out)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, f"regenerated ({out.stat().st_size:,} bytes)"
    else:
        return False, f"FAILED: {result.stderr.strip()[:200]}"


def main():
    ap = argparse.ArgumentParser(
        description="Regenerate all broodforge HTML docs from their Markdown sources."
    )
    ap.add_argument(
        "--check", action="store_true",
        help="Report which docs are stale without regenerating."
    )
    ap.add_argument(
        "--force", action="store_true",
        help="Regenerate all docs even if they appear up-to-date."
    )
    ap.add_argument(
        "--id", metavar="ID",
        help="Regenerate a single doc by its manifest id."
    )
    ap.add_argument(
        "--type", metavar="TYPE",
        help="Regenerate only docs of a given type (runbook, guide, reference, index)."
    )
    args = ap.parse_args()

    manifest = load_manifest()
    docs = manifest["docs"]

    # Apply filters
    if args.id:
        docs = [d for d in docs if d["id"] == args.id]
        if not docs:
            print(f"ERROR: No doc with id '{args.id}' in manifest.", file=sys.stderr)
            sys.exit(1)
    if args.type:
        docs = [d for d in docs if d.get("type") == args.type]
        if not docs:
            print(f"ERROR: No docs of type '{args.type}' in manifest.", file=sys.stderr)
            sys.exit(1)

    width = max(len(d["id"]) for d in docs) if docs else 20
    ok = stale = missing = failed = 0

    print(f"Broodforge doc regeneration — {len(docs)} doc(s)")
    print(f"Generator: {GENERATOR.relative_to(REPO_ROOT)}")
    print(f"Mode: {'check-only' if args.check else 'force-all' if args.force else 'incremental'}")
    print()

    for doc in docs:
        success, msg = regenerate(doc, force=args.force, check_only=args.check)
        doc_id = doc["id"].ljust(width)
        if "MISSING" in msg:
            print(f"  ⚠  {doc_id}  {msg}")
            missing += 1
        elif "STALE" in msg:
            print(f"  ↺  {doc_id}  needs regeneration  ({doc['source']} → {doc['output']})")
            stale += 1
        elif "FAILED" in msg:
            print(f"  ✗  {doc_id}  {msg}")
            failed += 1
        elif msg == "up-to-date":
            print(f"  ✓  {doc_id}  up-to-date")
            ok += 1
        else:
            print(f"  ✓  {doc_id}  {msg}")
            ok += 1

    print()
    if args.check:
        if stale or missing:
            print(f"  {stale} stale, {missing} missing source, {ok} up-to-date")
            print(f"  Run without --check to regenerate.")
            sys.exit(1)
        else:
            print(f"  All {ok} docs up-to-date.")
    else:
        if failed or missing:
            print(f"  {ok} regenerated, {failed} failed, {missing} missing source")
            sys.exit(1)
        else:
            print(f"  {ok} docs regenerated successfully.")


if __name__ == "__main__":
    main()
