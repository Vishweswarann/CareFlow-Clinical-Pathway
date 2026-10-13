"""
generate_ehr_events.py

Generates a FICTIONAL, synthetic Emergency Department (ED) event log for the
CareFlow project. Every row is one event inside one hospital encounter.

IMPORTANT: All data is invented by this script. It is NOT copied from MIMIC-IV
or any real hospital, and the probabilities below are design choices for
testing, NOT real hospital statistics.

Usage (from the project root folder):
    python src/generate_ehr_events.py
    python src/generate_ehr_events.py --encounters 100 --seed 42
"""

import argparse
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1. SETTINGS (change these numbers to change the behaviour of the generator)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "sample" / "ehr_events_sample.csv"

COLUMNS = [
    "event_id", "case_id", "activity", "timestamp", "department",
    "arrival_mode", "triage_level", "disposition",
]

# Which department is responsible for each activity.
ACTIVITY_DEPARTMENT = {
    "Registration": "Front Desk",
    "Triage": "Triage",
    "Doctor Consultation": "Emergency Medicine",
    "Laboratory Testing": "Laboratory",
    "Imaging": "Radiology",
    "Treatment": "Emergency Medicine",
    "Reassessment": "Emergency Medicine",
    "Discharge": "Emergency Medicine",
    "Hospital Admission": "Inpatient Admissions",
}

# How patients arrive, and how likely each way is.
ARRIVAL_MODES = ["Walk-in", "Ambulance", "Transfer"]
ARRIVAL_WEIGHTS = [0.65, 0.28, 0.07]

# Triage level 1 = most urgent ... 5 = least urgent (like the 5-level ESI scale).
# Each list gives the chance of levels 1,2,3,4,5 for that arrival mode.
TRIAGE_LEVELS = [1, 2, 3, 4, 5]
TRIAGE_WEIGHTS_BY_ARRIVAL = {
    "Walk-in":   [0.01, 0.10, 0.37, 0.37, 0.15],
    "Ambulance": [0.12, 0.30, 0.38, 0.15, 0.05],
    "Transfer":  [0.05, 0.30, 0.45, 0.15, 0.05],
}

# Chance (0 to 1) of each thing happening, by triage level.
ADMIT_PROBABILITY     = {1: 0.85, 2: 0.55, 3: 0.25, 4: 0.05, 5: 0.02}
LAB_PROBABILITY       = {1: 0.95, 2: 0.85, 3: 0.60, 4: 0.30, 5: 0.10}
IMAGING_PROBABILITY   = {1: 0.80, 2: 0.60, 3: 0.40, 4: 0.20, 5: 0.05}
TREATMENT_PROBABILITY = {1: 0.99, 2: 0.95, 3: 0.90, 4: 0.60, 5: 0.30}

# Deliberate "inefficiencies" so process mining has something to discover.
LOOPBACK_AFTER_IMAGING = 0.40   # patient is sent back to Triage after imaging
REPEAT_LAB_PROBABILITY = 0.15   # lab test is repeated
REPEAT_TREATMENT_PROBABILITY = 0.20
REASSESSMENT_PROBABILITY = 0.70
SECOND_REASSESSMENT_PROBABILITY = 0.20

# Typical waiting time (in minutes) BEFORE each activity starts: (median, spread).
# A bigger "spread" means more variation from patient to patient.
WAIT_MINUTES = {
    "Triage": (8, 0.5),
    "Doctor Consultation": (35, 0.6),
    "Laboratory Testing": (20, 0.5),
    "Imaging": (30, 0.5),
    "Treatment": (15, 0.5),
    "Reassessment": (40, 0.6),
    "Discharge": (25, 0.5),
    "Hospital Admission": (60, 0.6),
}

# Urgent patients wait less, non-urgent patients wait more.
URGENCY_MULTIPLIER = {1: 0.2, 2: 0.5, 3: 1.0, 4: 1.3, 5: 1.5}

# Relative chance of arriving in each hour of the day (index 0 = midnight hour).
HOUR_WEIGHTS = [2, 1.5, 1, 1, 1, 1.5, 2, 3, 4, 5, 6, 6,
                6, 5, 5, 5, 5, 6, 6, 5, 4, 3, 3, 2.5]


