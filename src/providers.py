# Vetted by AI - Manual Review Required by Senior Engineer/Manager
PROVIDER_REGISTRY = {
    "Ollama": {"key": "ollama", "label": "Ollama (local)", "type": "local"},
    "OpenRouter": {"key": "openrouter", "label": "OpenRouter (Free Cloud)", "type": "cloud",
                   "endpoint": "https://openrouter.ai/api/v1/chat/completions"},
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
    "llama3.2:3b",
    "phi3:latest",
    "deepseek-r1:1.5b",
    "qwen2.5-coder:1.5b",
]

DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

# Free models tersedia di OpenRouter (tidak perlu bayar)
# Diurutkan: reasoning quality (descending)
OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",       # Recommended — stabil
    "nvidia/nemotron-3-ultra-550b-a55b:free",        # Paling powerful
    "nvidia/nemotron-3-super-120b-a12b:free",        # High capability
    "qwen/qwen3-coder:free",                          # 480B Qwen3
    "nousresearch/hermes-3-llama-3.1-405b:free",     # 405B Hermes
    "openai/gpt-oss-120b:free",                      # OpenAI OSS
    "nvidia/nemotron-3-nano-30b-a3b:free",           # Fast fallback
    "google/gemma-4-31b-it:free",                    # Google Gemma
]

DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

def get_provider_names():
    return list(PROVIDER_REGISTRY.keys())
