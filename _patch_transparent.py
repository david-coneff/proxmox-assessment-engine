path = r'proxmox-bootstrap\md_to_html.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. CSS dim rules
old1 = (
    "  .nts-section.nts-dim>summary.nts-hdr{opacity:0.12}\n"
    "  .nts-section.nts-dim>.nts-body>textarea.note-area{opacity:0.12!important;border-color:transparent!important}\n"
    "  .nts-section.nts-dim>.nts-body>textarea.note-area::placeholder{opacity:0.08!important}"
)
new1 = (
    "  .nts-section.nts-dim{border-color:transparent!important}\n"
    "  .nts-section.nts-dim>summary.nts-hdr{opacity:0!important;pointer-events:none}\n"
    "  .nts-section.nts-dim>.nts-body>textarea.note-area{opacity:0!important;border-color:transparent!important;background:transparent!important}\n"
    "  .nts-section.nts-dim>.nts-body>textarea.note-area::placeholder{opacity:0!important}\n"
    "  .nts-section.nts-dim>.nts-body>.nts-ch>button{opacity:0!important;pointer-events:none}"
)
c1 = text.count(old1); assert c1 == 1, f"CSS:{c1}"; text = text.replace(old1, new1); print("CSS OK")

# 2. fOp value
old2 = "var fOp='0.12';"
new2 = "var fOp='0';"
c2 = text.count(old2); assert c2 == 1, f"fOp:{c2}"; text = text.replace(old2, new2); print("fOp OK")

# 3. applyOpacity forEach — add section bg/border, change textarea bg to transparent
old3 = (
    "            var dim=(s!==activeNoteContainer);\n"
    "            s.classList.toggle('nts-dim',dim);\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity=dim?fOp:'';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity=dim?fOp:'';ta.style.borderColor=dim?'transparent':'';ta.style.background=dim?'var(--bg3)':'';}  "
)
new3 = (
    "            var dim=(s!==activeNoteContainer);\n"
    "            s.classList.toggle('nts-dim',dim);\n"
    "            s.style.background=dim?'transparent':'';\n"
    "            s.style.borderColor=dim?'transparent':'';\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity=dim?fOp:'';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity=dim?fOp:'';ta.style.borderColor=dim?'transparent':'';ta.style.background=dim?'transparent':'';}  "
)
# strip trailing spaces so the match is exact
old3 = old3.rstrip()
new3 = new3.rstrip()
c3 = text.count(old3); assert c3 == 1, f"forEach:{c3}"; text = text.replace(old3, new3); print("forEach OK")

# 4. setFloat cleanup — add section bg/border reset
old4 = (
    "            s.classList.remove('nts-dim');\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity='';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity='';ta.style.borderColor='';ta.style.background='';}"
)
new4 = (
    "            s.classList.remove('nts-dim');\n"
    "            s.style.background=''; s.style.borderColor='';\n"
    "            var hdr=s.querySelector(':scope>summary');\n"
    "            if(hdr) hdr.style.opacity='';\n"
    "            var ta=s.querySelector(':scope>.nts-body>textarea');\n"
    "            if(ta){ta.style.opacity='';ta.style.borderColor='';ta.style.background='';}"
)
c4 = text.count(old4); assert c4 == 1, f"cleanup:{c4}"; text = text.replace(old4, new4); print("cleanup OK")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Done.")
