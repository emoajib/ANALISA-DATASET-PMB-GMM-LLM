PROVIDER_REGISTRY = {
    "Ollama": {"key": "ollama", "label": "Ollama (local)", "type": "local"},
    "Gemini": {"key": "gemini", "label": "Gemini CLI", "type": "cli"},
    "Kilo": {"key": "kilo", "label": "Kilo CLI", "type": "cli"},
    "OpenCode": {"key": "opencode", "label": "OpenCode CLI", "type": "cli"},
}

PROVIDER_NAMES = list(PROVIDER_REGISTRY.keys())
PROVIDER_KEYS = [v["key"] for v in PROVIDER_REGISTRY.values()]

def get_provider_key(name):
    return PROVIDER_REGISTRY.get(name, {}).get("key", name.lower())

def get_provider_label(name):
    return PROVIDER_REGISTRY.get(name, {}).get("label", name)

OLLAMA_MODELS = [
    "llama3.2:latest",
    "phi3:latest",
    "deepseek-r1:1.5b",
    "qwen2.5-coder:1.5b",
]

DEFAULT_OLLAMA_MODEL = "llama3.2:latest"

def get_provider_names():
    return list(PROVIDER_REGISTRY.keys())
