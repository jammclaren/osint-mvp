import streamlit as st
import requests
import os
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="OSINT Situational Awareness Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛡️ Regional Situational Awareness & OSINT Dashboard")
st.markdown("---")

# Sidebar Filters
st.sidebar.header("Operational Parameters")
selected_jtf = st.sidebar.selectbox("Joint Task Force", ["All", "JTF ZAMPELAN", "JTF ORION", "JTF Central", "JTF Poseidon"])
selected_vector = st.sidebar.selectbox("Thematic Vector", ["All", "Electoral Security", "Securitization & Threat Groups", "Territorial & Maritime Security"])

def render_timeline(df: pd.DataFrame) -> None:
    timeline = df.copy()
    timeline["date"] = pd.to_datetime(timeline["created_at"]).dt.date
    counts = timeline.groupby(["date", "activity_type"]).size().reset_index(name="count")
    fig = px.bar(counts, x="date", y="count", color="activity_type", barmode="stack", title="Records by Day")
    st.plotly_chart(fig, use_container_width=True)


def render_distribution(df: pd.DataFrame) -> None:
    fig = px.pie(df, names="thematic_vector", hole=0.5, title="Distribution by Thematic Vector")
    st.plotly_chart(fig, use_container_width=True)


def render_leaderboard(df: pd.DataFrame) -> None:
    leaderboard = (
        df.groupby("province")["threat_score"].mean().sort_values(ascending=False).head(7).reset_index()
    )
    fig = px.bar(leaderboard, x="province", y="threat_score", title="Priority Leaderboard — Avg Threat Score by Province")
    st.plotly_chart(fig, use_container_width=True)


def render_network(df: pd.DataFrame) -> None:
    graph = nx.Graph()
    for _, row in df.iterrows():
        graph.add_edge(row["jtf_assignment"], row["province"])
    pos = nx.spring_layout(graph, seed=42)

    edge_x, edge_y = [], []
    for u, v in graph.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color="#888"), hoverinfo="none", mode="lines")

    node_x = [pos[n][0] for n in graph.nodes()]
    node_y = [pos[n][1] for n in graph.nodes()]
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=list(graph.nodes()),
        textposition="top center", marker=dict(size=14),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="JTF ↔ Province Network", showlegend=False,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_heatmap(df: pd.DataFrame) -> None:
    heat = pd.crosstab(df["thematic_vector"], df["province"])
    fig = px.imshow(heat, aspect="auto", title="Co-occurrence — Thematic Vector × Province")
    st.plotly_chart(fig, use_container_width=True)


st.subheader("Live Telemetry & Threat Feed")

try:
    response = requests.get(f"{API_URL}/records/")
    if response.status_code == 200:
        records = response.json()
        if records:
            df = pd.DataFrame(records)

            # Apply filters
            if selected_jtf != "All":
                df = df[df["jtf_assignment"] == selected_jtf]
            if selected_vector != "All":
                df = df[df["thematic_vector"] == selected_vector]

            st.dataframe(df[["id", "jtf_assignment", "province", "thematic_vector", "activity_type", "threat_score", "content", "created_at"]], use_container_width=True)

            st.markdown("---")
            render_timeline(df)

            col1, col2 = st.columns(2)
            with col1:
                render_distribution(df)
            with col2:
                render_leaderboard(df)

            render_network(df)
            render_heatmap(df)
        else:
            st.info("No OSINT records found in local database. Ingest telemetry payloads via API.")
    else:
        st.error("Failed to connect to backend telemetry service.")
except Exception as e:
    st.error(f"Connection error: {e}")
