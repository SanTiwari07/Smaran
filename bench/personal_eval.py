"""Retrieval quality for the personal companion, on the real embedder.

    python -m bench.personal_eval

Loads the story history and the extra notes through the real agent loop into a temporary
device, then asks each paraphrased query four ways:

  bm25         keyword search only (Qdrant Edge Bm25)
  dense        semantic search only (bge-small)
  hybrid       dense + BM25 fused with RRF (the device's default search)
  hybrid+rank  hybrid, then the companion's rerank (recency, importance, kind/subject/time match)

Reports hit@1, hit@3, hit@5 and MRR, each with its denominator. Writes bench/results/personal_eval.json.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.common.log import Log  # noqa: E402
from backend.companion.llm import ModelRouter  # noqa: E402
from backend.companion.service import Companion  # noqa: E402
from backend.companion.story import load_story  # noqa: E402
from backend.device.classifier import PersonalClassifier  # noqa: E402
from backend.device.core import Device  # noqa: E402
from backend.device.embed import get_embedder  # noqa: E402


def build(tmp: Path, embedder):
    dev = Device("A", tmp / "dev", embedder, PersonalClassifier(), http=None, log=Log("eval", tmp / "logs"))
    dev.set_online(False)
    c = Companion(dev, None, ModelRouter(online=lambda: False, use_local=False))
    load_story(c)
    data = json.loads((ROOT / "bench" / "personal_eval.json").read_text(encoding="utf8"))
    real = c.clock
    for i, note in enumerate(data["extra_notes"]):
        days_ago = 1 + (i * 5) % 12            # spread over the same two weeks as the story
        c.clock = lambda d=days_ago: real() - d * 86400
        c.chat(note, request_id=f"extra-{i}")
    c.clock = real
    return c, data


def ranked(c, q: str, method: str, k: int = 5) -> list[str]:
    if method in ("bm25", "dense"):
        res = c.dev.search(q, limit=k, mode=method, allow_cloud=False)
        return [h["payload"]["text"] for h in res["results"]]
    r = c.recall(q, k, rerank_on=(method == "hybrid+rank"), allow_cloud=False)
    return [h["payload"]["text"] for h in r["hits"]]


def score(c, queries) -> dict:
    out = {}
    for method in ("bm25", "dense", "hybrid", "hybrid+rank"):
        hits = {1: 0, 3: 0, 5: 0}
        rr = 0.0
        misses = []
        for item in queries:
            texts = ranked(c, item["q"], method)
            pos = next((i for i, t in enumerate(texts) if any(s.lower() in t.lower() for s in item["relevant"])), None)
            for k in hits:
                hits[k] += pos is not None and pos < k
            rr += 1 / (pos + 1) if pos is not None else 0
            if pos is None or pos >= 3:
                misses.append(item["q"])
        n = len(queries)
        out[method] = {"hit@1": f"{hits[1]}/{n}", "hit@3": f"{hits[3]}/{n}", "hit@5": f"{hits[5]}/{n}",
                       "hit@1_rate": round(hits[1] / n, 3), "hit@3_rate": round(hits[3] / n, 3),
                       "hit@5_rate": round(hits[5] / n, 3), "mrr": round(rr / n, 3), "not_in_top3": misses}
    return out


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="smaran-eval-"))
    try:
        emb = get_embedder("fastembed")
        c, data = build(tmp, emb)
        n_mem = sum(c.dev.state()["counts"].values())
        res = score(c, data["queries"])
        report = {"embedder": emb.name, "memories": n_mem, "queries": len(data["queries"]), "results": res}
        out = ROOT / "bench" / "results"
        out.mkdir(exist_ok=True)
        (out / "personal_eval.json").write_text(json.dumps(report, indent=1), encoding="utf8")
        print(f"embedder={emb.name} memories={n_mem} queries={len(data['queries'])}")
        print(f"{'method':<13}{'hit@1':>8}{'hit@3':>8}{'hit@5':>8}{'MRR':>8}")
        for m, r in res.items():
            print(f"{m:<13}{r['hit@1']:>8}{r['hit@3']:>8}{r['hit@5']:>8}{r['mrr']:>8}")
        print("hybrid+rank not in top 3:", res["hybrid+rank"]["not_in_top3"])
        c.dev.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
