"""Retrieval benchmark plumbing: golden labels point at real memories; metrics are sane."""
from backend.common.log import Log
from backend.device.classifier import KeywordClassifier
from backend.device.core import Device
from backend.device.search import MODES
from bench.retrieval import corpus, evaluate, load_golden


def test_golden_ids_exist_in_corpus():
    ids = {cid for cid, _, _ in corpus()}
    queries = load_golden()
    assert len(queries) >= 30
    assert len({q["id"] for q in queries}) == len(queries)
    for q in queries:
        assert q["relevant"] and set(q["relevant"]) <= ids, q["id"]


def test_evaluate_returns_bounded_metrics(tmp_path, embedder):
    docs = corpus()[:40]
    queries = [q for q in load_golden() if set(q["relevant"]) & {cid for cid, _, _ in docs}][:5]
    dev = Device("R", tmp_path / "r", embedder, KeywordClassifier(), log=Log("r", tmp_path / "logs"))
    dev.set_online(False)
    try:
        res = evaluate(dev, queries, docs)
    finally:
        dev.close()
    assert set(res) == set(MODES)
    for mode in MODES:
        for key in ("hit@1", "hit@5", "mrr"):
            assert 0.0 <= res[mode]["all"][key] <= 1.0
        assert res[mode]["all"]["hit@1"] <= res[mode]["all"]["hit@5"]
