"""Compact dense-vector transport between devices and the gateway.

A 384-d vector as JSON floats is ~8 KB of text. As little-endian float16 bytes in base64 it
is 1,024 characters. float16 keeps ~3 significant digits, which changes cosine similarity
by far less than the gap between relevant and irrelevant results (see test_vectors.py).

Wire format inside a sync op or change-feed point:
    {"dense": [...floats...], "bm25": {...}}        # VECTOR_TRANSPORT=json (old format)
    {"dense_f16": "<base64>", "bm25": {...}}        # VECTOR_TRANSPORT=f16 (default)
Receivers accept both, so a device and gateway on different settings still interoperate.
"""
import base64

import numpy as np

from .config import settings


def encode_f16(dense: list[float]) -> str:
    return base64.b64encode(np.asarray(dense, dtype="<f2").tobytes()).decode("ascii")


def decode_f16(data: str) -> list[float]:
    return np.frombuffer(base64.b64decode(data), dtype="<f2").astype(np.float32).tolist()


def pack(dense: list[float], bm25: dict, transport: str | None = None) -> dict:
    """Vectors for the wire, in the configured transport."""
    if (transport or settings.vector_transport) == "f16":
        return {"dense_f16": encode_f16(dense), "bm25": bm25}
    return {"dense": [float(x) for x in dense], "bm25": bm25}


def dense_of(vectors: dict) -> list[float]:
    """The dense vector from either wire format."""
    if vectors.get("dense_f16") is not None:
        return decode_f16(vectors["dense_f16"])
    return list(vectors["dense"])


def unpack(vectors: dict) -> dict:
    """Wire vectors -> {"dense": [floats], "bm25": {...}} for storage."""
    return {"dense": dense_of(vectors), "bm25": vectors["bm25"]}
