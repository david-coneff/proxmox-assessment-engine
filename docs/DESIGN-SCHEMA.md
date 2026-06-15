# Broodforge UI Design Schema

This document records the qualitative design objectives and implementation conventions
for `proxmox-bootstrap/md_to_html.py` — the self-contained Markdown → HTML generator
used for all broodforge documentation.

It is the authoritative reference for anyone modifying the generator's CSS, HTML
structure, or JavaScript. All visual decisions should be traceable to a principle here.

---

## Design philosophy

Broodforge docs are **operator-facing tools, not marketing pages.** Every visual
decision serves legibility during an active procedure — often on a secondary monitor
while hands are on a server. The aesthetic follows from that function:

- High contrast dark theme by default; light theme available but secondary
- No animation except micro-transitions (collapse caret, button hover)
- Dense but not cramped — enough whitespace to parse structure quickly
- Controls stay out of the way until needed (hover reveals edit button; clear button
  is far from content to reduce accidental clicks)

---

## Colour system

All colours are CSS custom properties on `:root`, overridden by `body.light` for
the light theme. No hardcoded colours appear outside `_CSS`.

| Property | Dark value | Light value | Role |
|---|---|---|---|
| `--bg` | `#1a1d23` | `#ffffff` | Page and pane background |
| `--bg2` | `#22262e` | `#f4f5f7` | Cards, section headers, toolbar fill |
| `--bg3` | `#2a2f3a` | `#eceff2` | Nested cards, hover states |
| `--border` | `#3a3f4d` | `#6b7a8a` | Dividers, input outlines |
| `--text` | `#cdd6f4` | `#1f2328` | Body text and interactive labels |
| `--muted` | `#7f8498` | `#4a5568` | Secondary text, placeholders, labels |
| `--accent` | `#89b4fa` | `#1a6fc4` | Links, focus rings, active borders, TOC |
| `--green` | `#a6e3a1` | `#2d6a2d` | Success / checked state |
| `--yellow` | `#f9e2af` | `#7a5c00` | Warning (radio/check highlights) |
| `--orange` | `#fab387` | `#a04000` | Caution callouts |
| `--red` | `#f38ba8` | `#9b1c1c` | Error / danger |
| `--code-bg` | `#181b21` | `#f0f2f5` | Code block background |
| `--code-text` | `#a6e3a1` | `#1a3a1a` | Code block text |
| `--btn-bg` | `#2a2f3a` | `#e4e8ed` | Toolbar button and card background |
| `--radius` | `6px` | `6px` | Border radius for cards and inputs |

**Principle — no opacity for colour variation.** Muted/secondary colours are separate
named properties, not `rgba()` of the base colour. This keeps text crisp on all
backgrounds and avoids compounding opacity artefacts in nested contexts.

---

## Typography

- **Font stack**: `'Segoe UI', system-ui, -apple-system, sans-serif` (body);
  `'Consolas', 'Cascadia Code', 'SF Mono', 'Menlo', monospace` (code and counters)
- **Base size**: `14px`; line-height `1.65`
- **Headings**: `h1` 1.5em/600wt; `h2` 1.15em/600wt; `h3` 1.0em/600wt;
  `h4` 0.95em/500wt — sized to nest visually inside collapsible sections
- **Code**: inherits `--code-text` on `--code-bg`; `font-size: 0.875em`

---

## Layout

```
┌─────────────────────────────────────────────────────┐
│ #bf-app (flex row, full viewport height)            │
│  ┌──────────────────────────┐  │  ┌───────────────┐ │
│  │ #bf-doc-pane             │  │  │ #bf-notes-    │ │
│  │  ┌────────────────────┐  │  │  │ pane          │ │
│  │  │ #bf-toolbar        │  │ drag  │               │ │
│  │  │ (sticky top:0)     │  │  │  │               │ │
│  │  └────────────────────┘  │  │  │               │ │
│  │  #bf-doc-body            │  │  │               │ │
│  └──────────────────────────┘  │  └───────────────┘ │
└─────────────────────────────────────────────────────┘
```

- `#bf-app`: `display:flex; flex-direction:row; height:100vh`
- `#bf-doc-pane`: `flex:1; overflow-y:auto; min-width:0`
- `#bf-drag`: 6px wide drag handle; triggers JS pane resize
- `#bf-notes-pane`: fixed initial width `320px`; resizable; `scrollbar-gutter:stable`
  prevents layout shift when content changes scroll state

**Principle — no layout jump.** `scrollbar-gutter:stable` is applied to the notes pane
so the pane width is constant whether or not a scrollbar is visible. The doc pane avoids
fixed heights on content areas for the same reason.

---

## Toolbar

`#bf-toolbar` is `position:sticky; top:0; z-index:50` inside `#bf-doc-pane`. It uses
`flex-direction:column` with a single `.bf-toolbar-main` child row so future toolbar
rows (e.g. breadcrumbs) can be added without restructuring.

- **Border**: `border-bottom: 3px solid var(--accent)` — thick, bright line clearly
  demarcates the chrome from the document content
- **Top padding**: `.bf-toolbar-main { padding: 12px 0 6px }` — extra top clearance
  prevents the first row of buttons from feeling flush against the viewport edge
- **Button height**: all toolbar buttons and badges normalized to `height:28px`
  (explicit `height` + `display:inline-flex; align-items:center`)
- **Button colour**: `color:var(--text)` on both buttons and the section counter badge,
  so all chrome text reads at the same weight in dark mode

