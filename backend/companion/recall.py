"""Retrieval: query understanding -> hybrid search -> rerank -> context.

    "What did I decide about the database?"
        understand: wants a decision, about "database"    (structured hints)
        hybrid:     Qdrant Edge dense + BM25, fused with RRF   (semantic + keyword)
        rerank:     + recency + importance + kind/subject/time-window match
        result:     ranked memories, each with a score breakdown ("why this one")

The rerank weights are fixed constants, tuned once against bench/personal_eval.json and
reported in docs/BENCHMARKS.md, next to the plain hybrid and dense-only numbers they beat (or don't).
"""
import math
import re
import time
from datetime import datetime

from .lifecycle import lifecycle
from .timeparse import query_window

W_DENSE, W_RRF, W_RECENCY, W_IMPORTANCE, W_META = 0.45, 0.20, 0.10, 0.10, 0.15
HALF_LIFE_DAYS = 21.0

KIND_HINTS = [
    ("task", re.compile(r"\b(tasks?|todos?|to-do|remaining|pending|outstanding|left to do|deadlines?|to finish)\b", re.I)),
    ("decision", re.compile(r"\b(decid\w*|decision|chose|chosen|choose|pick\w*|using|use|stack|go(?:ing)? with)\b", re.I)),
    ("schedule", re.compile(r"\b(meeting|stand-?up|lecture|class|viva|schedule|when is|when's|what time (?:is|does|do we))\b", re.I)),
    ("preference", re.compile(r"\b(prefer\w*|habit\w*|usually|like to|favou?rite|how do i|work best|best time)\b", re.I)),
]
KIND_OF = {"task": {"task"}, "decision": {"decision"}, "schedule": {"fact"}, "preference": {"preference"}}


def understand(q: str, now: datetime, subjects: set[str]) -> dict:
    kinds = [k for k, rx in KIND_HINTS if rx.search(q)]
    low = q.lower()
    subj = [s for s in subjects if s and s.lower() in low]
    if not subj and re.search(r"\b(project|capstone|final[- ]year)\b", low) and "capstone" in subjects:
        subj = ["capstone"]
    return {"kinds": kinds, "subjects": subj, "window": query_window(q, now),
            "open_tasks_only": bool(re.search(r"\b(remaining|pending|outstanding|left|open|to do|todo)\b", low))}


def _norm_dense(d: float | None) -> float:
    return 0.0 if d is None else max(0.0, min(1.0, (d - 0.30) / 0.55))


def rerank(hits: list[dict], u: dict, now_ts: float) -> list[dict]:
    if not hits:
        return hits
    # RRF scores are only comparable within one fusion: the server's (cloud) scale differs from
    # the device's, so each group is normalised by its own best score.
    top = {}
    for h in hits:
        g = h["shard"] == "cloud"
        top[g] = max(top.get(g, 0.0), h["rrf"])
    want_kinds = set().union(*[KIND_OF[k] for k in u["kinds"]]) if u["kinds"] else set()
    for h in hits:
        p = h["payload"]
        age_days = max((now_ts - (p.get("valid_from") or now_ts)) / 86400, 0)
        f = {
            "semantic": _norm_dense(h.get("dense_score")),
            "keyword+semantic (rrf)": h["rrf"] / (top[h["shard"] == "cloud"] or 1.0),
            "recency": math.exp(-math.log(2) * age_days / HALF_LIFE_DAYS),
            "importance": float(p.get("importance") or 0.3),
        }
        meta, why = 0.0, []
        if want_kinds and p.get("kind") in want_kinds:
            meta += 0.5
            why.append(f"kind={p['kind']}")
        if u["subjects"] and p.get("subject") in u["subjects"]:
            meta += 0.35
            why.append(f"subject={p['subject']}")
        w = u["window"]
        if w and w[0] <= (p.get("valid_from") or 0) <= w[1]:
            meta += 0.4
            why.append("in time window")
        if p.get("kind") == "task" and u["open_tasks_only"] and p.get("task_status") in ("done", "cancelled"):
            meta -= 0.6
            why.append("task already closed")
        f["metadata"] = max(min(meta, 1.0), -1.0)
        score = (W_DENSE * f["semantic"] + W_RRF * f["keyword+semantic (rrf)"] + W_RECENCY * f["recency"]
                 + W_IMPORTANCE * f["importance"] + W_META * f["metadata"])
        lc = lifecycle(p, now_ts)
        if lc.state == "stale":
            score *= 0.8
            why.append("stale")
        h["lifecycle"] = lc.as_dict()
        h["score"] = round(score, 4)
        h["features"] = {k: round(v, 3) for k, v in f.items()}
        h["why"] = why
    hits.sort(key=lambda h: -h["score"])
    return hits


def recall(device, q: str, k: int = 5, now_ts: float | None = None, subjects: set[str] | None = None,
           rerank_on: bool = True, allow_cloud: bool = True) -> dict:
    now_ts = now_ts or time.time()
    u = understand(q, datetime.fromtimestamp(now_ts), subjects or set())
    t0 = time.perf_counter()
    res = device.search(q, limit=max(k * 4, 20), allow_cloud=allow_cloud)
    t1 = time.perf_counter()
    hits = rerank(res["results"], u, now_ts) if rerank_on else res["results"]
    hidden = 0
    if rerank_on and not re.search(r"\b(history|previous(?:ly)?|old|older|used to|archived?|back then)\b", q, re.I):
        kept = [h for h in hits if h.get("lifecycle", {}).get("state") != "archived"]
        hidden, hits = len(hits) - len(kept), kept      # archived memories stay stored, but recall does not surface them
    t2 = time.perf_counter()
    return {"hits": hits[:k], "archived_hidden": hidden, "understanding": {**u, "window": bool(u["window"])},
            "answered": res["answered"], "top_dense": res["top_dense"],
            "timing_ms": {"embed": res["embed_ms"], "search": res["search_ms"], "rerank": round((t2 - t1) * 1000, 2),
                          "total": round((t2 - t0) * 1000, 2)}}
