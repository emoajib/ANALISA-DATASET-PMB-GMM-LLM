import docx

doc = docx.Document("FULL TESIS/FULL TESIS FINAL.docx")
text = []
for p in doc.paragraphs:
    if p.text.strip():
        text.append(p.text.strip())

full_text = "\n".join(text)

print("\n--- RUMUSAN MASALAH FULL ---")
start = full_text.find("Rumusan Masalah")
if start != -1:
    print(full_text[start:start+1500])

print("\n--- KESIMPULAN FULL ---")
start = full_text.rfind("Kesimpulan")
if start != -1:
    print(full_text[start:start+2500])

