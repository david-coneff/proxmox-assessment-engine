"""
Fix applyOpacity: fOp was derived from fieldOpacity() which returns ~1.0
when panel is at full opacity, so dim never visually dimmed anything.
Use a fixed 0.35 value (matching the CSS) instead.
"""
from pathlib import Path

p = Path("proxmox-bootstrap/md_to_html.py")
content = p.read_text(encoding="utf-8")

OLD = "          var fOp=fieldOpacity();\n          var qn=document.getElementById('bf-session-notes');\n          /* quick-notes textarea: direct opacity fine (leaf element, no children) */\n          if(qn) qn.style.opacity=(qn===activeNoteContainer)?'1':fOp;"

NEW = "          var fOp='0.35';\n          var qn=document.getElementById('bf-session-notes');\n          /* quick-notes textarea: direct opacity fine (leaf element, no children) */\n          if(qn) qn.style.opacity=(qn===activeNoteContainer)?'':fOp;"

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    p.write_text(content, encoding="utf-8")
    print(f"Patched md_to_html.py ({p.stat().st_size:,} bytes)")
else:
    # Try to show what's actually there
    idx = content.find('var fOp=fieldOpacity')
    if idx >= 0:
        print("Pattern not exact — found at char", idx)
        print(repr(content[idx-50:idx+200]))
    else:
        print("ERROR: fOp=fieldOpacity not found at all")
