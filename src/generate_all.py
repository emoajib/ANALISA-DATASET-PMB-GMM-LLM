#!/usr/bin/env python3
"""
Pre-generate all artifacts for demo sidang.
Runs full pipeline, generates comparison personas, and verifies outputs.
Usage: python generate_all.py
"""
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pmb_pipeline import PMBAnalysisPipeline, flush_embedding_cache
from comparison import run_comparison
from providers import PROVIDER_NAMES

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
DATA_FILE = BASE_DIR / "data" / "DATASET PMB ITSNUPKL2019-2024_FIX.xlsx"

def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    logger.info("=" * 60)
    logger.info("PRE-GENERATE ALL ARTIFACTS FOR DEMO SIDANG")
    logger.info("=" * 60)

    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)

    logger.info("Initializing pipeline with Ollama...")
    pipeline = PMBAnalysisPipeline(str(DATA_FILE), llm_provider="Ollama")

    steps = [
        "business_understanding",
        "data_collection",
        "data_understanding",
        "data_preparation",
        "dimensionality_reduction",
        "modeling",
        "time_series_analysis",
        "evaluation",
        "otomasi_llm",
        "causal_trend_analysis",
        "narrative_summary",
        "deployment",
    ]

    for i, step in enumerate(steps, 1):
        logger.info(f"Step {i}/{len(steps)}: {step}...")
        try:
            method = getattr(pipeline, step)
            method()
            logger.info(f"  ✓ {step} completed")
        except Exception as e:
            logger.error(f"  ✗ {step} failed: {e}")
            sys.exit(1)

    flush_embedding_cache()

    # Generate comparison artifacts
    logger.info("=" * 60)
    logger.info("GENERATING COMPARISON ARTIFACTS")
    logger.info("=" * 60)
    try:
        results = run_comparison(pipeline, PROVIDER_NAMES)
        for provider, r in results.items():
            status = r.get("status", "missing")
            personas = r.get("personas", {})
            total = sum(len(v) for v in personas.values()) if personas else 0
            elapsed = r.get("metadata", {}).get("elapsed_seconds", "-")
            logger.info(f"  {provider:12s} | {status:10s} | {total:3d} personas | {elapsed:>8s}s")
        errors = [p for p in PROVIDER_NAMES if results.get(p, {}).get("status") == "error"]
        if errors:
            logger.warning(f"Providers with errors: {errors}")
        else:
            logger.info("  ✓ All providers completed successfully")
    except Exception as e:
        logger.error(f"Comparison generation failed: {e}")

    # Verify outputs
    logger.info("=" * 60)
    logger.info("VERIFICATION")
    logger.info("=" * 60)

    csv_files = list(OUTPUTS_DIR.glob("*.csv"))
    png_files = list(OUTPUTS_DIR.glob("*.png"))
    svg_files = list(OUTPUTS_DIR.glob("*.svg"))

    logger.info(f"CSV files: {len(csv_files)}")
    logger.info(f"PNG files: {len(png_files)}")
    logger.info(f"SVG files: {len(svg_files)}")
    logger.info(f"Total artifacts: {len(csv_files) + len(png_files) + len(svg_files)}")

    key_files = [
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
        "gambar_4_2b_scatter_2020.png",
        "gambar_4_2c_scatter_2021.png",
        "gambar_4_2d_scatter_2022.png",
        "gambar_4_2e_scatter_2023.png",
        "gambar_4_2f_scatter_2024.png",
        "gambar_4_3a_silhouette.png",
        "gambar_4_3c_ari.png",
        "gambar_4_5_proyeksi.png",
    ]

    missing = []
    for f in key_files:
        if not (OUTPUTS_DIR / f).exists():
            missing.append(f)

    if missing:
        logger.error(f"Missing {len(missing)} key files:")
        for f in missing:
            logger.error(f"  - {f}")
        sys.exit(1)

    # Check comparison artifacts
    from comparison import COMPARISON_DIR
    from providers import PROVIDER_KEYS
    comparison_ok = True
    for pk in PROVIDER_KEYS:
        persona_file = COMPARISON_DIR / pk / "personas.json"
        if persona_file.exists():
            import json
            with open(persona_file) as f:
                data = json.load(f)
            total = sum(len(v) for v in data.get("personas", {}).values())
            logger.info(f"  Comparison {pk}: OK ({total} personas)")
        else:
            logger.warning(f"  Comparison {pk}: MISSING")
            comparison_ok = False

    logger.info("=" * 60)
    if not missing and comparison_ok:
        logger.info("✓ ALL ARTIFACTS GENERATED SUCCESSFULLY")
    else:
        logger.warning("Some artifacts are missing (see above)")
    logger.info(f"Output directory: {OUTPUTS_DIR}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
