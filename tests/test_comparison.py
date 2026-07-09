import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from comparison import (
    PROVIDERS, get_provider_dir, save_personas, load_personas,
    clear_comparison, COMPARISON_CACHE_VERSION
)

td = {"2019": [{"cluster": 1, "persona": "A"}]}
tm = {"elapsed_seconds": 1.5, "total_personas": 1, "years": ["2019"]}

# Test 1: save/load roundtrip
save_personas("Ollama", td, tm)
d = load_personas("Ollama")
assert d is not None, "load_personas returned None"
assert d["version"] == COMPARISON_CACHE_VERSION, f"version mismatch"
assert d["personas"] == td, "personas mismatch"
print("Test 1 save/load roundtrip: PASS")

# Test 2: cache invalidation by dataset_hash
stale = load_personas("Ollama", dataset_hash="WRONG_HASH")
assert stale is None, "stale hash should return None"
valid = load_personas("Ollama", dataset_hash=tm.get("dataset_hash"))
assert valid is not None, "valid hash should return data"
print("Test 2 cache invalidation: PASS")

# Test 3: corrupted cache file
open(get_provider_dir("Ollama") / "personas.json", "w").write("{corrupted")
corrupt = load_personas("Ollama")
assert corrupt is None, "corrupted file should return None"
print("Test 3 corrupted cache: PASS")

# Test 4: clear_comparison
save_personas("Ollama", td, {})
save_personas("Gemini", td, {})
clear_comparison()
assert not (get_provider_dir("Ollama") / "personas.json").exists()
assert not (get_provider_dir("Gemini") / "personas.json").exists()
print("Test 4 clear_comparison: PASS")

# Test 5: provider directory structure
for p in PROVIDERS:
    d = get_provider_dir(p)
    assert "outputs/comparison" in str(d), f"bad path for {p}"
    assert d.name == p.lower(), f"bad dir name for {p}"
print(f"Test 5 provider dirs: PASS ({len(PROVIDERS)} providers)")

print()
print("All 5 comparison tests PASSED")
