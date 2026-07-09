"""SINGLE source of truth for all constants."""

from pathlib import Path

# ─── Phases & Colors ───
FASE: dict[int, str] = {
    2019: "Pre-COVID",
    2020: "COVID Crisis",
    2021: "COVID Crisis",
    2022: "Recovery",
    2023: "Recovery",
    2024: "Recovery",
}

PHASE_COLORS: dict[str, str] = {
    "Pre-COVID": "#3B8BD4",
    "COVID Crisis": "#E24B4A",
    "Recovery": "#1D9E75",
}

CLUSTER_COLORS: list[str] = [
    "#3B8BD4", "#1D9E75", "#E24B4A",
    "#BA7517", "#534AB7", "#993356",
]

# ─── ML Parameters ───
GMM_PARAMS: dict = {
    "covariance_type": "full",
    "init_params": "k-means",
    "n_init": 10,
    "random_state": 42,
}
PCA_VARIANCE_RATIO: float = 0.95
ARI_THRESHOLD: float = 0.30
COSINE_SIM_THRESHOLD: float = 0.70

# ─── Paths ───
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
OUTPUT_DIR: Path = PROJECT_ROOT / "outputs"
TABLES_DIR: Path = OUTPUT_DIR / "tables"
FIGURES_DIR: Path = OUTPUT_DIR / "figures"
CACHE_DIR: Path = OUTPUT_DIR / "cache"

OUTPUTS_DIR: Path = OUTPUT_DIR  # alias for backward compat
MASTER_DATASET: Path = RAW_DATA_DIR / "PMB_2019_2024.xlsx"
EMBEDDING_CACHE: Path = PROCESSED_DATA_DIR / "embeddings" / "embedding_cache.json"
LLM_CACHE: Path = CACHE_DIR / "llm_cache.json"

# ─── LLM ───
OPENROUTER_FREE_MODELS: list[str] = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-coder:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-large-2411:free",
    "cohere/command-r-plus:free",
    "microsoft/phi-3-medium-128k-instruct:free",
]
