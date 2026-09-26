"""JSON-lines logger: one file per service in logs/, plus a short line on stdout.

Trace one memory end to end with:  grep '"op_id": "A-000042"' logs/*.log
"""
import json
import sys
import threading
import time
from pathlib import Path

from .config import settings

_lock = threading.Lock()


class Log:
    def __init__(self, service: str, log_dir: Path | None = None):
        self.service = service
        d = log_dir or settings.path(settings.log_dir)
        d.mkdir(parents=True, exist_ok=True)
        self.file = d / f"{service}.log"

    def __call__(self, event: str, level: str = "info", **fields) -> dict:
        rec = {"ts": round(time.time(), 3), "service": self.service, "level": level, "event": event, **fields}
        line = json.dumps(rec, default=str, ensure_ascii=False)
        with _lock:
            with self.file.open("a", encoding="utf8") as f:
                f.write(line + "\n")
        short = " ".join(f"{k}={v}" for k, v in fields.items() if k in ("op_id", "entity_key", "status", "result", "error", "count"))
        print(f"[{self.service}] {level.upper():5} {event} {short}", file=sys.stderr, flush=True)
        return rec

    def error(self, event: str, **fields) -> dict:
        return self(event, level="error", **fields)
