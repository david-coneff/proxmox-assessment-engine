path = r'proxmox-bootstrap\md_to_html.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix: add-button is a direct child of .nts-body, NOT inside .nts-ch
# Fix it in CSS, applyOpacity forEach, and setFloat cleanup

fixes = [
    ("  .nts-section.nts-dim>.nts-body>.nts-ch>.nts-add-btn{opacity:0!important;pointer-events:none}",
     "  .nts-section.nts-dim>.nts-body>.nts-add-btn{opacity:0!important;pointer-events:none}"),
    ("s.querySelectorAll(':scope>.nts-body>.nts-ch>.nts-add-btn').forEach(function(b){b.style.opacity=hideOwn?'0':'';b.style.pointerEvents=hideOwn?'none':'';});",
     "s.querySelectorAll(':scope>.nts-body>.nts-add-btn').forEach(function(b){b.style.opacity=hideOwn?'0':'';b.style.pointerEvents=hideOwn?'none':'';});"),
    ("s.querySelectorAll(':scope>.nts-body>.nts-ch>.nts-add-btn').forEach(function(b){b.style.opacity='';b.style.pointerEvents='';});",
     "s.querySelectorAll(':scope>.nts-body>.nts-add-btn').forEach(function(b){b.style.opacity='';b.style.pointerEvents='';});"),
]

for old, new in fixes:
    c = text.count(old)
    assert c == 1, f"count={c} for: {old[:60]}"
    text = text.replace(old, new)
    print(f"OK: {old[:60]}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Done.")
