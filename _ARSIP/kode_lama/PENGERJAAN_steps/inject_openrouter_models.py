#!/usr/bin/env python3
"""
inject_openrouter_models.py — Memperbarui teks tesis untuk memasukkan rincian model OpenRouter.
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
    bak = path.replace(".docx", f"_BACKUP_INJECT_{ts}.docx")
    shutil.copy2(path, bak)
    print(f"[BACKUP] → {bak}")
    return bak

def main():
    if not os.path.exists(DOC):
        print(f"[ERROR] File tidak ditemukan: {DOC}")
        return

    print("=" * 72)
    print("  inject_openrouter_models.py  —  Injeksi Detail OpenRouter")
    print("=" * 72)

    bak_path = backup_file(DOC)
    doc = Document(DOC)
    changes_made = 0
    
    TEXT_BAB2_APPEND = (
        " Penelitian ini mengadopsi pendekatan Multi-Model Fallback menggunakan arsitektur Hybrid Cognitive Pipeline. "
        "Hasil penalaran kausal dan narasi akhir tidak hanya bergantung pada satu model, melainkan mensintesis kemampuan penalaran tingkat tinggi dari cloud engine melalui API OpenRouter. "
        "Model utama yang diandalkan adalah meta-llama/llama-3.3-70b-instruct yang menawarkan efisiensi tinggi, didukung oleh sistem fallback otomatis menggunakan model berkapasitas sangat besar dari NVIDIA, yaitu nvidia/nemotron-3-ultra-550b-a55b dan nvidia/nemotron-3-super-120b-a12b. "
        "Penggunaan orkestrasi multi-model ini menjamin ketersediaan (menghindari limitasi server) serta keandalan validitas output analitik EDM yang stabil."
    )

    TARGET_BAB3 = "(2) Cloud Engine OpenRouter API yang mengakses model-model penalaran tingkat tinggi (hingga 550B parameter) untuk tugas yang memerlukan reasoning kompleks"
    REPLACE_BAB3 = "(2) Cloud Engine OpenRouter API yang mengakses model-model penalaran tingkat tinggi secara berjenjang (cascade fallback), meliputi meta-llama/llama-3.3-70b-instruct sebagai model utama, serta nvidia/nemotron-3-ultra-550b-a55b dan nvidia/nemotron-3-super-120b-a12b sebagai model cadangan untuk memastikan keberhasilan tugas reasoning kompleks"

    for i, p in enumerate(doc.paragraphs):
        text = p.text

        # 1. BAB II - Sintesis Gap
        if "Sintesis Gap: Berdasarkan Tabel 2.4" in text and "Penelitian ini mengisi kesenjangan tersebut secara komprehensif." in text:
            if "Multi-Model Fallback" not in text:
                new_text = text + TEXT_BAB2_APPEND
                for run in p.runs:
                    run.text = ""
                p.text = new_text
                changes_made += 1
                print(f"     ✓ Par[{i}] BAB II diperbarui dengan kajian teori multi-model.")

        # 2. BAB III - Arsitektur Hybrid
        if TARGET_BAB3 in text:
            new_text = text.replace(TARGET_BAB3, REPLACE_BAB3)
            for run in p.runs:
                run.text = ""
            p.text = new_text
            changes_made += 1
            print(f"     ✓ Par[{i}] BAB III diperbarui dengan rincian model OpenRouter.")

        # 3. BAB IV - Pembahasan (default: ...)
        if "(default: meta-llama/llama-3.3-70b-instruct)" in text:
            new_text = text.replace(
                "(default: meta-llama/llama-3.3-70b-instruct)", 
                "(mensintesis output dari meta-llama/llama-3.3-70b-instruct, nvidia/nemotron-3-ultra-550b-a55b, dan nvidia/nemotron-3-super-120b-a12b)"
            )
            for run in p.runs:
                run.text = ""
            p.text = new_text
            changes_made += 1
            print(f"     ✓ Par[{i}] BAB IV diperbarui dengan multi-model.")
            
        # 3b. BAB IV - Gambar Caption
        if "(meta-llama/llama-3.3-70b-instruct) dengan fallback ke Llama 3.2 3B lokal" in text:
            new_text = text.replace(
                "(meta-llama/llama-3.3-70b-instruct) dengan fallback ke Llama 3.2 3B lokal",
                "(meta-llama/llama-3.3-70b-instruct dan nemotron-3-ultra) dengan fallback ke Llama 3.2 lokal"
            )
            for run in p.runs:
                run.text = ""
            p.text = new_text
            changes_made += 1
            print(f"     ✓ Par[{i}] BAB IV Caption diperbarui dengan multi-model.")

    if changes_made > 0:
        doc.save(DOC)
        print(f"\n[SUKSES] Berhasil menerapkan {changes_made} perubahan pada {DOC}")
    else:
        print("\n[INFO] Tidak ada teks yang cocok untuk diubah (mungkin sudah diperbarui sebelumnya).")

if __name__ == "__main__":
    main()
