
from pathlib import Path
import pm4py

# Project root and dataset location
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "sample"
    / "Sepsis Cases - Event Log.xes.gz"
)

if not DATASET_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATASET_PATH}"
    )

# Load the XES event log
event_log = pm4py.read_xes(str(DATASET_PATH))

# Convert the event log into a tabular DataFrame
df = pm4py.convert_to_dataframe(event_log)

print("Dataset loaded successfully!")
print(f"Number of events: {len(df)}")
print(f"Number of columns: {len(df.columns)}")

print("\nColumn names:")
print(df.columns.tolist())

print("\nFirst five records:")
print(df.head())

print("\nMissing values per column:")
print(df.isnull().sum())
