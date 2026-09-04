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


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state['token']}"}


def render_login() -> None:
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


def render_ingestion_form() -> None:
    with st.expander("➕ Log New OSINT Record"):
        with st.form("new_record_form"):
            content = st.text_area("Content")
            col1, col2 = st.columns(2)
            with col1:
                jtf_assignment = st.selectbox("Joint Task Force", ["JTF ZAMPELAN", "JTF ORION", "JTF Central", "JTF Poseidon"])
                thematic_vector = st.selectbox("Thematic Vector", ["Electoral Security", "Securitization & Threat Groups", "Territorial & Maritime Security"])
                province = st.text_input("Province")
            with col2:
                activity_type = st.selectbox("Activity Type", ["Non-Violent", "Violent"])
                threat_score = st.slider("Threat Score", 0.0, 10.0, 0.0, 0.1)
                sentiment_score = st.slider("Sentiment Score", -1.0, 1.0, 0.0, 0.1)
            source_url = st.text_input("Source URL (optional)")

            if st.form_submit_button("Submit Record") and content and province:
                payload = {
                    "content": content,
                    "jtf_assignment": jtf_assignment,
                    "thematic_vector": thematic_vector,
                    "province": province,
                    "activity_type": activity_type,
                    "threat_score": threat_score,
                    "sentiment_score": sentiment_score,
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
    st.sidebar.header("Operational Parameters")
    st.sidebar.markdown(f"Signed in as **{st.session_state['username']}** ({st.session_state['role']})")
    if st.sidebar.button("Log Out"):
        for key in ("token", "username", "role"):
            st.session_state.pop(key, None)
        st.rerun()

    selected_jtf = st.sidebar.selectbox("Joint Task Force", ["All", "JTF ZAMPELAN", "JTF ORION", "JTF Central", "JTF Poseidon"])
    selected_vector = st.sidebar.selectbox("Thematic Vector", ["All", "Electoral Security", "Securitization & Threat Groups", "Territorial & Maritime Security"])

    st.title("🛡️ Regional Situational Awareness & OSINT Dashboard")
    st.markdown("---")

    if st.session_state["role"] in ("Admin", "Analyst"):
        render_ingestion_form()

    render_semantic_search()

    st.subheader("Live Telemetry & Threat Feed")

    try:
        response = requests.get(f"{API_URL}/records/", headers=auth_headers())
        if response.status_code == 200:
            records = response.json()
            if records:
                df = pd.DataFrame(records)

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
