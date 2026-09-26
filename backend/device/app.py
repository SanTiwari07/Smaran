"""Device HTTP API. Routes stay thin: parse, call Device, return."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ..common.config import MACHINES
from ..common.schema import SHARDS, NoteIn, OnlineIn
from .core import Device
from .hermes import Hermes


def create_app(device: Device, hermes: Hermes | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app):
        if hermes:
            hermes.start()
        yield
        if hermes:
            hermes.stop()
        device.close()

    app = FastAPI(title=f"Smaran device {device.id}", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"ok": True, "service": f"device-{device.id}", "online": device.online,
                "gateway": str(getattr(device.http, "base_url", None))}

    @app.get("/state")
    def state():
        return device.state()

    @app.get("/machines")
    def machines():
        return MACHINES

    @app.post("/online")
    def set_online(body: OnlineIn):
        device.set_online(body.online)
        if hermes and body.online:
            hermes.poke()
        return device.state()

    @app.post("/notes")
    def add_note(note: NoteIn):
        out = device.add_note(note)
        if hermes and device.online:
            hermes.poke()
        return out

    @app.get("/search")
    def search(q: str, limit: int = 10, at: float | None = None, include_superseded: bool = False):
        return device.search(q, limit, at, include_superseded)

    @app.get("/memories")
    def memories(shard: str | None = None, status: str | None = None, machine: str | None = None):
        if shard and shard not in SHARDS:
            raise HTTPException(400, f"shard must be one of {SHARDS}")
        return device.memories(shard, status, machine)

    @app.get("/outbox")
    def outbox():
        return device.db.pending()

    @app.get("/decisions")
    def decisions(limit: int = 100):
        return device.db.decisions(limit)

    @app.get("/activity")
    def activity(limit: int = Query(100, le=300)):
        return list(device.activity)[:limit]

    @app.get("/history")
    def history(at: float | None = None, entity_key: str | None = None):
        return device.history(at or time.time(), entity_key)

    @app.post("/sync-now")
    def sync_now():
        if not device.online:
            raise HTTPException(409, "device is offline")
        if hermes is None:
            raise HTTPException(503, "sync worker not running")
        return hermes.sync_once()

    @app.post("/admin/reset")
    def reset(online: bool = True):
        if hermes:
            with hermes.lock:          # never wipe mid-sync, or a stale pull could write back
                device.reset()
        else:
            device.reset()
        device.set_online(online)
        return device.state()

    return app
