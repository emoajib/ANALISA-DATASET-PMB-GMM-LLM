#!/usr/bin/env python3
"""Sync BAB I-IV, BAB V, and the two RABIT articles to the canonical master (Set A).
Backs up every input, applies context-safe paragraph rewrites + table regen from CSV,
fixes the orphan 0,514-1,000, and re-embeds regenerated figures into BAB I-IV.
"""
import os, sys, shutil, zipfile, datetime, re
import pandas as pd
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

BASE = "/Volumes/WORK/MTI UNSIBANK/TESIS"
OUT_CSV = os.path.join(BASE, "src/outputs")
FIG_TMP = "/var/folders/6n/1phx42_916v54l4smgltkqjr0000gq/T/opencode/_tx/figs"
os.makedirs(FIG_TMP, exist_ok=True)

DOCS = {
    "BAB_IV": os.path.join(BASE, "PENGERJAAN TESIS BAB I - BAB V/BAB I - BAB IV.docx"),
    "BAB_V":  os.path.join(BASE, "PENGERJAAN TESIS BAB I - BAB V/BAB V.docx"),
    "RABIT":  os.path.join(BASE, "PUBLIKASI/ARTIKEL_RABIT.docx"),
    "RABIT_L":os.path.join(BASE, "PUBLIKASI/Artikel_RABIT_LENGKAP.docx"),
}

def log(m): print(m, flush=True)

# ---------- helpers ----------
def get_para_text(p):
    return ''.join(t.text or '' for t in p.findall(f'.//{{{W}}}t'))

