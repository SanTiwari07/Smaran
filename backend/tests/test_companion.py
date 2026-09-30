"""Smaran as a personal companion: memory layers, retrieval, agent tools, offline use, sync, conflicts."""
import time
from datetime import datetime

from backend.common.schema import HERMES, KRYPTA
from backend.companion.extract import extract, split_tasks
from backend.companion.llm import CloudLLM, GeminiLLM, ModelRouter, build_context, ungrounded
from backend.companion.story import HISTORY, load_story
from backend.companion.timeparse import parse_due, query_window
from backend.tests.conftest import FakeLLM

NOW = datetime(2026, 9, 30, 12, 0)


# ---- extraction ---------------------------------------------------------------------
def test_extracts_decisions_tasks_and_schedule_slots():
    cands = extract("We're using PostgreSQL and Qdrant. I need to finish the API integration and write the schema. "
                    "The capstone review meeting is at 4 PM.", NOW)
    kinds = {(c.kind, c.slot) for c in cands}
    assert ("decision", "decision:database") in kinds and ("decision", "decision:vector-store") in kinds
    assert ("task", "task:finish-the-api-integration") in kinds and ("task", "task:write-the-schema") in kinds
    assert any(c.kind == "fact" and c.slot and c.slot.startswith("schedule:") for c in cands)
    assert all(0 <= c.importance <= 1 for c in cands)
    assert {c.memory_type for c in cands} == {"semantic", "episodic"}


def test_questions_and_greetings_are_not_memories():
    assert extract("What database did we choose?", NOW) == []
    assert extract("thanks", NOW) == []


def test_preferences_are_procedural():
    c = extract("I prefer studying in the morning.", NOW)[0]
    assert (c.kind, c.memory_type) == ("preference", "procedural")


def test_split_tasks():
    assert split_tasks("finish the API integration and write the schema") == ["finish the API integration", "write the schema"]
    assert split_tasks("read the rock and roll paper") == ["read the rock and roll paper"]


def test_time_parsing_is_deterministic():
    ts = parse_due("tomorrow evening", NOW)
    assert datetime.fromtimestamp(ts) == datetime(2026, 10, 1, 18, 0)
    assert datetime.fromtimestamp(parse_due("in 2 days at 5 pm", NOW)) == datetime(2026, 10, 2, 17, 0)
    assert datetime.fromtimestamp(parse_due("by 12 Oct", NOW)).day == 12
    assert parse_due("no time here", NOW) is None
    lo, hi = query_window("what did we talk about last week", NOW)
    assert lo < hi < NOW.timestamp()


# ---- agent + tools ------------------------------------------------------------------------
def test_agent_remembers_then_answers_from_memory(make_companion):
    c = make_companion()
    out = c.chat("I'm working on my final-year project. We're using PostgreSQL and Qdrant. I'll handle the backend.")
    assert out["intent"] == "remember" and all(a["state"] == "executed" for a in out["actions"])
    assert all(a.get("verified") is not False for a in out["actions"])
    ans = c.chat("What did we decide about the database?")
    assert ans["intent"] == "ask" and "PostgreSQL" in ans["reply"]
    assert ans["route"]["route"] == "extractive"          # model down -> rules, still answers
    assert {s["step"] for s in ans["steps"]} >= {"perceive", "plan", "retrieve", "answer"}


def test_create_task_is_idempotent_and_updates_supersede(make_companion):
    c = make_companion()
    c.chat("Add task: write the unit tests")
    again = c.chat("Add task: write the unit tests")
    assert "already on your list" in again["reply"]
    assert len(c.tasks()) == 1
    c.chat("Mark the unit tests as done")
    t = c.tasks()
    assert len(t) == 1 and t[0]["status"] == "done"
    # the old version is kept, marked superseded (not deleted)
    versions = [r.payload for r in c.dev.store.scroll(HERMES) if r.payload.get("task_id") == "write-the-unit-tests"]
    assert sorted(v["status"] for v in versions) == ["current", "superseded"]


def test_request_id_makes_a_retried_request_a_noop(make_companion):
    c = make_companion()
    a = c.chat("I need to buy a notebook", request_id="req-1")
    n = len(c.dev.db.pending())
    b = c.chat("I need to buy a notebook", request_id="req-1")
    assert len(c.dev.db.pending()) == n and any(x["state"] == "duplicate" for x in b["actions"])
    assert a["actions"][0]["state"] == "executed"


