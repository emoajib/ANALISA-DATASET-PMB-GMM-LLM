"""
LLM Provider Router — Thin wrapper (backward compatible).

Semua implementasi engine telah dipindahkan ke src/llm/engines.py.
File ini hanya menyediakan alias `generate()` dan konstanta untuk
backward compatibility dengan kode lama (pipeline.py, dashboard).
"""

import os

# Legacy constants (used by old code)
PROVIDERS = {
    "Ollama": ["ollama", "run"],
    "Gemini": ["gemini", "--skip-trust", "-p"],
    "Kilo": ["kilo"],
    "OpenCode": ["opencode"],
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
)
