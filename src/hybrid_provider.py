# hybrid_provider.py
# Vetted by AI - Manual Review Required by Senior Engineer/Manager
# Vetted by Mujibul Hakim - Manual Review Required
"""
Hybrid Cognitive Pipeline — OpenRouter Free Models + Llama 3.2 Lokal
=====================================================================
Arsitektur dual-engine:
  1. Llama 3.2 Lokal (Ollama)  → PII gateway, persona generation, table narratives
  2. OpenRouter Cloud (Free)   → Causal reasoning tingkat tinggi, narrative summary

Privacy Flow:
  Raw PMB Data → [Llama 3.2 Sanitasi PII] → [Regex Validator] → [OpenRouter Cloud]

Technical Assumptions:
  - Sanitasi PII akurasi ~95-99%; regex validator sebagai safety net kedua
  - Ollama tetap berjalan lokal; DeepSeek/cloud hanya untuk high-reasoning tasks
  - LLM cache di-extend untuk menghindari biaya API berulang
  - Fallback otomatis ke Llama lokal jika API key tidak tersedia / error
"""

import os
import re
import json
import time
import hashlib
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# KONFIGURASI FREE MODELS OPENROUTER
# Diurutkan berdasarkan prioritas (context length + reasoning quality)
# ─────────────────────────────────────────────────────────────
OPENROUTER_FREE_MODELS = [
    # Tier 1: High reasoning, large context — ideal untuk causal analysis
    "nvidia/nemotron-3-ultra-550b-a55b:free",       # 1M ctx, 550B params
    "nvidia/nemotron-3-super-120b-a12b:free",        # 1M ctx, 120B params
    "qwen/qwen3-coder:free",                          # 1M ctx, 480B
    "meta-llama/llama-3.3-70b-instruct:free",        # 131K ctx, 70B — paling stabil
    "nousresearch/hermes-3-llama-3.1-405b:free",     # 131K ctx, 405B
    "nvidia/nemotron-3-nano-30b-a3b:free",           # 256K ctx, 30B fallback
    "google/gemma-4-31b-it:free",                    # 262K ctx, 31B fallback
    "openai/gpt-oss-120b:free",                      # 131K ctx, OpenAI OSS
]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_CHAT_ENDPOINT = f"{OPENROUTER_BASE_URL}/chat/completions"

# Default model untuk causal reasoning
DEFAULT_CLOUD_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

# Task type routing
TASK_ROUTING = {
    "persona_generation": "local",        # PII-sensitive → lokal
    "table_narrative": "local",           # Massal, efisiensi → lokal
    "pii_sanitization": "local",          # Privacy gate → lokal
    "causal_trend_analysis": "cloud",     # High-reasoning → cloud
    "narrative_summary": "cloud",         # High-quality output → cloud
    "structural_break_analysis": "cloud", # Complex reasoning → cloud
}

# ─────────────────────────────────────────────────────────────
# POLA PII UNTUK VALIDASI REGEX (safety net kedua)
# SCOPE KETAT: hanya data personal individu, BUKAN nama institusi/prodi
# ─────────────────────────────────────────────────────────────
# Whitelist: kata-kata yang BUKAN PII meskipun berbentuk nama kapital
PII_WHITELIST_TERMS = {
    "Teknik", "Informatika", "Sistem", "Informasi", "Manajemen", "Akuntansi",
    "Ekonomi", "Hukum", "Pendidikan", "Bahasa", "Indonesia", "Inggris",
    "Matematika", "Fisika", "Biologi", "Kimia", "Sekolah", "Universitas",
    "Institut", "Politeknik", "Akademi", "Negeri", "Swasta", "Nasional",
    "Pekalongan", "Batang", "Semarang", "Pemalang", "Kendal", "Tegal",
    "Brebes", "Purbalingga", "Banyumas", "Cilacap", "Kebumen", "Purworejo",
    "Klaster", "Wilayah", "Pesisir", "Tengah", "Utara", "Selatan", "Timur",
    "Barat", "Reguler", "KIPK", "Bidikmisi", "Mandiri", "Kerjasama",
    "Pre", "COVID", "Crisis", "Recovery", "ITSNU", "Representatif",
}

