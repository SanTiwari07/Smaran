"""Decision memory, contradiction detection, provenance, explain-action, lifecycle and the five-proof loop.

Every test drives the real agent loop (extraction, tools, Qdrant Edge shards, outbox); nothing is faked
except the network for the offline cases.
"""
import time
from datetime import datetime

from backend.companion import decisions as dec
from backend.companion.extract import extract
from backend.companion.lifecycle import lifecycle
from backend.companion.story import load_background

NOW = datetime(2026, 9, 30, 12, 0)
TEACH = ("I'm building Project Nova. I handle the backend, we're using FastAPI and PostgreSQL, and we chose "
         "PostgreSQL because we need relational transactions.")


def live(c, cat="database"):
    return [d for d in dec.live_decisions(c, cat)]


# ---- decision memory ---------------------------------------------------------------------------
def test_extraction_captures_decision_reason_and_subject():
    cands = {c.slot: c for c in extract(TEACH, NOW) if c.kind == "decision"}
    db = cands["decision:database"]
    assert db.subject == "project-nova" and db.fields["reason"] == "we need relational transactions"
    assert db.fields["decision_value"] == "PostgreSQL" and db.confidence == 0.9
    assert cands["decision:backend-framework"].fields["reason"] is None       # no invented reasons
    assert cands["decision:backend-framework"].confidence == 0.85
    prop = extract("I think we should use MongoDB instead.", NOW)[0]
    assert prop.kind == "decision" and prop.fields["stance"] == "proposal" and prop.confidence == 0.6


def test_decision_is_stored_with_reason_evidence_and_status(make_companion):
    c = make_companion()
    out = c.chat(TEACH)
    assert all(a["state"] == "executed" for a in out["actions"])
    d = live(c)[0]
    assert d["decision_value"] == "PostgreSQL" and d["reason"] == "we need relational transactions"
    assert d["subject"] == "project-nova" and d["status"] == "current" and d["superseded_by"] is None
    assert "relational transactions" in d["evidence"] and d["request_id"] == out["request_id"]
    rec = c.decisions()
    assert {r["value"] for r in rec} == {"PostgreSQL", "FastAPI"}


def test_why_question_answers_from_the_recorded_decision(make_companion):
    c = make_companion()
    c.chat(TEACH)
    ans = c.chat("Why did we choose PostgreSQL?")
    assert "relational transactions" in ans["reply"] and "PostgreSQL" in ans["reply"]
    assert any(a["tool"] == "why_decision" and a["state"] == "executed" for a in ans["actions"])
    p = ans["provenance"][0]
    assert p["decision"]["reason"] == "we need relational transactions" and p["source"]["type"] == "conversation"
    assert p["confidence"]["value"] == 0.96 and p["confidence"]["parts"][0]["value"] == 0.9   # 0.90 + 0.06 (supporting cap)


def test_why_says_so_when_there_is_no_recorded_reason(make_companion):
    c = make_companion()
    c.chat("We decided to use FastAPI for the backend.")
    ans = c.chat("Why did we choose FastAPI?")
    assert "no recorded reason" in ans["reply"]
    assert "Nothing" not in ans["reply"] and "relational" not in ans["reply"]


# ---- contradiction detection --------------------------------------------------------------------
def test_contradicting_decision_is_held_not_written(make_companion):
    c = make_companion()
    c.chat(TEACH)
    before = len(c.dev.memories(machine="project-nova"))
    out = c.chat("I think we should use MongoDB instead.")
    a = next(a for a in out["actions"] if a.get("contradiction"))
    cf = a["contradiction"]
    assert cf["previous"]["value"] == "PostgreSQL" and cf["new"]["value"] == "MongoDB"
    assert "Both refer to" in cf["why"] and "Conflicting memory" in out["reply"]
    assert len(c.dev.memories(machine="project-nova")) == before               # nothing written
    assert [d["decision_value"] for d in live(c)] == ["PostgreSQL"]
    assert len(out["pending"]) == 1 and a.get("verified") is None
    assert "Remembered" not in out["reply"]


def test_declining_keeps_the_old_decision(make_companion):
    c = make_companion()
    c.chat(TEACH)
    c.chat("We should move Project Nova to MongoDB.")
    out = c.chat("No, keep PostgreSQL")
    assert "Kept PostgreSQL" in out["reply"] and dec.pending(c) == []
    assert [d["decision_value"] for d in live(c)] == ["PostgreSQL"]
    assert "MongoDB" not in c.chat("Why did we choose PostgreSQL?")["reply"]


