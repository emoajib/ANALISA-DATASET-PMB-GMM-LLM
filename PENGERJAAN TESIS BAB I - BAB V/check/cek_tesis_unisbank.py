#!/usr/bin/env python3
"""
=============================================================
  CEK KEPATUHAN TESIS — Pedoman UNISBANK (Magister TI)
  Versi 1.0 | Berdasarkan Pedoman_Penulisan_Tesis-v_1_7.pdf
=============================================================

CARA PAKAI:
    python3 cek_tesis_unisbank.py <path_file_tesis.pdf>
    python3 cek_tesis_unisbank.py <path_file_tesis.docx>
"""

import sys, os, re, json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple
from datetime import datetime

class C:
    RESET="\033[0m"; BOLD="\033[1m"; GREEN="\033[92m"
    YELLOW="\033[93m"; RED="\033[91m"; CYAN="\033[96m"; DIM="\033[2m"

def ok(m): return f"{C.GREEN}\u2713{C.RESET} {m}"
def warn(m): return f"{C.YELLOW}\u26a0{C.RESET} {m}"
def err(m): return f"{C.RED}\u2717{C.RESET} {m}"
def info(m): return f"{C.CYAN}\u2139{C.RESET} {m}"

@dataclass
class Temuan:
    kategori: str; status: str; pesan: str; detail: str=""; referensi: str=""

@dataclass
class HasilCek:
    temuan: List[Temuan]=field(default_factory=list)
    def tambah(self,k,s,p,d="",r=""): self.temuan.append(Temuan(k,s,p,d,r))
    @property
    def ok(self): return sum(1 for t in self.temuan if t.status=="OK")
    @property
    def warn_(self): return sum(1 for t in self.temuan if t.status=="PERINGATAN")
    @property
    def err_(self): return sum(1 for t in self.temuan if t.status=="TIDAK SESUAI")
    @property
    def inf_(self): return sum(1 for t in self.temuan if t.status=="INFO")

def ekstrak_pdf(path):
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            meta={"jumlah_halaman":len(pdf.pages)}
            teks=[]
            for i,hal in enumerate(pdf.pages):
                t=hal.extract_text() or ""; teks.append(t)
                if i==0:
                    meta["ukuran_kertas_cm"]=(round(hal.width*0.0353,1),round(hal.height*0.0353,1))
            return teks,meta
    except ImportError:
        print(err("Install: pip install pdfplumber")); sys.exit(1)

def ekstrak_docx(path):
    try:
        import docx as pydocx
        doc=pydocx.Document(path)
        paras=[p.text for p in doc.paragraphs]
        meta={"jumlah_paragraf":len(paras)}
        if doc.sections:
            s=doc.sections[0]
            meta.update(margin_atas=s.top_margin.cm,margin_bawah=s.bottom_margin.cm,
                       margin_kiri=s.left_margin.cm,margin_kanan=s.right_margin.cm,
                       lebar_kertas=s.page_width.cm,tinggi_kertas=s.page_height.cm)
        return paras,meta
    except ImportError:
        print(err("Install: pip install python-docx")); sys.exit(1)

# ── Modul Pemeriksaan ──────────────────────────────────────────────────────────

def cek_kelengkapan(teks,hasil):
    kat="Kelengkapan Bagian Tesis"; tl=teks.lower()
    cek={
        "Cover/Judul":r"sampul|cover","Kata Pengantar":r"kata\s+pengantar",
        "Daftar Isi":r"daftar\s+isi","Abstrak":r"abstrak",
        "Daftar Tabel":r"daftar\s+tabel","Daftar Gambar":r"daftar\s+gambar",
        "Pernyataan Keaslian":r"pernyataan\s+keaslian",
        "BAB I Pendahuluan":r"bab\s+i.*pendahuluan",
        "BAB II Studi Pustaka":r"bab\s+ii.*studi\s+pustaka",
        "BAB III Metodologi":r"bab\s+iii.*metodologi",
        "BAB IV Pembahasan":r"(bab\s+iv|hasil\s+(dan\s+)?pembahasan)",
        "BAB V Kesimpulan":r"(bab\s+v|kesimpulan(\s+dan\s+saran)?)",
        "Daftar Pustaka":r"daftar\s+pustaka",
        "Latar Belakang":r"latar\s+belakang","Rumusan Masalah":r"rumusan\s+masalah",
        "Tujuan Penelitian":r"tujuan(\s+penelitian)?","Manfaat Penelitian":r"manfaat\s+penelitian",
    }
    for nama,pola in cek.items():
        if re.search(pola,tl):
            hasil.tambah(kat,"OK",f"{nama} \u2713")
        else:
            hasil.tambah(kat,"PERINGATAN",f"{nama} tidak terdeteksi")

def cek_margin(meta,hasil):
    kat="Margin & Kertas"
    w=meta.get("lebar_kertas"); h=meta.get("tinggi_kertas")
    if w and abs(w-21)<0.5 and abs(h-29.7)<0.5:
        hasil.tambah(kat,"OK","Kertas A4 (21x29.7 cm)")
    else:
        hasil.tambah(kat,"PERINGATAN",f"Kertas: {w}x{h} cm — bukan A4")
    for nama,key,target in [("Atas","margin_atas",4),("Bawah","margin_bawah",3),
                            ("Kiri","margin_kiri",4),("Kanan","margin_kanan",3)]:
        v=meta.get(key)
        if v and abs(v-target)<0.3:
            hasil.tambah(kat,"OK",f"Margin {nama}: {v:.1f} cm")
        else:
            hasil.tambah(kat,"PERINGATAN",f"Margin {nama}: {v} cm (target {target} cm)")

