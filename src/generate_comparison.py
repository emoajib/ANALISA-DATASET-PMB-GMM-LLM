#!/usr/bin/env python3
"""
Pre-generate persona comparison for all providers.
Runs persona generation for Ollama, Gemini, Kilo, OpenCode.
Usage: python generate_comparison.py
"""
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pmb_pipeline import PMBAnalysisPipeline
from comparison import run_comparison
from providers import PROVIDER_NAMES as PROVIDERS

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "DATASET PMB ITSNUPKL2019-2024_FIX.xlsx"

def main():
    logger.info("=" * 60)
    logger.info("PRE-GENERATE PERSONA COMPARISON")
    logger.info(f"Providers: {PROVIDERS}")
    logger.info("=" * 60)
    
    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)
    
    # Initialize pipeline (steps 1-8 only, we only need personas)
    logger.info("Initializing pipeline...")
    pipeline = PMBAnalysisPipeline(str(DATA_FILE), llm_provider="Ollama", llm_model="llama3.2:latest")
    
    steps = [
        "business_understanding",
        "data_collection",
        "data_understanding",
        "data_preparation",
        "dimensionality_reduction",
        "modeling",
        "time_series_analysis",
        "evaluation",
    ]
    for step in steps:
        logger.info(f"Running {step}...")
        getattr(pipeline, step)()
    
    # Run comparison for all providers
    logger.info("=" * 60)
    logger.info("RUNNING PERSONA COMPARISON")
    logger.info("=" * 60)
    
    results = run_comparison(pipeline, PROVIDERS)
    
    # Print summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    for provider in PROVIDERS:
        r = results.get(provider, {})
        status = r.get("status", "missing")
        personas = r.get("personas", {})
        metadata = r.get("metadata", {})
        total = sum(len(v) for v in personas.values()) if personas else 0
        elapsed = metadata.get("elapsed_seconds", "-")
        logger.info(f"{provider:12s} | {status:10s} | {total:3d} personas | {elapsed:>8s}s")
    
    # Check for errors
    errors = [p for p in PROVIDERS if results.get(p, {}).get("status") == "error"]
    if errors:
        logger.warning(f"Providers with errors: {errors}")
    
    logger.info("=" * 60)
    logger.info("Output directory: outputs/comparison/")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
