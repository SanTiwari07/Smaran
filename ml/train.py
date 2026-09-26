"""Train and evaluate the residency classifier; publish every number.

    python -m ml.data.gen_notes      # 200 template notes (training only)
    python -m ml.train               # -> ml/artifacts/residency.joblib + report.json

Test set = the first 60 hand-written notes (h001..h060). They are never used in training,
and template phrasing never reaches the test set.

Compared on that test set:
  rules-only       KeywordClassifier behind the full router (PII rules + safety floor)
  logreg (alone)   the model's raw proposal, no rules
  logreg + rules   what ships: PII rules -> logreg -> router rules
Also reports Cohen's kappa if a second labeller filled residency_2 / criticality_2.
"""
import csv
import json
import time
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, recall_score

from backend.common.schema import NoteIn
from backend.device.classifier import KeywordClassifier, LogRegClassifier
from backend.device.embed import get_embedder
from backend.device.router import Router

DATA = Path(__file__).parent / "data"
ART = Path(__file__).parent / "artifacts"
TEST_IDS = {f"h{i:03d}" for i in range(1, 61)}


class _NoDedup:
    def nearest(self, *a, **k):
        return []


def load() -> tuple[list[dict], list[dict], list[dict]]:
    with (DATA / "handwritten_notes.csv").open(encoding="utf8") as f:
        hand = list(csv.DictReader(f))
    tpl_path = DATA / "template_notes.csv"
    if not tpl_path.exists():
        from ml.data.gen_notes import main as gen
        gen()
    with tpl_path.open(encoding="utf8") as f:
        tpl = list(csv.DictReader(f))
    test = [r for r in hand if r["id"] in TEST_IDS]
    train = tpl + [r for r in hand if r["id"] not in TEST_IDS]
    return train, test, hand


def note(r: dict) -> NoteIn:
    return NoteIn(text=r["text"], kind=r["kind"], machine=r["machine"] or None)


def scores(y_true, y_pred, c_true, c_pred) -> dict:
    return {"residency_acc": round(accuracy_score(y_true, y_pred), 3),
            "residency_macro_f1": round(f1_score(y_true, y_pred, average="macro"), 3),
            "criticality_acc": round(accuracy_score(c_true, c_pred), 3),
            "safety_recall": round(recall_score(c_true, c_pred, labels=[2], average=None)[0], 3)}


def main() -> None:
    train, test, hand = load()
    emb = get_embedder("fastembed")
    t = time.perf_counter()
    X_train = emb.dense([r["text"] for r in train])
    X_test = emb.dense([r["text"] for r in test])
    embed_s = time.perf_counter() - t

    res = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced").fit(X_train, [r["residency"] for r in train])
    crit = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced").fit(X_train, [int(r["criticality"]) for r in train])
    ART.mkdir(exist_ok=True)
    path = ART / "residency.joblib"
    joblib.dump({"residency": res, "criticality": crit,
                 "meta": {"trained_on": len(train), "embedder": emb.name, "ts": time.time()}}, path)

    y = [r["residency"] for r in test]
    c = [int(r["criticality"]) for r in test]
    report = {"n_train": len(train), "n_test": len(test), "embed_seconds": round(embed_s, 2)}

    rules = Router(KeywordClassifier(), _NoDedup())
    d = [rules.decide(note(r), x) for r, x in zip(test, X_test)]
    report["rules-only"] = scores(y, [x.residency for x in d], c, [x.criticality for x in d])

    report["logreg (alone)"] = scores(y, list(res.predict(X_test)), c, [int(v) for v in crit.predict(X_test)])

    shipped = Router(LogRegClassifier(path), _NoDedup())
    t = time.perf_counter()
    d = [shipped.decide(note(r), x) for r, x in zip(test, X_test)]
    per_note_ms = (time.perf_counter() - t) * 1000 / len(test)
    report["logreg + rules (shipped)"] = scores(y, [x.residency for x in d], c, [x.criticality for x in d])
    report["decide_ms_per_note"] = round(per_note_ms, 3)
    report["errors"] = [{"id": r["id"], "text": r["text"], "label": r["residency"], "got": x.residency, "by": x.by}
                        for r, x in zip(test, d) if x.residency != r["residency"]]

    two = [r for r in hand if r["id"] in TEST_IDS and r.get("residency_2")]
    report["label_agreement"] = (
        {"n": len(two), "residency_kappa": round(cohen_kappa_score([r["residency"] for r in two], [r["residency_2"] for r in two]), 3),
         "criticality_kappa": round(cohen_kappa_score([r["criticality"] for r in two], [r["criticality_2"] for r in two]), 3)}
        if len(two) >= 10 else "not measured yet: a second labeller should fill residency_2 / criticality_2 for h001..h060")

    (ART / "report.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(f"\ntrain={len(train)} test={len(test)} (hand-written only)\n")
    print("| Model | Residency acc | Residency macro-F1 | Criticality acc | Safety-critical recall |\n|---|---|---|---|---|")
    for k in ("rules-only", "logreg (alone)", "logreg + rules (shipped)"):
        s = report[k]
        print(f"| {k} | {s['residency_acc']} | {s['residency_macro_f1']} | {s['criticality_acc']} | {s['safety_recall']} |")
    print(f"\nlabel agreement: {report['label_agreement']}")
    print(f"errors ({len(report['errors'])}):")
    for e in report["errors"]:
        print(f"  {e['id']} label={e['label']} got={e['got']} by={e['by']}: {e['text'][:80]}")
    print(f"\nsaved {path}")


if __name__ == "__main__":
    main()
