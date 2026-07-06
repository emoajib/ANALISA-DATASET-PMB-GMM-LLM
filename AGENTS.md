# TESIS ITSNU UNISBANK — Master Project Knowledge Base
## Strategi Segmentasi Probabilistik Calon Mahasiswa Menggunakan GMM + Otomasi LLM

> **Peneliti:** Mujibul Hakim (NIM 25.01.85.7010)
> **Program:** S2 Magister Teknologi Informasi — Universitas Stikubank (UNISBANK) Semarang
> **Institusi:** ITSNU Pekalongan
> **Judul:** Hybrid Pipeline IndoBERT–GMM–LLM Time Series untuk Optimalisasi Rekrutmen

---

## 🗺️ Ecosystem Map — DUA DOMAIN

```
TESIS/                                    ← ROOT
├── AGENTS.md                             ← THIS FILE (master context)
├── .gitignore                            ← Git ignore rules
│
├── DATASET/                              ← DOMAIN 1: Data Analysis Pipeline
│   ├── OLAH DATA/
│   │   ├── src/app.py                    ← Streamlit dashboard (671 lines)
│   │   ├── src/pmb_pipeline.py           ← CRISP-DM engine (1254 lines)
│   │   ├── requirements.txt              ← Python ML stack (12 deps)
│   │   └── outputs/                      ← 18 CSV tables + 5 chart sets
│   └── RAW DATA + OUTPUT_DTA/
│
├── PENGERJAAN TESIS BAB I - BAB V/       ← DOMAIN 2: Document Pipeline
│   ├── pipeline/run.py                   ← Master pipeline runner
│   ├── steps/*.py                        ← 15 fix scripts
│   ├── check/check_pedoman.py            ← Compliance checker (65 rules)
│   ├── reference/
│   │   ├── referensi_MENDELEY_OPTIMIZED.bib  ← BibTeX (35 entries)
│   │   └── referensi_pdf/                ← 35 PDFs (source citations)
│   ├── Tesis_ITSNU_v11_Final.docx        ← PRODUCTION DOCUMENT
│   └── docs/AGENTS.md                    ← Domain-specific context
│
├── ANALISA-DATASET-PMB-GMM-LLM/          ← Git repo (deployed version)
│
└── _BACKUP_TESIS_20260701/               ← External backup (outside project)
```

### Backup Location
Backup dipindahkan ke luar project:
```
/Volumes/WORK/MTI UNSIBANK/_BACKUP_TESIS_20260701/
├── root/              ← otomatis_cleanup.py, otomatis_pasca.py, config.json
├── docx/              ← v10 backups, temp files, FRONT_MATTER draft, Pedoman v1.7, Randi Afif examples
├── legacy/            ← DATASET/_LEGACY/
├── dataset_backup/    ← DATASET_BACKUP_20260623_214348/
├── archived/          ← PENGERJAAN/archived/
├── backup/            ← PENGERJAAN/backup/
├── SUMBER JURNAL/     ← 1 PDF (not cited)
└── RUJUKAN/           ← 1 PDF (identical to referensi_pdf/06_...)
```

---

## 🔬 DOMAIN 1 — Data Analysis Pipeline

### Stack
| Component | Version | Role |
|-----------|---------|------|
| Python | 3.8+ | Runtime |
| Streamlit | 1.32.0 | Dashboard UI |
| Scikit-learn | 1.4.2 | GMM, PCA, metrics |
| PyTorch | 2.2.2 | IndoBERT inference |
| Transformers | 4.39.3 | indobenchmark/indobert-base-p1 |
| Ollama | 0.1.9 | LLM local inference |
| GeoPy | 2.4.1 | Geocoding Indonesia |
| Matplotlib | 3.8.4 | Visualization |

### Working Directory
```
/Volumes/WORK/MTI UNSIBANK/TESIS/DATASET/OLAH DATA/
```

### Commands
```bash
cd DATASET/OLAH\ DATA/

# Install dependencies
pip install -r requirements.txt

# Run dashboard (requires Ollama running)
streamlit run src/app.py

# Run pipeline standalone (no UI)
python3 src/pmb_pipeline.py

# Verify demo readiness (Streamlit Cloud mode)
python3 src/verify_demo.py

# Generate persona comparison across providers
python3 src/generate_comparison.py
```

