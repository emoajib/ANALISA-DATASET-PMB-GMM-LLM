# STRATEGI SEGMENTASI PROBABILISTIK CALON MAHASISWA MENGGUNAKAN GAUSSIAN MIXTURE MODEL DAN OTOMASI ANALISIS LARGE LANGUAGE MODEL UNTUK OPTIMALISASI REKRUTMEN DI ITSNU PEKALONGAN

Penelitian ini mengembangkan strategi segmentasi probabilistik calon mahasiswa menggunakan Gaussian Mixture Model (GMM) dan otomasi analisis Large Language Model (LLM) untuk optimalisasi rekrutmen di Institut Teknologi Dan Sains Nahdlatul Ulama Pekalongan (ITSNU Pekalongan) berdasarkan data penerimaan mahasiswa baru periode 2019-2024.

## Struktur Proyek

```
├── src/                          # Kode sumber utama
│   ├── pmb_pipeline.py          # Pipeline analisis CRISP-DM
│   └── app.py                   # Aplikasi Streamlit dashboard
├── data/                        # Data dan dataset
│   ├── geo/                     # Data geografis Indonesia
│   │   ├── geo_data/           # Prosesing koordinat geografis
│   │   └── geografis_data/     # Library Node.js untuk data wilayah
│   └── DATASET PMB ITSNUPKL2019-2024_FIX.xls  # Dataset PMB
├── outputs/                     # Hasil analisis dan visualisasi
│   ├── tabel_*.csv             # Tabel hasil analisis
│   └── gambar_*.png/svg        # Visualisasi grafik
├── docs/                        # Dokumentasi tesis
│   ├── Tesis_ITSNU_GMM_LLM.docx
│   ├── BAB III.txt
│   └── thesis.txt
├── notebooks/                   # Notebook analisis (jika ada)
├── requirements.txt             # Dependensi Python
└── README.md                    # Dokumentasi proyek
```

## Instalasi dan Setup

1. Clone repository ini
2. Install dependensi Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi:
   ```bash
   streamlit run src/app.py
   ```

## Metodologi

Proyek ini menggunakan metodologi CRISP-DM (Cross Industry Standard Process for Data Mining) yang dikembangkan menjadi 10 langkah implementasi detail untuk analisis PMB ITSNU Pekalongan 2019-2024:

1. **Business Understanding**: Pemetaan kebutuhan rekrutmen ITSNU Pekalongan multi-periode dengan identifikasi pertanyaan bisnis kritis seperti segmentasi calon mahasiswa potensial, perubahan profil akibat pandemi, dan prioritas kampanye 2025. Definisi operasional otomasi analisis LLM untuk ekstraksi fitur, generasi persona, dan reasoning kausal.

2. **Data Collection**: Pengumpulan dataset sekunder calon mahasiswa ITSNU Pekalongan 2019-2024 dari sistem informasi akademik. Dataset mencakup spesifikasi atribut: nama (tekstual), tahun pendaftaran (kategorikal), asal sekolah (tekstual), program studi (kategorikal), kecamatan/kabupaten (kategorikal), alamat (tekstual), dan jenis jalur penerimaan (kategorikal). Definisi fase temporal: Pre-COVID (2019) sebagai baseline normal, COVID Crisis (2020-2021) sebagai fase disrupsi pandemi, dan Recovery (2022-2024) sebagai fase pemulihan transformasi digital.

3. **Data Understanding**: Analisis profil statistik deskriptif per periode dengan distribusi frekuensi variabel kategorikal, statistik ringkas, dan visualisasi bar chart pendaftar per tahun. Deteksi anomali dan missing values melalui pemeriksaan konsistensi format, identifikasi nilai hilang, dan deteksi duplikat. Validasi konsistensi kategori untuk penyeragaman format program studi antar tahun.

4. **Data Preparation (Otomasi Batch 6 Periode)**: Otomasi preprocessing untuk 6 periode dengan subproses text preprocessing (case folding, cleaning, normalisasi singkatan seperti JL→Jalan, DS→Desa), ekstraksi fitur semantik IndoBERT (model base-p1, mean pooling, validasi cosine similarity >0.70), geocoding koordinat dengan GeoPy/Nominatim dan data geografis Indonesia, encoding variabel kategorikal (LabelEncoder fit 2019, unseen categories → 'Unknown'), serta integrasi fitur (embedding 768 + geo 2 + encoded 3 = ~773 fitur) dengan standardisasi menggunakan StandardScaler.

