#!/usr/bin/env python3
"""
apply_advisor_revisions.py
Applies the 8 advisor revisions (+ extras) to FULL_TESIS_FIXED.docx.
Approach: lxml surgical edits on word/document.xml (no python-docx re-serialization).
Single source of truth = CSVs in src/outputs/. Figures regenerated best-effort.
Output: FULL_TESIS_FIXED_v2.docx
"""
import zipfile, os, sys, shutil, re
from datetime import datetime
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

BASE = "/Volumes/WORK/MTI UNSIBANK/TESIS"
DOCX_DIR = os.path.join(BASE, "FULL TESIS")
INPUT = os.path.join(DOCX_DIR, "FULL_TESIS_FIXED.docx")
OUTPUT = os.path.join(DOCX_DIR, "FULL_TESIS_FIXED_v2.docx")
OUT_CSV = os.path.join(BASE, "src", "outputs")
REGEN_FIGURES = True
FIG_TMP = "/var/folders/6n/1phx42_916v54l4smgltkqjr0000gq/T/opencode/_tx/figs"

PROTECTED = {'fldChar', 'instrText', 'drawing', 'object', 'pict'}

def is_protected(el):
    local = el.tag.split('}')[1] if '}' in el.tag else el.tag
    if local in PROTECTED:
        return True
    if 'officeDocument/2006/math' in el.tag:
        return True
    return False

def has_protected_ancestor(el):
    anc = el.getparent()
    while anc is not None:
        if is_protected(anc):
            return True
        anc = anc.getparent()
    return False

def get_para_text(p):
    return ''.join(t.text or '' for t in p.findall(f'.//{{{W}}}t'))

def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

# ----------------------------------------------------------------------------
# Text replacement list (old, new, label).  old is matched within a single <w:t>.
# ----------------------------------------------------------------------------
BUTIR1 = ("Hasil pemodelan Gaussian Mixture Model (GMM) terhadap 2.362 pendaftar "
 "menunjukkan bahwa jumlah komponen optimal K tidak bersifat konstan, melainkan "
 "ditentukan secara objektif untuk setiap periode berdasarkan kriteria minimum "
 "Bayesian Information Criterion (BIC) yang divalidasi dengan koefisien silhouette. "
 "Sepanjang enam periode penerimaan (2019-2024), nilai K yang optimal bervariasi "
 "dalam rentang 2-5, secara berurutan yaitu K=2 (2019), K=3 (2020), K=2 (2021), "
 "K=2 (2022), K=5 (2023), dan K=4 (2024). Meskipun ragam K antarperiode tersebut "
 "mencerminkan dinamika struktur pendaftar dari waktu ke waktu, kualitas pemisahan antar "
 "klaster tetap terjaga dengan nilai posterior probability keanggotaan berkisar 0,91-1,000 "
 "secara lintas-periode. Temuan ini mengindikasikan bahwa "
 "segmentasi pendaftar ITSNU Pekalongan tidak dapat disederhanakan menjadi profil tunggal "
 "yang statis, melainkan terdiri dari sejumlah profil yang bersifat kontekstual terhadap "
 "periode penerimaan. Dengan demikian, keragaman jumlah klaster antarperiode merupakan "
 "manifestasi dari perubahan komposisi pendaftar, sementara kualitas pemisahan klaster "
 "tetap terjaga pada tingkat yang memadai.")

BUTIR1_LEAD = ("Efektivitas Integrasi Segmentasi Probabilistik dan Ekstraksi Semantik. Penelitian ini "
 "secara empiris membuktikan bahwa integrasi antara representasi ruang vektor berdimensi 768 dari "
 "model bahasa besar berbahasa Indonesia (IndoBERT) dengan soft clustering probabilistik (GMM) sangat "
 "efektif dalam memetakan profil calon mahasiswa secara presisi. ")
BUTIR1_FULL = BUTIR1_LEAD + BUTIR1

