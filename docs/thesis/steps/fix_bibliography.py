#!/usr/bin/env python3
"""Rebuild Daftar Pustaka completely: clean, sort by author, fix orphans/hanging indent."""
import sys, os, re, shutil
from lxml import etree
import docx

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

DOC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TESIS_DOC', 'Tesis_ITSNU_v10_Final.docx')
BACKUP = DOC.replace('.docx', '_BEFORE_BIBFIX.docx')

ORPHAN_MARKS = ['Rai, K. D.']


def get_full_text(p_elem):
    """Get ALL text from paragraph including hyperlinks."""
    texts = []
    for t in p_elem.iter(f'{{{NS_W}}}t'):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)


def extract_author_surname(text):
    """Extract the surname from a bibliography entry for sorting."""
    # Remove arXiv DOI prefix — contains "arXiv" which falsely triggers [A-Z][a-z]
    text = re.sub(r'^https?://doi\.org/10\.48550/arXiv\.\d+\.\d+', '', text).strip()
    # Remove other URL prefixes — URL glued to author name without space.
    # The boundary is where a capital letter followed by lowercase begins (surname start).
    text = re.sub(r'^https?://[^\s]+?(?=[A-Z][a-z])', '', text).strip()
    # Remove leading non-alpha chars
    text = re.sub(r'^[^a-zA-Z]+', '', text)
    # Take text before first comma
    comma_idx = text.find(',')
    if comma_idx != -1:
        # Standard entry: "Surname, First..."
        words = text[:comma_idx].strip().split()
        if words:
            return words[-1].strip('.,;:()[]\'\"').lower()
    else:
        # Organizational entry (no comma). Use first word before the year.
        m = re.match(r'^([A-Za-z\s.]+?)\s*\(\d{4}\)', text)
        if m:
            words = m.group(1).strip().rstrip('.').split()
            if words:
                return words[0].strip('.,;:()[]\'\"').lower()
        parts = text.split()
        if parts:
            return parts[0].strip('.,;:()[]\'\"').lower()
    return text.strip().lower()


def strip_glued_url(text):
    """Remove URLs glued to beginning of entry (incorrect hyperlink artifacts)."""
    # Handle arXiv DOIs first
    text = re.sub(r'^https?://doi\.org/10\.48550/arXiv\.\d+\.\d+', '', text).strip()
    # Handle other URLs glued to author name
    text = re.sub(r'^https?://[^\s]+?(?=[A-Z][a-z])', '', text).strip()
    return text


