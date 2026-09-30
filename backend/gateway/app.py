"""Gateway HTTP API. Routes stay thin: parse, call Gateway, return."""
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from ..common.config import settings
from ..common.schema import ResolveIn, SearchIn, SyncBatch
from . import proofs
from .core import Gateway


def create_app(gw: Gateway) -> FastAPI:
    app = FastAPI(title="Smaran gateway")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health():
        return {"ok": True, "service": "gateway", "server": gw.server.describe()}

    @app.post("/sync")
    async def sync(request: Request):
        raw = await request.body()
        return gw.sync(SyncBatch.model_validate_json(raw), len(raw))

    @app.get("/changes")
    def changes(since: int = 0, limit: int = 500):
        return gw.changes(since, limit)

    @app.post("/search")
    def search(body: SearchIn):
        return gw.search(body.dense, body.bm25.model_dump(), body.limit)

    @app.get("/contested")
    def contested():
        return gw.contested()

    @app.post("/resolve")
    def resolve(body: ResolveIn):
        try:
            return gw.resolve(body.entity_key, body.op_id, body.text, body.author)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    @app.get("/audit")
    def audit():
        return gw.audit()

    @app.get("/stats")
    def stats():
        return gw.stats()

    @app.get("/memories")
    def memories(limit: int = 500):
        return gw.memories(limit)

    # ---- "Prove it": re-run a headline claim live (see proofs.py) ----------------------
    @app.get("/prove/conflicts")
    def prove_conflicts():
        return proofs.conflicts()

    @app.get("/prove/convergence")
    def prove_convergence(runs: int = Query(100, ge=1, le=1000)):
        return proofs.convergence(runs)

    @app.post("/prove/idempotency")
    def prove_idempotency():
        return proofs.idempotency(gw)

    @app.get("/prove/benchmarks")
    def prove_benchmarks():
        return proofs.benchmarks()

    @app.post("/admin/reset")
    def reset(seed: bool = True):
        gw.reset()
        n = gw.seed(settings.path(settings.seed_dir)) if seed else 0
        return {"ok": True, "seeded": n}

    @app.post("/admin/seed")
    def seed():
        return {"seeded": gw.seed(settings.path(settings.seed_dir))}

    return app
