import streamlit as st
import pandas as pd
import pm4py
from google.cloud import bigquery

from pm4py.visualization.dfg import visualizer as dfg_visualizer
from pm4py.visualization.petri_net import visualizer as pn_visualizer
from pm4py.visualization.heuristics_net import visualizer as hn_visualizer

st.set_page_config(page_title="CareFlow Process Map", layout="wide")
st.title("CareFlow Clinical Pathway Explorer")


@st.cache_data
def fetch_cloud_data():
    client = bigquery.Client(project="careflow-analytics-98234")
    query = """
        SELECT case_id, activity, timestamp 
        FROM `careflow-analytics-98234.careflow_analytics.event_logs`
        ORDER BY case_id, event_sequence
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


with st.spinner("Fetching live data from BigQuery..."):
    raw_df = fetch_cloud_data()

event_log = pm4py.format_dataframe(
    raw_df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
)

st.sidebar.header("Process Mining Controls")
model_type = st.sidebar.radio(
    "Select Model Type", ["Heuristics Net", "Directly-Follows Graph (DFG)", "Petri Net"]
)

st.subheader(f"Live Process Map: {model_type}")

if model_type == "Heuristics Net":
    dependency_thresh = st.sidebar.slider("Dependency Threshold", 0.0, 1.0, 0.5, 0.05)

    heu_net = pm4py.discover_heuristics_net(
        event_log, dependency_threshold=dependency_thresh
    )
    gviz = hn_visualizer.apply(heu_net)
    st.graphviz_chart(gviz)

elif model_type == "Directly-Follows Graph (DFG)":
    dfg, start_activities, end_activities = pm4py.discover_dfg(event_log)
    gviz = dfg_visualizer.apply(
        dfg, log=event_log, variant=dfg_visualizer.Variants.FREQUENCY
    )
    st.graphviz_chart(gviz)

elif model_type == "Petri Net":
    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(event_log)
    gviz = pn_visualizer.apply(net, initial_marking, final_marking)
    st.graphviz_chart(gviz)
