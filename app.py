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

# --- Custom JS event handler for log link ---
st.markdown(
    """
    <script>
    window.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'show_log') {
            window.parent.postMessage(event.data, '*');
            window.dispatchEvent(new CustomEvent('streamlit_bh_log', {detail: event.data.loca_id}));
        }
    });
    </script>
    """,
    unsafe_allow_html=True,
)

m = render_map(loca_df, transformer, st.session_state["selected_boreholes"])
map_data = st_folium(
    m, height=600, width=None, key=st.session_state.get("last_shape_hash")
)

# --- Listen for log event and update session state ---
log_placeholder = st.empty()
if "show_log_loca_id" not in st.session_state:
    st.session_state["show_log_loca_id"] = None

log_js = """
<script>
window.addEventListener('streamlit_bh_log', function(e) {
    const loca_id = e.detail;
    if (window.parent) {
        const streamlitDoc = window.parent.document;
        const input = streamlitDoc.querySelector('input[data-testid="stTextInput"]');
        if (input) { input.value = loca_id; }
    }
    window.parent.postMessage({type: 'streamlit_set_log', loca_id: loca_id}, '*');
    window.location.hash = '#show_log_' + loca_id;
    window.dispatchEvent(new CustomEvent('streamlit_set_log', {detail: loca_id}));
});
</script>
"""
st.markdown(log_js, unsafe_allow_html=True)

import streamlit.components.v1 as components

components.html(
    """<script>
window.addEventListener('streamlit_set_log', function(e) {
    const loca_id = e.detail;
    window.parent.postMessage({type: 'set_log', loca_id: loca_id}, '*');
});
</script>""",
    height=0,
)

if map_data and map_data.get("last_object_clicked_tooltip"):
    # This is a fallback for folium click events
    clicked = map_data["last_object_clicked_tooltip"]
    if clicked and isinstance(clicked, str) and "|" in clicked:
        bh_id = clicked.split("|")[0].strip()
        st.session_state["show_log_loca_id"] = bh_id


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
else:
    pass


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
    elif len(filtered_ids) == 1:
        # Show log plot immediately after single selection
        if "show_labels" not in st.session_state:
            st.session_state["show_labels"] = True
        st.session_state["show_labels"] = st.checkbox(
            "Labels",
            value=st.session_state["show_labels"],
            help="Show/hide GEOL_LEG labels on plots.",
            key="labels_checkbox",
        )
        render_borehole_log(
            filtered_ids[0],
            filename_map,
            st.session_state["ags_files"],
            show_labels=st.session_state["show_labels"],
            fig_height=12,
        )
    else:
        # Show section plot for multiple boreholes
        if "show_labels" not in st.session_state:
            st.session_state["show_labels"] = True
        st.session_state["show_labels"] = st.checkbox(
            "Labels",
            value=st.session_state["show_labels"],
            help="Show/hide GEOL_LEG labels on plots.",
            key="labels_checkbox",
        )
        section_fig = generate_section_plot(
            filtered_ids,
            selected,
            filename_map,
            show_labels=st.session_state["show_labels"],
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
else:
    st.info("Draw a rectangle or polygon to select boreholes.")

# --- Show log plot if triggered by Log link or marker click (AFTER map and selection UI) ---
if st.session_state.get("show_log_loca_id"):
    if "show_labels" not in st.session_state:
        st.session_state["show_labels"] = True
    st.session_state["show_labels"] = st.checkbox(
        "Labels",
        value=st.session_state["show_labels"],
        help="Show/hide GEOL_LEG labels on plots.",
        key="labels_checkbox",
    )
    render_borehole_log(
        st.session_state["show_log_loca_id"],
        filename_map,
        st.session_state["ags_files"],
        show_labels=st.session_state["show_labels"],
        fig_height=12,
    )
    st.session_state["show_log_loca_id"] = None
