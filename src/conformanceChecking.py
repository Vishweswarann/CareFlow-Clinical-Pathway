import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import pm4py
from google.cloud import bigquery
from google.oauth2 import service_account
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils
from pyvis.network import Network
from collections import Counter

st.set_page_config(page_title="CareFlow Executive Compliance", layout="wide")
st.title("CareFlow: Executive Clinical Compliance Dashboard")
st.markdown(
    "Monitor hospital standard operating procedure (SOP) adherence in real-time, "
    "identify where patient handoffs break down, and inspect high-frequency clinical deviations."
)


# ---------------------------------------------------------
# 1. Fetch Live Data from BigQuery (Using Streamlit Secrets)
# ---------------------------------------------------------
@st.cache_data
def fetch_live_bigquery_data():
    If running locally or via Streamlit Cloud secrets, handle credentials gracefully
    if "gcp_service_account" in st.secrets:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = bigquery.Client(
            credentials=credentials, project="careflow-analytics-98234"
        )
    else:
        # Fallback to local default GCP environment variables / gcloud CLI auth
        client = bigquery.Client(project="careflow-analytics-98234")

    query = """
        SELECT
            event_id, case_id, activity, timestamp, department,
            event_sequence, resource_role, resource_id, event_detail,
            arrival_mode, age_group, gender, chief_complaint, triage_level, disposition
        FROM `careflow-analytics-98234.careflow_analytics.event_logs`
        ORDER BY case_id, event_sequence
    """

    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


with st.spinner("Pulling live clinical event logs from BigQuery..."):
    try:
        df = fetch_live_bigquery_data()
    except Exception as e:
        st.error(f"Failed to connect to BigQuery: {e}")
        st.stop()

# Ensure chronological ordering per case
df = df.sort_values(by=["case_id", "event_sequence"])

formatted_df = pm4py.format_dataframe(
    df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
)
event_log = pm4py.convert_to_event_log(formatted_df)


# ---------------------------------------------------------
# 2. Build the Ideal Normative Model (Behind the Scenes)
# ---------------------------------------------------------
def build_normative_ed_model():
    net = PetriNet("Ideal_ED_Clinical_Pathway")

    p_start = PetriNet.Place("p_start")
    p_reg = PetriNet.Place("p_registered")
    p_triaged = PetriNet.Place("p_triaged")
    p_consulted = PetriNet.Place("p_consulted")
    p_end = PetriNet.Place("p_end")

    for p in [p_start, p_reg, p_triaged, p_consulted, p_end]:
        net.places.add(p)

    t_reg = PetriNet.Transition("t_reg", "Registration")
    t_triage = PetriNet.Transition("t_triage", "Triage")
    t_doc = PetriNet.Transition("t_doc", "Doctor Consultation")
    t_lab = PetriNet.Transition("t_lab", "Laboratory Testing")
    t_img = PetriNet.Transition("t_img", "Imaging")
    t_treat = PetriNet.Transition("t_treat", "Treatment")
    t_reassess = PetriNet.Transition("t_reassess", "Reassessment")
    t_disch = PetriNet.Transition("t_disch", "Discharge")
    t_admit = PetriNet.Transition("t_admit", "Hospital Admission")

    for t in [
        t_reg,
        t_triage,
        t_doc,
        t_lab,
        t_img,
        t_treat,
        t_reassess,
        t_disch,
        t_admit,
    ]:
        net.transitions.add(t)

    petri_utils.add_arc_from_to(p_start, t_reg, net)
    petri_utils.add_arc_from_to(t_reg, p_reg, net)
    petri_utils.add_arc_from_to(p_reg, t_triage, net)
    petri_utils.add_arc_from_to(t_triage, p_triaged, net)
    petri_utils.add_arc_from_to(p_triaged, t_doc, net)
    petri_utils.add_arc_from_to(t_doc, p_consulted, net)

    for workup in [t_lab, t_img, t_treat, t_reassess]:
        petri_utils.add_arc_from_to(p_consulted, workup, net)
        petri_utils.add_arc_from_to(workup, p_consulted, net)

    petri_utils.add_arc_from_to(p_consulted, t_disch, net)
    petri_utils.add_arc_from_to(t_disch, p_end, net)
    petri_utils.add_arc_from_to(p_consulted, t_admit, net)
    petri_utils.add_arc_from_to(t_admit, p_end, net)

    return net, Marking({p_start: 1}), Marking({p_end: 1})


net, im, fm = build_normative_ed_model()

with st.spinner(
    "Running A* alignment conformance diagnostics across BigQuery traces..."
):
    aligned_traces = pm4py.conformance_diagnostics_alignments(event_log, net, im, fm)


