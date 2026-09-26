"""The PS3 story end to end: offline memory, privacy, sync, conflicts, resolution, history."""
import time

from backend.common.schema import AGORA, HERMES, KRYPTA, NoteIn


def status_of(dev, op_id):
    for shard in (HERMES, AGORA):
        r = dev.store.get(shard, op_id)
        if r:
            return r.payload["status"]
    return None


def test_offline_write_and_search(make_device):
    a, _ = make_device("A")
    a.set_online(False)
    out = a.add_note(NoteIn(text="CNC-07 bearing replaced, vibration normal", kind="fix", machine="CNC-07"))
    assert out["shard"] == HERMES and a.db.depth() == 1
    res = a.search("CNC-07 bearing")
    assert res["answered"] == "local"
    assert res["results"][0]["payload"]["op_id"] == out["memory"]["op_id"]


def test_pii_stays_private_and_never_reaches_server(make_device, gateway):
    a, h = make_device("A")
    out = a.add_note(NoteIn(text="Call Ravi on 9876543210 about night shift", kind="observation"))
    assert out["shard"] == KRYPTA and out["decision"]["by"] == "pii_rule"
    assert a.db.depth() == 0
    h.sync_once()
    assert gateway.audit()["ok"] is True


def test_gateway_rejects_private_payload_defence_in_depth(gateway_client):
    body = {"device_id": "X", "ops": [{"op_id": "X-1", "vectors": {"dense": [0.0] * 384, "bm25": {"indices": [], "values": []}},
                                       "payload": {"op_id": "X-1", "text": "call 9876543210", "residency": "sync"}}]}
    r = gateway_client.post("/sync", json=body).json()
    assert r["results"][0]["result"] == "rejected"


def test_sync_is_idempotent(make_device, gateway):
    a, h = make_device("A")
    a.add_note(NoteIn(text="LATHE-03 chuck jaws worn, replaced", kind="fix", machine="LATHE-03"))
    h.sync_once()
    before = gateway.stats()["points"]
    a.db.conn.execute("UPDATE outbox SET state='pending'")   # simulate a crash before the ack
    assert h.sync_once()["push"]["results"] == {"duplicate": 1}
    assert gateway.stats()["points"] == before


def test_critical_first(make_device):
    a, _ = make_device("A")
    a.set_online(False)
    a.add_note(NoteIn(text="CNC-12 cleaned chips from the tray", kind="observation", machine="CNC-12"))
    a.add_note(NoteIn(text="PRESS-02 smoke and sparks from the motor", kind="observation", machine="PRESS-02"))
    first = a.db.due(10)[0][1]["payload"]
    assert first["criticality"] == 2 and "smoke" in first["text"]


def test_conflict_contested_then_resolved_everywhere(make_device, gateway, gateway_client):
    a, ha = make_device("A")
    b, hb = make_device("B")
    ha.sync_once(); hb.sync_once()                               # both mirror the fleet baseline
    a.set_online(False); b.set_online(False)
    ra = a.add_note(NoteIn(text="CNC-07 running normally after bearing change", kind="status", machine="CNC-07"))
    rb = b.add_note(NoteIn(text="CNC-07 still vibrating at high RPM", kind="status", machine="CNC-07"))
    # each device supersedes the baseline locally and believes its own version
    assert status_of(a, ra["memory"]["op_id"]) == "current"
    assert status_of(b, rb["memory"]["op_id"]) == "current"

    a.set_online(True); b.set_online(True)
    ha.sync_once(); hb.sync_once(); ha.sync_once()
    for dev in (a, b):
        assert status_of(dev, ra["memory"]["op_id"]) == "contested"
        assert status_of(dev, rb["memory"]["op_id"]) == "contested"
    assert [g["entity_key"] for g in gateway.contested()] == ["machine:CNC-07/status"]

    r = gateway_client.post("/resolve", json={"entity_key": "machine:CNC-07/status", "op_id": rb["memory"]["op_id"]}).json()
    ha.sync_once(); hb.sync_once()
    for dev in (a, b):
        assert status_of(dev, r["op_id"]) == "current"
        assert status_of(dev, ra["memory"]["op_id"]) == "superseded"
    assert gateway.contested() == []


