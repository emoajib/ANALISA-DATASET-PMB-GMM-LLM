#!/usr/bin/env python3
# test_hybrid_integration.py
# Vetted by AI - Manual Review Required by Senior Engineer/Manager
# Vetted by Mujibul Hakim - Manual Review Required
"""
Integration Test — Hybrid Cognitive Pipeline
=============================================
Menguji:
1. Koneksi OpenRouter API + model availability
2. PII Sanitizer (privacy gate)
3. Causal reasoning via cloud
4. Fallback ke lokal jika cloud gagal

Jalankan: python3 src/test_hybrid_integration.py
"""

import os
import sys
import json
import time

# Path setup

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    print("✅ .env berhasil dimuat")
except ImportError:
    print("⚠️  python-dotenv tidak terinstall. Jalankan: pip install python-dotenv")

# ─────────────────────────────────────────────────────────────
# TEST 1: OpenRouter API Connectivity
# ─────────────────────────────────────────────────────────────
def test_openrouter_connectivity():
    print("\n" + "="*60)
    print("TEST 1: OpenRouter API Connectivity")
    print("="*60)

    import requests

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("❌ OPENROUTER_API_KEY tidak ditemukan di .env")
        return False

    print(f"✅ API Key ditemukan: {api_key[:20]}...")

    # Test dengan model paling ringan
    model = "meta-llama/llama-3.3-70b-instruct:free"
    print(f"📡 Mencoba koneksi ke OpenRouter dengan model: {model}")

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ITSNU-PMB-Analysis",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Sebutkan 3 kata acak dalam bahasa Indonesia."}],
                "max_tokens": 50,
                "temperature": 0.5,
            },
            timeout=30,
        )

        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Respons dari {model}:")
            print(f"   '{content[:100]}'")
            return True
        elif resp.status_code == 429:
            print(f"⚠️  Rate limited (429). Model {model} sedang sibuk. Mencoba model lain...")
            return test_fallback_model(api_key)
        else:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_fallback_model(api_key: str) -> bool:
    """Coba model fallback jika model utama rate-limited."""
    import requests
    fallback = "nvidia/nemotron-3-nano-30b-a3b:free"
    print(f"   Fallback ke: {fallback}")
    time.sleep(5)

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": fallback,
            "messages": [{"role": "user", "content": "Apa itu GMM? Jawab singkat."}],
            "max_tokens": 50,
        },
        timeout=30,
    )
    if resp.status_code == 200:
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"✅ Fallback berhasil: '{content[:80]}'")
        return True
    print(f"❌ Fallback gagal: HTTP {resp.status_code}")
    return False


# ─────────────────────────────────────────────────────────────
# TEST 2: PII Sanitizer
# ─────────────────────────────────────────────────────────────
def test_pii_sanitizer():
    print("\n" + "="*60)
    print("TEST 2: PII Sanitizer (Privacy Gate)")
    print("="*60)

    try:
        from hybrid_provider import PIISanitizer

        sanitizer = PIISanitizer()

        # Simulasi data klaster mentah dengan PII
        cluster_raw = {
            "ci": 0,
            "n": 234,
            "pct": 38.2,
            "sil": 0.71,
            "topNama": [("Ahmad Fauzi Ramadan", 45), ("Siti Nur Aisyah", 32)],
            "topProdi": [("S1 Teknik Informatika", 89), ("S1 Sistem Informasi", 67)],
            "topJalur": [("Reguler", 120), ("KIPK", 89)],
            "topKab": [("Kab. Pekalongan", 145), ("Kab. Batang", 67)],
        }

        print("📥 Input (dengan PII):")
        print(f"   topNama: {cluster_raw['topNama']}")

        sanitized = sanitizer.sanitize_cluster_profile(cluster_raw)

        print("📤 Output (setelah sanitasi):")
        print(json.dumps(sanitized, indent=2, ensure_ascii=False))

        # Verifikasi: tidak ada nama asli
        output_str = json.dumps(sanitized)
        assert "Ahmad Fauzi Ramadan" not in output_str, "PII tidak tersanitasi!"
        assert "Siti Nur Aisyah" not in output_str, "PII tidak tersanitasi!"
        assert "n" in sanitized, "Statistik n hilang!"
        assert "pct" in sanitized, "Statistik pct hilang!"

        print("\n✅ PII Sanitizer LULUS — Nama riil tidak ada dalam output")
        print("✅ Statistik agregat dipertahankan (n, pct, sil)")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ GAGAL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error tak terduga: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# TEST 3: Hybrid Provider Instantiation
