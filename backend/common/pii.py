"""Argus, layer 1: PII rules. A match forces a memory to stay private, whatever a model says.

The gateway runs the same rules again as defence in depth.
"""
import re

RULES: dict[str, re.Pattern] = {
    "phone_in": re.compile(r"(?<![\d-])(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d-])"),
    "phone_intl": re.compile(r"\+\d{1,3}[\s-]?\d{3,5}[\s-]?\d{3,5}[\s-]?\d{0,5}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "aadhaar": re.compile(r"(?<![\d-])\d{4}[\s-]\d{4}[\s-]\d{4}(?![\d-])|(?<![\d-])\d{12}(?![\d-])"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
}


def find_pii(text: str) -> list[str]:
    """Names of the rules that match, e.g. ['phone_in']. Empty list means no PII found."""
    return [name for name, rx in RULES.items() if rx.search(text)]


def redact(text: str) -> str:
    for rx in RULES.values():
        text = rx.sub("[redacted]", text)
    return text
