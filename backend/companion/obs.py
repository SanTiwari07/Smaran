"""Observability: one small record per AI request, kept in memory for the dashboard.

Answers, per request: which route (local/cloud/rules), which model, how long, what memory was
retrieved (top-k), which tools ran, and what the sync queue looked like at that moment.
"""
import threading
import time
from collections import deque


class Observer:
    def __init__(self, size: int = 200):
        self.traces: deque = deque(maxlen=size)
        self.lock = threading.Lock()

    def record(self, **fields) -> dict:
        t = {"ts": time.time(), **fields}
        with self.lock:
            self.traces.appendleft(t)
        return t

    def recent(self, limit: int = 50) -> list[dict]:
        with self.lock:
            return list(self.traces)[:limit]

    def summary(self) -> dict:
        with self.lock:
            ts = list(self.traces)
        routes: dict[str, int] = {}
        for t in ts:
            r = (t.get("route") or {}).get("route")
            if r:
                routes[r] = routes.get(r, 0) + 1
        return {"requests": len(ts), "routes": routes,
                "tools": sum(len(t.get("tools", [])) for t in ts)}
