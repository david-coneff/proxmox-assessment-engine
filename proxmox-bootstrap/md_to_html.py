#!/usr/bin/env python3
"""
md_to_html.py — Minimal, stdlib-only Markdown → HTML converter.

Renders a self-contained HTML document in the Broodforge dark theme (the same
palette as docs/ARCHITECTURE.html, the dashboard, and the setup guide). Used to
give every long-form Markdown doc (README, ROADMAP, RECONSTRUCTION-DRILL,
DESIGN-HISTORY, …) a browser-viewable, print-friendly HTML equivalent.

Supported Markdown:
  - ATX headings (# … ######)
  - Fenced code blocks (``` …), preserved verbatim (box-drawing diagrams included)
  - GitHub-style tables (| a | b | with a |---|---| separator row)
  - Unordered (-, *, +) and ordered (1.) lists, with one level of nesting
  - Blockquotes (>), horizontal rules (---), paragraphs
  - Inline: `code`, **bold**, and [text](url) links

Deliberately conservative: single-`*`/`_` italics are NOT interpreted, because
these technical docs are full of identifiers like __main__ and network_topology.ssl_*
that would otherwise be mangled.

Usage:
    python3 md_to_html.py INPUT.md OUTPUT.html [--title "Title"]

Stdlib only.
"""

import argparse
import html
import re
import sys
from pathlib import Path

_CSS = """
  :root{--bg:#1a1d23;--bg2:#22262e;--bg3:#2a2f3a;--border:#3a3f4d;--text:#cdd6f4;--muted:#7f8498;
    --accent:#89b4fa;--green:#a6e3a1;--yellow:#f9e2af;--orange:#fab387;--red:#f38ba8;
    --code-bg:#181b21;--radius:6px}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
    font-size:14px;line-height:1.6;padding:24px;max-width:1100px;margin:0 auto}
  h1{color:var(--accent);font-size:1.7em;margin:18px 0 4px}
  h2{color:var(--accent);font-size:1.05em;margin:24px 0 8px;text-transform:uppercase;letter-spacing:.05em;
    border-bottom:1px solid var(--border);padding-bottom:4px}
  h3{color:var(--accent);font-size:.95em;margin:14px 0 6px}
  h4{color:var(--muted);font-size:.82em;margin:10px 0 4px;text-transform:uppercase;letter-spacing:.08em}
  h5,h6{color:var(--muted);font-size:.8em;margin:8px 0 4px}
  a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
  p{margin:8px 0}ul,ol{margin:8px 0 8px 22px}li{margin:4px 0}
  li>ul,li>ol{margin:4px 0 4px 18px}
  strong{color:var(--text);font-weight:600}
  hr{border:none;border-top:1px solid var(--border);margin:20px 0}
  blockquote{border-left:3px solid var(--accent);background:#1e2d3a;margin:10px 0;
    padding:8px 14px;border-radius:0 var(--radius) var(--radius) 0;color:var(--text)}
  code{background:var(--code-bg);color:var(--green);padding:1px 5px;border-radius:3px;
    font-family:'Cascadia Code','Fira Code',Consolas,monospace;font-size:.9em}
  pre{background:var(--code-bg);border:1px solid var(--border);border-radius:var(--radius);
    padding:12px 14px;overflow-x:auto;margin:10px 0;font-family:'Cascadia Code','Fira Code',Consolas,monospace;
    font-size:.85em;color:var(--green);white-space:pre}
  pre code{background:none;padding:0;color:inherit}
  table{width:100%;border-collapse:collapse;margin:10px 0;font-size:.88em}
  th{background:var(--bg2);color:var(--muted);text-align:left;padding:6px 8px;
    border-bottom:1px solid var(--border);font-weight:600;font-size:.8em;text-transform:uppercase;letter-spacing:.05em}
  td{padding:5px 8px;border-bottom:1px solid var(--bg3);vertical-align:top}
  tr:last-child td{border-bottom:none}
  .doc-meta{color:var(--muted);font-size:.8em;margin:4px 0 20px}
  @media print{body{padding:12px;max-width:none}}
"""


def _inline(text: str) -> str:
    """Render inline Markdown on a line of already-plain text."""
    text = html.escape(text, quote=False)
    # Protect inline code spans from further processing.
    spans: list = []

    def _stash(m: "re.Match") -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _stash, text)
    # Links: [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    # Bold: **text**  (single * / _ intentionally left literal)
    text = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", text)
    # Restore code spans.
    text = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", text)
    return text


def _is_table_sep(line: str) -> bool:
    s = line.strip()
    if "|" not in s and "-" not in s:
        return False
    s = s.strip("|")
    cells = s.split("|")
    if not cells:
        return False
    for c in cells:
        c = c.strip()
        if not c or not re.fullmatch(r":?-+:?", c):
            return False
    return True


def _split_row(line: str) -> list:
    s = line.strip()
    s = re.sub(r"^\|", "", s)
    s = re.sub(r"\|$", "", s)
    return [c.strip() for c in s.split("|")]


