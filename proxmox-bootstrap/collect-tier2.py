#!/usr/bin/env python3
"""
collect-tier2.py — Tier 2 Bootstrap State Collector (entry point)

This file is the runnable entry point. All logic lives in collect_tier2.py
(importable module) so that tests can import individual functions without
executing the CLI.

Usage:
    python3 proxmox-bootstrap/collect-tier2.py --host <proxmox-ip> [options]
    python3 proxmox-bootstrap/collect-tier2.py --help
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect_tier2 import main

if __name__ == "__main__":
    main()