# ---------------------------------------------------------
# 3. Sidebar Controls for Administrator View
# ---------------------------------------------------------
st.sidebar.header("Administrator View Controls")
deviation_scope = st.sidebar.radio(
    "Define 'Non-Compliant' Scope:",
    options=[
        "All Deviations (Rework + Unfinished/Skipped Steps)",
        "Strictly Active Violations (Wrong Order / Rework Only)",
    ],
    index=0,
    help="In live hospital feeds, unfinished cases may still be in beds. Toggle to isolate active clinical rework.",
)


# ---------------------------------------------------------
# 4. Extract Break-Off Activities & Red Non-Compliant Paths
# ---------------------------------------------------------
case_records = []
breakoff_records = []
red_edges_counter = Counter()
red_edge_reasons = {}
compliant_edge_counter = Counter()

for trace, align in zip(event_log, aligned_traces):
    case_id = trace.attributes["concept:name"]
    log_idx = 0
    last_actual_activity = "Arrival"

    has_rework = False
    has_skipped = False
    issue_descriptions = []

    for log_move, model_move in align["alignment"]:
        if log_move == ">>" and model_move is None:
            continue

        # 1. Compliant Step (Synchronous Move)
        if log_move == model_move:
            if last_actual_activity != "Arrival":
                compliant_edge_counter[(last_actual_activity, log_move)] += 1
            last_actual_activity = log_move
            log_idx += 1

        # 2. Active Violation / Rework (Log-Only Move)
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
                f"After '{last_actual_activity}' → extra '{log_move}' ({detail})"
            )
            last_actual_activity = log_move
            log_idx += 1

        # 3. Skipped Mandatory Step / Unfinished Journey (Model-Only Move)
        elif log_move == ">>":
            has_skipped = True
            if deviation_scope.startswith("All Deviations"):
                target_label = f"⚠️ Missing: {model_move}"
                edge_key = (last_actual_activity, target_label)
                red_edges_counter[edge_key] += 1
                red_edge_reasons.setdefault(edge_key, []).append(
                    f"{case_id}: Stopped after {last_actual_activity} (Missing {model_move})"
                )

                breakoff_records.append(
                    {
                        "Case ID": case_id,
                        "Trigger Activity (After This Step)": last_actual_activity,
                        "Non-Compliant Action": f"Skipped: {model_move}",
                        "Deviation Type": "Missing Mandatory Step / Drop-off",
                        "Department": "Unrecorded / Left Early",
                        "Clinical Reason": f"Journey stopped after '{last_actual_activity}' without '{model_move}'",
                    }
                )
                issue_descriptions.append(
                    f"After '{last_actual_activity}' → missed '{model_move}'"
                )

    if deviation_scope.startswith("Strictly Active"):
        is_compliant = not has_rework
    else:
        is_compliant = (not has_rework) and (not has_skipped)

    case_records.append(
        {
            "Case ID": case_id,
            "Compliance Status": "✅ Compliant" if is_compliant else "🔴 Non-Compliant",
            "Chief Complaint": trace[0]["chief_complaint"],
            "Triage Level": f"Level {trace[0]['triage_level']}",
            "What Went Wrong": "Followed standard protocol"
            if is_compliant
            else " | ".join(issue_descriptions),
        }
    )

cases_df = pd.DataFrame(case_records)
breakoff_df = pd.DataFrame(breakoff_records)


# ---------------------------------------------------------
# 5. Render Top-Level Administrator KPI Cards
# ---------------------------------------------------------
total_journeys = len(cases_df)
compliant_count = sum(cases_df["Compliance Status"] == "✅ Compliant")
non_compliant_count = total_journeys - compliant_count
compliant_pct = (compliant_count / total_journeys * 100) if total_journeys else 0
non_compliant_pct = (
    (non_compliant_count / total_journeys * 100) if total_journeys else 0
)

if not breakoff_df.empty:
    top_trigger = (
        breakoff_df["Trigger Activity (After This Step)"].value_counts().idxmax()
    )
    top_trigger_count = (
        breakoff_df["Trigger Activity (After This Step)"].value_counts().max()
    )
    trigger_text = f"{top_trigger} ({top_trigger_count} cases)"
else:
    trigger_text = "None"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Patient Journeys", total_journeys)
k2.metric("Compliant Journeys", f"{compliant_count} ({compliant_pct:.1f}%)")
k3.metric("Non-Compliant Journeys", f"{non_compliant_count} ({non_compliant_pct:.1f}%)")
k4.metric("Top Break-Off Point (After Activity)", trigger_text)

st.divider()


# ---------------------------------------------------------
# 6. Unified Workflow Map: Ideal Protocol + Red Deviations
# ---------------------------------------------------------
st.subheader("Ideal Clinical Workflow vs. Non-Compliant Deviations")
st.markdown(
    "**How to read this map:** **Blue Boxes & Slate Arrows** represent the hospital's "
    "**Ideal Standard Protocol**. **Bold Red Arrows** show where patient journeys broke protocol "
    "(rework loops or missing steps), scaled dynamically by case volume."
)


