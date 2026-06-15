# About This Documentation

This page explains how broodforge's interactive HTML documentation system works.
All documentation in this project is authored in Markdown and generated into
self-contained HTML files using `proxmox-bootstrap/md_to_html.py`. No HTML is
hand-authored — the pipeline is always **Markdown source → md_to_html.py → HTML output**.

To regenerate all documentation after changes to the generator or source files, run:

```bash
python3 proxmox-bootstrap/regenerate_docs.py
```

---

## What is generated

Every HTML companion page is rendered from a Markdown source file registered in
`proxmox-bootstrap/doc-manifest.json`. The manifest records the source path,
output path, page title, and generation flags for each document. The generator
(`md_to_html.py`) is stdlib-only — no external dependencies required.

The generated HTML is self-contained: all CSS, JavaScript, and structure are
embedded in a single file. No external libraries or CDNs are required to view a doc.

---

## Layout

Every page shares a three-pane layout:

- **Left pane** — the document content, rendered from Markdown
- **Drag handle** — resizable divider between content and notes
- **Right pane** — Session Notes panel (see below)

The layout adapts: when undocked, the notes panel floats freely over the document.

---

## Session Notes panel

The notes panel persists free-form notes and structured section notes in your browser's
`localStorage`, keyed by document. Notes are not sent anywhere — they live in your browser.

The panel provides:

- **Quick notes** — a free-form textarea for anything that doesn't fit a structured field
- **Section notes** — per-section note trees that mirror the document structure
- **Export** — download notes as Markdown or HTML for record-keeping or sharing
- **Import** — load a previously exported Markdown notes file back into the panel
- **Pop-out / dock** — float the panel over the page or return it to the sidebar
- **Opacity control** — adjust floating panel transparency with − and + buttons (5% steps)

Notes for walkthrough documents are included in the encrypted export package (see below).

---

## Walkthrough fields

Documents marked as walkthroughs (runbooks and drills) contain structured input fields
that the operator fills in while executing the procedure. These are rendered from
special directives in the Markdown source.

### Field types

**`@field[Label]`** — single-line text input. Use for values you look up or compute
during the procedure, such as an IP address, a package filename, or a verification hash.

**`@field[Label|VAR=default]`** — parameter field that also registers a template variable.
The value the operator types is injected into every `{{VAR}}` placeholder in command blocks
throughout the document, updating them live.

**`@area[Label]`** — multi-line text area. Use for observations, paste output, or longer notes.

**`@credential[Label]`** — password-style input, stored in `sessionStorage` (cleared on tab
close). Use for secrets the operator needs during the procedure. Marked with a lock icon
and a reminder to save to KeePass.

**`@credential[Label|VAR]`** — credential field that also injects into `{{VAR}}` command
blocks. Lets live commands include the credential without it appearing in plain text.

**`@radio[Label|Option1|Option2|...]`** — single-choice selector. Records which option
the operator chose, with an optional per-option note field.

**`@check[Label|Item1|Item2|...]`** — checklist. Records which items were completed,
with optional per-item notes.

**`@table[Label|Col1|Col2|...](Row1,Row2,...)`** — pre-populated table with editable cells.
Use for timing records, wave summaries, or multi-row observations.

**`@parse[Label|regex|target-field]`** — a textarea where the operator pastes terminal
output. When the Extract button is clicked, the regex is applied and the captured group
is applied to the named target field.

**`@filename[Label|template]`** — suggested filename field. The template can include
`{{note:field-slug}}` references that are resolved from other filled fields, and `{{STAMP}}`
for the current timestamp.

**`@dir[Label]`** — working directory field. Filled value is used as a `cd` shorthand
for subsequent command blocks in the same section.

**`@select[Label|Option1|Option2|...]`** — dropdown selector. Use for fields with a
fixed set of valid values (e.g. timezone, disk type, replication mode). The selected
value is stored in session notes and persists across reloads.

### Input validation

