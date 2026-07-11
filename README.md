# Strategi Segmentasi Probabilistik Calon Mahasiswa Menggunakan Gaussian Mixture Model dan Otomasi Analisis Large Language Model untuk Optimalisasi Rekrutmen di ITSNU Pekalongan

**Tesis — Magister Teknologi Informasi, Universitas Stikubank (UNISBANK) Semarang**

Penulis: Mujibul Hakim (25.01.85.7010)

---

## Abstrak

Penelitian ini mengembangkan strategi segmentasi probabilistik calon mahasiswa di ITSNU Pekalongan menggunakan Gaussian Mixture Model (GMM) dengan pipeline hybrid LLM (Llama 3.2 via Ollama + OpenRouter cloud fallback). Data historis 2019–2024 dianalisis dengan pipeline berbasis PCA + GMM (`covariance_type='tied'`, `reg_covar=0.1`). K optimal = 2 pada semua tahun — satu klaster mayoritas (98%+) dan satu minoritas (1–2%). Posterior probability 0,514–0,711 (2020–2024) mengkonfirmasi soft clustering non-degeneratif. Transisi antar tahun menunjukkan structural break (ARI −0.0102 s.d. −0.0037). Cosine similarity embedding rata-rata 0,8820. Proyeksi 2025: 592 pendaftar. Validasi pakar: 4,0/5.

---

## Struktur Proyek — 4 Domain

```
TESIS/
├── Domain 1: DATA
│   ├── DATASET/
│   │   └── DATASET PMB ITSNUPKL2019-2024_FIX.xls   ← data primer
│   └── data/
│       └── raw/PMB_2019_2024.xlsx                   ← data mentah
│
├── Domain 2: PIPELINE
│   ├── src/                                         ← kode modern (refactor)
│   │   ├── core/         (pipeline, modeling, preprocessor, dsb.)
│   │   ├── llm/          (provider, engines, registry)
│   │   ├── dashboard/    (streamlit dashboard)
│   │   └── scripts/      (regenerate_figures, run_pipeline, dsb.)
│   └── PENGERJAAN TESIS BAB I - BAB V/
│       ├── pipeline/     (run.py, config.py, utils.py)
│       ├── steps/        (20 script perbaikan naskah)
│       ├── scripts/      (utilitas assembly, update, dsb.)
│       ├── check/        (compliance checker)
│       └── utils/        (generator PPTX, Excel, dsb.)
│
├── Domain 3: NASKAH
│   ├── PENGERJAAN TESIS BAB I - BAB V/
│   │   ├── BAB I - BAB IV.docx      ← source BAB I–IV
│   │   └── BAB V.docx               ← source BAB V
│   └── FULL TESIS/
│       ├── FULL TESIS FINAL.docx    ← dokumen final (1,4 MB)
│       ├── Lembar_Temuan_Review_Tesis.docx
│       ├── Action_Plan_Revisi_Tesis.docx
│       └── TEMPLATE_*.docx
│
├── Domain 4: OUTPUT & PUBLIKASI
│   ├── PUBLIKASI/
│   │   ├── ARTIKEL_RABIT.docx       ← artikel jurnal
│   │   ├── LoA.pdf                  ← Letter of Acceptance
│   │   └── BUKTI FEE JURNAL RABIT.jpeg
│   └── PENGERJAAN TESIS BAB I - BAB V/reference/
│       └── referensi_pdf/           ← 38 PDF referensi
│
├── AGENTS.md                        ← konteks untuk AI agent
├── README.md                        ← file ini
└── sync_all.sh                      ← script sinkronisasi
```

---

## Teknologi

| Komponen | Tools |
|---|---|
| **Runtime** | Python 3.12 |
| **Clustering** | GMM (scikit-learn), PCA |
| **Embedding** | IndoBERT (huggingface) |
| **LLM** | Llama 3.2 via Ollama + OpenRouter (fallback) |
| **Dashboard** | Streamlit |
| **Dokumen** | Python-docx, docxcompose |
| **Analisis** | ARI, Cosine Similarity, Silhouette, BIC, ICL |

---

## Hasil Kunci

| Metrik | Nilai |
|---|---|
| K optimal (semua tahun) | 2 |
| Posterior probability (2020–2024) | 0,514 – 0,711 |
| ARI transisi | −0.0102 s.d. −0.0037 (structural break) |
| Cosine similarity rata-rata | 0,8820 |
| Silhouette score | 0,02 – 0,09 |
| Proyeksi 2025 | 592 pendaftar |
| Validasi pakar | 4,0 / 5,0 |

---

## Cara Menjalankan Pipeline

```bash
# Install dependencies
pip install -r requirements.txt

# Jalankan pipeline lengkap
python3 src/scripts/run_pipeline.py

# Regenerasi figur
python3 src/scripts/regenerate_figures.py

# Dashboard Streamlit
streamlit run src/dashboard/app.py
```

---

## Publikasi

- Artikel jurnal: `PUBLIKASI/ARTIKEL_RABIT.docx`
- Jurnal RABIT (Jurnal Riset dan Inovasi Teknologi)
- Status: **Accepted** (LoA tersedia)

---

## Lisensi

Hak cipta © 2026 Mujibul Hakim — Universitas Stikubank (UNISBANK) Semarang