def generate_admin_conformance_map(compliant_edges, red_edges, red_reasons):
    net_vis = Network(
        height="620px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#0f172a",
    )

    net_vis.set_options("""
    {
      "physics": {
        "enabled": false
      },
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "nodeSpacing": 140,
          "levelSeparation": 200
        }
      },
      "edges": {
        "smooth": {
          "type": "cubicBezier",
          "forceDirection": "horizontal",
          "roundness": 0.45
        }
      },
      "interaction": {
        "navigationButtons": true,
        "zoomView": true,
        "dragView": true,
        "hover": true
      }
    }
    """)

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
    for node_id, lvl, bg_color, border_color in ideal_nodes:
        net_vis.add_node(
            node_id,
            label=node_id,
            level=lvl,
            shape="box",
            color={"background": bg_color, "border": border_color},
            font={"size": 16, "color": "#0f172a", "face": "Arial", "bold": True},
            margin=14,
            borderWidth=2,
            shadow={
                "enabled": True,
                "color": "rgba(0,0,0,0.12)",
                "size": 5,
                "x": 2,
                "y": 2,
            },
        )
        added_nodes.add(node_id)

    ideal_protocol_edges = [
        ("Registration", "Triage"),
        ("Triage", "Doctor Consultation"),
        ("Doctor Consultation", "Laboratory Testing"),
        ("Doctor Consultation", "Imaging"),
        ("Doctor Consultation", "Treatment"),
        ("Imaging", "Reassessment"),
        ("Laboratory Testing", "Treatment"),
        ("Reassessment", "Discharge"),
        ("Treatment", "Hospital Admission"),
        ("Treatment", "Discharge"),
    ]

    for src, dst in ideal_protocol_edges:
        vol = compliant_edges.get((src, dst), 0)
        edge_label = f"{vol} Compliant" if vol > 0 else "Ideal SOP"
        net_vis.add_edge(
            src,
            dst,
            value=max(vol, 1),
            label=edge_label,
            title=f"Ideal Protocol Path: {src} → {dst} ({vol} compliant transitions)",
            color={"color": "#64748b", "highlight": "#0f172a"},
            arrows="to",
            font={
                "size": 11,
                "color": "#475569",
                "align": "top",
                "strokeWidth": 2,
                "strokeColor": "#ffffff",
            },
        )

    for (src, dst), count in red_edges.items():
        if dst not in added_nodes:
            net_vis.add_node(
                dst,
                label=dst,
                level=6,
                shape="box",
                color={"background": "#fef2f2", "border": "#dc2626"},
                font={"size": 15, "color": "#991b1b", "face": "Arial", "bold": True},
                margin=12,
                borderWidth=2,
            )
            added_nodes.add(dst)

        reasons_tooltip = "\n".join(red_reasons.get((src, dst), []))
        net_vis.add_edge(
            src,
            dst,
            value=count * 3,
            label=f"🚨 {count} Non-Compliant",
            title=f"NON-COMPLIANT PATH ({count} cases)\nAfter '{src}' → '{dst}'\nDetails:\n{reasons_tooltip}",
            color={"color": "#ef4444", "highlight": "#b91c1c"},
            arrows="to",
            dashes=True,
            font={
                "size": 13,
                "color": "#dc2626",
                "align": "bottom",
                "strokeWidth": 3,
                "strokeColor": "#ffffff",
            },
        )

    map_path = "careflow_admin_conformance_map.html"
    net_vis.save_graph(map_path)
    return map_path


map_file = generate_admin_conformance_map(
    compliant_edge_counter, red_edges_counter, red_edge_reasons
)
with open(map_file, "r", encoding="utf-8") as f:
    components.html(f.read(), height=640)

st.divider()


# ---------------------------------------------------------
# 7. Break-Off Analytics & Summary Tables
# ---------------------------------------------------------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("After Which Activity Did Patients Become Non-Compliant?")
    if not breakoff_df.empty:
        trigger_counts = (
            breakoff_df.groupby(
                ["Trigger Activity (After This Step)", "Deviation Type"]
            )
            .size()
            .reset_index(name="Patient Count")
            .sort_values("Patient Count", ascending=True)
        )
        fig_break = px.bar(
            trigger_counts,
            x="Patient Count",
            y="Trigger Activity (After This Step)",
            color="Deviation Type",
            orientation="h",
            color_discrete_map={
                "Active Rework / Out-of-Order": "#ef4444",
                "Missing Mandatory Step / Drop-off": "#f97316",
            },
            title="Activities Immediately Preceding a Protocol Deviation",
            text_auto=True,
        )
        fig_break.update_layout(plot_bgcolor="white", height=380)
        st.plotly_chart(fig_break, use_container_width=True)
    else:
        st.success("All patient journeys followed the ideal clinical pathway!")

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
    else:
        st.info("No deviation records found for the selected scope.")

st.subheader("Patient Journey Compliance Summary")
st.dataframe(cases_df, use_container_width=True, hide_index=True)