### Architecture
- **CRISP-DM 10 Tahap** embedded in `PMBAnalysisPipeline` class
- **IndoBERT** for 768D semantic embeddings (name + school + address + regency)
- **GMM** per period (2019–2024) with K-scan (BIC/AIC/Silhouette)
- **Time Series** stability: ARI, Jaccard Similarity, Centroid Drift
- **LLM Multi-Provider**: Ollama (local), Gemini CLI, Kilo CLI, OpenCode CLI
- **Caching**: Embedding (35MB JSON, tracked), LLM responses (158KB, tracked)

### Output Files (BAB IV Aligned)
| # | File | BAB IV Ref |
|---|------|------------|
| 1 | `tabel_4_1_distribusi.csv` | T4.1 |
| 2 | `tabel_4_2_prodi.csv` | T4.2 |
| 3 | `tabel_4_3_preprocessing.csv` | T4.3 |
| 4 | `tabel_4_4_cosine_similarity.csv` | T4.4 |
| 5 | `tabel_4_5_kscan.csv` | T4.5 |
| 6 | `tabel_4_6_ari.csv` | T4.6 |
| 7 | `tabel_4_7_evaluasi_internal.csv` | T4.7 |
| 8–13 | `tabel_4_9–14_profil_YYYY.csv` | T4.9–14 |
| 14 | `tabel_4_15_lifecycle.csv` | T4.15 |
| 15 | `tabel_4_16_prioritasi_2025.csv` | T4.16 |
| 16 | `tabel_4_17_rekomendasi_channel.csv` | T4.17 |
| 17 | `tabel_4_18_perbandingan.csv` | T4.18 |
| — | `gambar_4_*` (5 sets) | G4.1–4.5 |

### CI/CD
- **GitHub Actions**: `.github/workflows/test.yml`
- Tests: syntax check, import test, unit test, state guard
- Demo mode: Streamlit Cloud (no Ollama required, uses pre-generated cache)

---

## 📄 DOMAIN 2 — Document Pipeline

### Stack
| Component | Version | Role |
|-----------|---------|------|
| Python | 3.8+ | Runtime |
| python-docx | 1.2.0 | DOCX manipulation |
| lxml | (transitive) | XML-level fixes |

### Working Directory
```
/Volumes/WORK/MTI UNSIBANK/TESIS/PENGERJAAN TESIS BAB I - BAB V/
```

### Commands
```bash
cd "PENGERJAAN TESIS BAB I - BAB V/"

# Full pipeline (A→H + Z + compliance check)
python3 pipeline/run.py Tesis_ITSNU_v11_Final.docx --mode thesis

# BAB I–IV inline pipeline
python3 pipeline/run.py "BAB I - BAB IV.docx"

# Compliance check (Panduan v3, 65 rules A–Z)
python3 check/check_pedoman.py Tesis_ITSNU_v11_Final.docx

# Individual steps (run as needed)
python3 steps/fix_bibliography.py <file.docx>
python3 steps/fix_structure.py <file.docx>
python3 steps/fix_tables.py <file.docx>
python3 steps/fix_remaining.py <file.docx>
python3 steps/fix_compliance.py <file.docx>
python3 steps/fix_paragraphs.py <file.docx> --step all
python3 steps/fix_postprocess.py <file.docx> --front-matter FRONT_MATTER_DRAFT.docx --bib reference/referensi_MENDELEY_OPTIMIZED.bib
python3 steps/fix_merge_paragraphs.py <file.docx>
python3 steps/fix_pakar_label.py <file.docx>
python3 steps/fix_italic_foreign.py <file.docx>
python3 steps/fix_bab5_duplicates.py <file.docx>
python3 steps/clean_artifacts.py <file.docx>
python3 steps/generate_references.py <file.docx>
python3 steps/heading_split.py <file.docx>
python3 steps/ai_polish.py <file.docx>
python3 steps/merge_frontmatter.py <file.docx>
```

### Pipeline Flow (Thesis Mode)
```
run.py → Backup → A.Bibliography → B.Structure → C.Tables →
D.Remaining → E.Postprocess(TOC+ABSTRAK+frontmatter) →
F.Re-fix Structure → G.Re-fix Remaining → H.Final Compliance →
Z.Direct-XML(Margins+Outline+BibSpacing) → Check Pedoman
```