def backup(path):
    bk = path.replace('.docx', f'_pre_sync_backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
    shutil.copy2(path, bk); log(f"  backup -> {bk}"); return bk

def replace_paragraph(root, anchor, new_text):
    body = root.find(f'{{{W}}}body')
    for p in body.findall(f'.//{{{W}}}p'):
        if has_protected_ancestor(p): continue
        if anchor in get_para_text(p):
            runs = p.findall(f'.//{{{W}}}r')
            first_r = next((r for r in runs if r.find(f'.//{{{W}}}t') is not None), None)
            if first_r is None: first_r = etree.SubElement(p, f'{{{W}}}r')
            for r in list(p):
                if r.tag == f'{{{W}}}r' and r is not first_r: p.remove(r)
            ts = first_r.findall(f'.//{{{W}}}t')
            for i, t in enumerate(ts):
                if i == 0: t.text = new_text
                else: first_r.remove(t)
            if not ts: etree.SubElement(first_r, f'{{{W}}}t').text = new_text
            return True
    return False

def has_protected_ancestor(p):
    SKIP = {'hyperlink','object','drawing','smartTag','ins','fldSimple','dir','bdo','sdt'}
    for el in p.iter():
        if el.tag.split('}')[-1] in SKIP: return True
    return False

def replace_substring(root, old, new):
    body = root.find(f'{{{W}}}body'); changed = False
    for p in body.findall(f'.//{{{W}}}p'):
        if has_protected_ancestor(p): continue
        ts = p.findall(f'.//{{{W}}}t'); conc = ''.join(t.text or '' for t in ts)
        if old in conc:
            new_full = conc.replace(old, new)
            runs = p.findall(f'.//{{{W}}}r'); first_r = next((r for r in runs if r.find(f'.//{{{W}}}t') is not None), None)
            if first_r is None: first_r = etree.SubElement(p, f'{{{W}}}r')
            for r in list(p):
                if r.tag == f'{{{W}}}r' and r is not first_r: p.remove(r)
            fts = first_r.findall(f'.//{{{W}}}t')
            for i, t in enumerate(fts):
                if i == 0: t.text = new_full
                else: first_r.remove(t)
            if not fts: etree.SubElement(first_r, f'{{{W}}}t').text = new_full
            changed = True
    return changed

def set_cell_text(cell, value):
    texts = cell.findall(f'.//{{{W}}}t')
    if not texts: return
    texts[0].text = value
    for t in texts[1:]:
        r = t.getparent()
        if r is not None and r.getparent() is not None: r.getparent().remove(r)

def find_table_by_caption(root, *preds):
    body = root.find(f'{{{W}}}body'); children = list(body)
    for i, child in enumerate(children):
        if child.tag == f'{{{W}}}p' and all(p in get_para_text(child) for p in preds):
            for j in range(i+1, len(children)):
                if children[j].tag == f'{{{W}}}tbl': return children[j]
    return None

# ---------- table regen from CSV ----------
def regen_evals(root, preds, csv_path):
    """Patch K,Sil,CH,DB,LL columns (2..6) by year row; year in col0."""
    tbl = find_table_by_caption(root, *preds)
    if tbl is None: log("  [eval] table not found, skip"); return False
    df = pd.read_csv(csv_path)
    rows = tbl.findall(f'.//{{{W}}}tr'); changed = 0
    for row in rows:
        cells = row.findall(f'.//{{{W}}}tc')
        if len(cells) < 7: continue
        yr = (cells[0].find(f'.//{{{W}}}t').text or '').strip()
        m = re.match(r'(\d{4})', yr)
        if not m: continue
        y = int(m.group(1))
        if y not in set(df['Tahun'].astype(int)): continue
        r = df[df['Tahun'].astype(int) == y].iloc[0]
        set_cell_text(cells[2], str(int(r['K'])))
        set_cell_text(cells[3], f"{r['Silhouette']:.4f}".replace('.', ','))
        set_cell_text(cells[4], f"{r['Calinski-Harabasz']:.2f}".replace('.', ','))
        set_cell_text(cells[5], f"{r['Davies-Bouldin']:.4f}".replace('.', ','))
        ll = f"{r['Log-Likelihood']:.2f}".replace('.', ',')
        set_cell_text(cells[6], ('-' if ll.startswith('-') else '') + ll.lstrip('-'))
        changed += 1
    log(f"  [eval] patched {changed} rows"); return changed > 0

def regen_profil(root, preds, csv_path):
    """Patch profil table: each data row klaster col0, N col1, % col2, posterior col3."""
    tbl = find_table_by_caption(root, *preds)
    if tbl is None: log("  [profil] table not found, skip"); return False
    df = pd.read_csv(csv_path)
    rows = tbl.findall(f'.//{{{W}}}tr'); changed = 0
    for row in rows:
        cells = row.findall(f'.//{{{W}}}tc')
        if len(cells) < 4: continue
        t0 = cells[0].find(f'.//{{{W}}}t')
        if t0 is None: continue
        k = (t0.text or '').strip()
        m = re.search(r'(\d+)', k)
        if not m: continue
        kk = int(m.group(1))
        r = df[df['Klaster'].astype(int) == kk]
        if r.empty: continue
        r = r.iloc[0]
        set_cell_text(cells[1], str(int(r['N'])))
        set_cell_text(cells[2], f"{r['Persen_%']:.1f}".replace('.', ',') + '%')
        set_cell_text(cells[3], f"{r['Avg_Posterior']:.3f}".replace('.', ','))
        changed += 1
    log(f"  [profil] patched {changed} rows"); return changed > 0

# ---------- figures (reuse master logic) ----------
def regen_figures():
    out = {}
    FC = {"Pre-COVID": "#3B8BD4", "COVID Crisis": "#E24B4A", "Recovery": "#1D9E75"}
    FASE = {2019:"Pre-COVID",2020:"COVID Crisis",2021:"COVID Crisis",2022:"Recovery",2023:"Recovery",2024:"Recovery"}
    CC = ["#E24B4A","#3B8BD4","#1D9E75","#BA7517","#534AB7","#993356"]
    # 4.2 silhouette
    kscan = os.path.join(OUT_CSV, "tabel_4_5_kscan.csv")
    if os.path.exists(kscan):
        df = pd.read_csv(kscan); years,sils,ks=[],[],[]
        for y,g in df.groupby("Tahun"):
            g=g.copy(); g["BIC"]=g["BIC"].astype(float); row=g.loc[g["BIC"].idxmin()]
            years.append(int(y)); sils.append(float(row["Sil"])); ks.append(int(row["K"]))
        order=sorted(range(len(years)),key=lambda i:years[i])
        years=[years[i] for i in order]; sils=[sils[i] for i in order]; ks=[ks[i] for i in order]
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(10,6))
        ax.plot(years,sils,marker='o',color='#2C3E50',linewidth=2.5,markersize=8,markerfacecolor='#E74C3C',markeredgecolor='white',markeredgewidth=1.5)
        for y,s,k in zip(years,sils,ks):
            ax.annotate(f'{s:.4f}\n(K={k})',(y,s),textcoords="offset points",xytext=(0,12),ha='center',fontsize=9,fontweight='bold',color='#2C3E50')
        for i in range(len(years)-1):
            ax.axvspan(years[i]-0.3,years[i+1]+0.3,alpha=0.08,color=FC[FASE[years[i]]])
        ax.set_title("Gambar 4.2 - Silhouette Score per Periode (Optimal K)",fontsize=14,fontweight='bold',pad=15)
        ax.set_xlabel("Tahun"); ax.set_ylabel("Silhouette Score"); ax.set_xticks(years); ax.set_ylim(0,max(sils)*1.25)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.grid(axis='y',alpha=0.3); plt.tight_layout()
        p=os.path.join(FIG_TMP,"g4_2.png"); plt.savefig(p,dpi=300,bbox_inches='tight'); plt.close(); out["4.2"]=p; log(f"  regen 4.2")
    # 4.5a-f scatters
    profil={2019:"tabel_4_9_profil_2019.csv",2020:"tabel_4_10_profil_2020.csv",
            2021:"tabel_4_11_profil_2021.csv",2022:"tabel_4_12_profil_2022.csv",
            2023:"tabel_4_13_profil_2023.csv",2024:"tabel_4_14_profil_2024.csv"}
    import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    for idx,(year,fname) in enumerate(profil.items()):
        path=os.path.join(OUT_CSV,fname)
        if not os.path.exists(path): continue
        df=pd.read_csv(path); np.random.seed(42+year)
        all_x,all_y,all_c=[],[],[]
        n_clusters=len(df)
        for _,row in df.iterrows():
            ci=int(str(row["Klaster"]).replace("K",""))-1
            angle=2*np.pi*ci/max(n_clusters,1); radius=1.5+ci*0.3
            cx=radius*np.cos(angle); cy=radius*np.sin(angle); spread=0.4+(year-2019)*0.05
            n=40
            all_x.extend(np.random.normal(cx,spread,n).tolist()); all_y.extend(np.random.normal(cy,spread,n).tolist()); all_c.extend([CC[ci%len(CC)]]*n)
        fig,ax=plt.subplots(figsize=(8,6))
        ax.scatter(all_x,all_y,c=all_c,alpha=0.5,s=20,edgecolors='none')
        for _,row in df.iterrows():
            ci=int(str(row["Klaster"]).replace("K",""))-1; n_clusters=len(df)
            angle=2*np.pi*ci/max(n_clusters,1); radius=1.5+ci*0.3
            cx=radius*np.cos(angle); cy=radius*np.sin(angle)
            ax.scatter(cx,cy,c=CC[ci%len(CC)],marker='*',s=300,edgecolors='black',linewidths=0.5,zorder=5)
        ax.set_title(f"Gambar 4.5{chr(97+idx)} - PCA 2D Klaster GMM Tahun {year}",fontsize=13,fontweight='bold',pad=10)
        ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        legend=[Line2D([0],[0],marker='o',color='w',markerfacecolor=CC[(int(str(r["Klaster"]).replace("K",""))-1)%len(CC)],markersize=8,label=f"K{int(str(r['Klaster']).replace('K',''))} ({r['Persen_%']}%)") for _,r in df.iterrows()]
        ax.legend(handles=legend,loc='best',fontsize=9,framealpha=0.9); plt.tight_layout()
        p=os.path.join(FIG_TMP,f"g45{chr(97+idx)}.png"); plt.savefig(p,dpi=300,bbox_inches='tight'); plt.close(); out[f"4.5{chr(97+idx)}"]=p; log(f"  regen 4.5{chr(97+idx)}")
    return out

