"""Companion HTTP routes, mounted on the device app under /companion. Thin: parse, call, return."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .service import Companion


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    request_id: str | None = None
    prefer_cloud: bool = False
    provider: str | None = None     # "gemini" | "local" | "cloud"


class GeminiConfigIn(BaseModel):
    api_key: str
    model: str | None = None


class ConfirmIn(BaseModel):
    audit_id: int


class ResolveDecisionIn(BaseModel):
    id: str
    keep: str = Field(pattern="^(new|old)$")


class SeedIn(BaseModel):
    days: int = 5


def build_router(c: Companion) -> APIRouter:
    r = APIRouter(prefix="/companion")

    @r.post("/chat")
    def chat(body: ChatIn):
        return c.chat(body.text, body.request_id, body.prefer_cloud, body.provider)

    @r.post("/confirm")
    def confirm(body: ConfirmIn):
        return c.confirm(body.audit_id)

    @r.get("/recall")
    def recall(q: str, k: int = Query(5, ge=1, le=20), rerank: bool = True):
        return c.recall(q, k, rerank)

    @r.get("/tasks")
    def tasks():
        return c.tasks()

    @r.get("/briefing")
    def briefing():
        return c.briefing()

    @r.get("/conflicts")
    def conflicts():
        return c.conflicts()

    @r.get("/decisions")
    def decisions():
        return c.decisions()

    @r.get("/pending")
    def pending():
        return c.pending_decisions()

    @r.post("/decisions/resolve")
    def resolve_decision(body: ResolveDecisionIn):
        return c.resolve_decision(body.id, body.keep)

    @r.get("/explain")
    def explain(request_id: str | None = None, audit_id: int | None = None):
        out = c.explain(request_id, audit_id)
        if out is None:
            raise HTTPException(404, "no such request")
        return out

    @r.get("/memory/explain")
    def memory_explain(op_id: str):
        out = c.memory_explain(op_id)
        if out is None:
            raise HTTPException(404, "no such memory")
        return out

    @r.get("/lifecycle")
    def lifecycle():
        return c.lifecycle_report()

    @r.get("/status")
    def status():
        return c.status()

    @r.get("/audit")
    def audit(limit: int = Query(100, le=500)):
        return c.audit(limit)

    @r.get("/traces")
    def traces(limit: int = Query(50, le=200)):
        return c.obs.recent(limit)

    @r.get("/history")
    def history(limit: int = Query(50, le=200)):
        return c.chat_history(limit)

    @r.get("/tools")
    def tools():
        return [t.spec() for t in c.tools.values()]

    @r.post("/warmup")
    def warmup():
        if not c.router.local.available():
            raise HTTPException(503, "local model not available")
        return {"model": c.router.local.model, "ms": c.router.local.warm()}

    @r.post("/model")
    def model(use_local: bool):
        """Demo switch: take the local SLM out of the loop to show the rules-only fallback."""
        c.router.use_local = use_local
        return c.router.status()

    @r.post("/gemini/configure")
    def configure_gemini(body: GeminiConfigIn):
        """Configure or update the Google Gemini API key at runtime."""
        c.router.gemini.key = body.api_key.strip()
        if body.model:
            c.router.gemini.model = body.model.strip()
        return c.router.status()

    @r.post("/seed-story")
    def seed_story(body: SeedIn | None = None):
        from .story import load_story
        return load_story(c)

    @r.post("/seed-background")
    def seed_background():
        from .story import load_background
        return load_background(c)

    @r.get("/bench")
    def bench(n: int = Query(30, ge=5, le=200)):
        from .benchmark import quick
        return quick(c, n)

    return r
