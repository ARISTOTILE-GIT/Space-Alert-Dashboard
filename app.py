import streamlit as st
import numpy as np
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from skyfield.api import load, EarthSatellite

# ---------------------------------------------------------------
# 🌍 Streamlit Setup
# ---------------------------------------------------------------
st.set_page_config(page_title="🛰️ Project Kuppai-Track", layout="wide")
st.title("🛰️ Project Kuppai-Track")
st.markdown("A real-time conjunction alert system to track threats to our key satellites.")

# ---------------------------------------------------------------
# 📡 Load TLE Data (safe, no caching of Skyfield objects)
# ---------------------------------------------------------------
def load_tle_data():
    st.write("📡 Fetching TLE data from CelesTrak...")
    try:
        tle_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
        tle_text = requests.get(tle_url).text

        with open("active.txt", "w") as f:
            f.write(tle_text)

        ts = load.timescale()
        all_satellites = load.tle_file("active.txt")
        st.success(f"✅ Loaded {len(all_satellites)} active satellites.")
        return ts, all_satellites, tle_text

    except Exception as e:
        st.error(f"❌ Failed to load satellite data: {e}")
        return None, [], ""

ts, all_satellites, tle_text = load_tle_data()
if not all_satellites:
    st.stop()

# ---------------------------------------------------------------
# ⚙️ Sidebar Settings
# ---------------------------------------------------------------
st.sidebar.header("⚙️ Settings")
threshold_km = st.sidebar.slider("Alert Distance Threshold (km)", 10.0, 500.0, 100.0, 10.0)
st.sidebar.info("Adjust to control how close an object must be to trigger an alert.")

# ---------------------------------------------------------------
# 🎯 Target Satellite Selection
# ---------------------------------------------------------------
st.subheader("🎯 Select Target Satellite")
TARGETS = {
    "International Space Station (ISS)": 25544,
    "Hubble Space Telescope (HST)": 20580,
    "Starlink-4328": 51094
}
selected_name = st.selectbox("Choose a satellite to analyze:", TARGETS.keys())
target_id = TARGETS[selected_name]

# ---------------------------------------------------------------
# 🚀 Conjunction Analysis (cached safely)
# ---------------------------------------------------------------
@st.cache_data(show_spinner=True)
def run_conjunction_analysis(tle_text, target_id, threshold_km):
    ts = load.timescale()
    with open("cached.txt", "w") as f:
        f.write(tle_text)
    all_sats = load.tle_file("cached.txt")

    target_sat = next((s for s in all_sats if s.model.satnum == target_id), None)
    if not target_sat:
        return None, [], 0.0

    start_time = time.time()
    t_now = ts.now()
    t_range = ts.utc(t_now.utc_datetime() + np.arange(0, 1440) / 1440)  # 24h window

    target_pos = target_sat.at(t_range).position.km
    dangerous = []

    for debris in all_sats[:1000]:  # limit for performance
        if debris.model.satnum == target_id:
            continue
        debris_pos = debris.at(t_range).position.km
        dist = np.linalg.norm(target_pos - debris_pos, axis=0)
        min_d = np.min(dist)

        if 0.01 < min_d < threshold_km:
            idx = np.argmin(dist)
            t_closest = t_range[idx]
            dangerous.append({
                "Name": debris.name,
                "ID": debris.model.satnum,
                "Closest Distance (km)": f"{min_d:.2f}",
                "Time (UTC)": t_closest.utc_strftime('%Y-%m-%d %H:%M:%S')
            })

    dangerous.sort(key=lambda x: float(x["Closest Distance (km)"]))
    total_time = time.time() - start_time
    return target_sat, dangerous, total_time

# ---------------------------------------------------------------
# 🧠 Run Analysis
# ---------------------------------------------------------------
if st.button(f"🚀 Run Analysis for {selected_name}"):
    st.write("---")
    st.header(f"Results for {selected_name}")

    target_sat, dangerous_approaches, total_time = run_conjunction_analysis(
        tle_text, target_id, threshold_km
    )

    if not target_sat:
        st.error(f"Target {selected_name} not found in TLE data.")
        st.stop()

    st.metric("⏱ Analysis Time (s)", f"{total_time:.2f}")
    st.metric("🛰 Objects Checked", len(all_satellites))

    if not dangerous_approaches:
        st.success(f"✅ STATUS: GREEN — No objects within {threshold_km} km.")
    else:
        st.error(f"🚨 STATUS: RED — {len(dangerous_approaches)} Potential Conjunctions Found!")
        df = pd.DataFrame(dangerous_approaches)
        st.dataframe(df, use_container_width=True)

        # -------------------------------------------------------
        # 🪐 Optional: 3D Orbit Visualization
        # -------------------------------------------------------
        first = dangerous_approaches[0]
        debris = next((s for s in all_satellites if s.model.satnum == int(first['ID'])), None)
        if debris:
            t_range_short = ts.utc(ts.now().utc_datetime() + np.arange(0, 120) / 1440)
            target_path = target_sat.at(t_range_short).position.km
            debris_path = debris.at(t_range_short).position.km

            fig = go.Figure()
            fig.add_trace(go.Scatter3d(
                x=target_path[0], y=target_path[1], z=target_path[2],
                mode='lines', name=selected_name))
            fig.add_trace(go.Scatter3d(
                x=debris_path[0], y=debris_path[1], z=debris_path[2],
                mode='lines', name=first['Name'], line=dict(dash='dot')))
            fig.update_layout(
                scene=dict(xaxis_title='X (km)', yaxis_title='Y (km)', zaxis_title='Z (km)'),
                margin=dict(l=0, r=0, b=0, t=30),
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------
# 📘 Sidebar Info
# ---------------------------------------------------------------
st.sidebar.header("📘 About")
st.sidebar.info(
    "This app uses the Skyfield library and live CelesTrak data "
    "to predict potential collisions for major satellites over the next 24 hours."
)
