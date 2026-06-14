"""
Fix dim visibility: opacity 0.35 on dark textarea against dark panel = imperceptible.
Also change background color so there's actual visible contrast.
"""
from pathlib import Path

p = Path("proxmox-bootstrap/md_to_html.py")
content = p.read_text(encoding="utf-8")

OLD1 = "ta.style.borderColor=dim?'transparent':'';}\n          });"
NEW1 = "ta.style.borderColor=dim?'transparent':'';ta.style.background=dim?'var(--bg3)':'';})\n          ."
# That's messy - let me be more precise

OLD1 = "im?fOp:'';ta.style.borderColor=dim?'transparent':'';})"
NEW1 = "im?fOp:'';ta.style.borderColor=dim?'transparent':'';ta.style.background=dim?'var(--bg3)':'';}"

OLD2 = "pacity='';ta.style.borderColor='';}"
NEW2 = "pacity='';ta.style.borderColor='';ta.style.background='';}"

errors = []
for old, new, label in [(OLD1, NEW1, 'applyOpacity'), (OLD2, NEW2, 'setFloat cleanup')]:
    if old in content:
        content = content.replace(old, new, 1)
        print(f"✓ patched {label}")
    else:
        errors.append(label)
        print(f"✗ not found: {label}")

if errors:
    print("ERROR patterns not found:", errors)
else:
    p.write_text(content, encoding="utf-8")
    print(f"Wrote {p} ({p.stat().st_size:,} bytes)")
    # Verify
    c2 = p.read_text(encoding='utf-8')
    print("bg3 present:", "bg3" in c2)
