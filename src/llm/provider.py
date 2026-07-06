"""
HybridLLMProvider — Unified provider: Ollama lokal + OpenRouter cloud.

Routing logic:
  - Task PII-sensitive / massal → Ollama lokal
  - Task high-reasoning / agregat → OpenRouter cloud (free models)
Fallback: cloud tidak tersedia → otomatis ke Ollama lokal.
"""

import hashlib
import json
import logging
import os
from typing import Any

from src.llm.base import LLMProvider
from src.llm.engines import OllamaClient, OpenRouterClient
from src.llm.sanitizer import PIISanitizer

logger = logging.getLogger(__name__)

TASK_ROUTING = {
    "persona_generation": "local",
    "table_narrative": "local",
    "causal_trend_analysis": "cloud",
    "narrative_summary": "cloud",
}


class HybridLLMProvider(LLMProvider):
    """
    Hybrid Cognitive Pipeline: Llama 3.2 Lokal + OpenRouter Cloud.
    Fallback: Jika cloud tidak tersedia → otomatis ke Llama lokal.
    """

    def __init__(
        self,
        openrouter_api_key: str | None = None,
        ollama_model: str = "llama3.2:3b",
        cloud_model: str | None = None,
        enable_cache: bool = True,
    ):
        self.ollama = OllamaClient(model=ollama_model)
        self.api_key = openrouter_api_key or ""
        self.cloud_available = bool(self.api_key)
        self.cloud = OpenRouterClient(
            api_key=self.api_key, preferred_model=cloud_model
        ) if self.cloud_available else None
        self.sanitizer = PIISanitizer()
        self.enable_cache = enable_cache
        self._cache: dict[str, str] = {}

        if self.cloud_available:
            logger.info(f"[HybridProvider] ✅ Cloud: OpenRouter | Model: {cloud_model or 'default'}")
        else:
            logger.warning("[HybridProvider] ⚠️ Cloud key tidak ditemukan. Local-only mode.")

    def generate(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
        return self.ollama.generate(prompt, max_tokens, temperature)

    def is_available(self) -> bool:
        return True  # selalu ada fallback lokal

    # ── Cache ─────────────────────────────────────────────────
    def _cache_key(self, prompt: str, task: str) -> str:
        return hashlib.md5(f"{task}:{prompt}".encode()).hexdigest()

    def _get_cache(self, key: str) -> str | None:
        return self._cache.get(key) if self.enable_cache else None

    def _set_cache(self, key: str, value: str):
        if self.enable_cache:
            self._cache[key] = value

    # ── Cloud routing ─────────────────────────────────────────
    def _call_cloud(self, messages: list[dict[str, str]], temperature: float = 0.3,
                    max_tokens: int = 2000) -> str:
        if self.cloud:
            return self.cloud.chat(messages, max_tokens=max_tokens, temperature=temperature)
        raise RuntimeError("Cloud tidak tersedia")

    def _call_local(self, prompt: str, max_tokens: int = 1500) -> str:
        return self.ollama.generate(prompt, max_tokens=max_tokens)

    # ── High-level methods ────────────────────────────────────
    def causal_trend_analysis(
        self, year_from: int, year_to: int,
        fase_from: str, fase_to: str, ari: float,
        cluster_profiles_from: list[dict], cluster_profiles_to: list[dict],
        centroid_drift: float | None = None, jaccard: float | None = None,
    ) -> str:
        payload = self.sanitizer.sanitize_metrics_payload(
            year=year_to, ari=ari, fase_from=fase_from, fase_to=fase_to,
            cluster_profiles=cluster_profiles_to,
            centroid_drift=centroid_drift, jaccard=jaccard,
        )
        system = """Anda adalah Pakar Educational Data Mining dan Sosiologi Pendidikan Indonesia.
Tugas: analisis kausal mendalam tentang perubahan segmentasi mahasiswa.
ATURAN: JANGAN memanipulasi nilai numerik. Gunakan bahasa Indonesia ilmiah.
Output 300-500 kata."""
        user = f"""Analisis perubahan kausal segmentasi mahasiswa ITSNU Pekalongan:
{json.dumps(payload, indent=2, ensure_ascii=False)}
Pertanyaan: 1. Interpretasi ARI={ari:.4f} dalam transisi {fase_from}→{fase_to}?
2. Faktor eksternal paling mungkin? 3. Structural break? 4. Implikasi strategis?"""
        cache_key = self._cache_key(user, "causal")
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        if self.cloud:
            try:
                result = self.cloud.chat([
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ], temperature=0.3, max_tokens=2000)
                if not self.cloud.validate_integrity(result, {"ARI": ari}):
                    result += f"\n\n[VALIDASI]: ARI={ari:.4f} berdasarkan data aktual."
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"[Hybrid] Cloud causal gagal ({e}), fallback lokal...")

        result = self._call_local(f"{system}\n\n{user}", max_tokens=1500)
        self._set_cache(cache_key, result)
        return result

    def narrative_summary(
        self, total_mahasiswa: int, proyeksi_2025: int | None,
        avg_similarity: float | None, ari_summary: list[dict],
        periode: str = "2019-2024",
    ) -> str:
        payload = {
            "institusi": "ITSNU Pekalongan",
            "periode": periode,
            "total_pendaftar": total_mahasiswa,
            "proyeksi_2025": proyeksi_2025,
            "rata_rata_cosine_similarity": round(float(avg_similarity or 0), 4),
            "ringkasan_ari": ari_summary,
            "metodologi": "IndoBERT-768D + GMM + Time Series (CRISP-DM)",
        }
        system = """Anda adalah Peneliti Senior Educational Data Mining.
Buat ringkasan naratif akademik BAB IV tesis. Bahasa Indonesia ilmiah.
Paragraf mengalir (bukan bullet). 400-600 kata. Gaya: publikasi Sinta."""
        user = f"""Buat ringkasan BAB IV:
{json.dumps(payload, indent=2, ensure_ascii=False)}
Struktur: 1. Gambaran umum 2. Temuan utama GMM/ARI 3. Dampak COVID-19
4. Proyeksi 2025 5. Implikasi metodologi"""
        cache_key = self._cache_key(user, "summary")
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        if self.cloud:
            try:
                result = self.cloud.chat([
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ], temperature=0.4, max_tokens=2500)
                self._set_cache(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"[Hybrid] Cloud summary gagal ({e}), fallback lokal...")

        result = self._call_local(f"{system}\n\n{user}", max_tokens=2000)
        self._set_cache(cache_key, result)
        return result

    def get_status(self) -> dict[str, Any]:
        return {
            "cloud_available": self.cloud_available,
            "cloud_model": self.cloud.preferred_model if self.cloud else None,
            "local_model": self.ollama.model,
            "mode": "Hybrid" if self.cloud_available else "Local Only",
            "cache_size": len(self._cache),
        }


def create_hybrid_provider(
    openrouter_api_key: str | None = None,
    ollama_model: str = "llama3.2:3b",
    cloud_model: str | None = None,
) -> HybridLLMProvider:
    api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
    return HybridLLMProvider(
        openrouter_api_key=api_key,
        ollama_model=ollama_model,
        cloud_model=cloud_model,
    )
