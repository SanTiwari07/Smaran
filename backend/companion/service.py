"""Companion: the agent loop that ties memory, retrieval, models, tools and the audit log together.

    PERCEIVE  the user's words (stored encrypted in the chat log)
    PLAN      rules first; the local SLM only for imperatives the rules don't know
    RETRIEVE  hybrid search + rerank over local memory (questions and lookups)
    VALIDATE  registered tool? arguments match the schema? risk allowed?
    EXECUTE   a deterministic tool, idempotent, one audit row per action
    VERIFY    read the state back from the store and the outbox
    REMEMBER  the write itself is the memory; the audit row is the record of the action

Everything here runs on the device. Nothing in this file needs the network.
"""
import json
import threading
import time
import uuid
from datetime import datetime

from pydantic import ValidationError

from ..common.config import DEVICE_LABELS, settings
from ..common.crypto import Vault
from ..common.schema import AGORA, HERMES, KRYPTA
from . import decisions as dec
from . import planner as planner_mod
from . import provenance as prov
from .extract import extract, subject_label
from .lifecycle import lifecycle, summarize
from .llm import ModelRouter
from .obs import Observer
from .recall import recall as recall_fn
from .timeparse import human
from .tools import Tool, build_registry, current_tasks, verify

MAX_ACTIONS_PER_TURN = 8
NL = chr(10)
CONTEXT_TOOLS = {"create_task", "set_reminder", "update_task", "cancel_task"}


