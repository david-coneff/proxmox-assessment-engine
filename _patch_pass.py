path = r'proxmox-bootstrap\md_to_html.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. CSS: add nts-pass rules (ancestor sections — transparent container, own content hidden)
old1 = "  .nts-section:not(.nts-dim){visibility:visible}"
new1 = (
    "  .nts-section:not(.nts-dim){visibility:visible}\n"
    "  /* pass-through: ancestor of active section — hide own content, show children */\n"
    "  .nts-section.nts-pass{border-color:transparent!important}\n"
    "  .nts-section.nts-pass>summary.nts-hdr{opacity:0!important;pointer-events:none}\n"
    "  .nts-section.nts-pass>.nts-body>textarea.note-area{opacity:0!important;border-color:transparent!important;background:transparent!important}\n"
    "  .nts-section.nts-pass>.nts-body{background:transparent!important}\n"
    "  .nts-section.nts-pass>.nts-body>.nts-ch>button{opacity:0!important;pointer-events:none}"
)
c1 = text.count(old1); assert c1==1, f"CSS pass:{c1}"; text = text.replace(old1, new1); print("CSS pass OK")

# 2. JS applyOpacity forEach — replace dim logic with actSec guard + pass support
old2 = (
    "            var dim=(s!==activeNoteContainer)&&!activeNoteContainer.contains(s)&&!s.contains(activeNoteContainer);\n"
    "            s.classList.toggle('nts-dim',dim);\n"
    "            s.style.background=dim?'transparent':'';\n"
    "            s.style.borderColor=dim?'transparent':'';\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity=dim?fOp:'';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity=dim?fOp:'';ta.style.borderColor=dim?'transparent':'';ta.style.background=dim?'transparent':'';}  "
)
old2 = old2.rstrip()
new2 = (
    "            var actSec=activeNoteContainer&&activeNoteContainer.classList&&activeNoteContainer.classList.contains('nts-section');\n"
    "            var isActive=actSec&&(s===activeNoteContainer);\n"
    "            var isAnc=actSec&&(s!==activeNoteContainer)&&s.contains(activeNoteContainer);\n"
    "            var dim=actSec&&!isActive&&!isAnc;\n"
    "            var pass=actSec&&isAnc;\n"
    "            var hide=dim||pass;\n"
    "            s.classList.toggle('nts-dim',dim);\n"
    "            s.classList.toggle('nts-pass',pass);\n"
    "            s.style.background=hide?'transparent':'';\n"
    "            s.style.borderColor=hide?'transparent':'';\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity=hide?'0':'';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity=hide?'0':'';ta.style.borderColor=hide?'transparent':'';ta.style.background=hide?'transparent':'';}  "
)
new2 = new2.rstrip()
c2 = text.count(old2); assert c2==1, f"JS forEach:{c2}"; text = text.replace(old2, new2); print("JS forEach OK")

# 3. setFloat cleanup — also remove nts-pass
old3 = "            s.classList.remove('nts-dim');\n            s.style.background=''; s.style.borderColor='';"
new3 = "            s.classList.remove('nts-dim');\n            s.classList.remove('nts-pass');\n            s.style.background=''; s.style.borderColor='';"
c3 = text.count(old3); assert c3==1, f"cleanup:{c3}"; text = text.replace(old3, new3); print("cleanup OK")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Done.")
