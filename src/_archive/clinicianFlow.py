import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import bigquery
from google.oauth2 import service_account
import pm4py


# ---------------------------------------------------------
# 1. Fetch Department & Resource-Level Data from BigQuery
# ---------------------------------------------------------
@st.cache_data
def fetch_clinician_flow_data():
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
            case_id, activity, timestamp, department, 
            event_sequence, resource_role, resource_id, event_detail, 
            arrival_mode, chief_complaint, triage_level, disposition
        FROM `careflow-analytics-98234.careflow_analytics.event_logs`
        ORDER BY case_id, event_sequence
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


st.subheader("🩺 Clinician & Departmental Flow Audit")
st.markdown(
    "Brutal operational transparency for doctors and nurses: "
    "track department wait times, staff workloads, and handoff friction."
)

df = fetch_clinician_flow_data()

# ---------------------------------------------------------
# 2. Calculate Inter-Departmental Wait Times (The Brutal Truth)
# ---------------------------------------------------------
# Sort to find time spent between consecutive steps per patient
df["next_timestamp"] = df.groupby("case_id")["timestamp"].shift(-1)
df["next_activity"] = df.groupby("case_id")["activity"].shift(-1)
df["next_department"] = df.groupby("case_id")["department"].shift(-1)

df["duration_minutes"] = (
    df["next_timestamp"] - df["timestamp"]
).dt.total_seconds() / 60.0

# Drop negative or extreme outliers caused by parallel tracks
valid_transitions = df[
    (df["duration_minutes"] > 0) & (df["duration_minutes"] < 1440)
].copy()

emergency_conditions = (df["arrival_mode"] == "Ambulance") | (
    df["triage_level"].isin([1, 2])
)

df["is_emergency"] = emergency_conditions

# Separate the dataframes
emergency_df = df[df["is_emergency"] == True]
standard_df = df[df["is_emergency"] == False]

# Convert to PM4Py event logs separately
emergency_log = pm4py.format_dataframe(
    emergency_df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
)
standard_log = pm4py.format_dataframe(
    standard_df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
)

st.sidebar.subheader("Patient Acuity Filter")
flow_type = st.sidebar.radio(
    "Select Workflow Type to Audit:",
    options=["Routine / Walk-in", "High-Acuity / Emergency", "All Cases"],
)

if flow_type == "High-Acuity / Emergency":
    filtered_df = df[df["is_emergency"] == True]
elif flow_type == "Routine / Walk-in":
    filtered_df = df[df["is_emergency"] == False]
else:
    filtered_df = df


# ---------------------------------------------------------
# 3. Clinician Workload & Bottleneck Metrics
# ---------------------------------------------------------
col1, col2, col3 = st.columns(3)

active_patients = df[df["disposition"].isna() | (df["disposition"] == "Admitted")][
    "case_id"
].nunique()
avg_wait_time = valid_transitions[valid_transitions["activity"] == "Triage"][
    "duration_minutes"
].mean()
rework_events = df[
    df["event_detail"].str.contains("incomplete|repeat|re-triage", case=False, na=False)
].shape[0]

col1.metric("Active Patient Load", active_patients, help="Patients currently in system")
col2.metric(
    "Avg Triage-to-Consult Wait",
    f"{avg_wait_time:.1f} mins" if pd.notnull(avg_wait_time) else "N/A",
)
col3.metric(
    "Documented Charting Errors / Rework",
    rework_events,
    help="Incomplete forms or bounced handoffs",
)

st.divider()

# ---------------------------------------------------------
# 4. Staff & Departmental Workload Visualizations
# ---------------------------------------------------------
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("Patient Volume Handled by Staff Role")
    role_counts = df.groupby(["resource_role", "department"], as_index=False)[
        "case_id"
    ].count()
    role_counts.rename(columns={"case_id": "Total Actions"}, inplace=True)

    fig_role = px.bar(
        role_counts,
        x="Total Actions",
        y="resource_role",
        color="department",
        orientation="h",
        title="Task Distribution Across Clinical Roles",
        text_auto=True,
    )
    fig_role.update_layout(plot_bgcolor="white", height=400)
    st.plotly_chart(fig_role, use_container_width=True)

with c_right:
    st.subheader("Departmental Bottleneck (Avg Duration per Step)")
    dept_duration = (
        valid_transitions.groupby("department", as_index=False)["duration_minutes"]
        .mean()
        .sort_values("duration_minutes", ascending=True)
    )

    fig_dept = px.bar(
        dept_duration,
        x="duration_minutes",
        y="department",
        orientation="h",
        color="duration_minutes",
        color_continuous_scale="Reds",
        title="Where Do Patients Sit Longest? (Minutes)",
        text_auto=".1f",
    )
    fig_dept.update_layout(plot_bgcolor="white", height=400)
    st.plotly_chart(fig_dept, use_container_width=True)

# ---------------------------------------------------------
# 5. Live Clinician Alert Log (The "Bounced Patient" Feed)
# ---------------------------------------------------------
st.subheader("🚨 Live Friction Feed: Bounced & Delayed Patients")
st.markdown(
    "Patients who experienced rework, form rejections, or extended handoff lags:"
)

friction_df = df[
    df["event_detail"].str.contains(
        "incomplete|re-triage|follow-up", case=False, na=False
    )
][
    [
        "timestamp",
        "case_id",
        "department",
        "resource_role",
        "event_detail",
        "chief_complaint",
    ]
].sort_values("timestamp", ascending=False)

if not friction_df.empty:
    st.dataframe(friction_df, use_container_width=True, hide_index=True)
else:
    st.success("No active clinical handoff frictions logged in current window.")