### Key Files
| File | Role |
|------|------|
| `Tesis_ITSNU_v11_Final.docx` | **PRODUCTION DOC** (12,275 words, 28 bib, 10 APA cites) |
| `pipeline/run.py` | Master pipeline orchestrator |
| `pipeline/config.py` | Centralized format constants (v3) |
| `pipeline/utils.py` | Shared helpers (load_docx, find_daftar_pustaka, etc.) |
| `check/check_pedoman.py` | Compliance checker (65 checks, Panduan v3) |
| `reference/referensi_MENDELEY_OPTIMIZED.bib` | BibTeX database (35 entries) |
| `front_matter/FRONT_MATTER_DRAFT.docx` | Cover, pengesahan, abstrak template |
| `docs/PANDUAN_V3_TEKS.txt` | Extracted text of Panduan v3 (reference) |

### Document Current State
| BAB | Words | Citations | Status |
|-----|-------|-----------|--------|
| BAB I | 1,500 | 4 | ✅ |
| BAB II | 2,522 | 6 | ✅ |
| BAB III | 1,573 | 5 | ✅ |
| BAB IV | 5,141 | 3 | ✅ |
| BAB V | 654 | 3 | ✅ |
| **Total** | **12,275** | **10 APA** | **✅** |

- **Compliance**: 64/65 PASS (98.5%)
- **Bibliography**: 28 entries, sorted, hanging indent, 1 spasi
- **Tables**: 32 | **Images**: 13 | **OMML Equations**: 12

---

## 📏 Format Rules — Panduan Tesis v3 (Agustus 2025)

| Rule | Value | Enforcement |
|------|-------|-------------|
| Paper | A4 (21×29.7 cm) | Section margins in config.py |
| Margins | 4-3-4-3 cm (T-B-L-R) | `step_z_direct_xml()` |
| Font body | Times New Roman 12pt | `fix_remaining.py` |
| Font table | TNR 10pt | `fix_remaining.py` |
| Font abstrak | TNR 12pt (↑ from v1.7 11pt) | config.py |
| Line spacing body | 2 spasi (line=480) | config.py |
| Line spacing bibliography | 1 spasi (line=240) | `step_z_direct_xml()` |
| Space before/after | Must be 0 | `fix_compliance.py` |
| Justification | Rata kanan-kiri | `fix_compliance.py` |
| First-line indent | 720 twips | `fix_paragraphs.py` |
| Heading | Bold, Roman numerals (BAB I, II, ...) | `fix_structure.py` |
| Sub-bab | x.y format (4.1, 4.2, ...) | `fix_structure.py` |
| Decimal | Koma (,) bukan titik (.) | Manual |
| Equations | Native OMML | Manual in Word |
| Color | Black/auto only | `fix_compliance.py` |
| Italic | Greek, "et al.", Latin phrases | `fix_italic_foreign.py` |
| Citations | APA parenthetical (target ≥10) | `fix_bibliography.py` |
| Tables | Top/bottom/insideH border | `fix_tables.py` |
| Cover | Judul 2 bahasa, NIM, ID Tesis | Front matter (manual) |
| Referensi | Maksimal 5 tahun terakhir | `generate_references.py` |
| BAB V | Simpulan + Saran (Keterbatasan opsional) | config.py |

### Changes from v1.7 → v3
- Abstrak font: 12pt (was 11pt)
- Tabel/gambar spacing: 1 spasi (was 3)
- Space before/after: Must be 0 (new)
- BAB V Keterbatasan: Opsional (was wajib)
- Penomoran halaman: Kanan bawah
- Cover: 2 bahasa (was 1)
- Referensi: Maks 5 tahun (new)

---

## 📋 Coding Rules

