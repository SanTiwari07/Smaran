"""The model router: where a request is answered, and why.

Routes, in order of preference:

1. local-slm   a small language model on this machine (Ollama, which runs llama.cpp)
2. extractive  no model at all: the answer is composed from the retrieved memories by rules
3. cloud       an OpenAI-compatible endpoint, only if configured AND online AND the request
               carries no private (Krypta) memory. It is an enhancement, never a dependency.

Everything that decides a route is recorded in the returned `route` dict, which the
dashboard shows and the tests assert on. A model failure downgrades to the next route; it
never raises into the user's request.
"""
import os
import re
import time
from dataclasses import dataclass, field

import httpx

from ..common.config import settings

SYSTEM = (
    "You are Smaran, a personal memory assistant running on the user's own device. "
    "Answer the question using ONLY the numbered memories provided. Be brief: 1-3 sentences, plain words. "
    "State the actual facts (names, dates, times) in full. After a sentence you may add the memory number in "
    "square brackets, like [2], but never write a number instead of a fact. "
    "If the memories do not contain the answer, say you don't have that in memory yet. Never invent facts."
)


@dataclass
class Route:
    route: str                  # local-slm | extractive | cloud
    model: str
    reason: str
    latency_ms: float = 0.0
    tried: list = field(default_factory=list)   # routes that failed first, with the error

    def as_dict(self) -> dict:
        return {"route": self.route, "model": self.model, "reason": self.reason,
                "latency_ms": round(self.latency_ms, 1), "tried": self.tried}


class LocalSLM:
    """Ollama's HTTP API on localhost. The model file lives on this machine; no data leaves it."""
    kind = "local-slm"

    def __init__(self, model: str | None = None, base_url: str | None = None, client: httpx.Client | None = None,
                 timeout: float = 60.0):
        self.model = model or settings.local_llm_model
        self.base_url = (base_url or settings.local_llm_url).rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)
        self._available: tuple[float, bool] = (0.0, False)

    def available(self, max_age: float = 5.0) -> bool:
        ts, ok = self._available
        if time.time() - ts < max_age:
            return ok
        try:
            r = self.client.get(f"{self.base_url}/api/tags", timeout=1.5)
            names = {m["name"] for m in r.json().get("models", [])}
            ok = self.model in names or f"{self.model}:latest" in names
        except Exception:  # noqa: BLE001
            ok = False
        self._available = (time.time(), ok)
        return ok

    def chat(self, messages: list[dict], json_mode: bool = False, max_tokens: int = 220) -> str:
        body = {"model": self.model, "messages": messages, "stream": False, "keep_alive": "30m",
                "options": {"temperature": 0.1, "num_predict": max_tokens, "num_ctx": 2048}}
        if json_mode:
            body["format"] = "json"
        r = self.client.post(f"{self.base_url}/api/chat", json=body)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    def warm(self) -> float:
        t0 = time.perf_counter()
        self.chat([{"role": "user", "content": "ok"}], max_tokens=1)
        return round((time.perf_counter() - t0) * 1000)


