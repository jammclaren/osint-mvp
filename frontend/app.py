import streamlit as st
import requests
import os
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go

API_URL = os.getenv("API_URL", "http://localhost:8000")

STRAWBERRY_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="44" height="44">
  <path d="M50,25 C65,25 80,35 80,60 C80,80 55,95 50,95 C45,95 20,80 20,60 C20,35 35,25 50,25 Z" fill="#d9a441" />
  <path d="M50,28 C53,20 62,12 72,18 C65,22 60,28 58,32 C65,30 75,30 82,36 C72,38 62,36 55,34 C56,42 54,50 50,55 C46,50 44,42 45,34 C38,36 28,38 18,36 C25,30 35,30 42,32 C40,28 35,22 28,18 C38,12 47,20 50,28 Z" fill="#d9a441" />
  <g fill="#FFFFFF">
    <circle cx="42" cy="45" r="2" />
    <circle cx="58" cy="45" r="2" />
    <circle cx="34" cy="58" r="2" />
    <circle cx="50" cy="58" r="2" />
    <circle cx="66" cy="58" r="2" />
    <circle cx="42" cy="71" r="2" />
    <circle cx="58" cy="71" r="2" />
    <circle cx="50" cy="83" r="2" />
  </g>
</svg>
"""

st.set_page_config(
    page_title="OSINT Situational Awareness Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown("""
