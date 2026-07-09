import docx

doc = docx.Document("FULL TESIS/FULL TESIS FINAL.docx")
text = []
for p in doc.paragraphs:
    if p.text.strip():
        text.append(p.text.strip())

full_text = "\n".join(text)

print(f"Total characters: {len(full_text)}")
print("\n--- RUMUSAN MASALAH ---")
start = full_text.find("Rumusan Masalah")
if start != -1:
    print(full_text[start:start+500])

print("\n--- KESIMPULAN ---")
start = full_text.rfind("Kesimpulan")
if start != -1:
    print(full_text[start:start+1000])

print("\n--- NAMA KLASTER ---")
for t in full_text.split("\n"):
    if "Klaster" in t and ":" in t and len(t) < 100:
        print(t)
