"""Decision memory and contradiction detection.

A decision is more than a retrieved sentence. Each one is stored with:

    decision_value   what was chosen ("PostgreSQL")            category   what kind of choice ("database")
    reason           why, in the user's words (or none)         evidence   the sentence it came from
    valid_from       when it was recorded                       confidence deterministic, see extract.decision_confidence
    status           current | contested | superseded            superseded_by   the decision that replaced it

A decision in the same slot (same project, same category) is checked against the live one
before it is written. If the value differs, Smaran does NOT overwrite: it holds the new statement
as a pending contradiction and asks. Confirming writes the new decision as the next version of the
same entity, so the version-vector layer (Themis) marks the old one superseded and keeps it. Declining
drops the pending statement and changes nothing.
"""
import re
import time
import uuid

from pydantic import BaseModel, Field
from qdrant_edge import FieldCondition, Filter, MatchValue

from ..common.schema import AGORA, HERMES, KRYPTA
from .extract import CANON, TECH, TECH_CATEGORY, find_tech, subject_label
from .timeparse import human

PENDING_KEY = "pending_decisions"


class ResolveDecisionArgs(BaseModel):
    id: str = Field(min_length=3, max_length=40)
    keep: str = Field(pattern="^(new|old)$")


class WhyArgs(BaseModel):
    query: str = Field(min_length=2, max_length=300)


def _values(v: str | None) -> frozenset[str]:
    return frozenset(x.strip().lower() for x in re.split(r"\s+and\s+|,", v or "") if x.strip())


def category_of(p: dict) -> str | None:
    return p.get("category") or ((p.get("slot") or "").split(":", 1)[1] if (p.get("slot") or "").startswith("decision:") else None)


def all_decisions(c) -> list[dict]:
    """Every decision version on this device, oldest first."""
    flt = Filter(must=[FieldCondition(key="kind", match=MatchValue(value="decision"))])
    out = []
    for shard in (KRYPTA, HERMES, AGORA):
        out += [{"shard": shard, **r.payload} for r in c.dev.store.scroll(shard, flt)]
    uniq = {d["op_id"]: d for d in out}
    return sorted(uniq.values(), key=lambda d: (d.get("valid_from") or 0, d["op_id"]))


def live_decisions(c, category: str | None = None) -> list[dict]:
    return [d for d in all_decisions(c) if d.get("status") != "superseded" and (category is None or category_of(d) == category)]


def _value_of(d: dict) -> str:
    if d.get("decision_value"):
        return d["decision_value"]
    m = re.search(r"use (.+?) as the", d.get("text", ""))
    return m.group(1) if m else d.get("text", "")[:40]


def record(c, d: dict, by_id: dict | None = None) -> dict:
    """The decision as the dashboard and the answers show it."""
    by_id = by_id if by_id is not None else {x["op_id"]: x for x in all_decisions(c)}
    replaced = [x["op_id"] for x in by_id.values() if x.get("superseded_by") == d["op_id"]]
    res = d.get("resolution")
    return {
        "op_id": d["op_id"], "category": category_of(d), "value": _value_of(d), "subject": d.get("subject"),
        "subject_label": subject_label(d.get("subject")), "reason": d.get("reason"),
        "evidence": d.get("evidence"), "source": d.get("source") or "unknown",
        "at": d.get("valid_from"), "at_text": human(d["valid_from"]) if d.get("valid_from") else None,
        "confidence": d.get("confidence"), "stance": d.get("stance"), "status": d.get("status", "current"),
        "superseded_by": d.get("superseded_by"), "supersedes": replaced, "resolution": res,
        "device": d.get("device_id"), "request_id": d.get("request_id"),
    }


def decisions(c) -> list[dict]:
    by_id = {x["op_id"]: x for x in all_decisions(c)}
    return [record(c, d, by_id) for d in by_id.values()][::-1]


# ---- pending contradictions --------------------------------------------------------------
def pending(c) -> list[dict]:
    return c.dev.db.get(PENDING_KEY, [])


def _save(c, items: list[dict]) -> None:
    c.dev.db.set(PENDING_KEY, items)


def detect(c, args, subject: str | None) -> dict | None:
    """Return a pending-contradiction record if `args` (a decision) contradicts a live decision."""
    if args.kind != "decision" or not (args.slot or "").startswith("decision:"):
        return None
    cat = args.slot.split(":", 1)[1]
    live = live_decisions(c, cat)
    if subject:
        live = [d for d in live if d.get("subject") in (subject, None)]
    elif len({d.get("subject") for d in live}) > 1:      # ambiguous project: do not guess which one this is about
        live = []
    if not live:
        return None
    prev = live[-1]
    new_value = args.fields.get("decision_value") or ""
    if _values(new_value) == _values(_value_of(prev)):
        return None                          # reaffirmed: an ordinary new version of the same decision
    return {
        "id": uuid.uuid4().hex[:8], "category": cat, "subject": prev.get("subject"), "created": c.clock(),
        "previous": record(c, prev),
        "new": {"value": new_value, "reason": args.fields.get("reason"), "text": args.text,
                "confidence": args.confidence, "stance": args.fields.get("stance"), "args": args.model_dump()},
        "why": f"Both refer to the {cat.replace('-', ' ')} decision for {subject_label(prev.get('subject'))}.",
    }


def hold(c, pend: dict) -> dict:
    items = [p for p in pending(c) if not (p["category"] == pend["category"] and p["subject"] == pend["subject"])]
    items.append(pend)
    _save(c, items)
    return view(pend)


