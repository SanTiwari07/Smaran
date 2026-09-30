"""Provenance: why does Smaran believe this memory?

    explain_memory(c, op_id) -> source, when, confidence (with its parts), the decision and reason
                                where the memory is one, supporting memories, and version history.

Confidence is deterministic and shown part by part. Nothing here is a model's self-rating:

    stored confidence      set when the memory was written, by a stated rule
                           (decision: 0.85 settled / 0.60 proposal, +0.05 if a reason was given;
                            fact 0.75, task 0.8-0.9, preference 0.85, schedule 0.85, episode 0.6)
    + user confirmed       +0.25 when the user confirmed a contradiction or a conflict resolution
    + corroboration        +0.03 per other memory from the same message that supports it (max +0.06)
    - contested            -0.15 while two devices disagree and nobody has resolved it
    x lifecycle            x0.85 when stale, x0.60 when archived
    result is clamped to 0.05 .. 0.99
"""
from qdrant_edge import FieldCondition, Filter, MatchValue

from ..common.config import DEVICE_LABELS
from ..common.schema import AGORA, HERMES, KRYPTA
from . import decisions as dec
from .extract import subject_label
from .lifecycle import lifecycle
from .timeparse import human

SHARDS = (KRYPTA, HERMES, AGORA)


def find(c, op_id: str) -> dict | None:
    for shard in SHARDS:
        r = c.dev.store.get(shard, op_id)
        if r is not None:
            return {"shard": shard, **r.payload}
    return None


def clean(text: str) -> str:
    return text.split(" Original:")[0]


def supporting(c, p: dict) -> list[dict]:
    """Other memories written from the same message."""
    rid = p.get("request_id")
    if not rid:
        return []
    flt = Filter(must=[FieldCondition(key="request_id", match=MatchValue(value=rid))])
    out = {}
    for shard in SHARDS:
        for r in c.dev.store.scroll(shard, flt):
            q = r.payload
            if q["op_id"] != p["op_id"] and q.get("status") != "superseded":
                out[q["op_id"]] = {"op_id": q["op_id"], "text": clean(q["text"]), "kind": q.get("kind"),
                                   "why": "said in the same message"}
    return list(out.values())[:5]


def confidence(p: dict, n_support: int, lc_state: str) -> dict:
    stored = float(p.get("confidence") if p.get("confidence") is not None else 0.7)
    parts = [{"label": f"stored confidence ({p.get('basis') or p.get('source') or 'rule'})", "value": round(stored, 2), "op": "start"}]
    value = stored
    if n_support:
        d = min(0.03 * n_support, 0.06)
        parts.append({"label": f"{n_support} supporting {'memory' if n_support == 1 else 'memories'} from the same message", "value": d, "op": "add"})
        value += d
    if p.get("status") == "contested":
        parts.append({"label": "two devices disagree", "value": -0.15, "op": "add"})
        value -= 0.15
    if lc_state in ("stale", "archived"):
        m = 0.85 if lc_state == "stale" else 0.60
        parts.append({"label": f"memory is {lc_state}", "value": m, "op": "multiply"})
        value *= m
    return {"value": round(max(0.05, min(0.99, value)), 2), "parts": parts}


def explain_memory(c, op_id: str) -> dict | None:
    p = find(c, op_id)
    if p is None:
        return None
    now = c.clock()
    lc = lifecycle(p, now)
    sup = supporting(c, p)
    conf = confidence(p, len(sup), lc.state)
    src_type = p.get("source") or "unknown"
    res = p.get("resolution")
    history = []
    if p.get("entity_key"):
        for _, q in sorted(c.dev.store.by_entity(p["entity_key"]), key=lambda t: (t[1].get("valid_from") or 0, t[1]["op_id"])):
            history.append({"op_id": q["op_id"], "text": clean(q["text"]), "status": q.get("status"),
                            "at_text": human(q["valid_from"]) if q.get("valid_from") else None,
                            "device": DEVICE_LABELS.get(q.get("device_id"), q.get("device_id"))})
    out = {
        "op_id": p["op_id"], "text": clean(p["text"]), "kind": p.get("kind"), "subject": p.get("subject"),
        "subject_label": subject_label(p.get("subject")) if p.get("subject") else None,
        "status": p.get("status"), "shard": p["shard"],
        "source": {"type": src_type, "device": DEVICE_LABELS.get(p.get("device_id"), p.get("device_id")),
                   "request_id": p.get("request_id"), "quote": p.get("evidence") or clean(p["text"]),
                   "recorded_by": p.get("author") or None},
        "at": p.get("valid_from"), "at_text": human(p["valid_from"]) if p.get("valid_from") else None,
        "confidence": conf, "lifecycle": lc.as_dict(), "supporting": sup, "history": history,
        "derived_from": p.get("derived_from") or [], "resolution": res,
    }
    if p.get("resolved_by") or (p.get("device_id") == "supervisor"):
        out["resolution"] = out["resolution"] or {"mode": "user-confirmed", "by": p.get("author") or "you"}
        out["source"]["type"] = "user-confirmed resolution"
    if p.get("kind") == "decision":
        out["decision"] = dec.record(c, p)
    return out
