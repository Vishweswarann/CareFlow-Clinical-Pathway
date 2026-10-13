import pandas as pd


def calculate_elapsed_time(events):
    required = ["case_id", "activity", "timestamp"]

    for column in required:
        if column not in events.columns:
            raise ValueError(f"Missing column: {column}")

    df = events.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], errors="coerce"
    )

    df = df.dropna(
        subset=["case_id", "activity", "timestamp"]
    )

    df = df.sort_values(
        ["case_id", "timestamp"]
    ).reset_index(drop=True)

    df["previous_activity"] = (
        df.groupby("case_id")["activity"].shift(1)
    )

    df["previous_timestamp"] = (
        df.groupby("case_id")["timestamp"].shift(1)
    )

    df["elapsed_minutes"] = (
        df["timestamp"] - df["previous_timestamp"]
    ).dt.total_seconds() / 60

    return df


def summarize_transitions(events):
    transitions = events.dropna(
        subset=["previous_activity", "elapsed_minutes"]
    ).copy()

    transitions = transitions[
        transitions["elapsed_minutes"] >= 0
    ]

    return (
        transitions
        .groupby(["previous_activity", "activity"])
        ["elapsed_minutes"]
        .agg(
            mean_minutes="mean",
            median_minutes="median",
            maximum_minutes="max",
            count="count"
        )
        .reset_index()
        .sort_values("mean_minutes", ascending=False)
    )


if __name__ == "__main__":
    sample_data = pd.DataFrame({
        "case_id": [
            "case_001", "case_001", "case_001",
            "case_002", "case_002"
        ],
        "activity": [
            "ER Triage", "Lab Test", "Doctor Review",
            "ER Triage", "Lab Test"
        ],
        "timestamp": [
            "2026-01-01 10:00:00",
            "2026-01-01 10:30:00",
            "2026-01-01 11:15:00",
            "2026-01-01 09:00:00",
            "2026-01-01 10:00:00"
        ]
    })

    results = calculate_elapsed_time(sample_data)

    print("\nElapsed-time results:")
    print(results.to_string(index=False))

    print("\nTransition summary:")
    print(summarize_transitions(results).to_string(index=False))