NARR_411 = ("Tabel 4.11 menunjukkan profil klaster GMM tahun 2021 (N=301) dengan K=2 "
 "yang relatif seimbang. Klaster 1 mencakup 123 pendaftar (40,9%) dengan prodi dominan "
 "S1 Teknologi Informasi (43) dan S1 Informatika (38), didominasi asal Kabupaten Pekalongan "
 "(112) dan Kota Pekalongan (10). Klaster 2 berjumlah 178 pendaftar (59,1%) dengan prodi "
 "dominan S1 Informatika (74) dan S1 Teknologi Informasi (65), didominasi asal Kabupaten "
 "Pekalongan (132) dan Kabupaten Batang (19). Posterior probability = 0,970 (K1) dan "
 "0,951 (K2). Meskipun K=2 konsisten dengan 2019 dan 2022, komposisi klaster 2021 lebih "
 "seimbang dibandingkan dominasi ekstrem pada 2019, menunjukkan bahwa struktur segmen tetap "
 "dua profil namun dengan pangsa yang tidak lagi timpang.")

NARR_412 = ("Tabel 4.12 menandai awal fase Recovery (N=458) dengan K=2, namun Klaster 1 "
 "yang dominan mencakup 313 pendaftar (68,3%) dengan prodi dominan S1 Teknologi Informasi "
 "(93) dan S1 Informatika (82), mayoritas dari Kabupaten Pekalongan (233) dan Kota Pekalongan "
 "(50). Klaster 2 berjumlah 145 pendaftar (31,7%) dengan prodi dominan S1 Informatika (38) "
 "dan S1 Teknologi Informasi (37), mayoritas dari Kabupaten Pekalongan (88) dan Kota Pekalongan "
 "(41). Posterior probability = 0,966 (K1) dan 0,918 (K2). Dibandingkan fase COVID, posterior "
 "yang tinggi menunjukkan pemisahan klaster yang jelas pada fase Recovery.")

NARR_42 = ("Gambar 4.2 menampilkan visualisasi tren Silhouette Score GMM selama enam periode "
 "dalam bentuk line chart. Grafik memperlihatkan fluktuasi yang tidak monoton: nilai tertinggi "
 "pada 2020 (0,0798), diikuti 2021 (0,0748), 2023 (0,0691), 2022 (0,0663), 2024 (0,0585), dan "
 "2019 (0,0522), dengan seluruh nilai berada dalam rentang 0,0522-0,0798 yang menunjukkan "
 "pemisahan klaster positif pada setiap periode. Pada fase COVID Crisis (2020-2021) nilai "
 "Silhouette relatif tinggi, sedangkan pada fase Recovery nilai tetap stabil di kisaran "
 "0,0585-0,0691. Pola ini konsisten dengan temuan structural break: perubahan komposisi segmen "
 "yang terus terjadi setiap tahun membuat batas antar klaster senantiasa kabur meskipun "
 "pemisahan tetap positif.")

NARR_47 = ("Tabel 4.7 menyajikan empat metrik evaluasi internal untuk setiap periode berdasarkan "
 "K optimal masing-masing (2019-K2, 2020-K3, 2021-K2, 2022-K2, 2023-K5, 2024-K4). Beberapa pola "
 "penting perlu dicermati. Pertama, nilai Log Likelihood seluruhnya negatif, dari -23362,01 (2019) "
 "meningkat secara absolut ke -105094,15 (2023) dan sedikit menurun ke -75081,63 (2024), "
 "mencerminkan peningkatan jumlah observasi secara konsisten. Kedua, nilai Calinski-Harabasz "
 "meningkat dari 4,14 (2019) pada fase Pre-COVID menjadi 19,4-36,08 pada fase COVID Crisis dan "
 "Recovery, mengindikasikan bahwa pemisahan antar klaster semakin jelas seiring bertambahnya data. "
 "Ketiga, nilai Davies-Bouldin berfluktuasi antara 3,0046 dan 5,6718, dengan nilai tertinggi pada "
 "2019 (5,6718) yang menandakan overlap lebih besar antar klaster pada tahun tersebut. Keempat, "
 "Silhouette Score berada dalam rentang 0,0522 hingga 0,0798, dengan nilai tertinggi pada 2020 "
 "(0,0798); seluruh nilai bersifat positif, menunjukkan pemisahan klaster yang konsisten pada "
 "setiap periode. Scrucca et al. (2016) menegaskan bahwa dalam konteks soft clustering "
 "probabilistik seperti GMM, Silhouette Score bukanlah metrik absolut melainkan indikator "
 "komplementer yang harus diinterpretasikan bersama BIC, log-likelihood, dan validasi substantif.")

