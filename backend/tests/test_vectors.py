"""float16 vector transport: accuracy, wire format, and sync in both formats."""
import json
import random
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.common import vectors
from backend.common.schema import VectorsJson
from backend.device.search import cosine


def _rand_unit(rng, dim=384):
    v = [rng.gauss(0, 1) for _ in range(dim)]
    n = sum(x * x for x in v) ** 0.5
    return [x / n for x in v]


def test_f16_round_trip_is_accurate():
    rng = random.Random(7)
    for _ in range(50):
        a, b = _rand_unit(rng), _rand_unit(rng)
        a2 = vectors.decode_f16(vectors.encode_f16(a))
        assert len(a2) == len(a)
        assert max(abs(x - y) for x, y in zip(a, a2)) < 1e-3
        assert cosine(a, a2) > 0.9999
        assert abs(cosine(a, b) - cosine(a2, b)) < 1e-3     # ranking signal is preserved


def test_f16_is_much_smaller_on_the_wire():
    v = _rand_unit(random.Random(1))
    as_json = len(json.dumps(vectors.pack(v, {"indices": [], "values": []}, "json")))
    as_f16 = len(json.dumps(vectors.pack(v, {"indices": [], "values": []}, "f16")))
    assert as_f16 * 5 < as_json


def test_unpack_accepts_both_formats():
    v = [0.5, -0.25, 0.125]
    bm = {"indices": [1], "values": [1.0]}
    assert vectors.unpack(vectors.pack(v, bm, "json"))["dense"] == v
    assert vectors.unpack(vectors.pack(v, bm, "f16"))["dense"] == v   # exactly representable in f16


def test_schema_requires_exactly_one_dense_field():
    bm = {"indices": [], "values": []}
    VectorsJson(dense=[0.1], bm25=bm)
    VectorsJson(dense_f16=vectors.encode_f16([0.1]), bm25=bm)
    with pytest.raises(ValidationError):
        VectorsJson(bm25=bm)
    with pytest.raises(ValidationError):
        VectorsJson(dense=[0.1], dense_f16="AAA=", bm25=bm)


@pytest.mark.parametrize("transport", ["f16", "json"])
def test_sync_round_trip_in_both_formats(transport, make_device, gateway, monkeypatch):
    from backend.common.schema import NoteIn
    monkeypatch.setattr(vectors, "settings", SimpleNamespace(vector_transport=transport))
    a, ha = make_device("A")
    b, hb = make_device("B")
    out = a.add_note(NoteIn(text="LATHE-03 chuck jaws worn, replaced", kind="fix", machine="LATHE-03"))
    body = a.db.pending_bodies()[0][1]
    assert ("dense_f16" in body["vectors"]) == (transport == "f16")
    ha.sync_once()
    hb.sync_once()
    got = b.store.get("agora", out["memory"]["op_id"], with_vector=True)
    assert got is not None
    original = a.embedder.embed_doc("LATHE-03 chuck jaws worn, replaced")[0]
    assert cosine(original, got.vector["dense"]) > 0.9999
