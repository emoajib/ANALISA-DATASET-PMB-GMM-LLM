#!/usr/bin/env python3
"""
Verify demo readiness: checks all outputs exist, caches valid, LLM responds.
Usage: python verify_demo.py
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from providers import PROVIDER_KEYS

BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
CACHE_DIR = BASE_DIR / "src" / "steps" / "data"

def check_outputs():
    required = [
        "tabel_4_1_distribusi.csv",
        "tabel_4_2_prodi.csv",
        "tabel_4_3_preprocessing.csv",
        "tabel_4_4_cosine_similarity.csv",
        "tabel_4_5_kscan.csv",
        "tabel_4_6_ari.csv",
        "tabel_4_7_evaluasi_internal.csv",
        "tabel_4_15_lifecycle.csv",
        "tabel_4_16_prioritasi_2025.csv",
        "tabel_4_17_rekomendasi_channel.csv",
        "tabel_4_18_perbandingan.csv",
        "gambar_4_1_distribusi.png",
        "gambar_4_2a_scatter_2019.png",
        "gambar_4_3a_silhouette.png",
        "gambar_4_3c_ari.png",
        "gambar_4_5_proyeksi.png",
    ]
    
    missing = []
    for f in required:
        if not (OUTPUTS_DIR / f).exists():
            missing.append(f)
    
    return missing

def check_caches():
    caches = {
        "embedding": CACHE_DIR / "embedding_cache.json",
        "llm": BASE_DIR / "data" / "llm_cache.json",
    }
    
    status = {}
    for name, path in caches.items():
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                status[name] = f"OK ({len(data)} entries)"
            except Exception as e:
                status[name] = f"CORRUPTED: {e}"
        else:
            status[name] = "MISSING"
    
    return status

def check_llm():
    try:
        from llm_provider import generate
        result = generate("Test", provider="Ollama", max_tokens=10)
        if result and not result.startswith("[") and not result.startswith("Error"):
            return "OK"
        return f"FAILED: {result[:100]}"
    except Exception as e:
        return f"ERROR: {e}"

def check_comparison():
    comparison_dir = BASE_DIR / "outputs" / "comparison"
    providers = PROVIDER_KEYS
    status = {}
    for provider in providers:
        persona_file = comparison_dir / provider / "personas.json"
        if persona_file.exists():
            try:
                with open(persona_file, 'r') as f:
                    data = json.load(f)
                personas = data.get("personas", {})
                total = sum(len(v) for v in personas.values())
                status[provider] = f"OK ({total} personas)"
            except Exception as e:
                status[provider] = f"CORRUPTED: {e}"
        else:
            status[provider] = "MISSING"
    return status

def main():
    print("=" * 60)
    print("DEMO READINESS CHECK")
    print("=" * 60)
    
    # Check outputs
    print("\n[1] Checking output files...")
    missing = check_outputs()
    if missing:
        print(f"  ✗ Missing {len(missing)} files:")
        for f in missing:
            print(f"    - {f}")
    else:
        print(f"  ✓ All {16} required files present")
    
    # Check caches
    print("\n[2] Checking caches...")
    caches = check_caches()
    for name, status in caches.items():
        print(f"  {name}: {status}")
    
    # Check comparison
    print("\n[3] Checking comparison artifacts...")
    comparison = check_comparison()
    for provider, status in comparison.items():
        print(f"  {provider}: {status}")
    
    # Check LLM
    print("\n[4] Checking LLM provider...")
    llm_status = check_llm()
    print(f"  Ollama: {llm_status}")
    
    # Summary
    print("\n" + "=" * 60)
    comparison_ok = all("OK" in v for v in comparison.values())
    if not missing and "OK" in llm_status and comparison_ok:
        print("✓ DEMO READY - All checks passed")
        return 0
    else:
        print("✗ DEMO NOT READY - Fix issues above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
