import pm4py


def load_and_discover_basic_graph(file_path):
    # Load the event log directly from the compressed XES file.
    # We are keeping the original dataset unchanged per the project rules.
    print(f"Loading event log from {file_path}...")
    log = pm4py.read_xes(file_path)

    # Run a basic process discovery algorithm to generate a Directly-Follows Graph (DFG)
    print("Discovering Directly-Follows Graph (DFG)...")
    dfg, start_activities, end_activities = pm4py.discover_dfg(log)

    print("Log loaded successfully!")
    print(f"Found start activities: {list(start_activities.keys())}")

    return dfg, start_activities, end_activities


if __name__ == "__main__":
    # Pointing to the sample dataset location defined in the team guide
    log_path = "data/sample/sepsis_cases.xes.gz"
    load_and_discover_basic_graph(log_path)
