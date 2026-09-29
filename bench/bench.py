"""Smaran benchmarks (plan section 8). Publishes whatever it measures.

    python -m bench.bench                  # all, writes bench/results.json + docs/BENCHMARKS.md
    python -m bench.bench latency conflicts

Sections: latency, retrieval, conflicts, convergence, bandwidth, classifier, rehearsals (reads
logs/rehearsal.log), audit (needs a running gateway), snapshots (needs Qdrant Server).
"""
import csv
import json
import random
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

import httpx

from backend.common.config import MACHINES, settings
from backend.common.log import Log
from backend.common.schema import AGORA, HERMES, NoteIn
from backend.common.themis import CONTESTED, CURRENT, naive_merge, next_vv, resolve
from backend.common.vectors import pack, unpack
from backend.device.classifier import load_classifier
from backend.device.core import Device
from backend.device.embed import get_embedder
from bench.partial_snapshot import bench_snapshots, to_markdown as snapshots_md
from bench.retrieval import bench_retrieval, to_markdown as retrieval_md
from bench.simulate import run as simulate

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "bench" / "results.json"
OUT_MD = ROOT / "docs" / "BENCHMARKS.md"


def notes_corpus() -> list[dict]:
    rows = []
    for f in ("template_notes.csv", "handwritten_notes.csv"):
        with (ROOT / "ml" / "data" / f).open(encoding="utf8") as fh:
            rows += list(csv.DictReader(fh))
    return rows


def _tmpdir():
    """Scratch space on the project drive (runtime/ is git-ignored); removed afterwards."""
    d = ROOT / "runtime" / "bench-tmp"
    d.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=d, ignore_cleanup_errors=True)


def _device(tmp: Path, emb, name="bench") -> Device:
    return Device(name, tmp / name, emb, load_classifier(), http=None, log=Log(f"bench-{name}", tmp / "logs"))


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))], 2)


# ---------------------------------------------------------------------------------------
def bench_latency(emb, n_memories=2000, n_queries=1000) -> dict:
    rng = random.Random(3)
    corpus = [r["text"] for r in notes_corpus()]
    machines = MACHINES
    texts = [f"{rng.choice(corpus)} (shift {i % 3 + 1}, {rng.choice(machines)})" for i in range(n_memories)]
    with _tmpdir() as td:
        dev = _device(Path(td), emb)
        dev.set_online(False)
        dense = emb.dense(texts)
        for i, (t, d) in enumerate(zip(texts, dense)):
            shard = (AGORA, HERMES, "krypta")[i % 3]
            dev.store.upsert(shard, f"M-{i}", d, emb.bm25.embed_document(t),
                             {"op_id": f"M-{i}", "text": t, "status": CURRENT, "known_from": time.time()})
        dev.store.optimize()
        queries = [rng.choice(corpus)[:60] for _ in range(n_queries)]
        search_ms, total_ms = [], []
        for q in queries:
            r = dev.search(q)
            search_ms.append(r["search_ms"])
            total_ms.append(r["latency_ms"])
        dev.close()
    return {"memories": n_memories, "queries": n_queries, "shards": 3, "network": "offline",
            "search_p50_ms": pct(search_ms, 50), "search_p95_ms": pct(search_ms, 95),
            "with_embedding_p50_ms": pct(total_ms, 50), "with_embedding_p95_ms": pct(total_ms, 95)}


# ---------------------------------------------------------------------------------------
def bench_conflicts(n=50, seed=11) -> dict:
    """Scripted cases with known truth. Device clocks are skewed by up to +-10 minutes.

    update: B writes after seeing A's version (a real update)  -> newest must be current
    concurrent: A and B write without seeing each other         -> both must be flagged
    """
    rng = random.Random(seed)
    themis_ok = naive_ok = 0
    kinds = {"update": [0, 0, 0], "concurrent": [0, 0, 0]}   # cases, themis_ok, naive_ok
    for i in range(n):
        skew = {"A": rng.uniform(-600, 600), "B": rng.uniform(-600, 600)}
        base = {"op_id": "F-1", "vv": {"F": 1}, "valid_from": 0}
        t = 1000.0
        a = {"op_id": "A-1", "vv": next_vv([base["vv"]], "A", 1), "valid_from": t + skew["A"]}
        if i % 2 == 0:
            kind = "update"
            b = {"op_id": "B-1", "vv": next_vv([base["vv"], a["vv"]], "B", 1), "valid_from": t + 60 + skew["B"]}
            r = resolve([base, a, b])
            t_ok = r["B-1"][0] == CURRENT and r["A-1"][0] != CURRENT
            n_ok = naive_merge([base, a, b]) == "B-1"
        else:
            kind = "concurrent"
            b = {"op_id": "B-1", "vv": next_vv([base["vv"]], "B", 1), "valid_from": t + rng.uniform(-30, 30) + skew["B"]}
            r = resolve([base, a, b])
            t_ok = r["A-1"][0] == CONTESTED and r["B-1"][0] == CONTESTED
            n_ok = False     # a last-writer-wins merge can never flag a conflict; one edit is silently lost
        themis_ok += t_ok
        naive_ok += n_ok
        k = kinds[kind]
        k[0] += 1
        k[1] += t_ok
        k[2] += n_ok
    return {"cases": n, "themis_correct": themis_ok, "naive_correct": naive_ok,
            "by_kind": {k: {"cases": v[0], "themis": v[1], "naive": v[2]} for k, v in kinds.items()},
            "clock_skew": "+-10 min per device"}