def test_confirming_supersedes_the_old_decision_and_keeps_it(make_companion):
    c = make_companion()
    c.chat(TEACH)
    c.chat("We should move Project Nova to MongoDB.")
    out = c.chat("Yes, the decision has changed")
    assert "Switched" in out["reply"] and dec.pending(c) == []
    every = [d for d in dec.all_decisions(c) if d.get("category") == "database"]
    old, new = (next(d for d in every if d["decision_value"] == v) for v in ("PostgreSQL", "MongoDB"))
    assert old["status"] == "superseded" and old["superseded_by"] == new["op_id"]      # kept, not deleted
    assert new["status"] == "current" and new["resolution"]["mode"] == "user-confirmed"
    why = c.chat("Why did we choose MongoDB?")["reply"]
    assert "MongoDB" in why and "replaced PostgreSQL" in why
    hist = c.memory_explain(new["op_id"])["history"]
    assert [h["status"] for h in hist] == ["superseded", "current"]
    rec = next(r for r in c.decisions() if r["value"] == "MongoDB")
    assert rec["supersedes"] == [old["op_id"]]


def test_same_value_is_reaffirmation_not_contradiction(make_companion):
    c = make_companion()
    c.chat(TEACH)
    out = c.chat("We decided to use PostgreSQL for Project Nova.")
    assert not any(a.get("contradiction") for a in out["actions"]) and dec.pending(c) == []


def test_a_different_project_is_not_a_contradiction(make_companion):
    c = make_companion()
    c.chat(TEACH)
    out = c.chat("For Project Atlas we decided to use MongoDB.")
    assert not any(a.get("contradiction") for a in out["actions"])
    assert {d["subject"] for d in live(c)} == {"project-nova", "project-atlas"}


# ---- provenance ----------------------------------------------------------------------------------
def test_provenance_shows_source_confidence_parts_and_supporting_memories(make_companion):
    c = make_companion()
    c.chat(TEACH)
    d = live(c)[0]
    e = c.memory_explain(d["op_id"])
    assert e["source"]["type"] == "conversation" and e["source"]["quote"] == d["evidence"]
    assert e["decision"]["value"] == "PostgreSQL" and e["at_text"]
    assert {s["text"] for s in e["supporting"]} >= {"I handle the backend"}
    labels = [p["label"] for p in e["confidence"]["parts"]]
    assert labels[0].startswith("stored confidence") and any("supporting" in x for x in labels)
    assert e["lifecycle"]["state"] == "active"
    assert c.memory_explain("nope-000001") is None


# ---- explain this action ---------------------------------------------------------------------------
class NoNet:
    def __getattr__(self, name):
        def boom(*a, **k):
            raise ConnectionError("network is off")
        return boom


def test_explain_action_chain_offline(make_companion):
    c = make_companion(http=NoNet())
    c.chat(TEACH)
    c.dev.set_online(False)
    out = c.chat("Create a task to finish the authentication API tonight.")
    a = out["actions"][0]
    assert a["state"] == "executed" and out["online_at_start"] is False
    t = c.tasks()[0]
    assert t["title"] == "finish the authentication API" and t["subject"] == "project-nova"
    ex = c.explain(audit_id=a["audit_id"])
    stages = [s["stage"] for s in ex["chain"]]
    assert stages == ["User intent", "Relevant memory", "Agent decision", "Tool", "Result"]
    assert ex["mode"].startswith("Offline") and ex["user_request"].startswith("Create a task")
    mem = " ".join(ex["chain"][1]["items"])
    assert "Project Nova" in mem and ("backend" in mem.lower())
    assert "create_task" in ex["chain"][3]["items"][0] and "verified" in ex["chain"][4]["items"][0]
    assert ex["actions"][0]["op_ids"] and c.explain(request_id="missing") is None
    p = c.memory_explain(ex["actions"][0]["op_ids"][0])
    assert p["source"]["request_id"] == out["request_id"]


def test_explain_covers_answers_too(make_companion):
    c = make_companion()
    c.chat(TEACH)
    ans = c.chat("Why did we choose PostgreSQL?")
    ex = c.explain(request_id=ans["request_id"])
    assert ex["intent"] == "ask" and ex["actions"][0]["tool"] == "why_decision"
    assert "PostgreSQL" in ex["chain"][4]["items"][0]


