#!/usr/bin/env python3
"""
fix_compliance.py — Perbaiki 7 failure compliance check.
Jalankan SETELAH fix_structure.py + fix_remaining.py.
"""
import os, re, sys, copy
from lxml import etree
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TESIS_DOC', 'Tesis_ITSNU_v10_Final.docx')
NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

doc = Document(DOC)
body = doc.element.body
children = list(body)

def para_text(elem):
    texts = [t.text for t in elem.findall('.//' + qn('w:t')) if t.text]
    return ''.join(texts).strip()

def get_style_name(para):
    pPr = para.find(qn('w:pPr'))
    if pPr is None: return ''
    ps = pPr.find(qn('w:pStyle'))
    return ps.get(qn('w:val'), '') if ps is not None else ''

def get_outline_lvl(para):
    pPr = para.find(qn('w:pPr'))
    if pPr is None: return None
    ol = pPr.find(qn('w:outlineLvl'))
    return ol.get(qn('w:val')) if ol is not None else None

def ensure_pPr(para):
    pPr = para.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        para.insert(0, pPr)
    return pPr

def set_justify(para):
    pPr = ensure_pPr(para)
    jc = pPr.find(qn('w:jc'))
    if jc is None:
        jc = OxmlElement('w:jc')
        pPr.append(jc)
    jc.set(qn('w:val'), 'both')

def set_center(para):
    pPr = ensure_pPr(para)
    for jc in pPr.findall(qn('w:jc')):
        pPr.remove(jc)
    jc = OxmlElement('w:jc')
    jc.set(qn('w:val'), 'center')
    pPr.append(jc)

def set_bold(para, bold=True):
    for r in para.findall('.//' + qn('w:r')):
        rPr = r.find(qn('w:rPr'))
        if rPr is None:
            rPr = OxmlElement('w:rPr')
            r.insert(0, rPr)
        b = rPr.find(qn('w:b'))
        if bold:
            if b is None:
                b = OxmlElement('w:b')
                rPr.append(b)
        else:
            if b is not None:
                rPr.remove(b)

def _get_h1_style_name(body):
    """Detect the XML style name for Heading 1 from existing H1 paragraphs."""
    NS_W = qn('w:pPr').replace('w:pPr', '').rstrip('}')
    for c in body:
        if c.tag != qn('w:p'): continue
        pPr = c.find(qn('w:pPr'))
        if pPr is None: continue
        ps = pPr.find(qn('w:pStyle'))
        if ps is None: continue
        val = ps.get(qn('w:val'), '')
        if val and ('Heading1' in val or 'heading1' in val or 'Judul1' in val):
            return val
        # Also check outline level
        ol = pPr.find(qn('w:outlineLvl'))
        if ol is not None and ol.get(qn('w:val')) == '1':
            if val:
                return val
    return 'Heading1'

H1_STYLE = _get_h1_style_name(doc.element.body)

def set_heading1(para):
    """Set paragraph to Heading 1 style."""
    global H1_STYLE
    pPr = ensure_pPr(para)
    for ps in pPr.findall(qn('w:pStyle')):
        pPr.remove(ps)
    ps = OxmlElement('w:pStyle')
    ps.set(qn('w:val'), H1_STYLE)
    pPr.append(ps)
    # Set outline level 1 (NOT 0 — per pedoman H1 outline=1)
    for ol in pPr.findall(qn('w:outlineLvl')):
        pPr.remove(ol)
    ol = OxmlElement('w:outlineLvl')
    ol.set(qn('w:val'), '1')
    pPr.append(ol)
    # Center alignment
    set_center(para)
    # Bold
    set_bold(para, True)

def set_outline_lvl(para, lvl):
    pPr = ensure_pPr(para)
    for ol in pPr.findall(qn('w:outlineLvl')):
        pPr.remove(ol)
    ol = OxmlElement('w:outlineLvl')
    ol.set(qn('w:val'), str(lvl))
    pPr.append(ol)

changes = []

# ═══════════════════════════════════════════════════════════════
# FIX 1: Section 2 margins + paper size → 4-3-4-3 cm, A4
# ═══════════════════════════════════════════════════════════════

sectPrs = body.findall(qn('w:sectPr'))
S2_EMU_4CM = 1440000   # 4 cm
S2_EMU_3CM = 1080000   # 3 cm
S2_EMU_A4W = 11906     # A4 width in TWIPs
S2_EMU_A4H = 16838     # A4 height in TWIPs

