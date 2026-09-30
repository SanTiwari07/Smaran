"""The planner: from what the user said to a list of structured actions.

Two planners share one output shape (`Plan`):

1. Rules, always available, deterministic, instant. They cover the demo's verbs: remember,
   remind, add/finish/cancel a task, sync, connectivity, summarise, ask.
2. The local SLM, used only when the rules recognise an imperative but no pattern fits. It
   must answer in JSON `{"tool": ..., "args": {...}}`; whatever it says is then checked by the
   same validator as any other action, so a model mistake becomes a rejected action, never a
   change of state.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime

from .extract import QUESTION, clean_task_title, extract, sentences
from .llm import parse_json_loose
from .timeparse import parse_due

TIME_WORDS = re.compile(r"\b(tomorrow|today|tonight|this (?:morning|afternoon|evening)|day after tomorrow|next \w+day|"
                        r"(?:on |this |by )?(?:mon|tues|wednes|thurs|fri|satur|sun)day|in \d+ \w+|at \d{1,2}(?::\d{2})?\s*(?:am|pm)?|"
                        r"\d{1,2}(?::\d{2})?\s*(?:am|pm)|morning|afternoon|evening|night)\b", re.I)

IMPERATIVE = re.compile(r"^\s*(please\s+)?(create|add|set|update|mark|delete|remove|schedule|book|move|change|rename|"
                        r"cancel|finish|complete|close|push|reschedule|snooze)\b", re.I)


@dataclass
class Action:
    tool: str
    args: dict
    why: str = ""


@dataclass
class Plan:
    intent: str                                   # remember | action | ask | smalltalk
    actions: list[Action] = field(default_factory=list)
    question: str | None = None
    planner: str = "rules"
    notes: list[str] = field(default_factory=list)


def _strip_time(s: str) -> str:
    return re.sub(r"\s+", " ", TIME_WORDS.sub("", s)).strip(" .,-")


def plan_rules(text: str, now: datetime, subject: str | None) -> Plan | None:
    """Return a Plan, or None when no rule recognises the request."""
    t = text.strip()
    low = t.lower()

    if re.search(r"\b(sync|synchroni[sz]e)\b", low) and not QUESTION.search(t):
        return Plan("action", [Action("sync_now", {}, "user asked to sync")])
    if re.search(r"\b(am i|are we|is (?:the )?(?:internet|network|wi-?fi)|check (?:my |the )?(?:connection|connectivity|internet|network))\b.*", low) \
            and re.search(r"\b(online|offline|connected|connection|connectivity|internet|network)\b", low):
        return Plan("action", [Action("check_connectivity", {}, "connectivity question")])

    if (m := re.search(r"\bremind me\s+(?:to |about |that )?(.+)", t, re.I)) or \
            (m := re.search(r"\b(?:set|create|add)\s+(?:a\s+)?reminder\s+(?:to |for |about )?(.+)", t, re.I)):
        body = m.group(1)
        title = _strip_time(body)
        title = re.sub(r"^(?:to|that|about)\s+", "", title, flags=re.I)
        if len(title) >= 2:
            return Plan("action", [Action("set_reminder", {"title": title, "when": body, "subject": subject},
                                          "reminder request")])

    if (m := re.search(r"\b(?:mark|set)\s+(?:the\s+)?(.+?)\s+(?:task\s+)?as\s+(done|complete|completed|finished)\b", t, re.I)) or \
            (m := re.search(r"\b(?:i(?:'ve| have)?\s+)?(?:finished|completed|done with|wrapped up)\s+(?:the\s+|my\s+)?(.+)", t, re.I)) or \
            (m := re.search(r"\b(?:the\s+)?(.+?)\s+(?:task\s+)?is\s+(?:now\s+)?(?:done|complete|completed|finished)\b", t, re.I)):
        return Plan("action", [Action("update_task", {"match": clean_task_title(m.group(1)) or m.group(1), "status": "done"},
                                      "completion phrase")])

    if (m := re.search(r"\b(?:cancel|delete|remove|drop)\s+(?:the\s+)?(?:task\s+)?(.+)", t, re.I)) and not QUESTION.search(t):
        return Plan("action", [Action("cancel_task", {"match": m.group(1).strip(" .")}, "cancel request (needs confirmation)")])

    if (m := re.search(r"\b(?:add|create|new)\s+(?:a\s+)?(?:new\s+)?(?:task|todo|to-do)\s*(?:to|:|-)?\s*(.+)", t, re.I)) or \
            (m := re.search(r"\badd\s+(.+?)\s+to\s+(?:my\s+)?(?:tasks|to-?do(?:s| list)?)", t, re.I)):
        body = m.group(1)
        due = parse_due(body, now)
        title = _strip_time(body)
        return Plan("action", [Action("create_task", {"title": title, "subject": subject, "due": due}, "you asked for a task")])

    if (m := re.search(r"\b(?:summari[sz]e|summary of|status of|catch me up on|brief me on)\s+(?:my\s+|the\s+)?(.+)", t, re.I)):
        return Plan("action", [Action("summarize_project", {"subject": _subject_word(m.group(1), subject)}, "summary request")])

    return None


def _subject_word(s: str, fallback: str | None) -> str:
    if re.search(r"\b(project|capstone|final[- ]year)\b", s, re.I):
        return fallback or "capstone"
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-") or (fallback or "general")


def plan(text: str, now: datetime, subject: str | None) -> Plan:
    r = plan_rules(text, now, subject)
    if r:
        return r
    sents = sentences(text)
    questions = [s for s in sents if QUESTION.search(s)]
    statements = " ".join(s for s in sents if not QUESTION.search(s))
    actions: list[Action] = []
    if statements:
        for c in extract(statements, now, None):
            if c.kind == "task":
                actions.append(Action("create_task", {"title": c.fields["title"], "subject": c.subject,
                                                       "due": c.fields.get("due")}, f"auto-task: {c.why}"))
            else:
                actions.append(Action("store_memory", {
                    "text": c.text, "kind": c.kind, "memory_type": c.memory_type, "subject": c.subject,
                    "slot": c.slot, "importance": c.importance, "confidence": c.confidence, "entities": c.entities,
                    "tags": c.tags, "fields": c.fields}, c.why))
    if questions:
        return Plan("ask", actions, question=" ".join(questions), notes=["also remembered the statements"] if actions else [])
    if actions:
        return Plan("remember", actions)
    return Plan("smalltalk")


def llm_plan(slm, text: str, tools: dict) -> Plan | None:
    """Ask the local SLM for ONE tool call as JSON. The caller validates the result."""
    catalog = "\n".join(f"- {t.name}: {t.desc} args={list(t.spec()['args'])}" for t in tools.values() if t.risk != "destructive")
    prompt = ("Pick the single best tool for the user's request. Reply with JSON only: "
              '{"tool": "<name>", "args": {...}}. If nothing fits reply {"tool": null}.\nTools:\n' + catalog +
              f"\nRequest: {text}")
    try:
        obj = parse_json_loose(slm.chat([{"role": "user", "content": prompt}], json_mode=True, max_tokens=120))
    except Exception:  # noqa: BLE001
        return None
    if not obj or not obj.get("tool"):
        return None
    return Plan("action", [Action(str(obj["tool"]), obj.get("args") or {}, "chosen by local SLM")], planner="local-slm")