# ---- lifecycle ---------------------------------------------------------------------------------
def test_lifecycle_rules_are_deterministic_and_explained():
    day = 86400
    now = 100 * day

    def p(kind, age, **kw):
        return {"kind": kind, "valid_from": now - age * day, "status": "current", **kw}
    assert lifecycle(p("event", 1), now).state == "temporary"
    assert lifecycle(p("event", 6), now).state == "active"
    assert lifecycle(p("event", 20), now).state == "stale"
    assert lifecycle(p("note", 31), now).state == "archived"
    assert lifecycle(p("task", 40, task_status="done"), now).state == "archived"
    assert lifecycle(p("task", 1, task_status="done"), now).state == "active"
    assert lifecycle(p("task", 400, task_status="open"), now).state == "active"
    assert lifecycle(p("decision", 900), now).state == "active"
    assert lifecycle(p("preference", 900), now).state == "active"
    assert lifecycle(p("fact", 400), now).state == "archived"
    assert lifecycle(p("decision", 2, status="superseded", superseded_by="X-1"), now).state == "archived"
    r = lifecycle(p("event", 20), now)
    assert "20 days old" in r.reason and r.persistence == "decays"
    sched = p("fact", 5, tags=["schedule"], due=now - 3 * day)
    assert lifecycle(sched, now).state == "stale" and lifecycle({**sched, "due": now + day}, now).state == "active"


def test_archived_memory_is_hidden_from_recall_but_not_deleted(make_companion):
    c = make_companion()
    c.chat("I prefer studying in the morning.")
    load_background(c)
    rep = c.lifecycle_report()
    assert rep["counts"]["archived"] >= 3 and rep["examples"]["archived"]
    r = c.recall("what did the networks lecture cover about the OSI model", 5)
    assert all(h["lifecycle"]["state"] != "archived" for h in r["hits"]) and r["archived_hidden"] >= 1
    assert any("OSI" in h["payload"]["text"] for h in c.recall("what did the networks lecture cover about the OSI model, previously", 5)["hits"])
    assert any("OSI" in m["text"] for m in c.dev.memories())                         # still stored
    assert c.tasks() and c.tasks()[0]["status"] == "done"


# ---- reconcile with evidence, and the whole loop -------------------------------------------------------
def test_conflict_suggestion_uses_context_evidence(make_companion, campus_client):
    phone, laptop = make_companion("A"), make_companion("B")
    phone.chat("I'm building Project Nova.")
    phone.chat("The Project Nova review meeting is at 3 PM.")
    phone.chat("The mentor said 5 PM suits the whole team because everyone is free by then.")
    phone.hermes.sync_once(), laptop.hermes.sync_once()
    for c in (phone, laptop):
        c.dev.set_online(False)
    t = time.time()
    phone.clock, laptop.clock = (lambda: t + 1), (lambda: t + 60)
    phone.chat("The Project Nova review meeting is now at 4 PM.")
    laptop.chat("The Project Nova review meeting is now at 5 PM.")
    for c in (phone, laptop):
        c.dev.set_online(True)
        c.hermes.sync_once()
    phone.hermes.sync_once()
    cf = phone.conflicts()[0]
    assert cf["suggestion"]["basis"] == "context" and "5 PM" in cf["suggestion"]["text"]
    assert "mentor" in cf["suggestion"]["reason"] and "you decide" in cf["suggestion"]["reason"]
    assert "Phone says 4 PM" in cf["explanation"] and "Laptop says 5 PM" in cf["explanation"]
    assert cf["evidence"]["support_op_id"]
    # resolve through the gateway (mission control), then the outcome becomes memory with its provenance
    keep = next(v for v in cf["versions"] if "5 PM" in v["text"])["op_id"]
    campus_client.post("/resolve", json={"entity_key": cf["entity_key"], "op_id": keep, "author": "you"})
    for c in (phone, laptop):
        c.hermes.sync_once()
    assert phone.conflicts() == []
    ans = phone.chat("When is the Project Nova review meeting?")
    assert "5 PM" in ans["reply"]
    top = next(p for p in ans["provenance"] if "5 PM" in p["text"])
    assert top["source"]["type"] == "user-confirmed resolution" and top["resolution"]["mode"] == "user-confirmed"
    assert [h["status"] for h in top["history"]].count("superseded") == 3   # 3 PM, 4 PM, 5 PM


def test_no_evidence_means_the_user_decides(make_companion):
    phone, laptop = make_companion("A"), make_companion("B")
    phone.chat("The capstone review meeting is at 3 PM.")
    phone.hermes.sync_once(), laptop.hermes.sync_once()
    for c in (phone, laptop):
        c.dev.set_online(False)
    phone.chat("The capstone review meeting is at 4 PM.")
    laptop.chat("The capstone review meeting is at 5 PM.")
    for c in (phone, laptop):
        c.dev.set_online(True)
        c.hermes.sync_once()
    phone.hermes.sync_once()
    cf = phone.conflicts()[0]
    assert cf["suggestion"]["basis"] == "clock" and "you decide" in cf["suggestion"]["reason"] and cf["evidence"] is None