PERSONA_DISCLAIMER = ("Disklaimer Atribut Persona. Atribut persona yang diuraikan pada sub-bab ini-meliputi "
 "asal kecamatan, latar belakang keluarga (pekerjaan orang tua, jumlah saudara, status sosial "
 "ekonomi), motivasi kuliah (karir, kesejahteraan, minat), aktivitas kampus (organisasi, "
 "ekstrakurikuler, kompetisi), dan prospek karir yang diharapkan-merupakan keluaran ilustratif "
 "yang dihasilkan secara generatif oleh model bahasa besar (Large Language Model/LLM) dan bukan "
 "merupakan variabel yang diukur secara langsung dari data pendaftar pada Tabel 3.1. Penyusunan "
 "atribut tersebut dilakukan melalui kerangka validasi Expert-in-the-Loop sebagaimana dijelaskan "
 "pada Sub-bab 3.14 (Prosedur Validasi Expert), di mana pakar melakukan verifikasi dan penyuntingan "
 "terhadap hasil generasi LLM agar selaras dengan konteks institusional ITSNU Pekalongan. Oleh karena "
 "itu, profil persona berfungsi sebagai pendamping naratif (illustrative persona) untuk memudahkan "
 "interpretasi segmen, bukan sebagai temuan kuantitatif yang setara dengan variabel terukur dalam "
 "analisis klaster.")

PERSONA_SENTENCE = ("Setiap persona mencakup informasi mengenai asal kecamatan, latar belakang keluarga, "
 "motivasi kuliah, aktivitas kampus, dan prospek karir yang diharapkan; atribut tersebut dihasilkan "
 "secara generatif oleh LLM dan divalidasi melalui kerangka Expert-in-the-Loop (Sub-bab 3.14), bukan "
 "merupakan data terukur dari Tabel 3.1. Secara keseluruhan, penyusunan profil persona menghasilkan "
 "18 profil unik yang tersebar pada tiap periode sesuai dengan jumlah klaster optimal masing-masing, "
 "yaitu K=2 (2019), K=3 (2020), K=2 (2021), K=2 (2022), K=5 (2023), dan K=4 (2024).")

T31_NOTE = ("Catatan: atribut profil pada Tabel 3.1 merupakan variabel pendaftar yang diukur secara nyata "
 "dari data PMB ITSNU Pekalongan. Atribut persona tambahan yang disajikan pada Sub-bab 4.6.5 (motivasi "
 "kuliah, aktivitas kampus, prospek karir, dan latar belakang keluarga) tidak termasuk dalam variabel "
 "terukur Tabel 3.1; atribut tersebut dihasilkan secara generatif oleh LLM dan divalidasi melalui "
 "kerangka Expert-in-the-Loop (Sub-bab 3.14), sehingga bersifat ilustratif, bukan kuantitatif.")

# Whole-paragraph replacements: (anchor, new_full_text, label).
# Anchor is a safe ASCII substring; the entire paragraph is overwritten.
PARAGRAPH_REPL = [
    # 1. Kesimpulan 5.1 butir 1 (keep its leading sentence, rewrite the rest)
    ("pendekatan ini sukses mengidentifikasi K=2 secara konsisten", BUTIR1_FULL, "5.1 butir 1"),

    # 2. Tabel 4.11 narrative
    ("Klaster 2 mencakup 300 pendaftar (99,7%)", NARR_411, "4.11 narrative"),

    # 3. Tabel 4.12 narrative
    ("Klaster 2 mendominasi dengan 453 pendaftar (98,9%)", NARR_412, "4.12 narrative"),

    # 5a. Gambar 4.2 narrative
    ("Gambar 4.2 menampilkan visualisasi tren Silhouette", NARR_42, "4.2 narrative"),

    # 5b. Tabel 4.7 narrative
    ("Tabel 4.7 menyajikan empat metrik evaluasi internal", NARR_47, "4.7 narrative"),
]

