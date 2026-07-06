import logging
import os

import matplotlib.pyplot as plt
import pandas as pd

from src.config import CLUSTER_COLORS as CC
from src.config import FASE, OUTPUTS_DIR
from src.config import PHASE_COLORS as FC
from src.core.preprocessor import flush_llm_cache

logger = logging.getLogger(__name__)


class DeploymentMixin:
    def deployment(self):
        logger.info("DEPLOYMENT: Prioritasi segmen dinamis, mapping channel, proyeksi 2025")
        self._report_progress("Lifecycle analysis...", 5)
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
            self.lifecycle.append({
                "ci": ci,
                "pcts": pcts,
                "lc": "📈 Growth" if diff > 5 else "📉 Decline" if diff < -5 else "➡️ Stable",
            })
        self._report_progress("Generating table narratives...", 20)
        self.generate_table_narratives()
        self._report_progress("Saving outputs...", 80)
        self.save_outputs()
        flush_llm_cache()
        self._report_progress("Deployment completed", 100)

    def generate_table_narratives(self):
        logger.info("GENERATE TABLE NARRATIVES")
        self.table_narratives = {}
        self.image_narratives = {}
        _nc = [0]
        _total_narratives = 27

        def _narr_progress(msg):
            _nc[0] += 1
            pct = 20 + int(_nc[0] / _total_narratives * 55)
            self._report_progress(f"{msg} ({_nc[0]}/{_total_narratives})", pct)

        def generate_narrative(table_name, file_path, prompt_text):
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                prompt = (
                    f"Berikan penjelasan lengkap dan detail untuk {table_name} berdasarkan "
                    f"data berikut: {df.to_string()}. {prompt_text}"
                )
                try:
                    _narr_progress(table_name)
                    return self.generate_llm_response(prompt, self.llm_provider, None, 2000, model=self.llm_model)
                except Exception as e:
                    logger.warning(f"LLM failed for {table_name}: {e}")
                    try:
                        return self.generate_llm_response(prompt, self.llm_provider, None, 3000, model=self.llm_model)
                    except Exception as e2:
                        logger.warning(f"LLM failed again: {e2}")
                        return f"Tabel {table_name} menyajikan data statistik penting dari analisis PMB."
            _narr_progress(f"{table_name} (no data)")
            return None

        self.table_narratives["tabel_4_1"] = (
            generate_narrative("Tabel 4.1 Distribusi Pendaftar", str(OUTPUTS_DIR / "tabel_4_1_distribusi.csv"),
                              "Jelaskan tren pendaftaran dan perubahan persentase antar tahun.")
            or """Tabel 4.1 menyajikan distribusi jumlah pendaftar mahasiswa baru ITSNU Pekalongan selama periode 2019-2024."""
        )
        self.table_narratives["tabel_4_2"] = (
            generate_narrative("Tabel 4.2 Distribusi Program Studi", str(OUTPUTS_DIR / "tabel_4_2_prodi.csv"),
                              "Jelaskan distribusi pendaftar berdasarkan program studi.")
            or """Tabel 4.2 menggambarkan distribusi pendaftar berdasarkan program studi."""
        )
        self.table_narratives["tabel_4_3"] = (
            generate_narrative("Tabel 4.3 Preprocessing Data", str(OUTPUTS_DIR / "tabel_4_3_preprocessing.csv"),
                              "Jelaskan hasil preprocessing data sebelum analisis.")
            or """Tabel 4.3 mendokumentasikan hasil tahap Data Preparation dalam metodologi CRISP-DM."""
        )
        self.table_narratives["tabel_4_4"] = (
            generate_narrative("Tabel 4.4 Cosine Similarity", str(OUTPUTS_DIR / "tabel_4_4_cosine_similarity.csv"),
                              "Jelaskan tingkat kesamaan antar tahun berdasarkan cosine similarity.")
            or """Tabel 4.4 menampilkan matriks cosine similarity antar tahun."""
        )
        self.table_narratives["tabel_4_5"] = (
            generate_narrative("Tabel 4.5 K-Means Clustering", str(OUTPUTS_DIR / "tabel_4_5_kscan.csv"),
                              "Jelaskan hasil clustering dengan K-Means dan silhouette scores.")
            or """Tabel 4.5 menyajikan hasil analisis clustering menggunakan K-Means."""
        )
        self.table_narratives["tabel_4_7"] = (
            generate_narrative("Tabel 4.7 Evaluasi Internal GMM", str(OUTPUTS_DIR / "tabel_4_7_evaluasi_internal.csv"),
                              "Jelaskan metrik evaluasi internal GMM per tahun.")
            or """Tabel 4.7 menyajikan metrik evaluasi internal GMM per tahun."""
        )
        self.table_narratives["tabel_4_6"] = (
            generate_narrative("Tabel 4.6 Adjusted Rand Index", str(OUTPUTS_DIR / "tabel_4_6_ari.csv"),
                              "Jelaskan stabilitas cluster antar tahun menggunakan ARI.")
            or """Tabel 4.6 menampilkan Adjusted Rand Index antar tahun."""
        )
        self.table_narratives["tabel_4_15"] = (
            generate_narrative("Tabel 4.15 Lifecycle Analysis", str(OUTPUTS_DIR / "tabel_4_15_lifecycle.csv"),
                              "Jelaskan analisis lifecycle dan fase pendaftaran.")
            or """Tabel 4.15 menyajikan analisis lifecycle pendaftaran."""
        )
        self.table_narratives["tabel_4_16"] = (
            generate_narrative("Tabel 4.16 Prioritas 2025", str(OUTPUTS_DIR / "tabel_4_16_prioritasi_2025.csv"),
                              "Jelaskan prioritas pendaftaran untuk tahun 2025.")
            or """Tabel 4.16 menyajikan prioritas pendaftaran untuk 2025."""
        )
        self.table_narratives["tabel_4_17"] = (
            generate_narrative("Tabel 4.17 Rekomendasi Channel Rekrutmen", str(OUTPUTS_DIR / "tabel_4_17_rekomendasi_channel.csv"),
                              "Jelaskan rekomendasi channel rekrutmen per cluster.")
            or """Tabel 4.17 menyajikan rekomendasi channel rekrutmen."""
        )
        self.table_narratives["tabel_4_18"] = (
            generate_narrative("Tabel 4.18 Perbandingan", str(OUTPUTS_DIR / "tabel_4_18_perbandingan.csv"),
                              "Jelaskan perbandingan hasil analisis dengan baseline.")
            or """Tabel 4.18 menyajikan perbandingan hasil analisis."""
        )
        years = sorted(self.by_year.keys())
        for i, y in enumerate(years):
            table_num = f"4_{9 + i}"
            file_name = str(OUTPUTS_DIR / f"tabel_{table_num}_profil_{y}.csv")
            self.table_narratives[f"tabel_{table_num}"] = (
                generate_narrative(f"Tabel {table_num} Profil Tahun {y}", file_name,
                                  f"Jelaskan profil cluster untuk tahun {y}.")
                or f"""Tabel {table_num} menyajikan profil cluster mahasiswa tahun {y}."""
            )

        if os.path.exists(str(OUTPUTS_DIR / "tabel_4_1_distribusi.csv")):
            _narr_progress("Gambar 4.1")
            df = pd.read_csv(str(OUTPUTS_DIR / "tabel_4_1_distribusi.csv"))
            prompt = f"Analisis visual Gambar 4.1 sebagai diagram batang distribusi pendaftar. Data: {df.to_string()}"
            self.image_narratives["gambar_4_1"] = self.generate_llm_response(
                prompt, self.llm_provider, None, 2000, model=self.llm_model
            ) or """Gambar 4.1 menampilkan distribusi pendaftar 2019-2024."""

        if os.path.exists(str(OUTPUTS_DIR / "tabel_4_5_kscan.csv")):
            _narr_progress("Gambar 4.3a")
            df_kscan = pd.read_csv(str(OUTPUTS_DIR / "tabel_4_5_kscan.csv"))
            prompt = f"Analisis visual Gambar 4.3a silhouette scores. Data: {df_kscan.to_string()}"
            self.image_narratives["gambar_4_3a"] = self.generate_llm_response(
                prompt, self.llm_provider, None, 2000, model=self.llm_model
            ) or """Gambar 4.3a memvisualisasikan silhouette scores."""

        if os.path.exists(str(OUTPUTS_DIR / "tabel_4_6_ari.csv")):
            _narr_progress("Gambar 4.3c")
            df_ari = pd.read_csv(str(OUTPUTS_DIR / "tabel_4_6_ari.csv"))
            prompt = f"Analisis visual Gambar 4.3c ARI heatmap. Data: {df_ari.to_string()}"
            self.image_narratives["gambar_4_3c"] = self.generate_llm_response(
                prompt, self.llm_provider, None, 2000, model=self.llm_model
            ) or """Gambar 4.3c menampilkan heatmap ARI."""

        if os.path.exists(str(OUTPUTS_DIR / "tabel_4_16_prioritasi_2025.csv")):
            _narr_progress("Gambar 4.5")
            df_proj = pd.read_csv(str(OUTPUTS_DIR / "tabel_4_16_prioritasi_2025.csv"))
            prompt = f"Analisis visual Gambar 4.5 proyeksi 2025. Data: {df_proj.to_string()}"
            self.image_narratives["gambar_4_5"] = self.generate_llm_response(
                prompt, self.llm_provider, None, 2000, model=self.llm_model
            ) or """Gambar 4.5 memvisualisasikan proyeksi 2025."""

        years = sorted(self.by_year.keys())
        for i, y in enumerate(years):
            _narr_progress(f"Gambar 4.2{chr(97 + i)}")
            scatter_key = f"gambar_4_2{chr(97 + i)}"
            csv_file = str(OUTPUTS_DIR / f"tabel_4_{9 + i}_profil_{y}.csv")
            if os.path.exists(csv_file):
                df_scatter = pd.read_csv(csv_file)
                prompt = f"Analisis visual scatter plot Gambar 4.2{chr(97 + i)} tahun {y}. Data: {df_scatter.to_string()}"
                self.image_narratives[scatter_key] = self.generate_llm_response(
                    prompt, self.llm_provider, None, 2000, model=self.llm_model
                ) or f"""Gambar 4.2{chr(97 + i)} scatter plot clustering tahun {y}."""

    def save_outputs(self):
        years = sorted(self.by_year.keys())

        df_41 = pd.DataFrame({
            "Tahun": years,
            "Fase": [FASE[y] for y in years],
            "Jumlah": [self.gmm_res[y]["n"] for y in years],
            "Persen_%": [round(self.gmm_res[y]["n"] / len(self.raw) * 100, 1) for y in years],
            "Perubahan_%": ["baseline"] + [
                str(round((self.gmm_res[y]["n"] - self.gmm_res[prev]["n"]) / self.gmm_res[prev]["n"] * 100, 1)) + "%"
                for prev, y in zip(years[:-1], years[1:])
            ],
        })
        df_41.to_csv(str(OUTPUTS_DIR / "tabel_4_1_distribusi.csv"), index=False)

        from collections import Counter
        prodi_dist = Counter(
            str(r.get(self.cols["prodi"], "")).strip() or "(kosong)" for r in self.raw
        )
        df_42 = pd.DataFrame(list(prodi_dist.most_common(8)), columns=["Program_Studi", "Jumlah"])
        df_42["Persen_%"] = [round(n / len(self.raw) * 100, 1) for n in df_42["Jumlah"]]
        df_42.to_csv(str(OUTPUTS_DIR / "tabel_4_2_prodi.csv"), index=False)

        plt.figure(figsize=(10, 6))
        plt.bar(years, [self.gmm_res[y]["n"] for y in years], color=[FC[FASE[y]] for y in years])
        plt.title("Gambar 4.1 – Distribusi Pendaftar 2019–2024")
        plt.xlabel("Tahun")
        plt.ylabel("Jumlah")
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_1_distribusi.png"))
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_1_distribusi.svg"))
        plt.close()

        samples = [
            {"asli": "SMK N 1 PKL", "hasil": "sekolah menengah kejuruan negeri 1 pekalongan"},
            {"asli": "Jl. Ahmad Yani No.12", "hasil": "jalan ahmad yani nomor 12"},
            {"asli": "Kec. Wiradesa Kab. Pekalongan", "hasil": "kecamatan wiradesa kabupaten pekalongan"},
            {"asli": "MA Al-Hikmah Ds. Rowosari", "hasil": "madrasah aliyah al hikmah desa rowosari"},
            {"asli": "MTs. N 2 Batang", "hasil": "madrasah tsanawiyah negeri 2 batang"},
        ]
        df_43 = pd.DataFrame(samples)
        df_43.to_csv(str(OUTPUTS_DIR / "tabel_4_3_preprocessing.csv"), index=False)

        df_43a = pd.DataFrame(self.cos_sim)
        df_43a.to_csv(str(OUTPUTS_DIR / "tabel_4_4_cosine_similarity.csv"), index=False)

        k_scan_data = []
        for y in years:
            for k in self.k_scan[y]:
                k_scan_data.append({
                    "Tahun": y, "Fase": FASE[y], "K": k,
                    "Sil": self.k_scan[y][k]["sil"],
                    "BIC": self.k_scan[y][k]["bic"],
                    "AIC": self.k_scan[y][k]["aic"],
                    "CH": self.k_scan[y][k]["ch"],
                    "DB": self.k_scan[y][k]["db"],
                    "LL": self.k_scan[y][k]["ll"],
                })
        df_44 = pd.DataFrame(k_scan_data)
        df_44.to_csv(str(OUTPUTS_DIR / "tabel_4_5_kscan.csv"), index=False)

        sils = [self.gmm_res[y]["sil"] for y in years]
        plt.figure(figsize=(10, 6))
        plt.plot(years, sils, marker="o")
        plt.title("Gambar 4.3a – Silhouette Score per Periode (BAB IV)")
        plt.xlabel("Tahun")
        plt.ylabel("Silhouette Score")
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_3a_silhouette.png"))
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_3a_silhouette.svg"))
        plt.close()

        ari_df = pd.DataFrame(self.ari_pairs)
        jaccard_df = pd.DataFrame(self.jaccard_pairs)
        drift_df = pd.DataFrame(self.centroid_drifts)
        combined_df = ari_df.merge(jaccard_df, on=["y1", "y2", "label"], how="left").merge(
            drift_df, on=["y1", "y2", "label"], how="left"
        )
        combined_df.to_csv(str(OUTPUTS_DIR / "tabel_4_6_ari.csv"), index=False)

        eval_data = []
        for y in years:
            eval_data.append({
                "Tahun": y, "Fase": FASE[y], "K": self.gmm_res[y]["K"],
                "Silhouette": round(self.gmm_res[y]["sil"], 4),
                "Calinski-Harabasz": round(self.gmm_res[y]["ch"], 2),
                "Davies-Bouldin": round(self.gmm_res[y]["db"], 4),
                "Log-Likelihood": round(self.gmm_res[y]["ll"], 2),
            })
        df_47 = pd.DataFrame(eval_data)
        df_47.to_csv(str(OUTPUTS_DIR / "tabel_4_7_evaluasi_internal.csv"), index=False)

        plt.figure(figsize=(10, 6))
        plt.bar([p["label"] for p in self.ari_pairs], [p["ari"] for p in self.ari_pairs])
        plt.title("Gambar 4.3c – ARI Stabilitas Klaster (BAB IV)")
        plt.xlabel("Transisi")
        plt.ylabel("ARI")
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_3c_ari.png"))
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_3c_ari.svg"))
        plt.close()

        for y in years:
            clusters = self.gmm_res[y]["clusters"]
            data = []
            for cl in clusters:
                data.append({
                    "Klaster": cl["ci"] + 1,
                    "N": cl["n"],
                    "Persen_%": cl["pct"],
                    "Avg_Posterior": cl["avgPost"],
                    "Nama_Dominan": "; ".join([f"{n[0]}({n[1]})" for n in cl["topNama"][:2]]) if cl["topNama"] else "",
                    "Prodi_Dominan": "; ".join([f"{p[0]}({p[1]})" for p in cl["topProdi"][:2]]),
                    "Kab_Dominan": "; ".join([f"{k[0]}({k[1]})" for k in cl["topKab"][:2]]),
                })
            df = pd.DataFrame(data)
            df.to_csv(str(OUTPUTS_DIR / f"tabel_4_{9 + years.index(y)}_profil_{y}.csv"), index=False)

            pts2d = self.gmm_res[y].get("pts_2d", None)
            if pts2d is not None:
                plt.figure(figsize=(8, 6))
                for i, pt in enumerate(pts2d[:400]):
                    plt.scatter(pt[0], pt[1], c=CC[self.gmm_res[y]["labels"][i] % len(CC)], alpha=0.5)
                plt.title(f"Gambar 4.2{chr(97 + years.index(y))} – PCA 2D Klaster Tahun {y}")
                plt.xlabel("PC1")
                plt.ylabel("PC2")
                plt.savefig(str(OUTPUTS_DIR / f"gambar_4_2{chr(97 + years.index(y))}_scatter_{y}.png"))
                plt.savefig(str(OUTPUTS_DIR / f"gambar_4_2{chr(97 + years.index(y))}_scatter_{y}.svg"))
                plt.close()

        lifecycle_data = [{
            "Klaster": i + 1,
            **{str(y): (self.gmm_res[y]["clusters"][i]["pct"] if i < len(self.gmm_res[y]["clusters"]) else None) for y in years},
            "Lifecycle": self.lifecycle[i]["lc"],
        } for i in range(len(self.lifecycle))]
        df_412 = pd.DataFrame(lifecycle_data)
        df_412.to_csv(str(OUTPUTS_DIR / "tabel_4_15_lifecycle.csv"), index=False)

        last_y = max(years)
        max_k = len(self.gmm_res[last_y]["clusters"])
        prio_data = []
        for ci in range(max_k):
            life = self.lifecycle[ci]["lc"] if ci < len(self.lifecycle) else "–"
            trend = "Tumbuh" if "Growth" in life else "Menurun" if "Decline" in life else "Stabil"
            prio = "Tinggi" if ci == 0 else "Sedang" if ci == 1 else "Evaluasi"
            dom = self.gmm_res[last_y]["clusters"][ci] if ci < len(self.gmm_res[last_y]["clusters"]) else {}
            kab = dom.get("topKab", [[]])[0][0] if dom.get("topKab") else "-"
            prodi = dom.get("topProdi", [[]])[0][0] if dom.get("topProdi") else "-"
            prio_data.append({"Klaster": ci + 1, "Tren": trend, "Prioritas": prio, "Strategi": f"Intensifikasi di {kab}, fokus {prodi}."})
        df_413 = pd.DataFrame(prio_data)
        df_413.to_csv(str(OUTPUTS_DIR / "tabel_4_16_prioritasi_2025.csv"), index=False)

        plt.figure(figsize=(10, 6))
        plt.bar(list(years) + [2025], [self.gmm_res[y]["n"] for y in years] + [self.proj_2025])
        plt.title("Gambar 4.5 – Proyeksi Pendaftar 2025")
        plt.xlabel("Tahun")
        plt.ylabel("Jumlah")
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_5_proyeksi.png"))
        plt.savefig(str(OUTPUTS_DIR / "gambar_4_5_proyeksi.svg"))
        plt.close()

        comp_data = [
            {"Dimensi": "Silhouette", "GMM": self.gmm_res[last_y]["sil"], "KMeans": self.kmeans_res[last_y]["sil"]},
            {"Dimensi": "Calinski-Harabasz", "GMM": self.gmm_res[last_y]["ch"], "KMeans": self.kmeans_res[last_y]["ch"]},
            {"Dimensi": "Davies-Bouldin", "GMM": self.gmm_res[last_y]["db"], "KMeans": self.kmeans_res[last_y]["db"]},
            {"Dimensi": "Proyeksi 2025", "GMM": self.proj_2025, "KMeans": "Tidak ada"},
            {"Dimensi": "Persona LLM", "GMM": "Ya", "KMeans": "Tidak"},
        ]
        df_415 = pd.DataFrame(comp_data)
        df_415.to_csv(str(OUTPUTS_DIR / "tabel_4_18_perbandingan.csv"), index=False)

        channel_data = []
        for y in years:
            for cl in self.gmm_res[y]["clusters"][:3]:
                kab = cl["topKab"][0][0] if cl["topKab"] else "Tidak spesifik"
                prodi = cl["topProdi"][0][0] if cl["topProdi"] else "Tidak spesifik"
                channel_data.append({
                    "Tahun": y, "Cluster": cl["ci"] + 1,
                    "Kabupaten": kab, "Program Studi": prodi,
                    "Channel 1": "Instagram/TikTok Ads" if "pekalongan" in kab.lower() else "WhatsApp Broadcast",
                    "Channel 2": "Kunjungan SMA/SMK" if "pekalongan" in kab.lower() else "Webinar Daring",
                    "Pesan Kunci": "Teknologi & Karir" if "informatika" in prodi.lower() or "teknologi" in prodi.lower() else "Beasiswa & Aksesibilitas",
                    "Waktu Optimal": "Nov-Jan" if "pekalongan" in kab.lower() else "Des-Feb",
                })
        df_417 = pd.DataFrame(channel_data)
        df_417.to_csv(str(OUTPUTS_DIR / "tabel_4_17_rekomendasi_channel.csv"), index=False)