def cek_sitasi(teks,hasil):
    kat="Sitasi & Daftar Pustaka"
    sits=re.findall(r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?(?:\s+[&dan]+\s+[A-Z][a-z]+)?,\s*(19|20)\d{2}[a-z]?\)',teks)
    if sits:
        hasil.tambah(kat,"OK",f"Sitasi APA: {len(sits)} kemunculan")
    else:
        hasil.tambah(kat,"PERINGATAN","Sitasi APA tidak terdeteksi")
    ieee=re.findall(r'\[\d+\]',teks)
    if ieee:
        hasil.tambah(kat,"TIDAK SESUAI",f"IEEE [{len(ieee)}] — harus APA")
    entry=re.findall(r'^[A-Z][a-z]+,\s+[A-Z]\..*?\(\d{4}\)\.',teks,re.MULTILINE)
    if len(entry)>=8:
        hasil.tambah(kat,"OK",f"DP: {len(entry)} entri APA")
    else:
        hasil.tambah(kat,"PERINGATAN",f"DP: {len(entry)} entri (min 8)")

def cek_kata_orang(teks,hasil):
    kat="Kata Ganti Orang"
    teks_isi=re.split(r'kata\s+pengantar',teks,flags=re.I)[-1]  # skip kata pengantar
    found=set(re.findall(r'\b(saya|aku|kami|kita|kamu|anda)\b',teks_isi,re.I))
    if not found:
        hasil.tambah(kat,"OK","Tidak ada kata ganti orang di isi")
    else:
        hasil.tambah(kat,"TIDAK SESUAI",f"Ditemukan: {', '.join(found)}")

def cek_hipotesis(teks,hasil):
    kat="Hipotesis"
    if re.search(r'hipotesis',teks,re.I):
        hasil.tambah(kat,"OK","Hipotesis ditemukan")
    else:
        hasil.tambah(kat,"INFO","Hipotesis tidak ditemukan (opsional)")

def cetak_laporan(hasil,nama_file):
    lebar=72
    print(f"\n{C.BOLD}{'='*lebar}{C.RESET}")
    print(f"{C.BOLD}  LAPORAN KEPATUHAN TESIS \u2014 UNISBANK (Magister TI){C.RESET}")
    print(f"{C.BOLD}{'='*lebar}{C.RESET}")
    print(f"  File    : {nama_file}")
    print(f"  Tanggal : {datetime.now().strftime('%d %B %Y, %H:%M')}")
    stat_map={"OK":(C.GREEN,"\u2713"),"PERINGATAN":(C.YELLOW,"\u26a0"),"TIDAK SESUAI":(C.RED,"\u2717"),"INFO":(C.CYAN,"\u2139")}
    for t in hasil.temuan:
        w,l=stat_map.get(t.status,(C.DIM,"?"))
        print(f"  {w}{l}{C.RESET} [{t.kategori}] {t.pesan}")
        if t.detail: print(f"    {t.detail}")
    print(f"\n{'='*lebar}")
    print(f"  {C.GREEN}\u2713 Sesuai: {hasil.ok}{C.RESET}  {C.YELLOW}\u26a0 Peringatan: {hasil.warn_}{C.RESET}  {C.RED}\u2717 Tidak Sesuai: {hasil.err_}{C.RESET}  {C.CYAN}\u2139 Info: {hasil.inf_}{C.RESET}")
    skor=round(hasil.ok/max(hasil.ok+hasil.warn_+hasil.err_,1)*100)
    warna=C.GREEN if skor>=85 else C.YELLOW if skor>=65 else C.RED
    print(f"  Skor: {warna}{skor}%{C.RESET}")
    print(f"{'='*lebar}\n")

def main():
    if len(sys.argv)<2:
        print("Pakai: python3 cek_tesis_unisbank.py <file.pdf|.docx>"); sys.exit(0)
    path=sys.argv[1]
    if not os.path.exists(path): print(err("File tidak ada")); sys.exit(1)
    ext=Path(path).suffix.lower(); hasil=HasilCek()
    if ext==".pdf":
        teks,meta=ekstrak_pdf(path)
        teks_gabung="\n".join(teks)
    elif ext==".docx":
        teks,meta=ekstrak_docx(path)
        teks_gabung="\n".join(teks)
        cek_margin(meta,hasil)
    else: print(err("Format tidak didukung")); sys.exit(1)
    cek_kelengkapan(teks_gabung,hasil)
    cek_sitasi(teks_gabung,hasil)
    cek_kata_orang(teks_gabung,hasil)
    cek_hipotesis(teks_gabung,hasil)
    cetak_laporan(hasil,Path(path).name)
    json_path=str(Path(path).stem)+"_kepatuhan.json"
    with open(json_path,"w",encoding="utf-8") as f:
        json.dump({"file":Path(path).name,"tanggal":datetime.now().isoformat(),
                    "temuan":[{"kategori":t.kategori,"status":t.status,"pesan":t.pesan} for t in hasil.temuan]},
                   f,ensure_ascii=False,indent=2)
    print(info(f"Laporan: {json_path}"))

if __name__=="__main__": main()
