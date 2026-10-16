
import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="CareFlow | Clinical Pathway Analytics",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# STYLING
# --------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4f7fb;
    }

    [data-testid="stSidebar"] {
        background-color: #10243a;
    }

    [data-testid="stSidebar"] * {
        color: #f4f7fb;
    }

    .main-title {
        font-size: 30px;
        font-weight: 750;
        color: #10243a;
        margin-bottom: 4px;
    }

    .subtitle {
        color: #64748b;
        font-size: 15px;
        margin-bottom: 25px;
    }

    .section-heading {
        font-size: 21px;
        font-weight: 700;
        color: #10243a;
        margin-top: 22px;
        margin-bottom: 15px;
    }

    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 20px;
        min-height: 115px;
        box-shadow: 0 3px 12px rgba(15, 35, 60, 0.04);
    }

    .metric-label {
        color: #64748b;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    .metric-value {
        color: #10243a;
        font-size: 27px;
        font-weight: 750;
        margin-top: 12px;
    }

    .info-note {
        background: white;
        border: 1px solid #dbe5f0;
        border-radius: 12px;
        padding: 18px;
        color: #334155;
        line-height: 1.7;
    }

    div[data-testid="stMetric"] {
        background: white;
        padding: 14px;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# DATA LOADING AND VALIDATION
# --------------------------------------------------
def load_events(source):
    """Load and validate CSV or BigQuery event data."""

    if source is None:
        return None, "Select a data source to begin analysis."

    try:
        if isinstance(source, pd.DataFrame):
            data = source.copy()
        else:
            data = pd.read_csv(source)
    except Exception as exc:
        return None, f"Could not read the event data: {exc}"

    if "timestamp" not in data.columns:
        if "event_timestamp" in data.columns:
            data = data.rename(
                columns={"event_timestamp": "timestamp"}
            )

    required = ["case_id", "activity", "timestamp"]

    missing = [
        column
        for column in required
        if column not in data.columns
    ]

    if missing:
        return None, (
            "Missing required columns: "
            + ", ".join(missing)
        )

    input_rows = len(data)

    data["timestamp"] = pd.to_datetime(
        data["timestamp"],
        errors="coerce",
        utc=True,
    )

    data["case_id"] = (
        data["case_id"].astype("string").str.strip()
    )

    data["activity"] = (
        data["activity"].astype("string").str.strip()
    )

    invalid = (
        data["case_id"].isna()
        | data["activity"].isna()
        | data["timestamp"].isna()
        | data["case_id"].eq("")
        | data["activity"].eq("")
    )

    invalid_rows = int(invalid.sum())

    data = data.loc[~invalid].copy()

    data = data.sort_values(
        ["case_id", "timestamp"]
    ).reset_index(drop=True)

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

    events["previous_activity"] = (
        events.groupby("case_id")["activity"].shift(1)
    )

    events["previous_timestamp"] = (
        events.groupby("case_id")["timestamp"].shift(1)
    )

    events["elapsed_minutes"] = (
        events["timestamp"] - events["previous_timestamp"]
    ).dt.total_seconds() / 60

    transitions = events.dropna(
        subset=["previous_activity", "elapsed_minutes"]
    ).copy()

    negative_intervals = int(
        (transitions["elapsed_minutes"] < 0).sum()
    )

    transitions = transitions[
        transitions["elapsed_minutes"] >= 0
    ].copy()

    if transitions.empty:
        summary = pd.DataFrame(
            columns=[
                "previous_activity",
                "activity",
                "mean_minutes",
                "median_minutes",
                "maximum_minutes",
                "count",
            ]
        )
    else:
        summary = (
            transitions
            .groupby(["previous_activity", "activity"])
            ["elapsed_minutes"]
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
        ],
    )

    st.divider()
    st.markdown("### Event Log")

    data_source = st.radio(
        "Data source",
        ["CSV Upload", "BigQuery"],
    )

    uploaded_file = None
    row_limit = 1000

    if data_source == "CSV Upload":
        uploaded_file = st.file_uploader(
            "Upload an event-log CSV",
            type=["csv"],
            help="Required columns: case_id, activity, timestamp",
        )
    else:
        row_limit = st.selectbox(
            "Maximum events to load",
            [1000, 5000],
            index=0,
        )

        st.caption("Loads a limited sample from BigQuery.")

    st.divider()
    st.caption("CareFlow • Process Mining Project")


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------
st.markdown(
    '<div class="main-title">'
    'CareFlow Clinical Pathway Analytics</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Explore hospital event sequences, activity patterns, '
    'elapsed-time intervals, and data quality.'
    '</div>',
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
        error = (
            "Could not load data from BigQuery. "
            f"Details: {exc}"
        )

if error:
    st.info(error)

    if data_source == "CSV Upload":
        st.markdown(
            """
            <div class="info-note">
            <b>Getting started:</b> Upload a CSV containing
            <code>case_id</code>, <code>activity</code>, and
            <code>timestamp</code>. The dashboard analyzes the
            uploaded records and does not invent clinical statistics.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            "Check your Google Cloud authentication, "
            "BigQuery permissions, and query billing limit."
        )

    st.stop()

data, quality = loaded

if data.empty:
    st.error("No valid event records remain after validation.")
    st.stop()

st.success(
    f"Loaded {len(data):,} valid events from {data_source}."
)

events, transitions, transition_summary, negative_intervals = (
    calculate_dashboard_metrics(data)
)


# --------------------------------------------------
# FILTERS
# --------------------------------------------------
with st.expander("🔎 Filter the event log", expanded=False):
    activities = sorted(data["activity"].unique().tolist())

    selected_activities = st.multiselect(
        "Activities",
        options=activities,
        default=activities,
    )

    cases = sorted(data["case_id"].unique().tolist())

    selected_cases = st.multiselect(
        "Patient encounters",
        options=cases,
        default=cases,
    )

filtered = data[
    data["activity"].isin(selected_activities)
    & data["case_id"].isin(selected_cases)
].copy()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

filtered_events, filtered_transitions, filtered_summary, _ = (
    calculate_dashboard_metrics(filtered)
)


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------
if page == "Overview":
    st.markdown(
        '<div class="section-heading">'
        'Operational Overview</div>',
        unsafe_allow_html=True,
    )

    average_elapsed = (
        filtered_transitions["elapsed_minutes"].mean()
        if not filtered_transitions.empty
        else float("nan")
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
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="section-heading">'
        'Activity and Pathway Insights</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        activity_counts = (
            filtered["activity"]
            .value_counts()
            .head(10)
            .rename_axis("activity")
            .reset_index(name="event_count")
        )

        fig = px.bar(
            activity_counts.sort_values("event_count"),
            x="event_count",
            y="activity",
            orientation="h",
            title="Most Frequent Activities",
            labels={
                "event_count": "Number of events",
                "activity": "Activity",
            },
            color_discrete_sequence=["#3984C6"],
        )

        make_chart(fig)

    with right:
        if filtered_summary.empty:
            st.info(
                "Not enough consecutive events to show transitions."
            )
        else:
            top = filtered_summary.head(10).copy()

            top["transition"] = (
                top["previous_activity"]
                + " → "
                + top["activity"]
            )

            fig = px.bar(
                top.sort_values("mean_minutes"),
                x="mean_minutes",
                y="transition",
                orientation="h",
                title="Transitions with Highest Mean Elapsed Time",
                labels={
                    "mean_minutes": "Mean elapsed time (minutes)",
                    "transition": "Activity transition",
                },
                color_discrete_sequence=["#1CA58A"],
            )

            make_chart(fig)

    st.markdown(
        '<div class="section-heading">Event Timeline</div>',
        unsafe_allow_html=True,
    )

    timeline = (
        filtered.groupby("timestamp")
        .size()
        .reset_index(name="event_count")
        .sort_values("timestamp")
    )

    fig = px.line(
        timeline,
        x="timestamp",
        y="event_count",
        title="Events Recorded Over Time",
        labels={
            "timestamp": "Timestamp",
            "event_count": "Number of events",
        },
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
        filtered["activity"]
        .value_counts()
        .rename_axis("activity")
        .reset_index(name="event_count")
    )

    st.metric(
        "Activities observed",
        filtered["activity"].nunique(),
    )

    fig = px.bar(
        activity_counts.sort_values("event_count"),
        x="event_count",
        y="activity",
        orientation="h",
        title="Activity Frequency",
        labels={
            "event_count": "Number of events",
            "activity": "Activity",
        },
        color_discrete_sequence=["#3984C6"],
    )

    make_chart(fig, height=500)

    st.markdown("### Activity summary")

    st.dataframe(
        activity_counts,
        use_container_width=True,
        hide_index=True,
    )

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
        '<div class="section-heading">'
        'Elapsed-Time Analysis</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Elapsed intervals are calculated between consecutive "
        "recorded events within each encounter. They are not "
        "necessarily pure waiting times or proof of clinical delay."
    )

    if filtered_transitions.empty:
        st.info(
            "No consecutive event intervals are available "
            "for the selected records."
        )
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
                top["previous_activity"]
                + " → "
                + top["activity"]
            )

            fig = px.bar(
                top.sort_values("mean_minutes"),
                x="mean_minutes",
                y="transition",
                orientation="h",
                title="Mean Elapsed Time by Transition",
                labels={
                    "mean_minutes": "Mean elapsed time (minutes)",
                    "transition": "Activity transition",
                },
                color_discrete_sequence=["#1CA58A"],
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

        st.dataframe(
            display_summary,
            use_container_width=True,
            hide_index=True,
        )

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

    q1, q2, q3 = st.columns(3)

    q1.metric("Input rows", f"{quality['input_rows']:,}")
    q2.metric("Valid rows", f"{quality['valid_rows']:,}")
    q3.metric("Invalid rows removed", f"{quality['invalid_rows']:,}")

    st.markdown("### Validation checks")

    checks = pd.DataFrame(
        [
            {
                "Check": "Required columns present",
                "Result": "Passed",
                "Details": "case_id, activity, timestamp",
            },
            {
                "Check": "Missing or invalid required values",
                "Result": (
                    "Review required"
                    if quality["invalid_rows"] > 0
                    else "Passed"
                ),
                "Details": (
                    f"{quality['invalid_rows']} invalid rows removed"
                ),
            },
            {
                "Check": "Negative elapsed intervals",
                "Result": (
                    "Review required"
                    if negative_intervals > 0
                    else "Passed"
                ),
                "Details": str(negative_intervals),
            },
        ]
    )

    st.dataframe(
        checks,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Event data preview")

    st.dataframe(
        filtered.head(100),
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()

st.caption(
    "CareFlow Clinical Pathway Analytics • "
    "Metrics are calculated from the selected event data."
)
