#!/usr/bin/env python3
"""
ai_polish.py — Polish academic language using Gemini AI.

Mengirim setiap BAB ke Gemini untuk review & perbaikan bahasa akademik.
Hanya memproses body teks (BAB I-V), melewati front matter & daftar pustaka.
"""

import argparse, copy, os, re, sys, time, shutil, tempfile, zipfile
from lxml import etree

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = f'{{{NS_W}}}'


def _qn(tag):
    return f'{W}{tag}'


def _para_text(elem):
    texts = [t.text for t in elem.iter(_qn('t')) if t.text]
    return ''.join(texts).strip()


def get_body_xml_index(docx_path):
    """Return list of (xml_index, lxml_element, text) for body paragraphs (BAB I-V only)."""
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read('word/document.xml')
    tree = etree.fromstring(xml)
    body = tree.find(_qn('body'))
    
    result = []
    in_bab1 = False
    in_daftar_pustaka = False
    
    xml_idx = -1
    for child in body:
        if child.tag != _qn('p'):
            continue
        xml_idx += 1
        text = _para_text(child)
        
        # Detect BAB I start
        pPr = child.find(_qn('pPr'))
        style_val = None
        if pPr is not None:
            ps = pPr.find(_qn('pStyle'))
            if ps is not None:
                style_val = ps.get(_qn('val'))
        
        is_heading = style_val and ('Judul' in style_val or 'Heading' in style_val)
        
        if is_heading and text.startswith('BAB ') and 'BAB I' in text:
            in_bab1 = True
        
        if text == 'DAFTAR PUSTAKA':
            in_daftar_pustaka = True
        
        if in_bab1 and not in_daftar_pustaka:
            result.append((xml_idx, child, text))
    
    return result


def chunk_by_bab(paragraphs):
    """Group paragraphs by BAB using (xml_idx, elem, text) tuples."""
    chunks = []
    current_bab = None
    current_chunk = []
    
    for xml_idx, elem, text in paragraphs:
        if text.startswith('BAB ') and not any(text.startswith(f'BAB {b} ini') for b in 'IVX'):
            if current_chunk:
                chunks.append((current_bab, current_chunk))
            current_bab = text
            current_chunk = [(xml_idx, elem, text)]
        else:
            current_chunk.append((xml_idx, elem, text))
    
    if current_chunk:
        chunks.append((current_bab, current_chunk))
    
    return chunks


POLISH_PROMPT = """Anda adalah editor akademik tesis S2 Bahasa Indonesia.
Tugas: perbaiki bahasa akademik paragraf demi paragraf.

ATURAN KETAT:
1. HANYA perbaiki: tata bahasa, ejaan, diksi, struktur kalimat, kohesi, istilah baku
2. JANGAN UBAH STRUKTUR PARAGRAF: satu paragraf input = satu paragraf output. Jangan tambah list, bullet, atau nomor, atau pemformatan markdown apapun.
3. JANGAN UBAH: konten teknis, data, angka, sitasi (Penulis, Tahun), nama metode/alat (GMM, IndoBERT, LLM, GeoPy, dll)
4. Pertahankan gaya akademik formal dan istilah baku Bahasa Indonesia
5. KELUARKAN TEKS POLOS SAJA — tanpa asterisk, tanpa markdown, tanpa formatting apapun.

Format output PERSIS untuk setiap paragraf:
===PARA N===
[satu paragraf hasil perbaikan — TEKS POLOS, tanpa formatting]

Jika sudah baik: ===PARA N=== (OK)

MULAI:
"""


def polish_with_gemini(client, model, bab_name, paragraphs):
    """Send a BAB's paragraphs to Gemini for polish."""
    # Build prompt — use XML index for mapping
    lines = []
    for xml_idx, elem, text in paragraphs:
        lines.append(f"===PARA {xml_idx}===\n{text}")
    
    full_prompt = POLISH_PROMPT + f"\n--- {bab_name} ---\n" + "\n".join(lines)
    
    print(f"  Sending {len(paragraphs)} paragraphs ({bab_name})...")
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config={
                'temperature': 0.3,
                'max_output_tokens': 32000,
            }
        )
        return response.text
    except Exception as e:
        print(f"  ❌ Gemini error: {e}")
        return None


def parse_polish_response(response_text, expected_paras):
    """Parse Gemini response into {index: new_text} dict."""
    results = {}
    current_idx = None
    current_lines = []
    ok_indices = set()
    
    for line in response_text.split('\n'):
        m = re.match(r'===PARA\s+(\d+)===', line)
        if m:
            if current_idx is not None:
                text = '\n'.join(current_lines).strip()
                if text:
                    results[current_idx] = text
                else:
                    ok_indices.add(current_idx)
            current_idx = int(m.group(1))
            current_lines = []
            # Check if next content is (OK)
            continue
        elif current_idx is not None and line.strip() == '(OK)':
            ok_indices.add(current_idx)
            current_idx = None
            current_lines = []
            continue
        
        if current_idx is not None:
            current_lines.append(line)
    
    # Last para
    if current_idx is not None:
        text = '\n'.join(current_lines).strip()
        if text:
            results[current_idx] = text
        else:
            ok_indices.add(current_idx)
    
    return results, ok_indices


