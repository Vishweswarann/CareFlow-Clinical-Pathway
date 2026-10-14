"""
generate_ehr_events.py  (version 2)

Generates a FICTIONAL, synthetic Emergency Department (ED) event log for the
CareFlow project. Every row is one event inside one hospital encounter.

IMPORTANT: All data is invented by this script. It is NOT copied from MIMIC-IV
or any real hospital, and every probability below is a design choice for
testing, NOT a real hospital statistic.

Usage (from the project root folder):
    python src/generate_ehr_events.py                          # 100 encounters
    python src/generate_ehr_events.py --encounters 5000 --seed 7
    python src/generate_ehr_events.py --target-events 200000 --output data/ehr_events_200k.csv
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

# Column order in the CSV: core -> event-level -> encounter-level.
COLUMNS = [
    "event_id", "case_id", "activity", "timestamp", "department",      # core
    "event_sequence", "resource_role", "resource_id", "event_detail",  # per event
    "arrival_mode", "age_group", "gender", "chief_complaint",          # per encounter
    "triage_level", "disposition",                                     # per encounter
]

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

# Which kind of staff member performs each activity.
ACTIVITY_ROLE = {
    "Registration": "Registration Clerk",
    "Triage": "Triage Nurse",
    "Doctor Consultation": "ED Physician",
    "Laboratory Testing": "Lab Technician",
    "Imaging": "Radiographer",
    "Treatment": "ED Nurse",
    "Reassessment": "ED Nurse",
    "Discharge": "ED Physician",
    "Hospital Admission": "Admissions Officer",
}

# Fictional staff pools: role -> (ID prefix, number of staff members).
ROLE_POOL = {
    "Registration Clerk": ("REG", 6),
    "Triage Nurse": ("TRN", 10),
    "ED Physician": ("DOC", 12),
    "Lab Technician": ("LAB", 8),
    "Radiographer": ("RAD", 6),
    "ED Nurse": ("NUR", 14),
    "Admissions Officer": ("ADM", 4),
}

# How patients arrive, and how likely each way is.
ARRIVAL_MODES = ["Walk-in", "Ambulance", "Transfer"]
ARRIVAL_WEIGHTS = [0.65, 0.28, 0.07]

# Patient demographics (fictional).
AGE_GROUPS = ["0-17", "18-34", "35-49", "50-64", "65+"]
AGE_WEIGHTS = [0.15, 0.27, 0.20, 0.19, 0.19]
ADMIT_AGE_MULTIPLIER = {"0-17": 0.6, "18-34": 0.8, "35-49": 1.0, "50-64": 1.2, "65+": 1.5}
GENDERS = ["Female", "Male"]
GENDER_WEIGHTS = [0.52, 0.48]

# Reason for visit: name -> (chance, lab multiplier, imaging multiplier).
# Multipliers make some complaints need more (or fewer) tests than average.
COMPLAINTS = {
    "Chest pain":            (0.12, 1.3, 1.1),
    "Abdominal pain":        (0.14, 1.3, 1.3),
    "Injury or fracture":    (0.20, 0.4, 1.8),
    "Breathing difficulty":  (0.10, 1.2, 1.2),
    "Fever or infection":    (0.16, 1.4, 0.6),
    "Headache or dizziness": (0.08, 0.8, 1.4),
    "Minor wound or rash":   (0.12, 0.1, 0.3),
    "Other":                 (0.08, 1.0, 1.0),
}
COMPLAINT_NAMES = list(COMPLAINTS)
COMPLAINT_WEIGHTS = [v[0] for v in COMPLAINTS.values()]

# Triage level 1 = most urgent ... 5 = least urgent (like the 5-level ESI scale).
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
REPEAT_LAB_PROBABILITY = 0.15
REPEAT_TREATMENT_PROBABILITY = 0.20
REASSESSMENT_PROBABILITY = 0.70
SECOND_REASSESSMENT_PROBABILITY = 0.20

# Typical waiting time (minutes) BEFORE each activity: (median, spread).
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
URGENCY_MULTIPLIER = {1: 0.2, 2: 0.5, 3: 1.0, 4: 1.3, 5: 1.5}

# Relative chance of arriving in each hour of the day (index 0 = midnight hour).
HOUR_WEIGHTS = [2, 1.5, 1, 1, 1, 1.5, 2, 3, 4, 5, 6, 6,
                6, 5, 5, 5, 5, 6, 6, 5, 4, 3, 3, 2.5]

# Wording for the free-text "event_detail" column.
LAB_TESTS = ["Blood panel", "Urinalysis", "Cardiac markers", "Blood culture"]
IMAGING_TYPES = ["X-Ray", "CT Scan", "Ultrasound", "MRI"]
IMAGING_WEIGHTS = [0.55, 0.25, 0.17, 0.03]
TREATMENTS = ["IV fluids", "Medication administered", "Wound care",
              "Splinting or casting", "Oxygen therapy", "Nebulisation"]
REASSESSMENTS = ["Vitals recheck", "Pain recheck", "Response to treatment"]
DISCHARGE_TYPES = ["Home with instructions", "Home with follow-up appointment"]
DISCHARGE_WEIGHTS = [0.6, 0.4]
LOOPBACK_REASONS = ["Re-triage: missing intake paperwork",
                    "Re-triage: consent form incomplete",
                    "Re-triage: imaging request form incomplete"]
LOOPBACK_WEIGHTS = [0.6, 0.2, 0.2]
ADMIT_WARDS = ["ICU", "General Ward", "Surgical Ward", "Observation Unit"]
ADMIT_WARD_WEIGHTS_URGENT = [0.35, 0.40, 0.15, 0.10]   # triage level 1-2
ADMIT_WARD_WEIGHTS_OTHER = [0.05, 0.60, 0.15, 0.20]    # triage level 3-5


# ---------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def build_pathway(rng, triage_level, disposition, lab_multiplier=1.0, imaging_multiplier=1.0):
    """Return the ordered list of activities for ONE encounter."""
    pathway = ["Registration", "Triage", "Doctor Consultation"]

    # Decide which diagnostic steps this patient needs, then shuffle the order.
    diagnostics = []
    if rng.random() < min(1.0, LAB_PROBABILITY[triage_level] * lab_multiplier):
        diagnostics.append("Laboratory Testing")
    if rng.random() < min(1.0, IMAGING_PROBABILITY[triage_level] * imaging_multiplier):
        diagnostics.append("Imaging")
    rng.shuffle(diagnostics)

    for step in diagnostics:
        pathway.append(step)
        if step == "Laboratory Testing" and rng.random() < REPEAT_LAB_PROBABILITY:
            pathway.append("Laboratory Testing")                      # repeated activity
        if step == "Imaging" and rng.random() < LOOPBACK_AFTER_IMAGING:
            pathway.extend(["Triage", "Doctor Consultation"])         # loop-back

    if rng.random() < TREATMENT_PROBABILITY[triage_level]:
        pathway.append("Treatment")
        if rng.random() < REPEAT_TREATMENT_PROBABILITY:
            pathway.append("Treatment")                               # repeated activity

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
    return min(4 * 60 * 60, max(60, int(minutes * 60)))


def pick_resource(rng, role):
    """Pick a fictional staff member (e.g. 'DOC07') for the given role."""
    prefix, pool_size = ROLE_POOL[role]
    return f"{prefix}{rng.randint(1, pool_size):02d}"


def describe_event(rng, activity, occurrence, triage_level):
    """Short text detail for an event. 'occurrence' = how many times this
    activity has already happened in this encounter (0 = first time)."""
    if activity == "Registration":
        return "Emergency registration" if triage_level == 1 else "Standard registration"
    if activity == "Triage":
        if occurrence == 0:
            return "Initial triage"
        return rng.choices(LOOPBACK_REASONS, weights=LOOPBACK_WEIGHTS)[0]
    if activity == "Doctor Consultation":
        return "Initial consultation" if occurrence == 0 else "Follow-up consultation"
    if activity == "Laboratory Testing":
        return rng.choice(LAB_TESTS)
    if activity == "Imaging":
        return rng.choices(IMAGING_TYPES, weights=IMAGING_WEIGHTS)[0]
    if activity == "Treatment":
        return rng.choice(TREATMENTS)
    if activity == "Reassessment":
        return rng.choice(REASSESSMENTS)
    if activity == "Discharge":
        return rng.choices(DISCHARGE_TYPES, weights=DISCHARGE_WEIGHTS)[0]
    weights = ADMIT_WARD_WEIGHTS_URGENT if triage_level <= 2 else ADMIT_WARD_WEIGHTS_OTHER
    return rng.choices(ADMIT_WARDS, weights=weights)[0]   # Hospital Admission


# ---------------------------------------------------------------------------
# 3. MAIN GENERATOR
# ---------------------------------------------------------------------------

def generate_events(n_encounters=None, target_events=None, seed=42,
                    start_date=datetime(2025, 1, 1), days=365):
    """Build the full event log and return it as a pandas DataFrame.

    Stops when n_encounters encounters were created, or once at least
    target_events events exist (whichever limit is given). An encounter is
    never cut in half, so the final row count can be slightly above the target.
    """
    if n_encounters is None and target_events is None:
        raise ValueError("Give n_encounters or target_events.")

    rng = random.Random(seed)   # our own random generator -> reproducible
    rows = []
    encounter_number = 0

    while True:
        if n_encounters is not None and encounter_number >= n_encounters:
            break
        if target_events is not None and len(rows) >= target_events:
            break
        encounter_number += 1
        case_id = f"ED{encounter_number:06d}"

        # Encounter attributes: decided ONCE per encounter ...
        age_group = rng.choices(AGE_GROUPS, weights=AGE_WEIGHTS)[0]
        gender = rng.choices(GENDERS, weights=GENDER_WEIGHTS)[0]
        complaint = rng.choices(COMPLAINT_NAMES, weights=COMPLAINT_WEIGHTS)[0]
        _, lab_multiplier, imaging_multiplier = COMPLAINTS[complaint]
        arrival_mode = rng.choices(ARRIVAL_MODES, weights=ARRIVAL_WEIGHTS)[0]
        triage_level = rng.choices(
            TRIAGE_LEVELS, weights=TRIAGE_WEIGHTS_BY_ARRIVAL[arrival_mode]
        )[0]
        admit_chance = min(0.98, ADMIT_PROBABILITY[triage_level] * ADMIT_AGE_MULTIPLIER[age_group])
        disposition = "Admitted" if rng.random() < admit_chance else "Discharged"

        pathway = build_pathway(rng, triage_level, disposition,
                                lab_multiplier, imaging_multiplier)
        current_time = random_arrival_time(rng, start_date, days)
        seen_count = {}   # how many times each activity happened so far

        for step_number, activity in enumerate(pathway):
            if step_number > 0:
                current_time += timedelta(seconds=wait_seconds(rng, activity, triage_level))
            occurrence = seen_count.get(activity, 0)
            seen_count[activity] = occurrence + 1
            role = ACTIVITY_ROLE[activity]
            rows.append({
                "case_id": case_id,
                "activity": activity,
                "timestamp": current_time,
                "department": ACTIVITY_DEPARTMENT[activity],
                "event_sequence": step_number + 1,
                "resource_role": role,
                "resource_id": pick_resource(rng, role),
                "event_detail": describe_event(rng, activity, occurrence, triage_level),
                # ... then COPIED onto every event row of this encounter.
                "arrival_mode": arrival_mode,
                "age_group": age_group,
                "gender": gender,
                "chief_complaint": complaint,
                "triage_level": triage_level,
                "disposition": disposition,
            })

    # Sort like a real system log: oldest event first across the whole hospital.
    # (case_id and event_sequence only break ties between identical timestamps.)
    rows.sort(key=lambda r: (r["timestamp"], r["case_id"], r["event_sequence"]))

    # Give each event a unique ID in that final order.
    for number, row in enumerate(rows, start=1):
        row["event_id"] = f"EV{number:07d}"

    return pd.DataFrame(rows, columns=COLUMNS)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a synthetic ED event log.")
    size = parser.add_mutually_exclusive_group()
    size.add_argument("--encounters", type=int, help="number of encounters (default 100)")
    size.add_argument("--target-events", type=int, help="generate until at least this many event rows exist")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output CSV path")
    parser.add_argument("--start-date", default="2025-01-01", help="first possible arrival date, YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=365, help="arrivals spread over this many days (default 365)")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.encounters is None and args.target_events is None:
        args.encounters = 100
    if (args.encounters or 1) < 1 or (args.target_events or 1) < 1 or args.days < 1:
        raise SystemExit("--encounters, --target-events and --days must be at least 1")

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    df = generate_events(args.encounters, args.target_events, args.seed, start_date, args.days)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, date_format="%Y-%m-%d %H:%M:%S")

    print(f"Seed: {args.seed}")
    print(f"Encounters: {df['case_id'].nunique()}  |  Events: {len(df)}  |  Columns: {len(df.columns)}")
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
