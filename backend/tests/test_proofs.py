"""The dashboard's "Prove it" checks: each must re-run its claim and report it honestly."""
from fastapi.testclient import TestClient

from backend.common.schema import NoteIn
from backend.device.app import create_app as device_app


def test_prove_conflicts_and_convergence(gateway_client):
    c = gateway_client.get("/prove/conflicts").json()
    assert c["ok"] and c["themis_correct"] == c["cases"] == 50 and c["naive_correct"] < c["cases"]
    v = gateway_client.get("/prove/convergence", params={"runs": 20}).json()
    assert v["ok"] and v["converged"] == 20


def test_prove_idempotency_resend_is_not_stored_twice(gateway_client, gateway):
    before = gateway.stats()["points"]
    r = gateway_client.post("/prove/idempotency").json()
    assert r["ok"] and r["result"] == "duplicate"
    assert r["points_before"] == r["points_after"] == before == gateway.stats()["points"]


def test_prove_benchmarks_reads_results_or_says_how(gateway_client):
    r = gateway_client.get("/prove/benchmarks").json()
    assert "skipped" in r or "generated" in r


def test_prove_latency_runs_offline_on_device(make_device):
    a, _ = make_device("A")
    a.set_online(False)
    a.add_note(NoteIn(text="CNC-07 bearing replaced, vibration normal", kind="fix", machine="CNC-07"))
    r = TestClient(device_app(a)).get("/prove/latency", params={"n": 10}).json()
    assert r["queries"] == 10 and r["network"] == "none"
    assert 0 < r["search_p50_ms"] <= r["search_p95_ms"]