def test_validator_blocks_bad_actions(make_companion):
    c = make_companion()
    assert c.run_action("drop_database", {}, "i1", "r")["state"] == "blocked"
    r = c.run_action("create_task", {"title": "x"}, "i2", "r")
    assert r["state"] == "blocked" and "title" in r["message"]
    assert c.run_action("store_memory", {"text": "hello there", "kind": "status"}, "i3", "r")["state"] == "blocked"


def test_destructive_action_needs_confirmation(make_companion):
    c = make_companion()
    c.chat("Add task: renew library card")
    out = c.chat("Cancel the task renew library card")
    a = out["actions"][0]
    assert a["state"] == "pending_confirmation" and c.tasks()[0]["status"] == "open"
    done = c.confirm(a["audit_id"])
    assert done["state"] == "executed" and c.tasks()[0]["status"] == "cancelled"
    assert c.confirm(a["audit_id"])["state"] == "blocked"          # cannot confirm twice


def test_audit_log_records_every_action_with_verification(make_companion):
    c = make_companion()
    c.chat("Remind me tomorrow evening to finish the API integration")
    rows = c.audit()
    assert rows[0]["tool"] == "set_reminder" and rows[0]["verified"] == 1 and rows[0]["op_ids"]
    t = c.tasks()[0]
    assert datetime.fromtimestamp(t["due"]).hour == 18


def test_slm_planner_output_is_validated_not_trusted(make_companion):
    good = FakeLLM(reply='{"tool": "create_task", "args": {"title": "renew passport photos"}}')
    c = make_companion(local=good)
    out = c.chat("Schedule renew passport photos")
    assert out["planner"] == "local-slm" and out["actions"][0]["state"] == "executed"
    evil = FakeLLM(reply='{"tool": "delete_everything", "args": {}}')
    c2 = make_companion("B", local=evil)
    out = c2.chat("Schedule something odd")
    assert out["actions"][0]["state"] == "blocked"


# ---- offline ------------------------------------------------------------------------------
class NoNetwork:
    def __getattr__(self, name):
        def boom(*a, **k):
            raise ConnectionError("network is off")
        return boom


def test_everything_core_works_offline_with_no_network_at_all(make_companion):
    c = make_companion(http=NoNetwork())
    c.dev.set_online(False)
    c.chat("We're using PostgreSQL for the project database.")
    c.chat("Remind me tomorrow evening to finish the API integration")
    assert c.dev.db.depth() >= 2
    assert "PostgreSQL" in c.chat("Which database are we using?")["reply"]
    assert any("API integration" in t["title"] for t in c.tasks())
    assert c.chat("am I online?")["reply"].startswith("Offline")
    assert "Offline" in c.chat("sync now")["reply"]                    # honest, queue kept
    assert c.dev.db.depth() >= 2


def test_memory_survives_restart_while_offline(make_companion, tmp_path, embedder):
    from backend.common.log import Log
    from backend.companion.service import Companion
    from backend.device.classifier import PersonalClassifier
    from backend.device.core import Device
    c = make_companion(http=NoNetwork())
    c.dev.set_online(False)
    c.chat("We decided to use FastAPI for the backend.")
    c.chat("Remind me tomorrow morning to email the mentor")
    root = c.dev.root
    c.dev.close()
    d2 = Device("A", root, embedder, PersonalClassifier(), http=NoNetwork(), log=Log("re", tmp_path / "logs"))
    try:
        c2 = Companion(d2, None, ModelRouter(local=FakeLLM(fail=True), cloud=CloudLLM(), online=lambda: d2.online))
        assert not d2.online and d2.db.depth() == 2
        assert "FastAPI" in c2.chat("what backend framework did we pick?")["reply"]
        assert c2.tasks()[0]["title"] == "email the mentor"
        assert len(c2.chat_history()) >= 4 and len(c2.audit()) == 2
    finally:
        d2.close()


