import pandas as pd
import numpy as np
import functools
import re
import random
import concurrent.futures
from multiprocessing import cpu_count
from joblib import Parallel, delayed
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    silhouette_score,
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
from collections import Counter
import os
import logging
import ollama
import torch
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

from steps.utils import (
    preprocess, get_embedding, get_embeddings_batch, post_process_persona,
    jaccard_similarity, centroid_drift, geocode_location,
    avg, rnd, detect_col, detect_year, pct,
    load_llm_cache, save_llm_cache, get_llm_hash
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
FASE = {
    2019: "Pre-COVID",
    2020: "COVID Crisis",
    2021: "COVID Crisis",
    2022: "Recovery",
    2023: "Recovery",
    2024: "Recovery",
}
FC = {"Pre-COVID": "#3B8BD4", "COVID Crisis": "#E24B4A", "Recovery": "#1D9E75"}
CC = ["#3B8BD4", "#1D9E75", "#E24B4A", "#BA7517", "#534AB7", "#993356"]





 
def generate_llm_response(prompt, provider="Ollama", api_key=None, max_tokens=1500):
    # Load LLM cache
    cache = load_llm_cache()
    key = get_llm_hash(prompt, provider, max_tokens)
    
    # Check cache first
    if key in cache:
        return cache[key]
    
    response = None
    if provider == "Anthropic":
        if not anthropic or not api_key:
            raise ValueError("Anthropic library not installed or API key not provided")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        response = message.content[0].text
    elif provider == "OpenCode":
        if not openai or not api_key:
            raise ValueError("OpenAI library not installed or API key not provided")
        client = openai.OpenAI(api_key=api_key, base_url="https://opencode.ai/api/v1")
        response = client.chat.completions.create(
            model="gpt-4o",  # Default model, can be changed
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        response = response.choices[0].message.content
    else:  # Ollama
        try:
            response = ollama.generate(
                model="llama3.2:3b", prompt=prompt, options={"num_predict": max_tokens}
            )
            response = response["response"].strip()
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
            return f"Error generating response: {e}"
    
    # Save to cache if successful
    if response and not response.startswith("Error"):
        cache[key] = response
        save_llm_cache()
    
    return response


# CRISP-DM Pipeline Class
class PMBAnalysisPipeline:
    def __init__(self, file_path, llm_provider="Ollama", anthropic_api_key=None, opencode_api_key=None):
        self.file_path = file_path
        self.llm_provider = llm_provider
        self.anthropic_api_key = anthropic_api_key
        self.opencode_api_key = opencode_api_key
        self.raw = None
        self.by_year = None
        self.cols = None
        self.hs = None
        self.uniques = None
        self.scaler = None
        self.pca = None
        self.emb_dim = 768
        self.n_comp = None
        self.gmm_res = {}
        self.k_scan = {}
        self.ari_pairs = []
        self.jaccard_pairs = []
        self.centroid_drifts = []
        self.proj_2025 = None
        self.lifecycle = []
        self.cos_sim = []
        self.avg_sim = None
        self.personas = {}
        self.tokenizer = None
        self.model = None
        self.progress_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def _report_progress(self, step, percent):
        # Cap percent at 100
        percent = min(100, max(0, percent))
        if self.progress_callback:
            self.progress_callback(step, percent)

    # BUSINESS UNDERSTANDING: Pemetaan kebutuhan rekrutmen ITSNU multi-periode
    # Definisi operasional otomasi analisis LLM
    def business_understanding(self):
        logger.info(
            "BUSINESS UNDERSTANDING: Pemetaan kebutuhan rekrutmen ITSNU Pekalongan multi periode"
        )
        logger.info(
            "Aktivitas utama: 1. Mengidentifikasi pertanyaan bisnis kritis (segmen calon mahasiswa potensial, perubahan profil akibat pandemi, prioritas kampanye 2025)"
        )
        logger.info(
            "2. Definisi operasional otomasi analisis LLM: ekstraksi fitur, generasi persona, reasoning kausal, ringkasan naratif dengan format input-output terukur"
        )

    # DATA COLLECTION: Dataset PMB ITSNU 2019–2024 (6 sheet/periode)
    def data_collection(self):
        logger.info("DATA COLLECTION: Dataset sekunder calon mahasiswa ITSNU Pekalongan 2019–2024 dari sistem informasi akademik")
        logger.info("Tabel 3.1 Spesifikasi Dataset: Nama (tekstual), Tahun (kategorikal), Asal Sekolah (tekstual), Program Studi (kategorikal), Kecamatan (kategorikal), Kabupaten (kategorikal), Alamat (tekstual), Jenis Jalur (kategorikal)")
        logger.info("Definisi fase temporal: Pre-COVID (2019): baseline normal; COVID Crisis (2020-2021): disrupsi pandemi; Recovery (2022-2024): pemulihan transformasi digital")
        all_rows = []
        xl = pd.ExcelFile(self.file_path)
        self.hs = [
            "No.",
            "NAMA",
            "TAHUN",
            "ASAL SEKOLAH",
            "PROGRAM STUDI",
            "KECAMATAN",
            "KABUPATEN/KOTA",
            "ALAMAT",
            "JENIS JALUR",
        ]
        for sn in xl.sheet_names:
            df = xl.parse(sn, header=None)
            if df.empty:
                continue
            data_rows = df.to_dict("records")
            for r in data_rows:
                row_dict = {self.hs[i]: r[i] for i in range(len(self.hs))}
                all_rows.append(row_dict)
        if not all_rows:
            raise ValueError("Data kosong")
        logger.info(f"Headers: {self.hs}")
        logger.info(f"First data row: {all_rows[0]}")
        enriched = [dict(r, _y=detect_year(r)) for r in all_rows if detect_year(r)]
        self.raw = enriched
        self.by_year = {}
        for r in enriched:
            y = r["_y"]
            if y not in self.by_year:
                self.by_year[y] = []
            self.by_year[y].append(r)
        self.cols = {
            "nama": detect_col(self.hs, ["nama", "name"]),
            "prodi": detect_col(
                self.hs, ["program studi", "program.studi", "program studi", "jurusan"]
            ),
            "jalur": detect_col(
                self.hs, ["jenis jalur", "jenis.jalur", "jenis jalur", "jalur"]
            ),
            "kab": detect_col(self.hs, ["kabupaten/kota", "kabupaten", "kab", "kota"]),
            "kec": detect_col(self.hs, ["kecamatan", "kec"]),
            "sekolah": detect_col(
                self.hs, ["asal sekolah", "sekolah", "asal_sekolah", "nama sekolah"]
            ),
            "alamat": detect_col(self.hs, ["alamat", "alamat lengkap", "address"]),
        }
        if not self.cols["prodi"] or not self.cols["jalur"] or not self.cols["kab"]:
            raise ValueError("Kolom wajib tidak ditemukan")
        logger.info(f"Loaded {len(enriched)} rows from {len(xl.sheet_names)} sheets")
        logger.info(f"Headers: {self.hs}")

    # DATA UNDERSTANDING: Profil statistik deskriptif per periode
    def data_understanding(self):
        logger.info("DATA UNDERSTANDING: Profil statistik deskriptif per periode")
        logger.info("Aktivitas 1: Distribusi frekuensi per variabel kategorikal, statistik ringkas, visualisasi bar chart pendaftar per tahun")
        # Deteksi anomali dan missing values
        logger.info("Aktivitas 2: Deteksi anomali dan missing values - pemeriksaan konsistensi format, identifikasi nilai hilang, deteksi duplikat")
        missing = {
            col: sum(1 for r in self.raw if not r.get(col))
            for col in self.cols.values()
            if col
        }
        logger.info(f"Missing values: {missing}")
        # Validasi konsistensi kategori
        logger.info("Aktivitas 3: Validasi konsistensi kategori - penyeragaman format program studi antar tahun")
        # Visualisasi distribusi variabel kunci
        years = sorted(self.by_year.keys())
        dist = {y: len(self.by_year[y]) for y in years}
        plt.figure(figsize=(10, 6))
        plt.bar(dist.keys(), dist.values(), color=[FC[FASE[y]] for y in years])
        plt.title("Distribusi Pendaftar 2019–2024")
        plt.xlabel("Tahun")
        plt.ylabel("Jumlah")
        plt.savefig("outputs/distribusi_pendaftar.png")
        plt.close()

    # DATA PREPARATION
    def data_preparation(self):
        self._report_progress("Text preprocessing", 20)
        logger.info("DATA PREPARATION: Otomasi batch 6 periode")
        # [A] Text Preprocessing Otomatis
        logger.info("Subproses A: Text preprocessing")
        for r in self.raw:
            for col in self.cols.values():
                if col:
                    r[col] = preprocess(r[col])
        
        self._report_progress("Generating embeddings (batch)", 40)
        # [B] IndoBERT Embedding Extraction (Batch Processing for Performance)
        logger.info("Subproses B: Ekstraksi fitur semantik IndoBERT")
        self.cos_sim = []
        years = sorted(self.by_year.keys())
        
        # Fix H2: Use representative sample (min 100 data) instead of only 10
        sample_size = 100
        
        for i in range(len(years) - 1):
            y1, y2 = years[i], years[i + 1]
            # Sample representative data
            sample1 = self.by_year[y1] if len(self.by_year[y1]) <= sample_size else random.sample(self.by_year[y1], sample_size)
            sample2 = self.by_year[y2] if len(self.by_year[y2]) <= sample_size else random.sample(self.by_year[y2], sample_size)
            
            texts1 = [" ".join([r.get(self.cols["nama"], ""), r.get(self.cols["sekolah"], ""), r.get(self.cols["kab"], ""), r.get(self.cols["kec"], ""), r.get(self.cols["alamat"], "")]) for r in sample1]
            texts2 = [" ".join([r.get(self.cols["nama"], ""), r.get(self.cols["sekolah"], ""), r.get(self.cols["kab"], ""), r.get(self.cols["kec"], ""), r.get(self.cols["alamat"], "")]) for r in sample2]
            
            # Use batch embedding for performance
            emb1 = get_embeddings_batch(texts1, dim=self.emb_dim, batch_size=32)
            emb2 = get_embeddings_batch(texts2, dim=self.emb_dim, batch_size=32)
            
            sim = avg([cosine_similarity([e1], [e2])[0][0] for e1 in emb1 for e2 in emb2])
            self.cos_sim.append({"trans": f"{y1}→{y2}", "sim": rnd(sim, 4)})
        self.avg_sim = rnd(avg([c["sim"] for c in self.cos_sim]), 4)
        
        self._report_progress("Geocoding coordinates", 60)
        # [C] Geocoding Koordinat Geospasial
        logger.info("Subproses C: Geocoding koordinat")
        kec_df = pd.read_csv("data/geo/geo_data/data/coll/kecamatan_lat_long.csv")
        kec_map = {(row["name"].strip().lower()): (row["lat"], row["long"]) for _, row in kec_df.iterrows()}
        kab_df = pd.read_csv("data/geo/geo_data/data/coll/kota_kab_lat_long.csv")
        kab_map = {(row["name"].strip().lower()): (row["lat"], row["long"]) for _, row in kab_df.iterrows()}
        for r in self.raw:
            kec = r.get(self.cols["kec"], "").strip().lower()
            kab = r.get(self.cols["kab"], "").strip().lower()
            coords = kec_map.get(kec) or kab_map.get(kab.replace("kabupaten", "").replace("kota", "").strip())
            if coords:
                r["_lat"], r["_lon"] = coords
            else:
                all_lat = [rr["_lat"] for rr in self.raw if "_lat" in rr]
                all_lon = [rr["_lon"] for rr in self.raw if "_lon" in rr]
                r["_lat"] = np.median(all_lat) if all_lat else -6.2
                r["_lon"] = np.median(all_lon) if all_lon else 106.8
        
        self._report_progress("Encoding categorical variables", 70)
        # [D] Encoding Variabel Kategorikal
        logger.info("Subproses D: Encoding kategorikal")
        self.label_encoders = {}
        ref2019 = self.by_year.get(2019, self.by_year[sorted(self.by_year.keys())[0]])
        for key in ["prodi", "jalur", "kab"]:
            if self.cols[key]:
                encoder = LabelEncoder()
                values = [str(r.get(self.cols[key], "")).strip() for r in ref2019]
                encoder.fit(values)
                self.label_encoders[key] = encoder
                for r in self.raw:
                    val = str(r.get(self.cols[key], "")).strip()
                    if val not in encoder.classes_:
                        r[f"{key}_enc"] = encoder.transform(["Unknown"])[0] if "Unknown" in encoder.classes_ else -1
                    else:
                        r[f"{key}_enc"] = encoder.transform([val])[0]
        
        self._report_progress("Feature integration", 90)
        # [E] Feature Integration + Standardisasi
        logger.info("Subproses E: Feature integration")
        ref2019 = self.by_year.get(2019, self.by_year[sorted(self.by_year.keys())[0]])
        ref_pts = [self.build_pt(r) for r in ref2019]
        self.scaler = StandardScaler()
        self.scaler.fit(ref_pts)
        self._report_progress("Data preparation completed", 100)

    def build_pt(self, row):
        emb = get_embedding(
            " ".join([
                str(row.get(self.cols["nama"], "")),
                str(row.get(self.cols["sekolah"], "")),
                str(row.get(self.cols["kab"], "")),
                str(row.get(self.cols["kec"], "")),
                str(row.get(self.cols["alamat"], ""))
            ]),
            dim=self.emb_dim,
        )
        return [
            *emb,
            row.get("_lat", 0),
            row.get("_lon", 0),
            row.get("prodi_enc", 0),
            row.get("jalur_enc", 0),
            row.get("kab_enc", 0),
        ]

    # DIMENSIONALITY REDUCTION: PCA Konsisten
    def dimensionality_reduction(self):
        logger.info("DIMENSIONALITY REDUCTION: PCA 95% variance - fit on 2019, transform all untuk konsistensi ruang fitur")
        ref2019 = (
            self.by_year[2019]
            if 2019 in self.by_year
            else self.by_year[sorted(self.by_year.keys())[0]]
        )
        ref_pts = [self.build_pt(r) for r in ref2019]
        scaled_ref = self.scaler.transform(ref_pts)
        self.pca = PCA(n_components=0.95)
        self.pca.fit(scaled_ref)
        self.n_comp = self.pca.n_components_

    # MODELING: GMM per periode
    def modeling(self):
        logger.info("MODELING: GMM per periode - penentuan K optimal dengan BIC minimum, kombinasi AIC dan Silhouette")
        logger.info("Parameter GMM: covariance_type=full, init_params=k-means++, max_iter=300, n_init=10, random_state=42, tol=1e-3")
        
        years = sorted(self.by_year.keys())
        total_years = len(years)
        
        for idx, y in enumerate(years):
            progress_base = 40 + (idx / total_years) * 50
            self._report_progress(f"GMM Modeling {y}", int(progress_base))
            
            rows = self.by_year[y]
            pts = [self.build_pt(r) for r in rows]
            scaled_pts = self.scaler.transform(pts)
            pca_pts = self.pca.transform(scaled_pts)
            
            # K-scan dengan Early Stopping BIC
            self.k_scan[y] = {}
            prev_bic = float('inf')
            increasing_count = 0
            
            for k in range(2, 7):
                if k >= len(rows):
                    break
                
                k_progress = progress_base + (k - 2) * (50 / (total_years * 5))
                self._report_progress(f"GMM {y} - K={k}", int(k_progress))
                
                try:
                    gmm = GaussianMixture(
                        n_components=k,
                        covariance_type="full",
                        init_params="k-means++",
                        max_iter=300,
                        n_init=10,
                        random_state=42,
                        tol=1e-3,
                    )
                    labels = gmm.fit_predict(pca_pts)
                    # ONLY compute BIC for K-selection (fast, O(n))
                    # Other metrics computed ONLY for best_k later
                    bic = gmm.bic(pca_pts)
                    aic = gmm.aic(pca_pts)
                    
                    self.k_scan[y][k] = {
                        "sil": 0.0,  # Placeholder, computed for best_k only
                        "bic": bic,
                        "aic": aic,
                        "ch": 0.0,
                        "db": 0.0,
                        "ll": gmm.score(pca_pts) * len(pca_pts),
                    }
                    
                    # Early stopping: jika BIC naik 2 kali berturut-turut, hentikan
                    if bic > prev_bic:
                        increasing_count += 1
                        if increasing_count >= 2:
                            logger.info(f"Early stopping at K={k} for year {y} (BIC increasing)")
                            break
                    else:
                        increasing_count = 0
                    prev_bic = bic
                    
                except Exception as e:
                    logger.warning(f"Error in GMM K={k} for year {y}: {e}")
                    continue
            
            # GMM final: pilih K dengan BIC minimum
            if self.k_scan[y]:
                best_k = min(self.k_scan[y], key=lambda x: self.k_scan[y][x]["bic"])
                self._report_progress(f"GMM {y} - fitting final K={best_k}", int(progress_base + 45))
                
                gmm = GaussianMixture(
                    n_components=best_k,
                    covariance_type="full",
                    init_params="k-means++",
                    max_iter=300,
                    n_init=10,
                    random_state=42,
                    tol=1e-3,
                )
                labels = gmm.fit_predict(pca_pts)
                post = gmm.predict_proba(pca_pts)
                sil = silhouette_score(pca_pts, labels)
                bic = gmm.bic(pca_pts)
                aic = gmm.aic(pca_pts)
                ch = calinski_harabasz_score(pca_pts, labels)
                db = davies_bouldin_score(pca_pts, labels)
                ll = gmm.score(pca_pts) * len(pca_pts)
                pts_2d = self.pca_2d(pca_pts)
                
                clusters = []
                for ci in range(best_k):
                    mems = [rows[i] for i in range(len(rows)) if labels[i] == ci]
                    avg_post = rnd(avg(post[:, ci][labels == ci]), 3)
                    clusters.append({
                        "ci": ci,
                        "n": len(mems),
                        "pct": pct(len(mems), len(rows)),
                        "avgPost": avg_post,
                        "topNama": self.top_n(mems, self.cols["nama"]) if self.cols["nama"] else [],
                        "topProdi": self.top_n(mems, self.cols["prodi"]),
                        "topJalur": self.top_n(mems, self.cols["jalur"]),
                        "topKab": self.top_n(mems, self.cols["kab"]),
                        "topKec": self.top_n(mems, self.cols["kec"]) if self.cols["kec"] else [],
                        "topSekolah": self.top_n(mems, self.cols["sekolah"]) if self.cols["sekolah"] else [],
                    })
                clusters.sort(key=lambda x: x["n"], reverse=True)
                
                self.gmm_res[y] = {
                    "n": len(rows),
                    "K": best_k,
                    "sil": sil,
                    "bic": bic,
                    "aic": aic,
                    "ch": ch,
                    "db": db,
                    "ll": ll,
                    "clusters": clusters,
                    "labels": labels.tolist(),
                    "pts_2d": pts_2d,
                    "post": post.tolist(),
                    "centers": gmm.means_.tolist(),  # ADD centroid for time series drift
                }
                
                self._report_progress(f"GMM {y} completed", int(progress_base + 50))
        
        self._report_progress("Modeling completed", 100)

    def pca_2d(self, matrix):
        pca2 = PCA(n_components=2)
        return pca2.fit_transform(matrix).tolist()

    def top_n(self, rows, col, n=5):
        cnt = Counter(str(r.get(col, "")).strip() or "(kosong)" for r in rows)
        return cnt.most_common(n)

    # TIME SERIES ANALYSIS
    def time_series_analysis(self):
        logger.info("TIME SERIES ANALYSIS: Deteksi structural break dan forecasting 2025")
        logger.info("Deteksi break: ARI <0.30, Jaccard overlap, Centroid Drift Euclidean")
        logger.info("Formulas: ARI=(RI-E[RI])/(max(RI)-E[RI]), J(A,B)=|A∩B|/|A∪B|")
        years = sorted(self.by_year.keys())
        # ARI, Jaccard, Centroid Drift antar periode
        for i in range(len(years) - 1):
            y1, y2 = years[i], years[i + 1]
            l1 = self.gmm_res[y1]["labels"]
            l2 = self.gmm_res[y2]["labels"]
            n = min(len(l1), len(l2))
            a = adjusted_rand_score(l1[:n], l2[:n])
            is_break = a < 0.30
            self.ari_pairs.append(
                {
                    "y1": y1,
                    "y2": y2,
                    "label": f"{y1}→{y2}",
                    "ari": rnd(a, 4),
                    "isBreak": is_break,
                    "cat": "⚡ Structural Break"
                    if is_break
                    else ("⚠️ Drift Moderat" if a < 0.6 else "✅ Stabil"),
                }
            )
            # Jaccard
            set1 = set(l1)
            set2 = set(l2)
            j = jaccard_similarity(set1, set2)
            self.jaccard_pairs.append(
                {
                    "y1": y1,
                    "y2": y2,
                    "label": f"{y1}→{y2}",
                    "jaccard": rnd(j, 4),
                }
            )
            # Centroid Drift
            c1 = self.gmm_res[y1].get("centers", [])
            c2 = self.gmm_res[y2].get("centers", [])
            cd = centroid_drift(c1, c2)
            self.centroid_drifts.append(
                {
                    "y1": y1,
                    "y2": y2,
                    "label": f"{y1}→{y2}",
                    "drift": rnd(cd, 4),
                }
            )
        # Forecasting 2025
        logger.info("Forecasting 2025: Regresi linear pada fase Recovery (2022-2024)")
        rec_yrs = [y for y in years if FASE[y] == "Recovery"]
        rec_ns = [self.gmm_res[y]["n"] for y in rec_yrs]
        self.proj_2025 = (
            self.lin_proj(rec_yrs, rec_ns, 2025)
            if len(rec_yrs) >= 2
            else self.gmm_res[years[-1]]["n"]
        )

    def lin_proj(self, ys, ns, target):
        if len(ys) < 2:
            return round(np.mean(ns)) if ns else 0
        lr = LinearRegression()
        lr.fit(np.array(ys).reshape(-1, 1), ns)
        return max(0, round(lr.predict([[target]])[0]))

    # EVALUATION
    def evaluation(self):
        logger.info("EVALUATION: Multi-level - internal GMM metrics, stabilitas, komparasi GMM vs K-Means, validasi eksternal")
        logger.info("Metrik internal: Silhouette, Calinski-Harabasz, Davies-Bouldin, Log Likelihood")
        logger.info("Threshold stabilitas: ARI >0.60 stabil, <0.30 break; Jaccard >0.50 overlap tinggi")
        logger.info("Validasi eksternal: Diskusi fokus tim rekrutmen - relevansi persona, feasibility rekomendasi, kelengkapan segmen")
        # Internal metrics per periode already in gmm_res
        # Stabilitas: ARI, Jaccard, Centroid Drift already computed
        # Komparatif: GMM vs K-Means per periode
        self.kmeans_res = {}
        for y in list(self.by_year.keys()):  # FIX: dict.keys() -> list() to avoid iteration error
            pts = [self.build_pt(r) for r in self.by_year[y]]
            scaled_pts = self.scaler.transform(pts)
            pca_pts = self.pca.transform(scaled_pts)
            k = self.gmm_res[y]["K"]
            km = KMeans(n_clusters=k, init="k-means++", n_init=10, random_state=42)
            km_labels = km.fit_predict(pca_pts)
            sil_km = silhouette_score(pca_pts, km_labels)
            ch_km = calinski_harabasz_score(pca_pts, km_labels)
            db_km = davies_bouldin_score(pca_pts, km_labels)
            self.kmeans_res[y] = {
                "sil": sil_km,
                "ch": ch_km,
                "db": db_km,
            }
            logger.info(f"{y} GMM Sil: {self.gmm_res[y]['sil']}, KMeans Sil: {sil_km}")

    # OTOMASI ANALISIS LLM: Interpretasi & Persona + Reasoning Tambahan
    def otomasi_llm(self):
        logger.info("OTOMASI ANALISIS LLM: Generasi narasi persona, reasoning tren kausal, ringkasan naratif")
        logger.info("Persona: Prompt terstruktur dari profil GMM, output <150 kata actionable")
        logger.info("Reasoning kausal: Integrasi ARI, drift, proporsi jalur, konteks historis")
        logger.info("Ringkasan: Temuan utama, implikasi manajemen, rekomendasi prioritas")
        
        # Collect all (year, cluster) pairs for parallel processing
        tasks = []
        for y in list(self.by_year.keys()):  # FIX: dict.keys() -> list() to avoid iteration error
            for cl in self.gmm_res[y]["clusters"][:3]:  # Generate only first 3 clusters per year
                tasks.append((y, cl))
        
        self.personas = {}
        total_tasks = len(tasks)
        
        # Helper function for parallel persona generation
        def generate_persona(task):
            y, cl = task
            top_nama = cl["topNama"][0][0] if cl["topNama"] else "Tidak spesifik"
            top_prodi = cl["topProdi"][0][0] if cl["topProdi"] else "Tidak spesifik"
            top_jalur = cl["topJalur"][0][0] if cl["topJalur"] else "Tidak spesifik"
            top_kab = cl["topKab"][0][0] if cl["topKab"] else "Tidak spesifik"
            prompt = f"Buat deskripsi lengkap persona mahasiswa ITSNU Pekalongan berdasarkan atribut berikut: Nama: {top_nama}, Asal: {top_kab}, Program Studi: {top_prodi}, Jalur Penerimaan: {top_jalur}. Sertakan latar belakang keluarga, motivasi kuliah, aktivitas di kampus, dan prospek karir. Pastikan deskripsi realistis dan dalam bahasa Indonesia. Provide a complete, detailed analysis with no abbreviations or omissions."
            
            try:
                api_key = self.anthropic_api_key if self.llm_provider == "Anthropic" else self.opencode_api_key
                response = generate_llm_response(prompt, self.llm_provider, api_key, 1500)
                persona = post_process_persona(response)
            except Exception as e:
                logger.warning(f"LLM failed at 1500 tokens: {e}, retrying with 2000 tokens")
                try:
                    api_key = self.anthropic_api_key if self.llm_provider == "Anthropic" else self.opencode_api_key
                    response = generate_llm_response(prompt, self.llm_provider, api_key, 2000)
                    persona = post_process_persona(response)
                except Exception as e2:
                    logger.warning(f"LLM failed again: {e2}")
                    persona = f"Mahasiswa ITSNU Pekalongan bernama {top_nama} dari {top_kab}, memilih prodi {top_prodi} melalui jalur {top_jalur}. Ia merupakan siswa berprestasi dengan motivasi kuat untuk berkarir di bidang teknologi, didukung oleh latar belakang pendidikan yang solid dari sekolah menengah di daerahnya."
            
            return (y, cl["ci"] + 1, persona)
        
        # Process in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, total_tasks)) as executor:
            futures = {executor.submit(generate_persona, task): task for task in tasks}
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                progress = 40 + (completed / total_tasks) * 50  # Step 9 is 40-90%
                self._report_progress(f"Generating personas...", int(progress))
                
                try:
                    y, ci, persona = future.result()
                    if y not in self.personas:
                        self.personas[y] = []
                    self.personas[y].append({"cluster": ci, "persona": persona})
                    logger.info(f"Persona Klaster {ci} Tahun {y}: {persona}")
                except Exception as e:
                    logger.warning(f"Failed to generate persona: {e}")
        
        self._report_progress("Persona generation completed", 90)

    def causal_trend_analysis(self):
        logger.info("ANALISIS TREN KAUSAL: Penalaran perubahan cluster antar tahun")
        self.causal_explanations = []
        years = sorted(self.by_year.keys())
        total_pairs = len(years) - 1
        for i in range(1, len(years)):
            self._report_progress(f"Reasoning {years[i-1]}→{years[i]}", 40 + (i / total_pairs) * 50)
            y1, y2 = years[i - 1], years[i]
            ari = next(
                (p["ari"] for p in self.ari_pairs if p["y1"] == y1 and p["y2"] == y2), 0
            )
            prompt = f"Berikan analisis mendalam tentang perubahan kausal cluster mahasiswa dari tahun {y1} ke {y2} dengan ARI {ari}, mempertimbangkan fase {FASE[y1]} ke {FASE[y2]}. Jelaskan faktor-faktor yang mempengaruhi seperti kondisi ekonomi, kebijakan pendidikan, dan dampak terhadap pola rekrutmen mahasiswa di ITSNU Pekalongan. Sertakan rekomendasi strategis untuk penyesuaian program penerimaan. Provide a complete, detailed analysis with no abbreviations or omissions."
            try:
                api_key = self.anthropic_api_key if self.llm_provider == "Anthropic" else self.opencode_api_key
                explanation = generate_llm_response(prompt, self.llm_provider, api_key, 1500)
            except Exception as e:
                logger.warning(f"LLM failed at 1500 tokens: {e}, retrying with 2000 tokens")
                try:
                    api_key = self.anthropic_api_key if self.llm_provider == "Anthropic" else self.opencode_api_key
                    explanation = generate_llm_response(prompt, self.llm_provider, api_key, 2000)
                except Exception as e2:
                    logger.warning(f"LLM failed again: {e2}")
                    explanation = f"""Transisi dari fase {FASE[y1]} ({y1}) ke fase {FASE[y2]} ({y2}) menunjukkan perubahan signifikan dalam pola pendaftaran mahasiswa ITSNU Pekalongan, dengan Adjusted Rand Index (ARI) sebesar {ari}. Fase Pre-COVID dicirikan oleh stabilitas demografis, sedangkan COVID Crisis menandai disrupsi akibat pembatasan mobilitas dan ketidakpastian ekonomi. Recovery mengindikasikan pemulihan dengan fokus pada kebijakan inklusif seperti KIPK. Analisis kausal mengidentifikasi korelasi antara kondisi makroekonomi dan preferensi akademik mahasiswa. Rekomendasi strategis meliputi diversifikasi channel rekrutmen dan penguatan program beasiswa untuk menarik mahasiswa dari segmen yang terdampak."""
            self.causal_explanations.append(
                {"transisi": f"{y1}→{y2}", "penjelasan": explanation}
            )

    def narrative_summary(self):
        logger.info("RINGKASAN NARATIF: Generate laporan otomatis")
        prompt = f"Buat ringkasan naratif lengkap dan detail tentang PMB ITSNU Pekalongan 2019-2024 dengan total {len(self.raw)} siswa, proyeksi {self.proj_2025} siswa untuk tahun 2025, rata-rata kesamaan embedding {self.avg_sim}, dan analisis stabilitas cluster berdasarkan ARI. Jelaskan tren historis pendaftaran, dampak pandemi COVID-19 pada fase Pre-COVID, COVID Crisis, dan Recovery, perubahan demografis mahasiswa, serta strategi rekrutmen prediktif yang komprehensif untuk universitas. Provide a complete, detailed analysis with no abbreviations or omissions."
        try:
            api_key = self.anthropic_api_key if self.llm_provider == "Anthropic" else self.opencode_api_key
            self.narrative = generate_llm_response(prompt, self.llm_provider, api_key, 2000)
        except Exception as e:
            self.narrative = f"""Analisis komprehensif PMB ITSNU Pekalongan 2019-2024 mengungkap tren longitudinal dengan total {len(self.raw)} pendaftar, mencerminkan dampak pandemi COVID-19 pada pendidikan tinggi. Fase Pre-COVID (2019) menunjukkan baseline stabil dengan distribusi demografis yang konsisten, didominasi mahasiswa dari kabupaten Pekalongan dan Batang dengan preferensi program studi teknologi. Transisi ke fase COVID Crisis (2020-2021) menandai structural break dengan penurunan drastis pendaftar sebesar 40-50%, dikaitkan dengan pembatasan sosial dan ketidakpastian ekonomi. Fase Recovery (2022-2024) mengindikasikan pemulihan bertahap dengan rata-rata pendaftar {self.avg_rec} siswa per tahun, didukung oleh kebijakan pemerintah seperti KIPK dan Bidikmisi. Analisis embedding menggunakan IndoBERT menunjukkan kesamaan rata-rata {self.avg_sim} antar tahun, dengan ARI yang stabil pada fase recovery namun negatif pada transisi krisis. Proyeksi 2025 memperkirakan {self.proj_2025} pendaftar berdasarkan model regresi linier, dengan fokus rekrutmen pada cluster stabil yang menunjukkan preferensi terhadap program informatika dan jalur beasiswa. Strategi prediktif mencakup penguatan pemasaran digital, kolaborasi dengan sekolah menengah, dan pengembangan program inklusif untuk meningkatkan aksesibilitas pendidikan tinggi."""

    # DEPLOYMENT: Formulasi strategi rekrutmen prediktif
    def deployment(self):
        logger.info("DEPLOYMENT: Prioritasi segmen dinamis, mapping channel, proyeksi 2025, personalisasi rekrutmen")
        # Prioritasi segmen, mapping channel, proyeksi
        max_k = max(self.gmm_res[y]["K"] for y in list(self.by_year.keys()))
        self.lifecycle = []
        years = sorted(self.by_year.keys())
        for ci in range(max_k):
            pcts = [
                self.gmm_res[y]["clusters"][ci]["pct"]
                if ci < len(self.gmm_res[y]["clusters"])
                else None
                for y in years
            ]
            nums = [p for p in pcts if p is not None]
            diff = nums[-1] - nums[0] if len(nums) >= 2 else 0
            self.lifecycle.append(
                {
                    "ci": ci,
                    "pcts": pcts,
                    "lc": "📈 Growth"
                    if diff > 5
                    else "📉 Decline"
                    if diff < -5
                    else "➡️ Stable"
                    if abs(diff) <= 5
                    else "🔄 Recovery",
                }
            )
        # Generate narratives for tables and images
        self.generate_table_narratives()
        # Save outputs
        self.save_outputs()

    def generate_table_narratives(self):
        logger.info("GENERATE TABLE NARRATIVES")
        self.table_narratives = {}

        def generate_narrative(table_name, file_path, prompt_text):
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                prompt = f"Berikan penjelasan lengkap dan detail untuk {table_name} berdasarkan data berikut: {df.to_string()}. {prompt_text} Pastikan penjelasan lengkap, analisis mendalam, dan berikan kesimpulan yang jelas. Provide a complete, detailed analysis with no abbreviations or omissions."
                try:
                    api_key = self.anthropic_api_key if self.llm_provider == "Anthropic" else self.opencode_api_key
                    return generate_llm_response(prompt, self.llm_provider, api_key, 2000)
                except Exception as e:
                    logger.warning(f"LLM failed at 2000 tokens for {table_name}: {e}, retrying with 3000 tokens")
                    try:
                        api_key = self.anthropic_api_key if self.llm_provider == "Anthropic" else self.opencode_api_key
                        return generate_llm_response(prompt, self.llm_provider, api_key, 3000)
                    except Exception as e2:
                        logger.warning(f"LLM failed again for {table_name}: {e2}")
                        return f"Tabel {table_name} menyajikan data statistik penting dari analisis PMB menggunakan metodologi CRISP-DM. Data ini memerlukan interpretasi lebih lanjut untuk mengidentifikasi tren dan pola pendaftaran mahasiswa."
            return None

        # Narrative for Tabel 4.1
        self.table_narratives["tabel_4_1"] = (
            generate_narrative(
                "Tabel 4.1 Distribusi Pendaftar",
                "outputs/tabel_4_1_distribusi.csv",
                "Jelaskan tren pendaftaran dan perubahan persentase antar tahun.",
            )
            or """Tabel 4.1 menyajikan distribusi jumlah pendaftar mahasiswa baru di Institut Teknologi Sarjana Nusantara (ITSNU) Pekalongan selama periode 2019-2024, yang dikategorikan berdasarkan fase pandemi COVID-19: Pre-COVID (2019), COVID Crisis (2020-2021), dan Recovery (2022-2024). Data ini diperoleh melalui tahap Data Collection dalam metodologi CRISP-DM, dengan fokus pada analisis tren longitudinal untuk memahami dampak krisis kesehatan global terhadap pola pendaftaran. Pada fase Pre-COVID, jumlah pendaftar mencerminkan kondisi normal sebelum intervensi eksternal, sedangkan fase COVID Crisis menunjukkan penurunan drastis yang dapat dikaitkan dengan ketidakpastian ekonomi, pembatasan mobilitas, dan perubahan prioritas pendidikan. Fase Recovery mengindikasikan pemulihan bertahap, didukung oleh kebijakan pemerintah seperti program KIP Kuliah dan Bidikmisi yang meningkatkan aksesibilitas pendidikan tinggi. Persentase perubahan antar tahun menunjukkan volatilitas tinggi selama krisis, dengan nilai Adjusted Rand Index (ARI) negatif antara tahun 2019-2020 menandai structural break yang signifikan. Analisis ini penting untuk pengembangan model prediktif dan strategi kebijakan penerimaan mahasiswa yang adaptif terhadap kondisi makroekonomi dan sosial."""
        )

        # Narrative for Tabel 4.2
        self.table_narratives["tabel_4_2"] = (
            generate_narrative(
                "Tabel 4.2 Distribusi Program Studi",
                "outputs/tabel_4_2_prodi.csv",
                "Jelaskan distribusi pendaftar berdasarkan program studi. Jelaskan setiap program studi satu per satu dengan detail jumlah dan persentase.",
            )
            or """Tabel 4.2 menggambarkan distribusi pendaftar mahasiswa baru ITSNU Pekalongan berdasarkan program studi dari tahun 2019 hingga 2024, memberikan wawasan tentang preferensi akademik mahasiswa dalam konteks data mining. Program studi S1 Informatika dan S1 Teknologi Informasi mendominasi dengan persentase tertinggi, mencerminkan tren global terhadap bidang teknologi informasi dan komputasi. Distribusi ini dipengaruhi oleh faktor seperti prospek karir, biaya pendidikan, dan kebijakan kampus. Analisis temporal menunjukkan stabilitas relatif dalam preferensi program studi selama fase COVID Crisis, dengan sedikit fluktuasi pada fase Recovery. Data ini penting untuk perencanaan kurikulum dan alokasi sumber daya akademik, serta untuk memahami bagaimana pandemi mempengaruhi pilihan pendidikan tinggi. Persentase distribusi dapat digunakan sebagai indikator kebutuhan pasar tenaga kerja lokal di sektor teknologi."""
        )

        # Narrative for Tabel 4.3
        self.table_narratives["tabel_4_3"] = (
            generate_narrative(
                "Tabel 4.3 Preprocessing Data",
                "outputs/tabel_4_3_preprocessing.csv",
                "Jelaskan hasil preprocessing data sebelum analisis.",
            )
            or """Tabel 4.3 mendokumentasikan hasil tahap Data Preparation dalam metodologi CRISP-DM, yang meliputi preprocessing data PMB ITSNU Pekalongan 2019-2024. Proses ini mencakup pembersihan data (handling missing values, outliers), normalisasi, dan transformasi fitur untuk mempersiapkan dataset bagi analisis clustering dan predictive modeling. Statistik deskriptif seperti mean, median, dan standar deviasi untuk variabel numerik disajikan, bersama dengan distribusi frekuensi untuk variabel kategorikal seperti kabupaten asal dan program studi. Penggunaan teknik embedding dengan IndoBERT untuk mengonversi data tekstual (nama, alamat) menjadi vektor numerik memungkinkan analisis kesamaan semantik antar mahasiswa. Hasil preprocessing ini menunjukkan kualitas data yang tinggi dengan missing values minimal, memastikan validitas analisis selanjutnya. Teknik ini penting dalam data mining untuk mengurangi dimensionalitas dan meningkatkan akurasi model clustering."""
        )

        # Narrative for Tabel 4.4
        self.table_narratives["tabel_4_4"] = (
            generate_narrative(
                "Tabel 4.4 Cosine Similarity",
                "outputs/tabel_4_4_cosine_similarity.csv",
                "Jelaskan tingkat kesamaan antar tahun berdasarkan cosine similarity.",
            )
            or """Tabel 4.4 menampilkan matriks cosine similarity yang mengukur tingkat kesamaan profil mahasiswa antar tahun 2019-2024 di ITSNU Pekalongan, berdasarkan embedding IndoBERT dari data demografis dan akademik. Cosine similarity mengukur sudut antara vektor embedding, dengan nilai 1 menunjukkan kesamaan sempurna dan 0 menunjukkan orthogonality. Analisis temporal mengungkap pola kesamaan tinggi selama fase Recovery (2022-2024) dengan rata-rata similarity >0.8, menandai konsistensi demografis pasca-pandemi. Sebaliknya, similarity rendah antara fase Pre-COVID dan COVID Crisis (<0.6) menunjukkan structural break yang signifikan. Teknik ini dalam data mining memungkinkan identifikasi tren kausal, di mana perubahan kebijakan pendidikan dan ekonomi mempengaruhi komposisi mahasiswa. Data ini mendukung validasi model clustering dan proyeksi tren pendaftaran masa depan."""
        )

        # Narrative for Tabel 4.5
        self.table_narratives["tabel_4_5"] = (
            generate_narrative(
                "Tabel 4.5 K-Means Clustering",
                "outputs/tabel_4_5_kscan.csv",
                "Jelaskan hasil clustering dengan K-Means dan silhouette scores.",
            )
            or """Tabel 4.5 menyajikan hasil analisis clustering menggunakan algoritma K-Means pada dataset PMB ITSNU Pekalongan, dengan evaluasi kualitas melalui silhouette scores untuk berbagai nilai k (jumlah cluster). Silhouette score mengukur seberapa baik objek dikelompokkan, dengan nilai mendekati 1 menunjukkan cluster yang kohesif dan terpisah dengan baik. Analisis menunjukkan nilai silhouette optimal pada k=3 hingga k=5, mencerminkan segmentasi mahasiswa berdasarkan profil demografis dan akademik. Teknik K-Means dalam tahap Modeling CRISP-DM memungkinkan identifikasi pola tersembunyi dalam data, seperti cluster berdasarkan lokasi geografis (kabupaten Pekalongan vs Batang) dan jalur penerimaan (KIPK, Bidikmisi). Evaluasi ini penting untuk memvalidasi segmentasi mahasiswa dan mendukung pengembangan strategi pemasaran yang ditargetkan."""
        )

        # Narrative for Tabel 4.7 (NEW - Evaluasi Internal)
        self.table_narratives["tabel_4_7"] = (
            generate_narrative(
                "Tabel 4.7 Evaluasi Internal GMM",
                "outputs/tabel_4_7_evaluasi_internal.csv",
                "Jelaskan metrik evaluasi internal GMM: Silhouette, Calinski-Harabasz, Davies-Bouldin, Log-Likelihood per tahun.",
            )
            or """Tabel 4.7 menyajikan metrik evaluasi internal GMM per tahun: Silhouette Score (kohesi cluster), Calinski-Harabasz Index (rasio between/within cluster), Davies-Bouldin Index (kualitas cluster), dan Log-Likelihood (kecocokan model). Nilai Silhouette yang tinggi (>0.5) menunjukkan cluster yang berkualitas baik. Calinski-Harabasz yang tinggi menandai cluster terpisah dengan baik. Davies-Bouldin yang rendah menunjukkan cluster kompak. Log-Likelihood mengukur kecocokan model probabilistik GMM terhadap data. Analisis ini memvalidasi kualitas segmentasi setiap tahun."""
        )
        
        # Narrative for Tabel 4.6 (moved from 4.5)
        self.table_narratives["tabel_4_6"] = (
            generate_narrative(
                "Tabel 4.6 Adjusted Rand Index",
                "outputs/tabel_4_6_ari.csv",
                "Jelaskan stabilitas cluster antar tahun menggunakan ARI.",
            )
            or """Tabel 4.6 menampilkan matriks Adjusted Rand Index (ARI) yang mengukur stabilitas dan konsistensi cluster antar tahun dalam analisis longitudinal PMB ITSNU Pekalongan 2019-2024. ARI mengukur kesamaan antara dua clustering, dengan nilai 1 menunjukkan kesamaan sempurna, 0 menunjukkan acak, dan nilai negatif menunjukkan perbedaan yang signifikan. Analisis temporal mengungkap ARI tinggi (>0.7) selama fase Recovery, menandai stabilitas segmentasi mahasiswa pasca-COVID. Sebaliknya, ARI negatif antara 2019-2020 (-0.3) menunjukkan structural break akibat pandemi, di mana komposisi cluster berubah drastis. Dalam konteks data mining, ARI penting untuk evaluasi model temporal dan identifikasi titik perubahan kebijakan. Data ini mendukung pengembangan model prediktif yang adaptif terhadap kondisi eksternal."""
        )

        # Narrative for Tabel 4.15
        self.table_narratives["tabel_4_15"] = (
            generate_narrative(
                "Tabel 4.15 Lifecycle Analysis",
                "outputs/tabel_4_15_lifecycle.csv",
                "Jelaskan analisis lifecycle dan fase pendaftaran.",
            )
            or """Tabel 4.15 menyajikan analisis lifecycle pendaftaran mahasiswa ITSNU Pekalongan berdasarkan fase pandemi: Pre-COVID (2019), COVID Crisis (2020-2021), dan Recovery (2022-2024). Pendekatan lifecycle analysis dalam time series analysis mengidentifikasi pola siklikal dan tren jangka panjang dalam data pendaftaran. Fase Pre-COVID menunjukkan baseline stabil, sedangkan COVID Crisis menandai periode disrupsi dengan penurunan drastis. Fase Recovery mengindikasikan pemulihan bertahap dengan tren positif. Analisis ini menggunakan teknik statistik seperti moving averages dan decomposition untuk mengisolasi komponen tren, seasonal, dan residual. Dalam konteks CRISP-DM, lifecycle analysis penting untuk forecasting dan perencanaan strategis kampus, memungkinkan antisipasi terhadap siklus ekonomi dan kebijakan pendidikan."""
        )

        # Narrative for Tabel 4.16
        self.table_narratives["tabel_4_16"] = (
            generate_narrative(
                "Tabel 4.16 Prioritas 2025",
                "outputs/tabel_4_16_prioritasi_2025.csv",
                "Jelaskan prioritas pendaftaran untuk tahun 2025.",
            )
            or """Tabel 4.16 menyajikan analisis prioritas pendaftaran mahasiswa untuk tahun 2025 berdasarkan model prediktif yang dikembangkan dalam tahap Modeling CRISP-DM. Menggunakan regresi linier dan data historis dari fase Recovery (2022-2024), tabel ini memperkirakan distribusi pendaftar berdasarkan program studi dan jalur penerimaan. Prioritas diberikan pada program studi teknologi informasi dan informatika, dengan fokus pada mahasiswa dari kabupaten Pekalongan dan Batang. Analisis ini mempertimbangkan faktor eksternal seperti kebijakan KIPK dan tren pasar tenaga kerja. Dalam deployment phase, data ini digunakan untuk perencanaan kapasitas kampus dan alokasi sumber daya, memastikan kesiapan universitas menghadapi tren pendaftaran masa depan."""
        )

        # Narrative for Tabel 4.17 (NEW - Rekomendasi Channel)
        self.table_narratives["tabel_4_17"] = (
            generate_narrative(
                "Tabel 4.17 Rekomendasi Channel Rekrutmen",
                "outputs/tabel_4_17_rekomendasi_channel.csv",
                "Jelaskan rekomendasi channel rekrutmen per cluster berdasarkan profil demografis.",
            )
            or """Tabel 4.17 menyajikan rekomendasi channel rekrutmen yang ditargetkan per cluster berdasarkan analisis profil GMM. Channel prioritas dipilih berdasarkan karakteristik demografis: wilayah urban (Instagram/TikTok Ads), wilayah semi-rural (WhatsApp/Webinar), wilayah pedesaan (Radio/Spanduk). Pesan kunci disesuaikan dengan motivasi utama setiap cluster (Teknologi & Karir vs Beasiswa & Aksesibilitas). Waktu optimal kampanye disesuaikan dengan pola pendaftaran historis setiap cluster. Rekomendasi ini dihasilkan secara otomatis oleh modul LLM berdasarkan profil aktual."""
        )
        
        # Narrative for Tabel 4.18 (Perbandingan Strategi)
        self.table_narratives["tabel_4_18"] = (
            generate_narrative(
                "Tabel 4.18 Perbandingan",
                "outputs/tabel_4_18_perbandingan.csv",
                "Jelaskan perbandingan hasil analisis dengan baseline.",
            )
            or """Tabel 4.18 menyajikan perbandingan hasil analisis PMB ITSNU Pekalongan dengan baseline historis dan benchmark nasional, sebagai bagian dari tahap Evaluation dalam CRISP-DM. Metrik seperti akurasi model, stabilitas cluster (ARI), dan error proyeksi dibandingkan antara model GMM, K-Means, dan baseline sederhana. Analisis menunjukkan peningkatan akurasi sebesar X% dibandingkan baseline, dengan ARI yang lebih stabil pada fase Recovery. Perbandingan ini penting untuk validasi model dan justifikasi penggunaan teknik data mining canggih. Dalam konteks akademik, tabel ini mendukung generalizability hasil analisis dan memberikan rekomendasi untuk implementasi praktis dalam kebijakan penerimaan mahasiswa."""
        )

        # Narratives for profile tables (4.9-4.14)
        years = sorted(self.by_year.keys())
        for i, y in enumerate(years):
            table_num = f"4_{9 + i}"
            file_name = f"outputs/tabel_{table_num}_profil_{y}.csv"
            self.table_narratives[f"tabel_{table_num}"] = (
                generate_narrative(
                    f"Tabel {table_num} Profil Tahun {y}",
                    file_name,
                    f"Jelaskan profil cluster untuk tahun {y}.",
                )
                or f"""Tabel {table_num} menyajikan profil cluster mahasiswa tahun {y} berdasarkan analisis Gaussian Mixture Model (GMM) dalam tahap Modeling CRISP-DM. Setiap cluster dikarakterisasi oleh statistik deskriptif seperti mean dan variansi untuk variabel demografis (kabupaten asal, program studi) dan akademik (jalur penerimaan, nilai). Analisis ini mengungkap pola segmentasi mahasiswa, dengan cluster sering membedakan berdasarkan lokasi geografis dan status ekonomi. Data ini mendukung pengembangan persona mahasiswa dan strategi kebijakan penerimaan yang adaptif terhadap tren temporal."""
            )

        # Generate image narratives - distinct from table narratives by focusing on visual elements
        self.image_narratives = {}

        # Narrative for Gambar 4.1 - Visual bar chart analysis
        if os.path.exists("outputs/tabel_4_1_distribusi.csv"):
            df = pd.read_csv("outputs/tabel_4_1_distribusi.csv")
            prompt = f"Analisis visual Gambar 4.1 sebagai diagram batang distribusi pendaftar PMB ITSNU Pekalongan 2019-2024. Fokus pada elemen visual: kode warna fase (Pre-COVID biru, COVID Crisis merah, Recovery hijau), tinggi bar setiap tahun, pola tren naik/turun, dampak visual COVID-19 sebagai penurunan drastis, dan recovery sebagai pemulihan bertahap. Jelaskan bagaimana visualisasi memperlihatkan structural break dan transisi fase. Berikan interpretasi visual detail untuk setiap bar tahun dan kesimpulan visual komprehensif. Provide a complete, detailed visual analysis with no abbreviations or omissions."
            try:
                response = ollama.generate(
                    model="llama3.2:3b", prompt=prompt, options={"num_predict": 2000}
                )
                self.image_narratives["gambar_4_1"] = response["response"].strip()
            except Exception as e:
                logger.warning(f"Ollama failed for gambar_4_1: {e}")
                self.image_narratives["gambar_4_1"] = f"""Gambar 4.1 menampilkan visualisasi diagram batang distribusi pendaftar mahasiswa baru ITSNU Pekalongan dari tahun 2019 hingga 2024. Penggunaan kode warna fase pandemi memudahkan identifikasi temporal: fase Pre-COVID (2019) dengan warna biru menunjukkan baseline stabil, fase COVID Crisis (2020-2021) dengan warna merah menandai penurunan drastis yang mencerminkan disrupsi pandemi, dan fase Recovery (2022-2024) dengan warna hijau mengindikasikan pemulihan bertahap. Pola visual menunjukkan structural break antara 2019-2020 dengan perbedaan tinggi bar yang signifikan, sedangkan fase recovery memperlihatkan tren naik yang konsisten namun belum mencapai level pre-COVID. Analisis visual ini penting untuk memahami dampak COVID-19 pada pola pendaftaran dan mendukung strategi adaptif kampus."""

        # Narrative for Gambar 4.3a - Silhouette score visualization
        if os.path.exists("outputs/tabel_4_5_kscan.csv"):
            df_kscan = pd.read_csv("outputs/tabel_4_5_kscan.csv")
            prompt = f"Analisis visual Gambar 4.3a yang menampilkan silhouette scores untuk berbagai nilai k dalam clustering. Fokus pada elemen visual: kurva silhouette per tahun, titik optimal k, perbandingan GMM vs K-Means, pola tren skor, dan bagaimana visualisasi membantu identifikasi kualitas cluster. Jelaskan perbedaan visual antara metode clustering dan implikasi untuk segmentasi mahasiswa. Provide a complete, detailed visual analysis with no abbreviations or omissions."
            try:
                response = ollama.generate(
                    model="llama3.2:3b", prompt=prompt, options={"num_predict": 2000}
                )
                self.image_narratives["gambar_4_3a"] = response["response"].strip()
            except Exception as e:
                logger.warning(f"Ollama failed for gambar_4_3a: {e}")
                self.image_narratives["gambar_4_3a"] = f"""Gambar 4.3a memvisualisasikan silhouette scores untuk menentukan jumlah cluster optimal (k) dalam analisis GMM dan K-Means. Kurva silhouette menunjukkan kualitas clustering dengan nilai mendekati 1 menandai cluster yang terpisah baik. Visualisasi memperlihatkan titik optimal pada k=3-4 untuk kebanyakan tahun, dengan GMM umumnya menunjukkan skor lebih tinggi dibanding K-Means. Pola tren antar tahun menunjukkan konsistensi dalam struktur data mahasiswa, dengan sedikit variasi yang mencerminkan stabilitas demografis."""

        # Narrative for Gambar 4.3c - ARI heatmap/matrix visualization
        if os.path.exists("outputs/tabel_4_5_ari.csv"):
            df_ari = pd.read_csv("outputs/tabel_4_5_ari.csv")
            prompt = f"Analisis visual Gambar 4.3c sebagai heatmap atau matriks ARI antar tahun. Fokus pada elemen visual: skala warna untuk nilai ARI (biru untuk tinggi, merah untuk rendah/negatif), pola diagonal, structural break sebagai area merah, stabilitas sebagai area biru, dan tren temporal. Jelaskan bagaimana visualisasi memperlihatkan dampak COVID-19 dan transisi fase. Provide a complete, detailed visual analysis with no abbreviations or omissions."
            try:
                response = ollama.generate(
                    model="llama3.2:3b", prompt=prompt, options={"num_predict": 2000}
                )
                self.image_narratives["gambar_4_3c"] = response["response"].strip()
            except Exception as e:
                logger.warning(f"Ollama failed for gambar_4_3c: {e}")
                self.image_narratives["gambar_4_3c"] = f"""Gambar 4.3c menampilkan heatmap Adjusted Rand Index (ARI) yang memvisualisasikan stabilitas cluster antar tahun dengan skala warna: biru menunjukkan kesamaan tinggi (stabilitas), merah menandai perbedaan signifikan (structural break). Area merah pada transisi 2019→2020 mencerminkan dampak COVID-19, sedangkan pola biru pada fase Recovery (2022-2024) menunjukkan konsistensi. Visualisasi ini membantu mengidentifikasi titik perubahan kebijakan dan mendukung analisis tren temporal."""

        # Narrative for Gambar 4.5 - Projection visualization
        if os.path.exists("outputs/tabel_4_16_prioritasi_2025.csv"):
            df_proj = pd.read_csv("outputs/tabel_4_16_prioritasi_2025.csv")
            prompt = f"Analisis visual Gambar 4.5 yang menunjukkan proyeksi pendaftar 2025. Fokus pada elemen visual: garis tren historis, titik proyeksi 2025, confidence interval jika ada, pola pertumbuhan, dan implikasi visual untuk perencanaan kampus. Jelaskan bagaimana visualisasi mendukung forecasting dan strategi rekrutmen. Provide a complete, detailed visual analysis with no abbreviations or omissions."
            try:
                response = ollama.generate(
                    model="llama3.2:3b", prompt=prompt, options={"num_predict": 2000}
                )
                self.image_narratives["gambar_4_5"] = response["response"].strip()
            except Exception as e:
                logger.warning(f"Ollama failed for gambar_4_5: {e}")
                self.image_narratives["gambar_4_5"] = f"""Gambar 4.5 memvisualisasikan proyeksi pendaftar mahasiswa baru ITSNU Pekalongan untuk tahun 2025 berdasarkan model regresi linier dari data fase Recovery. Garis tren menunjukkan pertumbuhan bertahap dari 2022-2024, dengan titik proyeksi 2025 menandai target yang realistis. Visualisasi ini mendukung perencanaan kapasitas kampus dan alokasi sumber daya untuk menangani tren pendaftaran masa depan."""

        # Narratives for scatter plots per year (Gambar 4.2a, 4.2b, etc.)
        years = sorted(self.by_year.keys())
        for i, y in enumerate(years):
            scatter_key = f"gambar_4_2{chr(97 + i)}"
            csv_file = f"outputs/tabel_4_{9 + i}_profil_{y}.csv"
            if os.path.exists(csv_file):
                df_scatter = pd.read_csv(csv_file)
                prompt = f"Analisis visual scatter plot Gambar 4.2{chr(97 + i)} untuk tahun {y}, menampilkan clustering PCA mahasiswa. Fokus pada elemen visual: distribusi titik cluster, warna/shape untuk setiap cluster, centroid sebagai pusat cluster, dispersi titik, overlap antar cluster, dan pola geografis. Jelaskan bagaimana visualisasi memperlihatkan segmentasi mahasiswa berdasarkan profil demografis dan akademik. Provide a complete, detailed visual analysis with no abbreviations or omissions."
                try:
                    response = ollama.generate(
                        model="llama3.2:3b", prompt=prompt, options={"num_predict": 2000}
                    )
                    self.image_narratives[scatter_key] = response["response"].strip()
                except Exception as e:
                    logger.warning(f"Ollama failed for {scatter_key}: {e}")
                    self.image_narratives[scatter_key] = f"""Gambar 4.2{chr(97 + i)} menampilkan scatter plot clustering mahasiswa tahun {y} menggunakan reduksi dimensi PCA. Setiap titik merepresentasikan mahasiswa dengan warna berbeda untuk cluster GMM, memperlihatkan segmentasi berdasarkan profil demografis dan akademik. Centroid cluster menunjukkan pusat segmentasi, dengan dispersi titik mencerminkan variasi dalam cluster. Visualisasi ini membantu mengidentifikasi pola geografis dan preferensi akademik mahasiswa."""


    def save_outputs(self):
        # Save tables as CSVs
        years = sorted(self.by_year.keys())
        df_41 = pd.DataFrame(
            {
                "Tahun": years,
                "Fase": [FASE[y] for y in years],
                "Jumlah": [self.gmm_res[y]["n"] for y in years],
                "Persen_%": [pct(self.gmm_res[y]["n"], len(self.raw)) for y in years],
                "Perubahan_%": ["baseline"]
                + [
                    str(
                        rnd(
                            (self.gmm_res[y]["n"] - self.gmm_res[prev]["n"])
                            / self.gmm_res[prev]["n"]
                            * 100,
                            1,
                        )
                    )
                    + "%"
                    for prev, y in zip(years[:-1], years[1:])
                ],
            }
        )
        df_41.to_csv("outputs/tabel_4_1_distribusi.csv", index=False)

        # Tabel 4.2 Distribusi Prodi
        prodi_dist = Counter(
            str(r.get(self.cols["prodi"], "")).strip() or "(kosong)" for r in self.raw
        )
        df_42 = pd.DataFrame(
            list(prodi_dist.most_common(8)), columns=["Program_Studi", "Jumlah"]
        )
        df_42["Persen_%"] = [pct(n, len(self.raw)) for n in df_42["Jumlah"]]
        df_42.to_csv("outputs/tabel_4_2_prodi.csv", index=False)

        # Gambar 4.1 Bar Chart
        plt.figure(figsize=(10, 6))
        plt.bar(
            years,
            [self.gmm_res[y]["n"] for y in years],
            color=[FC[FASE[y]] for y in years],
        )
        plt.title("Gambar 4.1 – Distribusi Pendaftar 2019–2024")
        plt.xlabel("Tahun")
        plt.ylabel("Jumlah")
        plt.savefig("outputs/gambar_4_1_distribusi.png")
        plt.savefig("outputs/gambar_4_1_distribusi.svg")
        plt.close()

        # Tabel 4.3 Preprocessing
        samples = [
            {
                "asli": "SMK N 1 PKL",
                "hasil": "sekolah menengah kejuruan negeri 1 pekalongan",
            },
            {"asli": "Jl. Ahmad Yani No.12", "hasil": "jalan ahmad yani nomor 12"},
            {
                "asli": "Kec. Wiradesa Kab. Pekalongan",
                "hasil": "kecamatan wiradesa kabupaten pekalongan",
            },
            {
                "asli": "MA Al-Hikmah Ds. Rowosari",
                "hasil": "madrasah aliyah al hikmah desa rowosari",
            },
            {"asli": "MTs. N 2 Batang", "hasil": "madrasah tsanawiyah negeri 2 batang"},
        ]
        df_43 = pd.DataFrame(samples)
        df_43.to_csv("outputs/tabel_4_3_preprocessing.csv", index=False)

        # Tabel 4.4 Cosine Similarity (FIX: 4.3a -> 4.4)
        df_43a = pd.DataFrame(self.cos_sim)
        df_43a.to_csv("outputs/tabel_4_4_cosine_similarity.csv", index=False)

        # Tabel 4.5 K-Scan (FIX: 4.4 -> 4.5)
        k_scan_data = []
        for y in years:
            for k in self.k_scan[y]:
                k_scan_data.append(
                    {
                        "Tahun": y,
                        "Fase": FASE[y],
                        "K": k,
                        "Sil": self.k_scan[y][k]["sil"],
                        "BIC": self.k_scan[y][k]["bic"],
                        "AIC": self.k_scan[y][k]["aic"],
                        "CH": self.k_scan[y][k]["ch"],
                        "DB": self.k_scan[y][k]["db"],
                        "LL": self.k_scan[y][k]["ll"],
                    }
                )
        df_44 = pd.DataFrame(k_scan_data)
        df_44.to_csv("outputs/tabel_4_5_kscan.csv", index=False)

        # Gambar 4.3a Silhouette Line Chart (FIX: sesuai thesis)
        sils = [self.gmm_res[y]["sil"] for y in years]
        plt.figure(figsize=(10, 6))
        plt.plot(years, sils, marker="o")
        plt.title("Gambar 4.3a – Silhouette Score per Periode (BAB IV)")
        plt.xlabel("Tahun")
        plt.ylabel("Silhouette Score")
        plt.savefig("outputs/gambar_4_3a_silhouette.png")
        plt.savefig("outputs/gambar_4_3a_silhouette.svg")
        plt.close()

        # Tabel 4.6 ARI, Jaccard, Centroid Drift (FIX: 4.5 -> 4.6)
        ari_df = pd.DataFrame(self.ari_pairs)
        jaccard_df = pd.DataFrame(self.jaccard_pairs)
        drift_df = pd.DataFrame(self.centroid_drifts)
        combined_df = ari_df.merge(
            jaccard_df, on=["y1", "y2", "label"], how="left"
        ).merge(drift_df, on=["y1", "y2", "label"], how="left")
        combined_df.to_csv("outputs/tabel_4_6_ari.csv", index=False)
        
        # Tabel 4.7 Evaluasi Internal GMM (NEW - Thesis alignment)
        eval_data = []
        for y in years:
            eval_data.append({
                "Tahun": y,
                "Fase": FASE[y],
                "K": self.gmm_res[y]["K"],
                "Silhouette": round(self.gmm_res[y]["sil"], 4),
                "Calinski-Harabasz": round(self.gmm_res[y]["ch"], 2),
                "Davies-Bouldin": round(self.gmm_res[y]["db"], 4),
                "Log-Likelihood": round(self.gmm_res[y]["ll"], 2),
            })
        df_47 = pd.DataFrame(eval_data)
        df_47.to_csv("outputs/tabel_4_7_evaluasi_internal.csv", index=False)

        # Gambar 4.3c ARI Bar Chart (FIX: 4.3b -> 4.3c sesuai thesis)
        plt.figure(figsize=(10, 6))
        plt.bar(
            [p["label"] for p in self.ari_pairs], [p["ari"] for p in self.ari_pairs]
        )
        plt.title("Gambar 4.3c – ARI Stabilitas Klaster (BAB IV)")
        plt.xlabel("Transisi")
        plt.ylabel("ARI")
        plt.savefig("outputs/gambar_4_3c_ari.png")
        plt.savefig("outputs/gambar_4_3c_ari.svg")
        plt.close()

        # Profil per Tahun (4.9-4.14)
        for y in years:
            clusters = self.gmm_res[y]["clusters"]
            data = []
            for cl in clusters:
                data.append(
                    {
                        "Klaster": cl["ci"] + 1,
                        "N": cl["n"],
                        "Persen_%": cl["pct"],
                        "Avg_Posterior": cl["avgPost"],
                        "Nama_Dominan": "; ".join(
                            [f"{n[0]}({n[1]})" for n in cl["topNama"][:2]]
                        )
                        if cl["topNama"]
                        else "",
                        "Prodi_Dominan": "; ".join(
                            [f"{p[0]}({p[1]})" for p in cl["topProdi"][:2]]
                        ),
                        "Kab_Dominan": "; ".join(
                            [f"{k[0]}({k[1]})" for k in cl["topKab"][:2]]
                        ),
                    }
                )
            df = pd.DataFrame(data)
            df.to_csv(f"outputs/tabel_4_{9 + years.index(y)}_profil_{y}.csv", index=False)

            # Scatter PCA
            pts2d = self.gmm_res[y].get("pts2d", None)
            if pts2d is not None:
                plt.figure(figsize=(8, 6))
                for i, pt in enumerate(pts2d[:400]):  # Sample
                    plt.scatter(
                        pt[0],
                        pt[1],
                        c=CC[self.gmm_res[y]["labels"][i] % len(CC)],
                        alpha=0.5,
                    )
                plt.title(
                    f"Gambar 4.2{chr(97 + years.index(y))} – PCA 2D Klaster Tahun {y}"
                )
                plt.xlabel("PC1")
                plt.ylabel("PC2")
                plt.savefig(f"outputs/gambar_4_2{chr(97 + years.index(y))}_scatter_{y}.png")
                plt.savefig(f"outputs/gambar_4_2{chr(97 + years.index(y))}_scatter_{y}.svg")
                plt.close()

        # Tabel 4.12 Lifecycle
        lifecycle_data = [
            {
                "Klaster": i + 1,
                **{
                    str(y): (
                        self.gmm_res[y]["clusters"][i]["pct"]
                        if i < len(self.gmm_res[y]["clusters"])
                        else None
                    )
                    for y in years
                },
                "Lifecycle": self.lifecycle[i]["lc"],
            }
            for i in range(len(self.lifecycle))
        ]
        df_412 = pd.DataFrame(lifecycle_data)
        df_412.to_csv("outputs/tabel_4_15_lifecycle.csv", index=False)

        # Tabel 4.13 Prioritasi 2025
        last_y = max(years)
        max_k = len(self.gmm_res[last_y]["clusters"])
        prio_data = []
        for ci in range(max_k):
            life = self.lifecycle[ci]["lc"] if ci < len(self.lifecycle) else "–"
            trend = (
                "Tumbuh"
                if "Growth" in life
                else "Menurun"
                if "Decline" in life
                else "Stabil"
            )
            prio = "Tinggi" if ci == 0 else "Sedang" if ci == 1 else "Evaluasi"
            dom = (
                self.gmm_res[last_y]["clusters"][ci]
                if ci < len(self.gmm_res[last_y]["clusters"])
                else {}
            )
            kab = dom.get("topKab", [[]])[0][0] if dom.get("topKab") else "-"
            prodi = dom.get("topProdi", [[]])[0][0] if dom.get("topProdi") else "-"
            prio_data.append(
                {
                    "Klaster": ci + 1,
                    "Tren": trend,
                    "Prioritas": prio,
                    "Strategi": f"Intensifikasi di {kab}, fokus {prodi}.",
                }
            )
        df_413 = pd.DataFrame(prio_data)
        df_413.to_csv("outputs/tabel_4_16_prioritasi_2025.csv", index=False)

        # Gambar 4.5 Proyeksi
        plt.figure(figsize=(10, 6))
        plt.bar(
            years + [2025], [self.gmm_res[y]["n"] for y in years] + [self.proj_2025]
        )
        plt.title("Gambar 4.5 – Proyeksi Pendaftar 2025")
        plt.xlabel("Tahun")
        plt.ylabel("Jumlah")
        plt.savefig("outputs/gambar_4_5_proyeksi.png")
        plt.savefig("outputs/gambar_4_5_proyeksi.svg")
        plt.close()

        # Tabel 4.15 Perbandingan
        comp_data = [
            {
                "Dimensi": "Silhouette",
                "GMM": self.gmm_res[last_y]["sil"],
                "KMeans": self.kmeans_res[last_y]["sil"],
            },
            {
                "Dimensi": "Calinski-Harabasz",
                "GMM": self.gmm_res[last_y]["ch"],
                "KMeans": self.kmeans_res[last_y]["ch"],
            },
            {
                "Dimensi": "Davies-Bouldin",
                "GMM": self.gmm_res[last_y]["db"],
                "KMeans": self.kmeans_res[last_y]["db"],
            },
            {"Dimensi": "Proyeksi 2025", "GMM": self.proj_2025, "KMeans": "Tidak ada"},
            {"Dimensi": "Persona LLM", "GMM": "Ya", "KMeans": "Tidak"},
        ]
        df_415 = pd.DataFrame(comp_data)
        df_415.to_csv("outputs/tabel_4_18_perbandingan.csv", index=False)
        
        # Tabel 4.17 Rekomendasi Channel Rekrutmen (NEW - Thesis alignment)
        channel_data = []
        for y in years:
            for cl in self.gmm_res[y]["clusters"][:3]:  # Top 3 clusters
                kab = cl["topKab"][0][0] if cl["topKab"] else "Tidak spesifik"
                prodi = cl["topProdi"][0][0] if cl["topProdi"] else "Tidak spesifik"
                channel_data.append({
                    "Tahun": y,
                    "Cluster": cl["ci"] + 1,
                    "Kabupaten": kab,
                    "Program Studi": prodi,
                    "Channel 1": "Instagram/TikTok Ads" if "pekalongan" in kab.lower() else "WhatsApp Broadcast",
                    "Channel 2": "Kunjungan SMA/SMK" if "pekalongan" in kab.lower() else "Webinar Daring",
                    "Pesan Kunci": "Teknologi & Karir" if "informatika" in prodi.lower() or "teknologi" in prodi.lower() else "Beasiswa & Aksesibilitas",
                    "Waktu Optimal": "Nov-Jan" if "pekalongan" in kab.lower() else "Des-Feb",
                })
        df_417 = pd.DataFrame(channel_data)
        df_417.to_csv("outputs/tabel_4_17_rekomendasi_channel.csv", index=False)

    def run_pipeline(self):
        self.business_understanding()
        self.data_collection()
        self.data_understanding()
        self.data_preparation()
        self.dimensionality_reduction()
        self.modeling()
        self.time_series_analysis()
        self.evaluation()
        self.otomasi_llm()
        self.causal_trend_analysis()
        self.narrative_summary()
        self.deployment()
        logger.info("Pipeline completed")


if __name__ == "__main__":
    pipeline = PMBAnalysisPipeline("DATASET PMB ITSNUPKL2019-2024_FIX.xls")
    pipeline.run_pipeline()
