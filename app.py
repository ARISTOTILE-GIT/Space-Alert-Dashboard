import streamlit as st
import numpy as np
from skyfield.api import load, EarthSatellite
import time
import pandas as pd

# ===============================
# 🚀 PROJECT: "KUPPAI-TRACK"
# Real-Time Satellite Conjunction Alert System
# ===============================

# --- Global Constants ---
ALERT_THRESHOLD_KM = 100.0  # Minimum approach distance threshold
CHECK_MINUTES = 24 * 60     # Number of minutes to check ahead

# --- Cached Data Loader ---
@st.cache_data
def load_tle_data():
    ts = load.timescale()
    tle_url_active = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
    print("Loading TLE data from CelesTrak...")
    try:
        all_satellites = load.tle_file(tle_url_active, reload=True)
        print(f"Loaded {len(all_satellites)} active satellites.")
        return ts, all_satellites
    except Exception as e:
        print(f"Error loading active satellites: {e}")
        return ts, []

# --- Core Function ---
def run_conjunction_analysis(ts, all_satellites, target_id, target_name):
    start_time = time.time()
    
    # 1. Find target satellite
    target_sat = next((sat for sat in all_satellites if sat.model.satnum == target_id), None)
    if not target_sat:
        st.error(f"Error: Could not find {target_name} (ID: {target_id}) in the loaded data.")
        return [], 0.0

    # 2. Exclude target itself
    objects_to_check = [sat for sat in all_satellites if sat.model.satnum != target_id]
    
    dangerous_approaches = []

    # 3. Time range setup
    t0 = ts.now()
    t_range = ts.utc(t0.utc.year, t0.utc.month, t0.utc.day, t0.utc.hour,
                     range(t0.utc.minute, t0.utc.minute + CHECK_MINUTES))

    # 4. Compute target orbit
    st.write(f"🛰️ Calculating path for **{target_name}**...")
    target_pos = target_sat.at(t_range).position.km

    # 5. Loop through other objects
    st.write(f"--- Starting Conjunction Analysis ({len(objects_to_check)} objects) ---")
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_objects = len(objects_to_check)
    for i, debris in enumerate(objects_to_check):
        try:
            debris_pos = debris.at(t_range).position.km
            raw_distance = target_pos - debris_pos
            distance_km = np.linalg.norm(raw_distance, axis=0)
            min_distance = np.min(distance_km)

            if 0.01 < min_distance < ALERT_THRESHOLD_KM:
                min_index = np.argmin(distance_km)
                time_of_closest_approach = t_range[min_index]
                result = {
                    "Name": debris.name,
                    "ID": debris.model.satnum,
                    "Closest Distance (km)": round(min_distance, 2),
                    "Time of Approach (UTC)": time_of_closest_approach.utc_strftime('%Y-%m-%d %H:%M:%S')
                }
                dangerous_approaches.append(result)
        except Exception:
            continue  # Skip any invalid satellites
        
        # Update progress every 200 objects
        if (i + 1) % 200 == 0 or i == total_objects - 1:
            percent_complete = (i + 1) / total_objects
            progress_bar.progress(percent_complete)
            status_text.text(f"Checked {i + 1} / {total_objects} objects...")

    progress_bar.progress(1.0)
    status_text.text("✅ Conjunction check complete!")

    end_time = time.time()
    total_time = end_time - start_time

    # Sort by closest distance
    dangerous_approaches.sort(key=lambda x: x["Closest Distance (km)"])
    return dangerous_approaches, total_time

# ===============================
# 🌍 STREAMLIT INTERFACE
# ===============================

st.title("🛰️ Project 'SAT-Track'")
st.markdown("### Real-Time Satellite Conjunction Alert System")
st.info("Tracks possible close approaches (conjunctions) between major satellites and other active space objects using Skyfield & CelesTrak data.")

# --- Load Data ---
with st.spinner("📡 Loading satellite database from CelesTrak (one-time only)..."):
    ts, all_satellites = load_tle_data()

if not all_satellites:
    st.error("Failed to load satellite data. Please refresh or check your internet connection.")
    st.stop()

st.success(f"✅ Successfully loaded {len(all_satellites)} active satellites!")

# --- Show All Satellites (Optional) ---
if st.checkbox("Show all loaded satellites"):
    sat_info = [{"Name": sat.name, "ID": sat.model.satnum} for sat in all_satellites]
    st.dataframe(pd.DataFrame(sat_info))

# --- Satellite Selection ---
st.subheader("🎯 Select Your Target Satellite")
TARGETS = {
    "International Space Station (ISS)": 25544,
    "Hubble Space Telescope (HST)": 20580,
    "Starlink-4328": 51094
}
selected_name = st.selectbox("Select a target to track:", TARGETS.keys())
target_id_to_run = TARGETS[selected_name]

# --- Run Analysis ---
if st.button(f"🚀 Run Analysis for {selected_name}"):
    st.write("---")
    st.header(f"📊 Analysis Results for {selected_name}")

    dangerous_approaches, total_time = run_conjunction_analysis(ts, all_satellites, target_id_to_run, selected_name)
    st.info(f"⏱️ Computation Time: {total_time:.2f} seconds")

    if not dangerous_approaches:
        st.success("✅ **STATUS: GREEN** – No nearby objects detected.")
        st.write(f"No objects predicted to come within **{ALERT_THRESHOLD_KM} km** of {selected_name} in the next 24 hours.")
    else:
        st.error(f"🚨 **STATUS: RED** – {len(dangerous_approaches)} Potential Conjunction(s) Found!")
        df = pd.DataFrame(dangerous_approaches)
        st.dataframe(df)

        # Download Button
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download Results as CSV",
            data=csv,
            file_name=f"conjunctions_{selected_name.replace(' ', '_')}.csv",
            mime="text/csv"
        )

# --- Sidebar Info ---
st.sidebar.header("ℹ️ About")
st.sidebar.info("""
**Project 'Kuppai-Track'**
- Built with [Skyfield](https://rhodesmill.org/skyfield/) for orbital calculations.  
- Data Source: [CelesTrak Active Satellites](https://celestrak.org/NORAD/elements/).  
- Developed to analyze potential conjunctions and alert for space debris risks.
""")