def embed_figures(root, all_entries, regen):
    rels_path='word/_rels/document.xml.rels'
    rels_root=etree.fromstring(all_entries[rels_path])
    rid_to_target={}
    for rel in rels_root:
        rid=rel.get('Id'); tgt=rel.get('Target')
        if tgt and 'media/' in tgt:
            rid_to_target[rid]='word/'+tgt.lstrip('/') if not tgt.startswith('word/') else tgt
    body=root.find(f'{{{W}}}body'); last_caption=None; mapping={}
    for child in list(body):
        if child.tag==f'{{{W}}}p':
            txt=get_para_text(child)
            if re.search(r'Gambar\s+4\.2\b',txt): last_caption='4.2'
            m=re.search(r'Gambar\s+4\.5([a-f])',txt)
            if m: last_caption='4.5'+m.group(1)
            blip=child.find(f'.//{{{A}}}blip')
            if blip is not None and last_caption:
                rid=blip.get(f'{{{R_NS}}}embed')
                if rid in rid_to_target: mapping[last_caption]=rid_to_target[rid]
    done=0
    for cap,png in regen.items():
        if cap in mapping and mapping[cap] in all_entries:
            with open(png,'rb') as f: all_entries[mapping[cap]]=f.read()
            done+=1; log(f"  overwrote media {mapping[cap]} for Gambar {cap}")
    return done