Fields that expect network addresses or filesystem paths are validated as the operator
types. A yellow underline and inline hint appear if the value looks wrong; the hint
clears automatically when the value becomes valid.

Validation types applied automatically by field label:

- **IPv4** — fields whose label contains "IP address", "LAN IP", or "WAN IP"
- **Domain** — fields whose label contains "domain"
- **Path** — all `@dir` fields (must end with `/` so sub-paths compose correctly)

### Live commands (parameter injection)

Any code block in a document can contain `{{VAR}}` or `{{VAR=default}}` placeholders.
When the operator fills in a field linked to `VAR`, every command block that references
`{{VAR}}` updates immediately. The **Copy** button copies the resolved command — not the
template — so the operator never copies a placeholder by mistake.

The **Parameters** panel at the top of the page shows all declared variables in one place.
Editing a value there syncs to all corresponding field inputs and command blocks.

---

## Collapsible sections

All documentation pages have collapsible `##` sections. Each section has:

- A **▶ / ▼** toggle in the section heading to collapse or expand that section
- **Clear** — appears right-aligned in the section title row; clears all field inputs in that section only. This button is intentionally positioned away from the content to reduce accidental clicks.
- **Expand all / Collapse all** — at the top of the document, collapses or expands every section at once

Subsections (`###`, `####`) are also collapsible independently within their parent section.

---

## Export package

On walkthrough pages, the **⬇ Export** button generates an encrypted export package
containing all filled fields, session notes, and any attached files. The package is a
ZIP file encrypted with AES-256-GCM using a passphrase derived from PBKDF2-SHA256
(600,000 iterations). Credential fields (marked with 🔑) are included in the encrypted
package — this is intentional, as the package is meant to serve as a tamper-evident
audit record.

The passphrase is shown at export time. Store it in KeePass or another secure location —
there is no recovery mechanism if it is lost.

### Import session

A previously exported package can be imported back to restore all field values and notes.
The **↑ Import Session** button prompts for the export passphrase, decrypts, and restores.

---

## Inline editor

Every paragraph and heading in a document can be edited directly in the browser.
Hover over any paragraph to reveal the **✎** button. Clicking it opens an inline
textarea where the text can be revised.

Edits are saved to `localStorage` and persist across page reloads. An **(edited)**
marker appears next to modified blocks. The **↺ Reset** button inside the editor
restores the original generated text for that block.

The **⬇ Download with Edits** button (in the toolbar) downloads a copy of the page
with all inline edits baked into the HTML — useful for creating a customized version
without modifying the source Markdown.

---

## Attachments

On walkthrough pages, the **Attachments** panel appears at the top of the document
(above the main content). Drag files onto the panel or click **+ Add File** to attach
logs, screenshots, hardware profiles, or other files. Attached files are included in
the encrypted export package.

---

## Generating and updating documentation

All HTML documentation is generated from Markdown sources via `md_to_html.py`.
The document manifest (`proxmox-bootstrap/doc-manifest.json`) lists every registered
document with its source path, output path, title, and generation flags.

To regenerate everything after changes to the generator or styling:

```bash
python3 proxmox-bootstrap/regenerate_docs.py
```

To check which documents are stale without regenerating:

```bash
python3 proxmox-bootstrap/regenerate_docs.py --check
```

To regenerate a single document by its manifest ID:

```bash
python3 proxmox-bootstrap/regenerate_docs.py --id phoenix
```

New documents should be added to `doc-manifest.json` first, then their Markdown
source created, then regenerated. Hand-authored HTML is not permitted — all HTML
must be generated from a registered Markdown source.

---

## Light / dark theme

The **☀ Light** / **☾ Dark** toggle in the toolbar switches between colour themes.
The preference is saved in `localStorage` and applied on all subsequent page loads.

---

## Print

All pages have print-friendly CSS. The notes panel, toolbar, and interactive controls
are hidden when printing; only the document content is shown. Use your browser's
print function to produce a PDF of any page.
