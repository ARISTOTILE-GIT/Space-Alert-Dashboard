# 🛰️ Space Debris Alert Dashboard

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://space-alert-dashboard-try1.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![NumPy](https://img.shields.io/badge/NumPy-4D77CF?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org/)
[![Pandas](https://img.shields.io/badge/Pandas-130654?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/python/)
[![Skyfield](https://img.shields.io/badge/Skyfield-007849?style=for-the-badge)](https://rhodesmill.org/skyfield/)

A Streamlit web app that calculates and visualizes real-time collision risks for key satellites (like the ISS and HST) from 13,000+ other space objects and debris.

## 🚀 Live App

You can run the live application here:

👉 **[Try it Live on Streamlit!]](https://space-alert-dashboard-try1.streamlit.app/)** 👈 

## 📸 App Workings

Here is a look at the dashboard in action, showing a "RED ALERT" status and the list of potential threats.

![Space Debris Alert Dashboard Screenshot 1](https://raw.githubusercontent.com/ARISTOTILE-GIT/Space-Alert-Dashboard/main/demo-screenshot-1.png)

When a threat is found, the app also generates an interactive 3D plot to visualize the orbits of the target and the approaching object.

![Space Debris Alert Dashboard Screenshot 2](https://raw.githubusercontent.com/ARISTOTILE-GIT/Space-Alert-Dashboard/main/demo-screenshot-2.png)

---

## 🧐 About The Project

The orbit around Earth is increasingly crowded. With thousands of active satellites and tens of thousands of debris objects (like old rocket parts and dead satellites), the risk of collision is a serious problem. A single collision could create a cascade of new debris, making space unusable.

This project, **"Space Debris Alert Dashboard"**, is a simple but powerful "Space Traffic Alert" system.

It allows a user to select a high-value satellite (like the **International Space Station**) and scans the next 24 hours for any potential conjunctions (close approaches) with over 13,000 other active objects. If any object is predicted to come within a user-defined threshold (e.g., 100 km), it flags a **RED ALERT**, provides a list of the threats, and offers a clear recommendation.

## ✨ Key Features

* **Hybrid Data Model:** Loads a reliable local backup (`active.txt`) on startup and provides a button to fetch **live TLE data** from CelesTrak. This makes the app **100% reliable**, even if the live data server is down.
* **Physics-Based Analysis:** Uses the `skyfield` library to perform high-accuracy physics calculations, predicting the 24-hour orbital path (at 1-minute intervals) for all 13,000+ objects.
* **High-Speed Comparison:** Leverages `NumPy` for vectorized calculations to find the minimum distance between the target and every other object in seconds.
* **Dynamic Dashboard:**
    * Select from multiple targets (ISS, HST, Starlink).
    * Set a custom **Alert Threshold** (10km to 500km) with a simple slider.
    * View all potential threats in a clean, sortable table.
* **3D Visualization:** Uses `Plotly` to generate an interactive 3D plot of the target's orbit and the closest approaching object's orbit.
* **Clear Recommendations:** Provides simple, actionable insights (e.g., "High-Risk: Maneuver Recommended") based on the closest approach distance.

---

## 🔧 How It Works

1.  **Data Load:** On startup, the app loads a local `active.txt` TLE file (bundled with the repo) using `st.session_state`. This ensures the app **always works**.
2.  **Live Data (Optional):** A button in the sidebar ("🔄 Try Download Live Data") uses the `requests` library to fetch the latest TLE data from CelesTrak. If successful, it updates the session state; if it fails (e.g., timeout), it safely falls back to the local data.
3.  **User Selection:** The user selects a target satellite (e.g., ISS) and an alert threshold (e.g., 100 km).
4.  **Analysis (`@st.cache_data`):** When the "Run Analysis" button is clicked:
    * The core logic is wrapped in a cached function. To make it cache-friendly, we pass a simple `timestamp` and the raw `tle_text` as arguments.
    * Inside the function, `skyfield` loads the TLEs.
    * It calculates the 24-hour position vector for the target.
    * It loops through all 13,000+ other objects, calculates their paths, and uses `np.linalg.norm` to find the minimum distance.
    * It returns a simple list of "alert" dictionaries, which is cacheable.
5.  **Display Results:** The app displays the metrics (time, objects checked) and the "RED ALERT" table (using `pandas`).
6.  **Visualize:** If alerts are found, it takes the #1 threat, re-finds its satellite object (this part isn't cached), and plots its path against the target's path using `plotly`.

---

## 💻 Tech Stack

| Component | Technology |
| ----- | ----- |
| **Core Language** | Python |
| **Orbital Mechanics** | Skyfield |
| **Web App & UI** | Streamlit |
| **Data Visualization** | Plotly |
| **Numerical Computing** | NumPy |
| **Data Handling** | Pandas |
| **Live Data Fetching** | Requests |
| **Deployment** | Streamlit Cloud |

---

## 🚀 How to Run Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/ARISTOTILE-GIT/Space-Alert-Dashboard.git](https://github.com/ARISTOTILE-GIT/Space-Alert-Dashboard.git)
    cd Space-Alert-Dashboard
    ```

2.  **Create a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install the requirements:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the app:**
    ```bash
    streamlit run app.py
    ```

---

## 💡 Project Journey: The "AI-to-Physics" Pivot

This project started very differently. The initial goal was to use a **Deep Learning (LSTM) model** to *predict* a satellite's future path based on its past data.

We successfully built this model, but the results were a "successful failure." The model trained, but the **prediction error was over 9,000 km!**

**Why?** The orbital mechanics are too complex, and the 1-hour interval data was not enough for the model to learn the 90-minute orbit of the ISS.

Instead of trying to fix a flawed premise, we **pivoted**. We replaced the entire "AI" prediction model with a 100% accurate **physics-based calculation engine** using the `skyfield` library. This new approach was:
* **Infinitely more accurate** (0km error vs 9,000km error).
* **Faster** to compute.
* **More reliable** for a real-world safety application.

This project is a great example of choosing the right tool for the job and recognizing that a physics-based model is far superior to a "black box" AI model for a problem that is already governed by an exact set of physical laws.

---

## 🙏 Acknowledgements

This project would not be possible without the foundational work and publicly available TLE data provided by **Dr. T.S. Kelso** and **[CelesTrak](https://celestrak.org/)**.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
