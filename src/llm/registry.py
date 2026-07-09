"""
Provider registry — single source for provider metadata.

Model lists are centralized in src/config.py to avoid duplication.
"""


PROVIDER_REGISTRY = {
    "Ollama": {"key": "ollama", "label": "Ollama (local)", "type": "local"},
    "OpenRouter": {"key": "openrouter", "label": "OpenRouter (Free Cloud)", "type": "cloud",
                   "endpoint": "https://openrouter.ai/api/v1/chat/completions"},
    "Gemini": {"key": "gemini", "label": "Gemini CLI", "type": "cli"},
    "Kilo": {"key": "kilo", "label": "Kilo CLI", "type": "cli"},
    "OpenCode": {"key": "opencode", "label": "OpenCode CLI", "type": "cli"},
}

PROVIDER_NAMES = list(PROVIDER_REGISTRY.keys())

OLLAMA_MODELS = ["llama3.2:3b", "phi3:latest", "deepseek-r1:1.5b", "qwen2.5-coder:1.5b"]
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


def get_provider_key(name: str) -> str:
    return PROVIDER_REGISTRY.get(name, {}).get("key", name.lower())


def get_provider_label(name: str) -> str:
    return PROVIDER_REGISTRY.get(name, {}).get("label", name)


def get_provider_names() -> list:
    return list(PROVIDER_REGISTRY.keys())
