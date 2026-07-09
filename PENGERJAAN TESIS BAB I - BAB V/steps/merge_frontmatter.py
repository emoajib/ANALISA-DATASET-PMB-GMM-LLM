#!/usr/bin/env python3
"""
merge_frontmatter.py — Merge FRONT_MATTER_DRAFT.docx into main thesis DOCX.

Menyisipkan halaman depan (persetujuan, pengesahan, pernyataan,
kata pengantar, daftar isi, abstrak) di antara cover dan BAB I.
Mengatur section break untuk page numbering:
  - Cover: tanpa nomor
  - Front matter: angka Romawi (i, ii, iii, ...)
  - Body: angka Arab (1, 2, 3, ...)

Usage:
    python3 steps/merge_frontmatter.py <main_docx> --front-matter <path> [--output <path>]
"""

import argparse, copy, os, re, shutil, tempfile, zipfile
from lxml import etree

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = f'{{{NS_W}}}'


def _qn(tag):
    return f'{W}{tag}'


def _para_text(elem):
    texts = [t.text for t in elem.iter(_qn('t')) if t.text]
    return ''.join(texts).strip()


def merge_front_matter(main_path, fm_path, output_path):
    print(f"\n{'='*60}")
    print("MERGE FRONT MATTER")
    print(f"{'='*60}")

    # ── 1. Parse both DOCX as ZIP ──────────────────────────────
    with zipfile.ZipFile(main_path) as z:
        main_doc_xml = z.read('word/document.xml')
        main_rel = z.read('word/_rels/document.xml.rels') if 'word/_rels/document.xml.rels' in z.namelist() else b''

    with zipfile.ZipFile(fm_path) as z:
        fm_doc_xml = z.read('word/document.xml')
        fm_rel = z.read('word/_rels/document.xml.rels') if 'word/_rels/document.xml.rels' in z.namelist() else b''
        fm_namelist = z.namelist()

    # ── 2. Construct new body XML ──────────────────────────────
    main_tree = etree.fromstring(main_doc_xml)
    main_body = main_tree.find(_qn('body'))
    main_children = list(main_body)

    fm_tree = etree.fromstring(fm_doc_xml)
    fm_body = fm_tree.find(_qn('body'))
    fm_paras = [c for c in fm_body if c.tag in (_qn('p'), _qn('tbl'))]

    # Find BAB I index in fresh copy
    bab_idx = None
    for i, child in enumerate(main_children):
        if child.tag == _qn('p'):
            text2 = _para_text(child)
            pPr = child.find(_qn('pPr'))
            if pPr is not None:
                pStyle = pPr.find(_qn('pStyle'))
                if pStyle is not None:
                    sv = pStyle.get(_qn('val'))
                    if sv and ('Judul1' in sv or 'Heading1' in sv or sv == '1') and text2.startswith('BAB '):
                        bab_idx = i
                        break

    if bab_idx is None:
        print("  ❌ BAB I not found")
        return False

    print(f"  Main doc: {len(main_children)} elements, BAB I at index {bab_idx}")
    print(f"  Front matter: {len(fm_paras)} paragraphs/tables to insert")

    # Separate cover (before BAB I) and body (BAB I onwards)
    cover_elements = main_children[:bab_idx]
    body_elements = main_children[bab_idx:]

    # Extract original sectPr template (copy page size, margins etc.)
    original_sectpr = main_body.find(_qn('sectPr'))
    original_pr_copy = copy.deepcopy(original_sectpr) if original_sectpr is not None else None

    def _make_sectpr(template=None, pgNumType_fmt=None, pgNumType_start=None,
                     break_type=None, title_pg=False):
        """Create sectPr copying page dimensions from template."""
        sp = etree.Element(_qn('sectPr'))
        if template is not None:
            for child in template:
                # Copy pgSz, pgMar, headerReference, footerReference etc.
                tag_local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag_local in ('pgSz', 'pgMar', 'headerReference', 'footerReference',
                                 'cols', 'docGrid', 'titlePg', 'type', 'pgNumType'):
                    sp.append(copy.deepcopy(child))
        if pgNumType_fmt is not None:
            # Remove existing pgNumType
            for existing in sp.findall(_qn('pgNumType')):
                sp.remove(existing)
            pn = etree.SubElement(sp, _qn('pgNumType'))
            pn.set(_qn('fmt'), pgNumType_fmt)
            if pgNumType_start is not None:
                pn.set(_qn('start'), str(pgNumType_start))
        if break_type is not None:
            # Remove existing type
            for existing in sp.findall(_qn('type')):
                sp.remove(existing)
            bt = etree.SubElement(sp, _qn('type'))
            bt.set(_qn('val'), break_type)
        if title_pg:
            if sp.find(_qn('titlePg')) is None:
                etree.SubElement(sp, _qn('titlePg'))
        return sp

    # Remove all children from body to rebuild
    for child in list(main_body):
        main_body.remove(child)

    # Phase 1: Cover section
    for elem in cover_elements:
        main_body.append(copy.deepcopy(elem))

    # Section break 1: after cover → front matter (next page, title page)
    main_body.append(_make_sectpr(
        template=original_pr_copy,
        break_type='nextPage',
        title_pg=True
    ))

    # Phase 2: Front matter section
    for para in fm_paras:
        main_body.append(copy.deepcopy(para))

    # Section break 2: after front matter → body (next page, Roman numerals)
    main_body.append(_make_sectpr(
        template=original_pr_copy,
        pgNumType_fmt='lowerRoman',
        break_type='nextPage'
    ))

    # Phase 3: Body section (BAB I+) — skip trailing sectPr from original
    for elem in body_elements:
        if elem.tag == _qn('sectPr'):
            continue  # we'll add our own
        main_body.append(copy.deepcopy(elem))

    # Final sectPr: body properties (Arabic numbers starting from 1)
    main_body.append(_make_sectpr(
        template=original_pr_copy,
        pgNumType_fmt='decimal',
        pgNumType_start=1
    ))

    # ── 7. Merge relationships (only copy real image refs) ─────
    main_rel_root = None
    main_rids = set()
    if main_rel:
        main_rel_root = etree.fromstring(main_rel)
        for rel in main_rel_root:
            main_rids.add(rel.get('Id'))

    # Find next available rId
    next_id = 1
    while f'rId{next_id}' in main_rids:
        next_id += 1

    # Only copy image relationships from front matter
    rId_map = {}
    if fm_rel:
        fm_rel_root = etree.fromstring(fm_rel)
        for rel in fm_rel_root:
            rel_type = rel.get('Type', '')
            if 'image' not in rel_type:
                continue  # skip non-image rels
            rid = rel.get('Id')
            target = rel.get('Target')
            new_rid = f'rId{next_id}'
            next_id += 1
            rId_map[rid] = new_rid
            # Create rels root if needed (should always exist though)
            if main_rel_root is None:
                main_rel_root = etree.Element('{http://schemas.openxmlformats.org/package/2006/relationships}Relationships')
            new_rel = etree.SubElement(main_rel_root, 'Relationship')
            new_rel.set('Id', new_rid)
            new_rel.set('Type', rel_type)
            new_rel.set('Target', target)

    # Remap image references in merged body XML
    for blip in main_body.iter(_qn('blip')):
        embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
        if embed and embed in rId_map:
            blip.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed', rId_map[embed])

    # ── 8. Write output ────────────────────────────────────────
    print(f"\n  Writing to: {output_path}")

    # If in-place, write to temp file first
    use_temp = (os.path.abspath(main_path) == os.path.abspath(output_path))
    temp_path = None
    if use_temp:
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix='.docx')
        os.close(temp_fd)
        write_path = temp_path
    else:
        write_path = output_path

    # Copy main docx as base
    shutil.copy2(main_path, write_path)

    # Update word/document.xml
    with zipfile.ZipFile(write_path, 'r') as z:
        all_names = z.namelist()
        data = {n: z.read(n) for n in all_names}

    # Convert updated XML back to bytes
    data['word/document.xml'] = etree.tostring(main_tree, xml_declaration=True, encoding='UTF-8', standalone=True)

    # Write updated rels
    if main_rel is not None:
        data['word/_rels/document.xml.rels'] = etree.tostring(main_rel_root, xml_declaration=True, encoding='UTF-8', standalone=True)

    # Copy media files from front matter
    for name in fm_namelist:
        if name.startswith('word/media/') or name == 'word/media':
            if name not in data:
                with zipfile.ZipFile(fm_path) as zfm:
                    data[name] = zfm.read(name)

    # Write back
    with zipfile.ZipFile(write_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, content in data.items():
            zout.writestr(name, content)

    # If in-place, replace output with temp
    if use_temp and temp_path:
        shutil.move(temp_path, output_path)

    print(f"\n  ✅ Merge complete: {len(fm_paras)} front matter elements inserted")
    print(f"     Sections: cover → front matter (Roman) → body (Arabic)")
    return True


def main():
    parser = argparse.ArgumentParser(description='Merge front matter into thesis DOCX')
    parser.add_argument('main_docx', help='Main thesis DOCX file')
    parser.add_argument('--front-matter', required=True, help='FRONT_MATTER_DRAFT.docx path')
    parser.add_argument('--output', help='Output path (default: overwrite input)')
    args = parser.parse_args()

    output = args.output or args.main_docx

    merge_front_matter(args.main_docx, args.front_matter, output)


if __name__ == '__main__':
    main()