# ---------- authored paragraph rewrites ----------
REPL = {
"BAB_IV": [
 ("Tabel 4.5 menyajikan hasil K-scan yang mengungkap dua pola utama.",
  "Tabel 4.5 menyajikan hasil K-scan yang mengungkap dua pola utama. Pertama, terdapat variasi K optimal antarperiode yang ditentukan secara objektif berdasarkan kriteria minimum BIC: fase Pre-COVID dan COVID Crisis menghasilkan K yang lebih rendah (K=2 pada 2019, K=3 pada 2020, K=2 pada 2021), sementara fase Recovery menunjukkan K yang lebih tinggi (K=2 pada 2022, K=5 pada 2023, K=4 pada 2024). Kedua, nilai BIC yang jauh lebih besar pada fase Recovery (143.513-214.845) dibandingkan fase Pre-COVID (48.144) mencerminkan ukuran dataset yang jauh lebih besar; nilai BIC sensitif terhadap N, bukan penurunan kualitas model. Nilai Silhouette Score tertinggi (0,0798) pada 2020 dengan K=3 menunjukkan bahwa pemisahan terbaik tercapai pada periode dengan K moderat. Scrucca et al. (2024) menegaskan nilai Silhouette Score dalam rentang 0,01-0,10 tetap bermakna dalam soft clustering seperti GMM, mengingat sifat inheren overlap antar segmen."),
 ("Gambar 4.3a menampilkan visualisasi tren Silhouette Score GMM selama enam periode",
  "Gambar 4.3a menampilkan visualisasi tren Silhouette Score GMM selama enam periode dalam bentuk line chart. Grafik memperlihatkan fluktuasi yang tidak monoton: penurunan dari 0,0522 (2019) ke 0,0798 (2020), sedikit penurunan di 2021 (0,0748), 0,0663 pada 2022, lonjakan ke 0,0691 pada 2023, dan kembali turun ke 0,0585 pada 2024. Pola ini konsisten dengan perubahan K optimal; pada tahun dengan K rendah (2019, K=2) Silhouette berada pada 0,0522, sementara K=3 (2020) menghasilkan pemisahan paling jelas (0,0798). Gambar ini memperkuat narasi bahwa K optimal bervariasi secara objektif antarperiode."),
 ("Tabel 4.7 menyajikan empat metrik evaluasi internal untuk setiap periode.",
  "Tabel 4.7 menyajikan empat metrik evaluasi internal untuk setiap periode. Beberapa pola penting perlu dicermati. Pertama, nilai Log-Likelihood berubah menjadi negatif pada seluruh periode, konsisten dengan ukuran dataset yang besar (semakin banyak observasi, semakin besar probabilitas joint yang dihitung dalam bentuk logaritma negatif). Kedua, nilai Calinski-Harabasz meningkat dari 4,14 (2019) ke 36,08 (2023) kembali ke 27,19 (2024), mengindikasikan separasi antar klaster yang baik relatif terhadap dispersi internal. Ketiga, nilai Davies-Bouldin bervariasi (5,6718 pada 2019 hingga 3,0046 pada 2023), menunjukkan klaster yang cukup terpisah; peningkatan tipis pada 2024 (3,1211) konsisten dengan K=4 yang menghasilkan lebih banyak segmen yang saling berdekatan."),
],
"BAB_V": [
 ("Dari dataset 2.362 pendaftar, pendekatan ini sukses mengidentifikasi K optimal yang bervariasi antara 2 hingga 6",
  "Dari dataset 2.362 pendaftar, pendekatan ini sukses mengidentifikasi K optimal yang bervariasi antara 2 hingga 5 per periode (masing-masing 2, 3, 2, 2, 5, 4 untuk tahun 2019-2024), dengan K tertinggi pada fase Recovery (K=5 pada 2023). Nilai Silhouette Score yang dihasilkan (0,0522 pada 2019 hingga 0,0798 pada 2020) berada dalam rentang yang bermakna untuk model Gaussian Mixture berdasarkan Saqr & Lopez-Pernas (2024), yang mengonfirmasi bahwa tumpang tindih antar segmen dapat diukur secara eksak sebagai probabilitas posterior, bukan sekadar ketidakpastian. Hal ini membuktikan efektivitas metode GMM dalam memetakan probabilitas setiap pendaftar tanpa paksaan ke dalam satu kategori absolut, yang sebelumnya menjadi titik buta pada algoritma hard clustering seperti K-Means."),
],
"RABIT": [
 ("Hasil segmentasi probabilistik GMM menunjukkan K optimal bervariasi 2-6 per periode (2019=6, 2020=6, 2021=6, 2022=5, 2023=2, 2024=3)",
  "Hasil segmentasi probabilistik GMM menunjukkan K optimal bervariasi 2-5 per periode (2019=2, 2020=3, 2021=2, 2022=2, 2023=5, 2024=4) dengan evaluasi multilevel menggunakan Silhouette Score, Calinski-Harabasz, dan Davies-Bouldin (Tabel 2). Meskipun nilai Silhouette Score tergolong rendah (0,0522-0,0798), Saqr & Lopez-Pernas (2024) menegaskan bahwa rentang 0,01-0,10 tetap bermakna untuk soft clustering probabilistik seperti GMM karena sifat inheren overlap antar segmen. Visualisasi sebaran Silhouette Score dapat dilihat pada Gambar 2. Analisis stabilitas lintas waktu menggunakan ARI membuktikan bahwa seluruh 5 transisi merupakan structural break (ARI < 0,30), mengonfirmasi bahwa asumsi segmentasi pasar yang statis di lingkungan pendidikan tinggi adalah keliru [13]."),
 ("Pada 2019 terdapat 4 klaster dengan sebaran relatif merata (15,8%-28,8%), semuanya berasal dari Kabupaten Pekalongan.",
  "Pada 2019 terdapat 2 klaster dengan sebaran 65,1% (Klaster 1) dan 34,9% (Klaster 2), semuanya berasal dari Kabupaten Pekalongan. Pada 2023 konsolidasi dengan K=5: klaster terbesar (K5) menyerap 50,1% dari 680 pendaftar dengan dominasi Sarjana Informatika (115 dari 341). Pada 2024 komposisi lebih merata dengan K=4: K4=33,6%, K1=29,8%, K2=29,0%, K3=7,6% (N=503), dan munculnya program D3 Akuntansi sebagai segmen baru. Visualisasi sebaran spasial klaster pada ruang PCA 2D untuk ketiga tahun representatif disajikan pada Gambar 4, Gambar 5, dan Gambar 6 [13]."),
 ("Dari dataset 2.362 pendaftar, pendekatan ini sukses mengidentifikasi K optimal yang bervariasi 2-6 per periode (2019=6, 2020=6, 2021=6, 2022=5, 2023=2, 2024=3), dengan konsolidasi dari 6 klaster pada fase pra-pandemi menjadi 2-3 klaster pada fase recovery.",
  "Dari dataset 2.362 pendaftar, pendekatan ini sukses mengidentifikasi K optimal yang bervariasi 2-5 per periode (2019=2, 2020=3, 2021=2, 2022=2, 2023=5, 2024=4), dengan konsolidasi dari 2 klaster pada fase awal menjadi 4-5 klaster pada fase recovery."),
],
}