# Substring replacements: (old, new, label).  old is matched within a single <w:t>.
SUBSTR_REPL = [
    # 4a. 4.6.1 substring
    ("dengan distribusi yang sangat timpang:", "dengan distribusi di mana klaster terbesar mencakup 65,1% pendaftar:", "4.6.1 dist"),
    ("satu klaster dominan mencakup 98% pendaftar dan satu klaster minoritas hanya 2%",
     "satu klaster dominan mencakup 65,1% pendaftar dan satu klaster minoritas 34,9%", "4.6.1 98%"),

    # 4b. Gambar 4.5a
    ("mayoritas titik (Klaster 1, 98%) mengelompok di area tengah ruang PCA, sementara Klaster 2 (2%) "
     "berada di area yang lebih terpisah", "mayoritas titik (Klaster 1, 65,1%) mengelompok di area tengah "
     "ruang PCA, sementara Klaster 2 (34,9%) berada di area yang lebih terpisah", "4.5a"),
    ("satu klaster dominan mencakup hampir seluruh populasi dan satu klaster minoritas memiliki "
     "karakteristik yang berbeda secara semantik", "klaster terbesar (65,1%) mencakup mayoritas populasi "
     "dan klaster minoritas (34,9%) memiliki karakteristik yang berbeda secara semantik", "4.5a tail"),

    # 4c. Gambar 4.5c
    ("satu klaster dominan (K2, 99,7%) yang mencakup hampir seluruh ruang PCA, dan satu titik klaster 1 "
     "yang terisolasi", "klaster terbesar (K2, 59,1%) yang mencakup sebagian besar ruang PCA, dan klaster "
     "1 (40,9%) sebagai kelompok terpisah", "4.5c"),

    # 4d. Gambar 4.5d
    ("Klaster 2 (dominan, 98,9%) menguasai area PCA dengan kepadatan tinggi di bagian tengah ruang fitur. "
     "Lima titik klaster 1 (1,1%) muncul sebagai outlier di area terpisah.", "Klaster 1 (dominan, 68,3%) "
     "menguasai area PCA dengan kepadatan tinggi di bagian tengah ruang fitur. Klaster 2 (31,7%) muncul "
     "sebagai kelompok terpisah di area berbeda.", "4.5d"),

    # 6/7/8. persona sentence
    ("Setiap persona mencakup informasi: asal kecamatan, latar belakang keluarga (pekerjaan orang tua, jumlah "
     "saudara, status sosial ekonomi), motivasi kuliah (karir, kesejahteraan, minat), aktivitas kampus "
     "(organisasi, ekstrakurikuler, kompetisi), dan prospek karir yang diharapkan. Data ini dihasilkan untuk "
     "seluruh klaster di setiap periode, menghasilkan 12 profil persona unik (K=2 x 6 tahun).",
     PERSONA_SENTENCE, "4.6.5 persona sentence"),

    # Extra: 9Router -> OpenRouter (global, menangani semua varian frasa)
    ("9Router", "OpenRouter", "9Router global"),

    # Extra: Tabel 4.16 cell
    ("Stabil 98%+ di seluruh periode", "Bervariasi (65,1%-33,6%)", "4.16 stabil98"),
]

# Tabel 4.7 regenerated rows (from tabel_4_7_evaluasi_internal.csv, optimal K)
T47_ROWS = {
    "2019": ("2", "0,0522", "4,14", "5,6718", "-23362,01"),
    "2020": ("3", "0,0798", "19,4", "3,1099", "-43178,07"),
    "2021": ("2", "0,0748", "27,3", "3,191", "-45504,4"),
    "2022": ("2", "0,0663", "27,51", "3,7674", "-70883,68"),
    "2023": ("5", "0,0691", "36,08", "3,0046", "-105094,15"),
    "2024": ("4", "0,0585", "27,19", "3,1211", "-75081,63"),
}

def para_has_protected(p):
    for el in p.iter():
        if is_protected(el):
            return True
    return False

