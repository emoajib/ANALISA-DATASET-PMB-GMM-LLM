import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pmb_pipeline import PMBAnalysisPipeline

p = PMBAnalysisPipeline("dummy.xlsx", llm_provider="Ollama")
try:
    p.generate_personas_only()
    print("FAIL: should have raised RuntimeError")
    sys.exit(1)
except RuntimeError as e:
    if "by_year" in str(e):
        print(f"State guard OK: {e}")
    else:
        print(f"FAIL: unexpected message: {e}")
        sys.exit(1)
except AttributeError:
    print("State guard OK (no by_year attribute)")

print("State guard test PASSED")
