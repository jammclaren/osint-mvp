import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px

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


def render_running_strawberries() -> None:
    st.markdown("""
    <style>
    .strawberry-runner {
        position: fixed; width: 30px; height: 30px; z-index: 9999; pointer-events: none;
        animation: run-loop 10s linear infinite;
    }
    .strawberry-runner svg { width: 100% !important; height: 100% !important; }
    .strawberry-runner .bounce {
        display: block; width: 100%; height: 100%;
        animation: run-bounce 0.35s ease-in-out infinite alternate;
    }
    .strawberry-runner.chaser { animation-delay: -1.2s; }
    .strawberry-runner.chaser .bounce { animation-delay: -0.15s; }

    @keyframes run-loop {
        0%   { top: 4vh; left: 3vw; }
        24%  { top: 4vh; left: 92vw; }
        25%  { top: 4vh; left: 92vw; }
        49%  { top: 88vh; left: 92vw; }
        50%  { top: 88vh; left: 92vw; }
        74%  { top: 88vh; left: 3vw; }
        75%  { top: 88vh; left: 3vw; }
        99%  { top: 4vh; left: 3vw; }
        100% { top: 4vh; left: 3vw; }
    }
    @keyframes run-bounce {
        0%   { transform: translateY(0) rotate(-8deg) scaleX(1); }
        100% { transform: translateY(-6px) rotate(8deg) scaleX(0.95); }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<div class="strawberry-runner leader"><span class="bounce">{STRAWBERRY_ICON}</span></div>'
        f'<div class="strawberry-runner chaser"><span class="bounce">{STRAWBERRY_ICON}</span></div>',
        unsafe_allow_html=True,
    )


def render_login() -> None:
    render_running_strawberries()
    left, center, right = st.columns([1, 1.3, 1])
    with center:
        st.markdown(f'<div class="sidebar-icon">{STRAWBERRY_ICON}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;"><span class="badge-pill">▸ Regional OSINT Platform · WESMINCOM</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<h2 style="text-align:center;">OSINT — Sign In</h2>', unsafe_allow_html=True)

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


SMI_CATEGORIES = {
    "Local Terrorist Groups": ["isis", "abu sayyaf", "daulah islamiyah", "dawlah islamiyah", "asg", "maute"],
    "Communist Terrorist Groups": ["cpp-npa-ndf", "cpp-npa", "cpp", "npa", "ndf"],
    "BARMM Parliamentary Elections": ["barmm", "bangsamoro parliament", "bpe", "parliamentary election", "comelec", "bangsamoro"],
    "West Philippine Sea & Sabah": ["west philippine sea", "wps", "sabah", "south china sea"],
}


def classify_smi_category(content: str) -> str:
    lower = str(content).lower()
    for category, terms in SMI_CATEGORIES.items():
        if any(term in lower for term in terms):
            return category
    return "Other / Uncategorized"


def render_kpis(df: pd.DataFrame, active_sources: int) -> None:
    created = pd.to_datetime(df["created_at"])
    now = pd.Timestamp.now(tz="UTC")
    this_week = created[created >= now - pd.Timedelta(days=7)]
    violent = df[df["activity_type"] == "Violent"]
    high_threat = df[df["threat_score"] >= 7.0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Monitored Posts", len(df))
    c2.metric("Violent", len(violent))
    c3.metric("Non-Violent", len(df) - len(violent))
    c4.metric("High-Threat", len(high_threat))
    c5.metric("Active Sources", active_sources)
    st.caption(f"Reflects {len(this_week)} post(s) in the last 7 days, extracted from Monitored Sources.")


def render_category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    cat_df = df.copy()
    cat_df["smi_category"] = cat_df["content"].map(classify_smi_category)

    counts = cat_df.groupby(["smi_category", "activity_type"]).size().reset_index(name="count")
    fig = px.bar(
        counts, x="smi_category", y="count", color="activity_type", barmode="group",
        title="Monitored Posts by Category — Violent vs. Non-Violent",
        category_orders={"smi_category": list(SMI_CATEGORIES.keys()) + ["Other / Uncategorized"]},
    )
    fig.update_xaxes(title=None)
    st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(4)
    for i, category in enumerate(SMI_CATEGORIES.keys()):
        sub = cat_df[cat_df["smi_category"] == category]
        with cols[i]:
            st.markdown(f"**{category}**")
            st.metric("Violent", len(sub[sub["activity_type"] == "Violent"]))
            st.metric("Non-Violent", len(sub[sub["activity_type"] == "Non-Violent"]))

    return cat_df


def render_timeline(df: pd.DataFrame) -> None:
    timeline = df.copy()
    timeline["date"] = pd.to_datetime(timeline["created_at"]).dt.date
    counts = timeline.groupby(["date", "activity_type"]).size().reset_index(name="count")
    fig = px.bar(counts, x="date", y="count", color="activity_type", barmode="stack", title="Volume Over Time")
    st.plotly_chart(fig, use_container_width=True)


def render_platform_distribution(df: pd.DataFrame) -> None:
    if "source_platform" not in df.columns:
        return
    fig = px.pie(df, names="source_platform", hole=0.5, title="Posts by Source Platform")
    st.plotly_chart(fig, use_container_width=True)


def render_geo_priority(df: pd.DataFrame) -> None:
    geo = df.copy()
    geo["lat"] = geo["province"].map(lambda p: PROVINCE_CENTROIDS.get(p, (None, None))[0])
    geo["lon"] = geo["province"].map(lambda p: PROVINCE_CENTROIDS.get(p, (None, None))[1])
    geo = geo.dropna(subset=["lat", "lon"])
    if geo.empty:
        return

    agg = geo.groupby(["province", "lat", "lon"]).agg(
        post_count=("id", "count"), avg_threat=("threat_score", "mean")
    ).reset_index()

    fig = px.scatter_geo(
        agg, lat="lat", lon="lon", size="post_count", color="avg_threat",
        hover_name="province", color_continuous_scale="OrRd",
        title="Geographic Priority — Where to Focus Response",
    )
    fig.update_geos(
        lataxis_range=[4, 10], lonaxis_range=[118, 126],
        showland=True, landcolor="rgb(30,30,30)", showcountries=True,
    )
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


def render_compact_search() -> None:
    query = st.text_input("Search", key="smi_search", placeholder="🔎 Search monitored posts...", label_visibility="collapsed")
    if not query:
        return
    try:
        resp = requests.get(f"{API_URL}/records/search", params={"q": query, "limit": 5}, headers=auth_headers())
        if resp.status_code == 200:
            results = resp.json()
            if results:
                results_df = pd.DataFrame(results)
                results_df["similarity"] = results_df["similarity"].map(lambda s: f"{s:.2f}")
                st.dataframe(
                    results_df[["similarity", "province", "thematic_vector", "content", "created_at"]],
                    use_container_width=True, height=180,
                )
            else:
                st.caption("No matches.")
        else:
            st.error(resp.json().get("detail", "Search failed"))
    except Exception as e:
        st.error(f"Connection error: {e}")


def render_auto_assessment(df: pd.DataFrame, alerts: list) -> None:
    cat_df = df.copy()
    cat_df["smi_category"] = cat_df["content"].map(classify_smi_category)

    total = len(cat_df)
    violent = len(cat_df[cat_df["activity_type"] == "Violent"])
    high_threat = cat_df[cat_df["threat_score"] >= 7.0]
    unacknowledged = [a for a in alerts if not a["acknowledged"]]

    cat_counts = cat_df["smi_category"].value_counts()
    top_category = cat_counts.index[0] if not cat_counts.empty else "N/A"

    prov_threat = cat_df.groupby("province")["threat_score"].mean().sort_values(ascending=False)
    top_province = prov_threat.index[0] if not prov_threat.empty else "N/A"
    top_province_score = prov_threat.iloc[0] if not prov_threat.empty else 0

    with st.container(border=True):
        st.markdown("**SITUATION SUMMARY**")
        st.markdown(
            f"- **{total}** posts monitored, **{violent}** flagged violent ({violent / total * 100:.0f}% of total)."
            if total else "- No posts monitored yet."
        )
        if total:
            st.markdown(f"- Dominant category: **{top_category}** ({cat_counts.iloc[0]} posts).")
            st.markdown(f"- **{len(high_threat)}** post(s) at high threat level (≥7.0).")
            st.markdown(f"- Highest average threat concentration: **{top_province}** (avg {top_province_score:.1f}/10).")
        st.markdown(f"- **{len(unacknowledged)}** unacknowledged alert(s) pending review.")

        st.markdown("**RECOMMENDATION**")
        if len(unacknowledged) > 0:
            st.markdown(f"- Prioritize review of {len(unacknowledged)} open alert(s) before next scan cycle.")
        if total and top_province != "N/A" and top_province_score >= 5.0:
            st.markdown(f"- Consider reinforcing monitoring/response posture in **{top_province}** given elevated threat concentration.")
        if total and cat_counts.iloc[0] > 0:
            st.markdown(f"- Sustained volume in **{top_category}** warrants continued source coverage in that category.")
        if not unacknowledged and (not total or top_province_score < 5.0):
            st.markdown("- No immediate escalation indicated by current data; maintain standard monitoring cadence.")

        st.caption("Auto-generated from monitored source data — rule-based summary, not a substitute for analyst judgment.")


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

    header_col, search_col = st.columns([3, 1])
    with header_col:
        st.markdown('<span class="badge-pill">▸ Regional OSINT Platform · WESMINCOM</span>', unsafe_allow_html=True)
        st.title("🛡️ Regional Situational Awareness & OSINT Dashboard")
    with search_col:
        st.markdown("<div style='height:2.3em;'></div>", unsafe_allow_html=True)
        render_compact_search()

    now_str = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(
        f'<div class="ops-banner"><span><span class="status-dot"></span><span class="live">SYSTEM ONLINE</span> · SCAN: HOURLY / ON-DEMAND</span>'
        f'<span>{now_str}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    render_alerts()
    st.markdown("---")

    try:
        response = requests.get(f"{API_URL}/records/", headers=auth_headers())
        if response.status_code == 200:
            records = response.json()
            if records:
                df_all = pd.DataFrame(records)

                try:
                    sources = requests.get(f"{API_URL}/sources/", headers=auth_headers()).json()
                    active_source_count = sum(1 for s in sources if s["status"] == "Active")
                except Exception:
                    active_source_count = 0

                try:
                    all_alerts = requests.get(f"{API_URL}/alerts/", headers=auth_headers()).json()
                except Exception:
                    all_alerts = []

                df = df_all
                if selected_jtf != "All":
                    df = df[df["jtf_assignment"] == selected_jtf]
                if selected_vector != "All":
                    df = df[df["thematic_vector"] == selected_vector]

                st.subheader("📊 Social Media Intelligence Overview")
                st.caption("All entries extracted from Monitored Sources (public pages, officials, vloggers).")
                render_kpis(df, active_source_count)
                st.markdown("---")
                render_category_breakdown(df)
                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
                    render_timeline(df)
                with col2:
                    render_platform_distribution(df)

                render_geo_priority(df)

                st.markdown("---")
                st.subheader("🧭 Auto-Generated Analysis & Assessment")
                render_auto_assessment(df, all_alerts)
            else:
                st.info("No monitored posts yet.")
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