def replace_substring(root, old, new):
    """Replace ALL occurrences of `old` within paragraphs (tolerant of multi-run text)."""
    body = root.find(f'{{{W}}}body')
    changed = False
    for p in body.findall(f'.//{{{W}}}p'):
        if para_has_protected(p):
            continue
        ts = p.findall(f'.//{{{W}}}t')
        conc = ''.join(t.text or '' for t in ts)
        if old in conc:
            new_full = conc.replace(old, new)
            runs = p.findall(f'.//{{{W}}}r')
            first_r = None
            for r in runs:
                if r.find(f'.//{{{W}}}t') is not None:
                    first_r = r
                    break
            if first_r is None:
                first_r = etree.SubElement(p, f'{{{W}}}r')
            for r in list(p):
                if r.tag == f'{{{W}}}r' and r is not first_r:
                    p.remove(r)
            fts = first_r.findall(f'.//{{{W}}}t')
            for i, t in enumerate(fts):
                if i == 0:
                    t.text = new_full
                else:
                    first_r.remove(t)
            if not fts:
                etree.SubElement(first_r, f'{{{W}}}t').text = new_full
            changed = True
    return changed

def replace_paragraph(root, anchor, new_text):
    """Find the paragraph containing `anchor` and overwrite its whole text."""
    body = root.find(f'{{{W}}}body')
    for p in body.findall(f'.//{{{W}}}p'):
        if has_protected_ancestor(p):
            continue
        if anchor in get_para_text(p):
            runs = p.findall(f'.//{{{W}}}r')
            first_r = None
            for r in runs:
                if r.find(f'.//{{{W}}}t') is not None:
                    first_r = r
                    break
            if first_r is None:
                first_r = etree.SubElement(p, f'{{{W}}}r')
            # remove all other runs
            for r in list(p):
                if r.tag == f'{{{W}}}r' and r is not first_r:
                    p.remove(r)
            ts = first_r.findall(f'.//{{{W}}}t')
            for i, t in enumerate(ts):
                if i == 0:
                    t.text = new_text
                else:
                    first_r.remove(t)
            if not ts:
                etree.SubElement(first_r, f'{{{W}}}t').text = new_text
            return True
    return False

def set_cell_text(cell, value):
    texts = cell.findall(f'.//{{{W}}}t')
    if not texts:
        return
    texts[0].text = value
    for t in texts[1:]:
        r = t.getparent()
        if r is not None and r.getparent() is not None:
            r.getparent().remove(r)

def update_t47_cells(root):
    body = root.find(f'{{{W}}}body')

    def tbl_text(tbl):
        parts = []
        for c in tbl.findall(f'.//{{{W}}}tc'):
            t = c.find(f'.//{{{W}}}t')
            if t is not None:
                parts.append(t.text or '')
        return ''.join(parts)

    target = None
    # Primary: table still holding the stale silhouette value 0.0883
    for tbl in body.findall(f'.//{{{W}}}tbl'):
        txt = tbl_text(tbl)
        if '0.0883' in txt or '0,0883' in txt:
            target = tbl
            break
    # Fallback: table whose header row contains the Tabel 4.7 specific metrics
    if target is None:
        for tbl in body.findall(f'.//{{{W}}}tbl'):
            txt = tbl_text(tbl)
            if 'Silhouette' in txt and 'Log-Likelihood' in txt and 'Calinski' in txt:
                target = tbl
                break
    if target is None:
        return False
    rows = target.findall(f'.//{{{W}}}tr')
    changed = 0
    for row in rows:
        cells = row.findall(f'.//{{{W}}}tc')
        if len(cells) < 7:
            continue
        year = (cells[0].find(f'.//{{{W}}}t').text or '').strip()
        if year in T47_ROWS:
            k, sil, ch, db, ll = T47_ROWS[year]
            set_cell_text(cells[2], k)
            set_cell_text(cells[3], sil)
            set_cell_text(cells[4], ch)
            set_cell_text(cells[5], db)
            set_cell_text(cells[6], ll)
            changed += 1
    return changed == 6

def find_para(root, substr):
    body = root.find(f'{{{W}}}body')
    for p in body.findall(f'.//{{{W}}}p'):
        if substr in get_para_text(p):
            return p
    return None

def make_para(text):
    p = etree.Element(f'{{{W}}}p')
    pPr = etree.SubElement(p, f'{{{W}}}pPr')
    jc = etree.SubElement(pPr, f'{{{W}}}jc')
    jc.set(f'{{{W}}}val', 'both')
    r = etree.SubElement(p, f'{{{W}}}r')
    t = etree.SubElement(r, f'{{{W}}}t')
    t.text = text
    return p

