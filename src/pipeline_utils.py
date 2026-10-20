
import logging
from pathlib import Path
from datetime import datetime


def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("careflow_pipeline")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        log_file = log_dir / "nightly_pipeline.log"
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        ))
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler())

    return logger


def write_dry_run_report(
    report_dir: Path,
    incoming_rows: int,
    new_rows: int,
    existing_rows: int,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "dry_run_report.txt"

    report_path.write_text(
        f"CareFlow Nightly Pipeline - Dry Run\n"
        f"Run time: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Incoming rows: {incoming_rows}\n"
        f"Already existing IDs: {existing_rows}\n"
        f"New IDs detected: {new_rows}\n"
        f"BigQuery writes performed: NO\n",
        encoding="utf-8",
    )
    return report_path
