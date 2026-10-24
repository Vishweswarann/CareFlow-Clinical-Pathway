import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils
from pm4py.algo.filtering.dfg import dfg_filtering
from pm4py.visualization.dfg import visualizer as dfg_visualizer
from pm4py.visualization.petri_net import visualizer as pn_visualizer
from pm4py.visualization.heuristics_net import visualizer as hn_visualizer
from pyvis.network import Network
from collections import Counter
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title="CareFlow Analytics", layout="wide")


# ==========================================
# 1. Centralized Data Loader
# ==========================================
@st.cache_data
def fetch_global_data():
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
            event_id, case_id, activity, timestamp, department, 
            event_sequence, resource_role, resource_id, event_detail, 
            arrival_mode, age_group, gender, chief_complaint, triage_level, disposition
        FROM `careflow-analytics-98234.careflow_analytics.event_logs`
        ORDER BY case_id, event_sequence
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=False)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Calculate emergency flags dynamically
    emergency_conditions = (df["arrival_mode"] == "Ambulance") | (
        df["triage_level"].isin([1, 2])
    )
    df["is_emergency"] = emergency_conditions

    return df


with st.spinner("Initializing CareFlow Platform... Fetching Live Data..."):
    try:
        global_df = fetch_global_data()
    except Exception as e:
        st.error(f"Database Connection Failed: {e}")
        st.stop()

# ==========================================
# 2. Sidebar Navigation
# ==========================================
st.sidebar.title("CareFlow Analytics")
page = st.sidebar.radio(
    "Select Module:",
    [
        "Executive Compliance",
        "Process Discovery (Standard Models)",
        "Interactive Fuzzy Miner & Timelines",
        "Clinician Operations Audit",
    ],
)
st.sidebar.divider()

