from datetime import datetime

from src.generate_ehr_events import generate_events

def create_test_data(encounters=10, seed=42):
    """Generate a small dataset for testing."""
    return generate_events(
        n_encounters=encounters,
        seed=seed,
        start_date=datetime(2025, 1, 1),
        days=30,
    )


def test_required_columns_exist():
    df = create_test_data()

    expected_columns = [
        "event_id",
        "case_id",
        "activity",
        "timestamp",
        "department",
        "arrival_mode",
        "triage_level",
        "disposition",
    ]

    assert list(df.columns) == expected_columns


def test_encounter_count():
    df = create_test_data(encounters=10)

    assert df["case_id"].nunique() == 10


def test_event_ids_are_unique():
    df = create_test_data()

    assert df["event_id"].is_unique


def test_required_fields_have_no_missing_values():
    df = create_test_data()

    assert not df.isnull().any().any()


def test_timestamps_are_datetime_values():
    df = create_test_data()

    assert df["timestamp"].notna().all()
    assert df["timestamp"].map(
        lambda value: isinstance(value, datetime)
    ).all()


def test_events_are_sorted_by_timestamp():
    df = create_test_data()

    timestamps = df["timestamp"].tolist()

    assert timestamps == sorted(timestamps)


def test_each_encounter_has_one_final_event():
    df = create_test_data()

    terminal_activities = {"Discharge", "Hospital Admission"}

    for case_id, group in df.groupby("case_id"):
        terminal_rows = group[
            group["activity"].isin(terminal_activities)
        ]

        # Every encounter must have exactly one terminal event.
        assert len(terminal_rows) == 1, (
            f"{case_id} does not have exactly one terminal event"
        )

        # The terminal event must be the last event in that encounter.
        last_event = group.sort_values("timestamp").iloc[-1]

        assert last_event["activity"] in terminal_activities


def test_same_seed_produces_same_data():
    df1 = create_test_data(encounters=10, seed=42)
    df2 = create_test_data(encounters=10, seed=42)

    assert df1.equals(df2)


def test_different_seeds_produce_different_data():
    df1 = create_test_data(encounters=10, seed=42)
    df2 = create_test_data(encounters=10, seed=99)

    assert not df1.equals(df2)
