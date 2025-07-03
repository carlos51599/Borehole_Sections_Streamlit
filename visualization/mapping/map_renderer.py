"""
Map rendering module for displaying borehole locations.
"""

import streamlit as st
import folium
from folium.plugins import Draw
from folium import Marker, Icon, TileLayer, LayerControl, PolyLine
import pandas as pd
from typing import Optional, Dict, Any
import logging


# Get module logger
logger = logging.getLogger(__name__)


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
            <strong>Coordinates:</strong> {row.get('lat', '?')}, {row.get('lon', '?')}
        </p>
        <button onclick="window.parent.postMessage({{type: 'show_log', loca_id: '{row['LOCA_ID']}' }}, '*')"
                style='margin-top: 10px; padding: 5px 10px'>
            View Log
        </button>
    </div>"""


class MapRenderer:
    """Handles rendering of the interactive map."""

    def __init__(self, loca_df: pd.DataFrame):
        """Initialize the map renderer with location data."""
        self.loca_df = loca_df.copy()
        self.map = None

        # Handle missing coordinate columns
        required_cols = ["lat", "lon"]
        if not all(col in self.loca_df.columns for col in required_cols):
            logger.warning(
                f"Missing required coordinate columns in loca_df. "
                f"Available columns: {self.loca_df.columns.tolist()}"
            )
            # Add empty coordinate columns
            for col in required_cols:
                if col not in self.loca_df.columns:
                    self.loca_df[col] = pd.NA

    def create_map(
        self,
        selected_boreholes: Optional[pd.DataFrame] = None,
        zoom_start: int = 13,
        center: Optional[Any] = None
    ) -> folium.Map:
        """Create an interactive map with borehole locations."""
        # Get center from session state if available
        center = center or [self.loca_df["lat"].median(), self.loca_df["lon"].median()]
        if isinstance(center, dict):
            center = [center["lat"], center["lng"]]

        # Create base map
        self.map = folium.Map(
            location=center,
            zoom_start=zoom_start,
            tiles=None,
        )

        # Add tile layers
        TileLayer("OpenStreetMap", name="Base Map").add_to(self.map)
        TileLayer("Esri.WorldImagery", name="Satellite").add_to(self.map)

        # Add markers for valid coordinates
        selected_ids = (
            set()
            if selected_boreholes is None or selected_boreholes.empty
            else set(selected_boreholes["LOCA_ID"])
        )

        # Add markers for each borehole
        for _, row in self.loca_df.iterrows():
            try:
                if pd.isna(row["lat"]) or pd.isna(row["lon"]):
                    continue

                is_selected = row["LOCA_ID"] in selected_ids
                lat, lon = float(row["lat"]), float(row["lon"])

                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    logger.warning(
                        f"Invalid coordinates for borehole {row['LOCA_ID']}: {lat}, {lon}"
                    )
                    continue

                Marker(
                    location=[lat, lon],
                    tooltip=f"{row['LOCA_ID']} | GL: {row.get('LOCA_GL', '?')}m | Depth: {row.get('LOCA_FDEP', '?')}m",
                    popup=folium.Popup(create_popup_html(row), max_width=300),
                    icon=create_marker_icon(is_selected),
                ).add_to(self.map)
            except Exception as e:
                logger.error(
                    f"Error adding marker for borehole {row.get('LOCA_ID', '?')}: {str(e)}"
                )

        # Add drawing tools with options
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
        ).add_to(self.map)

        # Add layer control
        LayerControl().add_to(self.map)

        return self.map
