import streamlit as st
import pandas as pd
import pm4py
from google.cloud import bigquery
from google.oauth2 import service_account
from pyvis.network import Network
import streamlit.components.v1 as components

st.subheader("👨‍⚕️ Clinician-Centric Process & Workflow Audit")
st.markdown(
    "Monitoring staff-level execution: pivoting the event log to treat individual "
    "doctors and nurses as traces to audit their operational paths and task-switching friction."
)


@st.cache_data
def fetch_clinician_perspective_data():
    if "gcp_service_account" in st.secrets:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = bigquery.Client(
            credentials=credentials, project="careflow-analytics-98234"
        )
    else:
        client = bigquery.Client(project="careflow-analytics-98234")

    query = """
        SELECT 
            event_id, case_id, resource_id, resource_role, 
            activity, timestamp, department, event_detail
        FROM `careflow-analytics-98234.careflow_analytics.event_logs`
        WHERE resource_id IS NOT NULL
        ORDER BY resource_id, timestamp
    """
    print("Before Query")
    df = client.query(query).to_dataframe()
    print("After Query")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


with st.spinner("Aggregating clinician workflow logs from BigQuery..."):
    clinician_df = fetch_clinician_perspective_data()

    all_staff = clinician_df["resource_id"].unique()
    selected_staff = st.sidebar.selectbox(
        "Audit Specific Clinician Staff ID:",
        options=["All Staff (Hospital Aggregate)"] + list(all_staff),
    )

    if selected_staff != "All Staff (Hospital Aggregate)":
        filtered_staff_df = clinician_df[clinician_df["resource_id"] == selected_staff]
        st.info(
            f"Currently auditing workflow for staff ID: **{selected_staff}** ({filtered_staff_df['resource_role'].iloc[0]})"
        )
    else:
        filtered_staff_df = clinician_df

# ---------------------------------------------------------
# 3. Process Mining on Clinician Traces
# ---------------------------------------------------------
# Pivot perspective: resource_id acts as the case_id
staff_event_log = pm4py.format_dataframe(
    filtered_staff_df,
    case_id="resource_id",
    activity_key="activity",
    timestamp_key="timestamp",
)

# Discover Directly-Follows Graph (DFG) for staff tasks
staff_dfg, start_act, end_act = pm4py.discover_dfg(staff_event_log)


# ---------------------------------------------------------
# 4. Render the Clinician Workflow Map (PyVis)
# ---------------------------------------------------------
def generate_clinician_workflow_map(dfg_dict):
    net = Network(
        height="550px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#0f172a",
    )

    net.set_options("""
        {
        "physics": { 
            "enabled": true,
            "barnesHut": {
            "gravitationalConstant": -3000,
            "centralGravity": 0.3,
            "springLength": 150,
            "springConstant": 0.04
            }
        },
        "layout": {
            "hierarchical": {
            "enabled": false
            }
        },
        "edges": {
            "smooth": { 
            "type": "dynamic" 
            }
        },
        "interaction": { 
            "navigationButtons": true, 
            "zoomView": true, 
            "dragView": true 
        }
        }
        """)
    nodes_added = set()
    for (source, target), weight in dfg_dict.items():
        if source not in nodes_added:
            net.add_node(
                source,
                label=source,
                shape="box",
                color={
                    "background": "#fed7aa",
                    "border": "#fb923c",
                },  # Warm amber for staff tasks
                font={"size": 16, "color": "#0f172a", "bold": True},
                margin=12,
            )
            nodes_added.add(source)

        if target not in nodes_added:
            net.add_node(
                target,
                label=target,
                shape="box",
                color={"background": "#fed7aa", "border": "#fb923c"},
                font={"size": 16, "color": "#0f172a", "bold": True},
                margin=12,
            )
            nodes_added.add(target)

        net.add_edge(
            source,
            target,
            value=weight,
            label=str(weight),
            title=f"Transition Frequency: {weight} times",
            color={"color": "#94a3b8", "highlight": "#ea580c"},
            arrows="to",
        )

    html_path = "clinician_workflow_map.html"
    net.save_graph(html_path)
    return html_path


st.subheader("Staff Task-Transition Map")
st.markdown(
    "Shows the operational sequence of tasks executed by clinical staff during their shifts."
)

map_file = generate_clinician_workflow_map(staff_dfg)
with open(map_file, "r", encoding="utf-8") as f:
    components.html(f.read(), height=570)

# ---------------------------------------------------------
# 5. Staff Workload & Performance Summary Table
# ---------------------------------------------------------
st.subheader("Clinician Workload & Task Metrics")
summary_table = (
    filtered_staff_df.groupby(["resource_id", "resource_role"], as_index=False)
    .agg(
        Total_Actions=("event_id", "count"),
        Unique_Patients_Handled=("case_id", "nunique"),
        Departments_Visited=("department", "nunique"),
    )
    .sort_values("Total_Actions", ascending=False)
)

st.dataframe(summary_table, use_container_width=True, hide_index=True)