for idx, sp in enumerate(sectPrs):
    parent = sp.getparent()
    # Find the actual python-docx section
    if idx < len(doc.sections):
        sec = doc.sections[idx]
        pgSz = sp.find(qn('w:pgSz'))
        if pgSz is not None:
            w = int(pgSz.get(qn('w:w'), 0))
            h = int(pgSz.get(qn('w:h'), 0))
            # Check if not A4
            if abs(w - S2_EMU_A4W) > 10 or abs(h - S2_EMU_A4H) > 10:
                pgSz.set(qn('w:w'), str(S2_EMU_A4W))
                pgSz.set(qn('w:h'), str(S2_EMU_A4H))
                # Also fix orientation
                pgSz.set(qn('w:orient'), 'portrait')
                changes.append(f'S{idx+1} paper → A4')

        # Fix margins in sectPr — skip body-level sectPr (section 4)
        # body-level sectPr's parent is <w:body>, not <w:p>
        parent = sp.getparent()
        is_body_level = parent.tag == qn('w:body')
        if not is_body_level:
            for tag, val in [('w:pgMar', {'top':'1440','bottom':'1440','left':'1440','right':'1440',
                                           'header':'708','footer':'708','gutter':'0'})]:
                # Just remove existing pgMar, python-docx will regenerate
                pgMar = sp.find(qn('w:pgMar'))
                if pgMar is not None:
                    sp.remove(pgMar)
                    changes.append(f'S{idx+1} pgMar removed')

# Set margins for ALL sections (skip body-level sectPr — set separately)
from docx.shared import Cm as Dcm
for si in range(len(doc.sections)):
    sec = doc.sections[si]
    sec.top_margin = Dcm(4)
    sec.bottom_margin = Dcm(3)
    sec.left_margin = Dcm(4)
    sec.right_margin = Dcm(3)
    sec.page_width = Dcm(21)
    sec.page_height = Dcm(29.7)
    changes.append(f'S{si+1} margins set to 4-3-4-3 cm, A4')

# ═══════════════════════════════════════════════════════════════
# FIX 2: Justify all body paragraphs (not headings, TOC, captions)
# ═══════════════════════════════════════════════════════════════

first_bab_idx = None
last_dp_idx = None
for i, c in enumerate(children):
    if c.tag != qn('w:p'): continue
    t = para_text(c)
    if t.startswith('BAB I') or t == 'BAB I':
        if first_bab_idx is None:
            first_bab_idx = i
    if t == 'DAFTAR PUSTAKA' or t.startswith('DAFTAR PUSTAKA\n'):
        last_dp_idx = i

justify_count = 0
for i, c in enumerate(children):
    if c.tag != qn('w:p'): continue
    t = para_text(c)
    if not t: continue
    style = get_style_name(c)
    
    # Skip headings
    if style in ('Heading 1', 'Heading 2', 'Heading 3', 'heading1', 'heading2', 'heading3'):
        continue
    if style.startswith('TOC'):
        continue
    
    # Skip TOC field paragraph
    instr = c.findall('.//' + qn('w:instrText'))
    if instr and any('TOC' in (i.text or '') for i in instr):
        continue
    
    # Skip table/gambar captions (they should be centered, not justified)
    if re.match(r'^(Tabel|Gambar)\s+\d+\.\d+\s+', t):
        continue
    
    # Skip centered headings
    pPr = c.find(qn('w:pPr'))
    if pPr is not None:
        jc = pPr.find(qn('w:jc'))
        if jc is not None and jc.get(qn('w:val')) == 'center':
            continue
    
    # Only justify body text paragraphs (longer than 30 chars, not list items)
    if len(t) >= 30 and not t.startswith(('Sumber:', 'Catatan:', 'Keterangan:')):
        set_justify(c)
        justify_count += 1

changes.append(f'{justify_count} paragraphs justified')

# ═══════════════════════════════════════════════════════════════
# FIX 3: ABSTRAK/ABSTRACT heading → Heading 1, center, bold
# ═══════════════════════════════════════════════════════════════

for i, c in enumerate(children):
    if c.tag != qn('w:p'): continue
    t = para_text(c)
    if t.upper() in ('ABSTRAK', 'ABSTRACT'):
        old_style = get_style_name(c)
        if old_style != H1_STYLE:
            set_heading1(c)
            changes.append(f'[{i}] \"{t}\" → Heading1 (was \"{old_style}\")')

