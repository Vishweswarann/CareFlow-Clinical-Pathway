
import os
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st
from auth import login, signup
from ai_workflow import (
    generate_workflow_summary,
    generate_bottleneck_analysis,
)

st.set_page_config(
    page_title="CareFlow | Clinical Pathway Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {background-color: #f4f7fb;}
    [data-testid="stSidebar"] {background-color: #10243a;}
    [data-testid="stSidebar"] * {color: #f4f7fb;}

/* Make sidebar buttons clearly visible */
[data-testid="stSidebar"] button {
    background-color: #e2e8f0 !important;
    color: #10243a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

[data-testid="stSidebar"] button p,
[data-testid="stSidebar"] button span {
    color: #10243a !important;
}

[data-testid="stSidebar"] button:hover {
    background-color: #cbd5e1 !important;
    color: #10243a !important;
}

    .main-title {
        font-size: 30px; font-weight: 750;
        color: #10243a; margin-bottom: 4px;
    }
    .subtitle {
        color: #64748b; font-size: 15px;
        margin-bottom: 25px;
    }
    .section-heading {
        font-size: 21px; font-weight: 700;
        color: #10243a; margin-top: 22px;
        margin-bottom: 15px;
    }
    .metric-card {
        background: white; border: 1px solid #e2e8f0;
        border-radius: 14px; padding: 20px;
        min-height: 115px;
    }
    .metric-label {
        color: #64748b; font-size: 12px;
        font-weight: 700; letter-spacing: 0.5px;
    }
    .metric-value {
        color: #10243a; font-size: 27px;
        font-weight: 750; margin-top: 12px;
    }
    div[data-testid="stMetric"] {
        background: white; padding: 14px;
        border: 1px solid #e2e8f0; border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# LOGIN AND SIGN UP
# --------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🏥 CareFlow")
    st.subheader("Clinical Pathway Analytics")
    st.write("Log in or create an account to continue.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input(
                "Password", type="password", key="login_password"
            )
            login_submitted = st.form_submit_button("Login")

        if login_submitted:
            if login(login_email, login_password):
                st.session_state.authenticated = True
                st.session_state.user_email = login_email.strip().lower()
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input(
                "Password", type="password", key="signup_password"
            )
            confirm_password = st.text_input(
                "Confirm password", type="password"
            )
            signup_submitted = st.form_submit_button("Create account")

        if signup_submitted:
            if signup_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = signup(signup_email, signup_password)
                if success:
                    st.success(message)
                    st.info("Open the Login tab to sign in.")
                else:
                    st.error(message)

    st.stop()

# Show logout only after successful login.
st.sidebar.write(f"Signed in as: {st.session_state.get('user_email', '')}")

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.pop("user_email", None)
    st.rerun()

# --------------------------------------------------
# DATA LOADING AND VALIDATION
# --------------------------------------------------
def load_events(source):
    if source is None:
        return None, "Select a data source to begin analysis."

    try:
        data = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source)
    except Exception as exc:
        return None, f"Could not read the event data: {exc}"

    if "timestamp" not in data.columns and "event_timestamp" in data.columns:
        data = data.rename(columns={"event_timestamp": "timestamp"})

    required = ["case_id", "activity", "timestamp"]
    missing = [column for column in required if column not in data.columns]

    if missing:
        return None, "Missing required columns: " + ", ".join(missing)

    input_rows = len(data)

    data["timestamp"] = pd.to_datetime(
        data["timestamp"], errors="coerce", utc=True
    )
    data["case_id"] = data["case_id"].astype("string").str.strip()
    data["activity"] = data["activity"].astype("string").str.strip()

    invalid = (
        data["case_id"].isna()
        | data["activity"].isna()
        | data["timestamp"].isna()
        | data["case_id"].eq("")
        | data["activity"].eq("")
    )

    invalid_rows = int(invalid.sum())
    data = data.loc[~invalid].copy()
    data = data.sort_values(["case_id", "timestamp"]).reset_index(drop=True)

    quality = {
        "input_rows": input_rows,
        "valid_rows": len(data),
        "invalid_rows": invalid_rows,
    }
    return (data, quality), None


# --------------------------------------------------
# ELAPSED-TIME CALCULATIONS
# --------------------------------------------------
def calculate_dashboard_metrics(data):
    events = data.copy()
    events["previous_activity"] = events.groupby("case_id")["activity"].shift(1)
    events["previous_timestamp"] = events.groupby("case_id")["timestamp"].shift(1)

    events["elapsed_minutes"] = (
        events["timestamp"] - events["previous_timestamp"]
    ).dt.total_seconds() / 60

    transitions = events.dropna(
        subset=["previous_activity", "elapsed_minutes"]
    ).copy()

    negative_intervals = int((transitions["elapsed_minutes"] < 0).sum())
    transitions = transitions[transitions["elapsed_minutes"] >= 0].copy()

    if transitions.empty:
        summary = pd.DataFrame(
            columns=[
                "previous_activity", "activity", "mean_minutes",
                "median_minutes", "maximum_minutes", "count",
            ]
        )
    else:
        summary = (
            transitions.groupby(["previous_activity", "activity"])["elapsed_minutes"]
            .agg(
                mean_minutes="mean",
                median_minutes="median",
                maximum_minutes="max",
                count="count",
            )
            .reset_index()
            .sort_values("mean_minutes", ascending=False)
        )

    return events, transitions, summary, negative_intervals


def format_minutes(value):
    if pd.isna(value):
        return "N/A"
    if value >= 60:
        return f"{value / 60:,.1f} h"
    return f"{value:,.1f} min"


def make_chart(fig, height=390):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=15, r=15, t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:
    st.markdown("# 🏥 CareFlow")
    st.caption("CLINICAL PATHWAY ANALYTICS")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "Activity Analysis",
            "Elapsed-Time Analysis",
            "Data Quality",
            "Process Mining",
            "Workflow Variant Analysis",
            "AI Workflow Summary",
        ],
    )

    st.divider()


    st.markdown("### Event Log")

    data_source = st.radio(
        "Data source",
        ["CSV Upload", "BigQuery"],
        index=0,
    )

    uploaded_file = None
    row_limit = 200

    if data_source == "CSV Upload":
        uploaded_file = st.file_uploader(
            "Upload an event-log CSV",
            type=["csv"],
            help="Required columns: case_id, activity, timestamp",
        )
    else:
        row_limit = st.selectbox(
            "Maximum events to load",
            [200, 500, 1000],
            index=0,
        )


        st.caption("Loads a limited sample from BigQuery.")

    st.divider()
    st.caption("CareFlow • Process Mining Project")


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------
st.markdown(
    '<div class="main-title">CareFlow Clinical Pathway Analytics</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">Explore hospital event sequences, activity patterns, '
    'elapsed-time intervals, process models, and data quality.</div>',
    unsafe_allow_html=True,
)


# --------------------------------------------------
# LOAD SELECTED DATA SOURCE
# --------------------------------------------------
if data_source == "CSV Upload":
    loaded, error = load_events(uploaded_file)
else:
    try:
        from bigquery_data import load_bigquery_events
        bigquery_data = load_bigquery_events(row_limit)
        loaded, error = load_events(bigquery_data)
    except Exception as exc:
        loaded = None
        error = f"Could not load data from BigQuery. Details: {exc}"

if error:
    st.info(error)
    if data_source == "CSV Upload":
        st.markdown(
            """
            <div class="metric-card">
            <b>Getting started:</b> Upload a CSV containing
            <code>case_id</code>, <code>activity</code>, and
            <code>timestamp</code>. No clinical statistics are invented.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            "Check Google Cloud authentication, BigQuery permissions, "
            "and the query billing limit."
        )
    st.stop()

data, quality = loaded

quality["duplicate_rows"] = int(data.duplicated().sum())

if data.empty:
    st.error("No valid event records remain after validation.")
    st.stop()

st.success(f"Loaded {len(data):,} valid events from {data_source}.")

events, transitions, transition_summary, negative_intervals = (
    calculate_dashboard_metrics(data)
)


# --------------------------------------------------
# SHARED FILTERS
# --------------------------------------------------
with st.expander("🔎 Filter the event log", expanded=False):
    activities = sorted(data["activity"].unique().tolist())
    selected_activities = st.multiselect(
        "Activities", activities, default=activities
    )

    cases = sorted(data["case_id"].unique().tolist())
    selected_cases = st.multiselect(
        "Patient encounters", cases, default=cases
    )

filtered = data[
    data["activity"].isin(selected_activities)
    & data["case_id"].isin(selected_cases)
].copy()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()
st.download_button(
    label="Download filtered event log (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="careflow_filtered_event_log.csv",
    mime="text/csv",
    help="Download event records matching the selected encounter and activity filters.",
)

# Calculate transitions from the complete event timeline first.
# Then filter existing transitions without creating artificial adjacency.
filtered_events = events[
    events["case_id"].isin(selected_cases)
    & events["activity"].isin(selected_activities)
].copy()

filtered_transitions = transitions[
    transitions["case_id"].isin(selected_cases)
    & transitions["previous_activity"].isin(selected_activities)
    & transitions["activity"].isin(selected_activities)
].copy()

if filtered_transitions.empty:
    filtered_summary = transition_summary.iloc[0:0].copy()
else:
    filtered_summary = (
        filtered_transitions.groupby(
            ["previous_activity", "activity"]
        )["elapsed_minutes"]
        .agg(
            mean_minutes="mean",
            median_minutes="median",
            maximum_minutes="max",
            count="count",
        )
        .reset_index()
        .sort_values("mean_minutes", ascending=False)
    )


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------
if page == "Overview":
    st.markdown(
        '<div class="section-heading">Operational Overview</div>',
        unsafe_allow_html=True,
    )

    average_elapsed = (
        filtered_transitions["elapsed_minutes"].mean()
        if not filtered_transitions.empty else float("nan")
    )

    metrics = [
        ("TOTAL EVENTS", f"{len(filtered):,}"),
        ("UNIQUE ENCOUNTERS", f"{filtered['case_id'].nunique():,}"),
        ("UNIQUE ACTIVITIES", f"{filtered['activity'].nunique():,}"),
        ("AVG. ELAPSED INTERVAL", format_minutes(average_elapsed)),
    ]

    columns = st.columns(4)
    for column, (label, value) in zip(columns, metrics):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### Activity and Pathway Insights")
    left, right = st.columns(2)

    with left:
        activity_counts = (
            filtered["activity"].value_counts().head(10)
            .rename_axis("activity").reset_index(name="event_count")
        )
        fig = px.bar(
            activity_counts.sort_values("event_count"),
            x="event_count", y="activity", orientation="h",
            title="Most Frequent Activities",
            labels={"event_count": "Number of events", "activity": "Activity"},
        )
        make_chart(fig)

    with right:
        if filtered_summary.empty:
            st.info("Not enough consecutive events to show transitions.")
        else:
            top = filtered_summary.head(10).copy()
            top["transition"] = (
                top["previous_activity"] + " → " + top["activity"]
            )
            fig = px.bar(
                top.sort_values("mean_minutes"),
                x="mean_minutes", y="transition", orientation="h",
                title="Transitions with Highest Mean Elapsed Time",
                labels={
                    "mean_minutes": "Mean elapsed time (minutes)",
                    "transition": "Activity transition",
                },
            )
            make_chart(fig)

    st.markdown("### Department Distribution")
    if "department" in filtered.columns:
        department_counts = (
            filtered["department"].fillna("Unknown").value_counts()
            .rename_axis("department").reset_index(name="event_count")
        )
        fig = px.pie(
            department_counts, names="department", values="event_count",
            hole=0.55, title="Events by Department",
        )
        make_chart(fig)
    else:
        st.info("Department data is unavailable for this data source.")

    st.markdown("### Patient Pathway Diagram")
    pathway_data = filtered.sort_values(["case_id", "timestamp"]).copy()
    pathway_data["next_activity"] = (
        pathway_data.groupby("case_id")["activity"].shift(-1)
    )
    pathway_data = pathway_data.dropna(subset=["next_activity"])

    if pathway_data.empty:
        st.info("Select data containing consecutive events to display pathways.")
    else:
        pathway_counts = (
            pathway_data.groupby(["activity", "next_activity"])
            .size().reset_index(name="transition_count")
            .sort_values("transition_count", ascending=False).head(20)
        )
        pathway_counts["transition"] = (
            pathway_counts["activity"] + " -> " + pathway_counts["next_activity"]
        )
        fig = px.bar(
            pathway_counts.sort_values("transition_count"),
            x="transition_count", y="transition", orientation="h",
            title="Most Frequently Observed Patient Transitions",
            labels={
                "transition_count": "Observed transitions",
                "transition": "Activity transition",
            },
        )
        make_chart(fig, height=500)
        st.caption(
            "Shows up to 20 frequent transitions in the selected sample. "
            "This is not a complete hospital workflow."
        )

    timeline = (
        filtered.groupby("timestamp").size()
        .reset_index(name="event_count").sort_values("timestamp")
    )
    fig = px.line(
        timeline, x="timestamp", y="event_count",
        title="Events Recorded Over Time",
    )
    make_chart(fig, height=350)


# --------------------------------------------------
# ACTIVITY ANALYSIS
# --------------------------------------------------
elif page == "Activity Analysis":
    st.markdown(
        '<div class="section-heading">Activity Analysis</div>',
        unsafe_allow_html=True,
    )

    activity_counts = (
        filtered["activity"].value_counts()
        .rename_axis("activity").reset_index(name="event_count")
    )

    st.metric("Activities observed", filtered["activity"].nunique())

    fig = px.bar(
        activity_counts.sort_values("event_count"),
        x="event_count", y="activity", orientation="h",
        title="Activity Frequency",
    )
    make_chart(fig, height=500)

    st.markdown("### Activity summary")
    st.dataframe(activity_counts, use_container_width=True, hide_index=True)

    st.download_button(
        "Download activity summary",
        data=activity_counts.to_csv(index=False).encode("utf-8"),
        file_name="careflow_activity_summary.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# ELAPSED-TIME ANALYSIS
# --------------------------------------------------
elif page == "Elapsed-Time Analysis":
    st.markdown(
        '<div class="section-heading">Elapsed-Time Analysis</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Elapsed intervals are calculated between consecutive recorded events "
        "within each encounter. They are not necessarily pure waiting times "
        "or proof of clinical delay."
    )

    if filtered_transitions.empty:
        st.info("No consecutive event intervals are available.")
    else:
        average = filtered_transitions["elapsed_minutes"].mean()
        median = filtered_transitions["elapsed_minutes"].median()
        maximum = filtered_transitions["elapsed_minutes"].max()

        c1, c2, c3 = st.columns(3)
        c1.metric("Mean interval", format_minutes(average))
        c2.metric("Median interval", format_minutes(median))
        c3.metric("Maximum interval", format_minutes(maximum))

        st.markdown("### Transitions with highest mean intervals")
        top = filtered_summary.head(15).copy()

        if not top.empty:
            top["transition"] = (
                top["previous_activity"] + " → " + top["activity"]
            )
            fig = px.bar(
                top.sort_values("mean_minutes"),
                x="mean_minutes", y="transition", orientation="h",
                title="Mean Elapsed Time by Transition",
            )
            make_chart(fig, height=500)

        st.markdown("### Transition statistics")
        display_summary = filtered_summary.rename(
            columns={
                "previous_activity": "Previous activity",
                "activity": "Next activity",
                "mean_minutes": "Mean minutes",
                "median_minutes": "Median minutes",
                "maximum_minutes": "Maximum minutes",
                "count": "Transition count",
            }
        )
        st.dataframe(display_summary, use_container_width=True, hide_index=True)

        st.download_button(
            "Download transition summary",
            data=display_summary.to_csv(index=False).encode("utf-8"),
            file_name="careflow_transition_summary.csv",
            mime="text/csv",
        )


# --------------------------------------------------
# DATA QUALITY
# --------------------------------------------------
elif page == "Data Quality":
    st.markdown(
        '<div class="section-heading">Data Quality Report</div>',
        unsafe_allow_html=True,
    )
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Input rows", f"{quality['input_rows']:,}")
    q2.metric("Valid rows", f"{quality['valid_rows']:,}")
    q3.metric("Invalid rows removed", f"{quality['invalid_rows']:,}")
    q4.metric("Exact duplicate rows", f"{quality['duplicate_rows']:,}")

    checks = pd.DataFrame([
        {
            "Check": "Required columns present",
            "Result": "Passed",
            "Details": "case_id, activity, timestamp",
        },
        {
            "Check": "Missing or invalid required values",
            "Result": "Review required" if quality["invalid_rows"] else "Passed",
            "Details": f"{quality['invalid_rows']} invalid rows removed",
        },
        {
            "Check": "Negative elapsed intervals",
            "Result": "Review required" if negative_intervals else "Passed",
            "Details": str(negative_intervals),
        },
        {
            "Check": "Exact duplicate event rows",
            "Result": "Review required" if quality["duplicate_rows"] else "Passed",
            "Details": f"{quality['duplicate_rows']} exact duplicate rows found",
        },
    ])
    st.dataframe(checks, use_container_width=True, hide_index=True)

    st.markdown("### Event data preview")
    st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)


# --------------------------------------------------
# PROCESS MINING
# --------------------------------------------------
elif page == "Process Mining":
    st.markdown(
        '<div class="section-heading">Process Mining & Clinical Pathways</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Models use the currently loaded and filtered event data. "
        "No separate BigQuery query is made by this page."
    )

    try:
        import pm4py
        from pm4py.visualization.dfg import visualizer as dfg_visualizer
        from pm4py.visualization.petri_net import visualizer as pn_visualizer
        from pm4py.visualization.heuristics_net import visualizer as hn_visualizer
    except ImportError:
        st.error(
            "PM4Py is not installed. Add pm4py to requirements.txt and redeploy."
        )
        st.stop()

    process_df = filtered[["case_id", "activity", "timestamp"]].copy()
    process_df = process_df.dropna()
    process_df["case_id"] = process_df["case_id"].astype(str)
    process_df["activity"] = process_df["activity"].astype(str)
    process_df = process_df.sort_values(
        ["case_id", "timestamp"]
    ).reset_index(drop=True)

    if process_df.empty:
        st.warning("No valid events are available for process mining.")
        st.stop()

    # REWORK ANALYSIS: repeated activity types within each encounter
    st.markdown("### Rework Analysis")
    st.caption(
        "Repeated activity types are counted within each encounter. "
        "A repeat does not automatically indicate an error."
    )

    repeated_events = process_df[
        process_df.duplicated(
            subset=["case_id", "activity"], keep=False
        )
    ].copy()

    if repeated_events.empty:
        st.info("No repeated activity types were found in the selected data.")
    else:
        rework_by_activity = (
            repeated_events.groupby("activity")["case_id"]
            .nunique()
            .reset_index(name="encounters_with_repeat")
            .sort_values("encounters_with_repeat", ascending=False)
        )

        rework_cases = repeated_events["case_id"].nunique()
        total_cases = process_df["case_id"].nunique()

        metric_col1, metric_col2 = st.columns(2)
        metric_col1.metric(
            "Encounters with repeated activities", f"{rework_cases:,}"
        )
        metric_col2.metric("Total encounters analyzed", f"{total_cases:,}")

        st.markdown("#### Most frequently repeated activities")
        st.dataframe(
            rework_by_activity,
            use_container_width=True,
            hide_index=True,
        )

    try:
        event_log = pm4py.format_dataframe(
            process_df,
            case_id="case_id",
            activity_key="activity",
            timestamp_key="timestamp",
        )
    except Exception as exc:
        st.error(f"Could not prepare the event log: {exc}")
        st.stop()

    model_type = st.radio(
        "Choose process model",
        [
            "Heuristics Net",
            "Directly-Follows Graph (DFG)",
            "Petri Net",
            "Interactive Pathway Map",
            "Conformance Checking",
        ],
        horizontal=True,
    )

    if model_type == "Heuristics Net":
        dependency_thresh = st.slider(
            "Dependency threshold", 0.0, 1.0, 0.5, 0.05
        )
        try:
            heu_net = pm4py.discover_heuristics_net(
                event_log, dependency_threshold=dependency_thresh
            )
            st.graphviz_chart(hn_visualizer.apply(heu_net))
        except Exception as exc:
            st.error(f"Could not generate the Heuristics Net: {exc}")

    elif model_type == "Directly-Follows Graph (DFG)":
        try:
            dfg, start_activities, end_activities = pm4py.discover_dfg(
                event_log
            )

            if not dfg:
                st.warning(
                    "No consecutive activity transitions were found. "
                    "Each encounter needs at least two valid events "
                    "to generate a Directly-Follows Graph."
                )
            else:
                st.graphviz_chart(
                    dfg_visualizer.apply(
                        dfg,
                        log=event_log,
                        variant=dfg_visualizer.Variants.FREQUENCY,
                    )
                )
                st.caption(
                    f"Start activity types: {len(start_activities)} · "
                    f"End activity types: {len(end_activities)}"
                )

        except Exception as exc:
            st.error(f"Could not generate the DFG: {exc}")

    elif model_type == "Petri Net":
        try:
            net, initial_marking, final_marking = (
                pm4py.discover_petri_net_inductive(event_log)
            )
            st.graphviz_chart(
                pn_visualizer.apply(net, initial_marking, final_marking)
            )
        except Exception as exc:
            st.error(f"Could not generate the Petri Net: {exc}")


    elif model_type == "Conformance Checking":
        st.markdown("### Conformance Checking")
        st.caption(
            "Compares observed patient journeys against a Petri Net "
            "discovered from the currently selected event log."
        )

        try:
            from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
            from pm4py.algo.evaluation.replay_fitness import algorithm as replay_fitness
            from pm4py.algo.evaluation.precision import algorithm as precision_evaluator

            with st.spinner("Evaluating patient journeys..."):
                net, initial_marking, final_marking = (
                    pm4py.discover_petri_net_inductive(event_log)
                )

                replay_results = token_replay.apply(
                    event_log, net, initial_marking, final_marking
                )

                fitness = replay_fitness.apply(
                    event_log, net, initial_marking, final_marking
                )

                precision_score = precision_evaluator.apply(
                    event_log, net, initial_marking, final_marking
                )

            fitting_traces = sum(
                1 for result in replay_results
                if result.get("trace_is_fit", False)
            )
            total_traces = len(replay_results)
            deviations = total_traces - fitting_traces

            metric1, metric2, metric3, metric4 = st.columns(4)
            metric1.metric(
                "Process Fitness",
                f"{fitness['average_trace_fitness'] * 100:.2f}%"
            )
            metric2.metric(
                "Process Precision",
                f"{precision_score * 100:.2f}%"
            )
            metric3.metric(
                "Fitting Encounters",
                f"{fitting_traces:,} / {total_traces:,}"
            )
            metric4.metric(
                "Deviating Encounters",
                f"{deviations:,}"
            )
            st.markdown("#### Patient Journey Replay Results")


            replay_event_log = pm4py.convert_to_event_log(event_log)
            trace_rows = []

            for index, (trace, result) in enumerate(
                zip(replay_event_log, replay_results)
            ):
                trace_rows.append({
                    "Case ID": trace.attributes.get(
                        "concept:name", f"Trace {index + 1}"
                    ),
                    "Fitting": "Yes" if result.get("trace_is_fit") else "No",
                    "Trace Fitness": round(
                        result.get("trace_fitness", 0) * 100, 2
                    ),
                    "Missing Tokens": result.get("missing_tokens", 0),
                    "Remaining Tokens": result.get("remaining_tokens", 0),
                })

            trace_df = pd.DataFrame(trace_rows)

            st.dataframe(
                trace_df.sort_values(
                    ["Fitting", "Trace Fitness"],
                    ascending=[True, True]
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Token replay identifies deviations relative to this "
                "discovered model. It does not establish clinical non-compliance."
            )

        except Exception as exc:
            st.error(f"Conformance checking failed: {exc}")

    elif model_type == "Interactive Pathway Map":
        st.markdown("### Interactive pathway abstraction")

        st.caption(
            "This is a frequency-filtered DFG (fuzzy-style abstraction), "
            "not PM4Py's native Fuzzy Miner algorithm."
        )

        node_retention = st.slider(
            "Node frequency threshold", 0.0, 1.0, 0.80, 0.05
        )
        edge_retention = st.slider(
            "Path frequency threshold", 0.0, 1.0, 0.70, 0.05
        )

        try:
            from pm4py.algo.filtering.dfg import dfg_filtering
            dfg, start_activities, end_activities = pm4py.discover_dfg(event_log)
            activity_counts = process_df["activity"].value_counts().to_dict()

            filtered_dfg, starts, ends, activities_kept = (
                dfg_filtering.filter_dfg_on_activities_percentage(
                    dfg, start_activities, end_activities,
                    activity_counts, node_retention,
                )
            )
            filtered_dfg, starts, ends, activities_kept = (
                dfg_filtering.filter_dfg_on_paths_percentage(
                    filtered_dfg, starts, ends,
                    activities_kept, edge_retention,
                )
            )

            if not filtered_dfg:
                st.warning("No paths remain. Lower the frequency thresholds.")
            else:
                try:
                    from pyvis.network import Network
                    import streamlit.components.v1 as components

                    net = Network(
                        height="600px", width="100%", directed=True,
                        bgcolor="#ffffff", font_color="#0f172a",
                    )
                    net.set_options("""
                    {
                      "physics": {"enabled": false},
                      "layout": {"hierarchical": {
                        "enabled": true, "direction": "LR",
                        "sortMethod": "directed", "nodeSpacing": 150,
                        "levelSeparation": 180
                      }},
                      "edges": {"smooth": {
                        "type": "cubicBezier", "forceDirection": "horizontal",
                        "roundness": 0.4
                      }},
                      "interaction": {
                        "navigationButtons": true, "zoomView": true,
                        "dragView": true
                      }
                    }
                    """)

                    nodes = set()
                    for (src, dst), count in filtered_dfg.items():
                        for node in (src, dst):
                            if node not in nodes:
                                net.add_node(
                                    node, label=node, shape="box",
                                    color={
                                        "background": "#bae6fd",
                                        "border": "#38bdf8",
                                    },
                                    font={"size": 16, "color": "#0f172a"},
                                )
                                nodes.add(node)
                        net.add_edge(
                            src, dst, value=count, label=str(count),
                            title=f"Observed transition count: {count}",
                            arrows="to",
                        )

                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".html", delete=False,
                        encoding="utf-8",
                    ) as tmp:
                        html_path = tmp.name

                    try:
                        net.save_graph(html_path)
                        with open(html_path, "r", encoding="utf-8") as f:
                            components.html(f.read(), height=620, scrolling=True)
                    finally:
                        if os.path.exists(html_path):
                            os.remove(html_path)

                except ImportError:
                    st.warning(
                        "PyVis is missing. Add pyvis to requirements.txt "
                        "to show the interactive map."
                    )
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "From activity": src,
                                "To activity": dst,
                                "Observed transitions": count,
                            }
                            for (src, dst), count in filtered_dfg.items()
                        ]),
                        use_container_width=True,
                        hide_index=True,
                    )

            st.markdown("### Patient timeline")
            all_activities = sorted(process_df["activity"].unique().tolist())
            timeline_activities = st.multiselect(
                "Activities to display",
                all_activities,
                default=all_activities,
            )

            timeline_df = process_df[
                process_df["activity"].isin(timeline_activities)
            ].copy()

            if timeline_df.empty:
                st.info("No timeline events match the selected activities.")
            else:
                arrivals = (
                    timeline_df.groupby("case_id")["timestamp"]
                    .min().rename("arrival_time").reset_index()
                )
                timeline_df = timeline_df.merge(arrivals, on="case_id")
                timeline_df = timeline_df.sort_values(
                    ["arrival_time", "timestamp"]
                )

                fig = px.scatter(
                    timeline_df,
                    x="timestamp",
                    y="case_id",
                    color="activity",
                    title="CareFlow Event Timeline",
                    hover_data=["activity", "timestamp"],
                )
                fig.update_layout(
                    yaxis=dict(
                        type="category", categoryorder="trace",
                        showticklabels=False,
                        title="Patient encounters (ordered by arrival)",
                    ),
                    xaxis=dict(title="Time of clinical event"),
                    height=600,
                )
                fig.update_traces(marker=dict(size=8, opacity=0.7))
                make_chart(fig, height=600)

        except Exception as exc:
            st.error(f"Could not generate the interactive pathway map: {exc}")

# --------------------------------------------------
# WORKFLOW VARIANT ANALYSIS
# --------------------------------------------------
elif page == "Workflow Variant Analysis":
    st.markdown(
        '<div class="section-heading">Clinical Workflow Variant Analysis</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Explore the different event sequences observed across encounters. "
        "These are descriptive patterns, not clinical compliance judgments. "
        "BigQuery results may represent partial encounters because data is sampled."
    )

    if filtered.empty:
        st.info("No events are available for workflow analysis.")
    else:
        workflows = (
            filtered.sort_values(["case_id", "timestamp"])
            .groupby("case_id")["activity"]
            .agg(lambda activities: " → ".join(activities.astype(str)))
            .reset_index(name="Observed sequence")
        )

        variants = (
            workflows.groupby("Observed sequence")
            .size()
            .reset_index(name="Encounter count")
            .sort_values("Encounter count", ascending=False)
        )

        variants["Percentage"] = (
            variants["Encounter count"] / len(workflows) * 100
        ).round(2)

        c1, c2, c3 = st.columns(3)
        c1.metric("Encounters analysed", f"{len(workflows):,}")
        c2.metric("Distinct workflow variants", f"{len(variants):,}")
        c3.metric(
            "Most common variant",
            f"{variants.iloc[0]['Encounter count']:,}",
        )

        st.markdown("### Most frequently observed workflows")

        st.dataframe(
            variants.head(15),
            use_container_width=True,
            hide_index=True,
        )

        fig = px.bar(
            variants.head(10).sort_values("Encounter count"),
            x="Encounter count",
            y="Observed sequence",
            orientation="h",
            title="Top 10 Observed Workflow Variants",
        )
        make_chart(fig, height=550)

        st.download_button(
            "Download workflow variant report",
            data=variants.to_csv(index=False).encode("utf-8"),
            file_name="careflow_workflow_variants.csv",
            mime="text/csv",
        )

# --------------------------------------------------
# AI WORKFLOW SUMMARY
# --------------------------------------------------
elif page == "AI Workflow Summary":
    st.markdown("## AI Workflow Summary")

    if filtered.empty:
        st.info("No events available for analysis.")
    else:
        workflows = (
            filtered.sort_values(["case_id", "timestamp"])
            .groupby("case_id")["activity"]
            .agg(lambda x: " → ".join(x.astype(str)))
        )

        summary_data = {
            "encounters": int(len(workflows)),
            "events": int(len(filtered)),
            "distinct_activities": int(filtered["activity"].nunique()),
            "common_activities": filtered["activity"].value_counts().head(8).to_dict(),
            "common_workflows": workflows.value_counts().head(5).to_dict(),
        }

        st.write("Aggregate workflow statistics are ready.")

        # AI WORKFLOW SUMMARY
        if st.button("Generate AI Workflow Summary"):
            with st.spinner("Gemini is analysing workflow patterns..."):
                try:
                    result = generate_workflow_summary(summary_data)
                    st.markdown("### AI Analysis")
                    st.write(result)
                except Exception as exc:
                    st.error(f"AI analysis failed: {exc}")

        # AI BOTTLENECK ANALYSIS
        st.divider()
        st.markdown("### AI Bottleneck Analysis")

        if filtered_summary.empty:
            st.info("No transition data available for bottleneck analysis.")
        elif st.button("Generate AI Bottleneck Analysis"):
            transition_data = filtered_summary.to_dict(orient="records")

            with st.spinner("Gemini is analysing transition times..."):
                try:
                    result = generate_bottleneck_analysis(transition_data)
                    st.markdown("### Bottleneck Insights")
                    st.write(result)
                except Exception as exc:
                    st.error(f"Bottleneck analysis failed: {exc}")


# --------------------------------------------------
# AI WORKFLOW SUMMARY
# --------------------------------------------------
elif page == "AI Workflow Summary":
    st.markdown("## AI Workflow Summary")

    if filtered.empty:
        st.info("No events available for analysis.")
    else:
        workflows = (
            filtered.sort_values(["case_id", "timestamp"])
            .groupby("case_id")["activity"]
            .agg(lambda x: " → ".join(x.astype(str)))
        )

        summary_data = {
            "encounters": int(len(workflows)),
            "events": int(len(filtered)),
            "distinct_activities": int(filtered["activity"].nunique()),
            "common_activities": filtered["activity"].value_counts().head(8).to_dict(),
            "common_workflows": workflows.value_counts().head(5).to_dict(),
        }

        st.write("Aggregate workflow statistics are ready.")

        # AI WORKFLOW SUMMARY
        if st.button("Generate AI Workflow Summary"):
            with st.spinner("Gemini is analysing workflow patterns..."):
                try:
                    result = generate_workflow_summary(summary_data)
                    st.markdown("### AI Analysis")
                    st.write(result)
                except Exception as exc:
                    st.error(f"AI analysis failed: {exc}")

        # AI BOTTLENECK ANALYSIS
        st.divider()
        st.markdown("### AI Bottleneck Analysis")

        if filtered_summary.empty:
            st.info("No transition data available for bottleneck analysis.")
        elif st.button("Generate AI Bottleneck Analysis"):
            transition_data = filtered_summary.to_dict(orient="records")

            with st.spinner("Gemini is analysing transition times..."):
                try:
                    result = generate_bottleneck_analysis(transition_data)
                    st.markdown("### Bottleneck Insights")
                    st.write(result)
                except Exception as exc:
                    st.error(f"Bottleneck analysis failed: {exc}")



# --------------------------------------------------
# AI WORKFLOW SUMMARY
# --------------------------------------------------
elif page == "AI Workflow Summary":
    st.markdown("## AI Workflow Summary")

    if filtered.empty:
        st.info("No events available for analysis.")
    else:
        workflows = (
            filtered.sort_values(["case_id", "timestamp"])
            .groupby("case_id")["activity"]
            .agg(lambda x: " → ".join(x.astype(str)))
        )

        summary_data = {
            "encounters": int(len(workflows)),
            "events": int(len(filtered)),
            "distinct_activities": int(filtered["activity"].nunique()),
            "common_activities": filtered["activity"].value_counts().head(8).to_dict(),
            "common_workflows": workflows.value_counts().head(5).to_dict(),
        }

        st.write("Aggregate workflow statistics are ready.")

        # AI WORKFLOW SUMMARY
        if st.button("Generate AI Workflow Summary"):
            with st.spinner("Gemini is analysing workflow patterns..."):
                try:
                    result = generate_workflow_summary(summary_data)
                    st.markdown("### AI Analysis")
                    st.write(result)
                except Exception as exc:
                    st.error(f"AI analysis failed: {exc}")

        # AI BOTTLENECK ANALYSIS
        st.divider()
        st.markdown("### AI Bottleneck Analysis")

        if filtered_summary.empty:
            st.info("No transition data available for bottleneck analysis.")
        elif st.button("Generate AI Bottleneck Analysis"):
            transition_data = filtered_summary.to_dict(orient="records")

            with st.spinner("Gemini is analysing transition times..."):
                try:
                    result = generate_bottleneck_analysis(transition_data)
                    st.markdown("### Bottleneck Insights")
                    st.write(result)
                except Exception as exc:
                    st.error(f"Bottleneck analysis failed: {exc}")
# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()
st.caption(
    "CareFlow Clinical Pathway Analytics • "
    "Metrics are calculated from the selected event data."
)
