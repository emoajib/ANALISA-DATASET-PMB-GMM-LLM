# Vetted by AI - Manual Review Required by Senior Engineer/Manager
import os

PROVIDER_REGISTRY = {
    "Ollama": {"key": "ollama", "label": "Ollama (local)", "type": "local"},
    "OpenRouter": {"key": "openrouter", "label": "OpenRouter (Free Cloud)", "type": "cloud",
                   "endpoint": "https://openrouter.ai/api/v1/chat/completions"},
    "9Router": {"key": "9router", "label": "9Router (Local Proxy)", "type": "cloud",
                "endpoint": "http://localhost:20128/v1/chat/completions"},
    "Gemini": {"key": "gemini", "label": "Gemini CLI", "type": "cli"},
    "Kilo": {"key": "kilo", "label": "Kilo CLI", "type": "cli"},
    "OpenCode": {"key": "opencode", "label": "OpenCode CLI", "type": "cli"},
}

PROVIDER_NAMES = list(PROVIDER_REGISTRY.keys())
PROVIDER_KEYS = [v["key"] for v in PROVIDER_REGISTRY.values()]

def get_provider_key(name):
    return PROVIDER_REGISTRY.get(name, {}).get("key", name.lower())

def get_provider_label(name):
    return PROVIDER_REGISTRY.get(name, {}).get("label", name)

OLLAMA_MODELS = [
    "llama3.2:latest",
    "phi3:latest",
    "deepseek-r1:1.5b",
    "qwen2.5-coder:1.5b",
]

DEFAULT_OLLAMA_MODEL = "llama3.2:latest"

# Free models tersedia di OpenRouter (tidak perlu bayar)
OPENROUTER_FREE_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter/free",
]

DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Models via 9Router local proxy — verified WORK via pipeline test 12 Juli 2026
# Dari 25+ model yang dicoba, HANYA 2 yang return output non-kosong:
#   nvidia/minimaxai/minimax-m2.7  → primary (stabil, semua task)
#   oc/deepseek-v4-flash-free      → fallback (free tanpa auth)
# Semua model Kiro AI (kr/*), Antigravity (ag/*), Gemini return "Respons kosong".
# OpenRouter free return 429 rate limited.
# NVIDIA deepseek return 503 ResourceExhausted.
NINEROUTER_MODELS = [
    "nvidia/minimaxai/minimax-m2.7",      # WORK — stabil, semua task
    "oc/deepseek-v4-flash-free",           # WORK — free fallback
]

DEFAULT_NINEROUTER_MODEL = "nvidia/minimaxai/minimax-m2.7"

# Cache hasil fetch live agar tidak hit endpoint tiap rerun Streamlit.
_NINEROUTER_MODELS_LIVE = None
_NINEROUTER_MODELS_LIVE_T = 0.0


def fetch_ninerouter_models(
    base_url: str = "http://localhost:20128/v1/models",
    api_key: str = None,
    ttl: int = 300,
) -> list:
    """
    Ambil daftar model chat dari endpoint live 9Router (/v1/models).
    COMBO (smart auto-router) ditaruh di depan. Fallback ke NINEROUTER_MODELS
    (curated) kalau endpoint tidak reachable. Hasil di-cache ttl detik.
    """
    global _NINEROUTER_MODELS_LIVE, _NINEROUTER_MODELS_LIVE_T
    import time
    import requests

    now = time.time()
    if _NINEROUTER_MODELS_LIVE and (now - _NINEROUTER_MODELS_LIVE_T) < ttl:
        return _NINEROUTER_MODELS_LIVE

    api_key = api_key or os.getenv("NINEROUTER_API_KEY", "sk-dde8c533e27371c9-g79ucv-95effe97")
    try:
        resp = requests.get(
            base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", [])]
            if "COMBO" in ids:
                ids = ["COMBO"] + [m for m in ids if m != "COMBO"]
            _NINEROUTER_MODELS_LIVE = ids
            _NINEROUTER_MODELS_LIVE_T = now
            return ids
    except Exception:
        pass
    return NINEROUTER_MODELS


def get_provider_names():
    return list(PROVIDER_REGISTRY.keys())