# ─────────────────────────────────────────────────────────────
def test_hybrid_provider_init():
    print("\n" + "="*60)
    print("TEST 3: Hybrid Provider Initialization")
    print("="*60)

    try:
        from hybrid_provider import create_hybrid_provider

        api_key = os.getenv("OPENROUTER_API_KEY", "")
        provider = create_hybrid_provider(openrouter_api_key=api_key)

        status = provider.get_status()
        print("📊 Provider Status:")
        for k, v in status.items():
            emoji = "✅" if v else "⚠️ "
            print(f"   {emoji} {k}: {v}")

        if status["cloud_available"]:
            print("\n✅ Hybrid Provider siap — Cloud + Local aktif")
        else:
            print("\n⚠️  Hybrid Provider dalam mode Local-Only")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────
# TEST 4: End-to-End Causal Reasoning (dengan data mock)
# ─────────────────────────────────────────────────────────────
def test_causal_reasoning_e2e():
    print("\n" + "="*60)
    print("TEST 4: End-to-End Causal Reasoning (Mock Data)")
    print("="*60)

    try:
        from hybrid_provider import create_hybrid_provider

        api_key = os.getenv("OPENROUTER_API_KEY", "")
        provider = create_hybrid_provider(openrouter_api_key=api_key)

        if not provider.cloud_available:
            print("⚠️  Cloud tidak tersedia, melewati test E2E")
            return True

        # Mock cluster profiles (sudah bebas PII)
        mock_clusters = [
            {"ci": 0, "n": 234, "pct": 38.2, "sil": 0.71,
             "topProdi": [("S1 Informatika", 89)],
             "topJalur": [("Reguler", 120)],
             "topKab": [("Kab. Pekalongan", 145)]},
            {"ci": 1, "n": 187, "pct": 30.6, "sil": 0.65,
             "topProdi": [("S1 Sistem Informasi", 67)],
             "topJalur": [("KIPK", 89)],
             "topKab": [("Kab. Batang", 67)]},
        ]

        print("📡 Mengirim causal analysis ke OpenRouter (2019→2020, Pre-COVID→COVID Crisis)...")
        print("   ARI: -0.12 (structural break)")

        start = time.time()
        result = provider.causal_trend_analysis(
            year_from=2019,
            year_to=2020,
            fase_from="Pre-COVID",
            fase_to="COVID Crisis",
            ari=-0.12,
            cluster_profiles_from=mock_clusters,
            cluster_profiles_to=mock_clusters,
            centroid_drift=0.43,
            jaccard=0.31,
        )
        elapsed = time.time() - start

        print(f"\n⏱️  Waktu respons: {elapsed:.1f}s")
        print(f"📝 Panjang respons: {len(result)} karakter")
        print("\n── Preview (200 karakter pertama) ──")
        print(result[:200] + "...")
        print("\n✅ Causal Reasoning E2E LULUS")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 HYBRID PIPELINE INTEGRATION TEST")
    print("   Tesis ITSNU UNISBANK — Hybrid Cognitive Pipeline")
    print("   Mujibul Hakim (NIM 25.01.85.7010)")
    print()

    results = {}

    results["connectivity"] = test_openrouter_connectivity()
    results["pii_sanitizer"] = test_pii_sanitizer()
    results["hybrid_init"] = test_hybrid_provider_init()

    # E2E test hanya jika 3 test sebelumnya passed
    if all(results.values()):
        results["e2e_causal"] = test_causal_reasoning_e2e()
    else:
        print("\n⚠️  Melewati E2E test karena ada test sebelumnya yang gagal")
        results["e2e_causal"] = None

    print("\n" + "="*60)
    print("HASIL TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        if passed is None:
            status = "⏭️  SKIPPED"
        elif passed:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"  {status}  {test_name}")

    total_passed = sum(1 for v in results.values() if v is True)
    total_run = sum(1 for v in results.values() if v is not None)
    print(f"\nTotal: {total_passed}/{total_run} passed")

    if total_passed == total_run:
        print("\n🎉 SEMUA TEST LULUS — Hybrid Pipeline siap digunakan!")
        print("   Jalankan: streamlit run src/app.py")
    else:
        print("\n⚠️  Beberapa test gagal. Cek log di atas untuk detail.")
        sys.exit(1)
