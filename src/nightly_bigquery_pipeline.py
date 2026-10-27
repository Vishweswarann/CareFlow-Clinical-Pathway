
from pathlib import Path
import argparse
import logging

import pandas as pd

# CareFlow nightly pipeline: local dry-run only.
# This version does not connect to or write to BigQuery.

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "ehr_events_full.csv"
TEST_DIR = ROOT / "data" / "pipeline_test"
BASELINE_PATH = TEST_DIR / "existing_events.csv"
REPORT_DIR = ROOT / "data" / "pipeline_reports"
LOG_DIR = ROOT / "logs"

REQUIRED_COLUMNS = [
    "event_id",
    "case_id",
    "activity",
    "timestamp",
    "department",
    "event_sequence",
    "resource_role",
    "resource_id",
    "event_detail",
    "arrival_mode",
    "age_group",
    "gender",
    "chief_complaint",
    "triage_level",
    "disposition",
]


def setup_logger():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("careflow_pipeline")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        file_handler = logging.FileHandler(
            LOG_DIR / "nightly_pipeline.log",
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def load_and_validate_csv(csv_path):
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    df["event_id"] = df["event_id"].astype("string").str.strip()

    if df["event_id"].isna().any() or df["event_id"].eq("").any():
        raise ValueError("Blank event IDs found. Pipeline stopped.")

    if df["event_id"].duplicated().any():
        raise ValueError("Duplicate event IDs found. Pipeline stopped.")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="raise",
        utc=True,
    )

    return df


def load_local_baseline(logger):
    """Read the small synthetic baseline used for local testing."""
    if not BASELINE_PATH.exists():
        logger.info(
            "No local test baseline found; treating all incoming IDs "
            "as new in this simulation."
        )
        return set()

    baseline = pd.read_csv(
        BASELINE_PATH,
        dtype={"event_id": "string"},
    )

    if "event_id" not in baseline.columns:
        raise ValueError("Local baseline has no event_id column.")

    ids = baseline["event_id"].dropna().str.strip()

    if ids.eq("").any():
        raise ValueError("Blank event IDs found in local baseline.")

    if ids.duplicated().any():
        raise ValueError("Duplicate IDs found in local baseline.")

    logger.info(
        "Using LOCAL TEST baseline with %s IDs. "
        "This is not a live BigQuery comparison.",
        len(ids),
    )

    return set(ids)

def compare_event_ids(incoming_ids, existing_ids):
    """Compare incoming IDs against a validated existing-ID set."""
    incoming_ids = set(incoming_ids)
    existing_ids = set(existing_ids)

    already_present = incoming_ids & existing_ids
    new_ids = incoming_ids - existing_ids

    return already_present, new_ids


def write_report(incoming_rows, existing_count, new_count):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "dry_run_report.txt"

    report_text = (
        "CareFlow Nightly Pipeline - LOCAL DRY RUN\n"
        f"Incoming rows: {incoming_rows}\n"
        f"IDs found in local baseline: {existing_count}\n"
        f"New IDs in local simulation: {new_count}\n"
        "Comparison type: LOCAL TEST BASELINE ONLY\n"
        "Live BigQuery comparison performed: NO\n"
        "BigQuery writes performed: NO\n"
    )

    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="CareFlow local nightly pipeline dry run"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help="Path to the incoming CSV file",
    )
    args = parser.parse_args()

    logger = setup_logger()

    try:
        df = load_and_validate_csv(args.csv)

        logger.info("CSV validation passed: %s rows", len(df))
        logger.info(
            "Unique incoming event IDs: %s",
            df["event_id"].nunique(),
        )

        incoming_ids = set(df["event_id"].astype(str))
        existing_ids = load_local_baseline(logger)

        already_present_ids, new_ids = compare_event_ids(
            incoming_ids,
            existing_ids,
        )
        already_present = len(already_present_ids)

        report_path = write_report(
            incoming_rows=len(df),
            existing_count=already_present,
            new_count=len(new_ids),
        )

        logger.info("IDs found in local baseline: %s", already_present)
        logger.info("New IDs in local simulation: %s", len(new_ids))
        logger.info("Report saved to: %s", report_path)
        logger.info("DRY RUN ONLY: no BigQuery writes performed.")

    except Exception:
        logger.exception("Pipeline dry run failed.")
        raise


if __name__ == "__main__":
    main()
