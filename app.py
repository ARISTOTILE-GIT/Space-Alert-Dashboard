import streamlit as st
import numpy as np
import pandas as pd
import requests 
import time
import plotly.graph_objects as go 
from skyfield.api import load, EarthSatellite
from datetime import datetime, timezone


st.set_page_config(page_title="🛰️ Project Space Debris Alert Dashboard", layout="wide")

def load_backup_data():
    st.write("Loading local backup data (`active.txt`)...")
    try:
        
        all_satellites = load.tle_file("active.txt")
        
        with open("active.txt", "r") as f:
            tle_text = f.read()
        st.write(f"✅ Backup data loaded ({len(all_satellites)} objects).")
        return all_satellites, tle_text
    except Exception as e:
        st.error(f"❌ Error loading local 'active.txt' file. Make sure it's uploaded to GitHub! {e}")
        return [], ""


def download_live_data():
    ts = load.timescale()
    tle_url_active = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
    st.write(f"📡 Attempting to download LIVE data from: {tle_url_active}...")
    try:
       
        tle_text = requests.get(tle_url_active, timeout=20).text
        
        all_satellites = load.tle_file(tle_text.splitlines())
        st.success(f"✅ Live data loaded! Found {len(all_satellites)} satellites.")
        
        return all_satellites, tle_text
    except Exception as e:
        st.error(f"❌ Live data download failed (Timeout/Error). Using backup. Error: {e}")
        return None, None 



@st.cache_data(show_spinner=True)
def run_conjunction_analysis(ts_now_timestamp, tle_text, target_id, target_name, threshold_km):
    ts = load.timescale()
    
    
    with open("cache_tle.txt", "w") as f:
        f.write(tle_text)
    all_satellites = load.tle_file("cache_tle.txt")

    start_time = time.time()

    target_sat = next((sat for sat in all_satellites if sat.model.satnum == target_id), None)
    
    if not target_sat:
        return [], 0.0, 0 

    objects_to_check = [sat for sat in all_satellites if sat.model.satnum != target_id]
    dangerous_approaches = []
    
    total_objects = len(objects_to_check)


    dt = datetime.utcfromtimestamp(ts_now_timestamp).replace(tzinfo=timezone.utc)
    t0 = ts.from_datetime(dt)
    
    t_range = t0 + (np.arange(0, 1440) / 1440)
    target_pos = target_sat.at(t_range).position.km

    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text(f"Checking 0/{total_objects} objects...")

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
    status_text.text(f"✅ Analysis Complete! Checked {total_objects} objects.")

    total_time = time.time() - start_time
    dangerous_approaches.sort(key=lambda x: x['distance_km'])
    

    return dangerous_approaches, total_time, total_objects


st.title("🛰️ Project 'Space Debris Alert Dashboard'")
st.markdown("A real-time conjunction alert system to track threats to our key satellites.")


ts = load.timescale()


if 'data_loaded' not in st.session_state:
    
    all_sats, tle = load_backup_data()
    st.session_state.all_satellites = all_sats
    st.session_state.tle_text = tle
    st.session_state.data_source = "Backup"
    st.session_state.data_loaded = True


st.sidebar.header("⚙️ Settings")
threshold_km = st.sidebar.slider("Alert Distance Threshold (km)", 10.0, 500.0, 100.0, 10.0)
st.sidebar.info("Adjust to control how close an object must be to trigger an alert.")

st.sidebar.header("📘 About")
st.sidebar.info(
    "This app uses the Skyfield library and live CelesTrak data to predict potential collisions "
    "for major satellites over the next 24 hours."
)

st.sidebar.header("🛰️ Data Source")

if st.sidebar.button("🔄 Try Download Live Data"):
    new_sats, new_text = download_live_data()
    if new_sats:
        st.session_state.all_satellites = new_sats
        st.session_state.tle_text = new_text
        st.session_state.data_source = "Live"
        st.rerun()


if st.session_state.data_source == "Live":
    st.sidebar.success("✅ Using LIVE Data")
else:
    st.sidebar.warning("⚠️ Using LOCAL BACKUP Data (Data might be old)")