**Button order (left → right)**:
1. `⊟ Collapse all` / `⊞ Expand all` (only on collapsible pages)
2. Section counter badge `N / M`
3. `ⓘ About` link
4. `☀ Light` / `☾ Dark` theme toggle ← left of the right group
5. Right group: `⊘ Clear Fields` (walkthrough only), `⬇ Download with Edits`

---

## Collapsible sections

Each `##` heading becomes `<details class="section" open>` with a `<summary>` child.
Deeper headings (`###`, `####`) become `<details class="subsection">`.

- **Section header**: `background:var(--bg2)` bar; heading text inline in `<summary>`
- **Caret**: `▶/▼` in `--muted` at rest; transitions to `--accent` on hover
- **Expand/collapse sub-controls** (`⊟ ⊞`): appear inside the section header bar only
  for sections that have direct-child subsections; `border:1px solid transparent` at
  rest, `border-color:var(--accent)` on hover — border is invisible until hovered to
  reduce visual clutter

**Principle — controls visible on demand.** Expand/collapse buttons, inline edit
triggers (✎), and the section Clear button are all styled to be near-invisible at rest
and reveal on hover. This keeps the reading state clean without hiding functionality.

---

## Table of Contents

Auto-generated for collapsible pages with ≥ 3 `##`-level sections. Rendered as a
`<details id="bf-toc" open>` block at the top of `#bf-doc-body`, before all sections.

- Contains only `##` headings (one level deep)
- Each entry is `<a href="#hid">` where `hid` is the kebab-case slug of the heading text
- Click handler (JS): opens the target `<details.section>`, opens any ancestor
  `<details>`, then calls `scrollIntoView({behavior:'smooth', block:'start'})`

---

## Walkthrough fields

Rendered from `@`-prefixed directives. All inputs share `.note-input` and write to
`localStorage` on every `input` event, keyed `bf:{doc}:note:{slug}`.

| Directive | Element | Class |
|---|---|---|
| `@field` | `<input type="text">` | `note-input` |
| `@area` | `<textarea>` | `note-area` |
| `@credential` | `<input type="password">` | `note-input cred-input` |
| `@radio` | `<input type="radio">` group | — |
| `@check` | `<input type="checkbox">` group | — |
| `@select` | `<select>` | `note-input select-input` |
| `@dir` | `<input type="text">` | `note-input dir-input` |
| `@table` | `<table>` with `<input>` cells | `note-input` |
| `@parse` | `<textarea>` + Extract button | `note-area` |
| `@filename` | `<input type="text">` | `note-input filename-input` |

**Parameter fields** (`@field[Label|VAR=default]`, `@credential[Label|VAR]`) also
register in `tpl_vars` and appear in the Parameters panel. Their value is applied to
every `{{VAR}}` placeholder in code blocks via live DOM replacement. Parameter values
are stored under a separate key `bf:{doc}:param:{VAR}`.

**Dir ↔ param sync**: when a `@dir[Label]` field and a `{{VAR}}` placeholder share the
same slug, JS keeps them bidirectionally in sync — editing either updates the other.

**Input validation**: `.note-input` and `.param-input` elements receive `data-validate`
automatically based on label keywords (`ip address`/`lan ip`/`wan ip` → `ip4`;
`domain` → `domain`). All `@dir` fields get `data-validate="path"`. Validation fires on
`input` and `blur`; invalid values get `.val-warn` (yellow border) and a `.val-hint`
span below the field.

---

## Credential fields

`@credential` fields use `type="password"` and store in `sessionStorage` (not
`localStorage`) so secrets are cleared when the tab closes. A lock icon (🔑) and
reminder to save to KeePass appear below the field. Credential values are included in
the encrypted export package.

---

## Export package (walkthrough pages)

The `⬇ Export` button produces an AES-256-GCM encrypted ZIP containing:
- All filled field values (note and param keys)
- Session notes (quick notes + section note tree)
- Attached files

Passphrase is PBKDF2-SHA256 (600,000 iterations). No recovery if lost — users are
instructed to store it in KeePass.

---

## Session notes export HTML

The `⬇ HTML` export from the notes panel produces a self-contained file matching
broodforge dark-theme conventions:
- Sticky toolbar with expand/collapse all and `✎ Edit` / `⬇ Download edited` buttons
- Section bars (`--bg2` header, `--border` outline, `--radius` corners, caret toggle)
- Note text in `.note-text` divs; `contenteditable` toggled by Edit mode
- No external dependencies

---

## Inline editor

Any paragraph or heading in a generated doc can be edited inline. The `✎` button
appears on hover of an `.bf-editable-block` wrapper. Edits are saved per-block to
`localStorage` under `bf:{doc}:edit:{block-idx}`. The `⬇ Download with Edits` toolbar
button clones the live DOM, strips edit controls, and saves the result as HTML.

---

## Print

`@media print`: notes pane, toolbar, interactive controls, and edit buttons are hidden;
only `#bf-doc-body` content is printed. No special print CSS beyond display:none rules.

---

## Anti-patterns (what we explicitly avoid)

- **Hardcoded colours** in JS or HTML attributes — always use CSS custom properties
- **Opacity for dimming** — use `--muted` instead of `rgba(var(--text), 0.5)`
- **Fixed heights on content areas** — causes layout shift with dynamic content
- **External CDN dependencies** — the generator is stdlib-only; the HTML is self-contained
- **Hand-authored HTML** — all docs are generated from registered Markdown sources;
  `docs/*.html` files are never edited directly
- **git operations from the Linux sandbox** — always use the `bf-commit` PowerShell
  helper on Windows to avoid CIFS lock issues