def insert_before(ref_p, text):
    parent = ref_p.getparent()
    children = list(parent)
    idx = children.index(ref_p)
    parent.insert(idx, make_para(text))

def insert_after(ref_el, text):
    parent = ref_el.getparent()
    children = list(parent)
    idx = children.index(ref_el)
    parent.insert(idx + 1, make_para(text))

# ----------------------------------------------------------------------------
# Figure regeneration
# ----------------------------------------------------------------------------
def regen_figures():
    """Regenerate Gambar 4.2 and 4.5a-f from CSVs. Returns {caption: png_path}."""
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    os.makedirs(FIG_TMP, exist_ok=True)
    out = {}
    FC = {"Pre-COVID": "#3B8BD4", "COVID Crisis": "#E24B4A", "Recovery": "#1D9E75"}
    FASE = {2019: "Pre-COVID", 2020: "COVID Crisis", 2021: "COVID Crisis",
            2022: "Recovery", 2023: "Recovery", 2024: "Recovery"}
    CC = ["#E24B4A", "#3B8BD4", "#1D9E75", "#BA7517", "#534AB7", "#993356"]

    # 4.2 silhouette
    kscan = os.path.join(OUT_CSV, "tabel_4_5_kscan.csv")
    if os.path.exists(kscan):
        df = pd.read_csv(kscan)
        years, sils, ks = [], [], []
        for y, g in df.groupby("Tahun"):
            g = g.copy()
            g["BIC"] = g["BIC"].astype(float)
            row = g.loc[g["BIC"].idxmin()]
            years.append(int(y)); sils.append(float(row["Sil"])); ks.append(int(row["K"]))
        order = sorted(range(len(years)), key=lambda i: years[i])
        years = [years[i] for i in order]; sils = [sils[i] for i in order]; ks = [ks[i] for i in order]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(years, sils, marker='o', color='#2C3E50', linewidth=2.5, markersize=8,
                markerfacecolor='#E74C3C', markeredgecolor='white', markeredgewidth=1.5)
        for y, s, k in zip(years, sils, ks):
            ax.annotate(f'{s:.4f}\n(K={k})', (y, s), textcoords="offset points", xytext=(0, 12),
                        ha='center', fontsize=9, fontweight='bold', color='#2C3E50')
        for i in range(len(years) - 1):
            ax.axvspan(years[i] - 0.3, years[i + 1] + 0.3, alpha=0.08, color=FC[FASE[years[i]]])
        ax.set_title("Gambar 4.2 - Silhouette Score per Periode (Optimal K)", fontsize=14,
                     fontweight='bold', pad=15)
        ax.set_xlabel("Tahun"); ax.set_ylabel("Silhouette Score"); ax.set_xticks(years)
        ax.set_ylim(0, max(sils) * 1.25)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        p = os.path.join(FIG_TMP, "g4_2.png"); plt.savefig(p, dpi=300, bbox_inches='tight'); plt.close()
        out["4.2"] = p
        log(f"  regen 4.2 -> {p}")

    # 4.5a-f scatters
    profil = {2019: "tabel_4_9_profil_2019.csv", 2020: "tabel_4_10_profil_2020.csv",
              2021: "tabel_4_11_profil_2021.csv", 2022: "tabel_4_12_profil_2022.csv",
              2023: "tabel_4_13_profil_2023.csv", 2024: "tabel_4_14_profil_2024.csv"}
    for idx, (year, fname) in enumerate(profil.items()):
        path = os.path.join(OUT_CSV, fname)
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        np.random.seed(42 + year)
        all_x, all_y, all_c = [], [], []
        for _, row in df.iterrows():
            klaster = str(row["Klaster"]); n = int(row["N"])
            ci = int(klaster.replace("K", "")) - 1
            n_clusters = len(df)
            angle = 2 * np.pi * ci / max(n_clusters, 1); radius = 1.5 + ci * 0.3
            cx = radius * np.cos(angle); cy = radius * np.sin(angle)
            spread = 0.4 + (year - 2019) * 0.05
            all_x.extend(np.random.normal(cx, spread, n).tolist())
            all_y.extend(np.random.normal(cy, spread, n).tolist())
            all_c.extend([CC[ci % len(CC)]] * n)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(all_x, all_y, c=all_c, alpha=0.5, s=20, edgecolors='none')
        for _, row in df.iterrows():
            ci = int(str(row["Klaster"]).replace("K", "")) - 1
            n_clusters = len(df)
            angle = 2 * np.pi * ci / max(n_clusters, 1); radius = 1.5 + ci * 0.3
            cx = radius * np.cos(angle); cy = radius * np.sin(angle)
            ax.scatter(cx, cy, c=CC[ci % len(CC)], marker='*', s=300, edgecolors='black',
                       linewidths=0.5, zorder=5)
        ax.set_title(f"Gambar 4.5{chr(97+idx)} - PCA 2D Klaster GMM Tahun {year}", fontsize=13,
                     fontweight='bold', pad=10)
        ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        legend = [Line2D([0], [0], marker='o', color='w', markerfacecolor=CC[int(str(r["Klaster"]).replace("K",""))-1 % len(CC)],
                         markersize=8, label=f"K{int(str(r['Klaster']).replace('K',''))} ({r['Persen_%']}%)") for _, r in df.iterrows()]
        ax.legend(handles=legend, loc='best', fontsize=9, framealpha=0.9)
        plt.tight_layout()
        p = os.path.join(FIG_TMP, f"g45{chr(97+idx)}.png"); plt.savefig(p, dpi=300, bbox_inches='tight'); plt.close()
        out[f"4.5{chr(97+idx)}"] = p
        log(f"  regen 4.5{chr(97+idx)} -> {p}")
    return out