1. **SEBELUM edit kode pipeline**: Jalankan `python3 check/check_pedoman.py` dulu — tahu baseline
2. **Jangan gunakan API deprecated**: python-docx API menyesuaikan versi, cek docs
3. **Setelah edit step**: Jalankan step individu dulu, baru full pipeline
4. **Backup otomatis**: Pipeline selalu buat backup sebelum modifikasi
5. **Config-driven**: Semua format constants di `pipeline/config.py` — jangan hardcode
6. **ORPHAN_MARKS**: Hati-hati — hanya author yang benar-benar tidak ada di Bibliography
7. **Cache management**: Embedding cache (35MB) dan LLM cache (158KB) di-track di git
8. **Naming convention**: Output harus align BAB IV (`tabel_4_X`, `gambar_4_X`)

---

## 🔗 Domain Interconnections

```
Domain 1 (Data Analysis)          Domain 2 (Document)
┌──────────────────────┐          ┌──────────────────────┐
│ 18 CSV tables ───────────────→ Tabel di BAB IV       │
│ 5 chart sets  ───────────────→ Gambar di BAB IV       │
│ CRISP-DM flow  ──────────────→ BAB III Methodology    │
│ Hypothesis H1-H3 ───────────→ BAB IV Analysis        │
│ GMM results    ──────────────→ BAB IV Results         │
│ LLM personas   ──────────────→ BAB IV Discussion      │
│ Proyeksi 2025  ──────────────→ BAB V Recommendations  │
└──────────────────────┘          └──────────────────────┘
         │                                  │
         └──── Outputs feed Document ───────┘
              Pipeline absorbs them into DOCX
```

**Key insight**: Domain 1 GENERATES the data (tables, charts, narratives). Domain 2 FORMATS them into the thesis document following Panduan v3.

---

## 🚨 Known Issues & TODO

### Domain 1 (Data Analysis)
- [ ] Ollama dependency — Demo mode works without it, but full LLM needs local server
- [ ] Embedding cache is 35MB tracked — consider `.gitignore` for large repos
- [ ] `ANALISA-DATASET-PMB-GMM-LLM/` vs `DATASET/OLAH DATA/` duplication (unmanaged)

### Domain 2 (Document Pipeline)
- [ ] **1 compliance failure**: ABSTRAK heading in Judul1 style (front matter not yet integrated)
- [ ] Front matter (cover, pengesahan, abstrak, kata pengantar, daftar isi) — manual in Word
- [ ] Page count ~16 hal (target 150-200) — low because front matter & appendices not included
- [ ] After full formatting estimated ~80-100 hal (still below 150 target)

### Shared
- [ ] 13x `sys.path.insert()` — struktur import rapuh (jangan diubah sekarang)
- [ ] macOS-specific: AppleScript untuk TOC, font paths hardcoded
- [ ] Backup dipindahkan ke `/Volumes/WORK/MTI UNSIBANK/_BACKUP_TESIS_20260701/`

---

## 🏗️ Architecture Decisions (Trade-offs)

| Decision | Choice | Why | Trade-off |
|----------|--------|-----|-----------|
| Single AGENTS.md at root | ✅ | Fast onboarding for any AI agent | Less detail per domain |
| Separate pipelines | ✅ | Different stacks, different concerns | Duplication of context |
| Config-driven formatting | ✅ | Single source of truth for v3 rules | Must update config.py first |
| LLM cache in git | ✅ | Demo mode reproducibility | +158KB per clone |
| Embedding cache in git | ✅ | Skip 35MB IndoBERT recomputation | Repo bloat |
| `check_pedoman.py` as gate | ✅ | Automated compliance | 65 checks may miss edge cases |
| Backup outside project | ✅ | Prevents 1GB bloat in project tree | Manual access path |
| `.gitignore` at root | ✅ | Prevent accidental commits of backups/temp | — |

---

## 🎯 Defense Readiness Checklist

- [x] BAB I–V content complete (12,275 words)
- [x] 28 bibliography entries
- [x] 10 APA parenthetical citations
- [x] 32 tables, 13 images, 12 equations
- [x] Compliance 64/65 (98.5%)
- [x] Data pipeline outputs 18 tables + 5 charts
- [ ] Front matter integration (cover, pengesahan, abstrak)
- [ ] Final page count 150-200 hal
- [ ] Equation & image placement in Word
- [ ] AI content polish (needs Gemini API key)

---

*Last updated: 2026-07-01 | Pipeline v11 | Compliance 64/65 | Cleanup: 7543 files archived outside project*