def test_history_what_device_believed(make_device):
    a, _ = make_device("A")
    a.set_online(False)
    r1 = a.add_note(NoteIn(text="PRESS-02 pressure low", kind="status", machine="PRESS-02"))
    t_between = time.time()
    time.sleep(0.01)
    r2 = a.add_note(NoteIn(text="PRESS-02 pressure back to 180 bar", kind="status", machine="PRESS-02"))
    then = {g["entity_key"]: g for g in a.history(t_between)}
    now = {g["entity_key"]: g for g in a.history(time.time())}
    ek = "machine:PRESS-02/status"
    assert [v["op_id"] for v in then[ek]["versions"]] == [r1["memory"]["op_id"]]
    assert [v["op_id"] for v in now[ek]["versions"]] == [r2["memory"]["op_id"]]


def test_crash_recovery_replays_outbox(make_device, tmp_path, embedder):
    a, _ = make_device("A")
    a.set_online(False)
    out = a.add_note(NoteIn(text="ROBOT-ARM-5 gripper leaking air", kind="observation", machine="ROBOT-ARM-5"))
    op_id = out["memory"]["op_id"]
    a.store.delete(HERMES, op_id)                  # simulate: outbox written, shard write lost
    a.recover()
    assert a.store.get(HERMES, op_id) is not None
    rec = a.state()["recovery"]
    assert rec["pending"] == 1 and rec["restored"] == 1


def test_unclean_shutdown_rebuilds_krypta_and_agora(make_device):
    """Edge keeps recent writes in memory: a hard crash can lose them. SQLite is the log."""
    a, h = make_device("A")
    h.sync_once()
    fleet = a.store.count(AGORA)
    assert fleet > 0
    private = a.add_note(NoteIn(text="Call Ravi on 9876543210 about the night shift swap"))["memory"]["op_id"]
    # simulate the crash: the unflushed shard writes are gone, SQLite (seq, journal) is not
    a.store.clear()
    assert a.db.get("clean_shutdown") is False            # still running, so not a clean stop
    a.recover()
    assert a.store.get(KRYPTA, private) is not None       # replayed from the local journal
    assert a.state()["recovery"]["clean"] is False and a.db.get("last_server_seq") == 0
    h.sync_once()                                          # re-pulls the change feed
    assert a.store.count(AGORA) == fleet


def test_clean_shutdown_keeps_the_feed_position(make_device, tmp_path, embedder):
    from backend.common.log import Log
    from backend.device.classifier import KeywordClassifier
    from backend.device.core import Device
    a, h = make_device("A")
    h.sync_once()
    seq = a.db.get("last_server_seq")
    a.close()
    b = Device("A", a.root, embedder, KeywordClassifier(), log=Log("reopen", tmp_path / "logs"))
    try:
        assert b.recovery["clean"] is True and b.db.get("last_server_seq") == seq
        assert b.store.count(AGORA) > 0
    finally:
        b.close()


def test_crash_after_gateway_stored_resends_without_duplicates(make_device, gateway):
    """The worst crash point: the gateway stored the batch, the device never recorded the ack."""
    a, h = make_device("A")
    a.set_online(False)
    ops = [a.add_note(NoteIn(text=t, kind="observation", machine="CNC-12"))["memory"]["op_id"]
           for t in ("CNC-12 coolant low, topped up", "CNC-12 chips under the conveyor, cleared",
                     "CNC-12 spindle drive fan cleaned")]
    before = gateway.stats()["points"]
    h.push()                                                # gateway stores all three...
    a.db.conn.execute("UPDATE outbox SET state='pending'")  # ...but the acks are lost (crash)
    a.recover()                                             # restart
    assert a.state()["recovery"]["pending"] == 3 and a.db.depth() == 3
    a.set_online(True)
    assert h.sync_once()["push"]["results"] == {"duplicate": 3}
    assert a.db.depth() == 0 and a.state()["acked"] == 3
    assert gateway.stats()["points"] == before + 3          # stored exactly once
    stats = {d["device_id"]: d for d in gateway.stats()["devices"]}
    assert stats["A"]["ops"] == 3 and stats["A"]["duplicates"] == 3
    assert {m["op_id"] for m in gateway.memories()} >= set(ops)


def test_small_shard_does_not_outrank_relevant_hit(make_device):
    """Regression: per-shard RRF merged by rank let a one-note Krypta win every query."""
    a, h = make_device("A")
    h.sync_once()                                   # Agora holds the fleet manuals
    a.add_note(NoteIn(text="Call Ravi on 9876543210 about the night shift swap"))
    fix = a.add_note(NoteIn(text="CNC-07 bearing replaced, vibration normal", kind="fix", machine="CNC-07"))
    res = a.search("CNC-07 bearing replaced")
    top3 = [r["payload"]["op_id"] for r in res["results"][:3]]
    assert fix["memory"]["op_id"] in top3
    assert "krypta" not in [r["shard"] for r in res["results"][:3]]