5. **Dimensionality Reduction**: Reduksi dimensi dengan PCA 95% variance yang difit pada data 2019 untuk memastikan konsistensi ruang fitur antar periode.

6. **Modeling**: Clustering GMM per periode dengan penentuan K optimal menggunakan kombinasi BIC minimum, AIC, dan Silhouette score. Parameter GMM: covariance_type=full, init_params=k-means++, max_iter=300, n_init=10, random_state=42, tol=1e-3.

7. **Time Series Analysis**: Deteksi structural break menggunakan ARI <0.30, Jaccard overlap, dan Euclidean centroid drift. Forecasting pendaftaran 2025 dengan regresi linier pada fase Recovery (2022-2024).

8. **Evaluation**: Evaluasi multi-level meliputi metrik internal GMM (Silhouette, Calinski-Harabasz, Davies-Bouldin, Log Likelihood), analisis stabilitas temporal (ARI >0.60 stabil, <0.30 break), komparasi GMM vs K-Means per periode, serta validasi eksternal melalui diskusi fokus tim rekrutmen untuk menilai relevansi persona dan feasibility rekomendasi.

9. **Otomasi Analisis LLM**: Generasi narasi persona mahasiswa (<150 kata) berdasarkan profil GMM, reasoning kausal untuk perubahan cluster antar tahun dengan integrasi ARI dan konteks historis, serta ringkasan naratif komprehensif menggunakan Ollama Llama 3.2.

10. **Deployment**: Formulasi strategi rekrutmen prediktif dengan prioritisasi segmen dinamis berdasarkan lifecycle analysis, mapping channel komunikasi, proyeksi pendaftaran 2025, dan personalisasi rekrutmen melalui persona yang dihasilkan otomatis.

## Fitur Utama

- **Otomasi analisis LLM dengan Ollama (Llama 3.2)**: Generasi narasi persona mahasiswa, reasoning kausal tren temporal, dan ringkasan naratif otomatis untuk tabel dan visualisasi
- **Embedding semantik IndoBERT**: Ekstraksi fitur tekstual dari nama, alamat, dan asal sekolah mahasiswa dengan model IndoBERT base-p1 untuk analisis kesamaan semantik
- **Geocoding dengan data geografis Indonesia**: Konversi alamat tekstual ke koordinat geografis menggunakan GeoPy dan dataset GeoPy untuk pemetaan spasial mahasiswa
- **Multiple algoritma clustering**: Implementasi Gaussian Mixture Model (GMM) dan K-Means dengan evaluasi komparatif menggunakan metrik Silhouette, ARI, dan Jaccard similarity
- **Analisis temporal dengan ARI dan Jaccard**: Deteksi structural break antar periode menggunakan Adjusted Rand Index (ARI <0.30 sebagai threshold break) dan Jaccard overlap untuk stabilitas cluster
- **Pipeline otomasi batch 6 periode**: Preprocessing paralel untuk data 2019-2024 dengan validasi cosine similarity embedding antar tahun
- **Evaluasi multi-level**: Metrik internal clustering, stabilitas temporal, dan validasi eksternal melalui persona mahasiswa
- **Proyeksi prediktif 2025**: Forecasting pendaftaran menggunakan regresi linier pada fase Recovery dengan analisis lifecycle cluster
- **Visualisasi interaktif Streamlit**: Dashboard real-time dengan progress tracking dan narrative generation otomatis
- **Strategi deployment**: Prioritisasi segmen rekrutmen berdasarkan analisis lifecycle dan personalisasi komunikasi

## Dataset

Dataset PMB ITSNU Pekalongan 2019-2024 diperoleh dari sistem informasi akademik dengan spesifikasi tabel 3.1:

