#!/usr/bin/env python3
"""
update_bab3_hybrid.py — Memperbarui teks metodologi di BAB III 
untuk merefleksikan arsitektur "Hybrid Cognitive Pipeline".
"""

import sys
import os
import shutil
import re
from datetime import datetime
from docx import Document

from pipeline import utils

DOC = str(utils.get_doc_path())

def backup_file(path):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.replace(".docx", f"_BACKUP_{ts}.docx")
    shutil.copy2(path, bak)
    print(f"[BACKUP] → {bak}")
    return bak

def main():
    if not os.path.exists(DOC):
        print(f"[ERROR] File tidak ditemukan: {DOC}")
        return

    print("=" * 72)
    print("  update_bab3_hybrid.py  —  Sinkronisasi Hybrid Cognitive Pipeline")
    print("=" * 72)
    print()

    bak_path = backup_file(DOC)
    doc = Document(DOC)

    changes_made = 0
    
    TARGET_1 = "Model LLM: Ollama 0.1.0 LLM lokal (Llama 3.2 3B) dari keluarga Llama 3 ."
    REPLACE_1 = "Arsitektur Hybrid Cognitive Pipeline: Menggabungkan Llama 3.2 3B via Ollama (Lokal) untuk fase Privacy Gateway dan Persona Generation demi menjaga kerahasiaan data PII, serta OpenRouter (Cloud API) untuk model penalaran tingkat tinggi pada fase Causal Trend Analysis."

    TARGET_2 = "penggunaan LLM lokal (Ollama) yang memastikan data PMB tidak dikirim ke server pihak ketiga atau layanan cloud eksternal"
    REPLACE_2 = "penggunaan pendekatan Hybrid Cognitive Pipeline di mana data PII disanitasi sepenuhnya di lingkungan lokal (Ollama) sebelum insight anonim dikirim ke cloud untuk inferensi kausal tingkat lanjut"

    for i, p in enumerate(doc.paragraphs):
        text = p.text
        
        # Check target 1
        if "Model LLM: Ollama 0.1.0" in text:
            old_text = text
            new_text = re.sub(r"Model LLM: Ollama 0\.1\.0 LLM lokal \(Llama 3\.2 3B\) dari keluarga Llama 3 \.?", REPLACE_1, text)
            if new_text != old_text:
                for run in p.runs:
                    run.text = ""
                p.text = new_text
                changes_made += 1
                print(f"     ✓ Par[{i}] diperbarui untuk Arsitektur Hybrid.")

        # Check target 2
        if "tidak dikirim ke server pihak ketiga" in text:
            old_text = text
            new_text = text.replace(TARGET_2, REPLACE_2)
            if new_text == old_text:
                new_text = re.sub(r"penggunaan LLM lokal \(Ollama\) yang memastikan data PMB tidak dikirim ke server pihak ketiga atau layanan cloud eksternal", REPLACE_2, text)
            
            if new_text != old_text:
                for run in p.runs:
                    run.text = ""
                p.text = new_text
                changes_made += 1
                print(f"     ✓ Par[{i}] diperbarui untuk privasi data.")

    if changes_made > 0:
        doc.save(DOC)
        print(f"\n[SUKSES] Berhasil menerapkan {changes_made} perubahan pada {DOC}")
    else:
        print("\n[INFO] Tidak ada teks yang cocok untuk diubah (mungkin sudah diperbarui sebelumnya).")

if __name__ == "__main__":
    main()
