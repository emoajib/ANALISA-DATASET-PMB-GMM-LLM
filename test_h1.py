import docx
doc = docx.Document("FULL TESIS/FULL TESIS FINAL.docx")
count = 0
for p in doc.paragraphs:
    if p.style.name == 'Heading 1':
        count += 1
        print(f"H1: {p.text[:50]}")
