import subprocess
import os

PROVIDERS = {
    "Ollama": ["ollama", "run"],
    "Gemini": ["gemini", "--skip-trust", "-p"],
    "Kilo": ["kilo"],
    "OpenCode": ["opencode"],
}

def generate(prompt, provider="Ollama", max_tokens=1500, model=None):
    cmd = PROVIDERS.get(provider, PROVIDERS["Ollama"])
    if provider == "Ollama":
        model = model or "llama3.2:latest"
        cmd = cmd + [model, prompt]
    else:
        cmd = cmd + [prompt]
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode == 0:
            return r.stdout.strip()
        else:
            error_msg = r.stderr.strip()[:200] if r.stderr else "Unknown error"
            return f"[{provider} error] {error_msg}"
    except subprocess.TimeoutExpired:
        return f"[{provider} timeout] Process timed out after 120s"
    except FileNotFoundError:
        return f"[{provider} not found] CLI tool not installed"
    except Exception as e:
        return f"[{provider} exception] {str(e)}"
