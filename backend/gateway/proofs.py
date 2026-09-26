"""Checks behind the dashboard's "Prove it" panel. Each one re-runs a headline claim live.

The heavy lifting reuses the benchmark code (bench/), so the panel and docs/BENCHMARKS.md
measure the same thing. Run from the repo root, like every service.
"""
import json
import time

from ..common.config import settings
from ..common.schema import SyncBatch
from ..common.vectors import pack
from .server import vectors_json


def conflicts(n: int = 50) -> dict:
    from bench.bench import bench_conflicts
    t = time.perf_counter()
    r = bench_conflicts(n)
    return {**r, "ms": round((time.perf_counter() - t) * 1000, 1),
            "ok": r["themis_correct"] == r["cases"], "command": "python -m bench.bench conflicts"}


def convergence(runs: int = 100, devices: int = 5) -> dict:
    from bench.simulate import run
    t = time.perf_counter()
    r = run(runs, devices)
    return {**r, "ms": round((time.perf_counter() - t) * 1000, 1),
            "ok": r["converged"] == r["runs"] and r["lost_concurrent_edits"] == 0,
            "command": "python -m bench.bench convergence"}


def idempotency(gw) -> dict:
    """Send the most recently stored op again, as a device retrying after a lost ack would."""
    with gw.lock:
        recs = gw.server.scroll(with_vectors=True)
        if not recs:
            return {"ok": False, "error": "no memories on the server yet"}
        rec = max(recs, key=lambda r: r.payload.get("server_seq", 0))
        before = gw.server.count()
        v = vectors_json(rec.vector)
        batch = SyncBatch.model_validate({"device_id": "prove-it", "ops": [
            {"op_id": rec.payload["op_id"], "vectors": pack(v["dense"], v["bm25"]), "payload": rec.payload}]})
        result = gw.sync(batch, 0)["results"][0]["result"]
        after = gw.server.count()
    return {"op_id": rec.payload["op_id"], "result": result, "points_before": before, "points_after": after,
            "ok": result == "duplicate" and before == after, "command": "python -m pytest -k idempotent"}


def benchmarks() -> dict:
    """The last `python -m bench.bench` results (bench/results.json), for the scoreboard."""
    p = settings.path("bench/results.json")
    if not p.exists():
        return {"skipped": "run: python -m bench.bench"}
    r = json.loads(p.read_text(encoding="utf8"))
    keep = ("latency", "retrieval", "bandwidth", "conflicts", "convergence", "snapshots", "rehearsals")
    return {k: r[k] for k in keep if k in r} | {"generated": p.stat().st_mtime}
