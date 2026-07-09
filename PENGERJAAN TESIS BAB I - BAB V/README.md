# Pipeline Format Tesis — Panduan v3 (UNISBANK)

## 3 Perintah Ajaib

### Fase 1: BAB I–IV
```bash
python3 pipeline/run.py Tesis_Nama_BAB1_4.docx --mode bab1_4
python3 check/check_pedoman.py Tesis_Nama_BAB1_4.docx
```

### Fase 2: BAB I–V
```bash
python3 pipeline/run.py Tesis_Nama_BAB1_5.docx
python3 check/check_pedoman.py Tesis_Nama_BAB1_5.docx
```

### Fase 3: Full Tesis
```bash
python3 pipeline/run.py Tesis_Nama_Final.docx
python3 steps/fix_postprocess.py Tesis_Nama_Final.docx \
  --front-matter front_matter/FRONT_MATTER_DRAFT.docx --generate-toc
python3 check/check_pedoman.py Tesis_Nama_Final.docx
```

## Aturan Penting
- **Kerjakan di Microsoft Word** — jangan Google Docs/LibreOffice
- **Equations** → Equation Editor (Insert → Equation)
- **Gambar** → Insert langsung, jangan copy-paste
- **Daftar Pustaka** → jangan edit manual, pipeline yang atur

## Struktur File
```
pipeline/          ← otak aplikasi (run.py, config.py, utils.py)
steps/             ← script perbaikan (fix_paragraphs.py, dll)
check/             ← compliance checker (check_pedoman.py)
front_matter/      ← template cover, abstrak, dll
docs/              ← panduan & hasil cek
```

Lihat `docs/AGENTS.md` untuk dokumentasi lengkap.