# ---------------------------------------------------------------------------------------
def bench_bandwidth(emb, n=500, seed=5) -> dict:
    """Bytes pushed to the gateway for one note script.

    Two effects, reported separately so neither hides the other:
    - selection: Smaran sends only notes that should sync (same op format on both sides)
    - encoding:  dense vectors as base64 float16 instead of JSON floats (VECTOR_TRANSPORT)
    The baseline is "sync everything, vectors as JSON floats", which is the old Smaran format
    and what a naive dual-write of every note sends.
    """
    rng = random.Random(seed)
    corpus = notes_corpus()
    script = [rng.choice(corpus) for _ in range(n)]
    with _tmpdir() as td:
        dev = _device(Path(td), emb)
        dev.set_online(False)
        for r in script:
            dev.add_note(NoteIn(text=r["text"], kind=r["kind"], machine=r["machine"] or None))
        pending = [b for _, b in dev.db.pending_bodies()]
        decisions = dev.db.decisions(10_000)
        dev.close()

    def size(body: dict, transport: str) -> int:
        v = unpack(body["vectors"])
        wire = {**body, "vectors": pack(v["dense"], v["bm25"], transport)}
        return len(json.dumps({"device_id": "bench", "ops": [wire]}))

    json_sizes = [size(b, "json") for b in pending]
    f16_sizes = [size(b, "f16") for b in pending]
    avg_json = sum(json_sizes) / max(len(pending), 1)
    avg_f16 = sum(f16_sizes) / max(len(pending), 1)
    everything_json = int(avg_json * n)     # every note, JSON-float vectors
    counts = {}
    for d in decisions:
        counts[d["residency"]] = counts.get(d["residency"], 0) + 1
    smaran_json, smaran_f16 = sum(json_sizes), sum(f16_sizes)
    return {"notes": n, "residency": counts, "ops_sent": len(pending),
            "avg_op_bytes_json": round(avg_json), "avg_op_bytes_f16": round(avg_f16),
            "sync_everything_json_bytes": everything_json,
            "smaran_json_bytes": smaran_json, "smaran_f16_bytes": smaran_f16,
            "saved_by_selection_pct": round(100 * (1 - smaran_json / everything_json), 1),
            "saved_total_pct": round(100 * (1 - smaran_f16 / everything_json), 1),
            "transport": settings.vector_transport,
            "private_kept_on_device": counts.get("private", 0)}


def _retrieval(emb) -> dict:
    with _tmpdir() as td:
        def make(e) -> Device:
            dev = _device(Path(td), e, "retrieval")
            dev.set_online(False)
            return dev
        return bench_retrieval(emb, make)


def bench_classifier() -> dict:
    p = ROOT / "ml" / "artifacts" / "report.json"
    if not p.exists():
        return {"skipped": "run: python -m ml.train"}
    rep = json.loads(p.read_text(encoding="utf8"))
    return {k: rep[k] for k in ("n_train", "n_test", "rules-only", "logreg (alone)", "logreg + rules (shipped)", "label_agreement")}