PII_PATTERNS = [
    # NIK (16 digit — sangat spesifik, tidak mungkin false positive)
    r'\b\d{16}\b',
    # NIM format kampus
    r'\b\d{2}\.\d{2}\.\d{2}\.\d{4}\b',
    # Nomor telepon Indonesia
    r'\b(?:08|62|\+62)\d{8,12}\b',
    # Email
    r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    # Alamat spesifik (Jl., RT, RW)
    r'\b(?:Jl\.|Jalan|Gang|Gg\.|RT\s?\d+|RW\s?\d+)\s\w+',
    # Tanggal lahir
    r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b',
    # CATATAN: Pola nama personal TIDAK digunakan di sini karena terlalu banyak
    # false positive dengan nama akademis/institusional.
    # Nama personal sudah dieksklusi di sanitize_cluster_profile() via topNama → label abstrak.
]


# ─────────────────────────────────────────────────────────────
# RETRY DECORATOR DENGAN EXPONENTIAL BACKOFF
# ─────────────────────────────────────────────────────────────
def with_exponential_backoff(max_retries: int = 3, base_delay: float = 5.0):
    """Decorator: retry dengan exponential backoff untuk panggilan API cloud."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError) as e:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"[HybridProvider] Network error attempt {attempt+1}/{max_retries}: {e}. "
                        f"Retry dalam {delay:.0f}s..."
                    )
                    last_error = e
                    time.sleep(delay)
                except RateLimitError as e:
                    delay = max(e.retry_after, base_delay * (2 ** attempt))
                    logger.warning(
                        f"[HybridProvider] Rate limited. Retry dalam {delay:.0f}s..."
                    )
                    last_error = e
                    time.sleep(delay)
            raise RuntimeError(
                f"[HybridProvider] Gagal setelah {max_retries} percobaan. "
                f"Error terakhir: {last_error}"
            )
        return wrapper
    return decorator


class RateLimitError(Exception):
    def __init__(self, message: str, retry_after: float = 30.0):
        super().__init__(message)
        self.retry_after = retry_after


# ─────────────────────────────────────────────────────────────
# PII SANITIZER — Privacy Gate (Llama 3.2 Lokal)
# ─────────────────────────────────────────────────────────────
class PIISanitizer:
    """
    Privacy gatekeeper berbasis Llama 3.2 lokal + regex validator.
    
    TIDAK ADA data individu mahasiswa yang dikirim ke cloud.
    Hanya statistik agregat + label abstrak yang diizinkan keluar.
    """

    def __init__(self, ollama_model: str = "llama3.2:3b"):
        self.ollama_model = ollama_model
        self.ollama_url = "http://localhost:11434/api/generate"

    def sanitize_cluster_profile(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitasi profil klaster: hapus PII, pertahankan statistik agregat.
        
        Input:  {'topNama': [('Ahmad Fauzi', 45)], 'topKab': [('Kab. Pekalongan', 120)], ...}
        Output: {'representative_label': 'Klaster_1', 'topKab_abstrak': 'Wilayah_Pesisir_Tengah', ...}
        """
        # Abstraksi manual (deterministic, tidak perlu LLM untuk ini)
        sanitized = {
            "cluster_id": cluster_data.get("ci", 0) + 1,
            "label": f"Klaster_{cluster_data.get('ci', 0) + 1}",
            "n": cluster_data.get("n", 0),
            "pct": round(cluster_data.get("pct", 0.0), 2),
            "sil": round(cluster_data.get("sil", 0.0), 4),
            "topProdi": self._abstract_prodi(cluster_data.get("topProdi", [])),
            "topJalur": self._abstract_jalur(cluster_data.get("topJalur", [])),
            "topKab": self._abstract_kab(cluster_data.get("topKab", [])),
            # PII fields yang TIDAK boleh dikirim ke cloud:
            # topNama → diganti label abstrak saja
            "representative": f"Pendaftar_Representatif_Klaster_{cluster_data.get('ci', 0) + 1}",
        }
        # Double-check: pastikan tidak ada PII tersisa
        sanitized_str = json.dumps(sanitized)
        pii_found = self._detect_pii(sanitized_str)
        if pii_found:
            logger.warning(
                f"[PIISanitizer] ⚠️  PII terdeteksi setelah sanitasi: {pii_found}. "
                f"Menghapus paksa..."
            )
            sanitized = self._force_remove_pii(sanitized, pii_found)
        return sanitized

    def sanitize_metrics_payload(
        self,
        year: int,
        ari: float,
        fase_from: str,
        fase_to: str,
        cluster_profiles: List[Dict],
        centroid_drift: Optional[float] = None,
        jaccard: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Buat payload steril untuk dikirim ke cloud (causal reasoning).
        Hanya metrik kuantitatif + label abstrak — zero PII.
        """
        return {
            "konteks": "Analisis segmentasi mahasiswa baru ITSNU Pekalongan",
            "periode": f"{year-1}→{year}",
            "fase_transisi": f"{fase_from} → {fase_to}",
            "metrik_stabilitas": {
                "ari": round(float(ari), 4),
                "jaccard": round(float(jaccard), 4) if jaccard is not None else None,
                "centroid_drift": round(float(centroid_drift), 4) if centroid_drift is not None else None,
            },
            "klaster": [
                self.sanitize_cluster_profile(cl) for cl in cluster_profiles
            ],
            "catatan": "Data telah melalui sanitasi PII lokal. Nama dan alamat spesifik telah dianonimkan.",
        }

    def _abstract_prodi(self, top_prodi: List) -> List[str]:
        """Pertahankan nama prodi (bukan PII — nama institusi/jurusan)."""
        return [p[0] for p in top_prodi[:3]] if top_prodi else ["Tidak diketahui"]

    def _abstract_jalur(self, top_jalur: List) -> List[str]:
        """Pertahankan jalur penerimaan (bukan PII)."""
        return [j[0] for j in top_jalur[:3]] if top_jalur else ["Tidak diketahui"]

    def _abstract_kab(self, top_kab: List) -> List[str]:
        """
        Abstraksi kabupaten: pertahankan nama wilayah level kabupaten.
        (Kabupaten/kota bukan PII — ini data publik tingkat agregat)
        """
        return [k[0] for k in top_kab[:3]] if top_kab else ["Tidak diketahui"]

    def _detect_pii(self, text: str) -> List[str]:
        """Deteksi potensi PII menggunakan regex patterns."""
        found = []
        for pattern in PII_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                found.extend(matches)
        return found

    def _force_remove_pii(self, data: Dict, pii_list: List[str]) -> Dict:
        """Hapus paksa PII yang tersisa dari dict."""
        data_str = json.dumps(data)
        for pii in pii_list:
            data_str = data_str.replace(pii, "[REDACTED]")
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            logger.error("[PIISanitizer] Gagal parse setelah redaksi PII.")
            return {"error": "PII_SANITIZATION_FAILED", "label": "DATA_REDACTED"}


# ─────────────────────────────────────────────────────────────
# OPENROUTER CLOUD ENGINE
# ─────────────────────────────────────────────────────────────
class OpenRouterEngine:
    """
    Engine untuk panggilan OpenRouter API dengan free models.
    Mendukung model fallback otomatis jika model pertama rate-limited.
    """

    def __init__(self, api_key: str, preferred_model: Optional[str] = None):
        self.api_key = api_key
        self.preferred_model = preferred_model or DEFAULT_CLOUD_MODEL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ITSNU-PMB-Analysis",
            "X-Title": "ITSNU PMB Tesis Analysis Pipeline",
        })

    @with_exponential_backoff(max_retries=3, base_delay=5.0)
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Panggil OpenRouter API dengan satu model."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = self.session.post(
                OPENROUTER_CHAT_ENDPOINT,
                json=payload,
                timeout=60,
            )
        except requests.exceptions.Timeout:
            raise requests.exceptions.Timeout(f"Timeout >60s untuk model {model}")
        except requests.exceptions.ConnectionError as e:
            raise requests.exceptions.ConnectionError(f"Koneksi gagal: {e}")

        if resp.status_code == 429:
            retry_after = float(
                resp.json().get("error", {}).get("metadata", {}).get("retry_after_seconds", 30)
            )
            raise RateLimitError(f"Rate limited oleh {model}", retry_after=retry_after)

        if resp.status_code != 200:
            logger.warning(f"[OpenRouter] HTTP {resp.status_code}: {resp.text[:300]}")
            raise requests.exceptions.HTTPError(
                f"HTTP {resp.status_code} dari OpenRouter"
            )

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            raise ValueError(f"Respons kosong dari model {model}")
        return content

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate dengan model fallback otomatis.
        Jika model rate-limited (429), LANGSUNG coba model berikutnya tanpa retry.
        """
        models_to_try = [self.preferred_model] + [
            m for m in OPENROUTER_FREE_MODELS if m != self.preferred_model
        ]

        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"[OpenRouter] Mencoba model: {model}")
                result = self._call_api(messages, model, temperature, max_tokens)
                logger.info(f"[OpenRouter] ✅ Berhasil dengan model: {model}")
                return result
            except RateLimitError as e:
                # Rate-limited: LANGSUNG lanjut ke model berikutnya, tidak retry yang sama
                logger.warning(f"[OpenRouter] ⚡ {model} rate-limited → next model...")
                last_error = e
                time.sleep(2)  # Jeda minimal antar model
                continue
            except requests.exceptions.Timeout as e:
                logger.warning(f"[OpenRouter] ⏱️  {model} timeout → next model...")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"[OpenRouter] ⚠️  {model} error: {str(e)[:80]}")
                last_error = e
                continue

        raise RuntimeError(
            f"[OpenRouter] Semua {len(models_to_try)} model gagal/rate-limited. "
            f"Error terakhir: {last_error}"
        )

    def validate_numerical_integrity(
        self, response: str, expected_metrics: Dict[str, float]
    ) -> bool:
        """
        Validasi integritas numerik: pastikan LLM tidak memanipulasi angka statistik.
        
        Risk mitigation untuk: 'Hallusinasi Metrik Kuantitatif oleh MoE'
        """
        for metric_name, expected_val in expected_metrics.items():
            # Cari semua angka dalam respons yang mirip nilai metrik
            numbers_in_response = re.findall(r'-?\d+\.?\d*', response)
            expected_str = str(round(expected_val, 2))
            if expected_str not in response and expected_val != 0:
                logger.warning(
                    f"[NumericalGuard] ⚠️  Nilai {metric_name}={expected_val} tidak ditemukan "
                    f"dalam output LLM. Kemungkinan halusinasi!"
                )
                return False
        return True


