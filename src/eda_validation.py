
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "ehr_events_full.csv"

df = pd.read_csv(DATA_PATH)

print("=" * 60)
print("1. DATASET OVERVIEW")
print("=" * 60)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
print("Memory usage (MB):", round(df.memory_usage(deep=True).sum() / 1e6, 2))
print("\nData types:")
print(df.dtypes)

print("\n" + "=" * 60)
print("2. MISSING VALUES")
print("=" * 60)
missing = pd.DataFrame({
    "missing_count": df.isna().sum(),
    "missing_percent": (df.isna().mean() * 100).round(3),
})
print(missing.sort_values("missing_count", ascending=False))

print("\n" + "=" * 60)
print("3. DUPLICATE CHECKS")
print("=" * 60)
print("Exact duplicate rows:", df.duplicated().sum())

if "event_id" in df.columns:
    print("Duplicate event IDs:", df["event_id"].duplicated().sum())

if {"case_id", "activity", "timestamp"}.issubset(df.columns):
    repeated_event_keys = df.duplicated(
        subset=["case_id", "activity", "timestamp"],
        keep=False,
    )
    print(
        "Rows sharing case + activity + timestamp:",
        repeated_event_keys.sum(),
    )

print("\n" + "=" * 60)
print("4. ENCOUNTER AND ACTIVITY SUMMARY")
print("=" * 60)

if "case_id" in df.columns:
    case_sizes = df.groupby("case_id").size()
    print("Unique encounters:", df["case_id"].nunique())
    print("Events per encounter:")
    print(case_sizes.describe())

if "activity" in df.columns:
    print("\nActivity counts:")
    print(df["activity"].value_counts(dropna=False))

for column in [
    "department",
    "arrival_mode",
    "triage_level",
    "disposition",
    "age_group",
    "gender",
    "chief_complaint",
    "resource_role",
]:
    if column in df.columns:
        print(f"\n{column} distribution:")
        print(df[column].value_counts(dropna=False).head(20))

print("\n" + "=" * 60)
print("5. TIMESTAMP AND EVENT ORDER")
print("=" * 60)

if {"case_id", "timestamp"}.issubset(df.columns):
    timestamps = pd.to_datetime(df["timestamp"], errors="coerce")
    print("Invalid or missing timestamps:", timestamps.isna().sum())

    valid = df.loc[timestamps.notna(), ["case_id"]].copy()
    valid["timestamp"] = timestamps[timestamps.notna()]

    valid = valid.sort_values(["case_id", "timestamp"])
    time_gaps = valid.groupby("case_id")["timestamp"].diff()

    print("Negative timestamp gaps:", (time_gaps < pd.Timedelta(0)).sum())
    print("Zero timestamp gaps:", (time_gaps == pd.Timedelta(0)).sum())

if {"case_id", "event_sequence"}.issubset(df.columns):
    ordered = df.sort_values(["case_id", "event_sequence"])
    sequence = ordered.groupby("case_id")["event_sequence"]

    print(
        "Sequence starts at 1 for every encounter:",
        sequence.first().eq(1).all(),
    )
    print(
        "Sequence values unique within each encounter:",
        not ordered.duplicated(["case_id", "event_sequence"]).any(),
    )

print("\n" + "=" * 60)
print("6. ENCOUNTER ATTRIBUTE CONSISTENCY")
print("=" * 60)

case_attributes = [
    "arrival_mode",
    "triage_level",
    "disposition",
    "age_group",
    "gender",
    "chief_complaint",
]

for column in case_attributes:
    if {"case_id", column}.issubset(df.columns):
        counts = df.groupby("case_id")[column].nunique(dropna=False)
        print(f"{column}: inconsistent encounters =", (counts > 1).sum())


print("\n" + "=" * 60)
print("7. LOGICAL EVENT VALIDATION")
print("=" * 60)

ordered = df.sort_values(["case_id", "event_sequence"]).copy()
grouped = ordered.groupby("case_id", sort=False)

# Check that event sequences are consecutive: 1, 2, 3, ...
sequence_ok = grouped["event_sequence"].apply(
    lambda s: s.tolist() == list(range(1, len(s) + 1))
)
print("Encounters with consecutive event sequences:", sequence_ok.all())

# Check activity-to-department mapping.
expected_departments = {
    "Registration": "Front Desk",
    "Triage": "Triage",
    "Doctor Consultation": "Emergency Medicine",
    "Treatment": "Emergency Medicine",
    "Reassessment": "Emergency Medicine",
    "Discharge": "Emergency Medicine",
    "Laboratory Testing": "Laboratory",
    "Imaging": "Radiology",
    "Hospital Admission": "Inpatient Admissions",
}

if {"activity", "department"}.issubset(df.columns):
    expected = df["activity"].map(expected_departments)
    known = expected.notna()
    mismatches = known & df["department"].ne(expected)
    print("Rows with incorrect activity-department mapping:", mismatches.sum())
    print("Rows with unknown activities:", (~known).sum())

# Check that each encounter begins with Registration -> Triage.
first_two = grouped["activity"].apply(lambda s: s.iloc[:2].tolist())
starts_correctly = first_two.apply(
    lambda activities: activities == ["Registration", "Triage"]
)
print("Encounters starting with Registration -> Triage:", starts_correctly.all())

# Check that the final activity agrees with the encounter disposition.
last_rows = grouped.tail(1)

if {"activity", "disposition"}.issubset(last_rows.columns):
    expected_final = last_rows["disposition"].map({
        "Discharged": "Discharge",
        "Admitted": "Hospital Admission",
    })
    known_dispositions = expected_final.notna()
    final_mismatches = (
        known_dispositions
        & last_rows["activity"].ne(expected_final)
    )
    print("Encounters with incorrect final activity:", final_mismatches.sum())
    print("Rows with unknown dispositions:", (~known_dispositions).sum())

print("\n" + "=" * 60)
print("8. RESOURCE ROLE VALIDATION")
print("=" * 60)

expected_roles = {
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

role_prefixes = {
    "Registration Clerk": "REG",
    "Triage Nurse": "TRN",
    "ED Physician": "DOC",
    "Lab Technician": "LAB",
    "Radiographer": "RAD",
    "ED Nurse": "NUR",
    "Admissions Officer": "ADM",
}

if {"activity", "resource_role", "resource_id"}.issubset(df.columns):
    expected = df["activity"].map(expected_roles)
    known = expected.notna()

    role_mismatches = known & df["resource_role"].ne(expected)
    print("Rows with incorrect resource roles:", role_mismatches.sum())
    print("Rows with unknown activities:", (~known).sum())

    expected_prefix = df["resource_role"].map(role_prefixes)
    known_roles = expected_prefix.notna()

    prefix_mismatches = known_roles & (
    df["resource_id"].str.slice(0, 3) != expected_prefix
)

    print("Resource IDs with incorrect role prefixes:", prefix_mismatches.sum())
    print("Rows with unknown resource roles:", (~known_roles).sum())

print("\n" + "=" * 60)
print("Validation report complete. No data has been modified.")
print("=" * 60)