class Companion:
    def __init__(self, device, hermes=None, router: ModelRouter | None = None, clock=time.time, vault: Vault | None = None):
        self.dev = device
        self.hermes = hermes
        self.clock = clock
        self.vault = vault or Vault(device.root / "device.key")
        self.router = router or ModelRouter(online=lambda: device.online)
        self.obs = Observer()
        self.tools: dict[str, Tool] = build_registry()
        self.subjects: set[str] = set()
        self._local = threading.local()
        self._load_subjects()

    # ---- small state -----------------------------------------------------------------
    def _load_subjects(self) -> None:
        for shard in (KRYPTA, HERMES, AGORA):
            for r in self.dev.store.scroll(shard):
                if r.payload.get("subject") or r.payload.get("machine"):
                    self.subjects.add(r.payload.get("subject") or r.payload["machine"])

    def remember_subject(self, s: str | None) -> None:
        if s:
            self.subjects.add(s)
            self.dev.db.set("active_subject", s)

    def active_subject(self) -> str | None:
        return self.dev.db.get("active_subject")

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.clock())

    def ctx(self) -> dict:
        """Per-request scratch: the request id and the memories the request was grounded in."""
        c = getattr(self._local, "ctx", None)
        if c is None:
            c = self._local.ctx = {}
        return c

    def label(self) -> str:
        return DEVICE_LABELS.get(self.dev.id, f"Device {self.dev.id}")

    # ---- chat log + audit (encrypted at rest) ----------------------------------------
    def _log_chat(self, role: str, text: str) -> None:
        with self.dev.db.lock:
            self.dev.db.conn.execute("INSERT INTO chat(ts,role,text) VALUES(?,?,?)", (self.clock(), role, self.vault.seal(text)))

    def chat_history(self, limit: int = 50) -> list[dict]:
        with self.dev.db.lock:
            rows = self.dev.db.conn.execute("SELECT ts,role,text FROM chat ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"ts": r[0], "role": r[1], "text": self.vault.open(r[2])} for r in reversed(rows)]

    def _audit_find(self, idem: str):
        with self.dev.db.lock:
            return self.dev.db.conn.execute("SELECT id,state,result FROM audit WHERE idem=?", (idem,)).fetchone()

    def _audit_write(self, request_id, idem, tool, args, risk, state, result, verified, actor, op_ids) -> int:
        with self.dev.db.lock:
            cur = self.dev.db.conn.execute(
                "INSERT INTO audit(ts,request_id,idem,tool,args,risk,state,result,verified,actor,op_ids) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (self.clock(), request_id, idem, tool, self.vault.seal(json.dumps(args, default=str)), risk, state,
                 self.vault.seal(json.dumps(result, default=str)), None if verified is None else int(verified), actor, ",".join(op_ids)))
            return cur.lastrowid

    def audit(self, limit: int = 100) -> list[dict]:
        with self.dev.db.lock:
            rows = self.dev.db.conn.execute(
                "SELECT id,ts,request_id,tool,args,risk,state,result,verified,actor,op_ids FROM audit ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        out = []
        for r in rows:
            res = json.loads(self.vault.open(r[7]))
            out.append({"id": r[0], "ts": r[1], "request_id": r[2], "tool": r[3], "args": json.loads(self.vault.open(r[4])),
                        "risk": r[5], "state": r[6], "message": res.get("message"), "verified": r[8], "actor": r[9],
                        "op_ids": [o for o in (r[10] or "").split(",") if o]})
        return out

    # ---- retrieval -------------------------------------------------------------------
    def recall(self, q: str, k: int = 5, rerank_on: bool = True, allow_cloud: bool = True) -> dict:
        return recall_fn(self.dev, q, k, self.clock(), self.subjects, rerank_on, allow_cloud)

    # ---- the agent loop --------------------------------------------------------------
    def chat(self, text: str, request_id: str | None = None, prefer_cloud: bool = False) -> dict:
        t_start = time.perf_counter()
        request_id = request_id or uuid.uuid4().hex[:12]
        steps: list[dict] = []

        def step(name: str, detail: str, t0: float) -> None:
            steps.append({"step": name, "detail": detail, "ms": round((time.perf_counter() - t0) * 1000, 1)})

        t0 = time.perf_counter()
        self._log_chat("user", text)
        step("perceive", f"{len(text)} chars, link {'up' if self.dev.online else 'down'}, queue {self.dev.db.depth()}", t0)

        online_at_start = self.dev.online
        self._local.ctx = {"request_id": request_id, "context_ops": []}
        t0 = time.perf_counter()
        pend = dec.pending(self)
        verdict = dec.parse_verdict(text) if pend else None
        if verdict:
            pl = planner_mod.Plan("action", [planner_mod.Action("resolve_decision", {"id": pend[-1]["id"], "keep": verdict},
                                                                "answer to a pending contradiction")])
        else:
            pl = planner_mod.plan(text, self.now(), None)
        if (not verdict and planner_mod.IMPERATIVE.match(text) and pl.intent in ("smalltalk", "remember", "ask")
                and planner_mod.plan_rules(text, self.now(), None) is None
                and self.router.use_local and self.router.local.available()):
            alt = planner_mod.llm_plan(self.router.local, text, self.tools)     # the rules had no verb for this
            if alt:
                pl = alt
        step("plan", f"{pl.planner}: intent={pl.intent}, actions={[a.tool for a in pl.actions] or 'none'}", t0)

        results: list[dict] = []
        context: list[dict] = []
        if pl.intent == "action" and any(a.tool in CONTEXT_TOOLS for a in pl.actions):
            t0 = time.perf_counter()
            r0 = self.recall(text, k=4, allow_cloud=False)      # ground the action in what Smaran already knows
            context = self._compact_hits(r0["hits"])
            self._local.ctx["context_ops"] = [h["op_id"] for h in context if h["score"] >= 0.3][:4]
            step("context", f"{len(context)} relevant memories, active project {self.active_subject() or 'none'}", t0)
            subj = next((h["subject"] for h in context if h.get("subject") and h["semantic"] > 0.6), None) or self.active_subject()
            for act in pl.actions:
                if act.tool in ("create_task", "set_reminder") and not act.args.get("subject") and subj:
                    act.args["subject"] = subj
                    act.why += f"; filed under {subject_label(subj)}, " + ("the project of the closest matching memory" if subj != self.active_subject()
                                                                           else "the project you are working on")
        for i, act in enumerate(pl.actions[:MAX_ACTIONS_PER_TURN]):
            results.append(self.run_action(act.tool, act.args, f"{request_id}:{i}", request_id, steps, why=act.why))
        # a completion phrase that matched no task was probably just a statement
        if pl.intent == "action" and len(results) == 1 and results[0]["tool"] == "update_task" \
                and results[0]["state"] == "failed" and "couldn't find" in results[0]["message"]:
            alt = extract(text, self.now(), None)
            if alt:
                results.clear()
                pl = planner_mod.Plan("remember", [planner_mod.Action("store_memory", {
                    "text": c.text, "kind": c.kind, "memory_type": c.memory_type, "subject": c.subject,
                    "slot": c.slot, "importance": c.importance, "confidence": c.confidence, "entities": c.entities,
                    "tags": c.tags, "fields": c.fields}, c.why) for c in alt])
                for i, act in enumerate(pl.actions):
                    results.append(self.run_action(act.tool, act.args, f"{request_id}:f{i}", request_id, steps, why=act.why))

        rec, route = None, None
        answer_text = None
        provenance: list[dict] = []
        if pl.intent == "ask":
            t0 = time.perf_counter()
            rec = self.recall(pl.question or text, k=5)
            step("retrieve", f"{len(rec['hits'])} memories in {rec['timing_ms']['total']} ms ({rec['answered']})", t0)
            blocks: list[str] = []
            structured = None
            cover: list[str] = []
            why_res = None
            if dec.is_why_question(text):
                why_res = self.run_action("why_decision", {"query": text}, f"{request_id}:w", request_id, steps,
                                          why="why-question: look up the recorded decision and its reason")
                results.append(why_res)
                if why_res["state"] == "executed" and why_res.get("found"):
                    blocks.append(why_res["message"])
                    cover.append(why_res["decision"]["value"])
            if rec["understanding"]["open_tasks_only"] or "task" in rec["understanding"]["kinds"]:
                structured = self.run_action("list_tasks", {"status": "open"}, f"{request_id}:q", request_id, steps, why="structured lookup for a task question")
                results.append(structured)
                if structured["state"] == "executed":
                    blocks.append(structured["message"])
                    cover += [t["title"] for t in structured.get("tasks", []) if t.get("title")]
            t0 = time.perf_counter()
            extra = NL.join(blocks)
            answer_text, route = self.router.answer(pl.question or text, rec["hits"], prefer_cloud, extra, cover)
            step("answer", f"route={route.route} model={route.model} {route.latency_ms:.0f} ms", t0)
            context = self._compact_hits(rec["hits"])
            first = [why_res["op_id"]] if why_res and why_res.get("found") else []
            if structured and structured["state"] == "executed" and structured.get("tasks"):
                first += [t["op_id"] for t in structured["tasks"][:2]]      # a task answer is grounded in the tasks themselves
            for h in ([] if first else rec["hits"][:2]):
                if h["payload"]["op_id"] not in first and h["payload"].get("kind") in ("decision", "fact", "preference", "task"):
                    first.append(h["payload"]["op_id"])
            provenance = [e for e in (prov.explain_memory(self, o) for o in first[:2]) if e]

        reply = answer_text or self._compose_reply(pl, results)
        self._log_chat("assistant", reply)
        self._log_request(request_id, text, pl, online_at_start, route.as_dict() if route else None, context, reply)
        trace = self.obs.record(
            kind="chat", request=text[:120], route=route.as_dict() if route else {"route": "rules", "model": "planner", "reason": "no language model needed"},
            latency_ms=round((time.perf_counter() - t_start) * 1000, 1), planner=pl.planner, intent=pl.intent,
            topk=[{"op_id": h["payload"]["op_id"], "score": h["score"], "shard": h["shard"]} for h in (rec["hits"] if rec else [])],
            tools=[r["tool"] for r in results], sync={"queued": self.dev.db.depth(), "online": self.dev.online})
        return {"request_id": request_id, "reply": reply, "intent": pl.intent, "planner": pl.planner, "steps": steps,
                "actions": results, "retrieval": rec, "route": trace["route"], "latency_ms": trace["latency_ms"],
                "queued": self.dev.db.depth(), "online": self.dev.online, "online_at_start": online_at_start,
                "provenance": provenance, "context": context, "pending": dec.pending_views(self)}

    @staticmethod
    def _compact_hits(hits: list[dict]) -> list[dict]:
        return [{"op_id": h["payload"]["op_id"], "text": prov.clean(h["payload"]["text"])[:160], "kind": h["payload"].get("kind"),
                 "subject": h["payload"].get("subject"), "score": h["score"], "why": h.get("why", []), "shard": h["shard"],
                 "semantic": h["features"]["semantic"]} for h in hits]

    def _log_request(self, request_id, text, pl, online, route, context, reply) -> None:
        with self.dev.db.lock:
            self.dev.db.conn.execute(
                "INSERT OR REPLACE INTO request_log(request_id,ts,text,intent,planner,online,subject,route,context,reply) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (request_id, self.clock(), self.vault.seal(text), pl.intent, pl.planner, int(online), self.active_subject(),
                 json.dumps(route), self.vault.seal(json.dumps(context)), self.vault.seal(reply)))

    def _compose_reply(self, pl, results: list[dict]) -> str:
        if not results:
            return "I'm here. Tell me something to remember, ask me a question, or give me a task."
        msgs = []
        stored = [r for r in results if r["tool"] in ("store_memory",) and r["state"] == "executed" and not r.get("contradiction")]
        others = [r for r in results if r not in stored]
        if stored:
            kinds = sorted({a["args"].get("kind", "note") for a in [self._result_args(r) for r in stored]})
            msgs.append(f"Remembered {len(stored)} thing(s) ({', '.join(kinds)}).")
        for r in others:
            msgs.append(r["message"])
        if self.dev.db.depth():
            msgs.append(f"{self.dev.db.depth()} change(s) queued to sync" + ("" if self.dev.online else " (offline)") + ".")
        return " ".join(msgs)

    @staticmethod
    def _result_args(r: dict) -> dict:
        return {"args": r.get("args", {})}

    # ---- validate -> execute -> verify -> audit ------------------------------------------
    def run_action(self, tool_name: str, args: dict, idem: str, request_id: str, steps: list | None = None,
                   why: str = "", actor: str = "agent", confirmed: bool = False) -> dict:
        t0 = time.perf_counter()
        tool = self.tools.get(tool_name)
        base = {"tool": tool_name, "args": args, "risk": tool.risk if tool else "unknown", "why": why}

        def done(state, message, extra=None, verified=None, op_ids=()):
            res = {**base, "state": state, "message": message, **(extra or {}), "verified": verified}
            if state != "duplicate":
                res["audit_id"] = self._audit_write(request_id, idem, tool_name, args, base["risk"], state, res, verified, actor, list(op_ids))
            if steps is not None:
                steps.append({"step": "execute", "detail": f"{tool_name}({_short(args)}) -> {state}", "ms": round((time.perf_counter() - t0) * 1000, 1)})
                if verified is not None:
                    steps.append({"step": "verify", "detail": "ok" if verified else "FAILED: " + message, "ms": 0})
            return res

        if tool is None:
            return done("blocked", f"'{tool_name}' is not a registered tool")
        try:
            clean = tool.args(**args)
        except ValidationError as e:
            return done("blocked", "invalid arguments: " + "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:3]))
        prior = self._audit_find(idem)
        if prior and prior[1] in ("executed", "pending_confirmation") and not confirmed:
            res = json.loads(self.vault.open(prior[2]))
            return {**res, "state": "duplicate", "message": res.get("message", "") + " (already done: same request id)"}
        if tool.risk == "destructive" and not confirmed:
            return done("pending_confirmation", f"Please confirm: {tool_name} {_short(args)}", {"needs_confirmation": True})
        try:
            out = tool.fn(self, clean)
        except Exception as e:  # noqa: BLE001  a tool bug must not take the request down
            return done("failed", f"{tool_name} raised {type(e).__name__}: {e}")
        ok, detail = verify(self, tool_name, out)
        state = "executed" if out.get("ok") else "failed"
        return done(state, out.get("message", ""), {k: v for k, v in out.items() if k not in ("message", "ok")},
                    verified=ok if out.get("op_id") else None, op_ids=[out["op_id"]] if out.get("op_id") else ())

    def confirm(self, audit_id: int) -> dict:
        """Run a destructive action the user has just confirmed."""
        with self.dev.db.lock:
            row = self.dev.db.conn.execute("SELECT tool,args,request_id,idem FROM audit WHERE id=? AND state='pending_confirmation'",
                                           (audit_id,)).fetchone()
        if not row:
            return {"state": "blocked", "message": "no pending action with that id"}
        args = json.loads(self.vault.open(row[1]))
        with self.dev.db.lock:
            self.dev.db.conn.execute("UPDATE audit SET state='confirmed', idem=idem||'#confirmed' WHERE id=?", (audit_id,))
        return self.run_action(row[0], args, f"{row[3]}#run", row[2], actor="user", confirmed=True)

    # ---- views for the dashboard -------------------------------------------------------
    def tasks(self) -> list[dict]:
        rows = current_tasks(self)
        rows.sort(key=lambda r: (r.get("task_status") != "open", r.get("due") is None, r.get("due") or 0))
        return [{"op_id": r["op_id"], "task_id": r["task_id"], "title": r.get("title"), "status": r.get("task_status", "open"),
                 "due": r.get("due"), "due_text": human(r.get("due")) if r.get("due") else None, "subject": r.get("subject"),
                 "conflict": r["conflict"], "shard": r["shard"]} for r in rows]

    def briefing(self) -> dict:
        """Proactive: what needs attention now, without being asked."""
        now = self.clock()
        tasks = [t for t in self.tasks() if t["status"] == "open"]
        soon = [t for t in tasks if t["due"] and t["due"] - now < 48 * 3600]
        overdue = [t for t in tasks if t["due"] and t["due"] < now]
        conflicts = self.conflicts()
        items = []
        for t in overdue:
            items.append({"level": "alert", "text": f"Overdue: {t['title']} (was due {t['due_text']})"})
        for t in soon:
            if t not in overdue:
                items.append({"level": "info", "text": f"Coming up: {t['title']} ({t['due_text']})"})
        for c in conflicts:
            items.append({"level": "warn", "text": f"Conflict on {c['label']}: {len(c['versions'])} versions need your decision"})
        if self.dev.db.depth():
            items.append({"level": "info", "text": f"{self.dev.db.depth()} change(s) waiting to sync"})
        return {"items": items, "open_tasks": len(tasks)}

    def conflicts(self) -> list[dict]:
        """Contested facts as this device sees them, with a suggestion (never applied for you).

        The suggestion is evidence-based when it can be: another live memory that mentions exactly one
        of the competing times supports that version. Without such evidence the newest-by-clock version
        is offered as a weak hint and the message says the user has to decide."""
        groups: dict[str, list[dict]] = {}
        for shard in (HERMES, AGORA):
            for r in self.dev.store.scroll(shard):
                if r.payload.get("status") == "contested" and r.payload.get("entity_key"):
                    groups.setdefault(r.payload["entity_key"], []).append({"shard": shard, **r.payload})
        out = []
        for ek, vs in sorted(groups.items()):
            uniq = {v["op_id"]: v for v in vs}
            versions = sorted(uniq.values(), key=lambda v: v["valid_from"])
            newest = versions[-1]
            label = ek.split("/", 1)[-1].replace(":", " ")
            vinfo = [{"op_id": v["op_id"], "text": v["text"], "device": v["device_id"],
                      "device_label": DEVICE_LABELS.get(v["device_id"], v["device_id"]),
                      "at": v["valid_from"], "at_text": human(v["valid_from"]), "when": v.get("when_text")} for v in versions]
            explanation = (f"Both devices changed \u201c{label}\u201d while they could not see each other: "
                           + "; ".join(f"{v['device_label']} says {v['when'] or v['text']}" for v in vinfo)
                           + ". Neither change knew about the other, so Smaran kept both instead of picking one.")
            evidence = self._conflict_evidence(uniq, versions)
            if evidence:
                sugg = {"op_id": evidence["op_id"], "text": evidence["text"], "basis": "context",
                        "reason": f"another memory supports {evidence['when']}: \u201c{evidence['support_text']}\u201d. "
                                  "This is a suggestion only; you decide."}
            else:
                sugg = {"op_id": newest["op_id"], "text": newest["text"], "basis": "clock",
                        "reason": f"the {DEVICE_LABELS.get(newest['device_id'], newest['device_id'])} edit is the most recent by its own clock; "
                                  "clocks can be skewed and nothing else in memory supports either version, so this is a suggestion only and you decide"}
            out.append({"entity_key": ek, "label": label, "versions": vinfo, "explanation": explanation,
                        "why": "Both devices edited this while they could not see each other (their version vectors are concurrent).",
                        "evidence": evidence, "suggestion": sugg})
        return out

    def _conflict_evidence(self, uniq: dict, versions: list[dict]) -> dict | None:
        """A live memory (not one of the competing versions) that mentions exactly one competing time."""
        norm = lambda t: (t or "").lower().replace(" ", "")   # noqa: E731
        times = {norm(v.get("when_text")): v for v in versions if v.get("when_text")}
        if len(times) < 2:
            return None
        keys = {v.get("entity_key") for v in versions}
        found: dict[str, dict] = {}
        for shard in (HERMES, AGORA, KRYPTA):
            for r in self.dev.store.scroll(shard):
                q = r.payload
                if q["op_id"] in uniq or q.get("status") == "superseded" or q.get("entity_key") in keys:
                    continue
                low = norm(q["text"])
                hit = [t for t in times if t in low]
                if len(hit) == 1:
                    found.setdefault(hit[0], q)
        if len(found) != 1:
            return None
        t, q = next(iter(found.items()))
        v = times[t]
        return {"op_id": v["op_id"], "text": v["text"], "when": v.get("when_text"), "support_op_id": q["op_id"],
                "support_text": prov.clean(q["text"])[:140]}

    # ---- decisions, provenance, explanation, lifecycle ----------------------------------------
    def decisions(self) -> list[dict]:
        return dec.decisions(self)

    def pending_decisions(self) -> list[dict]:
        return dec.pending_views(self)

    def resolve_decision(self, pid: str, keep: str) -> dict:
        return self.run_action("resolve_decision", {"id": pid, "keep": keep}, f"resolve-{pid}-{keep}", uuid.uuid4().hex[:12],
                               why=f"user answered the pending contradiction: keep {keep}", actor="user")

    def memory_explain(self, op_id: str) -> dict | None:
        return prov.explain_memory(self, op_id)

    def explain(self, request_id: str | None = None, audit_id: int | None = None) -> dict | None:
        """Why did Smaran do that? User request -> relevant memory -> agent decision -> tool -> result."""
        with self.dev.db.lock:
            if request_id is None and audit_id is not None:
                row = self.dev.db.conn.execute("SELECT request_id FROM audit WHERE id=?", (audit_id,)).fetchone()
                request_id = row[0] if row else None
            row = self.dev.db.conn.execute(
                "SELECT request_id,ts,text,intent,planner,online,subject,route,context,reply FROM request_log WHERE request_id=?",
                (request_id,)).fetchone() if request_id else None
            acts = self.dev.db.conn.execute(
                "SELECT id,tool,args,risk,state,result,verified,actor,op_ids FROM audit WHERE request_id=? ORDER BY id",
                (request_id,)).fetchall() if request_id else []
        if row is None:
            return None
        rid, ts, text, intent, planner, online, subject, route, context, reply = row
        text, context, reply = self.vault.open(text), json.loads(self.vault.open(context)), self.vault.open(reply)
        route = json.loads(route) if route else None
        actions = []
        for a in acts:
            res = json.loads(self.vault.open(a[5]))
            actions.append({"audit_id": a[0], "tool": a[1], "args": json.loads(self.vault.open(a[2])), "risk": a[3], "state": a[4],
                            "message": res.get("message"), "why": res.get("why"), "verified": a[6], "actor": a[7],
                            "op_ids": [o for o in (a[8] or "").split(",") if o]})
        mode = "Offline (link off)" if not online else "Online"
        if route:
            model = f"{route['route']} ({route['model']}): {route['reason']}"
        else:
            model = "on-device rules planner, no language model needed" if planner == "rules" else f"{planner}"
        rel = [c for c in context if (subject and c["subject"] == subject) or c["semantic"] >= 0.6][:4] or context[:1]
        who = subject_label(subject) if subject else None
        mem_items = [c["text"] + (f"  [{', '.join(c['why'])}]" if c["why"] else "") for c in rel]
        if who:
            mem_items.append(f"Active project: {who}")
        def args_txt(a):
            shown = [f"{k}={v}" for k, v in list(a["args"].items())[:3] if v not in (None, "", [])]
            return f"{a['tool']}({', '.join(shown)}) [{a['risk']}]"
        chain = [
            {"stage": "User intent", "text": text},
            {"stage": "Relevant memory", "items": mem_items or ["nothing relevant in memory"]},
            {"stage": "Agent decision", "text": "; ".join(dict.fromkeys(a["why"] for a in actions if a.get("why"))) or f"intent: {intent}"},
            {"stage": "Tool", "items": [args_txt(a) for a in actions] or ["no tool needed"]},
            {"stage": "Result", "items": [f"{a['message']} \u2014 {a['state']}" + (", verified in the store" if a["verified"] else "")
                                          for a in actions] or [reply]},
        ]
        return {"request_id": rid, "ts": ts, "user_request": text, "intent": intent, "planner": planner, "mode": mode,
                "online": bool(online), "model": model, "active_subject": subject, "relevant_memories": rel,
                "actions": actions, "reply": reply, "chain": chain, "queued": self.dev.db.depth()}

    def lifecycle_report(self) -> dict:
        now = self.clock()
        every = {}
        for shard in (KRYPTA, HERMES, AGORA):
            for r in self.dev.store.scroll(shard):
                every[r.payload["op_id"]] = r.payload
        return summarize(list(every.values()), now)

    def connectivity(self) -> dict:
        reach, err = None, None
        if self.dev.online and self.dev.http is not None:
            try:
                reach = self.dev.http.get("/health", timeout=1.5).status_code == 200
            except Exception as e:  # noqa: BLE001
                reach, err = False, str(e)[:80]
        summary = ("Offline (link switched off): everything works locally, changes queue on this device."
                   if not self.dev.online else
                   "Online: gateway reachable." if reach else "Link is on but the gateway is not reachable; working locally.")
        return {"link": self.dev.online, "gateway_reachable": reach, "queued": self.dev.db.depth(), "error": err, "summary": summary}

    def status(self) -> dict:
        m = self.router.status()
        st = self.dev.state()
        counts = st["counts"]
        by_type: dict[str, int] = {}
        for shard in (KRYPTA, HERMES, AGORA):
            for r in self.dev.store.scroll(shard):
                t = r.payload.get("memory_type") or "unclassified"
                by_type[t] = by_type.get(t, 0) + 1
        return {"device": self.dev.id, "label": self.label(), "online": st["online"], "queued": st["outbox_depth"],
                "ai": {**m, "active_route": "local-slm" if m["local"]["available"] else "extractive"},
                "memory": {"counts": counts, "by_type": by_type, "index": "Qdrant Edge (dense bge-small + BM25)",
                           "embedder": st["embedder"], "encryption": {"chat_and_audit": "AES-256-GCM", "key": self.vault.protection,
                                                                       "shards": "not encrypted (use disk encryption)"}},
                "sync": {"queued": st["outbox_depth"], "acked": st["acked"], "last_sync": st["last_sync"], "last_error": st["last_error"],
                         "contested": st["contested"]}, "observability": self.obs.summary()}


def _short(args: dict) -> str:
    s = json.dumps(args, default=str)
    return s if len(s) < 90 else s[:87] + "..."
