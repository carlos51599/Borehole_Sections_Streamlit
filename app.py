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
m = render_map(loca_df, transformer, st.session_state["selected_boreholes"])
map_data = st_folium(
    m, height=600, width=None, key=st.session_state.get("last_shape_hash")
)

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

    if not filtered_ids:
        st.warning("No boreholes selected. Please check at least one borehole.")
    else:
        section_fig = generate_section_plot(filtered_ids, selected, filename_map)
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
