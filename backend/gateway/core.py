"""The sync gateway: idempotent ingest, Themis on the server side, the fleet change feed.

Every public method runs under one lock. At fleet-demo scale that's plenty, and it rules out
races between two devices syncing the same entity, and concurrent use of the shared SQLite
connection and of qdrant-client's embedded mode (neither is safe across threads).
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

from ..common import themis
from ..common.config import settings
from ..common.log import Log
from ..common.pii import find_pii
from ..common.schema import SyncBatch, entity_key_for
from ..device.search import cosine
from .server import FleetServer, eq, m, vectors_json

LOCAL_ONLY_FIELDS = ("known_from", "valid_to")   # each replica keeps its own view of time

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_ops(op_id TEXT PRIMARY KEY, device_id TEXT, result TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v INTEGER);
CREATE TABLE IF NOT EXISTS stats(device_id TEXT PRIMARY KEY, bytes INT DEFAULT 0, ops INT DEFAULT 0,
                                 duplicates INT DEFAULT 0, rejected INT DEFAULT 0, last_seen REAL);
"""


class Gateway:
    def __init__(self, server: FleetServer, db_path: Path, embedder_factory, log: Log | None = None):
        self.server = server
        self.log = log or Log("gateway")
        self.lock = threading.RLock()
        self._embedder, self._embedder_factory = None, embedder_factory
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = self._embedder_factory()
        return self._embedder

    # ---- small sqlite helpers --------------------------------------------------------
    def _next(self, key: str) -> int:
        self.db.execute("INSERT INTO meta(k,v) VALUES(?,1) ON CONFLICT(k) DO UPDATE SET v=v+1", (key,))
        return self.db.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()[0]

    def _meta(self, key: str) -> int:
        row = self.db.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
        return row[0] if row else 0

    def _stat(self, device_id: str, **inc) -> None:
        self.db.execute("INSERT OR IGNORE INTO stats(device_id) VALUES(?)", (device_id,))
        for col, n in inc.items():
            self.db.execute(f"UPDATE stats SET {col}={col}+?, last_seen=? WHERE device_id=?", (n, time.time(), device_id))

    # ---- ingest ----------------------------------------------------------------------
    def sync(self, batch: SyncBatch, raw_bytes: int) -> dict:
        with self.lock:
            self._stat(batch.device_id, bytes=raw_bytes)
            results = []
            for op in batch.ops:
                if self.db.execute("SELECT 1 FROM seen_ops WHERE op_id=?", (op.op_id,)).fetchone():
                    self._stat(batch.device_id, duplicates=1)
                    results.append({"op_id": op.op_id, "result": "duplicate"})
                    continue
                reason = self._reject_reason(op.payload)
                if reason:
                    result = "rejected"
                    self._stat(batch.device_id, rejected=1)
                    self.log.error("rejected", op_id=op.op_id, reason=reason)
                else:
                    result = self._ingest(op.op_id, op.vectors.model_dump(), op.payload)
                    self._stat(batch.device_id, ops=1)
                self.db.execute("INSERT INTO seen_ops VALUES(?,?,?,?)", (op.op_id, batch.device_id, result, time.time()))
                results.append({"op_id": op.op_id, "result": result})
            return {"results": results}

    @staticmethod
    def _reject_reason(payload: dict) -> str | None:
        """Defence in depth: private data should never arrive; if it does, it's not stored."""
        if payload.get("residency") != "sync":
            return f"residency={payload.get('residency')}"
        hits = find_pii(payload.get("text", ""))
        return f"PII rule matched: {', '.join(hits)}" if hits else None

    def _ingest(self, op_id: str, vectors: dict, payload: dict) -> str:
        p = {k: v for k, v in payload.items() if k not in LOCAL_ONLY_FIELDS}
        p.update(synced_at=time.time(), server_seq=self._next("server_seq"))
        ek = p.get("entity_key")
        if not ek:
            p.update(status="current", superseded_by=None)
            self.server.upsert(op_id, vectors, p)
            self.log("stored", op_id=op_id, result="applied")
            return "applied"
        plan = themis.apply(self.server.versions(ek), p)
        if plan.result == "duplicate":
            return "duplicate"
        status, by = plan.changes[op_id]
        p.update(status=status, superseded_by=by)
        self.server.upsert(op_id, vectors, p)
        for other, (st, sb) in plan.changes.items():
            if other != op_id:
                self.server.set_payload(other, {"status": st, "superseded_by": sb, "server_seq": self._next("server_seq")})
        if status == themis.CONTESTED:
            self.log("conflict", entity_key=ek, op_id=op_id, count=sum(1 for s, _ in plan.changes.values() if s == themis.CONTESTED))
        self.log("stored", op_id=op_id, entity_key=ek, status=status, result=plan.result)
        return plan.result

    # ---- change feed + search --------------------------------------------------------
    def changes(self, since: int, limit: int = 500) -> dict:
        with self.lock:
            recs = self.server.changes(since, limit)
            pts = [{"payload": r.payload, "vectors": vectors_json(r.vector)} for r in recs]
            return {"points": pts, "last_seq": recs[-1].payload["server_seq"] if recs else since}

    def search(self, dense: list[float], sparse: dict, limit: int = 10) -> dict:
        with self.lock:
            pts = self.server.hybrid(dense, sparse, limit)
            return {"results": [{"payload": p.payload, "rrf": p.score, "shard": "cloud",
                                 "dense_score": round(cosine(dense, p.vector["dense"]), 4)} for p in pts]}

    # ---- conflicts -------------------------------------------------------------------
    def contested(self) -> list[dict]:
        with self.lock:
            groups: dict[str, list] = {}
            for r in self.server.scroll(m.Filter(must=[eq("status", "contested")])):
                groups.setdefault(r.payload["entity_key"], []).append(r.payload)
            return [{"entity_key": ek, "versions": sorted(vs, key=lambda v: v["op_id"])} for ek, vs in sorted(groups.items())]

    def resolve(self, entity_key: str, keep_op_id: str | None, text: str | None, author: str) -> dict:
        with self.lock:
            versions = self.server.versions(entity_key)
            live = [v for v in versions if v["status"] != themis.SUPERSEDED]
            if not live:
                raise ValueError(f"no live versions for {entity_key}")
            if keep_op_id:
                chosen = next((v for v in live if v["op_id"] == keep_op_id), None)
                if chosen is None:
                    raise ValueError(f"{keep_op_id} is not a live version of {entity_key}")
                text = chosen["text"]
            if not text:
                raise ValueError("give op_id to keep, or a new text")
            n = self._next("supervisor_seq")
            op_id = f"SUP-{n:06d}"
            dense, sparse = self.embedder.embed_doc(text)
            now = time.time()
            payload = {
                "op_id": op_id, "entity_key": entity_key, "machine": live[0].get("machine"), "kind": "status",
                "text": text, "device_id": "supervisor", "author": author,
                "vv": themis.next_vv([v["vv"] for v in versions], "supervisor", n), "seq": n,
                "valid_from": now, "residency": "sync", "criticality": max(v.get("criticality", 0) for v in live),
                "decision": {"by": "supervisor", "residency": "sync", "criticality": 0, "confidence": 1.0,
                             "reason": f"resolved {len(live)} versions" + (f", kept {keep_op_id}" if keep_op_id else "")},
            }
            vectors = {"dense": dense, "bm25": {"indices": list(sparse.indices), "values": list(sparse.values)}}
            result = self._ingest(op_id, vectors, payload)
            self.db.execute("INSERT INTO seen_ops VALUES(?,?,?,?)", (op_id, "supervisor", result, now))
            self.log("resolved", entity_key=entity_key, op_id=op_id, result=result)
            return {"op_id": op_id, "result": result, "text": text}

    # ---- audit, stats, listing -------------------------------------------------------
    def audit(self) -> dict:
        with self.lock:
            recs = self.server.scroll()
            private = [r.payload["op_id"] for r in recs if r.payload.get("residency") != "sync"]
            pii = [r.payload["op_id"] for r in recs if find_pii(r.payload.get("text", ""))]
            return {"total": len(recs), "private_count": len(private), "pii_hits": len(pii),
                    "offenders": (private + pii)[:20], "ok": not private and not pii}

    def stats(self) -> dict:
        with self.lock:
            rows = self.db.execute("SELECT device_id, bytes, ops, duplicates, rejected, last_seen FROM stats").fetchall()
            return {"server": self.server.describe(), "points": self.server.count(),
                    "server_seq": self._meta("server_seq"),
                    "contested": self.server.count(m.Filter(must=[eq("status", "contested")])),
                    "devices": [dict(zip(("device_id", "bytes", "ops", "duplicates", "rejected", "last_seen"), r)) for r in rows]}

    def memories(self, limit: int = 500) -> list[dict]:
        with self.lock:
            out = [r.payload for r in self.server.scroll()]
            out.sort(key=lambda p: -p.get("server_seq", 0))
            return out[:limit]

    # ---- admin -----------------------------------------------------------------------
    def reset(self) -> None:
        with self.lock:
            self.server.reset()
            self.db.executescript("DELETE FROM seen_ops; DELETE FROM meta; DELETE FROM stats;")
            self.log("reset")

    def seed(self, path: Path) -> int:
        """Load fleet knowledge (machine manuals, baseline statuses) from seed/manuals/*.json."""
        items = []
        for f in sorted(path.glob("*.json")):
            items += json.loads(f.read_text(encoding="utf8"))
        with self.lock:
            dense_all = self.embedder.dense([it["text"] for it in items]) if items else []
            for i, (it, dense) in enumerate(zip(items, dense_all), start=1):
                op_id = f"FLEET-{i:04d}"
                if self.db.execute("SELECT 1 FROM seen_ops WHERE op_id=?", (op_id,)).fetchone():
                    continue
                sparse = self.embedder.bm25.embed_document(it["text"])
                kind = it.get("kind", "manual")
                payload = {"op_id": op_id, "entity_key": entity_key_for(it.get("machine"), kind),
                           "machine": it.get("machine"), "kind": kind, "text": it["text"], "device_id": "fleet",
                           "author": it.get("author", "maintenance-manual"), "vv": {"fleet": i}, "seq": i,
                           "valid_from": time.time() - 86400, "residency": "sync", "criticality": it.get("criticality", 0),
                           "decision": {"by": "seed", "residency": "sync", "criticality": 0, "confidence": 1.0,
                                        "reason": "fleet knowledge"}}
                vectors = {"dense": dense, "bm25": {"indices": list(sparse.indices), "values": list(sparse.values)}}
                self._ingest(op_id, vectors, payload)
                self.db.execute("INSERT INTO seen_ops VALUES(?,?,?,?)", (op_id, "fleet", "applied", time.time()))
            self.log("seeded", count=len(items))
            return len(items)
