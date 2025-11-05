import streamlit as st
import numpy as np
import pandas as pd
import requests  # Make sure 'requests' is in requirements.txt
import time
import plotly.graph_objects as go # Make sure 'plotly' is in requirements.txt
from skyfield.api import load, EarthSatellite

# --- Streamlit Config ---
st.set_page_config(page_title="🛰️ Project Kuppai-Track", layout="wide")

# --- Load TLE Data (This is the fix) ---
def load_tle_data():
    ts = load.timescale()
    
    # --- === ITHU THAN ANTHA FIX === ---
    # Use the direct .txt file, it's more stable
    tle_url_active = 'https://celestrak.org/NORAD/elements/active.txt'
    st.write(f"Loading TLE data from: {tle_url_active}...")
    try:
        # Use 'requests' with a 15-second timeout
        tle_text = requests.get(tle_url_active, timeout=15).text
        
        # Now load the satellites from the text
        # We use .splitlines() because skyfield's load.tle_file expects a list of lines
        all_satellites = load.tle_file(tle_text.splitlines())
        
        st.write(f"✅ Loaded {len(all_satellites)} active satellites.")
        # Return the text AND the loaded objects
        return ts, all_satellites, tle_text
    
    except Exception as e:
        st.error(f"Error loading active satellites: {e}")
        # Return empty values
        return ts, [], ""
    # --- === END OF FIX === ---


# --- Cached Analysis (Your smart logic) ---
@st.cache_data(show_spinner=True)
def run_conjunction_analysis(ts_now_str, tle_text, target_id, target_name, threshold_km):
    ts = load.timescale()
    # Load satellites from the cached text
    all_satellites = load.tle_file(tle_text.splitlines())
    start_time = time.time()

    target_sat = next((sat for sat in all_satellites if sat.model.satnum == target_id), None)
    if not target_sat:
        return None, [], 0.0

    objects_to_check = [sat for sat in all_satellites if sat.model.satnum != target_id]
    dangerous_approaches = []

    # 24h timeline (1-minute resolution)
    # We create the time object from the string, so it's cacheable
    t0 = ts.from_utc_strftime(ts_now_str) 
    t_range = ts.utc(t0.utc_datetime() + np.arange(0, 1440) / 1440)
    target_pos = target_sat.at(t_range).position.km

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_objects = len(objects_to_check)

    for i, debris in enumerate(objects_to_check):
        debris_pos = debris.at(t_range).position.km
        distance_km = np.linalg.norm(target_pos - debris_pos, axis=0)
        min_distance = np.min(distance_km)

        if 0.01 < min_distance < threshold_km:
            min_index = np.argmin(distance_km)
            time_of_closest_approach = t_range[min_index]
            dangerous_approaches.append({
                "name": debris.name,
                "id": debris.model.satnum,
                "distance_km": min_distance,
                "time_utc": time_of_closest_approach.utc_strftime('%Y-%m-%d %H:%M:%S')
            })

        if (i + 1) % 100 == 0:
            progress_bar.progress((i + 1) / total_objects)
            status_text.text(f"Checked {i+1}/{total_objects} objects...")

    progress_bar.progress(1.0)
    status_text.text("✅ Analysis Complete!")

    total_time = time.time() - start_time
    dangerous_approaches.sort(key=lambda x: x['distance_km'])
    return target_sat, dangerous_approaches, total_time

# --- UI ---
st.title("🛰️ Project 'Kuppai-Track'")
st.markdown("A real-time conjunction alert system to track threats to our key satellites.")

st.sidebar.header("⚙️ Settings")
threshold_km = st.sidebar.slider("Alert Distance Threshold (km)", 10.0, 500.0, 100.0, 10.0)
st.sidebar.info("Adjust to control how close an object must be to trigger an alert.")

# Load Satellite Data
with st.spinner("Fetching satellite database from CelesTrak..."):
    ts, all_satellites, tle_text = load_tle_data() # tle_text is the new variable

if not all_satellites:
    st.error("❌ Failed to load satellite data. Please refresh.")
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

    # --- CACHE FIX ---
    # Pass a simple string for the time, so the cache works.
    # This key changes every 10 minutes, so we get fresh results
    # without breaking the cache every second.
    now = ts.now()
    time_key = f"{now.utc_strftime('%Y-%m-%d-%H')}:{now.utc_minute // 10}"
    # --- END CACHE FIX ---

    target_sat, dangerous_approaches, total_time = run_conjunction_analysis(
        now.utc_strftime(), tle_text, target_id_to_run, selected_name, threshold_km
    )

    if not target_sat:
        st.error(f"Target {selected_name} not found in TLE data.")
        st.stop()

    st.metric("⏱ Analysis Time (s)", f"{total_time:.2f}")
    st.metric("🛰 Objects Checked", len(all_satellites))

    # Results Display
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

        # 3D Orbit Visualization (optional)
        st.write("### 🪐 3D Visualization (first conjunction example)")
        first = dangerous_approaches[0]
        debris = next((s for s in all_satellites if s.model.satnum == first['id']), None)
        if debris:
            t_range_short = ts.utc(ts.now().utc_datetime() + np.arange(0, 120) / 1440)
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
    "for major satellites over the next 24 hours."
)