# ═══════════════════════════════════════════════════════════════
# FIX 4: Gambar captions → center
# ═══════════════════════════════════════════════════════════════

gambar_count = 0
gambar_fixed = 0
for i, c in enumerate(children):
    if c.tag != qn('w:p'): continue
    t = para_text(c)
    m = re.match(r'^Gambar\s+\d+\.\d+\s+', t)
    if m:
        gambar_count += 1
        # Check if centered
        pPr = c.find(qn('w:pPr'))
        if pPr is not None:
            jc = pPr.find(qn('w:jc'))
            if jc is None or jc.get(qn('w:val')) != 'center':
                set_center(c)
                gambar_fixed += 1

if gambar_fixed:
    changes.append(f'{gambar_fixed}/{gambar_count} Gambar captions centered')

# ═══════════════════════════════════════════════════════════════
# FIX 5: Check bibliography sorting
# ═══════════════════════════════════════════════════════════════

bib_start = None
bib_end = None
for i, c in enumerate(children):
    if c.tag != qn('w:p'): continue
    t = para_text(c)
    if t == 'DAFTAR PUSTAKA' or t.startswith('DAFTAR PUSTAKA\n'):
        bib_start = i
        break

if bib_start is not None:
    # Find entries
    entries = []
    for j in range(bib_start + 1, min(bib_start + 50, len(children))):
        c = children[j]
        if c.tag != qn('w:p'): continue
        t = para_text(c)
        if not t:
            break
        entries.append((j, t))
    
    # Check sorting
    surnames = [(j, t.split(',')[0].lower() if ',' in t else t.split()[0].lower()) for j, t in entries]
    is_sorted = all(surnames[k][1] <= surnames[k+1][1] for k in range(len(surnames)-1))
    if not is_sorted:
        changes.append(f'WARNING: {len(entries)} bib entries NOT sorted (run fix_bibliography.py)')
    else:
        changes.append(f'{len(entries)} bib entries sorted OK')

# ═══════════════════════════════════════════════════════════════
# FIX 6: Decimal titik — identify violations
# ═══════════════════════════════════════════════════════════════

decimal_hits = []
for i, c in enumerate(children):
    if c.tag != qn('w:p'): continue
    t = para_text(c)
    if not t: continue
    style = get_style_name(c)
    if style in ('Heading 1', 'Heading 2', 'Heading 3'): continue
    if re.match(r'^(Tabel|Gambar) \d+\.\d+', t): continue
    
    hits = re.findall(r'\b\d+\.\d+\b', t)
    for h in hits:
        # Apply same filters as check_pedoman
        filtered = False
        # heading number
        if re.match(r'^\d\.\d$', h) and int(h.split('.')[0]) <= 5:
            filtered = True
        # year
        if re.match(r'^\d{4}$', h.replace('.','')):
            filtered = True
        # version
        if re.match(r'^\d+\.\d+\.\d+', h):
            filtered = True
        # DOI
        if re.match(r'^10\.\d+', h):
            filtered = True
        # NIM
        if re.match(r'^\d{2}\.\d{2}\.\d{4}', h) or re.search(r'\d{2}\.\d{2}\.\d{2}\.\d{4}', t):
            filtered = True
        # arxiv
        if re.match(r'^\d{4}\.\d+', h) and 'arxiv' in t.lower():
            filtered = True
        # DOI context
        if '/' in t and re.match(r'^\d+\.\d+', h) and re.search(r'doi\.org/|arxiv\.org/', t):
            filtered = True
        # thousands separator
        if re.match(r'^\d{1,3}(?:\.\d{3})+$', h) and not re.match(r'^\d+\.\d{1,2}$', h):
            filtered = True
        
        if not filtered:
            decimal_hits.append((i, h, t[:80]))

if decimal_hits:
    changes.append(f'Decimal titik violations: {len(decimal_hits)}')
    for idx, hit, ctx in decimal_hits:
        changes.append(f'  [{idx}] \"{hit}\" in \"{ctx}\"')
else:
    changes.append('No decimal titik violations found')

# ═══════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════

print(f'fix_compliance.py — {len(changes)} changes')
for ch in changes:
    print(f'  {ch}')

doc.save(DOC)
print(f'Saved: {DOC}')

