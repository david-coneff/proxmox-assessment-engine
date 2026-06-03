# Deprecated ODT/ODS Renderers

These files are preserved for reference but are **not used by the active codebase**.

The documentation engine generates HTML output only. HTML equivalents exist for
all deprecated renderers:

| Deprecated | Replacement |
|---|---|
| `recovery_runbook.py` (ODT) | `html_recovery_runbook.py` |
| `runbook.py` (ODT base) | `html_base.py` |
| `operational_report.py` (ODT) | `html_operational_report.py` |
| `workbook.py` (ODS) | `html_bootstrap.py` |

`engine.py` generates only HTML. Do not import from this directory in new code.

Deprecated: 2026-06-02
