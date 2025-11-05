import streamlit as st
import numpy as np
from skyfield.api import load, EarthSatellite
import time
import pandas as pd
import plotly.graph_objects as go

# --- Streamlit Config ---
st.set_page_config(page_title="🛰️ Project Kuppai-Track", layout="wide")

# --- Caching Data Loading ---
@st.cache_data(show_spinner=False)
def load_tle_data():
    ts = load.timescale()
    tle_url_active = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
    st.write("Loading TLE data from CelesTrak...")
    try:
        all_satellites = load.tle_file(tle_url_active, reload=True)
        st.write(f"✅ Loaded {len(all_satellites)} active satellites.")
        return ts, all_satellites
    except Exception as e:
        st.error(f"Error loading active satellites: {e}")
        return ts, []

# --- Cached Analysis ---
@st.cache_data(show_spinner=True)
def run_conjunction_analysis(ts, all_satellites, target_id, target_name, threshold_km):
    start_time = time.time()
    
    # Select Target
    target_sat = next((sat for sat in all_satellites if sat.model.satnum == target_id), None)
    if not target_sat:
        return None, [], 0.0

    objects_to_check = [sat for sat in all_satellites if sat.model.satnum != target_id]
    dangerous_approaches = []

    # Time range (1-minute resolution for 24h)
    t0 = ts.now()
    t_range = ts.utc(t0.utc_datetime() + np.arange(0, 1440) / 1440)  # 24h timeline

    target_pos = target_sat.at(t_range).position.km

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_objects = len(objects_to_check)
    for i, debris in enumerate(objects_to_check):
        debris_pos = debris.at(t_range).position.km
        raw_distance = target_pos - debris_pos
        distance_km = np.linalg.norm(raw_distance, axis=0)
        min_distance = np.min(distance_km)
        
        # Check threshold
        if 0.01 < min_distance < threshold_km:
            min_index = np.argmin(distance_km)
            time_of_closest_approach = t_range[min_index]
            dangerous_approaches.append({
                "name": debris.name,
                "id": debris.model.satnum,
                "distance_km": min_distance,
                "time_utc": time_of_closest_approach.utc_strftime('%Y-%m-%d %H:%M:%S')
            })
        
        if (i+1) % 100 == 0:
            progress_bar.progress((i+1) / total_objects)
            status_text.text(f"Checked {i+1}/{total_objects} objects...")

    progress_bar.progress(1.0)
    status_text.text("✅ Analysis Complete!")

    total_time = time.time() - start_time
    dangerous_approaches.sort(key=lambda x: x['distance_km'])
    return target_sat, dangerous_approaches, total_time

# --- UI Start ---
st.title("🛰️ Project 'Kuppai-Track'")
st.markdown("A real-time conjunction alert system to track threats to our key satellites.")

# Sidebar Info
st.sidebar.header("⚙️ Settings")
threshold_km = st.sidebar.slider("Alert Distance Threshold (km)", 10.0, 500.0, 100.0, 10.0)
st.sidebar.info("Adjust the alert distance to control sensitivity.")

# Load Data
with st.spinner("Fetching satellite database from CelesTrak..."):
    ts, all_satellites = load_tle_data()

if not all_satellites:
    st.error("Failed to load satellite data. Please refresh the app.")
    st.stop()

# Satellite Selection
st.subheader("🎯 Select Target Satellite")
TARGETS = {
    "International Space Station (ISS)": 25544,
    "Hubble Space Telescope (HST)": 20580,
    "Starlink-4328": 51094
}
selected_name = st.selectbox("Choose a satellite to analyze:", TARGETS.keys())
target_id_to_run = TARGETS[selected_name]

# Run Analysis
if st.button(f"🚀 Run Analysis for {selected_name}"):
    st.write("---")
    st.header(f"Results for {selected_name}")
    
    target_sat, dangerous_approaches, total_time = run_conjunction_analysis(
        ts, all_satellites, target_id_to_run, selected_name, threshold_km
    )

    if not target_sat:
        st.error(f"Target {selected_name} not found in TLE data.")
        st.stop()

    st.metric("⏱ Analysis Time (s)", f"{total_time:.2f}")
    st.metric("🛰 Objects Checked", len(all_satellites))

    # Results
    if not dangerous_approaches:
        st.success(f"✅ STATUS: GREEN — No objects within {threshold_km} km.")
    else:
        st.error(f"🚨 STATUS: RED — {len(dangerous_approaches)} Potential Conjunctions Found!")
        df = pd.DataFrame([{
            "Name": item['name'],
            "ID": item['id'],
            "Closest Distance (km)": f"{item['distance_km']:.2f}",
            "Time of Approach (UTC)": item['time_utc']
        } for item in dangerous_approaches])
        st.dataframe(df, use_container_width=True)

        # Optional: 3D Visualization for first conjunction
        st.write("### 🪐 3D Visualization (first conjunction example)")
        first = dangerous_approaches[0]
        debris = next((s for s in all_satellites if s.model.satnum == first['id']), None)
        if debris:
            t_range_short = ts.utc(t0.utc_datetime() + np.arange(0, 120) / 1440)  # 2 hours
            target_path = target_sat.at(t_range_short).position.km
            debris_path = debris.at(t_range_short).position.km
            fig = go.Figure()
            fig.add_trace(go.Scatter3d(x=target_path[0], y=target_path[1], z=target_path[2],
                                       mode='lines', name=selected_name))
            fig.add_trace(go.Scatter3d(x=debris_path[0], y=debris_path[1], z=debris_path[2],
                                       mode='lines', name=first['name'], line=dict(dash='dot')))
            fig.update_layout(scene=dict(xaxis_title='X (km)', yaxis_title='Y (km)', zaxis_title='Z (km)'),
                              margin=dict(l=0, r=0, b=0, t=30),
                              height=600)
            st.plotly_chart(fig, use_container_width=True)

st.sidebar.header("📘 About")
st.sidebar.info(
    "This app uses the Skyfield library and live CelesTrak data to predict potential collisions "
    "(conjunctions) for key satellites within the next 24 hours."
)