# ---- privacy ------------------------------------------------------------------------------
def test_sensitive_text_stays_in_krypta_and_chat_is_encrypted(make_companion, campus_gateway):
    c = make_companion()
    out = c.chat("Call Riya on 9876543210 about the Goa trip.")
    assert out["actions"][0]["residency"] == "private" and out["actions"][0]["shard"] == KRYPTA
    c.chat("My salary discussion with the manager is on Monday.")
    c.hermes.sync_once()
    assert campus_gateway.audit()["ok"] is True
    assert c.dev.db.depth() == 0
    raw = c.dev.db.conn.execute("SELECT text FROM chat").fetchall()
    assert raw and all(r[0].startswith("enc1:") for r in raw) and "9876543210" not in str(raw)
    assert "9876543210" in c.chat_history()[0]["text"]                 # readable through the vault
    assert c.audit()[-1]["args"]["text"].startswith("Call Riya")


def test_private_memory_never_goes_to_the_cloud(make_companion):
    cloud = FakeLLM(reply="cloud answer [1]", model="cloud-x")
    c = make_companion(local=FakeLLM(fail=True), cloud=cloud)
    c.chat("Call Riya on 9876543210 about the Goa trip.")
    out = c.chat("Who do I need to call about the trip?", prefer_cloud=True)
    assert out["route"]["route"] == "extractive" and cloud.calls == []
    assert "private memory" in out["route"]["reason"]


# ---- model router ---------------------------------------------------------------------------
def _hits(text, shard="hermes"):
    return [{"payload": {"text": text, "kind": "fact", "valid_from": time.time(), "op_id": "x"}, "shard": shard, "score": 0.9}]


def test_router_prefers_local_then_falls_back():
    local = FakeLLM(reply="Answer from local [1]")
    r = ModelRouter(local=local, cloud=CloudLLM(), online=lambda: True)
    text, route = r.answer("q", _hits("fact one"))
    assert route.route == "local-slm" and route.model == "fake-slm" and text.startswith("Answer")
    local.fail = True
    text, route = r.answer("q", _hits("fact one"))
    assert route.route == "extractive" and route.tried[0]["route"] == "local-slm" and "fact one" in text


def test_cloud_is_used_only_when_configured_online_and_allowed():
    cloud = FakeLLM(reply="cloud says [1]", model="cloud-x")
    r = ModelRouter(local=FakeLLM(fail=True), cloud=cloud, online=lambda: True)
    assert r.answer("q", _hits("fact"), prefer_cloud=True)[1].route == "cloud"
    r2 = ModelRouter(local=FakeLLM(fail=True), cloud=cloud, online=lambda: False)     # offline
    assert r2.answer("q", _hits("fact"), prefer_cloud=True)[1].route == "extractive"
    assert ModelRouter(local=FakeLLM(), cloud=cloud, online=lambda: True).answer("q", _hits("f"))[1].route == "local-slm"
    assert ModelRouter(local=FakeLLM(), cloud=CloudLLM(), online=lambda: True).status()["cloud"]["configured"] is False


def test_gemini_is_used_when_configured_online_and_allowed():
    gemini = FakeLLM(reply="Gemini says [1]", model="gemini-2.0-flash")
    r = ModelRouter(local=FakeLLM(fail=True), cloud=CloudLLM(), gemini=gemini, online=lambda: True)
    assert r.answer("q", _hits("fact"), prefer_cloud=True)[1].route == "gemini"
    assert r.answer("q", _hits("fact"), provider="gemini")[1].route == "gemini"

    # offline fallback
    r_offline = ModelRouter(local=FakeLLM(fail=True), cloud=CloudLLM(), gemini=gemini, online=lambda: False)
    assert r_offline.answer("q", _hits("fact"), prefer_cloud=True)[1].route == "extractive"

    # private (Krypta) memory invariant: Gemini is blocked
    r_private = ModelRouter(local=FakeLLM(fail=True), cloud=CloudLLM(), gemini=gemini, online=lambda: True)
    out, route = r_private.answer("q", _hits("confidential", shard="krypta"), prefer_cloud=True)
    assert route.route == "extractive"
    assert "private memory" in route.reason

    # unconfigured gemini
    assert ModelRouter(local=FakeLLM(), cloud=CloudLLM(), gemini=GeminiLLM(api_key=""), online=lambda: True).status()["gemini"]["configured"] is False


