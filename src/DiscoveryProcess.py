import pandas as pd
import pm4py

df = pd.read_csv("../data/sample/ehr_events_sample.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

event_log = pm4py.format_dataframe(
    df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
)

heu_net = pm4py.discover_heuristics_net(event_log, dependency_threshold=0.5)

dfg, start_activities, end_activities = pm4py.discover_dfg(event_log)

pm4py.save_vis_dfg(
    dfg, start_activities, end_activities, "../output/my_process_model.png"
)

net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(event_log)

pm4py.save_vis_petri_net(
    petri_net=net,
    initial_marking=initial_marking,
    final_marking=final_marking,
    file_path="../output/my_petrinet_model.png",
)


replayed_traces = pm4py.conformance_diagnostics_token_based_replay(
    event_log, net, initial_marking, final_marking
)

print(replayed_traces[0])
