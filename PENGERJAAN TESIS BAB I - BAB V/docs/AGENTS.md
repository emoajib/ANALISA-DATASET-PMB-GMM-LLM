# TESIS ITSNU — Document Pipeline Context

> **Domain:** Document Formatting & Compliance Pipeline
> **See also:** `../../AGENTS.md` — Master project context (covers both domains)

## Project
Tesis S2 Magister Teknologi Informasi, Universitas Stikubank (UNISBANK) Semarang.
Judul: **Strategi Segmentasi Probabilistik Calon Mahasiswa Menggunakan Hybrid Pipeline IndoBERT–GMM–LLM Time Series** (ITSNU Pekalongan).
Penulis: Mujibul Hakim (NIM 25.01.85.7010).

## Working Directory
```
/Volumes/WORK/MTI UNSIBANK/TESIS/PENGERJAAN TESIS BAB I - BAB V/
```

## Quick Start
```bash
# Full pipeline (after major edits)
python3 pipeline/run.py Tesis_ITSNU_v11_Final.docx --mode thesis

# Compliance check only
python3 check/check_pedoman.py Tesis_ITSNU_v11_Final.docx
```

## Key Files

| File | Description |
|------|-------------|
| `Tesis_ITSNU_v11_Final.docx` | **PRODUCTION** — BAB I–V + Daftar Pustaka (12,275 words) |
| `BAB I - BAB IV_final_fixed_comprehensive.docx` | BAB I–IV version (before BAB V) |
| `BAB I - BAB IV.docx` | Original source BAB I–IV |
| `docs/panduan tesis v3.pdf` | **Format guidelines v3 (Agustus 2025)** — 56 pages |
| `docs/PANDUAN_V3_TEKS.txt` | Extracted text of v3 (1454 lines, 50KB) |
| `docs/HASIL_KEPATUHAN_PEDOMAN.txt` | Latest compliance output |
| `check/check_pedoman.py` | Compliance checker (65 checks A–Z, v3) |
| `pipeline/run.py` | **MASTER PIPELINE** — orchestrator A→Z |
| `pipeline/config.py` | Centralized constants (format, BAB V sections) |
| `pipeline/utils.py` | Shared helpers (load_docx, find_daftar_pustaka) |
| `steps/*.py` | 15 fix scripts (see Pipeline Flow below) |
| `reference/referensi_MENDELEY_OPTIMIZED.bib` | BibTeX database (35 entries) |
| `front_matter/FRONT_MATTER_DRAFT.docx` | Cover/pengesahan/abstrak template |

## Pipeline Flow (Thesis Mode)
```
run.py
 ├── [Backup] Tesis_ITSNU_v11_Final_BACKUP.docx
 │
 ├── A. fix_bibliography.py     — Clean, sort, hanging indent
 ├── B. fix_structure.py        — Heading styles, outline levels, alignment
 ├── C. fix_tables.py           — Borders, caption merge
 ├── D. fix_remaining.py        — Line spacing, italic, table font
 ├── E. fix_postprocess.py      — ABSTRAK, placeholders, TOC + front matter
 ├── F. fix_structure.py        — Re-fix post-TOC
 ├── G. fix_remaining.py        — Re-fix post-TOC
 ├── H. fix_compliance.py       — Margins, justify, headings
 │
 ├── Z. step_z_direct_xml()     — Direct XML: margins, outline levels,
 │                                bib spacing, caption spacing, dup ABSTRAK
 │
 └── check_pedoman.py           — 65-rule compliance gate
```

## Individual Steps
```bash
python3 steps/fix_bibliography.py [file.docx]
python3 steps/fix_structure.py [file.docx]
python3 steps/fix_tables.py [file.docx]
python3 steps/fix_remaining.py [file.docx]
python3 steps/fix_compliance.py [file.docx]
python3 steps/fix_paragraphs.py [file.docx] --step all
python3 steps/fix_postprocess.py [file.docx] --front-matter FRONT_MATTER_DRAFT.docx --bib reference/referensi_MENDELEY_OPTIMIZED.bib
python3 steps/fix_merge_paragraphs.py [file.docx]
python3 steps/fix_pakar_label.py [file.docx]
python3 steps/fix_italic_foreign.py [file.docx]
python3 steps/fix_bab5_duplicates.py [file.docx]
python3 steps/clean_artifacts.py [file.docx]
python3 steps/generate_references.py [file.docx]
python3 steps/heading_split.py [file.docx]
python3 steps/ai_polish.py [file.docx]
python3 steps/merge_frontmatter.py [file.docx]
```

## Document Current State (Tesis_ITSNU_v11_Final.docx)

### Compliance: 64/65 PASS (98.5%)
| # | Rule | Status |
|---|------|--------|
| A–Z | 65 checks (font, spacing, margins, headings, citations, etc.) | 64 ✅ / 1 ❌ |
| ❌ | ABSTRAK heading uses Judul1 style | Front matter not yet integrated |

### Content Summary
| BAB | Words | Citations | Status |
|-----|-------|-----------|--------|
| BAB I | 1,500 | 4 | ✅ |
| BAB II | 2,522 | 6 | ✅ |
| BAB III | 1,573 | 5 | ✅ |
| BAB IV | 5,141 | 3 | ✅ |
| BAB V | 654 | 3 | ✅ |
| **Total** | **12,275** | **10 APA** | **✅** |

