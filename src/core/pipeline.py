import logging
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from src.core.data_collection import DataCollectionMixin
from src.core.deployment import DeploymentMixin
from src.core.llm_analysis import LlmAnalysisMixin
from src.core.modeling import ModelingMixin
from src.core.preprocessor import (
    avg,
    flush_embedding_cache,
    get_embedding,
    get_embeddings_batch,
    get_llm_hash,
    load_llm_cache,
    preprocess,
    rnd,
)
from src.llm import llm_provider

logger = logging.getLogger(__name__)

try:
    from src.llm.hybrid_provider import create_hybrid_provider
    _HYBRID_AVAILABLE = True
except ImportError:
    _HYBRID_AVAILABLE = False


class PMBAnalysisPipeline(
    DataCollectionMixin,
    ModelingMixin,
    LlmAnalysisMixin,
    DeploymentMixin,
):
    def __init__(self, file_path, llm_provider="Ollama", llm_model=None,
                 cloud_api_key=None, cloud_model=None):
        self.file_path = file_path
        self.llm_provider = llm_provider
        self.llm_model = llm_model or "llama3.2:3b"
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
        self._pt_cache = {}
        self.progress_callback = None
        _api_key = cloud_api_key or os.getenv("OPENROUTER_API_KEY", "")
        if _HYBRID_AVAILABLE and _api_key:
            self.hybrid = create_hybrid_provider(
                openrouter_api_key=_api_key,
                ollama_model=self.llm_model,
                cloud_model=cloud_model,
            )
            logger.info(f"[Pipeline] 🌐 Hybrid mode aktif — Cloud: {cloud_model or 'default'} | Local: {self.llm_model}")
        else:
            self.hybrid = None
            logger.info("[Pipeline] 💻 Local-only mode (Llama 3.2 Ollama)")

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def _report_progress(self, step, percent):
        percent = min(100, max(0, percent))
        if self.progress_callback:
            self.progress_callback(step, percent)

    def generate_llm_response(self, prompt, provider="Ollama", api_key=None, max_tokens=1500, model=None):
        cache = load_llm_cache()
        key = get_llm_hash(prompt, provider, max_tokens, model or "")
        if key in cache:
            return cache[key]
        response = llm_provider.generate(prompt, provider, max_tokens, model=model)
        if response and not response.startswith("[") and not response.startswith("Error"):
            cache[key] = response
        return response

    def build_pt(self, row):
        row_key = id(row)
        if row_key in self._pt_cache:
            return self._pt_cache[row_key]
        emb = get_embedding(
            " ".join([
                str(row.get(self.cols["nama"], "")),
                str(row.get(self.cols["sekolah"], "")),
                str(row.get(self.cols["kab"], "")),
                str(row.get(self.cols["kec"], "")),
                str(row.get(self.cols["alamat"], "")),
            ]),
            dim=self.emb_dim,
        )
        result = [
            *emb,
            row.get("_lat", 0),
            row.get("_lon", 0),
            row.get("prodi_enc", 0),
            row.get("jalur_enc", 0),
            row.get("kab_enc", 0),
        ]
        self._pt_cache[row_key] = result
        return result

    def data_preparation(self):
        self._report_progress("Text preprocessing", 20)
        logger.info("DATA PREPARATION: Otomasi batch 6 periode")
        for r in self.raw:
            for col in self.cols.values():
                if col:
                    r[col] = preprocess(r[col])

        self._report_progress("Generating embeddings (batch)", 40)
        self.cos_sim = []
        years = sorted(self.by_year.keys())
        sample_size = 100
        total_pairs = len(years) - 1
        for i in range(total_pairs):
            y1, y2 = years[i], years[i + 1]
            pair_pct = 40 + (i + 1) / total_pairs * 20
            self._report_progress(f"Embedding {y1}→{y2}", int(pair_pct))
            sample1 = self.by_year[y1] if len(self.by_year[y1]) <= sample_size else random.sample(self.by_year[y1], sample_size)
            sample2 = self.by_year[y2] if len(self.by_year[y2]) <= sample_size else random.sample(self.by_year[y2], sample_size)
            texts1 = [" ".join([r.get(self.cols["nama"], ""), r.get(self.cols["sekolah"], ""), r.get(self.cols["kab"], ""), r.get(self.cols["kec"], ""), r.get(self.cols["alamat"], "")]) for r in sample1]
            texts2 = [" ".join([r.get(self.cols["nama"], ""), r.get(self.cols["sekolah"], ""), r.get(self.cols["kab"], ""), r.get(self.cols["kec"], ""), r.get(self.cols["alamat"], "")]) for r in sample2]
            emb1 = get_embeddings_batch(texts1, dim=self.emb_dim, batch_size=32)
            emb2 = get_embeddings_batch(texts2, dim=self.emb_dim, batch_size=32)
            sim = avg([cosine_similarity([e1], [e2])[0][0] for e1 in emb1 for e2 in emb2])
            self.cos_sim.append({"trans": f"{y1}→{y2}", "sim": rnd(sim, 4)})
        self.avg_sim = rnd(avg([c["sim"] for c in self.cos_sim]), 4)

        self._report_progress("Geocoding coordinates", 60)
        from src.config import DATA_DIR
        geo_base = DATA_DIR / "processed" / "geo" / "geo_data" / "data" / "coll"
        kec_path = geo_base / "kecamatan_lat_long.csv"
        kab_path = geo_base / "kota_kab_lat_long.csv"
        kec_map = {}
        kab_map = {}
        try:
            if kec_path.exists():
                kec_df = pd.read_csv(str(kec_path))
                kec_map = {(row["name"].strip().lower()): (row["lat"], row["long"]) for _, row in kec_df.iterrows()}
            if kab_path.exists():
                kab_df = pd.read_csv(str(kab_path))
                kab_map = {(row["name"].strip().lower()): (row["lat"], row["long"]) for _, row in kab_df.iterrows()}
        except Exception as e:
            logger.warning(f"Geo data load error: {e}")
        total_raw = len(self.raw)
        for idx, r in enumerate(self.raw):
            if idx % 200 == 0:
                self._report_progress(f"Geocoding {idx}/{total_raw}", int(60 + idx / total_raw * 10))
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
        from sklearn.preprocessing import LabelEncoder
        self.label_encoders = {}
        ref2019 = self.by_year.get(2019, self.by_year[sorted(self.by_year.keys())[0]])
        for ki, key in enumerate(["prodi", "jalur", "kab"]):
            if self.cols[key]:
                encoder = LabelEncoder()
                values = [str(r.get(self.cols[key], "")).strip() for r in ref2019]
                encoder.fit(values)
                self.label_encoders[key] = encoder
                for idx, r in enumerate(self.raw):
                    if idx % 200 == 0:
                        self._report_progress(f"Encoding {key} {idx}/{total_raw}", int(70 + (ki + idx / total_raw) / 3 * 20))
                    val = str(r.get(self.cols[key], "")).strip()
                    if val not in encoder.classes_:
                        r[f"{key}_enc"] = encoder.transform(["Unknown"])[0] if "Unknown" in encoder.classes_ else -1
                    else:
                        r[f"{key}_enc"] = encoder.transform([val])[0]

        self._report_progress("Feature integration", 90)
        ref2019 = self.by_year.get(2019, self.by_year[sorted(self.by_year.keys())[0]])
        ref_pts = [self.build_pt(r) for r in ref2019]
        self.scaler = StandardScaler()
        self.scaler.fit(ref_pts)
        self._report_progress("Data preparation completed", 100)

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
        flush_embedding_cache()
        logger.info("Pipeline completed")


if __name__ == "__main__":
    _script_dir = Path(__file__).parent
    _data_path = (
        _script_dir.parent.parent / "data" / "raw" / "PMB_2019_2024.xlsx"
    )
    if not _data_path.exists():
        logger.error(f"Data file not found: {_data_path}")
        import sys
        sys.exit(1)
    pipeline = PMBAnalysisPipeline(str(_data_path))
    pipeline.run_pipeline()
