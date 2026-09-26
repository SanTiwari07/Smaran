"""One-time download of the embedding model into models/, so devices can run with Wi-Fi off.

Usage: python scripts/setup_models.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.common.config import settings  # noqa: E402


def main() -> None:
    from fastembed import TextEmbedding

    models_dir = ROOT / settings.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    t = time.perf_counter()
    model = TextEmbedding(settings.dense_model, cache_dir=str(models_dir))
    vec = next(iter(model.embed(["CNC-07 bearing replaced"])))
    print(f"{settings.dense_model}: dim={len(vec)} ready in {time.perf_counter() - t:.1f}s -> {models_dir}")
    print("BM25 is built into qdrant-edge-py; nothing to download.")


if __name__ == "__main__":
    main()
