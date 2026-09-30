"""Settings from .env (or the process environment): ports, URLs, thresholds.

Every service reads the same file, so a port or threshold is changed in one place.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    gateway_port: int = int(_env("GATEWAY_PORT", "8000"))
    gateway_url: str = _env("GATEWAY_URL", "http://127.0.0.1:8000")
    device_ports: dict = field(default_factory=lambda: {
        "A": int(_env("DEVICE_A_PORT", "8001")),
        "B": int(_env("DEVICE_B_PORT", "8002")),
    })
    # "server" talks to Qdrant Server at QDRANT_URL (the real PS3 setup, via Docker).
    # "embedded" uses qdrant-client's local mode: same API, no Docker; for dev and tests.
    qdrant_mode: str = _env("QDRANT_MODE", "server")
    qdrant_url: str = _env("QDRANT_URL", "http://127.0.0.1:6333")
    qdrant_collection: str = _env("QDRANT_COLLECTION", "smaran")
    dense_model: str = _env("DENSE_MODEL", "BAAI/bge-small-en-v1.5")
    dense_dim: int = int(_env("DENSE_DIM", "384"))
    models_dir: str = _env("MODELS_DIR", "models")
    runtime_dir: str = _env("RUNTIME_DIR", "runtime")
    log_dir: str = _env("LOG_DIR", "logs")
    escalate_at: float = float(_env("ESCALATE_AT", "0.55"))
    dedup_at: float = float(_env("DEDUP_AT", "0.95"))
    sync_interval: float = float(_env("SYNC_INTERVAL", "2.0"))
    sync_batch: int = int(_env("SYNC_BATCH", "20"))
    # How dense vectors travel on the wire: "f16" (base64 float16, ~8x smaller) or "json" floats.
    vector_transport: str = _env("VECTOR_TRANSPORT", "f16")
    # ---- companion (personal assistant layer) ----
    # Local small language model, served by Ollama (llama.cpp) on this machine.
    local_llm_url: str = _env("LOCAL_LLM_URL", "http://127.0.0.1:11434")
    local_llm_model: str = _env("LOCAL_LLM_MODEL", "llama3.2:latest")
    # Optional cloud enhancement: any OpenAI-compatible endpoint. Empty = not configured.
    cloud_llm_url: str = _env("CLOUD_LLM_URL", "")
    cloud_llm_key: str = _env("CLOUD_LLM_KEY", "")
    cloud_llm_model: str = _env("CLOUD_LLM_MODEL", "")
    # Google Gemini API for cloud LLM answers.
    gemini_api_key: str = _env("GEMINI_API_KEY", "")
    gemini_model: str = _env("GEMINI_MODEL", "gemini-2.0-flash")
    gemini_url: str = _env("GEMINI_URL", "https://generativelanguage.googleapis.com")
    # Which knowledge the gateway seeds into the fleet collection ("campus" or "manuals")
    # "personal" (student/developer companion) or "fleet" (the original maintenance-notes domain)
    domain: str = _env("SMARAN_DOMAIN", "personal")
    seed_dir: str = _env("SEED_DIR", "seed/campus")

    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else ROOT / p


settings = Settings()

MACHINES = ["CNC-07", "CNC-12", "LATHE-03", "PRESS-02", "ROBOT-ARM-5"]

# How the dashboard names the demo devices in the personal story.
DEVICE_LABELS = {"A": "Phone", "B": "Laptop"}