def test_gemini_llm_client_mock():
    import httpx

    # Test OpenAI-compatible format handling
    def handler(request: httpx.Request):
        if "openai" in str(request.url):
            return httpx.Response(200, json={"choices": [{"message": {"content": "Answer from Gemini OpenAI compat"}}]})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Answer from Gemini REST"}]}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    llm = GeminiLLM(api_key="test-key-123", client=client)
    assert llm.available() is True
    res = llm.chat([{"role": "user", "content": "hello"}])
    assert "Gemini" in res

    # Test native REST fallback
    def rest_only_handler(request: httpx.Request):
        if "openai" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Native Gemini answer"}]}}]})

    client2 = httpx.Client(transport=httpx.MockTransport(rest_only_handler))
    llm2 = GeminiLLM(api_key="test-key-123", client=client2)
    res2 = llm2.chat([{"role": "user", "content": "hello"}])
    assert res2 == "Native Gemini answer"


def test_grounding_check_rejects_invented_citations():
    assert ungrounded("It is 4 PM [3]", 1, []) is not None
    assert ungrounded("It is 4 PM [1]", 1, []) is None
    r = ModelRouter(local=FakeLLM(reply="Use MySQL [7]"), cloud=CloudLLM(), online=lambda: False)
    text, route = r.answer("q", _hits("We use PostgreSQL"))
    assert route.route == "extractive" and "PostgreSQL" in text and "grounding" in route.tried[0]["error"]


def test_context_is_budgeted():
    hits = _hits("word " * 100) * 30
    ctx, used = build_context(hits, budget=1400)
    assert len(ctx) < 1700 and 1 <= len(used) < 30


# ---- sync, two devices, conflicts ----------------------------------------------------------
def test_two_devices_conflict_is_detected_explained_and_resolved(make_companion, campus_client):
    phone, laptop = make_companion("A"), make_companion("B")
    phone.chat("The capstone review meeting is at 3 PM.")
    phone.hermes.sync_once(), laptop.hermes.sync_once()
    for c in (phone, laptop):
        c.dev.set_online(False)
    t = time.time()
    phone.clock = lambda: t + 1
    laptop.clock = lambda: t + 60
    phone.chat("The capstone review meeting is at 4 PM.")
    laptop.chat("The capstone review meeting is at 5 PM.")
    for c in (phone, laptop):
        c.dev.set_online(True)
        c.hermes.sync_once()
    phone.hermes.sync_once()
    conflicts = phone.conflicts()
    assert len(conflicts) == 1
    cf = conflicts[0]
    assert {v["device_label"] for v in cf["versions"]} == {"Phone", "Laptop"}
    assert "5 PM" in cf["suggestion"]["text"] and "suggestion only" in cf["suggestion"]["reason"]
    assert "concurrent" in cf["why"]
    assert "conflicting versions exist" in phone.chat("when is the capstone review meeting?")["reply"]
    # nothing was silently dropped: both versions are still live on the server
    assert len(campus_client.get("/contested").json()[0]["versions"]) == 2
    keep = next(v for v in cf["versions"] if "5 PM" in v["text"])["op_id"]
    r = campus_client.post("/resolve", json={"entity_key": cf["entity_key"], "op_id": keep}).json()
    assert r["result"] in ("applied", "stale")
    for c in (phone, laptop):
        c.hermes.sync_once()
        assert c.conflicts() == []
    assert "5 PM" in phone.chat("when is the capstone review meeting?")["reply"]


def test_task_edited_on_two_devices_offline_becomes_a_task_conflict(make_companion):
    phone, laptop = make_companion("A"), make_companion("B")
    phone.chat("Add task: submit the DBMS assignment")
    phone.hermes.sync_once(), laptop.hermes.sync_once()
    for c in (phone, laptop):
        c.dev.set_online(False)
    phone.chat("Mark the DBMS assignment as done")
    laptop.chat("Cancel the task submit the DBMS assignment")
    laptop.confirm(laptop.audit()[0]["id"])
    for c in (phone, laptop):
        c.dev.set_online(True)
    for _ in range(2):
        phone.hermes.sync_once(), laptop.hermes.sync_once()
    assert phone.tasks()[0]["conflict"] and len(phone.tasks()) == 2
    assert phone.briefing()["items"][0]["level"] == "warn"


