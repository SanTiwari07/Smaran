"""Small deterministic date/time parser for phrases like "tomorrow evening" or "in 2 days".

Runs on the device with no model, so reminders and deadlines work offline. `now` is passed in,
which keeps tests and the demo clock reproducible.
"""
import re
from datetime import datetime, timedelta

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
PARTS = {"morning": 9, "noon": 12, "afternoon": 15, "evening": 18, "tonight": 21, "night": 21, "eod": 17}


def _clock(text: str) -> tuple[int, int] | None:
    m = re.search(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text) or \
        re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\b", text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    ap = m.group(3) if m.lastindex and m.lastindex >= 3 else None
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return (h, mi) if h < 24 and mi < 60 else None


def parse_due(text: str, now: datetime) -> float | None:
    """Return a unix timestamp for the time the text refers to, or None if it names none."""
    t = text.lower()
    day: datetime | None = None
    if re.search(r"\bday after tomorrow\b", t):
        day = now + timedelta(days=2)
    elif re.search(r"\btomorrow\b", t):
        day = now + timedelta(days=1)
    elif re.search(r"\b(today|tonight|this evening|this afternoon|this morning)\b", t):
        day = now
    elif (m := re.search(r"\bin\s+(\d+)\s*(minute|min|hour|hr|day|week)s?\b", t)):
        n, unit = int(m.group(1)), m.group(2)
        if unit in ("minute", "min"):
            return (now + timedelta(minutes=n)).timestamp()
        if unit in ("hour", "hr"):
            return (now + timedelta(hours=n)).timestamp()
        day = now + timedelta(days=n * (7 if unit == "week" else 1))
    elif (m := re.search(r"\b(?:next\s+|on\s+|this\s+|by\s+)?(" + "|".join(DAYS) + r")\b", t)):
        ahead = (DAYS.index(m.group(1)) - now.weekday()) % 7
        if ahead == 0 or "next" in m.group(0):
            ahead = ahead or 7
        day = now + timedelta(days=ahead)
    elif (m := re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")[a-z]*\b", t)) or \
            (m2 := re.search(r"\b(" + "|".join(MONTHS) + r")[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b", t)):
        if m:
            d, mo = int(m.group(1)), MONTHS[m.group(2)]
        else:
            mo, d = MONTHS[m2.group(1)], int(m2.group(2))
        try:
            day = now.replace(month=mo, day=d)
        except ValueError:
            return None
        if day < now - timedelta(days=1):
            day = day.replace(year=now.year + 1)
    if day is None:
        return None
    clock = _clock(t)
    if clock is None:
        part = next((h for k, h in PARTS.items() if re.search(rf"\b{k}\b", t)), None)
        clock = (part, 0) if part is not None else (9, 0)
    return day.replace(hour=clock[0], minute=clock[1], second=0, microsecond=0).timestamp()


def query_window(text: str, now: datetime) -> tuple[float, float] | None:
    """A soft time window a question refers to ("last week"), used to boost, never to filter."""
    t = text.lower()
    day = timedelta(days=1)
    if "yesterday" in t:
        return (now - 2 * day).timestamp(), now.timestamp()
    if re.search(r"\blast week\b", t):
        return (now - 14 * day).timestamp(), (now - 3 * day).timestamp()
    if re.search(r"\b(this week|these days|recently|lately)\b", t):
        return (now - 7 * day).timestamp(), now.timestamp()
    if re.search(r"\blast month\b", t):
        return (now - 60 * day).timestamp(), (now - 14 * day).timestamp()
    if (m := re.search(r"\b(\d+|a few|few|couple of)\s+days ago\b", t)):
        n = int(m.group(1)) if m.group(1).isdigit() else 3
        return (now - (n + 2) * day).timestamp(), (now - max(n - 2, 0) * day).timestamp()
    return None


def human(ts: float | None, now: datetime | None = None) -> str:
    if ts is None:
        return "no date"
    d = datetime.fromtimestamp(ts)
    return d.strftime("%a %d %b, %I:%M %p").replace(" 0", " ")
