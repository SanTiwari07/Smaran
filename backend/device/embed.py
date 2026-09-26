"""Text -> vectors, fully on device.

- dense: FastEmbed bge-small-en-v1.5 (384-d, meaning), loaded from models/ with no network
- bm25:  Qdrant Edge's built-in BM25 (keywords); its token ids match Qdrant Server's BM25

HashEmbedder is a tiny deterministic stand-in used by tests and benchmarks that shouldn't
depend on model files.
"""
import hashlib
import math
import re

from qdrant_edge import Bm25, Bm25Config, SparseVector

from ..common.config import settings


def sparse_to_json(sv: SparseVector) -> dict:
    return {"indices": list(sv.indices), "values": [float(x) for x in sv.values]}


def sparse_from_json(d: dict) -> SparseVector:
    return SparseVector(indices=list(d["indices"]), values=list(d["values"]))


class Embedder:
    name = "base"
    dim = settings.dense_dim

    def __init__(self):
        self.bm25 = Bm25(Bm25Config(language="english"))

    def dense(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_doc(self, text: str) -> tuple[list[float], SparseVector]:
        return self.dense([text])[0], self.bm25.embed_document(text)

    def embed_query(self, text: str) -> tuple[list[float], SparseVector]:
        return self.dense([text])[0], self.bm25.embed_query(text)


class FastEmbedder(Embedder):
    name = "bge-small-en-v1.5"

    def __init__(self):
        super().__init__()
        from fastembed import TextEmbedding

        models_dir = settings.path(settings.models_dir)
        try:
            self.model = TextEmbedding(settings.dense_model, cache_dir=str(models_dir), local_files_only=True)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                f"Embedding model not found in {models_dir}. Run once with internet: "
                f"python scripts/setup_models.py  ({e})") from e

    def dense(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.model.embed(texts)]


class HashEmbedder(Embedder):
    """Bag-of-words hashed into `dim` buckets, L2-normalised. Deterministic, no model files."""
    name = "hash"

    def __init__(self, dim: int | None = None):
        super().__init__()
        self.dim = dim or settings.dense_dim

    def dense(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for tok in re.findall(r"[a-z0-9]+", t.lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


def get_embedder(kind: str = "fastembed") -> Embedder:
    return HashEmbedder() if kind == "hash" else FastEmbedder()
