import docx
doc = docx.Document("FULL TESIS/FULL TESIS FINAL.docx")
for p in doc.paragraphs:
    if "DAFTAR LAMPIRAN" in p.text:
        print("Found DAFTAR LAMPIRAN!")
    elif "Lampiran 1" in p.text or "Kode Python" in p.text:
        print(f"Found: {p.text}")
