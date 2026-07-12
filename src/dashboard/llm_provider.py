# llm_provider.py
# Vetted by AI - Manual Review Required by Senior Engineer/Manager
# Vetted by Mujibul Hakim - Manual Review Required
"""
LLM Provider Router — Hybrid Pipeline
======================================
Mendukung:
  - Ollama (lokal, default)          → task PII-sensitive, massal
  - OpenRouter (cloud, free models)  → task high-reasoning
  - Gemini/Kilo/OpenCode CLI         → CLI fallback providers

Konfigurasi via .env atau environment variables.
"""

import subprocess
import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

# Load dotenv jika tersedia
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv belum terinstall, lanjut dengan os.environ

PROVIDERS = {
    "Ollama": ["ollama", "run"],
    "Gemini": ["gemini", "--skip-trust", "-p"],
    "Kilo": ["kilo"],
    "OpenCode": ["opencode"],
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"
)

NINEROUTER_API_KEY = os.getenv("NINEROUTER_API_KEY", "sk-dde8c533e27371c9-g79ucv-95effe97")
NINEROUTER_BASE_URL = "http://localhost:20128/v1/chat/completions"


def _call_openrouter(prompt: str, model: str = None, max_tokens: int = 1500) -> str:
    """
    Panggil OpenRouter API (cloud, free models).
    Digunakan untuk causal reasoning dan narrative summary.
    """
    api_key = OPENROUTER_API_KEY
    if not api_key:
        return "[OpenRouter error] OPENROUTER_API_KEY tidak ditemukan di .env"

    target_model = model or DEFAULT_OPENROUTER_MODEL
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ITSNU-PMB-Analysis",
        "X-Title": "ITSNU PMB Tesis Analysis",
    }
    payload = {
        "model": target_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    try:
        resp = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        elif resp.status_code == 429:
            # Rate limited — coba model fallback
            logger.warning(f"[OpenRouter] Rate limited pada {target_model}, mencoba fallback...")
            return _openrouter_with_fallback(prompt, max_tokens)
        else:
            return f"[OpenRouter error] HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.exceptions.Timeout:
        return "[OpenRouter timeout] Request melebihi 60 detik"
    except requests.exceptions.ConnectionError as e:
        return f"[OpenRouter connection error] {str(e)[:100]}"
    except Exception as e:
        return f"[OpenRouter exception] {str(e)[:100]}"


def _openrouter_with_fallback(prompt: str, max_tokens: int = 1500) -> str:
    """Coba model-model free OpenRouter secara berurutan sebagai fallback."""
    from providers import OPENROUTER_FREE_MODELS
    import time

    api_key = OPENROUTER_API_KEY
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ITSNU-PMB-Analysis",
    }

    for model in OPENROUTER_FREE_MODELS[1:]:  # Skip model pertama (sudah gagal)
        try:
            time.sleep(3)  # Jeda antar percobaan
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            resp = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    logger.info(f"[OpenRouter] ✅ Berhasil dengan fallback model: {model}")
                    return content
        except Exception:
            continue

    return "[OpenRouter error] Semua model free gagal atau rate-limited"


def _call_9router(prompt: str, model: str = None, max_tokens: int = 1500) -> str:
    """
    Panggil 9Router local proxy (OpenAI-compatible, http://localhost:20128).
    Menangani quirk 9Router:
      - response mengappend 'data: [DONE]' setelah JSON
      - model "thinking" (tencent/hy3, COMBO) taruh jawaban di field 'reasoning'
      - beberapa model return content kosong/null
    """
    import re
    import json as _json
    from providers import NINEROUTER_MODELS

    api_key = NINEROUTER_API_KEY
    if not api_key:
        return "[9Router error] NINEROUTER_API_KEY tidak ditemukan di .env"

    target = model or NINEROUTER_MODELS[0]
    models_to_try = [target] + [m for m in NINEROUTER_MODELS if m != target]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for m in models_to_try:
        try:
            payload = {
                "model": m,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            resp = requests.post(NINEROUTER_BASE_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200:
                continue
            text = resp.text.strip()
            text = re.sub(r'\n?data:\s*\[DONE\].*$', '', text, flags=re.DOTALL).strip()
            if text.count('{"id') > 1:
                idx = text.index('{"id')
                depth = 0
                for i, c in enumerate(text[idx:]):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                    if depth == 0:
                        text = text[idx:idx + i + 1]
                        break
            data = _json.loads(text)
            msg = data.get("choices", [{}])[0].get("message", {}) or {}
            content = msg.get("content") or msg.get("reasoning") or ""
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            if content:
                return content
        except Exception:
            continue
    return "[9Router error] Semua model 9Router gagal atau proxy tidak aktif"


def generate(prompt, provider="Ollama", max_tokens=1500, model=None):
    """
    Main generate function — router utama untuk semua provider.
    
    Provider "OpenRouter" / "9Router" menggunakan HTTP API cloud.
    Provider lainnya menggunakan subprocess CLI.
    """
    # ── 9Router Local Proxy (HTTP API) ───────────────────────────────
    if provider == "9Router":
        return _call_9router(prompt, model=model, max_tokens=max_tokens)

    # ── OpenRouter Cloud (HTTP API) ──────────────────────────────────
    if provider == "OpenRouter":
        return _call_openrouter(prompt, model=model, max_tokens=max_tokens)

    # ── Ollama Local (HTTP API) ──────────────────────────────────────
    if provider == "Ollama":
        target_model = model or os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        try:
            # Precheck: pastikan model sudah di-pull (cegah silent empty/404)
            try:
                tags = requests.get("http://127.0.0.1:11434/api/tags", timeout=10).json().get("models", [])
                available = {m["name"] for m in tags}
                if target_model not in available:
                    return f"[Ollama error] model '{target_model}' tidak ditemukan. Jalankan: ollama pull {target_model}"
            except Exception:
                pass  # lanjut saja, biar error HTTP asli yang muncul
            payload = {
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.3
                }
            }
            resp = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                out = resp.json().get("response", "").strip()
                if not out:
                    return f"[Ollama error] model '{target_model}' mengembalikan response kosong"
                return out
            else:
                return f"[Ollama error] HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.Timeout:
            return "[Ollama timeout] API request melebihi 120 detik"
        except requests.exceptions.ConnectionError:
            return "[Ollama error] Gagal koneksi ke http://127.0.0.1:11434. Pastikan Ollama berjalan."
        except Exception as e:
            return f"[Ollama exception] {str(e)}"

    # ── CLI Providers (Gemini, Kilo, OpenCode) ────────────────
    cmd = PROVIDERS.get(provider)
    if not cmd:
        return f"[{provider} error] Unknown provider"
    cmd = cmd + [prompt]

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode == 0:
            return r.stdout.strip()
        else:
            error_msg = r.stderr.strip()[:200] if r.stderr else "Unknown error"
            return f"[{provider} error] {error_msg}"
    except subprocess.TimeoutExpired:
        return f"[{provider} timeout] Process timed out after 120s"
    except FileNotFoundError:
        return f"[{provider} not found] CLI tool not installed"
    except Exception as e:
        return f"[{provider} exception] {str(e)}"