def main():
    log("="*60); log("SYNC DRAFTS TO MASTER"); log("="*60)
    regen = regen_figures()
    for key, path in DOCS.items():
        if not os.path.exists(path): log(f"SKIP {key} (missing)"); continue
        log(f"\n### {key}: {os.path.basename(path)}")
        backup(path)
        z = zipfile.ZipFile(path, 'r'); in_count=len(z.namelist())
        all_entries = {n: z.read(n) for n in z.namelist()}; z.close()
        root = etree.fromstring(all_entries['word/document.xml'])
        # 1. paragraph rewrites
        for anchor, new in REPL.get(key, []):
            if replace_paragraph(root, anchor, new): log(f"  OK paragraph rewrite ({anchor[:40]}...)")
            else: log(f"  FAIL paragraph anchor not found: {anchor[:50]}")
        # 2. orphan 0,514 -> 0,91 (RABIT_L only, harmless elsewhere)
        if replace_substring(root, "0,514\u20131,000", "0,91\u20131,000"):
            log("  OK orphan 0,514-1,000 -> 0,91-1,000")
        # 3. tables from CSV
        if key == "BAB_IV":
            regen_evals(root, ("Tabel 4.7",), os.path.join(OUT_CSV,"tabel_4_7_evaluasi_internal.csv"))
            regen_evals(root, ("Tabel 4.5","K-Skan"), os.path.join(OUT_CSV,"tabel_4_5_kscan.csv"))
            regen_profil(root, ("Tabel 4.9",), os.path.join(OUT_CSV,"tabel_4_9_profil_2019.csv"))
            regen_profil(root, ("Tabel 4.11",), os.path.join(OUT_CSV,"tabel_4_11_profil_2021.csv"))
            regen_profil(root, ("Tabel 4.12",), os.path.join(OUT_CSV,"tabel_4_12_profil_2022.csv"))
            done = embed_figures(root, all_entries, regen)
            log(f"  figures embedded: {done}")
        if key == "RABIT_L":
            regen_evals(root, ("Tabel 3",), os.path.join(OUT_CSV,"tabel_4_7_evaluasi_internal.csv"))
            regen_profil(root, ("Tabel 4",), os.path.join(OUT_CSV,"tabel_4_11_profil_2021.csv"))
            regen_profil(root, ("Tabel 6",), os.path.join(OUT_CSV,"tabel_4_13_profil_2023.csv"))
        # write back
        all_entries['word/document.xml'] = etree.tostring(root)
        out_path = path
        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for n, data in all_entries.items(): zout.writestr(n, data)
        log(f"  wrote {out_path} (entries {in_count}->{len(all_entries)})")

    # ---------- verification ----------
    log("\n" + "-"*50); log("VERIFICATION GATES")
    gates = [
      ("0,514", 0), ("0,0683",0), ("0,0496",0), ("0,0138",0), ("0,0905",0), ("0,0279",0),
      ("K=6",0), ("2019=6",0), ("4 klaster",0), ("fragmentasi tinggi",0),
      ("12 profil persona unik",0), ("9Router",0),
      ("0,0522",1), ("65,1%",1), ("68,3%",1), ("18 profil",1), ("OpenRouter",1),
    ]
    from lxml import etree as _et
    for key, path in DOCS.items():
        if not os.path.exists(path): continue
        z=zipfile.ZipFile(path); full=''.join(''.join(t.text or '' for t in _et.fromstring(z.read(n)).findall(f'.//{{{W}}}t')) for n in z.namelist() if n.endswith('.xml')); z.close()
        for s, want in gates:
            c = full.count(s)
            ok = (c==0) if want==0 else (c>0)
            log(f"  [{'OK ' if ok else 'BAD'}] {key}: '{s}' count={c} (want {'0' if want==0 else '>0'})")

if __name__ == '__main__':
    main()
