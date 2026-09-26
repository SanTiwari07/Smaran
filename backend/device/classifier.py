"""Argus, layer 2: the residency classifier. It proposes; rules and Themis have the final word.

Every implementation sits behind the same interface, so switching is one line:
- KeywordClassifier: rules only, always available (the "rules only" baseline)
- LogRegClassifier:  scikit-learn heads on the bge-small embedding (trained by ml/train.py)
- LayaClassifier:    P2, not implemented; add it here behind the same interface
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..common.config import settings

SAFETY = re.compile(r"\b(fire|smoke|spark\w*|leak\w*|injur\w*|lockout|tagout|loto|overheat\w*|burn\w*|"
                    r"electric shock|shock hazard|guard (?:missing|removed|broken)|emergency stop|e-stop|"
                    r"gas|fume\w*|hydraulic burst|crush\w*|unsafe)\b", re.I)
IMPORTANT = re.compile(r"\b(fail\w*|broken|down|stopp\w*|alarm|error|fault|vibrat\w*|noise|crack\w*|"
                       r"worn|misalign\w*|jam\w*|downtime|urgent|replace\w*|abnormal)\b", re.I)
PERSONAL = re.compile(r"\b(my|wife|husband|son|daughter|family|salary|leave|sick|doctor|hospital|home|"
                      r"personal|loan|rent|birthday|appraisal|manager said|complain\w* about)\b", re.I)
CHITCHAT = re.compile(r"^(ok|okay|thanks|thank you|done|noted|hi|hello|good morning|lunch|tea|"
                      r"cricket|weekend|lol|haha|see you)\b|\b(lunch|tea break|cricket|canteen|weekend plans)\b", re.I)
MACHINE = re.compile(r"\b(cnc|lathe|press|robot|spindle|bearing|motor|pump|coolant|belt|sensor|axis|"
                     r"encoder|hydraulic|valve|filter|rpm|torque|calibrat\w*|firmware|plc|servo|gear\w*)\b", re.I)


def safety_floor(text: str) -> int:
    """Criticality the text must have at minimum, whatever a model predicts."""
    return 2 if SAFETY.search(text) else 0


def keyword_criticality(text: str) -> int:
    return 2 if SAFETY.search(text) else 1 if IMPORTANT.search(text) else 0


def combine_criticality(model: int, text: str) -> int:
    """Safety-critical if the model OR the safety keywords say so; otherwise the keyword level.

    Measured on the 60 held-out notes (ml/artifacts/report.json): the model alone catches
    more safety notes but over-flags routine ones; keywords alone miss safety notes. Missing
    a safety note is the worse error, so level 2 takes the union.
    """
    kw = keyword_criticality(text)
    return 2 if (model == 2 or kw == 2) else kw


@dataclass
class Prediction:
    residency: str      # private | sync | drop
    confidence: float
    criticality: int    # 0 routine | 1 important | 2 safety-critical


class ResidencyClassifier(Protocol):
    name: str

    def predict(self, text: str, dense: list[float]) -> Prediction: ...


class KeywordClassifier:
    name = "rules-only"

    def predict(self, text: str, dense: list[float] | None = None) -> Prediction:
        crit = keyword_criticality(text)
        if PERSONAL.search(text) and not MACHINE.search(text):
            return Prediction("private", 0.7, crit)
        if CHITCHAT.search(text) and not MACHINE.search(text):
            return Prediction("drop", 0.7, crit)
        if MACHINE.search(text) or crit:
            return Prediction("sync", 0.7, crit)
        return Prediction("sync", 0.4, crit)


class LogRegClassifier:
    name = "logreg-bge-small"

    def __init__(self, path: Path):
        import joblib

        bundle = joblib.load(path)
        self.res, self.crit = bundle["residency"], bundle["criticality"]
        self.meta = bundle.get("meta", {})

    def predict(self, text: str, dense: list[float]) -> Prediction:
        p = self.res.predict_proba([dense])[0]
        i = int(p.argmax())
        crit = int(self.crit.predict([dense])[0])
        return Prediction(str(self.res.classes_[i]), float(p[i]), crit)


def load_classifier(kind: str = "auto") -> ResidencyClassifier:
    path = settings.path("ml/artifacts/residency.joblib")
    if kind in ("auto", "logreg") and path.exists():
        return LogRegClassifier(path)
    if kind == "logreg":
        raise FileNotFoundError(f"{path} missing; run: python -m ml.train")
    return KeywordClassifier()
