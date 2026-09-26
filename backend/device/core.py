"""One edge device: the write path, local conflict resolution, mirror ingest and search.

app.py (HTTP) and the tests both drive this class, so every behaviour can be reproduced
without starting a server.
"""
import time
from collections import deque
from pathlib import Path

from qdrant_edge import FieldCondition, Filter, MatchValue

from ..common import themis
from ..common.config import settings
from ..common.log import Log
from ..common.schema import AGORA, HERMES, KRYPTA, SHARDS, NoteIn, entity_key_for
from .embed import Embedder, sparse_from_json, sparse_to_json
from .outbox import DeviceDB
from .router import Router
from .search import believed_at, local_search
from .store import Store


class Device:
    def __init__(self, device_id: str, root: Path, embedder: Embedder, classifier, http=None,
                 log: Log | None = None):
        self.id = device_id
        self.root = Path(root)
        self.embedder = embedder
        self.classifier = classifier
        self.http = http                      # httpx.Client-like, base_url = gateway
        self.log = log or Log(f"device-{device_id}")
        self.store = Store(self.root, embedder.dim)
        self.db = DeviceDB(self.root / "device.db")
        self.router = Router(classifier, self.store)
        self.activity: deque = deque(maxlen=300)
        self.last_write = 0.0
        self.recover()

    # ---- state -----------------------------------------------------------------------
    @property
    def online(self) -> bool:
        return bool(self.db.get("online", True))

    def set_online(self, value: bool) -> None:
        self.db.set("online", value)
        if value:
            self.db.retry_now()
        self.event("online" if value else "offline")

    def event(self, kind: str, **fields) -> None:
        self.activity.appendleft({"ts": time.time(), "device": self.id, "kind": kind, **fields})
        self.log(kind, **fields)

    def state(self) -> dict:
        return {
            "device_id": self.id, "online": self.online, "outbox_depth": self.db.depth(),
            "last_sync": self.db.get("last_sync"), "last_error": self.db.get("last_error"),
            "last_server_seq": self.db.get("last_server_seq", 0),
            "bytes_sent": self.db.get("bytes_sent", 0),
            "counts": {s: self.store.count(s) for s in SHARDS},
            "contested": self.store.count(HERMES, _status("contested")) + self.store.count(AGORA, _status("contested")),
            "classifier": self.classifier.name, "embedder": self.embedder.name,
        }

    # ---- crash recovery --------------------------------------------------------------
    def recover(self) -> None:
        """Replay pending outbox rows into Hermes (the shard write may not have happened)."""
        replayed = 0
        for op_id, body in self.db.pending_bodies():
            if self.store.get(HERMES, op_id) is None and self.store.get(AGORA, op_id) is None:
                v = body["vectors"]
                self.store.upsert(HERMES, op_id, v["dense"], sparse_from_json(v["bm25"]), body["payload"])
                replayed += 1
        if replayed:
            self.event("recovered", count=replayed)

    # ---- write path ------------------------------------------------------------------
    def add_note(self, note: NoteIn) -> dict:
        dense, sparse = self.embedder.embed_doc(note.text)
        decision = self.router.decide(note, dense)
        seq = self.db.next_seq()
        op_id = f"{self.id}-{seq:06d}"
        now = time.time()
        ek = entity_key_for(note.machine, note.kind) if decision.residency == "sync" else None
        known = [p["vv"] for _, p in self.store.by_entity(ek)] if ek else []
        payload = {
            "op_id": op_id, "entity_key": ek, "machine": note.machine, "kind": note.kind,
            "text": note.text, "device_id": self.id, "author": note.author or f"tech-{self.id}",
            "vv": themis.next_vv(known, self.id, seq), "seq": seq,
            "valid_from": now, "known_from": now, "valid_to": None, "superseded_by": None,
            "status": "current", "residency": decision.residency, "criticality": decision.criticality,
            "decision": decision.as_dict(),
        }
        self.db.add_decision(op_id, note.text, decision.as_dict())
        shard = None
        if decision.residency == "private":
            shard = KRYPTA
            self.store.upsert(KRYPTA, op_id, dense, sparse, payload)
        elif decision.residency == "sync":
            shard = HERMES
            body = {"op_id": op_id, "vectors": {"dense": dense, "bm25": sparse_to_json(sparse)}, "payload": payload}
            self.db.enqueue(op_id, decision.criticality, seq, body)   # outbox FIRST: crash-safe
            self.store.upsert(HERMES, op_id, dense, sparse, payload)
            if ek:
                self.resolve_entity(ek)
        self.last_write = now
        self.event("decision", op_id=op_id, residency=decision.residency, by=decision.by,
                   criticality=decision.criticality, reason=decision.reason, text=note.text[:120])
        stored = self.store.get(shard, op_id).payload if shard else payload
        return {"memory": stored, "decision": decision.as_dict(), "shard": shard}

    # ---- Themis, locally -------------------------------------------------------------
    def resolve_entity(self, ek: str) -> dict:
        versions = self.store.by_entity(ek)
        statuses = themis.resolve([p for _, p in versions])
        now = time.time()
        for shard, p in versions:
            status, by = statuses[p["op_id"]]
            if (p.get("status"), p.get("superseded_by")) != (status, by):
                upd = {"status": status, "superseded_by": by}
                if status == themis.SUPERSEDED and p.get("valid_to") is None:
                    upd["valid_to"] = now
                self.store.set_payload(shard, p["op_id"], upd)
                if status == themis.CONTESTED and p.get("status") != themis.CONTESTED:
                    self.event("conflict", entity_key=ek, op_id=p["op_id"], text=p["text"][:120])
        return statuses

    # ---- mirror ingest (called by Hermes after GET /changes) -------------------------
    def ingest(self, points: list[dict]) -> int:
        touched = set()
        now = time.time()
        for pt in points:
            p = dict(pt["payload"])
            op_id = p["op_id"]
            local = self.store.get(AGORA, op_id) or self.store.get(HERMES, op_id)
            # keep this replica's own view of time; take everything else from the server
            p["known_from"] = local.payload.get("known_from", now) if local else now
            p["valid_to"] = local.payload.get("valid_to") if local else None
            if local:
                p["status"], p["superseded_by"] = local.payload.get("status"), local.payload.get("superseded_by")
            v = pt["vectors"]
            self.store.upsert(AGORA, op_id, v["dense"], sparse_from_json(v["bm25"]), p)
            if self.store.get(HERMES, op_id) is not None:
                self.store.delete(HERMES, op_id)         # now fleet knowledge; the outbox already acked it
                self.db.ack([op_id])
            if p.get("entity_key"):
                touched.add(p["entity_key"])
        for ek in touched:
            self.resolve_entity(ek)
        if len(points) > 50:
            self.store.optimize()
        return len(points)

    # ---- reads -----------------------------------------------------------------------
    def search(self, q: str, limit: int = 10, at: float | None = None, include_superseded: bool = False) -> dict:
        res = local_search(self.store, self.embedder, q, limit, at, include_superseded)
        dq, sq = res.pop("query_vectors")
        res["answered"] = "local"
        if at is None and self.online and self.http is not None and res["top_dense"] < settings.escalate_at:
            try:
                r = self.http.post("/search", json={"dense": dq, "bm25": sparse_to_json(sq), "limit": limit})
                r.raise_for_status()
                have = {h["payload"]["op_id"] for h in res["results"]}
                cloud = [h for h in r.json()["results"] if h["payload"]["op_id"] not in have]
                for h in cloud:
                    h["shard"] = "cloud"
                res["results"] = (res["results"] + cloud)[:limit] if cloud else res["results"]
                res["answered"] = "escalated"
                self.event("escalated", q=q, top_dense=res["top_dense"], cloud_hits=len(cloud))
            except Exception as e:  # noqa: BLE001  cloud is a backup, never a crutch
                self.event("escalation_failed", error=str(e))
        return res

    def memories(self, shard: str | None = None, status: str | None = None, machine: str | None = None,
                 limit: int = 500) -> list[dict]:
        must = []
        if status:
            must.append(FieldCondition(key="status", match=MatchValue(value=status)))
        if machine:
            must.append(FieldCondition(key="machine", match=MatchValue(value=machine)))
        flt = Filter(must=must) if must else None
        out = []
        for s in ([shard] if shard else SHARDS):
            out += [{"shard": s, **r.payload} for r in self.store.scroll(s, flt)]
        out.sort(key=lambda m: -(m.get("known_from") or 0))
        return out[:limit]

    def history(self, at: float, entity_key: str | None = None) -> list[dict]:
        """What this device believed about each entity at time `at`."""
        flt = Filter(must=[FieldCondition(key="entity_key", match=MatchValue(value=entity_key))]) if entity_key else None
        groups: dict[str, list[dict]] = {}
        for s in (HERMES, AGORA):
            for r in self.store.scroll(s, flt):
                p = r.payload
                if p.get("entity_key") and believed_at(p, at):
                    groups.setdefault(p["entity_key"], []).append({"shard": s, **p})
        return [{"entity_key": ek, "status": "current" if len(vs) == 1 else "contested",
                 "versions": sorted(vs, key=lambda v: v["op_id"])} for ek, vs in sorted(groups.items())]

    # ---- admin -----------------------------------------------------------------------
    def reset(self) -> None:
        t0 = time.perf_counter()
        self.store.clear()
        self.db.reset()
        self.activity.clear()
        self.event("reset", ms=round((time.perf_counter() - t0) * 1000))

    def close(self) -> None:
        self.store.close()
        self.db.close()


def _status(s: str) -> Filter:
    return Filter(must=[FieldCondition(key="status", match=MatchValue(value=s))])
