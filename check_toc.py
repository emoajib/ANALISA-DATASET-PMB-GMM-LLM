import docx
doc = docx.Document("FULL TESIS/FULL TESIS FINAL.docx")
found = False
for p in doc.paragraphs:
    if 'TOC' in p._element.xml:
        found = True
        break
print(f"TOC field in final: {found}")
