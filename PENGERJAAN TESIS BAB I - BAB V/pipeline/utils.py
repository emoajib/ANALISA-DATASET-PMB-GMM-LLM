import re
from lxml import etree
from pathlib import Path


NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def load_docx(path):
    import docx
    return docx.Document(str(path))


def save_docx(doc, path):
    doc.save(str(path))


def get_xml_spacing(p_elem):
    pPr = p_elem.find(f'{{{NS_W}}}pPr')
    if pPr is None:
        pPr = etree.SubElement(p_elem, f'{{{NS_W}}}pPr')
        p_elem.insert(0, pPr)
    return pPr


def set_spacing(p_elem, line=240, after=0, before=0, line_rule='auto'):
    pPr = get_xml_spacing(p_elem)
    for sp in pPr.findall(f'{{{NS_W}}}spacing'):
        pPr.remove(sp)
    sp = etree.SubElement(pPr, f'{{{NS_W}}}spacing')
    sp.set(f'{{{NS_W}}}line', str(line))
    sp.set(f'{{{NS_W}}}lineRule', line_rule)
    sp.set(f'{{{NS_W}}}after', str(after))
    sp.set(f'{{{NS_W}}}before', str(before))
    return sp


def set_hanging_indent(p_elem, left=720, hanging=720):
    pPr = get_xml_spacing(p_elem)
    for ind in pPr.findall(f'{{{NS_W}}}ind'):
        pPr.remove(ind)
    ind = etree.SubElement(pPr, f'{{{NS_W}}}ind')
    ind.set(f'{{{NS_W}}}left', str(left))
    ind.set(f'{{{NS_W}}}hanging', str(hanging))


def set_first_line_indent(p_elem, indent=720):
    pPr = get_xml_spacing(p_elem)
    for ind in pPr.findall(f'{{{NS_W}}}ind'):
        pPr.remove(ind)
    ind = etree.SubElement(pPr, f'{{{NS_W}}}ind')
    ind.set(f'{{{NS_W}}}first', str(indent))


def set_paragraph_alignment(p_elem, alignment='both'):
    pPr = get_xml_spacing(p_elem)
    for jc in pPr.findall(f'{{{NS_W}}}jc'):
        pPr.remove(jc)
    jc = etree.SubElement(pPr, f'{{{NS_W}}}jc')
    jc.set(f'{{{NS_W}}}val', alignment)


def get_para_text(p_elem):
    texts = [t.text for t in p_elem.findall(f'.//{{{NS_W}}}t') if t.text]
    return ''.join(texts).strip()


def find_daftar_pustaka(doc):
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip().upper() == 'DAFTAR PUSTAKA' or p.text.strip().upper().startswith('DAFTAR PUSTAKA\n'):
            return i, p._element
    return None, None


def get_doc_path(path_arg=None):
    import os, sys
    if path_arg:
        return Path(path_arg).resolve()
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    env_doc = os.environ.get('TESIS_DOC')
    if env_doc:
        return Path(env_doc).resolve()
    return Path('BAB I - BAB IV.docx').resolve()
