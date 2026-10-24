import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pm4py
from google.cloud import bigquery
from pyvis.network import Network
from pm4py.algo.filtering.dfg import dfg_filtering
import plotly.express as px

st.set_page_config(page_title="CareFlow Process Map", layout="wide")
st.title("CareFlow: Interactive Process Abstraction")


# 1. Fetch and Cache Data from BigQuery
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


with st.spinner("Pulling live data from BigQuery..."):
    df = fetch_cloud_data()

event_log = pm4py.format_dataframe(
    df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
)

# 2. Fuzzy Abstraction Controls (Sidebar)
st.sidebar.header("Zoom & Abstraction Controls")
st.sidebar.markdown(
    "Adjust these sliders to simulate a Fuzzy Miner. "
    "Lowering the retention hides low-frequency clinical anomalies."
)

# Sliders represent the percentage of common activities/paths to keep (0.0 to 1.0)
node_retention = st.sidebar.slider("Node Frequency Threshold", 0.0, 1.0, 0.80, 0.05)
edge_retention = st.sidebar.slider("Path Frequency Threshold", 0.0, 1.0, 0.70, 0.05)

# 3. Process Discovery & Mathematical Filtering
dfg, start_activities, end_activities = pm4py.discover_dfg(event_log)
activities_count = dict(event_log["concept:name"].value_counts())

# Filter Nodes (Activities)
filtered_dfg, filtered_starts, filtered_ends, filtered_activities = (
    dfg_filtering.filter_dfg_on_activities_percentage(
        dfg, start_activities, end_activities, activities_count, node_retention
    )
)

# Filter Edges (Paths)
filtered_dfg, filtered_starts, filtered_ends, filtered_activities = (
    dfg_filtering.filter_dfg_on_paths_percentage(
        filtered_dfg,
        filtered_starts,
        filtered_ends,
        filtered_activities,
        edge_retention,
    )
)


# 4. Build the Interactive, Zoomable PyVis Network with Enhanced UI
def generate_zoomable_graph(dfg_dict):
    net = Network(
        height="650px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",  # Set canvas to clean white
        font_color="#0f172a",
    )

    # UI Options: Strict JSON formatting for vis.js configuration.
    # Note: Disabled physics & custom horizontal compression to keep nodes tightly grouped.
    net.set_options("""
    {
      "physics": {
        "enabled": false
      },
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "nodeSpacing": 150,
          "levelSeparation": 180
        }
      },
      "edges": {
        "smooth": {
          "type": "cubicBezier",
          "forceDirection": "horizontal",
          "roundness": 0.4
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
        # Large, high-visibility styled nodes
        if source not in nodes_added:
            net.add_node(
                source,
                label=source,
                shape="box",
                color={
                    "background": "#bae6fd",
                    "border": "#38bdf8",
                    "highlight": {"background": "#7dd3fc", "border": "#0284c7"},
                },
                font={"size": 18, "color": "#0f172a", "face": "Arial", "bold": True},
                margin=15,  # Expands padding to size up the boxes
                borderWidth=2,
                shadow={
                    "enabled": True,
                    "color": "rgba(0,0,0,0.15)",
                    "size": 6,
                    "x": 2,
                    "y": 3,
                },
            )
            nodes_added.add(source)

        if target not in nodes_added:
            net.add_node(
                target,
                label=target,
                shape="box",
                color={
                    "background": "#bae6fd",
                    "border": "#38bdf8",
                    "highlight": {"background": "#7dd3fc", "border": "#0284c7"},
                },
                font={"size": 18, "color": "#0f172a", "face": "Arial", "bold": True},
                margin=15,
                borderWidth=2,
                shadow={
                    "enabled": True,
                    "color": "rgba(0,0,0,0.15)",
                    "size": 6,
                    "x": 2,
                    "y": 3,
                },
            )
            nodes_added.add(target)

        # Edges now display weights natively and scale based on frequency
        net.add_edge(
            source,
            target,
            value=weight,
            label=str(weight),  # Direct label visualization
            title=f"Patient Volume: {weight}",
            color={"color": "#94a3b8", "highlight": "#475569"},
            arrows="to",
            font={
                "size": 12,
                "color": "#475569",
                "align": "top",
                "strokeWidth": 2,
                "strokeColor": "#ffffff",
            },
        )

    # Save and output
    html_path = "careflow_zoomable_map.html"
    net.save_graph(html_path)
    return html_path


# 5. Render to the Streamlit Dashboard
st.subheader("Live Clinical Pathway")
st.markdown(
    "Interact with the canvas: **Scroll to zoom**, **click and drag nodes** to reorganize the flow, and **hover over arrows** for patient volume data."
)

html_file = generate_zoomable_graph(filtered_dfg)

# Embed the interactive HTML canvas
with open(html_file, "r", encoding="utf-8") as f:
    html_content = f.read()

components.html(html_content, height=670)

st.divider()
st.subheader("Patient Timeline & Bottleneck Analysis")

# 1. UI Control: Let the user declutter the chart by hiding minor tasks
all_activities = df["activity"].unique()
selected_activities = st.multiselect(
    "Filter Clinical Activities (Remove noise to spot bottlenecks):",
    all_activities,
    default=all_activities,
)

# Apply the filter
filtered_df = df[df["activity"].isin(selected_activities)].copy()

# 2. The Magic Fix: Sort the Y-axis by when the patient first arrived!
# This transforms the chaotic static into a clean, readable "waterfall" diagonal.
case_starts = filtered_df.groupby("case_id")["timestamp"].min().reset_index()
case_starts.rename(columns={"timestamp": "arrival_time"}, inplace=True)

# Merge the arrival times back in and sort
merged_df = pd.merge(filtered_df, case_starts, on="case_id")
merged_df = merged_df.sort_values(by=["arrival_time", "timestamp"])

# 3. Render the Plot
fig = px.scatter(
    merged_df,
    x="timestamp",
    y="case_id",
    color="activity",
    title="CareFlow Event Timeline",
    hover_data=["activity", "timestamp"],
)

fig.update_layout(
    yaxis=dict(
        type="category",
        categoryorder="trace",  # Forces Plotly to respect our arrival_time sorting
        showticklabels=False,  # Hide the cluttered Case IDs on the left
        title="Patients (Sorted by Arrival Time)",
    ),
    xaxis=dict(title="Time of Clinical Event"),
    plot_bgcolor="white",
    height=600,
)

fig.update_traces(
    marker=dict(size=8, opacity=0.7, line=dict(width=1, color="DarkSlateGrey"))
)

st.plotly_chart(fig, use_container_width=True)
