"""The demo story's history: a student's first two weeks with Smaran.

`load_story` replays these utterances through the real agent loop (extraction, routing,
tools, audit), with the clock set back so they carry believable dates. Nothing is inserted
behind the pipeline's back, which makes it the same code path the live demo uses.
"""
import time

DAY = 86400

# (days ago, hour, utterance)
HISTORY = [
    (12, 10, "I'm working on my final-year project. We're using PostgreSQL and Qdrant. My teammate Aarav handles the frontend and I'll handle the backend."),
    (12, 10, "I need to finish the API integration and write the database schema."),
    (11, 22, "I prefer studying in the morning and I usually code late at night."),
    (10, 15, "Today's DBMS lecture covered normalization up to BCNF and functional dependencies."),
    (10, 16, "I have to submit the DBMS assignment by 12 Oct."),
    (9, 11, "The capstone review meeting is at 3 PM."),
    (8, 12, "We decided to use FastAPI for the backend."),
    (7, 14, "Today's operating systems lecture was about CPU scheduling: round robin and shortest job first."),
    (6, 17, "Discussed with our mentor that demo day is on 14 Oct, so we must freeze features by 10 Oct."),
    (5, 20, "Learned that we don't need pgvector because Qdrant already handles vector search for the project."),
    (5, 21, "My salary discussion with the manager at my internship is on Monday."),
    (4, 9, "Call Riya on 9876543210 about the Goa trip."),
    (4, 15, "Machine learning lecture today covered gradient descent and learning rate schedules."),
    (3, 18, "I need to prepare the capstone demo slides."),
    (2, 13, "Attended the hackathon info session; registration closes on 5 Oct and teams can have four members."),
]


# Older, transient material: it exists so the demo can show memory that has aged out (see lifecycle.py).
BACKGROUND = [
    (40, 10, "Attended the freshers orientation today and picked up my ID card."),
    (33, 16, "Today's computer networks lecture covered the OSI model layers."),
    (30, 9, "I need to collect the library card."),
    (28, 10, "I finished the library card."),
]


def _replay(c, items, tag) -> dict:
    real = c.clock
    t0 = time.perf_counter()
    stored = tasks = private = 0
    try:
        base = real()
        for days_ago, hour, text in items:
            day = base - days_ago * DAY
            lt = time.localtime(day)
            c.clock = lambda ts=time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, hour, 0, 0, 0, 0, -1)): ts
            out = c.chat(text, request_id=f"{tag}-{days_ago}-{hour}-{sum(map(ord, text)) % 10000}")
            for a in out["actions"]:
                if a["state"] == "executed":
                    stored += 1
                    tasks += a["tool"] in ("create_task", "set_reminder")
                    private += a.get("residency") == "private"
    finally:
        c.clock = real
    return {"utterances": len(items), "memories_written": stored, "tasks": tasks, "private": private,
            "ms": round((time.perf_counter() - t0) * 1000)}


def load_story(c) -> dict:
    """Replay HISTORY on companion `c`. Safe to call once per fresh device."""
    return _replay(c, HISTORY, "story")


def load_background(c) -> dict:
    """Replay BACKGROUND (aged-out material) through the same pipeline, so lifecycle has something to show."""
    return _replay(c, BACKGROUND, "background")
