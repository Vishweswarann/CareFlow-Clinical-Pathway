
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "sample" / "ehr_events_sample.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


def calculate_waiting_time_metrics(events):
    """Calculate elapsed times between consecutive events in each case."""
    required = {"case_id", "activity", "timestamp"}
    missing = required - set(events.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["case_id", "activity", "timestamp"])

    sort_columns = (
        ["case_id", "timestamp", "event_id"]
        if "event_id" in df.columns
        else ["case_id", "timestamp"]
    )
    df = df.sort_values(sort_columns).copy()

    df["previous_activity"] = df.groupby("case_id")["activity"].shift(1)
    df["previous_timestamp"] = df.groupby("case_id")["timestamp"].shift(1)

    df["elapsed_minutes"] = (
        df["timestamp"] - df["previous_timestamp"]
    ).dt.total_seconds() / 60

    intervals = df.dropna(
        subset=["previous_activity", "elapsed_minutes"]
    ).copy()

    negative_count = int((intervals["elapsed_minutes"] < 0).sum())
    intervals = intervals[intervals["elapsed_minutes"] >= 0].copy()

    summary = (
        intervals.groupby(
            ["previous_activity", "activity"], as_index=False
        )
        .agg(
            transition_count=("elapsed_minutes", "count"),
            mean_elapsed_minutes=("elapsed_minutes", "mean"),
            median_elapsed_minutes=("elapsed_minutes", "median"),
            max_elapsed_minutes=("elapsed_minutes", "max"),
        )
        .sort_values("median_elapsed_minutes", ascending=False)
        .reset_index(drop=True)
    )

    return intervals, summary, negative_count


def analyze_waiting_times():
    """Run the analysis on the project's sample CSV and save its outputs."""
    df = pd.read_csv(INPUT_FILE)

    intervals, summary, negative_count = calculate_waiting_time_metrics(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    detail_file = OUTPUT_DIR / "event_intervals.csv"
    intervals.to_csv(detail_file, index=False)

    summary_file = OUTPUT_DIR / "waiting_time_by_transition.csv"
    summary.to_csv(summary_file, index=False)

    print(f"Input events: {len(df)}")
    print(f"Patient cases: {df['case_id'].nunique()}")
    print(f"Valid consecutive intervals: {len(intervals)}")
    print(f"Negative intervals excluded: {negative_count}")
    print(f"\nDetailed results: {detail_file}")
    print(f"Transition summary: {summary_file}")
    print("\nTransitions with the highest median elapsed time:")
    print(summary.head(10).round(2).to_string(index=False))


if __name__ == "__main__":
    analyze_waiting_times()