**Atribut Utama:**
- Nama mahasiswa (tekstual)
- Tahun pendaftaran (kategorikal: 2019-2024)
- Asal sekolah (tekstual: nama sekolah menengah)
- Program studi (kategorikal: S1 Informatika, S1 Teknologi Informasi, D3 Akuntansi, dll.)
- Kecamatan asal (kategorikal)
- Kabupaten/Kota asal (kategorikal)
- Alamat lengkap (tekstual)
- Jenis jalur penerimaan (kategorikal: KIPK, Bidikmisi, Umum, dll.)

**Pipeline Transformasi Data:**
- **Text Preprocessing**: Case folding, cleaning, normalisasi singkatan (JL→Jalan, DS→Desa, SMK→Sekolah Menengah Kejuruan)
- **Feature Engineering**: Embedding IndoBERT 768-dimensi dari kombinasi nama + sekolah + kabupaten + kecamatan + alamat
- **Geospatial Encoding**: Koordinat latitude/longitude dari geocoding menggunakan dataset geografis Indonesia
- **Categorical Encoding**: Label encoding untuk program studi, jalur penerimaan, dan kabupaten (fit pada data 2019)
- **Feature Integration**: Gabungan embedding (768) + geospatial (2) + encoded (3) = ~773 fitur total
- **Standardisasi**: StandardScaler fit pada data 2019 untuk konsistensi temporal
- **Dimensionality Reduction**: PCA 95% variance menghasilkan ~100-150 komponen utama

**Statistik Dataset:**
- Total records: ~5000+ mahasiswa (varies per tahun)
- Periode temporal: 6 tahun dengan fase Pre-COVID, COVID Crisis, dan Recovery
- Validasi kualitas: Missing values <5%, cosine similarity embedding antar periode >0.70 pada fase stabil

## Teknologi

**Core Libraries:**
- **Streamlit**: Framework dashboard interaktif untuk visualisasi dan kontrol pipeline
- **Scikit-learn**: Algoritma machine learning (GMM, K-Means, PCA, StandardScaler, metrik evaluasi)
- **Transformers (IndoBERT)**: Model bahasa Indonesia untuk embedding semantik (indobenchmark/indobert-base-p1)
- **Ollama**: Runtime LLM lokal untuk generasi narasi dengan model Llama 3.2 3B
- **GeoPy**: Library geocoding untuk konversi alamat ke koordinat geografis
- **Pandas & NumPy**: Manipulasi dan analisis data tabular
- **Matplotlib**: Visualisasi grafik distribusi dan tren temporal

**Infrastructure:**
- **Python 3.8+**: Runtime utama dengan dependency management via requirements.txt
- **Dataset GeoPy**: File CSV geografis Indonesia untuk geocoding fallback
- **Persistent Storage**: Output CSV untuk tabel hasil analisis dan PNG/SVG untuk visualisasi

## Arsitektur Pipeline

Pipeline analisis mengikuti arsitektur sequential dengan dependency enforcement dalam Streamlit session state:

```
Data Input (XLS) → Business Understanding → Data Collection → Data Understanding
    ↓
Data Preparation (Batch 6 Periode) → Dimensionality Reduction → Modeling (GMM per Periode)
    ↓
Time Series Analysis → Evaluation (Multi-level) → Otomasi LLM (Persona + Reasoning)
    ↓
Deployment (Strategi Prediktif 2025)
```

**Karakteristik Arsitektur:**
- **Sequential Dependencies**: Setiap langkah harus complete sebelum unlock langkah berikutnya
- **State Management**: Session state tracking progress dan error handling per langkah
- **Batch Processing**: Otomasi paralel untuk 6 periode (2019-2024) dalam data preparation
- **Temporal Consistency**: StandardScaler dan PCA fit pada baseline 2019 untuk konsistensi ruang fitur
- **LLM Integration**: Otomasi narasi menggunakan prompt engineering terstruktur dengan fallback multi-token
- **Output Generation**: CSV tables, PNG charts, dan narrative text untuk dokumentasi tesis

**Validasi Pipeline:**
- Cosine similarity embedding >0.70 antar periode stabil
- ARI >0.60 untuk stabilitas cluster temporal
- Silhouette score >0.5 untuk kualitas clustering
- LLM persona <150 kata dengan koreksi typo otomatis

## Lisensi

Dikembangkan untuk keperluan tesis akademik.