### Structure
- Sections: 2 | Tables: 32 | Images: 13 | OMML equations: 12
- Bibliography: **28 entries** (sorted, hanging indent, 1 spasi ✅)
- APA citations: **10 parenthetical** (target ≥10 ✅)

### BAB V Sections
- 5.1 Simpulan — 4 kesimpulan menjawab rumusan masalah
- 5.2 Implikasi — teoretis + praktis
- 5.3 Keterbatasan Penelitian — 4 keterbatasan
- 5.4 Saran — 4 saran (metodologis + praktis + pengembangan + riset)

## Format Rules (Panduan v3 — Agustus 2025)

| Rule | Value | Config Source |
|------|-------|---------------|
| Paper | A4 (21×29.7 cm) | config.py `PAPER_SIZE` |
| Margins | 4-3-4-3 cm (T-B-L-R) | config.py `MARGIN_*` |
| Font body | TNR 12pt | config.py `FONT_SIZE_BODY` |
| Font table | TNR 10pt | config.py `FONT_SIZE_TABLE` |
| Font abstrak | TNR 12pt (↑ from v1.7 11pt) | config.py `FONT_SIZE_ABSTRAK` |
| Line spacing body | 2 spasi (line=480) | config.py `LINE_SPACING_BODY` |
| Line spacing bib | 1 spasi (line=240) | config.py `LINE_SPACING_BIB` |
| Line spacing caption | 1 spasi (line=240) | config.py `LINE_SPACING_CAPTION` |
| Space before/after | Must be 0 | config.py `SPACE_*_BODY` |
| Justification | Rata kanan-kiri | fix_compliance.py |
| First-line indent | 720 twips | config.py `FIRST_LINE_INDENT` |
| Hanging indent | 720 twips | config.py `HANGING_INDENT` |
| Heading | Bold, Roman numerals | fix_structure.py |
| Sub-bab | x.y format | fix_structure.py |
| Decimal | Koma (,) not titik (.) | Manual |
| Equations | Native OMML | Manual |
| Color | Black/auto only | fix_compliance.py |
| Italic | Greek, "et al.", Latin | fix_italic_foreign.py |
| Citations | APA (target ≥10) | fix_bibliography.py |
| Tables | Top/bottom/insideH border | fix_tables.py |
| Referensi | Maks 5 tahun terakhir | generate_references.py |
| BAB V | Simpulan + Saran only | config.py `BAB5_*` |

### ORPHAN_MARKS (Bibliography filter)
Current: `['Rai, K. D.']`
⚠️ Only add entries here if author truly has no corresponding bibliography entry. `Hossler, D.` was removed (was false positive — real Hossler entry exists).

## Known Issues
1. **1 compliance failure**: ABSTRAK heading in Judul1 style — needs front matter integration
2. **Front matter** (cover, pengesahan, abstrak, kata pengantar, daftar isi) — must be done manually in Word
3. **Page count** ~16 hal currently — dramatically low because front matter, appendices, and deep formatting not included
4. **Target pages**: ~80-100 after full formatting (below 150 target — needs appendices)

## Recent Changes (Session 2026-06-30)
- Added 3 bibliography entries: Shearer (2000), Shmueli et al. (2016), Hossler & Gallagher (1987) → 28 total
- Added 3 parenthetical citations → 10 APA total
- Fixed orphan detection bug (Hossler, D. false positive)
- Fixed body spacing (270 paragraphs), justification (70), outline levels (83)
- Fixed bib line spacing (28 entries → line=240), captions (7 entries → line=240)
- Fixed Gambar captions centering (24 captions)
- Updated check_pedoman.py: accepts "5.1 Simpulan" and "5.4 Saran" alternatives

## Pipeline Changes Log
- `steps/fix_bibliography.py` — DAFTAR PUSTAKA detection uses startswith; ORPHAN_MARKS reduced
- `pipeline/utils.py` — find_daftar_pustaka() uses startswith
- `pipeline/config.py` — ORPHAN_MARKS reduced; BAB V constants added
- `check/check_pedoman.py` — accepts alternative headings; BAB V content checks
- `steps/generate_references.py` — REFERENCE_DB: 28 entries; generates from BibTeX
- `reference/referensi_MENDELEY_OPTIMIZED.bib` — 35 total entries (28 + 7 extras)

## Dependencies
```
python-docx==1.2.0
lxml (transitive)
```
Install: `pip install python-docx==1.2.0`

## Coding Rules (Document Pipeline)
1. **SEBELUM edit step script**: Run `check_pedoman.py` dulu — tahu baseline
2. **Config-driven**: Semua format constants di `pipeline/config.py` — jangan hardcode
3. **Backup otomatis**: Pipeline selalu buat backup sebelum modifikasi
4. **Step order matters**: Steps A–D are order-dependent; E triggers TOC rebuild
5. **ORPHAN_MARKS**: Hati-hati — hanya author yang benar-benar tidak ada di Bibliography
6. **BAB V**: Only Simpulan + Saran required; Keterbatasan is optional per v3

## Data Flow from Domain 1
Domain 1 (Data Analysis Pipeline) produces outputs that feed into this document:
- `outputs/tabel_4_*.csv` → Tables 4.1–4.18 in BAB IV
- `outputs/gambar_4_*` → Figures 4.1–4.5 in BAB IV
- LLM persona narratives → Discussion sections
- GMM analysis results → BAB IV Results section

---

*Last updated: 2026-06-30 | Pipeline v11 | Compliance 64/65 (98.5%)*
*See `../../AGENTS.md` for master project context.*
