import json
import os
import time
import hashlib
import concurrent.futures
from pathlib import Path

from providers import PROVIDER_REGISTRY, get_provider_names

BASE_DIR = Path(__file__).parent.parent
COMPARISON_DIR = BASE_DIR / "outputs" / "comparison"

PROVIDERS = get_provider_names()
COMPARISON_CACHE_VERSION = "1.0"

def get_provider_dir(provider):
    return COMPARISON_DIR / provider.lower()

def _get_dataset_hash(pipeline):
    if hasattr(pipeline, 'file_path') and pipeline.file_path:
        try:
            with open(pipeline.file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:16]
        except Exception:
            pass
    return "unknown"

def save_personas(provider, personas, metadata=None):
    provider_dir = get_provider_dir(provider)
    provider_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "version": COMPARISON_CACHE_VERSION,
        "personas": personas,
        "metadata": metadata or {},
        "generated_at": time.time(),
    }
    tmp = provider_dir / "personas.json.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, provider_dir / "personas.json")

def load_personas(provider, dataset_hash=None):
    path = get_provider_dir(provider) / "personas.json"
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if data.get("version") != COMPARISON_CACHE_VERSION:
            print(f"Cache version mismatch for {provider}, regenerating")
            return None
        if dataset_hash and data.get("metadata", {}).get("dataset_hash") != dataset_hash:
            print(f"Dataset changed for {provider}, regenerating cache")
            return None
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"Cache file corrupted for {provider}: {e}, will regenerate")
        return None
    except Exception as e:
        print(f"Unexpected error loading personas for {provider}: {e}")
        return None

def _run_one_provider(pipeline, provider, dataset_hash):
    cached = load_personas(provider, dataset_hash)
    if cached:
        return provider, {
            "status": "cached",
            "personas": cached.get("personas", {}),
            "metadata": cached.get("metadata", {}),
        }
    try:
        start = time.time()
        personas = pipeline.generate_personas_only(provider)
        elapsed = time.time() - start
        total = sum(len(v) for v in personas.values()) if personas else 0
        metadata = {
            "elapsed_seconds": round(elapsed, 2),
            "total_personas": total,
            "years": sorted(personas.keys()) if personas else [],
            "dataset_hash": dataset_hash or "unknown",
        }
        save_personas(provider, personas, metadata)
        return provider, {
            "status": "generated",
            "personas": personas,
            "metadata": metadata,
        }
    except Exception as e:
        return provider, {
            "status": "error",
            "error": str(e),
            "personas": {},
            "metadata": {},
        }

def run_comparison(pipeline, providers=None):
    if providers is None:
        providers = PROVIDERS
    dataset_hash = _get_dataset_hash(pipeline)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(providers), 4)) as executor:
        futures = {
            executor.submit(_run_one_provider, pipeline, p, dataset_hash): p
            for p in providers
        }
        for future in concurrent.futures.as_completed(futures):
            provider, result = future.result()
            results[provider] = result
    return results

def clear_comparison(providers=None):
    if providers is None:
        providers = PROVIDERS
    for provider in providers:
        provider_dir = get_provider_dir(provider)
        if provider_dir.exists():
            for f in provider_dir.glob("*"):
                f.unlink()
