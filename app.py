# 3D plot code mudinja odane...
        
        st.write("---") # Oru line pottu pirikalam
        st.subheader("⚠️ Insights & Recommendation")

        # Get the closest object from the list
        closest_object = dangerous_approaches[0]
        closest_dist = float(closest_object['distance_km'])
        closest_name = closest_object['name']

        # Oru simple logic vechi conclusion sollalam
        if closest_dist < 25:
            st.warning(f"**Insight:** The closest object, **{closest_name}**, is predicted to pass within **{closest_dist:.2f} km**. This is a **HIGH-RISK** conjunction.")
            st.info(f"**Recommendation:** A **Debris Avoidance Maneuver (DAM)** is highly recommended for the **{selected_name}** to ensure a safe passing distance.")
        elif closest_dist < 50:
            st.warning(f"**Insight:** The closest object, **{closest_name}**, is predicted to pass within **{closest_dist:.2f} km**. This is a **MEDIUM-RISK** event.")
            st.info(f"**Recommendation:** This conjunction requires close monitoring. Be prepared for a possible maneuver if the orbit prediction changes.")
        else:
            st.info(f"**Insight:** While multiple objects are within the {threshold_km} km threshold, the closest object ({closest_name} at {closest_dist:.2f} km) is not an immediate collision threat.")
            st.info(f"**Recommendation:** No immediate action required. Continue routine monitoring.")
