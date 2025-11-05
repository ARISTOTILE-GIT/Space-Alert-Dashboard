import streamlit as st
import numpy as np
import pandas as pd
import requests  # Make sure 'requests' is in requirements.txt
import time
import plotly.graph_objects as go  # Make sure 'plotly' is in requirements.txt
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
        # --- === ITHU THAN ANTHA FIX === ---
        # Use the direct .txt file, it's more stable
        tle_url = 'https://celestrak.org/NORAD/elements/active.txt'
        # Add a 10-second timeout
        tle_text = requests.get(tle_url, timeout=10).text
        # --- === END OF FIX === ---

        # Save the text to a local file for Skyfield to read
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
# Cache the function. The 'tle_text' is a simple string, so it's safe to cache.
@st.cache_data(show_spinner=True)
def run_conjunction_analysis(tle_text, target_id, threshold_km):
    # We must re-load the TLE text inside the cached function
    ts = load.timescale()
    with open("cached.txt", "w") as f:
        f.write(tle_text)
    all_sats = load.tle_file("cached.txt")

    target_sat = next((s for s in all_sats if s.model.satnum == target_id), None)
    if not target_sat:
        return None, [], 0.0, 0 # Return 0 for objects checked

    start_time = time.time()
    t_now = ts.now()
    # Create a 24-hour time range (1 point per minute)
    t_range = ts.utc(t_now.utc_datetime() + np.arange(0, 1440) / 1440)

    target_pos = target_sat.at(t_range).position.km
    dangerous = []

    # --- PERFORMANCE FIX ---
    # We should check ALL satellites, not just 1000
    objects_to_check = [s for s in all_sats if s.model.satnum != target_id]
    total_to_check = len(objects_to_check)
    # -----------------------

    for i, debris in enumerate(objects_to_check):
        debris_pos = debris.at(t_range).position.km
        dist = np.linalg.norm(target_pos - debris_pos, axis=0)
        min_d = np.min(dist)

        if 0.01 < min_d < threshold_km: # Ignore docked objects
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
    return target_sat, dangerous, total_time, total_to_check

# ---------------------------------------------------------------
# 🧠 Run Analysis
# ---------------------------------------------------------------
if st.button(f"🚀 Run Analysis for {selected_name}"):
    st.write("---")
    st.header(f"Results for {selected_name}")

    target_sat, dangerous_approaches, total_time, objects_checked = run_conjunction_analysis(
        tle_text, target_id, threshold_km
    )

    if not target_sat:
        st.error(f"Target {selected_name} not found in TLE data.")
        st.stop()

    # Display key metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("⏱ Analysis Time (s)", f"{total_time:.2f}")
    col2.metric("🛰️ Objects Checked", f"{objects_checked:,}") # Add comma for thousands
    col3.metric("🚨 Alerts Found", len(dangerous_approaches))

    if not dangerous_approaches:
        st.success(f"✅ STATUS: GREEN — No objects within {threshold_km} km.")
    else:
        st.error(f"🚨 STATUS: RED — {len(dangerous_approaches)} Potential Conjunctions Found!")
        df = pd.DataFrame(dangerous_approaches)
        st.dataframe(df, use_container_width=True)

        # -------------------------------------------------------
        # 🪐 Optional: 3D Orbit Visualization
        # -------------------------------------------------------
        st.subheader("Visualizing the Closest Approach")
        first = dangerous_approaches[0] # Get the most dangerous object
        debris = next((s for s in all_satellites if s.model.satnum == int(first['ID'])), None)
        if debris:
            st.write(f"Plotting orbit for **{selected_name}** vs. **{first['Name']}**...")
            
            # Create a 2-hour window for the plot
            t_range_short = ts.utc(ts.now().utc_datetime() + np.arange(0, 120) / 1440)
            target_path = target_sat.at(t_range_short).position.km
            debris_path = debris.at(t_range_short).position.km

            fig = go.Figure()
            # Target Satellite Path
            fig.add_trace(go.Scatter3d(
                x=target_path[0], y=target_path[1], z=target_path[2],
                mode='lines', name=selected_name, line=dict(width=4)))
            # Debris Path
            fig.add_trace(go.Scatter3d(
                x=debris_path[0], y=debris_path[1], z=debris_path[2],
                mode='lines', name=first['Name'], line=dict(dash='dot', width=4)))
            
            # Add a sphere for Earth
            fig.add_trace(go.Surface(
                x=6371 * np.outer(np.cos(np.linspace(0, 2*np.pi, 30)), np.sin(np.linspace(0, np.pi, 30))),
                y=6371 * np.outer(np.sin(np.linspace(0, 2*np.pi, 30)), np.sin(np.linspace(0, np.pi, 30))),
                z=6371 * np.outer(np.ones(30), np.cos(np.linspace(0, np.pi, 30))),
                colorscale=[[0, 'blue'], [1, 'blue']],
                opacity=0.3,
                showscale=False
            ))
            
            fig.update_layout(
                title=f"Closest Approach: {first['Name']} ({first['Closest Distance (km)']} km)",
                scene=dict(
                    xaxis_title='X (km)', yaxis_title='Y (km)', zaxis_title='Z (km)',
                    aspectmode='data' # This makes the Earth spherical
                ),
                margin=dict(l=0, r=0, b=0, t=40),
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