def test_reconnect_pushes_pulls_and_is_idempotent(make_companion, campus_gateway):
    c = make_companion()
    c.dev.set_online(False)
    for s in ("We decided to use MySQL for the project.", "I need to write the report.", "The lab viva is at 2 PM."):
        c.chat(s)
    q = c.dev.db.depth()
    assert q >= 3
    c.dev.set_online(True)
    first = c.hermes.sync_once()
    assert first["push"]["sent"] == q and c.dev.db.depth() == 0
    pts = campus_gateway.stats()["points"]
    c.dev.db.conn.execute("UPDATE outbox SET state='pending'")             # replay everything
    assert set(c.hermes.sync_once()["push"]["results"]) == {"duplicate"}
    assert campus_gateway.stats()["points"] == pts


# ---- story + scale -----------------------------------------------------------------------------
def test_story_history_loads_through_the_real_pipeline(make_companion):
    c = make_companion()
    r = load_story(c)
    assert r["utterances"] == len(HISTORY) and r["memories_written"] >= 15 and r["private"] == 2
    assert {t["title"] for t in c.tasks()} >= {"finish the API integration", "write the database schema"}
    kinds = c.status()["memory"]["by_type"]
    assert kinds["episodic"] and kinds["semantic"] and kinds["procedural"]
    assert c.briefing()["open_tasks"] >= 3


def test_retrieval_stays_fast_with_a_large_memory(make_companion):
    c = make_companion()
    from backend.common.schema import NoteIn
    for i in range(600):
        c.dev.add_note(NoteIn(text=f"Lecture note {i}: topic {i % 37} covers subject {i % 11} and example {i}",
                              kind="event", subject=f"course-{i % 5}"))
    c.dev.add_note(NoteIn(text="We decided to use PostgreSQL as the database", kind="decision", subject="capstone",
                          slot="decision:database"))
    t0 = time.perf_counter()
    r = c.recall("which database did we decide on", 3)
    assert (time.perf_counter() - t0) < 1.0
    assert "PostgreSQL" in r["hits"][0]["payload"]["text"]


def test_a_summary_that_drops_a_task_is_rejected_for_the_exact_list():
    r = ModelRouter(local=FakeLLM(reply="You have one task: write the schema."), cloud=CloudLLM(), online=lambda: False)
    extra = "2 task(s): write the schema; email the mentor"
    text, route = r.answer("what is left", _hits("x"), extra=extra, cover=["write the schema", "email the mentor"])
    assert route.route == "extractive" and text == extra and "leaves out" in route.tried[0]["error"]
    ok = ModelRouter(local=FakeLLM(reply="Write the schema, and email the mentor."), cloud=CloudLLM(), online=lambda: False)
    assert ok.answer("what is left", _hits("x"), extra=extra, cover=["write the schema", "email the mentor"])[1].route == "local-slm"


def test_semantic_retrieval_with_the_real_embedder_needs_no_shared_keywords(tmp_path):
    import shutil

    import pytest

    from backend.common.log import Log
    from backend.companion.service import Companion
    from backend.device.classifier import PersonalClassifier
    from backend.device.core import Device
    from backend.device.embed import get_embedder
    try:
        emb = get_embedder("fastembed")
    except RuntimeError:
        pytest.skip("embedding model not downloaded (python scripts/setup_models.py)")
    dev = Device("A", tmp_path / "sem", emb, PersonalClassifier(), http=None, log=Log("sem", tmp_path / "logs"))
    try:
        c = Companion(dev, None, ModelRouter(local=FakeLLM(fail=True), cloud=CloudLLM(), online=lambda: False))
        c.chat("We're using PostgreSQL and Qdrant for the final-year project.")
        c.chat("Today's operating systems lecture was about CPU scheduling and round robin.")
        c.chat("I prefer studying in the morning.")
        top = c.recall("Which DB are we going with for the capstone?", 1, allow_cloud=False)["hits"][0]["payload"]["text"]
        assert "PostgreSQL" in top                      # 'DB' and 'capstone' appear nowhere in the memory
        assert "round robin" in c.recall("which algorithms did the OS class cover", 1, allow_cloud=False)["hits"][0]["payload"]["text"]
    finally:
        dev.close()
        shutil.rmtree(tmp_path / "sem", ignore_errors=True)
