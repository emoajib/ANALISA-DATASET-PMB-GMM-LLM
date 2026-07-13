#!/usr/bin/env python3
"""
recover_tesis_final.py — Final text recovery for FULL TESIS FINAL.docx

Changes:
  1. "covariance_type full" → "covariance_type diag" (2x body text)
  2. "init_params k-means" → "init_params k-means++" (in same para as #1)
  3. Clear 9Router proxy paragraph text (D7/BAB III)
  4. Add Abstrak ID sentence: "Penelitian ini menganalisis 592 pendaftar..."
  5. "validasiDua" → "validasi Dua" (if found)

Rules:
  - lxml only, NO python-docx
  - Only modify <w:t> text nodes
  - NEVER touch <w:fldChar>, <w:instrText>, <w:drawing>, <w:object>, <m:oMath>
  - NEVER delete <w:p> — only clear text content if needed
  - Preserve all 42 ZIP entries

Usage:
  python3 recover_tesis_final.py
"""

import zipfile
import os
import sys
import shutil
from datetime import datetime
from lxml import etree

# === CONFIG ===
INPUT = "/Volumes/WORK/MTI UNSIBANK/TESIS/FULL TESIS/FULL TESIS FINAL.docx"
OUTPUT = "/Volumes/WORK/MTI UNSIBANK/TESIS/FULL TESIS/FULL_TESIS_FIXED.docx"
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# Protected XML tags — never modify
PROTECTED_LOCAL_TAGS = {
    'fldChar', 'instrText', 'drawing', 'object', 'pict',
}

def is_protected(el):
    """Check if element is a protected node (field code, drawing, equation)."""
    local = el.tag.split('}')[1] if '}' in el.tag else el.tag
    if local in PROTECTED_LOCAL_TAGS:
        return True
    if 'http://schemas.openxmlformats.org/officeDocument/2006/math' in el.tag:
        return True
    return False

def has_protected_ancestor(el):
    """Check if any ancestor is a protected node."""
    anc = el.getparent()
    while anc is not None:
        if is_protected(anc):
            return True
        anc = anc.getparent()
    return False

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_para_text(p):
    """Get full text of a paragraph element."""
    return ''.join(t.text or '' for t in p.findall(f'.//{{{W}}}t'))

def find_paragraph(t_node):
    """Walk up to find the enclosing <w:p>."""
    p = t_node.getparent()
    while p is not None and p.tag != f'{{{W}}}p':
        p = p.getparent()
    return p

def is_code_paragraph(p):
    """Check if paragraph is a code listing (import, def, class, #, st., logger)."""
    text = get_para_text(p)
    if 'import ' in text or text.strip().startswith('def ') or text.strip().startswith('class '):
        return True
    if text.strip().startswith('#') or text.strip().startswith('st.') or text.strip().startswith('logger.'):
        return True
    return False

def verify_zip(z, label):
    """Verify all ZIP entries are readable, return count and total size."""
    names = z.namelist()
    total = 0
    for n in names:
        total += len(z.read(n))
    log(f"{label}: {len(names)} files, {total:,} bytes")
    return len(names), total

