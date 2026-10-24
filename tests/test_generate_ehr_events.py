"""Automated checks for the synthetic ED event-log generator. Run with: pytest -v"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_ehr_events import (  # noqa: E402
    ACTIVITY_DEPARTMENT, COLUMNS, generate_events,
)

START = datetime(2025, 1, 1)
CASE_ATTRIBUTES = ["arrival_mode", "age_group", "gender", "chief_complaint",
                   "triage_level", "disposition"]


@pytest.fixture(scope="module")
def df():
    return generate_events(n_encounters=300, seed=42, start_date=START, days=365)


def test_columns_and_order(df):
    assert list(df.columns) == COLUMNS


def test_encounter_count(df):
    assert df["case_id"].nunique() == 300


def test_no_missing_values(df):
    assert not df.isna().any().any()
    for column in df.columns:
        assert not (df[column].astype(str).str.strip() == "").any()


def test_event_ids_are_unique(df):
    assert df["event_id"].is_unique


def test_timestamps_strictly_increase_within_each_case(df):
    for _, case in df.groupby("case_id"):
        stamps = case.sort_values("event_sequence")["timestamp"]
        assert stamps.is_monotonic_increasing and stamps.is_unique


def test_event_sequence_is_1_to_n_per_case(df):
    for _, case in df.groupby("case_id"):
        assert sorted(case["event_sequence"]) == list(range(1, len(case) + 1))


def test_encounter_attributes_are_constant_within_a_case(df):
    assert (df.groupby("case_id")[CASE_ATTRIBUTES].nunique() == 1).all().all()


def test_every_case_starts_with_registration_then_triage(df):
    ordered = df.sort_values(["case_id", "event_sequence"])
    first_two = ordered.groupby("case_id")["activity"].apply(lambda s: tuple(s.iloc[:2]))
    assert (first_two == ("Registration", "Triage")).all()


def test_last_event_matches_disposition_and_is_the_only_final_event(df):
    ordered = df.sort_values(["case_id", "event_sequence"])
    last = ordered.groupby("case_id").tail(1)
    expected = last["disposition"].map({"Admitted": "Hospital Admission", "Discharged": "Discharge"})
    assert (last["activity"] == expected).all()
    finals = df[df["activity"].isin(["Discharge", "Hospital Admission"])]
    assert finals["case_id"].is_unique


def test_department_matches_activity(df):
    assert (df["department"] == df["activity"].map(ACTIVITY_DEPARTMENT)).all()


def test_triage_levels_are_1_to_5(df):
    assert set(df["triage_level"]).issubset({1, 2, 3, 4, 5})


def test_pathways_vary_and_include_repeats_and_loopbacks(df):
    pathways = df.sort_values(["case_id", "event_sequence"]).groupby("case_id")["activity"].apply(tuple)
    assert pathways.nunique() > 10
    assert (df[df["activity"] == "Triage"].groupby("case_id").size() > 1).any()   # loop-back
    assert (df.groupby(["case_id", "activity"]).size() > 1).any()                  # repeats


def test_same_seed_gives_identical_data():
    a = generate_events(n_encounters=50, seed=7, start_date=START, days=30)
    b = generate_events(n_encounters=50, seed=7, start_date=START, days=30)
    assert a.equals(b)


def test_different_seed_gives_different_data():
    a = generate_events(n_encounters=50, seed=7, start_date=START, days=30)
    b = generate_events(n_encounters=50, seed=8, start_date=START, days=30)
    assert not a.equals(b)


def test_target_events_never_cuts_an_encounter_in_half():
    df = generate_events(target_events=1000, seed=1, start_date=START, days=60)
    assert 1000 <= len(df) < 1030
    last = df.sort_values(["case_id", "event_sequence"]).groupby("case_id").tail(1)
    assert last["activity"].isin(["Discharge", "Hospital Admission"]).all()


def test_must_give_a_size_limit():
    with pytest.raises(ValueError):
        generate_events()

def test_single_encounter_has_complete_pathway():
    df = generate_events(
        n_encounters=1,
        seed=42,
        start_date=START,
        days=30,
    )

    activities = df["activity"].tolist()

    assert activities[0] == "Registration"
    assert activities[1] == "Triage"
    assert activities[-1] in ["Discharge", "Hospital Admission"]
    assert df["case_id"].nunique() == 1

def test_sample_event_log_integrity():
    path = Path(__file__).resolve().parents[1] / "data" / "sample" / "ehr_events_sample.csv"
    import pandas as pd

    sample = pd.read_csv(path)

    assert list(sample.columns) == COLUMNS
    assert sample["event_id"].is_unique
    assert sample["timestamp"].notna().all()

    timestamps = pd.to_datetime(sample["timestamp"], errors="coerce")
    assert timestamps.notna().all()