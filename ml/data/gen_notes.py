"""Generate 200 labelled template notes -> ml/data/template_notes.csv

Templates are for TRAINING only. The test set comes only from hand-written notes, so
template phrasing can't leak into the score.

    python -m ml.data.gen_notes
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).with_name("template_notes.csv")
MACHINES = ["CNC-07", "CNC-12", "LATHE-03", "PRESS-02", "ROBOT-ARM-5"]
NAMES = ["Ravi", "Priya", "Suresh", "Anjali", "Imran", "Kavya", "Deepak", "Meena"]

SYMPTOMS = [  # (text, criticality)
    ("vibration at high RPM", 1), ("spindle noise during finishing pass", 1), ("axis 2 backlash 0.03 mm", 1),
    ("coolant level low", 0), ("chip conveyor slow", 0), ("tool changer jam", 1), ("alarm 1040 on the drive", 1),
    ("hydraulic pressure at 140 bar", 1), ("encoder drift on axis 3", 1), ("belt worn, visible cracks", 1),
    ("smoke from the motor housing", 2), ("sparks near the electrical cabinet", 2), ("oil leak under the press", 2),
    ("guard missing on the pulley", 2), ("spindle overheating at 80 C", 2), ("burning smell near the drive", 2),
    ("filter clogged", 0), ("minor surface finish marks", 0), ("lubrication due next week", 0),
]
FIXES = ["replaced the bearing set", "re-tensioned the belt", "cleaned the coolant filter", "recalibrated axis 3",
         "tightened the tool holder", "replaced the shaft seal", "updated the PLC firmware", "reset the drive alarm",
         "adjusted the relief valve", "replaced the gripper spring"]
STATUS = ["running normally", "down for maintenance", "running at reduced speed", "back in production",
          "waiting for spare parts", "stopped, do not use"]
PERSONAL = [
    "{name} asked me to cover the night shift, call {name} on {phone}",
    "my son is sick, leaving early today",
    "{name}'s leave application for next week, number {phone}",
    "salary slip issue, manager said to email hr",
    "doctor appointment at 4 pm, will be back after",
    "{name} complained about the shift roster, reach at {email}",
    "personal note: pay rent before friday",
    "{name} will send the gate pass, aadhaar {aadhaar}",
]
CHITCHAT = ["ok", "thanks", "noted", "tea break", "lunch at canteen?", "good morning team", "done", "see you tomorrow",
            "cricket match tonight?", "weekend plans anyone", "haha", "okay will check", "hello"]


def phone(r):
    return f"{r.choice('6789')}{r.randint(100000000, 999999999)}"


def main(n_sync=120, n_private=45, n_drop=35, seed=7) -> None:
    r = random.Random(seed)
    rows = []
    for _ in range(n_sync):
        m = r.choice(MACHINES)
        form = r.random()
        if form < 0.45:
            s, crit = r.choice(SYMPTOMS)
            rows.append((f"{m} {s}", "observation", m, "sync", crit))
        elif form < 0.8:
            s, crit = r.choice(SYMPTOMS)
            rows.append((f"{m}: {s}, {r.choice(FIXES)}", "fix", m, "sync", max(crit - 1, 0)))
        else:
            st = r.choice(STATUS)
            rows.append((f"{m} {st}", "status", m, "sync", 2 if "do not use" in st else 1 if "down" in st else 0))
    for _ in range(n_private):
        t = r.choice(PERSONAL).format(name=r.choice(NAMES), phone=phone(r), email=f"{r.choice(NAMES).lower()}@plant.example.com",
                                      aadhaar=f"{r.randint(1000, 9999)} {r.randint(1000, 9999)} {r.randint(1000, 9999)}")
        rows.append((t, "observation", "", "private", 0))
    for _ in range(n_drop):
        rows.append((r.choice(CHITCHAT), "observation", "", "drop", 0))
    r.shuffle(rows)
    with OUT.open("w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["text", "kind", "machine", "residency", "criticality", "source"])
        for row in rows:
            w.writerow([*row, "template"])
    print(f"wrote {len(rows)} notes -> {OUT}")


if __name__ == "__main__":
    main()