def _render_blocks(md: str) -> str:
    lines = md.split("\n")
    out: list = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Blank
        if not stripped:
            i += 1
            continue

        # Fenced code block
        m = re.match(r"^(\s*)(`{3,}|~{3,})(.*)$", line)
        if m:
            fence = m.group(2)[0]
            buf: list = []
            i += 1
            while i < n and not re.match(rf"^\s*{fence}{{3,}}\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code = html.escape("\n".join(buf), quote=False)
            out.append(f"<pre><code>{code}</code></pre>")
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.fullmatch(r"(\s*[-*_]){3,}\s*", line) and set(stripped) <= {"-", "*", "_", " "}:
            out.append("<hr>")
            i += 1
            continue

        # Table: current line has a pipe and the next line is a separator row
        if "|" in line and i + 1 < n and _is_table_sep(lines[i + 1]):
            header = _split_row(line)
            i += 2  # skip header + separator
            body: list = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(_split_row(lines[i]))
                i += 1
            thead = "".join(f"<th>{_inline(c)}</th>" for c in header)
            rows_html = ""
            for row in body:
                # pad/truncate to header width
                cells = (row + [""] * len(header))[: len(header)]
                rows_html += "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>"
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{rows_html}</tbody></table>")
            continue

        # Blockquote
        if re.match(r"^\s*>\s?", line):
            buf = []
            while i < n and re.match(r"^\s*>\s?", lines[i]):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = " ".join(b.strip() for b in buf if b.strip())
            out.append(f"<blockquote>{_inline(inner)}</blockquote>")
            continue

        # Lists (unordered or ordered), with one level of nesting by indent
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            i = _render_list(lines, i, out)
            continue

        # Paragraph: accumulate consecutive non-blank, non-special lines
        buf = []
        while i < n and lines[i].strip() and not _starts_block(lines[i], lines, i):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")

    return "\n".join(out)


def _starts_block(line: str, lines: list, idx: int) -> bool:
    """True if line begins a non-paragraph block (so paragraph accumulation stops)."""
    if re.match(r"^(\s*)(`{3,}|~{3,})", line):
        return True
    if re.match(r"^#{1,6}\s+", line):
        return True
    if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
        return True
    if re.match(r"^\s*>\s?", line):
        return True
    if re.fullmatch(r"(\s*[-*_]){3,}\s*", line) and set(line.strip()) <= {"-", "*", "_", " "}:
        return True
    if "|" in line and idx + 1 < len(lines) and _is_table_sep(lines[idx + 1]):
        return True
    return False


def _render_list(lines: list, i: int, out: list) -> int:
    """Render a (possibly one-level-nested) list starting at lines[i]. Returns new i."""
    n = len(lines)
    base_indent = len(lines[i]) - len(lines[i].lstrip())
    ordered = bool(re.match(r"^\s*\d+\.\s+", lines[i]))
    tag = "ol" if ordered else "ul"
    out.append(f"<{tag}>")
    while i < n:
        line = lines[i]
        if not line.strip():
            # allow a single blank line within a list
            if i + 1 < n and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i + 1]):
                i += 1
                continue
            break
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if not m:
            break
        indent = len(m.group(1))
        if indent < base_indent:
            break
        if indent >= base_indent + 2 and out and not out[-1].endswith("</li>"):
            # nested list — recurse, attach inside the open <li>
            # close the current item text first by recursing for the nested block
            i = _render_list(lines, i, out)
            continue
        out.append(f"<li>{_inline(m.group(3))}</li>")
        i += 1
    out.append(f"</{tag}>")
    return i


def render_html(md: str, title: str, source_name: str = "") -> str:
    """Render a full standalone HTML document from Markdown text."""
    body = _render_blocks(md)
    meta = (f'<div class="doc-meta">Generated from <code>{html.escape(source_name)}</code> '
            f'— self-contained · print-friendly</div>') if source_name else ""
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        f"{meta}\n{body}\n"
        "</body>\n</html>\n"
    )


def convert_file(src: Path, dst: Path, title: str = "") -> None:
    md = src.read_text(encoding="utf-8-sig")
    if not title:
        m = re.search(r"^#\s+(.*)$", md, re.MULTILINE)
        title = m.group(1).strip() if m else src.stem
    dst.write_text(render_html(md, title, src.name), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert a Markdown file to themed HTML")
    ap.add_argument("input", help="Input .md file")
    ap.add_argument("output", help="Output .html file")
    ap.add_argument("--title", default="", help="Document title (default: first H1)")
    args = ap.parse_args()
    src = Path(args.input)
    if not src.exists():
        print(f"[md_to_html] not found: {src}", file=sys.stderr)
        sys.exit(2)
    convert_file(src, Path(args.output), args.title)
    print(f"[md_to_html] wrote {args.output}")


if __name__ == "__main__":
    main()
