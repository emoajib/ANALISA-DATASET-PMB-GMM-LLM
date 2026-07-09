import docx

doc = docx.Document("PENGERJAAN TESIS BAB I - BAB V/BAB I - BAB IV.docx")
bib_idx = -1
for i, p in enumerate(doc.paragraphs):
    if "DAFTAR PUSTAKA" in p.text.upper():
        bib_idx = i
        break

print(f"Found DAFTAR PUSTAKA at index {bib_idx}")
