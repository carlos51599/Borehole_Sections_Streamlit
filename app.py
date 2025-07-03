# --- Listen for select_bh event and draw a tiny circle to select the borehole ---
# This must be placed after all imports and after loca_df is defined


def setup_bh_circle_event_bridge(loca_df):
    import streamlit.components.v1 as components
    import json
    from map_utils import filter_selection_by_shape

    components.html(
        """
        <script>
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'select_bh') {
                const lat = event.data.lat;
                const lon = event.data.lon;
                const payload = JSON.stringify({lat: lat, lon: lon});
                window.parent.postMessage({type: 'set_bh_circle', payload: payload}, '*');
                // Set a hidden input for Streamlit to pick up
                const input = window.parent.document.querySelector('input[data-testid=\"stTextInput\"]');
                if (input) { input.value = payload; input.dispatchEvent(new Event('input', {bubbles: true})); }
            }
        });
        </script>
        """,
        height=0,
    )

    import streamlit as st

    bh_circle = st.text_input(
        "", value="", key="bh_circle_input", label_visibility="collapsed"
    )
    if bh_circle:
        try:
            coords = json.loads(bh_circle)
            lat, lon = coords["lat"], coords["lon"]
            # Draw a tiny circle as a selection shape (for map_render.py to display)
            # Remove previous drawn shapes to ensure only one circle is shown
            st.session_state["drawn_shapes"] = []
            st.session_state["last_drawn_shape"] = {
                "type": "Circle",
                "coordinates": [lon, lat],
                "radius": 0.5,  # meters, as small as possible
            }
            st.session_state["last_shape_hash"] = f"circle_{lat}_{lon}"
            # Filter selection by this tiny circle
            selected = filter_selection_by_shape(
                st.session_state["last_drawn_shape"], loca_df
            )
            # If multiple boreholes are selected, pick the closest one to the circle origin
            if selected is not None and not selected.empty:
                if len(selected) > 1:
                    import numpy as np

                    dists = np.sqrt(
                        (selected["lat"] - lat) ** 2 + (selected["lon"] - lon) ** 2
                    )
                    closest_idx = dists.idxmin()
                    selected = selected.loc[[closest_idx]]
            st.session_state["selected_boreholes"] = selected
            # Do not rerun here; let the map update naturally so the circle is visible
        except Exception:
            pass


import streamlit as st
import pandas as pd
from io import BytesIO
from pyproj import Transformer
from streamlit_folium import st_folium
from data_loader import load_all_loca_data
from map_utils import filter_selection_by_shape
from borehole_selection import render_checkbox_grid
from section_logic import generate_section_plot
from map_render import render_map
from borehole_log import render_borehole_log

st.set_page_config(layout="wide")

if "ags_files" not in st.session_state:
    uploaded_files = st.file_uploader(
        "Upload one or more AGS files",
        type=["ags"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        st.session_state["ags_files"] = [
            (f.name, f.getvalue().decode("utf-8")) for f in uploaded_files
        ]
    else:
        st.info("Please upload one or more AGS files to continue.")
        st.stop()

loca_df, filename_map = load_all_loca_data(st.session_state["ags_files"])


if loca_df.empty:
    st.warning(
        "No valid location data found (LOCA_NATE or LOCA_NATN missing or invalid)."
    )
    st.stop()

transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy=True)
loca_df[["lat", "lon"]] = loca_df.apply(
    lambda r: pd.Series(transformer.transform(r["LOCA_NATE"], r["LOCA_NATN"])[::-1]),
    axis=1,
)

if "drawn_shapes" not in st.session_state:
    st.session_state["drawn_shapes"] = []

if "last_shape_hash" not in st.session_state:
    st.session_state["last_shape_hash"] = None

if "selected_boreholes" not in st.session_state:
    st.session_state["selected_boreholes"] = pd.DataFrame()


st.subheader("Select Boreholes on Map")


# --- Layout: Map and Plot Button Side by Side ---
cols = st.columns([2, 1])
with cols[0]:
    m = render_map(loca_df, transformer, st.session_state["selected_boreholes"])
    map_data = st_folium(
        m, height=600, width=None, key=st.session_state.get("last_shape_hash")
    )

    # Capture marker click and update session state
    if map_data and map_data.get("last_object_clicked"):
        props = map_data["last_object_clicked"].get("properties", {})
        if "LOCA_ID" in props:
            # Store as a DataFrame for compatibility with rest of app
            selected_row = loca_df[loca_df["LOCA_ID"] == props["LOCA_ID"]]
            st.session_state["selected_boreholes"] = selected_row


with cols[1]:
    selected = st.session_state.get("selected_boreholes", pd.DataFrame())
    if not selected.empty and len(selected) == 1:
        if st.button("Create Plot"):
            st.session_state["show_log_plot"] = True
    elif not selected.empty and len(selected) > 1:
        st.info("Select only one borehole to create a log plot.")
    else:
        st.info("Select a borehole marker on the map.")

# --- Show borehole log plot below columns if requested ---
if st.session_state.get("show_log_plot"):
    selected = st.session_state.get("selected_boreholes", pd.DataFrame())
    if not selected.empty and len(selected) == 1:
        bh_id = selected.iloc[0]["LOCA_ID"]
        render_borehole_log(
            bh_id,
            filename_map,
            st.session_state["ags_files"],
            show_labels=st.session_state.get("show_labels", True),
            fig_height=4,
        )
    st.session_state["show_log_plot"] = False


# Only update selection from drawn shapes, not marker clicks
if map_data and map_data.get("last_active_drawing"):
    geom = map_data["last_active_drawing"]["geometry"]
    geom_hash = str(geom)
    if st.session_state["last_shape_hash"] != geom_hash:
        selected = filter_selection_by_shape(geom, loca_df)
        st.session_state["selected_boreholes"] = selected
        st.session_state["last_shape_hash"] = geom_hash
        st.session_state["last_drawn_shape"] = geom
        if map_data.get("center"):
            center = map_data["center"]
            if isinstance(center, dict) and "lat" in center and "lng" in center:
                st.session_state["map_center"] = [center["lat"], center["lng"]]
            else:
                st.session_state["map_center"] = center
        if map_data.get("zoom"):
            st.session_state["map_zoom"] = map_data["zoom"]
        st.rerun()