def view(p: dict) -> dict:
    prev, new = p["previous"], p["new"]
    return {"id": p["id"], "category": p["category"], "subject": p["subject"], "subject_label": subject_label(p["subject"]),
            "previous": {k: prev[k] for k in ("op_id", "value", "reason", "at_text", "confidence", "evidence")},
            "new": {"value": new["value"], "reason": new["reason"], "confidence": new["confidence"], "stance": new["stance"]},
            "why": p["why"],
            "question": f"Has the {p['category'].replace('-', ' ')} decision for {subject_label(p['subject'])} changed from "
                        f"{prev['value']} to {new['value']}? Say yes to switch (the old decision is kept as history), or no to keep {prev['value']}."}


def pending_views(c) -> list[dict]:
    return [view(p) for p in pending(c)]


ACCEPT = re.compile(r"^\s*(yes|yep|yeah|yup|confirm(?:ed)?|correct|right|switch|go ahead|do it|that'?s right|it has changed)\b", re.I)
REJECT = re.compile(r"^\s*(no|nope|nah|keep|never ?mind|cancel|don'?t|not)\b", re.I)


def parse_verdict(text: str) -> str | None:
    """A short yes/no answer to a pending contradiction. Long messages are treated as new statements."""
    if len(text) > 90:
        return None
    if ACCEPT.match(text):
        return "new"
    if REJECT.match(text):
        return "old"
    return None


def resolve(c, pid: str, keep: str) -> dict:
    """The tool behind 'yes' / 'no'. keep='new' writes the new decision as the next version."""
    items = pending(c)
    p = next((x for x in items if x["id"] == pid), None)
    if p is None:
        return {"ok": False, "message": "no pending contradiction with that id"}
    _save(c, [x for x in items if x["id"] != pid])
    prev = p["previous"]
    if keep == "old":
        return {"ok": True, "kept": "old", "message": f"Kept {prev['value']} as the {p['category'].replace('-', ' ')} for "
                f"{subject_label(p['subject'])}. The {p['new']['value']} statement was not stored."}
    from .tools import StoreArgs, _write, NoteIn
    a = StoreArgs(**{**p["new"]["args"], "subject": p["subject"]})
    fields = {**a.fields, "resolution": {"mode": "user-confirmed", "replaces": prev["op_id"], "by": "user", "at": c.clock()},
              "stance": "decided"}
    out = _write(c, NoteIn(text=a.text, kind="decision", machine=p["subject"], memory_type="semantic", slot=a.slot,
                           importance=a.importance, confidence=min(0.95, (a.confidence or 0.6) + 0.25), entities=a.entities,
                           tags=a.tags, fields=fields, source="conversation"))
    out["kept"] = "new"
    out["replaced"] = prev["op_id"]
    out["message"] = (f"Switched the {p['category'].replace('-', ' ')} for {subject_label(p['subject'])} from {prev['value']} to "
                      f"{p['new']['value']}. {prev['value']} is kept as history, marked superseded.")
    return out


# ---- "why did we choose X?" ----------------------------------------------------------------------
WHY = re.compile(r"\bwhy\b.*\b(choose|chose|chosen|pick|picked|use|using|go(?:ing)? with|decide|decided|select|selected|switch|went with)\b|"
                 r"\b(reason|rationale)\b.*\b(for|behind)\b", re.I)

CATEGORY_WORDS = {"database": "database", "db": "database", "datastore": "database", "backend": "backend-framework",
                  "framework": "backend-framework", "frontend": "frontend", "language": "language",
                  "hosting": "hosting", "vector": "vector-store"}


def is_why_question(text: str) -> bool:
    return bool(WHY.search(text))


def why_answer(c, query: str) -> dict:
    """The recorded decision, its reason and its evidence, for a why-question. No guessing:
    if no decision matches, say so."""
    every = {d["op_id"]: d for d in all_decisions(c)}
    techs = [CANON.get(t, t) for t in find_tech(query)]
    cats = {TECH_CATEGORY[t] for t in find_tech(query)} | {CATEGORY_WORDS[w] for w in re.findall(r"[a-z]+", query.lower()) if w in CATEGORY_WORDS}
    matches = [d for d in every.values() if any(t.lower() in _values(_value_of(d)) for t in techs)]
    if not matches and cats:
        matches = [d for d in every.values() if category_of(d) in cats and d.get("status") != "superseded"]
    if not matches:
        active = c.active_subject()
        matches = [d for d in every.values() if d.get("status") != "superseded" and (not active or d.get("subject") == active)]
        if len(matches) != 1:
            return {"ok": True, "found": False, "message": "I don't have a recorded decision that matches that."}
    live = [d for d in matches if d.get("status") != "superseded"] or matches
    d = live[-1]
    r = record(c, d, every)
    place = f" for {r['subject_label']}" if r["subject"] else ""
    what = f"{r['value']} as the {r['category'].replace('-', ' ')}" if r["category"] else r["value"]
    verb = "proposed" if r["stance"] == "proposal" else "chose"
    if r["status"] == "superseded":
        newer = every.get(r["superseded_by"])
        head = f"You used {what}{place} ({r['at_text']}), but it was replaced by {_value_of(newer)}" if newer else \
            f"You used {what}{place} ({r['at_text']}), but it was superseded"
    else:
        head = f"You {verb} {what}{place} on {r['at_text']}"
    because = f" Reason: {r['reason']}." if r["reason"] else " I have no recorded reason for it."
    quote = f" (You said: “{r['evidence']}”)" if r["evidence"] else ""
    older = [every[o] for o in r["supersedes"] if o in every]
    hist = f" It replaced {_value_of(older[-1])}." if older else ""
    return {"ok": True, "found": True, "op_id": d["op_id"], "decision": r,
            "message": f"{head}.{because}{hist}{quote}"}
