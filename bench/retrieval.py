"""Retrieval quality on a golden query set: hybrid vs dense-only vs BM25-only.

    python -m bench.bench retrieval      # writes the "Retrieval quality" section of docs/BENCHMARKS.md

Corpus: fleet manuals go to Agora (as after a sync), hand-written notes to Hermes, so the
query runs across shards exactly like on a device. Metrics per mode, over all queries and
per category: hit@1, hit@5 (any relevant id in the top k) and MRR (1 / rank of the first
relevant id, 0 if not in the top 10).
"""
import csv
import json
import time
from pathlib import Path

from backend.common.schema import AGORA, HERMES
from backend.device.search import MODES

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "bench" / "golden_queries.json"
K = 10


def corpus() -> list[tuple[str, str, str]]:
    """(corpus id, shard, text)."""
    items = json.loads((ROOT / "seed" / "manuals" / "fleet.json").read_text(encoding="utf8"))
    out = [(f"FLEET-{i:04d}", AGORA, it["text"]) for i, it in enumerate(items, start=1)]
    with (ROOT / "ml" / "data" / "handwritten_notes.csv").open(encoding="utf8") as fh:
        out += [(r["id"], HERMES, r["text"]) for r in csv.DictReader(fh)]
    return out


def load_golden(path: Path = GOLDEN) -> list[dict]:
    return json.loads(path.read_text(encoding="utf8"))["queries"]


def _scores(ranked: list[str], relevant: set[str]) -> dict:
    rank = next((i + 1 for i, cid in enumerate(ranked) if cid in relevant), None)
    return {"hit1": rank == 1, "hit5": rank is not None and rank <= 5, "rr": 1.0 / rank if rank else 0.0}


def _summary(rows: list[dict]) -> dict:
    n = max(len(rows), 1)
    return {"n": len(rows), "hit@1": round(sum(r["hit1"] for r in rows) / n, 3),
            "hit@5": round(sum(r["hit5"] for r in rows) / n, 3), "mrr": round(sum(r["rr"] for r in rows) / n, 3)}


def evaluate(device, queries: list[dict], docs: list[tuple[str, str, str]]) -> dict:
    """Load `docs` into `device` and score every query in every mode."""
    emb = device.embedder
    dense = emb.dense([t for _, _, t in docs])
    for (cid, shard, text), d in zip(docs, dense):
        device.store.upsert(shard, cid, d, emb.bm25.embed_document(text),
                            {"op_id": cid, "text": text, "status": "current", "known_from": time.time()})
    device.store.optimize()
    out = {}
    for mode in MODES:
        rows = []
        for q in queries:
            res = device.search(q["q"], limit=K, mode=mode)
            ranked = [h["payload"]["op_id"] for h in res["results"]]
            rows.append({"id": q["id"], "category": q["category"], **_scores(ranked, set(q["relevant"]))})
        cats = sorted({r["category"] for r in rows})
        out[mode] = {"all": _summary(rows), **{c: _summary([r for r in rows if r["category"] == c]) for c in cats},
                     "misses_at_5": [r["id"] for r in rows if not r["hit5"]]}
    return out


def bench_retrieval(emb, make_device) -> dict:
    queries = load_golden()
    dev = make_device(emb)
    try:
        res = evaluate(dev, queries, corpus())
    finally:
        dev.close()
    return {"queries": len(queries), "corpus": len(corpus()), "k": K, "modes": res}


def to_markdown(x: dict) -> list[str]:
    L = ["## Retrieval quality", "",
         f"{x['queries']} golden queries (`bench/golden_queries.json`) over {x['corpus']} memories "
         "(fleet manuals in Agora, hand-written notes in Hermes), device offline. A query is a hit at k if any "
         "relevant memory is in the top k; MRR uses the rank of the first relevant memory (top 10).", "",
         "| Mode | hit@1 | hit@5 | MRR |", "|---|---|---|---|"]
    for mode in MODES:
        a = x["modes"][mode]["all"]
        name = "**hybrid (shipped)**" if mode == "hybrid" else f"{mode} only"
        L.append(f"| {name} | {a['hit@1']} | {a['hit@5']} | {a['mrr']} |")
    cats = [c for c in x["modes"]["hybrid"] if c not in ("all", "misses_at_5")]
    L += ["", "hit@5 by query type:", "", "| Type | Queries | " + " | ".join(MODES) + " |",
          "|---|---|" + "---|" * len(MODES)]
    for c in cats:
        L.append(f"| {c} | {x['modes']['hybrid'][c]['n']} | "
                 + " | ".join(str(x["modes"][m][c]["hit@5"]) for m in MODES) + " |")
    L += ["", "Misses at 5 (hybrid): " + (", ".join(x["modes"]["hybrid"]["misses_at_5"]) or "none") + ".", "",
          "Caveats: 40 queries written by the team against a known corpus, labelled by one person so far; "
          "treat the numbers as indicative, not as a general benchmark.", ""]
    return L