<style>
:root {
    --bg: #0a0a0a;
    --panel: #12140f;
    --panel-border: #2a2f22;
    --gold: #d9a441;
    --gold-hover: #e8b755;
    --gold-dim: rgba(217, 164, 65, 0.12);
    --text: #d8dccc;
    --text-muted: #7c8268;
    --green: #4ade80;
    --amber-glow: rgba(217, 164, 65, 0.25);
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg); color: var(--text);
    font-family: 'Rajdhani', sans-serif;
}
[data-testid="stAppViewContainer"] {
    background-image:
        linear-gradient(rgba(217,164,65,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(217,164,65,0.035) 1px, transparent 1px);
    background-size: 32px 32px;
}
[data-testid="stHeader"] { background-color: var(--bg); }
[data-testid="stSidebar"] { background-color: #0d0f0a; border-right: 1px solid var(--panel-border); }

h1, h2, h3, h4 { color: var(--text) !important; letter-spacing: 0.03em; font-family: 'Rajdhani', sans-serif; font-weight: 700 !important; text-transform: uppercase; }
p, span, div, label, li { font-family: 'Rajdhani', sans-serif; }
code, .stCode, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { font-family: 'Share Tech Mono', monospace !important; }

.ops-banner {
    display: flex; justify-content: space-between; align-items: center;
    border: 1px solid var(--panel-border); border-left: 3px solid var(--gold);
    background: linear-gradient(90deg, rgba(217,164,65,0.06), transparent);
    padding: 6px 14px; margin-bottom: 14px;
    font-family: 'Share Tech Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--text-muted);
}
.ops-banner .live { color: var(--green); }

.badge-pill {
    display: inline-block; padding: 4px 12px; border: 1px solid var(--gold);
    border-radius: 2px; color: var(--gold); font-size: 0.72rem; font-weight: 700;
    font-family: 'Share Tech Mono', monospace;
    letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 12px;
    clip-path: polygon(8px 0, 100% 0, 100% 100%, 0 100%, 0 8px);
}
.status-dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background-color: var(--green); margin-right: 6px;
    box-shadow: 0 0 6px var(--green);
    animation: pulse 1.6s infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

.sidebar-icon { text-align: center; margin-bottom: 4px; }
.sidebar-icon svg {
    background-color: #f4f1e8; border: 2px solid var(--gold); border-radius: 50%;
    padding: 6px; box-shadow: 0 0 12px var(--gold-dim);
}

.stButton > button {
    background-color: transparent; color: var(--gold); border: 1px solid var(--gold);
    border-radius: 2px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; font-size: 0.8rem;
    font-family: 'Share Tech Mono', monospace;
}
.stButton > button:hover { background-color: var(--gold-dim); border-color: var(--gold-hover); color: var(--gold-hover); box-shadow: 0 0 10px var(--amber-glow); }

[data-testid="stFormSubmitButton"] > button {
    background-color: var(--gold); color: #0a0a0a; border: none;
    border-radius: 2px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    font-family: 'Share Tech Mono', monospace;
}
[data-testid="stFormSubmitButton"] > button:hover { background-color: var(--gold-hover); color: #0a0a0a; box-shadow: 0 0 12px var(--amber-glow); }

[data-testid="stExpander"] { background-color: var(--panel); border: 1px solid var(--panel-border); border-radius: 2px; }
[data-testid="stMetric"] {
    background-color: var(--panel); border: 1px solid var(--panel-border); border-left: 2px solid var(--gold);
    border-radius: 2px; padding: 10px 14px;
}

input, textarea { background-color: #14150f !important; border-color: var(--panel-border) !important; color: var(--text) !important; border-radius: 2px !important; }
[data-baseweb="select"] > div { background-color: #14150f !important; border-color: var(--panel-border) !important; border-radius: 2px !important; }

[data-testid="stDataFrame"] { border: 1px solid var(--panel-border); border-radius: 2px; }
.stAlert { border-radius: 2px; }
[data-testid="stMetricValue"] { color: var(--gold) !important; text-shadow: 0 0 8px var(--amber-glow); }
</style>
""", unsafe_allow_html=True)


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state['token']}"}


def render_login() -> None:
    st.markdown(f'<div class="sidebar-icon" style="text-align:left;">{STRAWBERRY_ICON}</div>', unsafe_allow_html=True)
    st.markdown('<span class="badge-pill">▸ Regional OSINT Platform · WESMINCOM</span>', unsafe_allow_html=True)
    st.title("🛡️ OSINT Dashboard — Sign In")
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In") and username and password:
                try:
                    resp = requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})
                    if resp.status_code == 200:
                        st.session_state["token"] = resp.json()["access_token"]
                        me = requests.get(f"{API_URL}/auth/me", headers={"Authorization": f"Bearer {st.session_state['token']}"})
                        st.session_state["username"] = me.json()["username"]
                        st.session_state["role"] = me.json()["role"]
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Login failed"))
                except Exception as e:
                    st.error(f"Connection error: {e}")

    with register_tab:
        st.caption("The first account registered becomes Admin. Later accounts default to Viewer.")
        with st.form("register_form"):
            username = st.text_input("Choose a username")
            password = st.text_input("Choose a password", type="password")
            if st.form_submit_button("Register") and username and password:
                try:
                    resp = requests.post(f"{API_URL}/auth/register", json={"username": username, "password": password})
                    if resp.status_code == 200:
                        st.success("Account created. Switch to the Login tab to sign in.")
                    else:
                        st.error(resp.json().get("detail", "Registration failed"))
                except Exception as e:
                    st.error(f"Connection error: {e}")


PLATFORM_OPTIONS = ["X/Twitter", "Telegram", "Facebook", "Field Report"]
PLATFORM_ICON = {"X/Twitter": "🐦", "Telegram": "✈️", "Facebook": "📘", "Field Report": "📋"}


def render_ingestion_form() -> None:
    with st.expander("➕ Log New OSINT Record"):
        with st.form("new_record_form"):
            content = st.text_area("Content")
            col1, col2 = st.columns(2)
            with col1:
                jtf_assignment = st.selectbox("Joint Task Force", ["JTF ZAMPELAN", "JTF ORION", "JTF Central", "JTF Poseidon"])
                thematic_vector = st.selectbox("Thematic Vector", ["Electoral Security", "Securitization & Threat Groups", "Territorial & Maritime Security"])
                province = st.text_input("Province")
                source_platform = st.selectbox("Source Platform", PLATFORM_OPTIONS)
            with col2:
                activity_type = st.selectbox("Activity Type", ["Non-Violent", "Violent"])
                threat_score = st.slider("Threat Score", 0.0, 10.0, 0.0, 0.1)
                sentiment_score = st.slider("Sentiment Score", -1.0, 1.0, 0.0, 0.1)
            source_url = st.text_input("Source URL / Post Link (optional)")

            if st.form_submit_button("Submit Record") and content and province:
                payload = {
                    "content": content,
                    "jtf_assignment": jtf_assignment,
                    "thematic_vector": thematic_vector,
                    "province": province,
                    "activity_type": activity_type,
                    "threat_score": threat_score,
                    "sentiment_score": sentiment_score,
                    "source_platform": source_platform,
                    "source_url": source_url or None,
                }
                try:
                    resp = requests.post(f"{API_URL}/records/", json=payload, headers=auth_headers())
                    if resp.status_code == 200:
                        st.success("Record logged.")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Failed to submit record"))
                except Exception as e:
                    st.error(f"Connection error: {e}")


def render_edit_delete(df: pd.DataFrame) -> None:
    with st.expander("✏️ Edit / Delete Record"):
        record_id = st.selectbox("Record ID", df["id"].tolist(), key="edit_record_id")
        record = df[df["id"] == record_id].iloc[0]

        with st.form("edit_record_form"):
            content = st.text_area("Content", value=record["content"])
            col1, col2 = st.columns(2)
            jtf_options = ["JTF ZAMPELAN", "JTF ORION", "JTF Central", "JTF Poseidon"]
            vector_options = ["Electoral Security", "Securitization & Threat Groups", "Territorial & Maritime Security"]
            activity_options = ["Non-Violent", "Violent"]
            with col1:
                jtf_assignment = st.selectbox("Joint Task Force", jtf_options, index=jtf_options.index(record["jtf_assignment"]) if record["jtf_assignment"] in jtf_options else 0)
                thematic_vector = st.selectbox("Thematic Vector", vector_options, index=vector_options.index(record["thematic_vector"]) if record["thematic_vector"] in vector_options else 0)
                province = st.text_input("Province", value=record["province"])
                current_platform = record.get("source_platform", "Field Report")
                source_platform = st.selectbox("Source Platform", PLATFORM_OPTIONS, index=PLATFORM_OPTIONS.index(current_platform) if current_platform in PLATFORM_OPTIONS else 3)
            with col2:
                activity_type = st.selectbox("Activity Type", activity_options, index=activity_options.index(record["activity_type"]) if record["activity_type"] in activity_options else 0)
                threat_score = st.slider("Threat Score", 0.0, 10.0, float(record["threat_score"]), 0.1)
                sentiment_score = st.slider("Sentiment Score", -1.0, 1.0, float(record["sentiment_score"]), 0.1)

            col_save, col_delete = st.columns(2)
            with col_save:
                save = st.form_submit_button("Save Changes")
            with col_delete:
                delete = st.form_submit_button("Delete Record", type="primary")

            if save:
                payload = {
                    "content": content, "jtf_assignment": jtf_assignment, "thematic_vector": thematic_vector,
                    "province": province, "activity_type": activity_type,
                    "threat_score": threat_score, "sentiment_score": sentiment_score,
                    "source_platform": source_platform,
                }
                try:
                    resp = requests.patch(f"{API_URL}/records/{record_id}", json=payload, headers=auth_headers())
                    if resp.status_code == 200:
                        st.success("Record updated.")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Update failed"))
                except Exception as e:
                    st.error(f"Connection error: {e}")

            if delete:
                if st.session_state["role"] != "Admin":
                    st.error("Only Admins can delete records.")
                else:
                    try:
                        resp = requests.delete(f"{API_URL}/records/{record_id}", headers=auth_headers())
                        if resp.status_code == 200:
                            st.success("Record deleted.")
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Delete failed"))
                    except Exception as e:
                        st.error(f"Connection error: {e}")


def render_timeline(df: pd.DataFrame) -> None:
    timeline = df.copy()
    timeline["date"] = pd.to_datetime(timeline["created_at"]).dt.date
    counts = timeline.groupby(["date", "activity_type"]).size().reset_index(name="count")
    fig = px.bar(counts, x="date", y="count", color="activity_type", barmode="stack", title="Records by Day")
    st.plotly_chart(fig, use_container_width=True)


def render_kpis(df: pd.DataFrame, active_sources: int) -> None:
    created = pd.to_datetime(df["created_at"])
    now = pd.Timestamp.now(tz="UTC")
    this_week = created[created >= now - pd.Timedelta(days=7)]
    high_threat = df[df["threat_score"] >= 7.0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Monitored Incidents", len(df))
    c2.metric("Incidents — Last 7 Days", len(this_week))
    c3.metric("High-Threat Incidents", len(high_threat))
    c4.metric("Active Monitored Sources", active_sources)


def render_platform_distribution(df: pd.DataFrame) -> None:
    if "source_platform" not in df.columns:
        return
    fig = px.pie(df, names="source_platform", hole=0.5, title="Incidents by Source Platform")
    st.plotly_chart(fig, use_container_width=True)


def render_monitored_sources() -> None:
    with st.expander("📡 Monitored Sources — Public Pages & Figures"):
        try:
            resp = requests.get(f"{API_URL}/sources/", headers=auth_headers())
            sources = resp.json() if resp.status_code == 200 else []
        except Exception:
            sources = []

        if sources:
            st.dataframe(pd.DataFrame(sources)[["platform", "handle", "status", "notes"]], use_container_width=True)
        else:
            st.caption("No sources configured yet.")

        with st.form("new_source_form"):
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                platform = st.selectbox("Platform", PLATFORM_OPTIONS[:-1])
            with col2:
                handle = st.text_input("Page / Channel / Handle", placeholder="e.g. Cotabato News, Brigada News BARMM")
            with col3:
                source_status = st.selectbox("Status", ["Active", "Pending", "Paused"])
            notes = st.text_input("Notes (optional)", placeholder="e.g. Public news page / public figure / vlogger")
            if st.form_submit_button("Add Source") and handle:
                try:
                    resp = requests.post(
                        f"{API_URL}/sources/",
                        json={"platform": platform, "handle": handle, "status": source_status, "notes": notes or None},
                        headers=auth_headers(),
                    )
                    if resp.status_code == 200:
                        st.success(f"Added '{handle}'.")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Failed to add source"))
                except Exception as e:
                    st.error(f"Connection error: {e}")


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


PROVINCE_CENTROIDS = {
    "Sulu": (6.0474, 121.0000),
    "Basilan": (6.4297, 121.9689),
    "Tawi-Tawi": (5.1339, 119.9333),
    "Zamboanga del Sur": (7.8383, 123.4360),
    "Zamboanga del Norte": (8.1527, 123.2577),
    "Zamboanga Sibugay": (7.5222, 122.8198),
    "Lanao del Sur": (7.8232, 124.4357),
    "Lanao del Norte": (8.1156, 123.9315),
    "Maguindanao": (6.9423, 124.4198),
}

SEVERITY_COLOR = {"High": "🔴", "Medium": "🟠"}


def render_alerts() -> None:
    st.subheader("🚨 Alerts")
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.session_state["role"] in ("Admin", "Analyst") and st.button("Run Scan Now"):
            try:
                resp = requests.post(f"{API_URL}/scan/run", headers=auth_headers())
                if resp.status_code == 200:
                    st.success(f"Scan complete — {resp.json()['new_alerts']} new alert(s).")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", "Scan failed"))
            except Exception as e:
                st.error(f"Connection error: {e}")

    try:
        resp = requests.get(f"{API_URL}/alerts/", params={"unacknowledged_only": True}, headers=auth_headers())
        if resp.status_code != 200:
            st.error("Failed to load alerts.")
            return
        alerts = resp.json()
        if not alerts:
            st.caption("No active alerts.")
            return
        for alert in alerts:
            icon = SEVERITY_COLOR.get(alert["severity"], "⚪")
            c1, c2 = st.columns([9, 1])
            with c1:
                st.markdown(f"{icon} **{alert['rule_type']}** — {alert['message']}")
            with c2:
                if st.session_state["role"] in ("Admin", "Analyst") and st.button("Ack", key=f"ack_{alert['id']}"):
                    requests.post(f"{API_URL}/alerts/{alert['id']}/acknowledge", headers=auth_headers())
                    st.rerun()
    except Exception as e:
        st.error(f"Connection error: {e}")


def render_keyword_manager() -> None:
    with st.expander("🎯 Target Keyword Dictionary"):
        try:
            resp = requests.get(f"{API_URL}/keywords/", headers=auth_headers())
            keywords = resp.json() if resp.status_code == 200 else []
        except Exception:
            keywords = []

        if keywords:
            st.dataframe(pd.DataFrame(keywords)[["term", "category", "created_at"]], use_container_width=True)
        else:
            st.caption("No keywords tracked yet.")

        with st.form("new_keyword_form"):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                term = st.text_input("Term (e.g. CPP-NPA, Abu Sayyaf, COMELEC)")
            with col2:
                category = st.selectbox("Category", ["Threat Group", "Election", "Region"])
            with col3:
                st.write("")
                submitted = st.form_submit_button("Add")
            if submitted and term:
                try:
                    resp = requests.post(f"{API_URL}/keywords/", json={"term": term, "category": category}, headers=auth_headers())
                    if resp.status_code == 200:
                        st.success(f"Added '{term}'.")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Failed to add keyword"))
                except Exception as e:
                    st.error(f"Connection error: {e}")


def render_trend_spikes(df: pd.DataFrame) -> None:
    trend = df.copy()
    trend["date"] = pd.to_datetime(trend["created_at"]).dt.date
    daily = trend.groupby(["date", "thematic_vector"]).size().reset_index(name="count")

    daily["mean"] = daily.groupby("thematic_vector")["count"].transform("mean")
    daily["std"] = daily.groupby("thematic_vector")["count"].transform("std").fillna(0)
    daily["is_spike"] = daily["count"] > (daily["mean"] + daily["std"])

    fig = px.bar(
        daily, x="date", y="count", color="thematic_vector",
        pattern_shape="is_spike", pattern_shape_map={True: "x", False: ""},
        title="Trend Analysis — Volume by Thematic Vector (✕ pattern = spike day)",
    )
    st.plotly_chart(fig, use_container_width=True)

    spikes = daily[daily["is_spike"]]
    if not spikes.empty:
        st.warning(f"{len(spikes)} spike day(s) detected — volume above the vector's rolling mean + 1 std dev.")
        st.dataframe(spikes[["date", "thematic_vector", "count"]], use_container_width=True)


def render_geo_map(df: pd.DataFrame) -> None:
    geo = df.copy()
    geo["lat"] = geo["province"].map(lambda p: PROVINCE_CENTROIDS.get(p, (None, None))[0])
    geo["lon"] = geo["province"].map(lambda p: PROVINCE_CENTROIDS.get(p, (None, None))[1])
    geo = geo.dropna(subset=["lat", "lon"])

    if geo.empty:
        st.caption("No records with a mappable province yet.")
        return

    agg = geo.groupby(["province", "lat", "lon"]).agg(
        record_count=("id", "count"), avg_threat=("threat_score", "mean")
    ).reset_index()

    fig = px.scatter_geo(
        agg, lat="lat", lon="lon", size="record_count", color="avg_threat",
        hover_name="province", color_continuous_scale="OrRd",
        title="Geospatial Distribution — OSINT Data Points by Province",
    )
    fig.update_geos(
        lataxis_range=[4, 10], lonaxis_range=[118, 126],
        showland=True, landcolor="rgb(30,30,30)", showcountries=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_semantic_search() -> None:
    with st.expander("🔎 Semantic Search"):
        query = st.text_input("Search by meaning (not just keywords)", key="semantic_query")
        if query:
            try:
                resp = requests.get(f"{API_URL}/records/search", params={"q": query, "limit": 10}, headers=auth_headers())
                if resp.status_code == 200:
                    results = resp.json()
                    if results:
                        results_df = pd.DataFrame(results)
                        results_df["similarity"] = results_df["similarity"].map(lambda s: f"{s:.2f}")
                        st.dataframe(
                            results_df[["similarity", "jtf_assignment", "province", "thematic_vector", "content", "created_at"]],
                            use_container_width=True,
                        )
                    else:
                        st.info("No matches — records need an embedding, which is only generated for records created after this feature shipped.")
                else:
                    st.error(resp.json().get("detail", "Search failed"))
            except Exception as e:
                st.error(f"Connection error: {e}")


def render_dashboard() -> None:
    st.sidebar.markdown(f'<div class="sidebar-icon">{STRAWBERRY_ICON}</div>', unsafe_allow_html=True)
    st.sidebar.header("Operational Parameters")
    st.sidebar.markdown(f"Signed in as **{st.session_state['username']}** ({st.session_state['role']})")
    if st.sidebar.button("Log Out"):
        for key in ("token", "username", "role"):
            st.session_state.pop(key, None)
        st.rerun()

    selected_jtf = st.sidebar.selectbox("Joint Task Force", ["All", "JTF ZAMPELAN", "JTF ORION", "JTF Central", "JTF Poseidon"])
    selected_vector = st.sidebar.selectbox("Thematic Vector", ["All", "Electoral Security", "Securitization & Threat Groups", "Territorial & Maritime Security"])

    st.markdown('<span class="badge-pill">▸ Regional OSINT Platform · WESMINCOM</span>', unsafe_allow_html=True)
    st.title("🛡️ Regional Situational Awareness & OSINT Dashboard")
    now_str = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(
        f'<div class="ops-banner"><span><span class="status-dot"></span><span class="live">SYSTEM ONLINE</span> · SCAN: HOURLY / ON-DEMAND</span>'
        f'<span>{now_str}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    render_alerts()
    st.markdown("---")

    if st.session_state["role"] in ("Admin", "Analyst"):
        render_ingestion_form()
        render_keyword_manager()
        render_monitored_sources()

    render_semantic_search()

    st.subheader("Live Telemetry & Threat Feed")

    try:
        response = requests.get(f"{API_URL}/records/", headers=auth_headers())
        if response.status_code == 200:
            records = response.json()
            if records:
                df_all = pd.DataFrame(records)

                try:
                    active_sources = requests.get(f"{API_URL}/sources/", headers=auth_headers()).json()
                    active_source_count = sum(1 for s in active_sources if s["status"] == "Active")
                except Exception:
                    active_source_count = 0

                render_kpis(df_all, active_source_count)
                st.markdown("---")

                df = df_all
                if selected_jtf != "All":
                    df = df[df["jtf_assignment"] == selected_jtf]
                if selected_vector != "All":
                    df = df[df["thematic_vector"] == selected_vector]

                display_df = df.copy()
                if "source_platform" in display_df.columns:
                    display_df["source_platform"] = display_df["source_platform"].map(
                        lambda p: f"{PLATFORM_ICON.get(p, '')} {p}"
                    )
                    cols = ["id", "source_platform", "jtf_assignment", "province", "thematic_vector", "activity_type", "threat_score", "content", "created_at"]
                else:
                    cols = ["id", "jtf_assignment", "province", "thematic_vector", "activity_type", "threat_score", "content", "created_at"]
                st.dataframe(display_df[cols], use_container_width=True)

                if st.session_state["role"] in ("Admin", "Analyst"):
                    render_edit_delete(df)

                st.markdown("---")
                render_timeline(df)

                col1, col2 = st.columns(2)
                with col1:
                    render_distribution(df)
                with col2:
                    render_leaderboard(df)

                render_platform_distribution(df)

                render_network(df)
                render_heatmap(df)

                st.markdown("---")
                render_trend_spikes(df)

                st.markdown("---")
                render_geo_map(df)
            else:
                st.info("No OSINT records found in local database. Use the form above to log one.")
        elif response.status_code == 401:
            for key in ("token", "username", "role"):
                st.session_state.pop(key, None)
            st.rerun()
        else:
            st.error("Failed to connect to backend telemetry service.")
    except Exception as e:
        st.error(f"Connection error: {e}")


if "token" not in st.session_state:
    render_login()
else:
    render_dashboard()
