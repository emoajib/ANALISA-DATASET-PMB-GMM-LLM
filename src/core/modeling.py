import logging
from collections import Counter

import numpy as np
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
from src.core.preprocessor import avg, centroid_drift, jaccard_similarity, pct, rnd

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
                        covariance_type="full",
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
                    "centers": gmm.means_.tolist(),
                }
                self._report_progress(f"GMM {y} completed", int(progress_base + 50))
        self._report_progress("Modeling completed", 100)

    def pca_2d(self, matrix):
        from sklearn.decomposition import PCA
        pca2 = PCA(n_components=2)
        return pca2.fit_transform(matrix).tolist()

    def top_n(self, rows, col, n=5):
        cnt = Counter(str(r.get(col, "")).strip() or "(kosong)" for r in rows)
        return cnt.most_common(n)

    def time_series_analysis(self):
        logger.info("TIME SERIES ANALYSIS: Deteksi structural break dan forecasting 2025")
        years = sorted(self.by_year.keys())
        for i in range(len(years) - 1):
            y1, y2 = years[i], years[i + 1]
            l1 = self.gmm_res[y1]["labels"]
            l2 = self.gmm_res[y2]["labels"]
            n = min(len(l1), len(l2))
            a = adjusted_rand_score(l1[:n], l2[:n])
            is_break = a < ARI_THRESHOLD
            self.ari_pairs.append({
                "y1": y1, "y2": y2,
                "label": f"{y1}→{y2}",
                "ari": rnd(a, 4),
                "isBreak": is_break,
                "cat": "⚡ Structural Break" if is_break else ("⚠️ Drift Moderat" if a < 0.6 else "✅ Stabil"),
            })
            set1 = set(l1)
            set2 = set(l2)
            j = jaccard_similarity(set1, set2)
            self.jaccard_pairs.append({
                "y1": y1, "y2": y2,
                "label": f"{y1}→{y2}",
                "jaccard": rnd(j, 4),
            })
            c1 = self.gmm_res[y1].get("centers", [])
            c2 = self.gmm_res[y2].get("centers", [])
            cd = centroid_drift(c1, c2)
            self.centroid_drifts.append({
                "y1": y1, "y2": y2,
                "label": f"{y1}→{y2}",
                "drift": rnd(cd, 4),
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
