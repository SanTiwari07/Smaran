"""Memory extraction: turn something the user said into structured memory candidates.

Pipeline (all rules, so it is instant, deterministic and works offline):

    utterance -> sentences -> [drop questions] -> classify -> score importance -> Candidate

Each Candidate says what kind of memory it is (episodic / semantic / procedural), which
subject (project, course) it belongs to, and, for facts that can change, a `slot`. The slot is
what lets a later "we switched to MySQL" replace an earlier "we use PostgreSQL" as a new
version of the same fact, and lets two devices that disagree be flagged as a conflict.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime

from .timeparse import parse_due

# canonical technology -> category. Categories double as decision slots.
TECH = {
    "database": ["postgresql", "postgres", "mysql", "sqlite", "mongodb", "mariadb", "firebase", "supabase", "redis"],
    "vector-store": ["qdrant", "pinecone", "weaviate", "chroma", "milvus", "faiss", "pgvector"],
    "frontend": ["react", "vue", "angular", "svelte", "nextjs", "next.js", "flutter", "tailwind"],
    "backend-framework": ["fastapi", "django", "flask", "express", "spring", "nestjs", "node"],
    "language": ["python", "java", "typescript", "javascript", "rust", "go", "kotlin", "c++"],
    "hosting": ["aws", "azure", "gcp", "vercel", "render", "heroku", "docker", "kubernetes"],
}
TECH_CATEGORY = {t: cat for cat, ts in TECH.items() for t in ts}
CANON = {"postgres": "PostgreSQL", "postgresql": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite",
         "mongodb": "MongoDB", "qdrant": "Qdrant", "fastapi": "FastAPI", "react": "React", "nextjs": "Next.js",
         "next.js": "Next.js", "aws": "AWS", "gcp": "GCP", "faiss": "FAISS", "pgvector": "pgvector"}

SUBJECT_HINTS = [
    (r"\b(final[- ]year project|capstone|major project|fyp)\b", "capstone"),
    (r"\b(dbms|database (?:systems|course|assignment))\b", "dbms"),
    (r"\b(operating systems?|os assignment)\b", "os"),
    (r"\b(machine learning|ml course|ml assignment)\b", "ml-course"),
    (r"\b(hackathon)\b", "hackathon"),
    (r"\b(internship)\b", "internship"),
]

QUESTION = re.compile(r"(\?\s*$)|^\s*(what|when|where|who|why|how|which|did|do|does|can you|could you|"
                      r"is there|are there|tell me|show me|remind me what|list)\b", re.I)
DECISION = re.compile(r"\b(we(?:'re| are)? (?:using|going with|use)|we (?:decided|chose|picked|selected|agreed)|"
                      r"decided to|going with|switch(?:ed|ing)? to|settled on|let's (?:use|go with)|i(?:'ll| will) use|"
                      r"we should (?:use|go with|switch to|move (?:\w+\s){0,3}?to|migrate (?:\w+\s){0,3}?to|adopt)|"
                      r"(?:move|migrate)(?:d)? (?:\w+\s){0,3}?to)\b", re.I)
# a proposal ("I think we should...") is a weaker signal than a settled choice ("we chose...")
TENTATIVE = re.compile(r"\b(i think|maybe|perhaps|might|should|consider(?:ing)?|thinking (?:of|about)|how about|probably)\b", re.I)
SETTLED = re.compile(r"\b(?:we|i)(?:'re| are)?\s+(?:decided|chose|picked|selected|agreed|going with|using)\b", re.I)
REASON = re.compile(r"\b(?:because(?: of)?|since|due to|so that|given that|in order to)\s+(.+?)\s*$|"
                    r"\bas\s+(we\s+(?:need|want|require|expect)\s+.+?)\s*$", re.I)
CLAUSE_SPLIT = re.compile(r",\s*(?:and\s+|but\s+)?(?=(?:we|i|our|my)\b)|\s+and\s+(?=we\b)", re.I)
PROJECT_NAME = re.compile(r"\b[Pp]roject\s+([A-Z][A-Za-z0-9]{2,})\b")
NAMED_PROJECT = re.compile(r"\b(?:project|app|product|system)\s+(?:called|named|codenamed)\s+([A-Z][A-Za-z0-9]{2,})\b")
PREFERENCE = re.compile(r"\b(i (?:prefer|like|love|hate|always|usually|never|tend to)|my favou?rite|i work best|"
                        r"i study (?:best|better)|please always|from now on)\b", re.I)
OBLIGATION = re.compile(r"\b(i (?:need|have|must|should|gotta|ought) to|need to|have to|todo|to-do|"
                        r"don't forget to|remember to|i still (?:need|have) to|remaining:)\b", re.I)
MEETING = re.compile(r"\b(meeting|stand-?up|sync|review|viva|lecture|class|demo|call|interview|lab)\b", re.I)
TIME_OF_DAY = re.compile(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}:\d{2})\b", re.I)
ROLE = re.compile(r"\b(handles?|responsible for|working on|in charge of|owns?|will handle|i'?ll handle|teammate|"
                  r"team ?mate|partner|mentor|guide|supervisor)\b", re.I)
EXPLICIT = re.compile(r"\b(remember|important|note that|keep in mind|don't forget)\b", re.I)
GREETING = re.compile(r"^\s*(hi|hello|hey|thanks|thank you|ok|okay|cool|nice|good (?:morning|night|evening))\W*$", re.I)


@dataclass
class Candidate:
    text: str
    kind: str                   # decision | task | fact | preference | event | note
    memory_type: str            # episodic | semantic | procedural
    subject: str | None = None
    slot: str | None = None
    importance: float = 0.3
    confidence: float = 0.7
    entities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    fields: dict = field(default_factory=dict)
    why: str = ""               # which rule fired, shown in the trace


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+|;\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 2]


def clauses(s: str) -> list[str]:
    """'I handle the backend, we're using FastAPI, and we chose PostgreSQL because ...' is three
    statements. Only sentences that carry a decision are split, so other text is unaffected."""
    if not DECISION.search(s):
        return [s]
    parts = [p.strip(" ,") for p in CLAUSE_SPLIT.split(s) if p and p.strip(" ,")]
    return parts or [s]


def find_reason(s: str) -> str | None:
    m = REASON.search(s)
    if not m:
        return None
    r = (m.group(1) or m.group(2) or "").strip(" .,;")
    return r if len(r) >= 4 else None


def decision_confidence(s: str, reason: str | None) -> tuple[float, list[dict]]:
    """Deterministic, and explainable part by part (shown in the memory's provenance):
    a settled choice starts at 0.85, a proposal at 0.60, and a stated reason adds 0.05."""
    tentative = bool(TENTATIVE.search(s)) and not SETTLED.search(s)
    base = 0.60 if tentative else 0.85
    parts = [{"label": "proposal wording" if tentative else "settled-choice wording", "value": base}]
    if reason:
        parts.append({"label": "a reason was stated", "value": 0.05})
    return round(sum(p["value"] for p in parts), 2), parts


def find_tech(s: str) -> list[str]:
    low = s.lower()
    found = []
    for t in TECH_CATEGORY:
        if re.search(rf"(?<![\w.]){re.escape(t)}(?![\w])", low):
            found.append(t)
    return found


def subject_label(slug: str | None) -> str:
    """'project-nova' -> 'Project Nova'; other slugs are shown as they are."""
    if slug and slug.startswith("project-"):
        return "Project " + slug[len("project-"):].replace("-", " ").title()
    return slug or "general"


def find_subject(s: str, default: str | None) -> str | None:
    m = NAMED_PROJECT.search(s) or PROJECT_NAME.search(s)
    if m:
        return "project-" + m.group(1).lower()
    for rx, name in SUBJECT_HINTS:
        if re.search(rx, s, re.I):
            return name
    return default


def find_entities(s: str) -> list[str]:
    ents = [CANON.get(t, t.title()) for t in find_tech(s)]
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]{2,}(?:\s[A-Z][a-z]+)*)\b", s):
        w = m.group(1)
        if w not in ents and w.lower() not in {"i", "we", "the", "my", "tomorrow", "today", "monday", "tuesday",
                                               "wednesday", "thursday", "friday", "saturday", "sunday"}:
            ents.append(w)
    return list(dict.fromkeys(ents))[:8]


def clean_task_title(s: str) -> str:
    t = re.sub(r"^(?:and\s+|also\s+|then\s+)?", "", s.strip(), flags=re.I)
    t = re.sub(r"\b(?:i\s+(?:still\s+)?(?:need|have|must|should|gotta|ought)\s+to|need to|have to|don't forget to|"
               r"remember to|todo:?|to-do:?|remaining:)\s*", "", t, flags=re.I)
    t = re.sub(r"\b(?:by|before|on|due|until)\s+(?:tomorrow|today|tonight|next\s+\w+|\w+day|\d{1,2}\s+\w+)\b.*$", "", t, flags=re.I)
    t = re.sub(r"\b(?:tomorrow|today|tonight)(?:\s+(?:morning|afternoon|evening|night))?\b", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" .,-")


VERBS = (r"(?:finish|write|complete|prepare|submit|fix|review|update|implement|test|deploy|read|study|revise|build|create|add|set up|"
         r"install|draft|design|call|email|send|book|practice|push|merge|refactor|document|record|plan|clean)")


def split_tasks(title: str) -> list[str]:
    """'finish the API integration and write the schema' is two tasks, not one."""
    parts = re.split(rf"\s*(?:,|\band\b)\s+(?={VERBS}\b)", title, flags=re.I)
    return [p.strip(" .,") for p in parts if p.strip(" .,")]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "item"


def importance(kind: str, s: str, entities: list[str], due: float | None) -> float:
    score = {"decision": 0.6, "task": 0.5, "fact": 0.45, "preference": 0.55, "event": 0.3, "note": 0.25}.get(kind, 0.3)
    if due is not None:
        score += 0.2
    if EXPLICIT.search(s):
        score += 0.15
    score += min(len(entities), 3) * 0.04
    if re.search(r"\d", s):
        score += 0.05
    return round(min(score, 1.0), 2)


def extract(utterance: str, now: datetime, subject: str | None = None) -> list[Candidate]:
    out: list[Candidate] = []
    active = find_subject(utterance, subject)
    for s in [c for sent in sentences(utterance) for c in clauses(sent)]:
        if GREETING.match(s) or QUESTION.search(s):
            continue
        explicit = find_subject(s, None)
        subj = explicit or active
        active = subj
        ents = find_entities(s)
        techs = find_tech(s)
        due = parse_due(s, now)

        if DECISION.search(s) and techs:
            reason = find_reason(s)
            tentative = bool(TENTATIVE.search(s)) and not SETTLED.search(s)
            conf, _ = decision_confidence(s, reason)
            by_cat: dict[str, list[str]] = {}
            for t in techs:
                by_cat.setdefault(TECH_CATEGORY[t], []).append(CANON.get(t, t))
            for cat, names in by_cat.items():
                joined = " and ".join(dict.fromkeys(names))
                why_txt = f" Reason: {reason}." if reason else ""
                out.append(Candidate(
                    text=f"Decision{f' ({subject_label(subj)})' if subj else ''}: use {joined} as the {cat.replace('-', ' ')}."
                         f"{why_txt} Original: {s}",
                    kind="decision", memory_type="semantic", subject=subj, slot=f"decision:{cat}",
                    importance=importance("decision", s, ents, None), confidence=conf,
                    entities=ents, tags=["decision", cat],
                    fields={"category": cat, "decision_value": joined, "reason": reason, "evidence": s,
                            "stance": "proposal" if tentative else "decided",
                            "basis": f"decision phrase + {cat} technology"},
                    why=f"decision phrase + {cat} technology" + (" + stated reason" if reason else "")))
            continue

        m = OBLIGATION.search(s)
        if m:
            made = 0
            for title in split_tasks(clean_task_title(s)):
                if len(title) >= 3:
                    made += 1
                    out.append(Candidate(
                        text=f"TODO: {title}", kind="task", memory_type="episodic", subject=subj,
                        slot=f"task:{slugify(title)}",
                        importance=importance("task", s, ents, due), confidence=0.8, entities=ents, tags=["task"],
                        fields={"title": title, "task_id": slugify(title), "task_status": "open", "due": due},
                        why="obligation phrase -> task"))
            if made:
                continue

        if MEETING.search(s) and TIME_OF_DAY.search(s):
            mt = MEETING.search(s).group(1).lower()
            lead = re.search(r"\b(?:the\s+)?([\w-]+(?:\s[\w-]+)?)\s+" + mt, s, re.I)
            who = slugify(lead.group(1)) if lead and lead.group(1).lower() not in {"a", "the", "our", "my", "is", "has", "have"} else "team"
            out.append(Candidate(
                text=s.rstrip("."), kind="fact", memory_type="semantic", subject=subj, slot=f"schedule:{who}-{mt}",
                importance=importance("fact", s, ents, due) + 0.1, confidence=0.85, entities=ents,
                tags=["schedule", mt], fields={"when_text": TIME_OF_DAY.search(s).group(1), "due": due},
                why="meeting + clock time -> schedule slot"))
            continue

        if PREFERENCE.search(s):
            out.append(Candidate(text=s.rstrip("."), kind="preference", memory_type="procedural", subject=None,
                                 importance=importance("preference", s, ents, None), confidence=0.85, entities=ents,
                                 tags=["preference"], why="preference phrase -> procedural memory"))
            continue

        if ROLE.search(s) or techs or explicit:
            out.append(Candidate(text=s.rstrip("."), kind="fact", memory_type="semantic", subject=subj,
                                 importance=importance("fact", s, ents, due), confidence=0.75, entities=ents,
                                 tags=["fact"] + (["team"] if ROLE.search(s) else []), why="fact about a project or person"))
            continue

        if len(s.split()) >= 4:
            out.append(Candidate(text=s.rstrip("."), kind="event" if re.search(r"\b(today|yesterday|attended|discussed|met|learned|learnt|worked)\b", s, re.I) else "note",
                                 memory_type="episodic", subject=subj, importance=importance("event", s, ents, due),
                                 confidence=0.6, entities=ents, tags=["episode"], why="substantive statement -> episodic"))
    return merge_decisions(out)


def merge_decisions(cands: list[Candidate]) -> list[Candidate]:
    """One decision per slot in a message: "we're using PostgreSQL ... we chose PostgreSQL because
    X" is one decision, and the clause that gave a reason wins."""
    best: dict[str, Candidate] = {}
    for c in cands:
        if c.kind == "decision" and c.slot:
            cur = best.get(c.slot)
            if cur is None or (c.fields.get("reason") and not cur.fields.get("reason")) or                     bool(c.fields.get("reason")) == bool(cur.fields.get("reason")):
                best[c.slot] = c
    out, seen = [], set()
    for c in cands:
        if c.kind == "decision" and c.slot:
            if c.slot in seen or best[c.slot] is not c:
                continue
            seen.add(c.slot)
        out.append(c)
    return out
