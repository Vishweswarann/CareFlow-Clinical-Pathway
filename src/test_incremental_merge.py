
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = ROOT / "data" / "pipeline_test"
EXISTING_FILE = TEST_DIR / "existing_events.csv"
INCOMING_FILE = TEST_DIR / "incoming_events.csv"
OUTPUT_FILE = TEST_DIR / "merged_events.csv"


def merge_new_events(existing, incoming):
    for name, df in [("existing", existing), ("incoming", incoming)]:
        if "event_id" not in df.columns:
            raise ValueError(f"{name} data has no event_id column")
        if df["event_id"].isna().any():
            raise ValueError(f"{name} data contains blank event IDs")
        if df["event_id"].duplicated().any():
            raise ValueError(f"{name} data contains duplicate event IDs")

    new_rows = incoming[
        ~incoming["event_id"].isin(existing["event_id"])
    ]
    return pd.concat([existing, new_rows], ignore_index=True), len(new_rows)


def main():
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    existing = pd.DataFrame({
        "event_id": ["EV001", "EV002"],
        "activity": ["Registration", "Triage"],
    })
    incoming = pd.DataFrame({
        "event_id": ["EV002", "EV003", "EV004"],
        "activity": ["Triage", "Consultation", "Discharge"],
    })

    # First run
    merged_once, inserted_once = merge_new_events(existing, incoming)

    # Second run with the exact same batch
    merged_twice, inserted_twice = merge_new_events(
        merged_once, incoming
    )

    assert inserted_once == 2, "Expected two new events on first run"
    assert inserted_twice == 0, "Second run should add no events"
    assert len(merged_once) == 4
    assert len(merged_twice) == 4
    assert merged_twice["event_id"].is_unique

    merged_twice.to_csv(OUTPUT_FILE, index=False)

    print("First run — new events:", inserted_once)
    print("Second run — new events:", inserted_twice)
    print("Final row count:", len(merged_twice))
    print("Unique event IDs:", merged_twice["event_id"].nunique())
    print("IDEMPOTENCY TEST PASSED")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