def main():
    log("=" * 60)
    log("FULL TESIS FINAL — Text Recovery Script")
    log("=" * 60)

    # === Step 0: Verify input ===
    if not os.path.exists(INPUT):
        log(f"ERROR: Input not found: {INPUT}")
        sys.exit(1)

    input_size = os.path.getsize(INPUT)
    log(f"Input: {INPUT} ({input_size:,} bytes)")

    if os.path.exists(OUTPUT):
        backup = OUTPUT.replace('.docx', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
        shutil.copy2(OUTPUT, backup)
        log(f"Backed up existing output → {backup}")

    # === Step 1: Read all ZIP entries ===
    log("Reading input ZIP...")
    z_in = zipfile.ZipFile(INPUT, 'r')
    in_count, in_bytes = verify_zip(z_in, "Input")

    all_entries = {}
    for name in z_in.namelist():
        all_entries[name] = z_in.read(name)
    z_in.close()

    # === Step 2: Parse document.xml ===
    log("Parsing word/document.xml...")
    doc_data = all_entries['word/document.xml']
    root = etree.fromstring(doc_data)

    body = root.find(f'{{{W}}}body')
    if body is None:
        log("FATAL: No <w:body> found in document.xml")
        sys.exit(1)

    # All text nodes in body
    texts = body.findall(f'.//{{{W}}}t')
    log(f"Found {len(texts)} <w:t> nodes in body")

    changes = []
    warnings = []

    # For debugging: track which paras we touch
    touched_paras = set()

    # ============================================================
    # CHANGE 1 + 2: covariance_type full → diag + k-means → k-means++
    # ============================================================
    cov_count = 0
    kplus_count = 0
    for t in texts:
        txt = t.text or ''

        # 1a: covariance_type full → diag
        if 'covariance_type full' in txt:
            if has_protected_ancestor(t):
                log("  SKIP covariance_type full (protected ancestor)")
                continue
            p = find_paragraph(t)
            if p is not None and is_code_paragraph(p):
                log("  SKIP covariance_type full (code block)")
                continue

            old = t.text
            new = old.replace('covariance_type full', 'covariance_type diag')
            if new != old:
                t.text = new
                cov_count += 1
                touched_paras.add(id(p))
                log(f"  ✅ CHANGE 1a: covariance_type full→diag in paragraph starting with '{get_para_text(p)[:80]}...'")
                changes.append("covariance_type full → diag (1)")

        # 1b: init_params k-means → k-means++
        if 'init_params k-means' in txt and 'k-means++' not in txt:
            if has_protected_ancestor(t):
                continue
            p = find_paragraph(t)
            if p is not None and is_code_paragraph(p):
                continue

            old = t.text
            new = old.replace('init_params k-means', 'init_params k-means++')
            if new != old:
                t.text = new
                kplus_count += 1
                touched_paras.add(id(p))
                log(f"  ✅ CHANGE 1b: init_params k-means→k-means++")
                changes.append("init_params k-means → k-means++")

    if cov_count == 0:
        warnings.append("covariance_type full not found — already fixed?")
    log(f"Change 1 (covariance_type): {cov_count} occurrence(s)")
    log(f"Change 2 (k-means++): {kplus_count} occurrence(s)")

    # ============================================================
    # CHANGE 3: validasiDua → validasi Dua
    # ============================================================
    vd_count = 0
    for t in texts:
        txt = t.text or ''
        if 'validasiDua' in txt:
            old = t.text
            new = old.replace('validasiDua', 'validasi Dua')
            if new != old:
                t.text = new
                vd_count += 1
                changes.append("validasiDua → validasi Dua")
                log(f"  ✅ CHANGE 3: validasiDua→validasi Dua")

    if vd_count == 0:
        warnings.append("'validasiDua' not found — already correct or never present")
        log(f"  Note: 'validasiDua' not found (already correct)")

    # ============================================================
    # CHANGE 4: Clear 9Router proxy paragraph
    # ============================================================
    cleared = False
    for t in texts:
        txt = t.text or ''
        # Identify the specific paragraph by content
        if 'Cloud Engine via proxy lokal 9Router' in txt or \
           'Pipeline mengimplementasikan Hybrid Cognitive Pipeline dengan dual-engine' in txt:
            p = find_paragraph(t)
            if p is not None:
                para_full = get_para_text(p)
                if '9Router' in para_full and 'cascade fallback' in para_full:
                    # Clear all <w:t> text nodes in this paragraph
                    t_nodes = p.findall(f'.//{{{W}}}t')
                    for tn in t_nodes:
                        tn.text = ''
                    # Remove <w:br> for cleanliness
                    for br in p.findall(f'.//{{{W}}}br'):
                        br_parent = br.getparent()
                        if br_parent is not None:
                            br_parent.remove(br)
                    cleared = True
                    changes.append(f"Cleared 9Router proxy paragraph ({len(t_nodes)} text nodes)")
                    log(f"  ✅ CHANGE 4: Cleared 9Router paragraph ({len(t_nodes)} <w:t> nodes)")
                    break

    if not cleared:
        warnings.append("9Router proxy paragraph not found")
        log(f"  ⚠️  WARNING: 9Router paragraph not found to clear")

    # ============================================================
    # CHANGE 5: Add Abstrak ID sentence
    # ============================================================
    # Strategy: find "Kata kunci:" paragraph, go backward to find
    # the paragraph containing "Penelitian ini mengembangkan strategi"
    # Insert new sentence paragraph right after it.

    kata_kunci_para = None
    for t in texts:
        if t.text and t.text.startswith('Kata kunci:'):
            kata_kunci_para = find_paragraph(t)
            break

    if kata_kunci_para is not None:
        body_children = list(body)
        # Find index of Kata kunci paragraph
        kk_idx = body_children.index(kata_kunci_para) if kata_kunci_para in body_children else -1

        if kk_idx >= 2:
            # Go backward to find Abstrak ID paragraph
            abstrak_idx = -1
            for i in range(kk_idx - 1, max(0, kk_idx - 10), -1):
                child = body_children[i]
                text_content = get_para_text(child)
                if 'Penelitian ini mengembangkan strategi segmentasi probabilistik' in text_content:
                    abstrak_idx = i
                    break

            if abstrak_idx >= 0:
                # Create new paragraph element
                new_p = etree.Element(f'{{{W}}}p')

                # Add paragraph properties (justify both = rata kanan-kiri)
                pPr = etree.SubElement(new_p, f'{{{W}}}pPr')
                jc = etree.SubElement(pPr, f'{{{W}}}jc')
                jc.set(f'{{{W}}}val', 'both')

                # Add run with text
                r = etree.SubElement(new_p, f'{{{W}}}r')
                t_node = etree.SubElement(r, f'{{{W}}}t')
                t_node.text = (
                    'Penelitian ini menganalisis 592 pendaftar yang diproyeksikan '
                    'untuk tahun 2025 dan memvalidasi kualitas segmentasi melalui '
                    'validasi pakar dengan skor 4,0/5.'
                )

                # Insert right after Abstrak ID paragraph
                body.insert(abstrak_idx + 1, new_p)
                changes.append("Added Abstrak ID sentence")
                log(f"  ✅ CHANGE 5: Inserted Abstrak sentence after body index {abstrak_idx}")
            else:
                warnings.append("Abstrak ID paragraph not found before Kata kunci")
                log(f"  ⚠️  WARNING: Abstrak ID paragraph not found")
        else:
            warnings.append(f"Kata kunci at unexpected index {kk_idx}")
            log(f"  ⚠️  WARNING: Kata kunci at index {kk_idx}")
    else:
        warnings.append("'Kata kunci:' paragraph not found")
        log(f"  ⚠️  WARNING: Kata kunci paragraph not found")

    # === Step 4: Serialize document.xml ===
    log("Serializing document.xml...")
    doc_bytes = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    all_entries['word/document.xml'] = doc_bytes
    log(f"  Size: {len(doc_bytes):,} bytes")

    # === Step 5: Write output ZIP ===
    log("Writing output ZIP...")
    z_out = zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED)
    for name in sorted(all_entries.keys()):
        z_out.writestr(name, all_entries[name])
    z_out.close()

    # === Step 6: Verify output ===
    log("Verifying output integrity...")
    if not os.path.exists(OUTPUT):
        log("FATAL: Output file not written")
        sys.exit(1)

    try:
        z_verify = zipfile.ZipFile(OUTPUT, 'r')
        out_count, out_bytes = verify_zip(z_verify, "Output")
        z_verify.close()
    except Exception as e:
        log(f"FATAL: Output ZIP corrupt: {e}")
        sys.exit(1)

    if out_count != in_count:
        log(f"WARNING: Entry count mismatch! In={in_count}, Out={out_count}")
    else:
        log(f"✅ Entry count preserved: {out_count}")

    # Spot-check: re-parse document.xml and verify changes
    log("Spot-checking changes...")
    try:
        z_check = zipfile.ZipFile(OUTPUT, 'r')
        check_root = etree.fromstring(z_check.read('word/document.xml'))
        z_check.close()
        check_body = check_root.find(f'{{{W}}}body')
        check_texts = check_body.findall(f'.//{{{W}}}t')

        verifications = 0
        for ct in check_texts:
            txt = ct.text or ''
            if 'covariance_type full' in txt:
                log(f"  ⚠️  VERIFY FAIL: 'covariance_type full' still present!")
            if 'covariance_type diag' in txt:
                verifications += 1
            if 'init_params k-means' in txt and 'k-means++' not in txt:
                log(f"  ⚠️  VERIFY FAIL: 'init_params k-means' still present!")

        if verifications > 0:
            log(f"  ✅ Verified: {verifications}x 'covariance_type diag' present")

        # Check Abstrak sentence
        found_abstrak = False
        for ct in check_texts:
            if ct.text and '592 pendaftar yang diproyeksikan' in ct.text:
                found_abstrak = True
                break
        if found_abstrak:
            log(f"  ✅ Verified: Abstrak sentence present")
        else:
            log(f"  ⚠️  VERIFY FAIL: Abstrak sentence not found!")

        # Check 9Router paragraph cleared
        for ct in check_texts:
            if ct.text and 'Cloud Engine via proxy lokal 9Router' in ct.text:
                log(f"  ⚠️  VERIFY FAIL: 9Router text still present!")
                break
        else:
            log(f"  ✅ Verified: 9Router paragraph text cleared")

    except Exception as e:
        log(f"  ⚠️  Spot-check error: {e}")

    # === Summary ===
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Changes applied: {len(changes)}")
    for c in changes:
        log(f"  ✅ {c}")
    if warnings:
        log(f"Warnings ({len(warnings)}):")
        for w in warnings:
            log(f"  ⚠️  {w}")

    out_size = os.path.getsize(OUTPUT)
    log(f"Input size:  {input_size:,} bytes")
    log(f"Output size: {out_size:,} bytes")
    log(f"Input ZIP entries:  {in_count}")
    log(f"Output ZIP entries: {out_count}")
    log(f"Output: {OUTPUT}")
    log("Done.")

if __name__ == '__main__':
    main()
