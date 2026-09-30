"""The agent's tools. The model never touches application state directly:

    planner (rules or SLM)  ->  structured action {tool, args}
        -> validator (registered tool? args match the schema? risk allowed?)
        -> tool (deterministic Python)  ->  result  ->  verifier reads the state back

Risk levels: read (free), write (allowed, audited, idempotent), destructive (needs the user's
explicit confirmation). Deleting is never a tool: cancelling a task writes a new version and
keeps the old one ("superseded, not deleted").
"""
import time
from datetime import datetime
from typing import Callable, Optional

from pydantic import BaseModel, Field

from qdrant_edge import FieldCondition, Filter, MatchValue

from ..common.schema import AGORA, HERMES, KRYPTA, NoteIn
from . import decisions as dec
from .extract import slugify
from .timeparse import human, parse_due


# ---- argument schemas (the validator) ------------------------------------------------
class SearchArgs(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    k: int = Field(default=5, ge=1, le=20)


class TaskArgs(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    subject: Optional[str] = None
    due: Optional[float] = None          # unix seconds, already parsed
    reminder: bool = False


class ReminderArgs(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    when: str = Field(min_length=2, max_length=100)       # natural phrase, parsed by the tool
    subject: Optional[str] = None


class UpdateTaskArgs(BaseModel):
    match: str = Field(min_length=2, max_length=200)      # task id or words from the title
    status: Optional[str] = Field(default=None, pattern="^(open|done|cancelled)$")
    due: Optional[float] = None


class ListTasksArgs(BaseModel):
    status: Optional[str] = Field(default="open", pattern="^(open|done|cancelled|all)$")
    subject: Optional[str] = None


class StoreArgs(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    kind: str = Field(default="note", pattern="^(decision|fact|preference|event|note)$")
    memory_type: str = Field(default="episodic", pattern="^(episodic|semantic|procedural)$")
    subject: Optional[str] = None
    slot: Optional[str] = None
    importance: float = Field(default=0.4, ge=0, le=1)
    confidence: float = Field(default=0.7, ge=0, le=1)
    entities: list[str] = []
    tags: list[str] = []
    fields: dict = {}


class SubjectArgs(BaseModel):
    subject: str = Field(min_length=2, max_length=80)


class NoArgs(BaseModel):
    pass


class Tool:
    def __init__(self, name: str, desc: str, risk: str, args: type[BaseModel], fn: Callable):
        self.name, self.desc, self.risk, self.args, self.fn = name, desc, risk, args, fn

    def spec(self) -> dict:
        return {"name": self.name, "description": self.desc, "risk": self.risk,
                "args": self.args.model_json_schema().get("properties", {})}


# ---- task helpers -----------------------------------------------------------------
def task_versions(c) -> list[dict]:
    """Every live (not superseded) task version on this device, newest last."""
    flt = Filter(must=[FieldCondition(key="kind", match=MatchValue(value="task"))],
                 must_not=[FieldCondition(key="status", match=MatchValue(value="superseded"))])
    out = []
    for shard in (KRYPTA, HERMES, AGORA):
        out += [{"shard": shard, **r.payload} for r in c.dev.store.scroll(shard, flt)]
    out.sort(key=lambda p: (p.get("valid_from") or 0, p["op_id"]))
    return out


def current_tasks(c) -> list[dict]:
    """One row per task: the newest live version. A contested task shows all live versions."""
    by: dict[tuple, list[dict]] = {}
    for p in task_versions(c):
        by.setdefault((p.get("subject"), p.get("task_id")), []).append(p)
    rows = []
    for versions in by.values():
        contested = [v for v in versions if v.get("status") == "contested"]
        if contested:
            for v in contested:
                rows.append({**v, "conflict": True})
        else:
            rows.append({**versions[-1], "conflict": False})
    return rows


def find_task(c, match: str) -> dict | None:
    rows = current_tasks(c)
    m = slugify(match)
    for r in rows:
        if r.get("task_id") == m:
            return r
    words = set(m.split("-")) - {"the", "a", "my", "task", "to", "of"}
    best, best_n = None, 0
    for r in rows:
        n = len(words & set((r.get("task_id") or "").split("-")))
        if n > best_n:
            best, best_n = r, n
    return best if best_n and best_n >= max(1, len(words) // 2) else None


def _task_text(title: str, status: str, due: float | None) -> str:
    head = {"open": "TODO", "done": "DONE", "cancelled": "CANCELLED"}[status]
    return f"{head}: {title}" + (f" (due {human(due)})" if due and status == "open" else "")


def _write(c, note: NoteIn) -> dict:
    note.source = note.source or "agent"
    note.ts = c.clock()
    ctx = c.ctx()
    if ctx.get("request_id"):
        note.fields = {"request_id": ctx["request_id"], **note.fields}
    if ctx.get("context_ops") and "derived_from" not in note.fields:
        note.fields = {**note.fields, "derived_from": ctx["context_ops"]}
    out = c.dev.add_note(note)
    c.remember_subject(note.machine)
    m = out["memory"]
    return {"ok": out["decision"]["residency"] != "drop", "op_id": m["op_id"], "shard": out["shard"],
            "residency": out["decision"]["residency"], "reason": out["decision"]["reason"],
            "entity_key": m.get("entity_key"), "text": m["text"]}


# ---- tools ----------------------------------------------------------------------------
def t_search_memory(c, a: SearchArgs) -> dict:
    r = c.recall(a.query, a.k)
    return {"ok": True, "count": len(r["hits"]),
            "message": f"{len(r['hits'])} memories found", "hits": [
                {"op_id": h["payload"]["op_id"], "text": h["payload"]["text"], "score": h["score"]} for h in r["hits"]]}


def default_subject(c, text: str) -> str | None:
    """Which project/course does this belong to? The subject of the closest memory if it is
    clearly related, else the one the user last named."""
    try:
        r = c.recall(text, 1)
        if r["hits"] and r["hits"][0]["features"]["semantic"] > 0.6 and r["hits"][0]["payload"].get("subject"):
            return r["hits"][0]["payload"]["subject"]
    except Exception:  # noqa: BLE001
        pass
    return None


def t_create_task(c, a: TaskArgs) -> dict:
    tid = slugify(a.title)
    existing = find_task(c, tid)
    if existing and existing.get("task_id") == tid and existing.get("task_status") == "open" and not existing.get("conflict"):
        if a.due and a.due != existing.get("due"):        # "remind me ..." about a task that exists: set its time
            r = t_update_task(c, UpdateTaskArgs(match=tid, due=a.due))
            r["message"] = f"'{a.title}' was already a task; its due time is now {human(a.due)}"
            return r
        return {"ok": True, "noop": True, "op_id": existing["op_id"], "shard": existing["shard"],
                "message": f"'{a.title}' is already on your list"}
    subject = a.subject or default_subject(c, a.title)
    out = _write(c, NoteIn(
        text=_task_text(a.title, "open", a.due), kind="task", machine=subject, memory_type="episodic",
        slot=f"task:{tid}", importance=0.7 if a.due else 0.5, confidence=0.9, tags=["task"] + (["reminder"] if a.reminder else []),
        fields={"title": a.title, "task_id": tid, "task_status": "open", "due": a.due, "reminder": a.reminder}))
    out["message"] = f"Task added: {a.title}" + (f", due {human(a.due)}" if a.due else "")
    out["task_id"] = tid
    return out


def t_set_reminder(c, a: ReminderArgs) -> dict:
    due = parse_due(a.when, datetime.fromtimestamp(c.clock()))
    if due is None:
        r = t_create_task(c, TaskArgs(title=a.title, subject=a.subject, reminder=True))
        r["message"] += " (I couldn't work out a time from that, so no reminder time is set)"
        return r
    r = t_create_task(c, TaskArgs(title=a.title, subject=a.subject, due=due, reminder=True))
    r["message"] = f"Reminder set: {a.title} at {human(due)}"
    return r


def t_update_task(c, a: UpdateTaskArgs) -> dict:
    cur = find_task(c, a.match)
    if not cur:
        return {"ok": False, "message": f"I couldn't find a task matching '{a.match}'"}
    status = a.status or cur.get("task_status", "open")
    due = a.due if a.due is not None else cur.get("due")
    title = cur.get("title") or a.match
    out = _write(c, NoteIn(
        text=_task_text(title, status, due), kind="task", machine=cur.get("subject"), memory_type="episodic",
        slot=f"task:{cur['task_id']}", importance=cur.get("importance") or 0.5, confidence=0.9, tags=["task"],
        fields={"title": title, "task_id": cur["task_id"], "task_status": status, "due": due,
                "reminder": cur.get("reminder", False)}))
    out["task_id"] = cur["task_id"]
    out["message"] = {"done": f"Marked done: {title}", "cancelled": f"Cancelled: {title}",
                      "open": f"Updated: {title}" + (f", due {human(due)}" if due else "")}[status]
    return out


def t_cancel_task(c, a: UpdateTaskArgs) -> dict:
    return t_update_task(c, UpdateTaskArgs(match=a.match, status="cancelled"))


def t_list_tasks(c, a: ListTasksArgs) -> dict:
    rows = current_tasks(c)
    if a.subject:
        rows = [r for r in rows if r.get("subject") == a.subject]
    if a.status != "all":
        rows = [r for r in rows if r.get("task_status", "open") == a.status]
    rows.sort(key=lambda r: (r.get("due") is None, r.get("due") or 0))
    tasks = [{"task_id": r["task_id"], "title": r.get("title"), "status": r.get("task_status", "open"),
              "due": r.get("due"), "subject": r.get("subject"), "conflict": r["conflict"], "op_id": r["op_id"]} for r in rows]
    if not tasks:
        return {"ok": True, "tasks": [], "message": "No matching tasks."}
    lines = [f"{t['title']}" + (f" (due {human(t['due'])})" if t["due"] else "") + (" [conflict]" if t["conflict"] else "")
             for t in tasks]
    return {"ok": True, "tasks": tasks, "message": f"{len(tasks)} task(s): " + "; ".join(lines)}


def t_store_memory(c, a: StoreArgs) -> dict:
    subject = a.subject or default_subject(c, a.text)
    pend = dec.detect(c, a, subject)
    if pend:                      # a decision that contradicts a live one is held, never written over it
        v = dec.hold(c, pend)
        return {"ok": True, "contradiction": v, "message": "Conflicting memory: " + v["question"]}
    out = _write(c, NoteIn(text=a.text, kind=a.kind, machine=subject, memory_type=a.memory_type, slot=a.slot,
                           importance=a.importance, confidence=a.confidence, entities=a.entities, tags=a.tags,
                           fields=a.fields, source="conversation"))
    label = {"private": "kept private on this device (Krypta)", "sync": "saved and queued to sync",
             "drop": "not saved (near-duplicate or idle chat)"}[out["residency"]]
    out["message"] = f"Remembered ({a.kind}): {label}"
    return out


def t_summarize_project(c, a: SubjectArgs) -> dict:
    flt = Filter(must=[FieldCondition(key="machine", match=MatchValue(value=a.subject))],
                 must_not=[FieldCondition(key="status", match=MatchValue(value="superseded"))])
    mems = []
    for shard in (KRYPTA, HERMES, AGORA):
        mems += [{"shard": shard, **r.payload} for r in c.dev.store.scroll(shard, flt)]
    if not mems:
        return {"ok": True, "message": f"I have nothing stored for '{a.subject}' yet."}
    dec = [m["text"].split(" Original:")[0] for m in mems if m["kind"] == "decision"]
    open_t = [m for m in mems if m["kind"] == "task" and m.get("task_status", "open") == "open"]
    done_t = [m for m in mems if m["kind"] == "task" and m.get("task_status") == "done"]
    facts = [m["text"] for m in mems if m["kind"] in ("fact", "preference")][:4]
    parts = [f"{len(mems)} memories about {a.subject}."]
    if dec:
        parts.append("Decisions: " + " ".join(dec))
    if facts:
        parts.append("Facts: " + "; ".join(facts))
    parts.append(f"Tasks: {len(open_t)} open, {len(done_t)} done.")
    return {"ok": True, "message": " ".join(parts), "open": len(open_t), "done": len(done_t)}


def t_why_decision(c, a: dec.WhyArgs) -> dict:
    return dec.why_answer(c, a.query)


def t_resolve_decision(c, a: dec.ResolveDecisionArgs) -> dict:
    return dec.resolve(c, a.id, a.keep)


def t_check_connectivity(c, a: NoArgs) -> dict:
    return {"ok": True, **c.connectivity(), "message": c.connectivity()["summary"]}


def t_sync_now(c, a: NoArgs) -> dict:
    if not c.dev.online:
        return {"ok": False, "message": "Offline: the change queue is safe on this device and will sync when the link returns.",
                "queued": c.dev.db.depth()}
    if c.hermes is None:
        return {"ok": False, "message": "The sync worker is not running."}
    before = c.dev.db.depth()
    r = c.hermes.sync_once()
    return {"ok": bool(r["push"].get("ok") and r["pull"].get("ok")), "sent": r["push"].get("sent", 0),
            "pulled": r["pull"].get("pulled", 0), "queued_before": before,
            "message": f"Synced: sent {r['push'].get('sent', 0)}, pulled {r['pull'].get('pulled', 0)}"}


def build_registry() -> dict[str, Tool]:
    tools = [
        Tool("search_memory", "Search the user's memory (hybrid semantic + keyword, reranked).", "read", SearchArgs, t_search_memory),
        Tool("list_tasks", "List tasks, by default the open ones.", "read", ListTasksArgs, t_list_tasks),
        Tool("summarize_project", "Summarise decisions, facts and tasks for one project.", "read", SubjectArgs, t_summarize_project),
        Tool("check_connectivity", "Report link and gateway state.", "read", NoArgs, t_check_connectivity),
        Tool("why_decision", "Explain a recorded decision: what was chosen, why, and from what evidence.", "read", dec.WhyArgs, t_why_decision),
        Tool("resolve_decision", "Answer a pending contradiction: keep the old decision or switch to the new one (old is kept as history).",
             "write", dec.ResolveDecisionArgs, t_resolve_decision),
        Tool("store_memory", "Save something the user said as a structured memory.", "write", StoreArgs, t_store_memory),
        Tool("create_task", "Create a task (idempotent by title).", "write", TaskArgs, t_create_task),
        Tool("set_reminder", "Create a task with a due time from a phrase like 'tomorrow evening'.", "write", ReminderArgs, t_set_reminder),
        Tool("update_task", "Change a task's status or due time (writes a new version).", "write", UpdateTaskArgs, t_update_task),
        Tool("sync_now", "Push queued changes and pull fleet changes.", "write", NoArgs, t_sync_now),
        Tool("cancel_task", "Cancel a task. Needs the user's confirmation.", "destructive", UpdateTaskArgs, t_cancel_task),
    ]
    return {t.name: t for t in tools}


def verify(c, tool: str, result: dict) -> tuple[bool, str]:
    """Read the state back. A tool that says ok must be visible in the store (and queued, if it syncs)."""
    if not result.get("ok"):
        return False, "tool reported failure"
    op_id, shard = result.get("op_id"), result.get("shard")
    if not op_id or not shard:
        return True, "read-only or no write to verify"
    rec = c.dev.store.get(shard, op_id)
    if rec is None:
        return False, f"{op_id} not found in {shard}"
    if result.get("residency") == "sync" and not result.get("noop"):
        if not c.dev.db.has_op(op_id):
            return False, f"{op_id} is not in the sync outbox"
        return True, f"{op_id} stored in {shard} and in the sync outbox"
    return True, f"{op_id} stored in {shard}"
