import streamlit as st
import numpy as np
from skyfield.api import load, EarthSatellite
import time
import pandas as pd # For better table display

# --- === ITHU THAN PUTHIYA FIX === ---
# Define the threshold here, at the top, so everyone can see it
ALERT_THRESHOLD_KM = 100.0
# --- === END OF FIX === ---


# --- Caching Data Loading ---
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

# --- Namma Core Logic ah oru Function ah maathurom ---
def run_conjunction_analysis(ts, all_satellites, target_id, target_name):
    start_time = time.time()
    
    # 1. Select Target
    target_sat = None
    for sat in all_satellites:
        if sat.model.satnum == target_id:
            target_sat = sat
            break

    if not target_sat:
        st.error(f"Error: Could not find {target_name} (ID: {target_id}) in the loaded data.")
        return [], 0.0

    # 2. Create check list
    objects_to_check = [sat for sat in all_satellites if sat.model.satnum != target_id]
    
    # We don't need to define ALERT_THRESHOLD_KM here anymore
    dangerous_approaches = []

    # 3. Set time range
    t0 = ts.now()
    minutes_in_day = 24 * 60
    t_range = ts.utc(t0.utc.year, t0.utc.month, t0.utc.day, t0.utc.hour, range(t0.utc.minute, t0.utc.minute + minutes_in_day))
    
    # 4. Calculate Target's path
    st.write(f"Calculating path for {target_name}...")
    target_pos = target_sat.at(t_range).position.km
    
    st.write(f"--- Starting Conjunction Analysis (Checking {len(objects_to_check)} objects) ---")
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 5. Loop through ALL other objects
    total_objects = len(objects_to_check)
    for i, debris in enumerate(objects_to_check):
        
        debris_pos = debris.at(t_range).position.km
        raw_distance = target_pos - debris_pos
        distance_km = np.linalg.norm(raw_distance, axis=0) 
        min_distance = np.min(distance_km)
        
        # Check threshold (it will use the global variable)
        if min_distance < ALERT_THRESHOLD_KM:
            if min_distance < 0.01:
                continue
            else:
                min_index = np.argmin(distance_km)
                time_of_closest_approach = t_range[min_index]
                
                result = {
                    "name": debris.name,
                    "id": debris.model.satnum,
                    "distance_km": min_distance,
                    "time_utc": time_of_closest_approach.utc_strftime('%Y-%m-%d %H:%M:%S')
                }
                dangerous_approaches.append(result)
        
        if (i+1) % 100 == 0: 
            percent_complete = (i+1) / total_objects
            progress_bar.progress(percent_complete)
            status_text.text(f"Checked {i+1} / {total_objects} objects...")

    progress_bar.progress(1.0)
    status_text.text(f"Checked {total_objects} / {total_objects} objects... Complete!")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    dangerous_approaches.sort(key=lambda x: x['distance_km'])
    
    return dangerous_approaches, total_time

# --- Streamlit UI (Ithu than namma Web App) ---

# 1. Title
st.title("🛰️ Project 'Kuppai-Track'")
st.markdown("A real-time conjunction alert system to track threats to our key satellites.")

# 2. Load Data
with st.spinner("Loading satellite database from CelesTrak... (One time only)"):
    ts, all_satellites = load_tle_data()

if all_satellites:
    st.success(f"Successfully loaded {len(all_satellites)} active objects!")
else:
    st.error("Failed to load satellite data from CelesTrak. Please refresh the app.")
    st.stop() # Stop the app if data loading fails

# 3. User Selection
st.subheader("Select Your Target Satellite")

# Create a dictionary for targets
TARGETS = {
    "International Space Station (ISS)": 25544,
    "Hubble Space Telescope (HST)": 20580,
    "Starlink-4328": 51094
}

selected_name = st.selectbox("Select a target to track:", TARGETS.keys())
target_id_to_run = TARGETS[selected_name]

# 4. Run Button
if st.button(f"🚀 Run Analysis for {selected_name}"):
    st.write("---")
    st.header(f"Analysis Results for {selected_name}")
    
    dangerous_approaches, total_time = run_conjunction_analysis(ts, all_satellites, target_id_to_run, selected_name)
    
    st.write(f"--- Analysis Complete in {total_time:.2f} seconds ---")

    # 5. Display Dashboard
    if not dangerous_approaches:
        st.success(f"✅ STATUS: GREEN")
        # Intha line ippo work aagum, yenna 'ALERT_THRESHOLD_KM' global la irukku
        st.write(f"No objects predicted to come within {ALERT_THRESHOLD_KM} km of {selected_name} in the next 24 hours.")
    else:
        st.error(f"🚨 STATUS: RED - {len(dangerous_approaches)} Potential Conjunctions Found!")
        
        results_data = []
        for item in dangerous_approaches:
            results_data.append({
                "Name": item['name'],
                "ID": item['id'],
                "Closest Distance (km)": f"{item['distance_km']:.2f}",
                "Time of Approach (UTC)": item['time_utc']
            })
        
        df = pd.DataFrame(results_data)
        st.dataframe(df)

st.sidebar.header("About")
st.sidebar.info("This app uses the Skyfield library to calculate orbits and predict potential collisions (conjunctions) for key space assets.")
