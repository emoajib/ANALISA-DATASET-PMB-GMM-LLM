import docx

def update_front_matter():
    path = "PENGERJAAN TESIS BAB I - BAB V/front_matter/FRONT_MATTER_DRAFT.docx"
    doc = docx.Document(path)
    
    for p in doc.paragraphs:
        if "Lampiran 1 – Kumpulan Kode Pemrograman Python" in p.text:
            p.text = p.text.replace("Kumpulan Kode Pemrograman Python", "Kode Python untuk olahdata")
            
    doc.save(path)
    print("Updated FRONT_MATTER_DRAFT.docx")

if __name__ == "__main__":
    update_front_matter()
