path = r'proxmox-bootstrap\md_to_html.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. CSS: fix add-btn selector — button is child of .nts-body directly, not .nts-ch
old1 = "  .nts-section.nts-dim>.nts-body>.nts-ch>.nts-add-btn{opacity:0!important;pointer-events:none}"
new1 = "  .nts-section.nts-dim>.nts-body>.nts-add-btn{opacity:0!important;pointer-events:none}"
c1 = text.count(old1); assert c1==1, f"CSS:{c1}"; text = text.replace(old1, new1); print("CSS OK")

# 2. JS forEach: replace dim logic with flat per-element inline style approach.
#    Key rules:
#      - actSec guard: if activeNoteContainer is not an .nts-section (e.g. quick notes), show everything
#      - hideOwn = true for ALL non-active sections (including ancestors) — each element styled independently
#      - add-buttons targeted directly, not via CSS cascade
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
    "            var isAnc=actSec&&!isActive&&s.contains(activeNoteContainer);\n"
    "            var hideOwn=actSec&&!isActive;\n"
    "            s.classList.toggle('nts-dim',actSec&&!isActive&&!isAnc);\n"
    "            s.style.background=hideOwn?'transparent':'';\n"
    "            s.style.borderColor=hideOwn?'transparent':'';\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity=hideOwn?'0':'';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity=hideOwn?'0':'';ta.style.borderColor=hideOwn?'transparent':'';ta.style.background=hideOwn?'transparent':'';}  \n"
    "            s.querySelectorAll(':scope>.nts-body>.nts-add-btn').forEach(function(b){b.style.opacity=hideOwn?'0':'';b.style.pointerEvents=hideOwn?'none':'';});  "
)
new2 = new2.rstrip()
c2 = text.count(old2); assert c2==1, f"forEach:{c2}"; text = text.replace(old2, new2); print("forEach OK")

# 3. setFloat cleanup: also clear add-button inline styles
old3 = (
    "            if(ta){ta.style.opacity='';ta.style.borderColor='';ta.style.background='';}\n"
    "          });"
)
# Find the cleanup forEach specifically (not the applyOpacity one) by using more context
old3_full = (
    "            s.classList.remove('nts-dim');\n"
    "            s.style.background=''; s.style.borderColor='';\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity='';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity='';ta.style.borderColor='';ta.style.background='';}\n"
    "          });"
)
new3_full = (
    "            s.classList.remove('nts-dim');\n"
    "            s.style.background=''; s.style.borderColor='';\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity='';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity='';ta.style.borderColor='';ta.style.background='';}\n"
    "            s.querySelectorAll(':scope>.nts-body>.nts-add-btn').forEach(function(b){b.style.opacity='';b.style.pointerEvents='';});\n"
    "          });"
)
c3 = text.count(old3_full); assert c3==1, f"cleanup:{c3}"; text = text.replace(old3_full, new3_full); print("cleanup OK")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Done.")
