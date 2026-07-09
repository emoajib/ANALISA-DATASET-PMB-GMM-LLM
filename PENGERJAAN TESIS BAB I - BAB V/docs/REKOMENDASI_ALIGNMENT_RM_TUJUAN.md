# REKOMENDASI ALIGNMENT: Rumusan Masalah ↔ Tujuan Penelitian

## Analisis Gap

### Kondisi Saat Ini

| Rumusan Masalah (RQ)                | Tujuan Penelitian                      | Status   |
|--------------------------------------|----------------------------------------|----------|
| RQ1: Segmentasi GMM + IndoBERT       | T1: Analisis segmentasi GMM            | ✅ Match |
| RQ2: Evolusi klaster + structural break | T2: Ukur stabilitas + structural break | ✅ Match |
| RQ3: Otomasi LLM (persona, reasoning, personalisasi) | T3: Bangun sistem otomasi LLM | ✅ Match |
| ❌ **TIDAK ADA**                     | T4: Uji validitas via Expert Judgement  | ❌ **GAP** |

### Detail Gap

**Tujuan 4** (Par[62]):
> "Tujuan keempat menguji validitas hasil otomasi analisis LLM melalui perbandingan dengan pakar praktisi data sains dan rekrutmen (Expert Judgement) guna memastikan akurasi, aplikabilitas, dan relevansi strategi terhadap kebijakan institusional."

Tujuan ini **tidak memiliki Rumusan Masalah yang sesuai**. Ketiga RQ saat ini hanya mencakup:
1. Segmentasi (RQ1)
2. Stabilitas temporal (RQ2)  
3. Otomasi LLM (RQ3)

Validasi expert merupakan dimensi yang berbeda dari ketiga RQ di atas — validasi bukan bagian dari "otomasi" melainkan *evaluasi/verifikasi* terhadap output otomasi.

---

## OPSI REKOMENDASI

### OPSI A (Direkomendasikan): Tambah RQ4 Baru

Tambahkan Rumusan Masalah keempat (RQ4) yang secara eksplisit menanyakan validitas output sistem.

**Teks Rekomendasi untuk RQ4:**

> "Bagaimana validitas hasil otomasi analisis LLM berdasarkan penilaian pakar (Expert Judgement) dalam konteks enrollment management ITSNU Pekalongan, dan bagaimana implikasinya terhadap kebijakan rekrutmen institusi?"

**Letak:** Setelah RQ3 (Par[39]), sebagai butir (4) dalam daftar Rumusan Masalah.

**Dampak:**
- ✅ Tujuan 4 memiliki pasangan RQ
- ✅ Konsisten dengan struktur "setiap Tujuan punya RQ"
- ✅ Menambah cakupan tanpa menghapus konten

---

### OPSI B (Alternatif): Integrasikan ke RQ3

Perluas RQ3 untuk mencakup validasi:

**Teks Rekomendasi RQ3 yang Direvisi:**

> "Bagaimana sistem otomasi analisis LLM yang mencakup generasi persona, reasoning kausal, personalisasi rekrutmen, dan validasi output melalui Expert Judgement dapat dioptimalkan untuk enrollment management ITSNU Pekalongan?"

**Dampak:**
- ✅ Tidak perlu RQ baru
- ⚠️ RQ3 jadi lebih panjang dan kurang fokus
- ⚠️ Validasi adalah aktivitas *evaluasi*, bukan bagian dari "otomasi" — secara konseptual kurang tepat

---

### OPSI C (Tidak Direkomendasikan): Hapus Tujuan 4

**Dampak:**
- ❌ Menghilangkan kontribusi penting: validasi expert adalah elemen kunci dari pendekatan *Expert-in-the-Loop*
- ❌ Bertentangan dengan H3b yang membutuhkan validasi
- ❌ Menghilangkan bukti empiris dari Tabel 4.19 dan narasi 4.9

---

## REKOMENDASI FINAL: OPSI A

**Tambah RQ4** dengan teks berikut pada Par[39] (setelah RQ3):

```
(4) Bagaimana validitas hasil otomasi analisis LLM berdasarkan penilaian 
pakar (Expert Judgement) dalam konteks enrollment management ITSNU 
Pekalongan, dan bagaimana implikasinya terhadap kebijakan rekrutmen institusi?
```

### Justifikasi:

1. **Konsistensi struktural:** Setiap Tujuan punya RQ pendamping.
2. **Kelayakan akademik:** RQ4 membuka ruang pembahasan untuk sub-bab 4.9 (Hasil Validasi Pakar) dan 4.10.3 (Kontribusi Sistem Otomasi LLM).
3. **Tidak mengubah konten:** Tidak perlu menghapus atau mengubah Tujuan 4 maupun bagian lain.
4. **Memenuhi kaidah penelitian:** Rumusan masalah harus mencakup seluruh tujuan penelitian.
5. **Memperkuat kontribusi:** Validasi expert adalah pembeda penelitian ini dari penelitian segmentasi konvensional.

---

*Dibuat oleh: @explore mode | 2026-06-08*