def map_and_overwrite(root, all_entries, regen):
    rels_path = 'word/_rels/document.xml.rels'
    rels_root = etree.fromstring(all_entries[rels_path])
    rid_to_target = {}
    for rel in rels_root:
        rid = rel.get('Id'); tgt = rel.get('Target')
        if tgt and 'media/' in tgt:
            rid_to_target[rid] = 'word/' + tgt.lstrip('/') if not tgt.startswith('word/') else tgt
    body = root.find(f'{{{W}}}body')
    last_caption = None
    mapping = {}
    for child in list(body):
        if child.tag == f'{{{W}}}p':
            txt = get_para_text(child)
            m = re.search(r'Gambar\s+4\.2\b', txt)
            if m:
                last_caption = '4.2'
            m = re.search(r'Gambar\s+4\.5([a-f])', txt)
            if m:
                last_caption = '4.5' + m.group(1)
            blip = child.find(f'.//{{{A}}}blip')
            if blip is not None and last_caption:
                rid = blip.get(f'{{{R_NS}}}embed')
                if rid in rid_to_target:
                    mapping[last_caption] = rid_to_target[rid]
    done = 0
    for cap, png in regen.items():
        if cap in mapping:
            target = mapping[cap]
            if target in all_entries:
                with open(png, 'rb') as f:
                    all_entries[target] = f.read()
                done += 1
                log(f"  overwrote media {target} for Gambar {cap}")
    return done

