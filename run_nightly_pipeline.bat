
@echo off
cd /d C:\Careflow

call .venv\Scripts\activate.bat

python src\nightly_bigquery_pipeline.py

if errorlevel 1 (
    echo CareFlow nightly dry-run FAILED.
) else (
    echo CareFlow nightly dry-run completed successfully.
)