# ==========================================
# MODULE 1: Executive Compliance
# ==========================================
if page == "Executive Compliance":
    st.title("CareFlow: Executive Clinical Compliance Dashboard")
    st.markdown(
        "Monitor hospital standard operating procedure (SOP) adherence in real-time."
    )

    deviation_scope = st.sidebar.radio(
        "Define 'Non-Compliant' Scope:",
        [
            "All Deviations (Rework + Skipped Steps)",
            "Strictly Active Violations (Rework Only)",
        ],
    )

    formatted_df = pm4py.format_dataframe(
        global_df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )
    event_log = pm4py.convert_to_event_log(formatted_df)

    # Build Normative Model
    net = PetriNet("Ideal_ED_Clinical_Pathway")
    p_start, p_reg, p_triaged, p_consulted, p_end = [
        PetriNet.Place(name)
        for name in ["p_start", "p_registered", "p_triaged", "p_consulted", "p_end"]
    ]
    for p in [p_start, p_reg, p_triaged, p_consulted, p_end]:
        net.places.add(p)

    transitions = {
        name: PetriNet.Transition(name, label)
        for name, label in [
            ("t_reg", "Registration"),
            ("t_triage", "Triage"),
            ("t_doc", "Doctor Consultation"),
            ("t_lab", "Laboratory Testing"),
            ("t_img", "Imaging"),
            ("t_treat", "Treatment"),
            ("t_reassess", "Reassessment"),
            ("t_disch", "Discharge"),
            ("t_admit", "Hospital Admission"),
        ]
    }
    for t in transitions.values():
        net.transitions.add(t)

    petri_utils.add_arc_from_to(p_start, transitions["t_reg"], net)
    petri_utils.add_arc_from_to(transitions["t_reg"], p_reg, net)
    petri_utils.add_arc_from_to(p_reg, transitions["t_triage"], net)
    petri_utils.add_arc_from_to(transitions["t_triage"], p_triaged, net)
    petri_utils.add_arc_from_to(p_triaged, transitions["t_doc"], net)
    petri_utils.add_arc_from_to(transitions["t_doc"], p_consulted, net)

    for workup in ["t_lab", "t_img", "t_treat", "t_reassess"]:
        petri_utils.add_arc_from_to(p_consulted, transitions[workup], net)
        petri_utils.add_arc_from_to(transitions[workup], p_consulted, net)

    petri_utils.add_arc_from_to(p_consulted, transitions["t_disch"], net)
    petri_utils.add_arc_from_to(transitions["t_disch"], p_end, net)
    petri_utils.add_arc_from_to(p_consulted, transitions["t_admit"], net)
    petri_utils.add_arc_from_to(transitions["t_admit"], p_end, net)

    im, fm = Marking({p_start: 1}), Marking({p_end: 1})
    aligned_traces = pm4py.conformance_diagnostics_alignments(event_log, net, im, fm)

    case_records, breakoff_records = [], []
    red_edges_counter, compliant_edge_counter = Counter(), Counter()
    red_edge_reasons = {}

    for trace, align in zip(event_log, aligned_traces):
        case_id = trace.attributes["concept:name"]
        log_idx, last_actual_activity = 0, "Arrival"
        has_rework, has_skipped = False, False
        issue_descriptions = []

        for log_move, model_move in align["alignment"]:
            if log_move == ">>" and model_move is None:
                continue

            if log_move == model_move:
                if last_actual_activity != "Arrival":
                    compliant_edge_counter[(last_actual_activity, log_move)] += 1
                last_actual_activity = log_move
                log_idx += 1
            elif model_move == ">>":
                has_rework = True
                ev = trace[log_idx]
                detail = ev["event_detail"]
                edge_key = (last_actual_activity, log_move)
                red_edges_counter[edge_key] += 1
                red_edge_reasons.setdefault(edge_key, []).append(f"{case_id}: {detail}")

                breakoff_records.append(
                    {
                        "Case ID": case_id,
                        "Trigger Activity (After This Step)": last_actual_activity,
                        "Non-Compliant Action": f"Rework: {log_move}",
                        "Deviation Type": "Active Rework / Out-of-Order",
                        "Department": ev["department"],
                        "Clinical Reason": detail,
                    }
                )
                issue_descriptions.append(
                    f"After '{last_actual_activity}' → extra '{log_move}'"
                )
                last_actual_activity = log_move
                log_idx += 1
            elif log_move == ">>":
                has_skipped = True
                if deviation_scope.startswith("All"):
                    target = f"⚠️ Missing: {model_move}"
                    edge_key = (last_actual_activity, target)
                    red_edges_counter[edge_key] += 1
                    red_edge_reasons.setdefault(edge_key, []).append(
                        f"{case_id}: Stopped after {last_actual_activity}"
                    )

                    breakoff_records.append(
                        {
                            "Case ID": case_id,
                            "Trigger Activity (After This Step)": last_actual_activity,
                            "Non-Compliant Action": f"Skipped: {model_move}",
                            "Deviation Type": "Missing Mandatory Step / Drop-off",
                            "Department": "Unrecorded",
                            "Clinical Reason": f"Stopped without '{model_move}'",
                        }
                    )
                    issue_descriptions.append(f"Missed '{model_move}'")

        is_compliant = (
            (not has_rework)
            if deviation_scope.startswith("Strictly")
            else (not has_rework and not has_skipped)
        )
        case_records.append(
            {
                "Case ID": case_id,
                "Compliance Status": "✅ Compliant"
                if is_compliant
                else "🔴 Non-Compliant",
                "What Went Wrong": "Followed standard protocol"
                if is_compliant
                else " | ".join(issue_descriptions),
            }
        )

    cases_df = pd.DataFrame(case_records)
    breakoff_df = pd.DataFrame(breakoff_records)

    total_journeys = len(cases_df)
    compliant_count = sum(cases_df["Compliance Status"] == "✅ Compliant")
    non_compliant_count = total_journeys - compliant_count

    if not breakoff_df.empty:
        top_trigger = (
            breakoff_df["Trigger Activity (After This Step)"].value_counts().idxmax()
        )
        trigger_text = f"{top_trigger} ({breakoff_df['Trigger Activity (After This Step)'].value_counts().max()} cases)"
    else:
        trigger_text = "None"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Patient Journeys", total_journeys)
    k2.metric(
        "Compliant Journeys",
        f"{compliant_count} ({(compliant_count / total_journeys * 100) if total_journeys else 0:.1f}%)",
    )
    k3.metric(
        "Non-Compliant Journeys",
        f"{non_compliant_count} ({(non_compliant_count / total_journeys * 100) if total_journeys else 0:.1f}%)",
    )
    k4.metric("Top Break-Off Point", trigger_text)
    st.divider()

    st.subheader("Ideal Clinical Workflow vs. Non-Compliant Deviations")
    net_vis = Network(
        height="620px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#0f172a",
    )
    net_vis.set_options(
        '{"physics": {"enabled": false}, "layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed", "nodeSpacing": 140, "levelSeparation": 200}}, "edges": {"smooth": {"type": "cubicBezier", "forceDirection": "horizontal", "roundness": 0.45}}}'
    )

    ideal_nodes = [
        ("Registration", 1, "#e0f2fe", "#0284c7"),
        ("Triage", 2, "#e0f2fe", "#0284c7"),
        ("Doctor Consultation", 3, "#e0f2fe", "#0284c7"),
        ("Laboratory Testing", 4, "#f0fdf4", "#16a34a"),
        ("Imaging", 4, "#f0fdf4", "#16a34a"),
        ("Treatment", 4, "#f0fdf4", "#16a34a"),
        ("Reassessment", 5, "#f0fdf4", "#16a34a"),
        ("Discharge", 6, "#dcfce7", "#15803d"),
        ("Hospital Admission", 6, "#dcfce7", "#15803d"),
    ]
    added_nodes = set()

    for node_id, lvl, bg, border in ideal_nodes:
        net_vis.add_node(
            node_id,
            label=node_id,
            level=lvl,
            shape="box",
            color={"background": bg, "border": border},
            font={"size": 16, "bold": True},
            margin=14,
            borderWidth=2,
        )
        added_nodes.add(node_id)

    for (src, dst), count in red_edges_counter.items():
        if dst not in added_nodes:
            net_vis.add_node(
                dst,
                label=dst,
                level=6,
                shape="box",
                color={"background": "#fef2f2", "border": "#dc2626"},
                font={"size": 15, "color": "#991b1b", "bold": True},
                margin=12,
            )
            added_nodes.add(dst)
        tooltip = "\n".join(red_edge_reasons.get((src, dst), []))
        net_vis.add_edge(
            src,
            dst,
            value=count * 3,
            label=f"🚨 {count}",
            title=tooltip,
            color={"color": "#ef4444"},
            dashes=True,
        )

    for (src, dst), count in compliant_edge_counter.items():
        net_vis.add_edge(
            src, dst, value=max(count, 1), label=f"{count} Compliant", color="#64748b"
        )

    net_vis.save_graph("admin_map.html")
    with open("admin_map.html", "r") as f:
        components.html(f.read(), height=640)

    st.divider()
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.subheader("Activities Preceding Non-Compliance")
        if not breakoff_df.empty:
            trigger_counts = (
                breakoff_df.groupby(
                    ["Trigger Activity (After This Step)", "Deviation Type"]
                )
                .size()
                .reset_index(name="Count")
            )
            fig_break = px.bar(
                trigger_counts,
                x="Count",
                y="Trigger Activity (After This Step)",
                color="Deviation Type",
                orientation="h",
                color_discrete_map={
                    "Active Rework / Out-of-Order": "#ef4444",
                    "Missing Mandatory Step / Drop-off": "#f97316",
                },
            )
            st.plotly_chart(fig_break, use_container_width=True)
        else:
            st.success("All patient journeys followed the ideal pathway!")
    with col_right:
        st.subheader("Departmental Root-Cause Breakdown")
        if not breakoff_df.empty:
            st.dataframe(
                breakoff_df[
                    [
                        "Case ID",
                        "Trigger Activity (After This Step)",
                        "Non-Compliant Action",
                        "Clinical Reason",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                height=380,
            )

    st.subheader("Patient Journey Compliance Summary")
    st.dataframe(cases_df, use_container_width=True, hide_index=True)

# ==========================================
# MODULE 2: Process Discovery (Standard Models)
# ==========================================
elif page == "Process Discovery (Standard Models)":
    st.title("CareFlow Process Map Explorer")

    event_log = pm4py.format_dataframe(
        global_df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )

    st.sidebar.header("Process Mining Controls")
    model_type = st.sidebar.radio(
        "Select Model Type",
        ["Heuristics Net", "Directly-Follows Graph (DFG)", "Petri Net"],
    )
    st.subheader(f"Live Process Map: {model_type}")

    if model_type == "Heuristics Net":
        thresh = st.sidebar.slider("Dependency Threshold", 0.0, 1.0, 0.5, 0.05)
        heu_net = pm4py.discover_heuristics_net(event_log, dependency_threshold=thresh)
        st.graphviz_chart(hn_visualizer.apply(heu_net))
    elif model_type == "Directly-Follows Graph (DFG)":
        dfg, sa, ea = pm4py.discover_dfg(event_log)
        st.graphviz_chart(
            dfg_visualizer.apply(
                dfg, log=event_log, variant=dfg_visualizer.Variants.FREQUENCY
            )
        )
    elif model_type == "Petri Net":
        net, im, fm = pm4py.discover_petri_net_inductive(event_log)
        st.graphviz_chart(pn_visualizer.apply(net, im, fm))

# ==========================================
# MODULE 3: Interactive Fuzzy Miner & Timelines
# ==========================================
elif page == "Interactive Fuzzy Miner & Timelines":
    st.title("Interactive Process Abstraction")
    st.markdown(
        "Adjust sliders to simulate a Fuzzy Miner, filtering out low-frequency clinical noise."
    )

    node_ret = st.sidebar.slider("Node Frequency Threshold", 0.0, 1.0, 0.80, 0.05)
    edge_ret = st.sidebar.slider("Path Frequency Threshold", 0.0, 1.0, 0.70, 0.05)

    event_log = pm4py.format_dataframe(
        global_df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )
    dfg, starts, ends = pm4py.discover_dfg(event_log)
    counts = dict(event_log["concept:name"].value_counts())

    f_dfg, f_starts, f_ends, f_acts = dfg_filtering.filter_dfg_on_activities_percentage(
        dfg, starts, ends, counts, node_ret
    )
    f_dfg, _, _, _ = dfg_filtering.filter_dfg_on_paths_percentage(
        f_dfg, f_starts, f_ends, f_acts, edge_ret
    )

    net = Network(height="650px", width="100%", directed=True, bgcolor="#ffffff")
    net.set_options(
        '{"physics": {"enabled": false}, "layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed", "nodeSpacing": 150, "levelSeparation": 180}}, "edges": {"smooth": {"type": "cubicBezier", "roundness": 0.4}}}'
    )

    added = set()
    for (src, tgt), w in f_dfg.items():
        for node in [src, tgt]:
            if node not in added:
                net.add_node(
                    node,
                    label=node,
                    shape="box",
                    color={"background": "#bae6fd", "border": "#38bdf8"},
                    font={"size": 18, "bold": True},
                    margin=15,
                    borderWidth=2,
                )
                added.add(node)
        net.add_edge(src, tgt, value=w, label=str(w), color={"color": "#94a3b8"})

    net.save_graph("fuzzy_map.html")
    with open("fuzzy_map.html", "r") as f:
        components.html(f.read(), height=670)

    st.divider()
    st.subheader("Patient Timeline & Bottleneck Analysis")

    all_activities = global_df["activity"].unique()
    selected_acts = st.multiselect(
        "Filter Clinical Activities:", all_activities, default=all_activities
    )
    filtered_df = global_df[global_df["activity"].isin(selected_acts)].copy()

    case_starts = (
        filtered_df.groupby("case_id")["timestamp"]
        .min()
        .reset_index()
        .rename(columns={"timestamp": "arrival_time"})
    )
    merged_df = pd.merge(filtered_df, case_starts, on="case_id").sort_values(
        by=["arrival_time", "timestamp"]
    )

    fig = px.scatter(
        merged_df,
        x="timestamp",
        y="case_id",
        color="activity",
        title="CareFlow Event Timeline",
    )
    fig.update_layout(
        yaxis=dict(
            type="category",
            categoryorder="trace",
            showticklabels=False,
            title="Patients (Sorted by Arrival Time)",
        ),
        plot_bgcolor="white",
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MODULE 4: Clinician Operations Audit
# ==========================================
elif page == "Clinician Operations Audit":
    st.title("🩺 Clinician & Departmental Flow Audit")

    df = global_df.copy()
    df["next_ts"] = df.groupby("case_id")["timestamp"].shift(-1)
    df["duration"] = (df["next_ts"] - df["timestamp"]).dt.total_seconds() / 60.0
    valid_trans = df[(df["duration"] > 0) & (df["duration"] < 1440)]

    st.sidebar.subheader("Patient Acuity Filter")
    flow_type = st.sidebar.radio(
        "Select Workflow Type:",
        ["Routine / Walk-in", "High-Acuity / Emergency", "All Cases"],
    )
    if flow_type == "High-Acuity / Emergency":
        df = df[df["is_emergency"] == True]
    elif flow_type == "Routine / Walk-in":
        df = df[df["is_emergency"] == False]

    staff = st.sidebar.selectbox(
        "Filter Staff ID:", ["All"] + list(df["resource_id"].dropna().unique())
    )
    staff_df = df if staff == "All" else df[df["resource_id"] == staff]

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Active Patient Load",
        df[df["disposition"].isna() | (df["disposition"] == "Admitted")][
            "case_id"
        ].nunique(),
    )
    avg_triage = valid_trans[valid_trans["activity"] == "Triage"]["duration"].mean()
    c2.metric(
        "Avg Triage Wait", f"{avg_triage:.1f} mins" if pd.notnull(avg_triage) else "N/A"
    )
    c3.metric(
        "Charting Reworks",
        df[
            df["event_detail"].str.contains(
                "incomplete|re-triage", case=False, na=False
            )
        ].shape[0],
    )
    st.divider()

    cl, cr = st.columns(2)
    with cl:
        st.subheader("Patient Volume by Role")
        fig1 = px.bar(
            df.groupby(["resource_role", "department"])
            .size()
            .reset_index(name="Count"),
            x="Count",
            y="resource_role",
            color="department",
            orientation="h",
        )
        st.plotly_chart(fig1, use_container_width=True)
    with cr:
        st.subheader("Department Bottleneck (Wait Times)")
        fig2 = px.bar(
            valid_trans.groupby("department")["duration"].mean().reset_index(),
            x="duration",
            y="department",
            orientation="h",
            color="duration",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Staff Task-Transition Map")
    staff_filtered = df[df["resource_id"].notna()] if staff == "All" else staff_df
    s_log = pm4py.format_dataframe(
        staff_filtered,
        case_id="resource_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    s_dfg, _, _ = pm4py.discover_dfg(s_log)

    net2 = Network(height="550px", width="100%", directed=True)
    net2.set_options(
        '{"physics": {"enabled": true, "barnesHut": {"gravitationalConstant": -3000}}, "layout": {"hierarchical": {"enabled": false}}}'
    )
    added = set()
    for (src, tgt), w in s_dfg.items():
        for node in [src, tgt]:
            if node not in added:
                net2.add_node(
                    node,
                    label=node,
                    shape="box",
                    color={"background": "#fed7aa", "border": "#fb923c"},
                    font={"bold": True},
                    margin=12,
                )
                added.add(node)
        net2.add_edge(src, tgt, value=w, label=str(w))

    net2.save_graph("staff_map.html")
    with open("staff_map.html", "r") as f:
        components.html(f.read(), height=570)

    st.subheader("Clinician Workload & Task Metrics")
    # Using the corrected grouping logic (excluding department) for accurate Departments_Visited count
    summary_table = (
        staff_filtered.groupby(["resource_id", "resource_role"], as_index=False)
        .agg(
            Total_Actions=("event_id", "count"),
            Unique_Patients_Handled=("case_id", "nunique"),
            Departments_Visited=("department", "nunique"),
        )
        .sort_values("Total_Actions", ascending=False)
    )
    st.dataframe(summary_table, use_container_width=True, hide_index=True)

    st.subheader("🚨 Live Friction Feed: Bounced & Delayed Patients")
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
        st.success("No active clinical handoff frictions logged.")
