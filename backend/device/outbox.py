"""Device SQLite: the crash-safe outbox, the decision log and small counters.

WAL mode + one write per statement means a crash never loses an acknowledged write.
The outbox row is written BEFORE the shard upsert; on restart, pending rows are replayed.
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox(
  op_id TEXT PRIMARY KEY, criticality INT, seq INT, body TEXT,
  attempts INT DEFAULT 0, next_try REAL DEFAULT 0, state TEXT DEFAULT 'pending', created REAL);
CREATE INDEX IF NOT EXISTS outbox_due ON outbox(state, criticality DESC, seq ASC);
CREATE TABLE IF NOT EXISTS decisions(
  id INTEGER PRIMARY KEY, ts REAL, op_id TEXT, text TEXT, by TEXT, residency TEXT,
  criticality INT, confidence REAL, reason TEXT);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""


class DeviceDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    def reset(self) -> None:
        with self.lock:
            self.conn.executescript("DELETE FROM outbox; DELETE FROM decisions; DELETE FROM meta;")

    # ---- meta ------------------------------------------------------------------------
    def get(self, k: str, default=None):
        with self.lock:
            row = self.conn.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, k: str, v) -> None:
        with self.lock:
            self.conn.execute("INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                              (k, json.dumps(v)))

    def incr(self, k: str, by: int | float = 1):
        with self.lock:
            v = self.get(k, 0) + by
            self.set(k, v)
            return v

    def next_seq(self) -> int:
        return self.incr("seq")

    # ---- outbox ----------------------------------------------------------------------
    def enqueue(self, op_id: str, criticality: int, seq: int, body: dict) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO outbox(op_id,criticality,seq,body,created) VALUES(?,?,?,?,?)",
                (op_id, criticality, seq, json.dumps(body), time.time()))

    def due(self, limit: int) -> list[tuple[str, dict]]:
        """Pending ops ready to send, most critical first, then oldest first."""
        with self.lock:
            rows = self.conn.execute(
                "SELECT op_id, body FROM outbox WHERE state='pending' AND next_try<=? "
                "ORDER BY criticality DESC, seq ASC LIMIT ?", (time.time(), limit)).fetchall()
        return [(r[0], json.loads(r[1])) for r in rows]

    def pending_bodies(self) -> list[tuple[str, dict]]:
        """Every pending op regardless of backoff (used for crash recovery)."""
        with self.lock:
            rows = self.conn.execute("SELECT op_id, body FROM outbox WHERE state='pending'").fetchall()
        return [(r[0], json.loads(r[1])) for r in rows]

    def pending(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT op_id, criticality, seq, attempts, body FROM outbox WHERE state='pending' "
                "ORDER BY criticality DESC, seq ASC").fetchall()
        return [{"op_id": r[0], "criticality": r[1], "seq": r[2], "attempts": r[3],
                 "text": json.loads(r[4])["payload"]["text"]} for r in rows]

    def ack(self, op_ids: list[str]) -> None:
        with self.lock:
            self.conn.executemany("UPDATE outbox SET state='acked' WHERE op_id=?", [(o,) for o in op_ids])

    def fail(self, op_ids: list[str]) -> None:
        """Exponential backoff, capped at 30 s."""
        with self.lock:
            for o in op_ids:
                self.conn.execute(
                    "UPDATE outbox SET attempts=attempts+1, next_try=? WHERE op_id=?",
                    (time.time() + min(2 ** (self._attempts(o) + 1), 30), o))

    def retry_now(self) -> None:
        with self.lock:
            self.conn.execute("UPDATE outbox SET next_try=0 WHERE state='pending'")

    def _attempts(self, op_id: str) -> int:
        row = self.conn.execute("SELECT attempts FROM outbox WHERE op_id=?", (op_id,)).fetchone()
        return row[0] if row else 0

    def depth(self) -> int:
        with self.lock:
            return self.conn.execute("SELECT COUNT(*) FROM outbox WHERE state='pending'").fetchone()[0]

    # ---- decision log ----------------------------------------------------------------
    def add_decision(self, op_id: str, text: str, d: dict) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO decisions(ts,op_id,text,by,residency,criticality,confidence,reason) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (time.time(), op_id, text, d["by"], d["residency"], d["criticality"], d["confidence"], d["reason"]))

    def decisions(self, limit: int = 100) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT ts,op_id,text,by,residency,criticality,confidence,reason FROM decisions "
                "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        keys = ("ts", "op_id", "text", "by", "residency", "criticality", "confidence", "reason")
        return [dict(zip(keys, r)) for r in rows]