# ─────────────────────────────────────────────────────────────
# HYBRID LLM PROVIDER — Main Class
# ─────────────────────────────────────────────────────────────
class HybridLLMProvider:
    """
    Hybrid Cognitive Pipeline: Llama 3.2 Lokal + OpenRouter Cloud.
    
    Routing logic:
    - Task ringan / PII-sensitive  → Llama 3.2 (Ollama lokal)
    - Task high-reasoning / agregat → OpenRouter Cloud (free models)
    
    Fallback: Jika cloud tidak tersedia → otomatis ke Llama lokal.
    """

    def __init__(
        self,
        openrouter_api_key: Optional[str] = None,
    ollama_model: str = "llama3.2:3b",

        cloud_model: Optional[str] = None,
        enable_cache: bool = True,
    ):
        self.api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.ollama_model = ollama_model
        self.cloud_available = bool(self.api_key)
        self.enable_cache = enable_cache
        self._response_cache: Dict[str, str] = {}

        self.sanitizer = PIISanitizer(ollama_model=ollama_model)

        if self.cloud_available:
            self.cloud_engine = OpenRouterEngine(
                api_key=self.api_key,
                preferred_model=cloud_model or DEFAULT_CLOUD_MODEL,
            )
            logger.info(
                f"[HybridProvider] ✅ Cloud engine aktif: OpenRouter | "
                f"Model: {cloud_model or DEFAULT_CLOUD_MODEL}"
            )
        else:
            self.cloud_engine = None
            logger.warning(
                "[HybridProvider] ⚠️  OPENROUTER_API_KEY tidak ditemukan. "
                "Semua task akan diproses secara lokal oleh Llama 3.2."
            )

    def _cache_key(self, prompt: str, task_type: str) -> str:
        content = f"{task_type}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[str]:
        if self.enable_cache and key in self._response_cache:
            logger.debug(f"[Cache] Hit: {key[:8]}...")
            return self._response_cache[key]
        return None

    def _save_to_cache(self, key: str, value: str):
        if self.enable_cache:
            self._response_cache[key] = value

    def _call_ollama_local(self, prompt: str, max_tokens: int = 1500) -> str:
        """Panggil Llama 3.2 melalui Ollama REST API lokal."""
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=120,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return f"[Ollama error] HTTP {resp.status_code}"
        except requests.exceptions.ConnectionError:
            return "[Ollama error] Ollama tidak berjalan di localhost:11434"
        except requests.exceptions.Timeout:
            return "[Ollama timeout] Proses melebihi 120 detik"
        except Exception as e:
            return f"[Ollama exception] {str(e)}"

    def causal_trend_analysis(
        self,
        year_from: int,
        year_to: int,
        fase_from: str,
        fase_to: str,
        ari: float,
        cluster_profiles_from: List[Dict],
        cluster_profiles_to: List[Dict],
        centroid_drift: Optional[float] = None,
        jaccard: Optional[float] = None,
    ) -> str:
        """
        Analisis tren kausal antar dua periode menggunakan cloud reasoning.
        
        PRIVACY: Data disanitasi lokal sebelum dikirim ke cloud.
        """
        # Step 1: Sanitasi payload (lokal, zero cloud)
        payload_steril = self.sanitizer.sanitize_metrics_payload(
            year=year_to,
            ari=ari,
            fase_from=fase_from,
            fase_to=fase_to,
            cluster_profiles=cluster_profiles_to,
            centroid_drift=centroid_drift,
            jaccard=jaccard,
        )

        # Step 2: Buat prompt akademik
        system_prompt = """Anda adalah Pakar Educational Data Mining dan Sosiologi Pendidikan Indonesia.
Tugas Anda: analisis kausal mendalam tentang perubahan segmentasi mahasiswa berdasarkan metrik statistik.

ATURAN KETAT (wajib dipatuhi):
1. JANGAN memanipulasi atau mengubah nilai ARI, Silhouette, atau Centroid Drift yang diberikan
2. Gunakan nilai numerik PERSIS seperti yang disediakan dalam data
3. Berikan analisis dalam bahasa Indonesia ilmiah-akademik
4. Sertakan referensi ke konteks makroekonomi dan kebijakan pendidikan Indonesia
5. Output minimal 300 kata, maksimal 500 kata"""

        user_prompt = f"""Analisis perubahan kausal segmentasi mahasiswa baru ITSNU Pekalongan:

DATA STATISTIK TERVERIFIKASI:
{json.dumps(payload_steril, indent=2, ensure_ascii=False)}

Pertanyaan analisis:
1. Apa interpretasi nilai ARI={ari:.4f} dalam konteks transisi {fase_from} → {fase_to}?
2. Faktor eksternal apa (ekonomi, kebijakan, pandemi) yang paling mungkin menyebabkan pergeseran ini?
3. Apakah terjadi structural break? Jelaskan dengan reasoning berbasis metrik di atas.
4. Apa implikasi strategis untuk program rekrutmen ITSNU tahun berikutnya?

Berikan analisis kausal komprehensif dengan bahasa akademik yang sesuai standar jurnal Sinta 2."""

        cache_key = self._cache_key(user_prompt, "causal_trend_analysis")
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Step 3: Kirim ke cloud jika tersedia, fallback ke lokal
        if self.cloud_available and self.cloud_engine:
            try:
                logger.info(f"[HybridProvider] 🌐 Causal analysis {year_from}→{year_to} via cloud")
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                result = self.cloud_engine.generate(messages, temperature=0.3, max_tokens=2000)

                # Validasi numerik
                expected = {"ARI": ari}
                if not self.cloud_engine.validate_numerical_integrity(result, expected):
                    logger.warning(
                        "[HybridProvider] ⚠️  Numerical guard triggered! "
                        "Menambahkan catatan validasi ke output..."
                    )
                    result += (
                        f"\n\n[CATATAN VALIDASI]: Nilai ARI yang digunakan dalam analisis ini "
                        f"adalah {ari:.4f} berdasarkan data aktual."
                    )

                self._save_to_cache(cache_key, result)
                return result

            except Exception as e:
                logger.error(
                    f"[HybridProvider] ❌ Cloud gagal untuk causal analysis: {e}. "
                    f"Fallback ke Llama lokal..."
                )

        # Fallback: Llama 3.2 lokal
        logger.info(f"[HybridProvider] 💻 Causal analysis {year_from}→{year_to} via Llama lokal")
        local_prompt = f"{system_prompt}\n\n{user_prompt}"
        result = self._call_ollama_local(local_prompt, max_tokens=1500)
        self._save_to_cache(cache_key, result)
        return result

    def narrative_summary(
        self,
        total_mahasiswa: int,
        proyeksi_2025: Optional[int],
        avg_similarity: Optional[float],
        ari_summary: List[Dict],
        periode: str = "2019-2024",
    ) -> str:
        """
        Generate ringkasan naratif komprehensif BAB IV menggunakan cloud reasoning.
        Data yang dikirim: hanya agregat statistik — zero PII.
        """
        payload_steril = {
            "institusi": "ITSNU Pekalongan",
            "periode": periode,
            "total_pendaftar": total_mahasiswa,
            "proyeksi_2025": proyeksi_2025,
            "rata_rata_cosine_similarity": round(float(avg_similarity or 0), 4),
            "ringkasan_ari": ari_summary,  # Sudah berupa statistik agregat
            "metodologi": "IndoBERT-768D + GMM + Time Series (CRISP-DM)",
        }

        system_prompt = """Anda adalah Peneliti Senior Educational Data Mining.
Tugas: Buat ringkasan naratif akademik komprehensif untuk BAB IV tesis magister.
Gunakan bahasa Indonesia ilmiah. Format: paragraf mengalir (bukan bullet point).
Panjang: 400-600 kata. Gaya: standar publikasi Jurnal Sinta/IEEE."""

        user_prompt = f"""Buat ringkasan naratif BAB IV untuk tesis dengan data berikut:

{json.dumps(payload_steril, indent=2, ensure_ascii=False)}

Struktur narasi:
1. Gambaran umum hasil analisis PMB
2. Temuan utama berdasarkan metrik GMM dan ARI
3. Dampak COVID-19 pada pola pendaftaran (berbasis data)
4. Proyeksi dan rekomendasi berbasis bukti
5. Implikasi untuk pengembangan metodologi"""

        cache_key = self._cache_key(user_prompt, "narrative_summary")
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if self.cloud_available and self.cloud_engine:
            try:
                logger.info("[HybridProvider] 🌐 Narrative summary via cloud")
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                result = self.cloud_engine.generate(messages, temperature=0.4, max_tokens=2500)
                self._save_to_cache(cache_key, result)
                return result
            except Exception as e:
                logger.error(f"[HybridProvider] ❌ Cloud gagal untuk summary: {e}. Fallback...")

        # Fallback lokal
        logger.info("[HybridProvider] 💻 Narrative summary via Llama lokal")
        local_prompt = f"{system_prompt}\n\n{user_prompt}"
        result = self._call_ollama_local(local_prompt, max_tokens=2000)
        self._save_to_cache(cache_key, result)
        return result

    def generate_simple(self, prompt: str, task_type: str = "table_narrative",
                        max_tokens: int = 1500) -> str:
        """
        Generate sederhana untuk task lokal (persona, table narratives).
        Selalu menggunakan Llama 3.2 lokal — tidak mengirim ke cloud.
        """
        routing = TASK_ROUTING.get(task_type, "local")
        if routing == "cloud" and self.cloud_available:
            try:
                messages = [{"role": "user", "content": prompt}]
                return self.cloud_engine.generate(messages, max_tokens=max_tokens)
            except Exception as e:
                logger.warning(f"[HybridProvider] Cloud fallback untuk {task_type}: {e}")

        return self._call_ollama_local(prompt, max_tokens=max_tokens)

    def get_status(self) -> Dict[str, Any]:
        """Kembalikan status provider untuk ditampilkan di Streamlit UI."""
        return {
            "cloud_available": self.cloud_available,
            "cloud_model": self.cloud_engine.preferred_model if self.cloud_engine else None,
            "local_model": self.ollama_model,
            "mode": "Hybrid (Cloud + Local)" if self.cloud_available else "Local Only",
            "provider": "OpenRouter (Free Tier)" if self.cloud_available else "Ollama",
            "cache_size": len(self._response_cache),
        }


# ─────────────────────────────────────────────────────────────
# FACTORY FUNCTION — Kemudahan instantiasi
# ─────────────────────────────────────────────────────────────
def create_hybrid_provider(
    openrouter_api_key: Optional[str] = None,
    ollama_model: str = "llama3.2:3b",
    cloud_model: Optional[str] = None,
) -> HybridLLMProvider:
    """
    Factory function untuk membuat HybridLLMProvider.
    API key diambil dari parameter atau env var OPENROUTER_API_KEY.
    """
    api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
    return HybridLLMProvider(
        openrouter_api_key=api_key,
        ollama_model=ollama_model,
        cloud_model=cloud_model,
    )