def apply_polish(docx_path, all_improvements):
    """Apply polished text back into the DOCX — update existing run text, preserve formatting."""
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read('word/document.xml')
    
    tree = etree.fromstring(xml)
    body = tree.find(_qn('body'))
    
    # Collect all paragraphs with their XML indices
    para_elements = []
    for child in body:
        if child.tag == _qn('p'):
            para_elements.append(child)
    
    changes = 0
    for idx, new_text in all_improvements.items():
        if idx >= len(para_elements):
            continue
        elem = para_elements[idx]
        
        # Find existing runs
        existing_runs = list(elem.findall(_qn('r')))
        if not existing_runs:
            continue
        
        # Update the FIRST existing run's text with the polished version
        first_run = existing_runs[0]
        t_elem = first_run.find(_qn('t'))
        if t_elem is not None:
            t_elem.text = new_text
        else:
            # Create new t element
            new_t = etree.SubElement(first_run, _qn('t'))
            new_t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            new_t.text = new_text
        
        # Remove additional runs (keep only first)
        for extra_run in existing_runs[1:]:
            elem.remove(extra_run)
        
        changes += 1
    
    # Write back
    with zipfile.ZipFile(docx_path) as z:
        data = {n: z.read(n) for n in z.namelist()}
    
    data['word/document.xml'] = etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
    
    fd, tmp = tempfile.mkstemp(suffix='.docx')
    os.close(fd)
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, content in data.items():
            zout.writestr(name, content)
    shutil.move(tmp, docx_path)
    
    return changes


def main():
    parser = argparse.ArgumentParser(description='AI polish thesis academic language')
    parser.add_argument('docx', help='Path ke DOCX thesis')
    parser.add_argument('--model', default='gemini-2.5-flash', help='Gemini model')
    parser.add_argument('--bab', help='Hanya proses BAB tertentu (I, II, III, IV, V)')
    args = parser.parse_args()
    
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY tidak ditemukan. Set dulu: export GOOGLE_API_KEY=...")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("AI POLISH — Academic Language Review")
    print(f"{'='*60}")
    print(f"Model: {args.model}")
    
    # Import google genai
    try:
        import google.genai as genai
    except ImportError:
        print("❌ google.genai tidak terinstall. Jalankan: pip install google-genai")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    # Get paragraphs
    print(f"\nReading: {args.docx}")
    paragraphs = get_body_xml_index(args.docx)
    print(f"Body paragraphs found: {len(paragraphs)}")
    
    if not paragraphs:
        print("❌ Tidak ada body paragraphs (BAB I-V)")
        sys.exit(1)
    
    # Chunk by BAB
    chunks = chunk_by_bab(paragraphs)
    print(f"BAB sections: {len(chunks)}")
    
    # Filter by BAB if specified
    if args.bab:
        bab_map = {'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4}
        target = bab_map.get(args.bab.upper())
        if target is not None and target < len(chunks):
            chunks = [chunks[target]]
            print(f"  Filtered to BAB {args.bab}")
        else:
            print(f"⚠️  BAB {args.bab} not found")
    
    # Process each BAB
    all_improvements = {}
    total_ok = 0
    
    for bab_name, bab_paras in chunks:
        print(f"\n{'─'*50}")
        
        result = polish_with_gemini(client, args.model, bab_name, bab_paras)
        if not result:
            print(f"  ⚠️  Skipping {bab_name} (error)")
            continue
        
        improvements, ok_indices = parse_polish_response(result, bab_paras)
        
        print(f"  Improved: {len(improvements)} / {len(bab_paras)} paragraphs")
        total_ok += len(ok_indices)
        
        all_improvements.update(improvements)
        
        # Rate limit protection
        time.sleep(1)
    
    # Apply changes
    if all_improvements:
        print(f"\n{'─'*50}")
        print(f"Applying {len(all_improvements)} improvements to DOCX...")
        
        # Make backup
        import shutil as sh
        backup = args.docx.replace('.docx', '_before_polish.docx')
        sh.copy2(args.docx, backup)
        print(f"  Backup: {backup}")
        
        changes = apply_polish(args.docx, all_improvements)
        print(f"  ✅ {changes} paragraphs updated")
    else:
        print(f"\n  ℹ️  No improvements to apply")
    
    print(f"\n{'='*60}")
    print(f"AI POLISH COMPLETE")
    print(f"  Total paragraphs reviewed: {len(paragraphs)}")
    print(f"  Improved: {len(all_improvements)}")
    print(f"  Already good: {total_ok}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
