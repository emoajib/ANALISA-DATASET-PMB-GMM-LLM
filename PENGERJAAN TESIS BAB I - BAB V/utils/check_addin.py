import docx
doc = docx.Document("PENGERJAAN TESIS BAB I - BAB V/BAB I - BAB IV.docx")
found = False
for p in doc.paragraphs:
    if 'ADDIN' in p._element.xml:
        found = True
        break
print(f"ADDIN fields in source: {found}")
