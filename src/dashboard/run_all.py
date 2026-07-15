#!/usr/bin/env python3
"""Run the full PMB analysis pipeline, writing outputs to src/outputs (canonical).
Safe driver: backs nothing up (caller did), tolerates LLM-step failures,
verifies Set-A optimality after numeric steps."""
import sys, os, logging
from pathlib import Path

HERE = Path(__file__).resolve().parent          # src/dashboard
sys.path.insert(0, str(HERE))
ROOT = HERE.parent.parent                      # TESIS root
OUT = HERE.parent / "outputs"                     # src/outputs (canonical)
DATA = ROOT / "DATASET" / "DATASET PMB ITSNUPKL2019-2024_FIX.xls"

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
log = logging.getLogger("run_all")

import pmb_pipeline
pmb_pipeline.OUTPUTS_DIR = OUT                        # redirect writes to canonical dir
from pmb_pipeline import PMBAnalysisPipeline, flush_embedding_cache
from comparison import run_comparison
from providers import PROVIDER_NAMES

def main():
    if not DATA.exists():
        log.error("Dataset missing: %s", DATA); sys.exit(1)
    log.info("OUTPUTS_DIR = %s", OUT)
    log.info("DATASET    = %s", DATA)
    pipe = PMBAnalysisPipeline(str(DATA), llm_provider="Ollama")
    steps = ["business_understanding","data_collection","data_understanding",
             "data_preparation","dimensionality_reduction","modeling",
             "time_series_analysis","evaluation","otomasi_llm",
             "causal_trend_analysis","narrative_summary","deployment"]
    for i, s in enumerate(steps, 1):
        try:
            getattr(pipe, s)()
            log.info("  ✓ step %d/%d %s", i, len(steps), s)
        except Exception as e:
            log.error("  ✗ step %d %s failed: %s", i, s, e)
    try:
        flush_embedding_cache()
    except Exception as e:
        log.warning("flush_embedding_cache: %s", e)
    # comparison personas
    try:
        run_comparison(pipe, PROVIDER_NAMES)
        log.info("✓ comparison personas generated")
    except Exception as e:
        log.warning("comparison generation skipped: %s", e)
    # ---- VERIFY Set-A optimality from regenerated kscan ----
    try:
        import pandas as pd
        df = pd.read_csv(OUT / "tabel_4_5_kscan.csv")
        opt = {}
        for y, g in df.groupby("Tahun"):
            g = g.copy(); g["BIC"] = g["BIC"].astype(float)
            opt[int(y)] = int(g.loc[g["BIC"].idxmin()]["K"])
        log.info("VERIFY optimal K per year = %s (expect 2019-2024: 2,3,2,2,5,4)", opt)
        expect = {2019:2,2020:3,2021:2,2022:2,2023:5,2024:4}
        ok = all(opt.get(y)==expect[y] for y in expect)
        log.info("SET-A CHECK: %s", "PASS ✓" if ok else "FAIL ✗ (investigate before trusting docx)")
    except Exception as e:
        log.warning("verify skipped: %s", e)

if __name__ == "__main__":
    main()