def clean_brackets(text):
    text = re.sub(r'\s*\[Referensi[^\]]*\]', '', text)
    text = re.sub(r'\s*\[Software\]', '', text)
    text = re.sub(r'\s*\[ISBN[^\]]*\]', '', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def make_entry_run(text):
    """Create a w:r for bibliography entry (TNR 12pt)."""
    r = etree.SubElement(etree.Element('dummy'), f'{{{NS_W}}}r')
    rPr = etree.SubElement(r, f'{{{NS_W}}}rPr')
    rFonts = etree.SubElement(rPr, f'{{{NS_W}}}rFonts')
    rFonts.set(f'{{{NS_W}}}ascii', 'Times New Roman')
    rFonts.set(f'{{{NS_W}}}hAnsi', 'Times New Roman')
    rFonts.set(f'{{{NS_W}}}cs', 'Times New Roman')
    sz = etree.SubElement(rPr, f'{{{NS_W}}}sz')
    sz.set(f'{{{NS_W}}}val', '24')
    szCs = etree.SubElement(rPr, f'{{{NS_W}}}szCs')
    szCs.set(f'{{{NS_W}}}val', '24')
    t = etree.SubElement(r, f'{{{NS_W}}}t')
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return r


def set_hanging_indent(pPr):
    ind = pPr.find(f'{{{NS_W}}}ind')
    if ind is None:
        ind = etree.SubElement(pPr, f'{{{NS_W}}}ind')
    if ind.get(f'{{{NS_W}}}first') is not None:
        del ind.attrib[f'{{{NS_W}}}first']
    if ind.get(f'{{{NS_W}}}hanging') is not None:
        del ind.attrib[f'{{{NS_W}}}hanging']
    ind.set(f'{{{NS_W}}}left', '720')
    ind.set(f'{{{NS_W}}}hanging', '720')


def main():
    shutil.copy2(DOC, BACKUP)
    doc = docx.Document(DOC)
    body = doc.element.body
    paras = body.findall(f'{{{NS_W}}}p')

    # === Find bibliography range after "DAFTAR PUSTAKA" heading ===
    bib_start = None
    first_entry_text = None
    heading_idx = None
    for i, p_elem in enumerate(paras):
        text = get_full_text(p_elem).strip()
        if text.upper().startswith('DAFTAR PUSTAKA'):
            pPr = p_elem.find(f'{{{NS_W}}}pPr')
            style_val = ''
            if pPr is not None:
                pStyle = pPr.find(f'{{{NS_W}}}pStyle')
                if pStyle is not None:
                    style_val = pStyle.get(f'{{{NS_W}}}val', '')
            is_heading = False
            if style_val:
                try:
                    s_name = doc.styles[style_val].name
                    is_heading = 'Heading' in s_name
                except:
                    is_heading = any(x in style_val for x in ['Heading', 'heading', 'Judul'])
            if is_heading:
                header = text[:14]
                rest = text[14:].strip()
                if rest:
                    first_entry_text = rest
                heading_idx = i
                bib_start = i + 1
                print(f'  DAFTAR PUSTAKA heading found at P{i} ({style_val})')
                break
    if bib_start is None:
        print('ERROR: Could not find DAFTAR PUSTAKA heading')
        sys.exit(1)
    total_p = len(paras)
    print(f'  Bibliography range: P{bib_start}-P{total_p-1}')

    raw = []
    if first_entry_text:
        cleaned = clean_brackets(first_entry_text).strip()
        cleaned = strip_glued_url(cleaned)
        if cleaned:
            raw.append({'text': cleaned, 'sort_key': extract_author_surname(cleaned)})

    for i in range(bib_start, total_p):
        p = paras[i]
        text = get_full_text(p)
        text = clean_brackets(text).strip()
        text = strip_glued_url(text)
        if text:
            raw.append({'idx': i, 'text': text, 'sort_key': extract_author_surname(text)})

    print(f'  Read {len(raw)} entries')

    # === Remove orphans ===
    active = []
    removed = 0
    for entry in raw:
        is_orphan = any(m in entry['text'] for m in ORPHAN_MARKS)
        if is_orphan:
            removed += 1
            t = entry['text'][:70]
            print(f'  Removed: {t}')
        else:
            active.append(entry)
    print(f'  Removed {removed} orphans')

    # === Sort alphabetically ===
    active.sort(key=lambda e: e['sort_key'])

    # === Clear all bibliography paragraphs ===
    for i in range(bib_start, total_p):
        p = paras[i]
        for child in list(p):
            tag = child.tag.split('}')[1] if '}' in child.tag else child.tag
            if tag != 'w:pPr':
                p.remove(child)

    # === Write sorted entries ===
    for offset, entry in enumerate(active):
        target_idx = bib_start + offset
        target_p = paras[target_idx]

        pPr = target_p.find(f'{{{NS_W}}}pPr')
        if pPr is None:
            pPr = etree.SubElement(target_p, f'{{{NS_W}}}pPr')
            target_p.insert(0, pPr)

        set_hanging_indent(pPr)
        target_p.append(make_entry_run(entry['text']))

    # === Clear remaining empty slots ===
    for i in range(bib_start + len(active), total_p):
        p = paras[i]
        for child in list(p):
            tag = child.tag.split('}')[1] if '}' in child.tag else child.tag
            if tag != 'w:pPr':
                p.remove(child)

    print(f'  Written {len(active)} entries, sorted + hanging indent + brackets cleaned')

    # Fix merged heading text (DAFTAR PUSTAKANdibalema → DAFTAR PUSTAKA)
    if heading_idx is not None and first_entry_text:
        h_elem = paras[heading_idx]
        for child in list(h_elem):
            tag = child.tag.split('}')[1] if '}' in child.tag else child.tag
            if tag != 'w:pPr':
                h_elem.remove(child)
        h_elem.append(make_run('DAFTAR PUSTAKA', bold=True))
        print(f'  Fixed merged heading: removed first entry from P{heading_idx}')

    doc.save(DOC)
    print(f'Saved: {DOC}')


if __name__ == '__main__':
    main()