class GeminiLLM:
    """Google Gemini API (https://ai.google.dev/) for cloud LLM answers.
    Privacy invariant: private (Krypta) memories are NEVER sent to Gemini.
    """
    kind = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None,
                 client: httpx.Client | None = None, timeout: float = 30.0):
        self.key = api_key if api_key is not None else (settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", ""))
        self.model = model or settings.gemini_model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.base_url = (base_url or settings.gemini_url or os.environ.get("GEMINI_URL", "")).rstrip("/")
        if not self.base_url:
            self.base_url = "https://generativelanguage.googleapis.com"
        self.client = client or httpx.Client(timeout=timeout)

    def available(self) -> bool:
        return bool(self.key and self.key.strip())

    def chat(self, messages: list[dict], json_mode: bool = False, max_tokens: int = 300) -> str:
        # 1. Try Google's OpenAI-compatible endpoint
        try:
            r = self.client.post(
                f"{self.base_url}/v1beta/openai/chat/completions",
                headers={"authorization": f"Bearer {self.key}", "content-type": "application/json"},
                json={"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1})
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

        # 2. Native REST generateContent endpoint fallback
        system_text = ""
        user_text = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_text += content + "\n"
            elif role == "user":
                user_text.append(content)
            elif role == "assistant":
                user_text.append(f"Assistant: {content}")

        payload = {
            "contents": [{"parts": [{"text": "\n\n".join(user_text)}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text.strip()}]}
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.key}"
        r = self.client.post(url, json=payload)
        if r.status_code == 404 and "gemini-2.0-flash" in self.model:
            alt_url = f"{self.base_url}/v1beta/models/gemini-1.5-flash:generateContent?key={self.key}"
            r = self.client.post(alt_url, json=payload)
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts).strip()


class CloudLLM:
    """Any OpenAI-compatible chat endpoint (CLOUD_LLM_URL, CLOUD_LLM_KEY, CLOUD_LLM_MODEL)."""
    kind = "cloud"

    def __init__(self, client: httpx.Client | None = None):
        self.url, self.key, self.model = settings.cloud_llm_url, settings.cloud_llm_key, settings.cloud_llm_model
        self.client = client or httpx.Client(timeout=20.0)

    def available(self) -> bool:
        return bool(self.url and self.key)

    def chat(self, messages: list[dict], json_mode: bool = False, max_tokens: int = 300) -> str:
        r = self.client.post(f"{self.url.rstrip('/')}/chat/completions", headers={"authorization": f"Bearer {self.key}"},
                             json={"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def build_context(hits: list[dict], budget: int = 1400) -> tuple[str, list[dict]]:
    """Numbered memory lines for the prompt, cut to a character budget. Returns (text, used)."""
    lines, used, size = [], [], 0
    for h in hits:
        p = h["payload"]
        when = time.strftime("%d %b", time.localtime(p.get("valid_from") or 0))
        tag = f"[{len(used) + 1}] ({when}, {p.get('kind')}{', ' + p['subject'] if p.get('subject') else ''}) {p['text']}"
        if p.get("status") == "contested":
            tag += "  [CONFLICT: two versions exist]"
        if size + len(tag) > budget and used:
            break
        lines.append(tag)
        used.append(h)
        size += len(tag)
    return "\n".join(lines), used


class ModelRouter:
    def __init__(self, local: LocalSLM | None = None, cloud: CloudLLM | None = None,
                 gemini: GeminiLLM | None = None, online=lambda: True, use_local: bool = True):
        self.local = local if local is not None else LocalSLM()
        self.cloud = cloud if cloud is not None else CloudLLM()
        self.gemini = gemini if gemini is not None else GeminiLLM()
        self.online = online
        self.use_local = use_local

    # ---- status for the dashboard ----------------------------------------------------
    def status(self) -> dict:
        return {"local": {"model": self.local.model, "available": self.use_local and self.local.available(),
                          "runtime": "Ollama (llama.cpp)", "url": self.local.base_url},
                "gemini": {"model": self.gemini.model, "configured": self.gemini.available(),
                           "usable_now": self.gemini.available() and bool(self.online())},
                "cloud": {"model": self.cloud.model, "configured": self.cloud.available(),
                          "usable_now": self.cloud.available() and bool(self.online())},
                "policy": "local first; gemini/cloud only if configured, online, and no private memory in context"}

    # ---- answering -------------------------------------------------------------------
    def answer(self, question: str, hits: list[dict], prefer_cloud: bool = False, extra: str = "",
               cover: list[str] | None = None, provider: str | None = None) -> tuple[str, Route]:
        """`extra` is an authoritative structured fact block (e.g. the exact open-task list)
        that is put in front of the retrieved memories and used as the no-model answer."""
        context, used = build_context(hits)
        if extra:
            context = f"AUTHORITATIVE LIST (complete, use it as is):\n{extra}\n\nOther memories:\n{context}"
        private = any(h["shard"] == "krypta" for h in used)
        tried: list[dict] = []
        candidates: list[str] = []

        # If user or config explicitly prefers Gemini or cloud
        if (provider == "gemini" or prefer_cloud) and self.gemini.available() and self.online() and not private:
            candidates.append("gemini")
        if (provider == "cloud" or prefer_cloud) and self.cloud.available() and self.online() and not private:
            candidates.append("cloud")

        # Local on-device model (Ollama)
        if self.use_local and self.local.available() and provider != "gemini":
            candidates.append("local-slm")

        # Cloud / Gemini fallback if no local model is available
        if not prefer_cloud and self.gemini.available() and self.online() and not private and "local-slm" not in candidates and "gemini" not in candidates:
            candidates.append("gemini")
        if not prefer_cloud and self.cloud.available() and self.online() and not private and "local-slm" not in candidates and "cloud" not in candidates:
            candidates.append("cloud")

        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Memories:\n{context or '(none)'}\n\nQuestion: {question}"}]
        for route in candidates:
            if route == "gemini":
                llm = self.gemini
            elif route == "cloud":
                llm = self.cloud
            else:
                llm = self.local
            t0 = time.perf_counter()
            try:
                text = llm.chat(msgs)
                bad = ungrounded(text, len(used), used) or incomplete(text, cover or [])
                if bad:
                    tried.append({"route": route, "error": f"answer rejected by grounding check: {bad}"})
                    continue
                if text:
                    if route == "gemini":
                        why = "Gemini cloud answer; online, context verified non-private"
                    elif route == "cloud":
                        why = "cloud requested and allowed"
                    else:
                        why = "on-device model available; data stayed local"
                    return text, Route(route, llm.model, why, (time.perf_counter() - t0) * 1000, tried)
            except Exception as e:  # noqa: BLE001
                tried.append({"route": route, "error": str(e)[:120]})
        if not candidates:
            why = "no model available" + ("; private memory in context blocks cloud" if private else "")
        else:
            why = "model call failed"
        if private and (self.cloud.available() or self.gemini.available()):
            why += "; cloud/gemini blocked: private memory in context"
        t0 = time.perf_counter()
        text = extra or extractive_answer(question, used)
        return text, Route("extractive", "rules", why + " -> answered by rules from local memory",
                           (time.perf_counter() - t0) * 1000, tried)


def ungrounded(text: str, n_memories: int, used: list[dict]) -> str | None:
    """Cheap checks that an answer is tied to what was retrieved. Returns a reason, or None."""
    cited = [int(x) for x in re.findall(r"\[(\d+)\]", text)]
    if any(c < 1 or c > max(n_memories, 1) for c in cited):
        return "cites a memory number that does not exist"
    if used and re.search(r"don'?t have|do not have|no (?:information|memory)", text, re.I)             and used[0].get("score", 0) >= 0.6:
        return "says it has no memory although a strong match was retrieved"
    return None


def incomplete(text: str, items: list[str]) -> str | None:
    """An answer that lists an authoritative set must mention every item (by a distinctive word)."""
    low = text.lower()
    for it in items:
        words = [w for w in re.findall(r"[a-z0-9]+", it.lower()) if len(w) >= 5] or re.findall(r"[a-z0-9]+", it.lower())
        if words and not any(w in low for w in words):
            return f"leaves out '{it}' from the complete list"
    return None


def extractive_answer(question: str, used: list[dict]) -> str:
    """No-model fallback: state the best memories plainly, with dates. Always works offline."""
    if not used:
        return "I don't have anything about that in memory yet."
    def line(h):
        p = h["payload"]
        text = p["text"].split(" Original:")[0]
        when = time.strftime("%d %b", time.localtime(p.get("valid_from") or 0))
        flag = " (conflicting versions exist)" if p.get("status") == "contested" else ""
        return f"{text} ({when}){flag}"
    top = used[0]
    rest = [line(h) for h in used[1:3] if h.get("score", 1) >= 0.8 * used[0].get("score", 1)]
    out = f"From memory: {line(top)}"
    if rest:
        out += "\nAlso related: " + " | ".join(rest)
    return out


def parse_json_loose(text: str) -> dict | None:
    import json

    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                return None
    return None