if not st.session_state.all_satellites:
    st.error("Fatal Error: Could not load backup data. App cannot start.")
    st.stop()


st.subheader("🎯 Select Target Satellite")
TARGETS = {
    "International Space Station (ISS)": 25544,
    "Hubble Space Telescope (HST)": 20580,
    "Starlink-4328": 51094
}
selected_name = st.selectbox("Choose a satellite to analyze:", TARGETS.keys())
target_id_to_run = TARGETS[selected_name]


if st.button(f"🚀 Run Analysis for {selected_name}"):
    st.write("---")
    st.header(f"Results for {selected_name}")
    
    now_ts = datetime.utcnow().timestamp()

    tle_text_to_use = st.session_state.tle_text
    
    dangerous_approaches, total_time, objects_checked = run_conjunction_analysis(
        now_ts, tle_text_to_use, target_id_to_run, selected_name, threshold_km
    )

   
    if objects_checked == 0 and not dangerous_approaches:
        st.error(f"Target {selected_name} not found in the TLE data.")
        st.stop()

  
    col1, col2, col3 = st.columns(3)
    col1.metric("⏱ Analysis Time (s)", f"{total_time:.2f}")
    col2.metric("🛰️ Objects Checked", f"{objects_checked:,}") # Add comma for thousands
    col3.metric("🚨 Alerts Found", len(dangerous_approaches))



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
        st.subheader("🪐 3D Visualization (Closest Approach)")
        
        # Re-find the target_sat object here (it's fast)
        target_sat = next((s for s in st.session_state.all_satellites if s.model.satnum == target_id_to_run), None)

        first = dangerous_approaches[0]
        debris = next((s for s in st.session_state.all_satellites if s.model.satnum == first['id']), None)
        
        if debris and target_sat: # Check if both were found
            st.write(f"Plotting orbit for **{selected_name}** vs. **{first['name']}**...")
            
            # Use the ts.now() Skyfield object directly
            t_range_short = ts.now() + (np.arange(0, 120) / 1440)

            target_path = target_sat.at(t_range_short).position.km
            debris_path = debris.at(t_range_short).position.km

            fig = go.Figure()
            fig.add_trace(go.Scatter3d(x=target_path[0], y=target_path[1], z=target_path[2],
                                        mode='lines', name=selected_name, line=dict(width=4)))
            fig.add_trace(go.Scatter3d(x=debris_path[0], y=debris_path[1], z=debris_path[2],
                                        mode='lines', name=first['name'], line=dict(dash='dot', width=4)))
            
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
                title=f"Closest Approach: {first['name']} ({first['distance_km']:.2f} km)",
                scene=dict(
                    xaxis_title='X (km)', yaxis_title='Y (km)', zaxis_title='Z (km)',
                    aspectmode='data' 
                ),
                margin=dict(l=0, r=0, b=0, t=40),
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)

        st.write("---") 
        st.subheader("⚠️ Insights & Recommendation")

        closest_object = dangerous_approaches[0]
        closest_dist = float(closest_object['distance_km'])
        closest_name = closest_object['name']

        if closest_dist < 25:
            st.warning(f"**Insight:** The closest object, **{closest_name}**, is predicted to pass within **{closest_dist:.2f} km**. This is a **HIGH-RISK** conjunction.")
            st.info(f"**Recommendation:** A **Debris Avoidance Maneuver (DAM)** is highly recommended for the **{selected_name}** to ensure a safe passing distance.")
        elif closest_dist < 50:
            st.warning(f"**Insight:** The closest object, **{closest_name}**, is predicted to pass within **{closest_dist:.2f} km**. This is a **MEDIUM-RISK** event.")
            st.info(f"**Recommendation:** This conjunction requires close monitoring. Be prepared for a possible maneuver if the orbit prediction changes.")
        else:
            st.info(f"**Insight:** While multiple objects are within the {threshold_km} km threshold, the closest object ({closest_name} at {closest_dist:.2f} km) is not an immediate collision threat.")
            st.info(f"**Recommendation:** No immediate action required. Continue routine monitoring.")
