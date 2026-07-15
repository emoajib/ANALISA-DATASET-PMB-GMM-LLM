#!/usr/bin/env python3
"""unitalicize_llm.py — Menghilangkan cetak miring pada kata LLM"""
import os, sys, re
from copy import deepcopy
from lxml import etree
from docx import Document
from docx.oxml.ns import qn

from pipeline import utils

PATH = str(utils.get_doc_path())

if not os.path.exists(PATH):
    print(f"[ERROR] File not found: {PATH}"); sys.exit(1)

doc = Document(PATH)

def get_run_text(r):
    return ''.join(t.text or '' for t in r.findall(qn('w:t')))

def split_run(r, at):
    t = get_run_text(r)
    if at <= 0 or at >= len(t): return r, None
    for el in r.findall(qn('w:t')): r.remove(el)
    t1 = etree.SubElement(r, qn('w:t')); t1.text = t[:at]; t1.set(qn('xml:space'), 'preserve')
    nr = deepcopy(r)
    for el in nr.findall(qn('w:t')): nr.remove(el)
    t2 = etree.SubElement(nr, qn('w:t')); t2.text = t[at:]; t2.set(qn('xml:space'), 'preserve')
    return r, nr

def unset_it(r):
    rp = r.find(qn('w:rPr'))
    if rp is not None:
        i = rp.find(qn('w:i'))
        if i is not None:
            # We can either remove the tag or set it to false
            # setting to false explicitly is safer to override paragraph styles
            i.set(qn('w:val'), 'false')

def unitalicize_span(p, cs, ce):
    mapping, run_elems = {}, p._p.findall(qn('w:r'))
    pos = 0
    for ri, r in enumerate(run_elems):
        for ci in range(len(get_run_text(r))):
            mapping[pos] = (ri, ci); pos += 1
    if not mapping or cs not in mapping or (ce-1) not in mapping: return False
    s_ri, e_ri = mapping[cs][0], mapping[ce-1][0]
    if s_ri == e_ri:
        r = run_elems[s_ri]; lt = len(get_run_text(r))
        if ce < len(mapping):
            _, aft = split_run(r, mapping[ce][1])
            if aft is not None: r.addnext(aft)
        if mapping[cs][1] > 0:
            _, mid = split_run(r, mapping[cs][1])
            if mid is not None: r.addnext(mid); unset_it(mid); return True
        unset_it(r); return True
    for ri in range(s_ri+1, e_ri):
        if ri < len(run_elems): unset_it(run_elems[ri])
    fr = run_elems[s_ri]; fl = len(get_run_text(fr))
    if mapping[cs][1] > 0:
        _, s2 = split_run(fr, mapping[cs][1])
        if s2 is not None: fr.addnext(s2); unset_it(s2)
    else: unset_it(fr)
    lr = run_elems[e_ri]; ll = len(get_run_text(lr))
    if mapping[ce-1][1] + 1 < ll:
        fp, sp = split_run(lr, mapping[ce-1][1]+1)
        if sp is not None: lr.addnext(sp); unset_it(fp)
    else: unset_it(lr)
    return True

total_changes = 0
total_paras = 0

for i, p in enumerate(doc.paragraphs):
    txt = p.text
    if not txt or not txt.strip(): continue
    
    # Cari LLM 
    matches = []
    for m in re.finditer(r'\bLLM\b', txt, re.IGNORECASE):
        matches.append((m.start(), m.end()))
        
    if not matches: continue
    matches.sort(key=lambda x: (x[0], -(x[1]-x[0])))
    filtered = []
    for s, e in matches:
        if filtered and s < filtered[-1][1]:
            if e <= filtered[-1][1]: continue
            filtered[-1] = (s, e); continue
        filtered.append((s, e))
    if not filtered: continue
    filtered.sort(reverse=True)
    
    changes = 0
    for s, e in filtered:
        if unitalicize_span(p, s, e): changes += 1
    if changes:
        print(f"  [UNITALIC] Par[{i}] +{changes} term(s)")
        total_changes += changes; total_paras += 1

print(f"\nParagraf diubah: {total_paras}, total kata LLM: {total_changes}")
doc.save(PATH)
print(f"Saved: {PATH}")
