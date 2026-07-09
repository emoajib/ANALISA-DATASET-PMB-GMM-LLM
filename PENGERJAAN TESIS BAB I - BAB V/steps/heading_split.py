import re
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DOC = 'Tesis_ITSNU_v11_Final.docx'
doc = Document(DOC)

manual_titles = {
    238: "2.1 Enrollment Management dan Strategi Rekrutmen Perguruan Tinggi",
    306: "3.1 Desain Penelitian",
    334: "3.8 Tahap 6 Pemodelan: GMM per Periode",
    375: "4.1 Deskripsi Data Time Series Calon Mahasiswa (2019–2024)",
}

auto_indices = [244, 256, 260, 273, 278, 280, 286, 289, 301]

all_indices = sorted(set(list(manual_titles.keys()) + auto_indices), reverse=True)

total = len(all_indices)
print(f"=== Heading Split ({total} heading) ===\n")

for idx in all_indices:
    para = doc.paragraphs[idx]
    text = para.text.strip()
    orig_len = len(text)

    if idx in manual_titles:
        title = manual_titles[idx]
        if not text.startswith(title):
            print(f"  P{idx}: WARNING - text does not start with expected title!")
            print(f"    Expected: |{title}|")
            print(f"    Actual:   |{text[:60]}...|")
            body = text
        else:
            body = text[len(title):].strip()
        method = "MANUAL"
    else:
        match = re.match(r'^(.+?)\.\s+([A-Z].*)$', text)
        if match and len(match.group(1)) <= 80:
            title, body = match.group(1), match.group(2)
            method = "PERIOD"
        else:
            cutoff = text[:80]
            last_space = cutoff.rfind(' ')
            title = text[:last_space]
            body = text[last_space + 1:]
            method = "CAP80"

    p_elem = para._element

    # --- Replace heading text (preserve pPr) ---
    for child in list(p_elem):
        if child.tag != qn('w:pPr'):
            p_elem.remove(child)

    h_r = OxmlElement('w:r')
    h_rPr = OxmlElement('w:rPr')
    h_rFonts = OxmlElement('w:rFonts')
    h_rFonts.set(qn('w:ascii'), 'Times New Roman')
    h_rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    h_rPr.append(h_rFonts)
    h_b = OxmlElement('w:b')
    h_rPr.append(h_b)
    h_sz = OxmlElement('w:sz')
    h_sz.set(qn('w:val'), '24')
    h_rPr.append(h_sz)
    h_szCs = OxmlElement('w:szCs')
    h_szCs.set(qn('w:val'), '24')
    h_rPr.append(h_szCs)
    h_r.insert(0, h_rPr)
    h_t = OxmlElement('w:t')
    h_t.text = title
    h_t.set(qn('xml:space'), 'preserve')
    h_r.append(h_t)
    p_elem.append(h_r)

    # --- Create body paragraph ---
    new_p = OxmlElement('w:p')
    new_pPr = OxmlElement('w:pPr')
    new_pStyle = OxmlElement('w:pStyle')
    new_pStyle.set(qn('w:val'), 'Normal')
    new_pPr.append(new_pStyle)
    new_ind = OxmlElement('w:ind')
    new_ind.set(qn('w:firstLine'), '720')
    new_pPr.append(new_ind)
    new_spacing = OxmlElement('w:spacing')
    new_spacing.set(qn('w:line'), '480')
    new_spacing.set(qn('w:lineRule'), 'auto')
    new_pPr.append(new_spacing)
    new_p.insert(0, new_pPr)

    new_r = OxmlElement('w:r')
    new_rPr = OxmlElement('w:rPr')
    new_rFonts = OxmlElement('w:rFonts')
    new_rFonts.set(qn('w:ascii'), 'Times New Roman')
    new_rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    new_rPr.append(new_rFonts)
    new_sz = OxmlElement('w:sz')
    new_sz.set(qn('w:val'), '24')
    new_rPr.append(new_sz)
    new_szCs = OxmlElement('w:szCs')
    new_szCs.set(qn('w:val'), '24')
    new_rPr.append(new_szCs)
    new_r.insert(0, new_rPr)
    new_t = OxmlElement('w:t')
    new_t.text = body
    new_t.set(qn('xml:space'), 'preserve')
    new_r.append(new_t)
    new_p.append(new_r)

    p_elem.addnext(new_p)

    body_start_ok = body[0].isupper() if body else False
    status = "✅" if body_start_ok else "⚠️"
    print(f"  P{idx} [{method}] {status} ({orig_len}c → title={len(title)}c, body={len(body)}c)")
    print(f"    H: {title[:70]}")
    print(f"    B: {body[:70]}...")

doc.save(DOC)
print(f"\n✅ Saved: {DOC}")
