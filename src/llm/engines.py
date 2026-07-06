"""
Consolidated LLM engines: Ollama (local), OpenRouter (cloud), CLI providers.

Replaces duplicate HTTP/CLI logic previously split across llm_provider.py
and hybrid_provider.py.
"""

import logging
import os
import subprocess
import time

import requests

from src.config import OPENROUTER_FREE_MODELS
from src.llm.base import LLMProvider

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# OLLAMA (Local)
# ─────────────────────────────────────────────────────────────
class OllamaClient(LLMProvider):
    """Local Ollama provider via HTTP API."""

    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://127.0.0.1:11434"):
        self.model = model
        self.base_url = base_url
        self._available: bool | None = None

    def generate(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": temperature},
                },
                timeout=120,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return f"[Ollama error] HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.ConnectionError:
            return "[Ollama error] Ollama tidak berjalan. Pastikan `ollama serve` aktif."
        except requests.exceptions.Timeout:
            return "[Ollama timeout] Request melebihi 120 detik"
        except Exception as e:
            return f"[Ollama exception] {e}"

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            self._available = resp.status_code == 200
        except requests.exceptions.ConnectionError:
            self._available = False
        return self._available


# ─────────────────────────────────────────────────────────────
# OPENROUTER (Cloud)
# ─────────────────────────────────────────────────────────────
class OpenRouterClient(LLMProvider):
    """OpenRouter cloud provider with model fallback + numerical validation."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str | None = None, preferred_model: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.preferred_model = preferred_model or "meta-llama/llama-3.3-70b-instruct:free"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ITSNU-PMB-Analysis",
            "X-Title": "ITSNU PMB Tesis",
        })

    def generate(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
        return self.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens, temperature=temperature)

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 2000,
             temperature: float = 0.3) -> str:
        """Generate dengan fallback otomatis ke model lain jika rate-limited."""
        models_to_try = [self.preferred_model] + [
            m for m in OPENROUTER_FREE_MODELS if m != self.preferred_model
        ]
        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"[OpenRouter] Mencoba: {model}")
                result = self._call(model, messages, temperature, max_tokens)
                logger.info(f"[OpenRouter] ✅ Berhasil: {model}")
                return result
            except requests.exceptions.HTTPError as e:
                if "429" in str(e):
                    logger.warning(f"[OpenRouter] ⚡ {model} rate-limited → next")
                    last_error = e
                    time.sleep(2)
                    continue
                last_error = e
                continue
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"[OpenRouter] ⏱️ {model} error → next")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"[OpenRouter] ⚠️ {model}: {str(e)[:80]}")
                last_error = e
                continue
        raise RuntimeError(
            f"[OpenRouter] Semua {len(models_to_try)} model gagal. "
            f"Terakhir: {last_error}"
        )

    def _call(self, model: str, messages: list[dict[str, str]],
              temperature: float, max_tokens: int) -> str:
        for attempt in range(3):
            try:
                resp = self.session.post(
                    self.BASE_URL,
                    json={"model": model, "messages": messages,
                          "temperature": temperature, "max_tokens": max_tokens},
                    timeout=60,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                delay = 5 * (2 ** attempt)
                logger.warning(f"[OpenRouter] Network error attempt {attempt+1}: {e}. Retry {delay}s...")
                time.sleep(delay)
                continue

            if resp.status_code == 429:
                raise requests.exceptions.HTTPError(f"429 {model}")
            if resp.status_code != 200:
                logger.warning(f"[OpenRouter] HTTP {resp.status_code}: {resp.text[:300]}")
                if attempt < 2:
                    time.sleep(5 * (2 ** attempt))
                    continue
                raise requests.exceptions.HTTPError(f"HTTP {resp.status_code}")

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("Respons kosong")
            return content

        raise RuntimeError(f"[OpenRouter] Gagal setelah 3 percobaan untuk model {model}")

    def validate_integrity(self, response: str, expected: dict[str, float]) -> bool:
        """Pastikan LLM tidak memanipulasi angka statistik."""
        for name, val in expected.items():
            expected_str = str(round(val, 2))
            if expected_str not in response and val != 0:
                logger.warning(f"[NumericalGuard] {name}={val} tidak ditemukan di output")
                return False
        return True

    def is_available(self) -> bool:
        return bool(self.api_key)


# ─────────────────────────────────────────────────────────────
# CLI PROVIDERS (Gemini, Kilo, OpenCode)
# ─────────────────────────────────────────────────────────────
CLI_COMMANDS = {
    "Gemini": ["gemini", "--skip-trust", "-p"],
    "Kilo": ["kilo"],
    "OpenCode": ["opencode"],
}


class CLIProvider(LLMProvider):
    """CLI-based provider (Gemini, Kilo, OpenCode)."""

    def __init__(self, name: str):
        self.name = name
        self.cmd_base = CLI_COMMANDS.get(name)
        if not self.cmd_base:
            raise ValueError(f"Unknown CLI provider: {name}")

    def generate(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
        cmd = self.cmd_base + [prompt]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return r.stdout.strip()
            return f"[{self.name} error] {r.stderr.strip()[:200]}"
        except subprocess.TimeoutExpired:
            return f"[{self.name} timeout] Process timed out"
        except FileNotFoundError:
            return f"[{self.name} not found] CLI tool not installed"
        except Exception as e:
            return f"[{self.name} exception] {str(e)[:100]}"

    def is_available(self) -> bool:
        try:
            subprocess.run([self.cmd_base[0], "--version"],
                           capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


# ─────────────────────────────────────────────────────────────
# ROUTER — standalone generate() matching old llm_provider.generate() API
# ─────────────────────────────────────────────────────────────
_ollama_client: OllamaClient | None = None
_openrouter_client: OpenRouterClient | None = None
_cli_clients: dict[str, CLIProvider] = {}


def router(prompt: str, provider: str = "Ollama", max_tokens: int = 1500,
           model: str | None = None) -> str:
    """
    Router fungsi — menggantikan llm_provider.generate().
    Parameter signature identik untuk backward compatibility.
    """
    global _ollama_client, _openrouter_client

    if provider == "Ollama":
        if _ollama_client is None:
            _ollama_client = OllamaClient(model=model or "llama3.2:3b")
        return _ollama_client.generate(prompt, max_tokens=max_tokens)

    if provider == "OpenRouter":
        if _openrouter_client is None:
            _openrouter_client = OpenRouterClient()
        return _openrouter_client.generate(prompt, max_tokens=max_tokens)

    if provider in CLI_COMMANDS:
        if provider not in _cli_clients:
            _cli_clients[provider] = CLIProvider(provider)
        return _cli_clients[provider].generate(prompt, max_tokens=max_tokens)

    return f"[{provider} error] Unknown provider"
