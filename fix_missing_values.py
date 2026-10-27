from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_ROOT / "ehr_events_enhanced.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "ehr_events_cleaned.csv"

REQUIRED_COLUMNS = [
    "event_id",
    "case_id",
    "activity",
    "timestamp",
    "task_duration_minutes",
    "waiting_time_minutes",
    "arrival_timestamp",
    "minutes_until_next_event",
]


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    print(f"Input rows: {len(df)}")
    print(f"Unique event IDs: {df['event_id'].nunique()}")
    print(f"Duplicate event IDs: {df['event_id'].duplicated().sum()}")

    for column in (
        "task_duration_minutes",
        "waiting_time_minutes",
        "minutes_until_next_event",
    ):
        df[column] = pd.to_numeric(df[column], errors="coerce")
        print(f"Missing {column}: {df[column].isna().sum()}")

    negative_intervals = (
        df["minutes_until_next_event"] < 0
    ).sum()
    print(f"Negative intervals: {negative_intervals}")

    # Preserve missing values; do not invent clinical durations.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Local cleaned copy saved to: {OUTPUT_FILE}")
    print("No BigQuery operations were performed.")


if __name__ == "__main__":
    main()