def bench_rehearsals() -> dict:
    """Summarise logs/rehearsal.log (written by scripts/demo.py rehearse), newest session per beat set.

    A session is a run of consecutive lines with the same Qdrant target, commit and beats.
    """
    path = ROOT / "logs" / "rehearsal.log"
    if not path.exists():
        return {"skipped": "no logs/rehearsal.log: run python scripts/demo.py rehearse"}
    rows = [json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip()]
    rows = [r for r in rows if "qdrant" in r]          # older lines didn't record the target
    sessions: list[dict] = []
    for r in rows:
        beats = sorted(k for k in r if k.startswith("b") and k[1:].isdigit())
        key = (r["qdrant"], r["commit"], tuple(beats))
        if sessions and sessions[-1]["key"] == key and r["run"] == sessions[-1]["runs"] + 1:
            s_ = sessions[-1]
        else:
            s_ = {"key": key, "runs": 0, "passed": 0, "ts": r["ts"]}
            sessions.append(s_)
        s_["runs"] += 1
        s_["passed"] += all(r[b] for b in beats)
    latest: dict[tuple, dict] = {}
    for s_ in sessions:
        latest[(s_["key"][0], s_["key"][2])] = s_
    return {"sessions": [{"qdrant": k[0], "commit": v["key"][1], "beats": list(k[1]), "runs": v["runs"],
                          "passed": v["passed"], "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(v["ts"]))}
                         for k, v in latest.items()]}


def bench_audit() -> dict:
    try:
        return httpx.get(f"{settings.gateway_url}/audit", timeout=5).json()
    except Exception as e:  # noqa: BLE001
        return {"skipped": f"gateway not reachable ({e.__class__.__name__}); start it and rerun: python -m bench.bench audit"}


# ---------------------------------------------------------------------------------------
def to_markdown(r: dict) -> str:
    L = ["# Benchmarks", "", f"Generated by `python -m bench.bench` on {time.strftime('%Y-%m-%d %H:%M')}. "
         "Numbers are measured, not targets. Machine: the dev laptop, CPU only.", ""]
    if "latency" in r:
        x = r["latency"]
        L += ["## Offline search latency", "",
              f"{x['queries']} hybrid queries (dense cosine + BM25 with device-wide IDF, fused with RRF across all {x['shards']} shards) over "
              f"{x['memories']} memories, device offline.", "",
              "| | p50 | p95 | target |", "|---|---|---|---|",
              f"| Search only | {x['search_p50_ms']} ms | {x['search_p95_ms']} ms | < 20 / 50 ms |",
              f"| Including query embedding | {x['with_embedding_p50_ms']} ms | {x['with_embedding_p95_ms']} ms | |", ""]
    if "retrieval" in r:
        L += retrieval_md(r["retrieval"])
    if "conflicts" in r:
        x = r["conflicts"]
        L += ["## Conflict accuracy (Themis vs naive last-writer-wins)", "",
              f"{x['cases']} scripted cases, device clocks skewed {x['clock_skew']}.", "",
              "| Case | Cases | Themis correct | Naive merge correct |", "|---|---|---|---|"]
        for k, v in x["by_kind"].items():
            L.append(f"| {k} | {v['cases']} | {v['themis']} | {v['naive']} |")
        L += [f"| **total** | {x['cases']} | **{x['themis_correct']}** | {x['naive_correct']} |", "",
              "A naive merge can never flag a concurrent edit: one technician's report is silently lost.", ""]
    if "convergence" in r:
        x = r["convergence"]
        L += ["## Multi-device convergence", "",
              f"{x['runs']} randomized runs, {x['devices']} devices + gateway ({x['replicas_per_run']} replicas), random "
              "offline edits, random delivery order, duplicate sends.", "",
              f"- Replicas identical: **{x['converged']} / {x['runs']}**",
              f"- Same result as resolving the full set at once: {x['matches_batch_resolve']} / {x['runs']}",
              f"- Concurrent edits lost: **{x['lost_concurrent_edits']}** "
              f"(across {x['entities_with_conflicts']} entities that had real conflicts)", ""]
    if "bandwidth" in r:
        x = r["bandwidth"]
        L += ["## Bandwidth", "",
              f"The same {x['notes']}-note script. Decisions: "
              + ", ".join(f"{k} {v}" for k, v in sorted(x['residency'].items()))
              + f". Baseline: sync every note with the dense vector as JSON floats.", "",
              "| | Bytes pushed | Saved vs baseline |", "|---|---|---|",
              f"| Baseline: every note, JSON-float vectors | {x['sync_everything_json_bytes']:,} | |",
              f"| Smaran, selection only (JSON-float vectors) | {x['smaran_json_bytes']:,} | {x['saved_by_selection_pct']}% |",
              f"| **Smaran, selection + float16 vectors (shipped)** | **{x['smaran_f16_bytes']:,}** | **{x['saved_total_pct']}%** |", "",
              f"- Target >= 40%. Selection alone saves {x['saved_by_selection_pct']}% (it missed the target on its own); "
              f"float16 transport takes the total to {x['saved_total_pct']}%.",
              f"- Average op: {x['avg_op_bytes_json']:,} bytes with JSON floats, {x['avg_op_bytes_f16']:,} bytes with float16 "
              f"({x['ops_sent']} ops sent). Private notes kept on device: {x['private_kept_on_device']}.",
              "- float16 changes cosine similarity by < 0.001 (`backend/tests/test_vectors.py`).", ""]
    if "classifier" in r:
        x = r["classifier"]
        if "skipped" not in x:
            L += ["## Residency classifier", "",
                  f"Trained on {x['n_train']} notes, tested on {x['n_test']} held-out hand-written notes.", "",
                  "| Model | Residency acc | Macro-F1 | Criticality acc | Safety-critical recall |", "|---|---|---|---|---|"]
            for k in ("rules-only", "logreg (alone)", "logreg + rules (shipped)"):
                s = x[k]
                L.append(f"| {k} | {s['residency_acc']} | {s['residency_macro_f1']} | {s['criticality_acc']} | {s.get('safety_recall', '')} |")
            la = x["label_agreement"]
            if isinstance(la, dict):
                agree = (f"Label agreement (Cohen's kappa, {la['n']} test notes): residency **{la['residency_kappa']}**, "
                         f"criticality **{la['criticality_kappa']}** (target 0.7). The second labeller was **Claude, an AI "
                         "model**, not a human: it labelled from the written class definitions without being shown the first "
                         "labels (apart from the first two rows, seen by accident). Reported as measured; no label was changed "
                         "to raise it. A human second labeller is still worth adding.")
            else:
                agree = f"Label agreement: {la}"
            L += ["", agree, "",
                  "Caveats: the hand-written set is small (60 test notes), and the criticality combination rule "
                  "was chosen after looking at these results, so treat those numbers as optimistic.", ""]
    if "rehearsals" in r:
        x = r["rehearsals"]
        L += ["## Demo rehearsals", "",
              "`python scripts/demo.py rehearse` resets and plays each beat with automated checks; every run is "
              "logged to `logs/rehearsal.log` with the Qdrant target and git commit. Latest session per target and beat set:", ""]
        if "skipped" in x:
            L += [f"- {x['skipped']}", ""]
        else:
            L += ["| Qdrant target | Beats | Passed | Commit | Date |", "|---|---|---|---|---|"]
            for s_ in x["sessions"]:
                L.append(f"| `{s_['qdrant']}` | {' '.join(s_['beats'])} | **{s_['passed']}/{s_['runs']}** | "
                         f"{s_['commit']} | {s_['date']} |")
            L.append("")
    if "snapshots" in r:
        L += snapshots_md(r["snapshots"])
    if "audit" in r:
        x = r["audit"]
        L += ["## Personal data on the server", ""]
        L += [f"- {x['skipped']}"] if "skipped" in x else [
            f"- Points on server: {x['total']} · private records: **{x['private_count']}** · PII regex hits: **{x['pii_hits']}**"]
        L.append("")
    return "\n".join(L)


def main(sections: list[str]) -> None:
    sections = sections or ["latency", "retrieval", "conflicts", "convergence", "bandwidth", "classifier",
                            "rehearsals", "audit", "snapshots"]
    results = json.loads(OUT_JSON.read_text(encoding="utf8")) if OUT_JSON.exists() else {}
    emb = get_embedder("fastembed") if {"latency", "bandwidth", "retrieval"} & set(sections) else None
    for s in sections:
        t = time.perf_counter()
        results[s] = {"latency": lambda: bench_latency(emb), "conflicts": bench_conflicts,
                      "retrieval": lambda: _retrieval(emb),
                      "convergence": lambda: simulate(1000, 5), "bandwidth": lambda: bench_bandwidth(emb),
                      "classifier": bench_classifier, "rehearsals": bench_rehearsals, "audit": bench_audit,
                      "snapshots": bench_snapshots}[s]()
        print(f"{s}: {results[s]}  ({time.perf_counter() - t:.1f}s)")
    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf8")
    OUT_MD.write_text(to_markdown(results), encoding="utf8")
    print(f"\nwrote {OUT_JSON} and {OUT_MD}")
    shutil.rmtree(ROOT / "logs" / "bench", ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1:])