# ---------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def build_pathway(rng, triage_level, disposition):
    """Return the ordered list of activities for ONE encounter."""
    pathway = ["Registration", "Triage", "Doctor Consultation"]

    # Decide which diagnostic steps this patient needs, then shuffle the order.
    diagnostics = []
    if rng.random() < LAB_PROBABILITY[triage_level]:
        diagnostics.append("Laboratory Testing")
    if rng.random() < IMAGING_PROBABILITY[triage_level]:
        diagnostics.append("Imaging")
    rng.shuffle(diagnostics)

    for step in diagnostics:
        pathway.append(step)
        if step == "Laboratory Testing" and rng.random() < REPEAT_LAB_PROBABILITY:
            pathway.append("Laboratory Testing")          # repeated activity
        if step == "Imaging" and rng.random() < LOOPBACK_AFTER_IMAGING:
            pathway.extend(["Triage", "Doctor Consultation"])  # loop-back

    if rng.random() < TREATMENT_PROBABILITY[triage_level]:
        pathway.append("Treatment")
        if rng.random() < REPEAT_TREATMENT_PROBABILITY:
            pathway.append("Treatment")                   # repeated activity

    if rng.random() < REASSESSMENT_PROBABILITY:
        pathway.append("Reassessment")
        if rng.random() < SECOND_REASSESSMENT_PROBABILITY:
            pathway.append("Reassessment")

    # Every encounter ends with exactly one final event.
    pathway.append("Hospital Admission" if disposition == "Admitted" else "Discharge")
    return pathway


def random_arrival_time(rng, start_date, days):
    """Pick a random arrival date/time, busier during the daytime."""
    day = rng.randrange(days)
    hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
    return start_date + timedelta(
        days=day, hours=hour, minutes=rng.randrange(60), seconds=rng.randrange(60)
    )


def wait_seconds(rng, activity, triage_level):
    """Random waiting time before an activity (always at least 60 seconds)."""
    median, spread = WAIT_MINUTES[activity]
    minutes = rng.lognormvariate(math.log(median), spread) * URGENCY_MULTIPLIER[triage_level]
    return max(60, int(minutes * 60))


# ---------------------------------------------------------------------------
# 3. MAIN GENERATOR
# ---------------------------------------------------------------------------

def generate_events(n_encounters, seed, start_date, days):
    """Build the full event log and return it as a pandas DataFrame."""
    rng = random.Random(seed)   # our own random generator -> reproducible
    rows = []

    for i in range(1, n_encounters + 1):
        case_id = f"ED{i:06d}"

        # Encounter attributes: decided ONCE per encounter ...
        arrival_mode = rng.choices(ARRIVAL_MODES, weights=ARRIVAL_WEIGHTS)[0]
        triage_level = rng.choices(
            TRIAGE_LEVELS, weights=TRIAGE_WEIGHTS_BY_ARRIVAL[arrival_mode]
        )[0]
        disposition = "Admitted" if rng.random() < ADMIT_PROBABILITY[triage_level] else "Discharged"

        pathway = build_pathway(rng, triage_level, disposition)
        current_time = random_arrival_time(rng, start_date, days)

        for step_number, activity in enumerate(pathway):
            if step_number > 0:
                current_time += timedelta(seconds=wait_seconds(rng, activity, triage_level))
            rows.append({
                "case_id": case_id,
                "activity": activity,
                "timestamp": current_time,
                "department": ACTIVITY_DEPARTMENT[activity],
                # ... then COPIED onto every event row of this encounter.
                "arrival_mode": arrival_mode,
                "triage_level": triage_level,
                "disposition": disposition,
                "_step": step_number,
            })

    # Sort like a real system log: oldest event first across the whole hospital.
    rows.sort(key=lambda r: (r["timestamp"], r["case_id"], r["_step"]))

    # Give each event a unique ID in that final order.
    for number, row in enumerate(rows, start=1):
        row["event_id"] = f"EV{number:07d}"
        del row["_step"]

    return pd.DataFrame(rows, columns=COLUMNS)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a synthetic ED event log.")
    parser.add_argument("--encounters", type=int, default=100, help="number of encounters (default 100)")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output CSV path")
    parser.add_argument("--start-date", default="2026-01-01", help="first possible arrival date, YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=90, help="arrivals spread over this many days (default 90)")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.encounters < 1 or args.days < 1:
        raise SystemExit("--encounters and --days must be at least 1")

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    df = generate_events(args.encounters, args.seed, start_date, args.days)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, date_format="%Y-%m-%d %H:%M:%S")

    print(f"Seed: {args.seed}")
    print(f"Encounters: {df['case_id'].nunique()}  |  Events: {len(df)}")
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
