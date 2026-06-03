# Deprecated ODS Workbook Generators

These files generated ODS (LibreOffice Calc) workbooks embedded in packages.
They are **not used** by the active codebase — all packages now embed HTML workbooks.

| Deprecated | Replacement |
|---|---|
| `spawn_workbook.py` (ODS) | `html_spawn_workbook.py` |
| `forge_workbook.py` (ODS) | `html_forge_workbook.py` |

The assemblers (`assemble_spawn_package.py`, `assemble_forge_package.py`) import
from the HTML equivalents. These ODS files are preserved for reference only.

Deprecated: 2026-06-03