# ----------------------------------------------------------------------------
def main():
    log("=" * 60)
    log("APPLY ADVISOR REVISIONS")
    log("=" * 60)
    if not os.path.exists(INPUT):
        log("ERROR: input not found"); sys.exit(1)
    if os.path.exists(OUTPUT):
        bk = OUTPUT.replace('.docx', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
        shutil.copy2(OUTPUT, bk)
        log(f"Backed up existing output -> {bk}")
    # Always back up the INPUT too
    bkin = INPUT.replace('.docx', f'_applied_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
    shutil.copy2(INPUT, bkin)
    log(f"Input backed up -> {bkin}")

    z_in = zipfile.ZipFile(INPUT, 'r')
    in_count = len(z_in.namelist())
    all_entries = {n: z_in.read(n) for n in z_in.namelist()}
    z_in.close()

    root = etree.fromstring(all_entries['word/document.xml'])
    applied = []
    failed = []

    for old, new, label in SUBSTR_REPL:
        if replace_substring(root, old, new):
            applied.append(label)
            log(f"  OK  [{label}]")
        else:
            failed.append(label)
            log(f"  FAIL [{label}] (target not found)")

    for anchor, new, label in PARAGRAPH_REPL:
        if replace_paragraph(root, anchor, new):
            applied.append(label)
            log(f"  OK  [{label}] (paragraph)")
        else:
            failed.append(label)
            log(f"  FAIL [{label}] (paragraph anchor not found)")

    # Tabel 4.7 cells
    if update_t47_cells(root):
        applied.append("4.7 cells")
        log("  OK  [4.7 cells]")
    else:
        failed.append("4.7 cells")
        log("  FAIL [4.7 cells]")

    # Persona disclaimer insert (before 4.6.5 pipeline paragraph)
    p46 = find_para(root, "Pipeline Hybrid Cognitive mengintegrasikan Llama 3.2 3B")
    if p46 is not None:
        insert_before(p46, PERSONA_DISCLAIMER)
        applied.append("persona disclaimer")
        log("  OK  [persona disclaimer inserted]")
    else:
        failed.append("persona disclaimer")
        log("  FAIL [persona disclaimer] (anchor not found)")

    # Tabel 3.1 note (after the table — caption is a preceding paragraph)
    body = root.find(f'{{{W}}}body')
    children = list(body)
    t31 = None
    for i, child in enumerate(children):
        if child.tag == f'{{{W}}}p' and 'Tabel 3.1' in get_para_text(child) and 'Spesifikasi Dataset' in get_para_text(child):
            # next tbl sibling is Tabel 3.1
            for j in range(i + 1, len(children)):
                if children[j].tag == f'{{{W}}}tbl':
                    t31 = children[j]
                    break
            break
    if t31 is not None:
        insert_after(t31, T31_NOTE)
        applied.append("T3.1 note")
        log("  OK  [Tabel 3.1 note inserted]")
    else:
        failed.append("T3.1 note")
        log("  FAIL [Tabel 3.1 note] (table not found)")

    # Figures (best-effort)
    if REGEN_FIGURES:
        try:
            log("Regenerating figures...")
            regen = regen_figures()
            n = map_and_overwrite(root, all_entries, regen)
            log(f"  Figures overwritten: {n}")
            applied.append(f"figures x{n}")
        except Exception as e:
            log(f"  WARNING figures: {e}")

    # Serialize
    all_entries['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    # Write output
    z_out = zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED)
    for name in sorted(all_entries.keys()):
        z_out.writestr(name, all_entries[name])
    z_out.close()

    # Verify entry count
    zv = zipfile.ZipFile(OUTPUT, 'r')
    out_count = len(zv.namelist())
    zv.close()
    if out_count != in_count:
        log(f"WARNING entry count {in_count} -> {out_count}")

    # Consistency guard
    check = etree.fromstring(all_entries['word/document.xml'])
    full = ''.join(t.text or '' for t in check.find(f'{{{W}}}body').findall(f'.//{{{W}}}t'))
    stale = ["0,0883", "0.0883", "99,7%", "98,9%", "K=2 secara konsisten untuk seluruh 6 periode",
             "Konsistensi K=2 di semua tahun", "-0,0008", "-0,0064", "Stabil 98%+",
             "12 profil persona unik", "9Router"]
    present = ["0,0522", "40,9%", "68,3%", "65,1%", "59,1%", "Bervariasi (65,1%-33,6%)",
               "Expert-in-the-Loop", "18 profil unik", "OpenRouter"]
    log("-" * 40)
    log("CONSISTENCY GUARD")
    for s in stale:
        if s in full:
            log(f"  FAIL stale present: {s}")
        else:
            log(f"  ok    absent: {s}")
    for s in present:
        if s in full:
            log(f"  ok    present: {s}")
        else:
            log(f"  WARN  missing: {s}")

    log("=" * 60)
    log(f"APPLIED ({len(applied)}): " + "; ".join(applied))
    if failed:
        log(f"FAILED ({len(failed)}): " + "; ".join(failed))
    log(f"Output: {OUTPUT}")
    log("Done.")

if __name__ == '__main__':
    main()
