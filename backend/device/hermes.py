"""Hermes: the sync worker. Carries memories to the gateway when the link is up.

Each tick, only while the device is online:
1. push: up to SYNC_BATCH pending outbox ops, most critical first -> POST /sync
2. pull: GET /changes?since=<last server_seq> -> ingest into Agora, re-run Themis locally
3. optimize the shards when the device has been idle for 10 s (Edge has no background optimizer)

Sending critical ops out of order is safe because Themis is order-independent.
"""
import json
import threading
import time

from ..common.config import settings


class Hermes:
    def __init__(self, device, interval: float = settings.sync_interval):
        self.dev = device
        self.interval = interval
        self.wake = threading.Event()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._run, name=f"hermes-{device.id}", daemon=True)
        self.lock = threading.Lock()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_flag.set()
        self.wake.set()
        self.thread.join(timeout=5)

    def poke(self) -> None:
        self.wake.set()

    def _run(self) -> None:
        while not self.stop_flag.is_set():
            try:
                if self.dev.online:
                    self.sync_once()
                if self.dev.store.dirty and time.time() - self.dev.last_write > 10:
                    self.dev.store.optimize()
            except Exception as e:  # noqa: BLE001  the worker must never die
                self.dev.log.error("hermes_tick_failed", error=repr(e))
            self.wake.wait(self.interval)
            self.wake.clear()

    def sync_once(self) -> dict:
        with self.lock:
            pushed = self.push()
            pulled = self.pull()
            if pushed.get("ok") and pulled.get("ok"):
                self.dev.db.set("last_sync", time.time())
                self.dev.db.set("last_error", None)
            return {"push": pushed, "pull": pulled}

    def push(self) -> dict:
        dev, total = self.dev, {"ok": True, "sent": 0, "results": {}}
        while True:
            due = dev.db.due(settings.sync_batch)
            if not due:
                return total
            body = {"device_id": dev.id, "ops": [b for _, b in due]}
            raw = json.dumps(body)
            ids = [o for o, _ in due]
            try:
                r = dev.http.post("/sync", content=raw, headers={"content-type": "application/json"})
                r.raise_for_status()
            except Exception as e:  # noqa: BLE001
                dev.db.fail(ids)
                dev.db.set("last_error", f"push: {e}")
                dev.log.error("push_failed", error=str(e), count=len(ids))
                return {**total, "ok": False, "error": str(e)}
            dev.db.incr("bytes_sent", len(raw))
            results = r.json()["results"]
            dev.db.ack([x["op_id"] for x in results])
            for x in results:
                total["results"][x["result"]] = total["results"].get(x["result"], 0) + 1
                dev.event("synced", op_id=x["op_id"], result=x["result"])
            total["sent"] += len(ids)

    def pull(self) -> dict:
        dev, n = self.dev, 0
        while True:
            since = dev.db.get("last_server_seq", 0)
            try:
                r = dev.http.get("/changes", params={"since": since, "limit": 500})
                r.raise_for_status()
            except Exception as e:  # noqa: BLE001
                dev.db.set("last_error", f"pull: {e}")
                dev.log.error("pull_failed", error=str(e))
                return {"ok": False, "pulled": n, "error": str(e)}
            data = r.json()
            if not data["points"]:
                return {"ok": True, "pulled": n}
            n += dev.ingest(data["points"])
            dev.db.set("last_server_seq", data["last_seq"])
            dev.event("pulled", count=len(data["points"]), last_seq=data["last_seq"])
