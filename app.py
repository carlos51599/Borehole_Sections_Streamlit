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
from streamlit_folium import st_folium
from data_loader import load_all_loca_data
from map_utils import filter_selection_by_shape
from borehole_selection import render_checkbox_grid
from section_logic import generate_section_plot
from map_render import render_map
from borehole_log import render_borehole_log
from pyproj import Transformer
from config import MAP_HEIGHT, MAP_WIDTH, LOG_FIG_HEIGHT, LOG_FIG_WIDTH

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


# --- Caching for expensive data loading and transformation ---
@st.cache_data(show_spinner=False)
def load_all_loca_data_cached(ags_files):
    return load_all_loca_data(ags_files)


@st.cache_data(show_spinner=False)
def transform_loca_df(loca_df):
    transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy=True)
    loca_df = loca_df.copy()
    loca_df[["lat", "lon"]] = loca_df.apply(
        lambda r: pd.Series(
            transformer.transform(r["LOCA_NATE"], r["LOCA_NATN"])[::-1]
        ),
        axis=1,
    )
    return loca_df


loca_df, filename_map = load_all_loca_data_cached(st.session_state["ags_files"])
loca_df = transform_loca_df(loca_df)

if loca_df.empty:
    st.warning(
        "No valid location data found (LOCA_NATE or LOCA_NATN missing or invalid)."
    )
    st.stop()

if "drawn_shapes" not in st.session_state:
    st.session_state["drawn_shapes"] = []

if "last_shape_hash" not in st.session_state:
    st.session_state["last_shape_hash"] = None


# --- Session state initialization ---
if "selected_boreholes" not in st.session_state:
    st.session_state["selected_boreholes"] = pd.DataFrame()
if "show_log_plot" not in st.session_state:
    st.session_state["show_log_plot"] = False
if "last_plotted_selection_hash" not in st.session_state:
    st.session_state["last_plotted_selection_hash"] = None

st.subheader("Select Boreholes on Map")


# Compute a hash for the current selection (for change detection)
def get_selection_hash(selected):
    if selected is None or selected.empty:
        return None
    # Use LOCA_IDs and their order for hash
    return hash(tuple(selected["LOCA_ID"].tolist()))


current_selection = st.session_state["selected_boreholes"]
current_selection_hash = get_selection_hash(current_selection)

# Add Create Plot button under the map title
button_disabled = (
    current_selection is None
    or current_selection.empty
    or current_selection_hash == st.session_state["last_plotted_selection_hash"]
)
if st.button("Create Plot from Selection", disabled=button_disabled):
    st.session_state["show_log_plot"] = True
    st.session_state["last_plotted_selection_hash"] = current_selection_hash


# --- Map size control ---
transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy=True)
m = render_map(loca_df, transformer, st.session_state["selected_boreholes"])
map_data = st_folium(
    m, height=MAP_HEIGHT, width=MAP_WIDTH, key=st.session_state.get("last_shape_hash")
)

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

# --- Show log plot when popup is clicked (native Streamlit-Folium) ---
if map_data and map_data.get("last_object_clicked_popup"):
    popup_text = map_data["last_object_clicked_popup"]
    # Extract LOCA_ID as the first sequence of non-space characters (including dashes)
    loca_id = popup_text.strip().split()[0]
    selected_row = loca_df[loca_df["LOCA_ID"] == loca_id]
    if not selected_row.empty:
        st.session_state["selected_boreholes"] = selected_row
        st.session_state["last_drawn_shape"] = {}
        st.session_state["last_shape_hash"] = f"loglink_{loca_id}"
        st.session_state["show_log_plot"] = True
        st.rerun()

# --- Centralized plot sizing and single "Labels" checkbox ---

selected = st.session_state["selected_boreholes"]
if selected is not None and not selected.empty:
    st.markdown("**Selected Boreholes:**")
    filtered_ids = render_checkbox_grid(selected)

    # Divider below checkboxes
    st.markdown(
        '<hr style="margin: 0.5em 0 1em 0; border: none; border-top: 1px solid #bbb;">',
        unsafe_allow_html=True,
    )

    if not filtered_ids:
        st.warning("No boreholes selected. Please check at least one borehole.")
    else:
        # Only one "Labels" checkbox, always present if any selection
        if "show_labels" not in st.session_state:
            st.session_state["show_labels"] = True
        show_labels = st.checkbox(
            "Labels",
            value=st.session_state["show_labels"],
            help="Show/hide GEOL_LEG labels on plots.",
            key="labels_checkbox",
        )
        st.session_state["show_labels"] = show_labels

        # Plot if: (1) user pressed button for this selection, (2) plot options changed for current selection, or (3) restoring last plot after rerun
        plot_now = False
        if (
            st.session_state.get("show_log_plot", False)
            and current_selection_hash
            == st.session_state["last_plotted_selection_hash"]
        ) or (
            current_selection_hash == st.session_state["last_plotted_selection_hash"]
            and st.session_state.get("last_plot_options", None) != show_labels
        ):
            plot_now = True
            # Save last plot info for persistence
            st.session_state["last_plot_data"] = {
                "selection_hash": current_selection_hash,
                "plot_options": show_labels,
                "plot_type": "log" if len(filtered_ids) == 1 else "section",
                "filtered_ids": filtered_ids,
            }
        # Restore last plot if selection and options match
        elif (
            st.session_state.get("last_plot_data")
            and st.session_state["last_plot_data"].get("selection_hash")
            == current_selection_hash
            and st.session_state["last_plot_data"].get("plot_options") == show_labels
        ):
            plot_now = True
            filtered_ids = st.session_state["last_plot_data"]["filtered_ids"]
        if plot_now:
            st.session_state["last_plot_options"] = show_labels
            if len(filtered_ids) == 1:
                render_borehole_log(
                    filtered_ids[0],
                    filename_map,
                    st.session_state["ags_files"],
                    show_labels=show_labels,
                    fig_height=LOG_FIG_HEIGHT,
                    fig_width=LOG_FIG_WIDTH,
                )
            elif len(filtered_ids) > 1:
                section_fig = generate_section_plot(
                    filtered_ids,
                    selected,
                    filename_map,
                    show_labels=show_labels,
                )
                if section_fig:
                    buffer = BytesIO()
                    section_fig.savefig(buffer, format="png", bbox_inches="tight")
                    buffer.seek(0)
                    st.download_button(
                        label="Download Section Plot",
                        data=buffer,
                        file_name="section_plot.png",
                        mime="image/png",
                        use_container_width=True,
                    )
            st.session_state["show_log_plot"] = False
        elif current_selection_hash != st.session_state["last_plotted_selection_hash"]:
            # Only show info if no plot has been created for this selection
            if not st.session_state.get("last_plot_options", None):
                st.info("Click 'Create Plot from Selection' to generate a plot.")
        # Do not show any info message if a plot is already shown or just updated
else:
    st.info("Draw a rectangle or polygon to select boreholes.")


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
