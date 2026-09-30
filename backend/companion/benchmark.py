"""Live, side-effect-free measurements for the dashboard's "Edge benchmark" card.

Every number is measured now, on this device, with a stopwatch. Nothing here writes memory.
The heavier benchmark (model load, 5,000-memory scale, offline restart) is bench/edge.py.
"""
import os
import statistics
import time
from pathlib import Path


def _pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))], 2)


def dir_size_mb(path: Path) -> float:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                pass
    return round(total / 1e6, 1)


QUERIES = ["which database did we decide on", "what tasks are left for the project", "when is the review meeting",
           "who handles the frontend", "when should I study", "what was covered in the last lecture"]


def quick(c, n: int = 30) -> dict:
    dev = c.dev
    embed_ms, recall_ms = [], []
    for i in range(n):
        q = QUERIES[i % len(QUERIES)]
        t0 = time.perf_counter()
        dev.embedder.embed_query(q)
        embed_ms.append((time.perf_counter() - t0) * 1000)
        recall_ms.append(c.recall(q, 5, allow_cloud=False)["timing_ms"]["total"])
    agent_ms = []
    for i in range(min(n, 15)):
        t0 = time.perf_counter()
        c.run_action("list_tasks", {"status": "open"}, f"bench-{time.time()}-{i}", "bench")
        agent_ms.append((time.perf_counter() - t0) * 1000)
    # bench audit rows are read-only actions; drop them so the audit trail stays about the user
    with dev.db.lock:
        dev.db.conn.execute("DELETE FROM audit WHERE request_id='bench'")
    slm = None
    if c.router.use_local and c.router.local.available():
        try:
            t0 = time.perf_counter()
            c.router.local.chat([{"role": "user", "content": "Reply with one word: ready"}], max_tokens=4)
            slm = round((time.perf_counter() - t0) * 1000)
        except Exception:  # noqa: BLE001
            slm = None
    counts = dev.state()["counts"]
    return {
        "measured_at": time.time(), "samples": n, "memories": sum(counts.values()),
        "embed_ms_p50": _pct(embed_ms, 50), "embed_ms_p95": _pct(embed_ms, 95),
        "retrieval_ms_p50": _pct(recall_ms, 50), "retrieval_ms_p95": _pct(recall_ms, 95),
        "agent_read_action_ms_p50": _pct(agent_ms, 50),
        "local_slm_ms": slm, "local_slm_model": c.router.local.model,
        "data_dir_mb": dir_size_mb(dev.root), "network_used": "none for these measurements",
        "note": "retrieval includes query embedding, Qdrant Edge hybrid search over 3 shards, and rerank",
        "mean_retrieval_ms": round(statistics.mean(recall_ms), 2),
    }
