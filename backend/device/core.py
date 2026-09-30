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
from ..common.vectors import dense_of, pack
from .embed import Embedder, sparse_from_json, sparse_to_json
from .outbox import DeviceDB
from .router import Router
from .search import believed_at, local_search
from .store import Store


# payload keys a caller-supplied `fields` dict may never overwrite
_RESERVED = {"op_id", "entity_key", "vv", "seq", "status", "residency", "decision", "device_id",
             "valid_from", "known_from", "valid_to", "superseded_by", "text", "kind"}


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
        self.recovery: dict = {}
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
            "bytes_sent": self.db.get("bytes_sent", 0), "acked": self.db.acked(),
            "recovery": self.recovery,
            "counts": {s: self.store.count(s) for s in SHARDS},
            "contested": self.store.count(HERMES, _status("contested")) + self.store.count(AGORA, _status("contested")),
            "classifier": self.classifier.name, "embedder": self.embedder.name,
        }

    # ---- crash recovery --------------------------------------------------------------
    def recover(self) -> None:
        """On start, rebuild whatever a hard crash may have cost the Edge shards (see outbox.py):

        1. Hermes: replay pending outbox rows whose shard write was lost. Hermes sends them
           again; the gateway ignores any it already stored (idempotency by op_id), so a crash
           between "gateway stored" and "device acked" costs a duplicate send, never a
           duplicate memory.
        2. Krypta: replay the local journal.
        3. Agora: after an unclean shutdown, pull the change feed again from the start.
        4. Re-run Themis for every known entity (lost set_payload status changes).
        """
        clean = bool(self.db.get("clean_shutdown", True))
        pending = self.db.pending_bodies()
        restored = 0
        for op_id, body in pending:
            if self.store.get(HERMES, op_id) is None and self.store.get(AGORA, op_id) is None:
                v = body["vectors"]
                self.store.upsert(HERMES, op_id, dense_of(v), sparse_from_json(v["bm25"]), body["payload"])
                restored += 1
        krypta = 0
        for op_id, body in self.db.journal_bodies():
            if self.store.get(KRYPTA, op_id) is None:
                self.store.upsert(KRYPTA, op_id, body["dense"], sparse_from_json(body["bm25"]), body["payload"])
                krypta += 1
        if not clean:
            self.db.set("last_server_seq", 0)
        keys = {r.payload["entity_key"] for s in (HERMES, AGORA) for r in self.store.scroll(s) if r.payload.get("entity_key")}
        for ek in keys:
            self.resolve_entity(ek)
        self.db.set("clean_shutdown", False)       # set back to True only by close()
        self.recovery = {"ts": time.time(), "clean": clean, "pending": len(pending),
                         "restored": restored, "krypta_restored": krypta}
        if pending or krypta or not clean:
            self.event("recovered", count=len(pending), restored=restored, krypta_restored=krypta, clean=clean)

    # ---- write path ------------------------------------------------------------------
    def add_note(self, note: NoteIn) -> dict:
        dense, sparse = self.embedder.embed_doc(note.text)
        decision = self.router.decide(note, dense)
        seq = self.db.next_seq()
        op_id = f"{self.id}-{seq:06d}"
        now = note.ts or time.time()
        ek = entity_key_for(note.machine, note.kind, note.slot) if decision.residency == "sync" else None
        known = [p["vv"] for _, p in self.store.by_entity(ek)] if ek else []
        payload = {
            "op_id": op_id, "entity_key": ek, "machine": note.machine, "kind": note.kind,
            "text": note.text, "device_id": self.id, "author": note.author or f"tech-{self.id}",
            "vv": themis.next_vv(known, self.id, seq), "seq": seq,
            "valid_from": now, "known_from": now, "valid_to": None, "superseded_by": None,
            "status": "current", "residency": decision.residency, "criticality": decision.criticality,
            "decision": decision.as_dict(),
            "subject": note.machine, "memory_type": note.memory_type, "slot": note.slot,
            "importance": note.importance, "confidence": note.confidence, "entities": note.entities,
            "tags": note.tags, "source": note.source,
            **{k: v for k, v in note.fields.items() if k not in _RESERVED},
        }
        self.db.add_decision(op_id, note.text, decision.as_dict())
        shard = None
        if decision.residency == "private":
            shard = KRYPTA
            self.db.journal_put(op_id, {"dense": dense, "bm25": sparse_to_json(sparse), "payload": payload})
            self.store.upsert(KRYPTA, op_id, dense, sparse, payload)
        elif decision.residency == "sync":
            shard = HERMES
            body = {"op_id": op_id, "vectors": pack(dense, sparse_to_json(sparse)), "payload": payload}
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
            self.store.upsert(AGORA, op_id, dense_of(v), sparse_from_json(v["bm25"]), p)
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
    def search(self, q: str, limit: int = 10, at: float | None = None, include_superseded: bool = False,
               mode: str = "hybrid", allow_cloud: bool = True) -> dict:
        res = local_search(self.store, self.embedder, q, limit, at, include_superseded, mode=mode)
        res["mode"] = mode
        dq, sq = res.pop("query_vectors")
        res["answered"] = "local"
        if (allow_cloud and at is None and mode == "hybrid" and self.online and self.http is not None
                and res["top_dense"] < settings.escalate_at):
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

    def prove_latency(self, n: int = 50) -> dict:
        """Run n hybrid searches on this device's current memory, never touching the network
        (local_search only: no cloud escalation). Target from the plan: p50 < 20 ms, p95 < 50 ms."""
        search_ms, total_ms = [], []
        for i in range(n):
            r = local_search(self.store, self.embedder, PROBE_QUERIES[i % len(PROBE_QUERIES)], 10)
            search_ms.append(r["search_ms"])
            total_ms.append(r["latency_ms"])
        p50, p95 = _pct(search_ms, 50), _pct(search_ms, 95)
        return {"queries": n, "memories": sum(self.store.count(s) for s in SHARDS), "network": "none",
                "search_p50_ms": p50, "search_p95_ms": p95, "total_p50_ms": _pct(total_ms, 50),
                "ok": p50 < 20 and p95 < 50, "command": "python -m bench.bench latency"}

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
        self.db.set("clean_shutdown", False)
        self.activity.clear()
        self.event("reset", ms=round((time.perf_counter() - t0) * 1000))

    def close(self) -> None:
        if not self.store.shards:                # already closed
            return
        self.store.close()                       # closing an Edge shard persists it
        self.db.set("clean_shutdown", True)
        self.db.close()


PROBE_QUERIES = ["CNC-07 bearing trouble", "spindle overheating", "hydraulic pressure low on PRESS-02",
                 "coolant pump leak", "robot gripper pressure fault", "alarm 1040", "lockout tagout",
                 "chatter marks on the lathe", "smoke from the motor", "encoder drift on axis 3"]


def _pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))], 2)


def _status(s: str) -> Filter:
    return Filter(must=[FieldCondition(key="status", match=MatchValue(value=s))])
