import folium
from folium.plugins import Draw
from folium import Marker, Icon, TileLayer, LayerControl, PolyLine
from sklearn.decomposition import PCA
import streamlit as st
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd


@st.cache_data
def create_marker_icon(is_selected: bool = False) -> Icon:
    """Create a cached marker icon"""
    return Icon(color="red" if is_selected else "blue", icon="info-sign")


@st.cache_data
def create_popup_html(row: pd.Series) -> str:
    """Create cached popup HTML content"""
    return f"""
    <div style='min-width: 200px'>
        <h4 style='margin: 0 0 10px 0'>{row['LOCA_ID']}</h4>
        <p style='margin: 5px 0'>
            <strong>Ground Level:</strong> {row.get('LOCA_GL', '?')}<br>
            <strong>Final Depth:</strong> {row.get('LOCA_FDEP', '?')}<br>
            <strong>Easting:</strong> {row.get('LOCA_NATE', '?')}<br>
            <strong>Northing:</strong> {row.get('LOCA_NATN', '?')}
        </p>
        <button onclick="window.parent.postMessage({{type: 'show_log', loca_id: '{row['LOCA_ID']}' }}, '*')" 
                style='margin-top: 10px; padding: 5px 10px'>
            View Log
        </button>
    </div>
    """


def render_map(
    loca_df: pd.DataFrame,
    transformer: Any,
    selected_boreholes: pd.DataFrame,
    default_zoom: int = 17,
) -> folium.Map:
    """
    Render an interactive map with borehole locations.

    Args:
        loca_df: DataFrame containing borehole locations
        transformer: Coordinate transformer object
        selected_boreholes: DataFrame of currently selected boreholes
        default_zoom: Default zoom level for the map

    Returns:
        folium.Map object with all markers and controls
    """
    # Get or calculate map center
    map_center = st.session_state.get("map_center")
    if not map_center:
        map_center = [loca_df["lat"].median(), loca_df["lon"].median()]

    # Create base map
    m = folium.Map(
        location=map_center,
        zoom_start=st.session_state.get("map_zoom", default_zoom),
        tiles=None,
    )

    # Add tile layers
    TileLayer("OpenStreetMap", name="Base Map").add_to(m)
    TileLayer("Esri.WorldImagery", name="Satellite").add_to(m)

    # Create set of selected IDs for quick lookup
    selected_ids = (
        set(selected_boreholes["LOCA_ID"]) if not selected_boreholes.empty else set()
    )

    # Add markers for each borehole
    for _, row in loca_df.iterrows():
        is_selected = row["LOCA_ID"] in selected_ids

        Marker(
            location=(row["lat"], row["lon"]),
            tooltip=f"{row['LOCA_ID']} | GL: {row.get('LOCA_GL', '?')} | Depth: {row.get('LOCA_FDEP', '?')}",
            popup=folium.Popup(create_popup_html(row), max_width=300),
            icon=create_marker_icon(is_selected),
        ).add_to(m)

    # Add drawing controls
    draw_options = {
        "polyline": True,
        "circle": False,
        "marker": False,
        "circlemarker": False,
        "rectangle": True,
        "polygon": True,
    }
    Draw(
        export=True,
        draw_options=draw_options,
        edit_options={"edit": False, "remove": False},
    ).add_to(m)

    # Add layer control
    LayerControl().add_to(m)

    # Add any existing drawn shapes
    drawn_shape = st.session_state.get("last_drawn_shape")
    if drawn_shape:
        _add_drawn_shape_to_map(m, drawn_shape)

    return m


@st.cache_data
def _add_drawn_shape_to_map(m: folium.Map, shape: Dict[str, Any]) -> None:
    """Add a cached drawn shape to the map"""
    geom_type = shape.get("type")
    coords = shape.get("coordinates", [])

    if not coords:
        return

    if geom_type == "Polygon":
        folium.Polygon(
            locations=[[lat, lon] for lon, lat in coords[0]],
            color="red",
            fill=True,
            opacity=0.5,
        ).add_to(m)
    elif geom_type == "LineString":
        folium.PolyLine(
            locations=[[lat, lon] for lon, lat in coords], color="red", weight=2
        ).add_to(m)
