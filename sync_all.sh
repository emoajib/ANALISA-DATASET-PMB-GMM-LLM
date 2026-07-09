#!/bin/bash
set -e

echo "============================================================"
echo "  MASTER PIPELINE SINKRONISASI - TESIS ITSNU"
echo "============================================================"

# Domain 1: Data Analysis Pipeline
echo ""
echo "▶ [DOMAIN 1] Menjalankan Pipeline Analisis Data (CRISP-DM)"
echo "------------------------------------------------------------"
cd "DATASET/OLAH DATA"
# Run the pipeline
python3 src/pmb_pipeline.py
cd ../..
echo "✅ [DOMAIN 1] Analisis Data Selesai."

# Domain 4: Perakitan Dokumen Tesis (Assembly)
echo ""
echo "▶ [DOMAIN 4] Merakit Komponen Tesis (BAB I-V & Lampiran Kode)"
echo "------------------------------------------------------------"
cd "PENGERJAAN TESIS BAB I - BAB V"
python3 scripts/assemble_domain4.py
cd ..
echo "✅ [DOMAIN 4] Perakitan FULL TESIS FINAL.docx Selesai."

# Domain 2: Document Formatting Pipeline
echo ""
echo "▶ [DOMAIN 2] Menjalankan Validasi dan Format Dokumen (Panduan v3)"
echo "------------------------------------------------------------"
cd "PENGERJAAN TESIS BAB I - BAB V"
export PYTHONPATH=.
python3 pipeline/run.py "../FULL TESIS/FULL TESIS FINAL.docx" --mode thesis
cd ..
echo "✅ [DOMAIN 2] Pemformatan Tesis Selesai."

# Domain 3: Publikasi Jurnal
echo ""
echo "▶ [DOMAIN 3] Status Publikasi Jurnal RABIT"
echo "------------------------------------------------------------"
echo "🎉 LoA telah diterima. Jurnal penelitian sedang dalam antrean terbit."
echo "✅ [DOMAIN 3] Tersinkronisasi (Completed)."

echo ""
echo "============================================================"
echo "  SINKRONISASI 4 DOMAIN BERHASIL (100%)"
echo "  Output Akhir: FULL TESIS/FULL TESIS FINAL.docx"
echo "============================================================"
