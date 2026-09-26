"""Hybrid search across Krypta, Hermes and Agora.

1. Each shard returns a dense (cosine) list and a BM25 list from Qdrant Edge.
2. The dense lists are merged into ONE global list by cosine score. That's valid because
   every shard uses the same embedding model and distance.
3. The BM25 lists are merged into one global list by BM25 score. The query is weighted with
   a device-wide IDF (Store.idf_query), so these scores are comparable across shards too.
4. The two global lists are fused with RRF.

Why not native Fusion.Rrf per shard and then merge the three shard lists by rank? Because a
tiny shard's #1 hit would tie with a big shard's #1 even when it's irrelevant (found in the
dashboard: a one-note Krypta outranked the real answer). Store.hybrid (native per-shard RRF)
is still used when searching a single shard.

`dense_score` (cosine to the query) is reported per result. Cloud escalation uses the best
dense_score, because RRF scores say nothing about absolute relevance.
"""
import math
import time

from ..common.schema import SHARDS
from .store import NOT_SUPERSEDED

RRF_K = 60


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def rrf_fuse(ranked_lists: list[list[tuple[str, object]]], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion over lists of (op_id, anything). Returns op_id -> score."""
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for rank, (op_id, _) in enumerate(lst):
            scores[op_id] = scores.get(op_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def global_list(per_shard: dict[str, list]) -> list[tuple[str, tuple[str, object]]]:
    """Merge per-shard ranked points by raw score; one entry per op_id (Agora wins ties)."""
    best: dict[str, tuple[float, str, object]] = {}
    for shard, points in per_shard.items():
        for p in points:
            op_id = p.payload["op_id"]
            if op_id not in best or p.score > best[op_id][0] or (p.score == best[op_id][0] and shard == "agora"):
                best[op_id] = (p.score, shard, p)
    ordered = sorted(best.items(), key=lambda kv: -kv[1][0])
    return [(op_id, (shard, p)) for op_id, (_, shard, p) in ordered]


def believed_at(payload: dict, at: float) -> bool:
    """Did this replica believe this version at time `at`? Uses local known/valid times."""
    known = payload.get("known_from") or payload.get("valid_from") or 0
    until = payload.get("valid_to")
    return known <= at and (until is None or until > at)


MODES = ("hybrid", "dense", "bm25")


def local_search(store, embedder, q: str, limit: int = 10, at: float | None = None,
                 include_superseded: bool = False, shards=SHARDS, mode: str = "hybrid") -> dict:
    """mode: "hybrid" (default, dense + BM25 fused with RRF), or one list alone ("dense" /
    "bm25"), used by the retrieval-quality benchmark to show what each half contributes."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    t0 = time.perf_counter()
    dq, sq = embedder.embed_query(q)
    t1 = time.perf_counter()
    flt = None if (include_superseded or at is not None) else NOT_SUPERSEDED
    k = max(limit * 2, 20) if at is None else 100
    dense = global_list({s: store.vector_search(s, dq, "dense", k, flt) for s in shards})
    wq = store.idf_query(sq)
    sparse = global_list({s: store.vector_search(s, wq, "bm25", k, flt) for s in shards})
    fused = rrf_fuse({"hybrid": [dense, sparse], "dense": [dense], "bm25": [sparse]}[mode])
    seen = {op_id: sp for op_id, sp in dense}
    seen.update({op_id: sp for op_id, sp in sparse if op_id not in seen})
    hits = []
    for op_id in sorted(fused, key=lambda o: -fused[o]):
        shard, p = seen[op_id]
        if at is not None and not believed_at(p.payload, at):
            continue
        vec = (p.vector or {}).get("dense")
        hits.append({"payload": p.payload, "shard": shard, "rrf": round(fused[op_id], 5),
                     "dense_score": round(cosine(dq, vec), 4) if vec else None})
        if len(hits) == limit:
            break
    t2 = time.perf_counter()
    top = max((h["dense_score"] or 0 for h in hits), default=0.0)
    return {"results": hits, "top_dense": top, "query_vectors": (dq, sq),
            "embed_ms": round((t1 - t0) * 1000, 2), "search_ms": round((t2 - t1) * 1000, 2),
            "latency_ms": round((t2 - t0) * 1000, 2)}
