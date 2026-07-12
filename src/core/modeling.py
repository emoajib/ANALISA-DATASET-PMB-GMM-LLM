import logging
from collections import Counter

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture

from src.config import ARI_THRESHOLD, FASE, PCA_VARIANCE_RATIO
from src.core.preprocessor import avg, pct, rnd

logger = logging.getLogger(__name__)


class ModelingMixin:
    def dimensionality_reduction(self):
        logger.info("DIMENSIONALITY REDUCTION: PCA 95% variance")
        ref2019 = (
            self.by_year[2019]
            if 2019 in self.by_year
            else self.by_year[sorted(self.by_year.keys())[0]]
        )
        ref_pts = [self.build_pt(r) for r in ref2019]
        scaled_ref = self.scaler.transform(ref_pts)
        self.pca = PCA(n_components=PCA_VARIANCE_RATIO)
        self.pca.fit(scaled_ref)
        self.n_comp = self.pca.n_components_
        # A7: PCA 2D di-fit SEKALI pada 2019 -> basis koordinat konsisten semua tahun
        self.pca_2d_model = PCA(n_components=2)
        self.pca_2d_model.fit(scaled_ref)

    def modeling(self):
        logger.info("MODELING: GMM per periode")
        years = sorted(self.by_year.keys())
        total_years = len(years)

        for idx, y in enumerate(years):
            progress_base = 40 + (idx / total_years) * 50
            self._report_progress(f"GMM Modeling {y}", int(progress_base))

            rows = self.by_year[y]
            pts = [self.build_pt(r) for r in rows]
            scaled_pts = self.scaler.transform(pts)
            pca_pts = self.pca.transform(scaled_pts)

            self.k_scan[y] = {}
            prev_bic = float("inf")
            increasing_count = 0

            for k in range(2, 7):
                if k >= len(rows):
                    break
                k_progress = progress_base + (k - 2) * (50 / (total_years * 5))
                self._report_progress(f"GMM {y} - K={k}", int(k_progress))
                try:
                    gmm = GaussianMixture(
                        n_components=k,
                        covariance_type="diag",
                        reg_covar=1.0,
                        init_params="k-means++",
                        max_iter=300,
                        n_init=10,
                        random_state=42,
                        tol=1e-3,
                    )
                    labels = gmm.fit_predict(pca_pts)
                    bic = gmm.bic(pca_pts)
                    aic = gmm.aic(pca_pts)
                    sil = silhouette_score(pca_pts, labels)

                    self.k_scan[y][k] = {
                        "sil": sil,
                        "bic": bic,
                        "aic": aic,
                        "ch": 0.0,
                        "db": 0.0,
                        "ll": gmm.score(pca_pts) * len(pca_pts),
                    }

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

            if self.k_scan[y]:
                best_k = min(self.k_scan[y], key=lambda x: self.k_scan[y][x]["bic"])
                self._report_progress(f"GMM {y} - fitting final K={best_k}", int(progress_base + 45))
                gmm = GaussianMixture(
                    n_components=best_k,
                    covariance_type="diag",
                    reg_covar=1.0,
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
                pts_2d = self.pca_2d(scaled_pts)

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
                    "centers": gmm.means_.tolist(),
                }
                # A1: simpan model & titik PCA untuk cross-prediction di time_series_analysis
                self.gmm_models[y] = gmm
                self.pca_pts_cache[y] = pca_pts

                self._report_progress(f"GMM {y} completed", int(progress_base + 50))
        self._report_progress("Modeling completed", 100)

    def pca_2d(self, matrix):
        # A7: transform dengan basis 2D yang di-fit sekali pada 2019 (lihat dimensionality_reduction)
        return self.pca_2d_model.transform(matrix).tolist()

    def top_n(self, rows, col, n=5):
        cnt = Counter(str(r.get(col, "")).strip() or "(kosong)" for r in rows)
        return cnt.most_common(n)

    def time_series_analysis(self):
        logger.info("TIME SERIES ANALYSIS: Hungarian-matched ARI, Jaccard, centroid drift + forecasting 2025")
        years = sorted(self.by_year.keys())
        for i in range(len(years) - 1):
            y1, y2 = years[i], years[i + 1]
            c1 = np.array(self.gmm_res[y1].get("centers", []))
            c2 = np.array(self.gmm_res[y2].get("centers", []))

            # Hungarian matching of centroids (centroid drift + alignment cluster index)
            if len(c1) > 0 and len(c2) > 0:
                cost = cdist(c1, c2, metric="euclidean")
                row_ind, col_ind = linear_sum_assignment(cost)
                matched_cost = cost[row_ind, col_ind].mean()
            else:
                row_ind = np.array([])
                col_ind = np.array([])
                matched_cost = float("inf")

            # A1: ARI cross-prediction — GMM(thn t) prediksi data thn t+1,
            #     ARI(label prediksi vs label aktual GMM thn t+1) = stabilitas struktural valid.
            actual = np.array(self.gmm_res[y2]["labels"])
            pred = self.gmm_models[y1].predict(self.pca_pts_cache[y2])
            ari_val = adjusted_rand_score(actual, pred) if len(actual) > 1 else 0.0
            is_break = ari_val < ARI_THRESHOLD
            self.ari_pairs.append({
                "y1": y1, "y2": y2,
                "label": f"{y1}→{y2}",
                "ari": rnd(ari_val, 4),
                "isBreak": is_break,
                "cat": "⚡ Structural Break" if is_break else ("⚠️ Drift Moderat" if ari_val < 0.6 else "✅ Stabil"),
                "method": "cross_prediction",
            })

            # A2: Jaccard keanggotaan dari confusion matrix prediksi vs aktual,
            #     di-align via Hungarian centroid (cluster t+1 -> index t).
            if len(c1) > 0 and len(c2) > 0:
                from sklearn.metrics import confusion_matrix
                label_map = {old: new for old, new in zip(col_ind, row_ind)}
                actual_m = np.array([label_map.get(lab, -1) for lab in actual])
                cm = confusion_matrix(pred, actual_m)
                jaccards = []
                for idx in range(min(cm.shape[0], cm.shape[1])):
                    tp = cm[idx, idx]
                    fp = cm[idx, :].sum() - tp
                    fn = cm[:, idx].sum() - tp
                    denom = tp + fp + fn
                    jaccards.append(tp / denom if denom > 0 else 0.0)
                jaccard_val = np.mean(jaccards) if jaccards else 0.0
            else:
                jaccard_val = 0.0
            self.jaccard_pairs.append({
                "y1": y1, "y2": y2,
                "label": f"{y1}→{y2}",
                "jaccard": rnd(jaccard_val, 4),
                "method": "hungarian_contingency",
            })

            # 3. Centroid drift dengan pasangan Hungarian
            cd = rnd(matched_cost, 4) if matched_cost != float("inf") else float("inf")
            self.centroid_drifts.append({
                "y1": y1, "y2": y2,
                "label": f"{y1}→{y2}",
                "drift": cd,
                "method": "hungarian_matched",
            })
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

    def evaluation(self):
        logger.info("EVALUATION: Multi-level - internal GMM metrics, stabilitas, komparasi GMM vs K-Means")
        self.kmeans_res = {}
        years_eval = list(self.by_year.keys())
        for yi, y in enumerate(years_eval):
            self._report_progress(f"K-Means comparison {y} ({yi+1}/{len(years_eval)})", 20 + int(yi / len(years_eval) * 70))
            pts = [self.build_pt(r) for r in self.by_year[y]]
            scaled_pts = self.scaler.transform(pts)
            pca_pts = self.pca.transform(scaled_pts)
            k = self.gmm_res[y]["K"]
            km = KMeans(n_clusters=k, init="k-means++", n_init=10, random_state=42)
            km_labels = km.fit_predict(pca_pts)
            sil_km = silhouette_score(pca_pts, km_labels)
            ch_km = calinski_harabasz_score(pca_pts, km_labels)
            db_km = davies_bouldin_score(pca_pts, km_labels)
            self.kmeans_res[y] = {"sil": sil_km, "ch": ch_km, "db": db_km}
            logger.info(f"{y} GMM Sil: {self.gmm_res[y]['sil']}, KMeans Sil: {sil_km}")
        self._report_progress("Evaluation completed", 100)
