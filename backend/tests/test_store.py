from backend.common.schema import AGORA, HERMES
from backend.device.embed import HashEmbedder
from backend.device.store import Store


def test_bm25_scores_comparable_across_shards(tmp_path):
    """Device-wide IDF: the same text scores the same in a busy shard and an almost empty one."""
    emb = HashEmbedder()
    s = Store(tmp_path / "s", emb.dim)
    try:
        for i in range(20):
            t = f"CNC-{i:02d} manual: spindle lubrication schedule {i}"
            s.upsert(AGORA, f"F-{i}", *emb.embed_doc(t), {"op_id": f"F-{i}", "text": t, "status": "current"})
        text = "CNC-07 bearing replaced, vibration normal"
        s.upsert(AGORA, "X-agora", *emb.embed_doc(text), {"op_id": "X-agora", "text": text, "status": "current"})
        s.upsert(HERMES, "X-hermes", *emb.embed_doc(text), {"op_id": "X-hermes", "text": text, "status": "current"})
        q = s.idf_query(emb.bm25.embed_query("bearing vibration"))
        a = s.vector_search(AGORA, q, "bm25", 5)[0]
        h = s.vector_search(HERMES, q, "bm25", 5)[0]
        assert a.payload["op_id"] == "X-agora" and h.payload["op_id"] == "X-hermes"
        assert abs(a.score - h.score) < 1e-4
        # df bookkeeping survives delete and reload
        n = s.n_docs
        s.delete(HERMES, "X-hermes")
        assert s.n_docs == n - 1
        s.close()
        s.open()
        assert s.n_docs == n - 1
    finally:
        s.close()
