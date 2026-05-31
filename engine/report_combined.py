"""
Combined node + guest assessment report.

Merges the node assessment report (engine/report.py) and the guest
assessment report (engine/report_guest.py) into a single Markdown document.

All content is factual.  No recommendations are generated.
"""

from __future__ import annotations

from engine.report import generate_report
from engine.report_guest import generate_guest_report


def generate_combined_report(assessment: dict) -> str:
    """
    Produce a single Markdown document combining the node and guest reports.

    The node sections come first, then the guest sections.  A horizontal
    rule separates the two halves.
    """
    node_report = generate_report(assessment, fmt="markdown")
    guest_report = generate_guest_report(assessment)

    # Replace the node report's H1 heading to make it clear this is combined
    node_report = node_report.replace(
        "# Node Assessment Report",
        "# Infrastructure Assessment Report",
        1,
    )

    # Replace the guest report's H1 heading so both halves use H2 feel
    # (keep the heading but mark it as the guest section)
    guest_report = guest_report.replace(
        "# Guest Assessment Report",
        "---\n\n# Guest Assessment",
        1,
    )

    return node_report + "\n\n" + guest_report
