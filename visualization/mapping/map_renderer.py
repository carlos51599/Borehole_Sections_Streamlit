"""
Map rendering module for displaying borehole locations.
"""

import streamlit as st
import folium
from typing import List, Optional, Tuple
import pandas as pd
from folium import plugins
import logging
from core.config import AppConfig


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MapRenderer:
    """
    Class for rendering interactive maps with borehole locations.

    This class provides functionality for creating interactive web maps showing
    borehole locations, with features like:
    - Marker clustering for dense borehole groups
    - Popup information for each borehole
    - Layer controls and fullscreen capability
    - Selection state visualization

    The maps are rendered using Folium with custom styling and interactivity.
    Calculations and data processing are cached for better performance.

    Attributes:
        loca_df (pd.DataFrame): DataFrame containing borehole location data
    """

    def __init__(self, loca_df: pd.DataFrame) -> None:
        """
        Initialize the map renderer.

        Args:
            loca_df: DataFrame containing borehole locations with required columns:
                    LOCA_ID: Unique borehole identifier
                    LOCA_LAT: Latitude in decimal degrees
                    LOCA_LON: Longitude in decimal degrees
                    LOCA_GL: Ground level in meters
                    LOCA_FDEP: Final depth in meters

        Raises:
            ValueError: If required columns are missing from loca_df
        """
        required_cols = ["LOCA_ID", "LOCA_LAT", "LOCA_LON", "LOCA_GL", "LOCA_FDEP"]
        missing_cols = [col for col in required_cols if col not in loca_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        self.loca_df = loca_df
        self._setup_cache()

    def _setup_cache(self) -> None:
        """Setup cached computations."""
        self.center = self._calculate_center()
        self.bounds = self._calculate_bounds()

    @st.cache_data(ttl=AppConfig.CACHE_TTL)
    def _calculate_center(self) -> Tuple[float, float]:
        """
        Calculate the cached map center.

        This method computes the average latitude and longitude of all boreholes
        to determine the best center point for the map view. The calculation is
        cached for better performance.

        Returns:
            Tuple of (latitude, longitude) in decimal degrees for map center

        Raises:
            ValueError: If no valid coordinates are found in data
        """
        try:
            return (
                float(self.loca_df["LOCA_LAT"].mean()),
                float(self.loca_df["LOCA_LON"].mean()),
            )
        except Exception as e:
            logger.error(f"Error calculating map center: {str(e)}")
            raise

    @st.cache_data(ttl=AppConfig.CACHE_TTL)
    def _calculate_bounds(self) -> List[List[float]]:
        """
        Calculate the cached map bounds.

        This method computes the minimum and maximum latitude and longitude of all boreholes
        to determine the bounding box for the map view. The calculation is
        cached for better performance.

        Returns:
            List of [[southwest_lat, southwest_lon], [northeast_lat, northeast_lon]]

        Raises:
            ValueError: If no valid coordinates are found in data
        """
        lat_min = float(self.loca_df["LOCA_LAT"].min())
        lat_max = float(self.loca_df["LOCA_LAT"].max())
        lon_min = float(self.loca_df["LOCA_LON"].min())
        lon_max = float(self.loca_df["LOCA_LON"].max())
        return [[lat_min, lon_min], [lat_max, lon_max]]

    def _create_popup_content(self, row: pd.Series) -> str:
        """
        Create cached popup content.

        This method generates the HTML content for the popup of each borehole marker,
        showing key information like ID, ground level, and final depth.

        Args:
            row: Pandas Series containing a single row of borehole data

        Returns:
            HTML string for popup content
        """
        return f"""
            <div style='font-family: Arial; font-size: 12px;'>
                <b>ID:</b> {row['LOCA_ID']}<br>
                <b>Ground Level:</b> {row.get('LOCA_GL', 'N/A')} mOD<br>
                <b>Final Depth:</b> {row.get('LOCA_FDEP', 'N/A')} m
            </div>
        """

    @st.cache_data(ttl=AppConfig.CACHE_TTL)
    def create_map(
        self,
        selected_boreholes: Optional[List[str]] = None,
        zoom_start: int = AppConfig.MAP_DEFAULT_ZOOM,
        tile_layer: str = AppConfig.MAP_DEFAULT_STYLE,
    ) -> folium.Map:
        """
        Create an interactive map with optimized rendering.

        This method creates a Folium map with the following features:
        - Base map with selectable tile layers
        - Borehole markers with popups showing details
        - Optional marker clustering for better visualization
        - Highlighting of selected boreholes
        - Layer control and fullscreen capability

        The map creation is cached for better performance.

        Args:
            selected_boreholes: List of borehole IDs to highlight
            zoom_start: Initial zoom level (1-18, default: 13)
            tile_layer: Base map tile source (default: "OpenStreetMap")

        Returns:
            Folium Map object ready for display

        Raises:
            ValueError: If invalid zoom level or tile layer is specified
            RuntimeError: If map creation fails
        """
        # Create base map
        m = folium.Map(
            location=self.center,
            zoom_start=zoom_start,
            tiles=tile_layer,
        )

        # Add tile layers with caching
        folium.TileLayer(
            AppConfig.MAP_ALTERNATIVE_STYLE,
            name="Satellite",
            attr="Esri World Imagery",
        ).add_to(m)

        # Create feature groups
        points = []
        selected_points = []

        # Process points
        for _, row in self.loca_df.iterrows():
            point = {
                "loc": [row["LOCA_LAT"], row["LOCA_LON"]],
                "popup": self._create_popup_content(row),
                "selected": selected_boreholes and row["LOCA_ID"] in selected_boreholes,
            }
            if point["selected"]:
                selected_points.append(point)
            else:
                points.append(point)

        # Add markers with clustering if needed
        if len(points) > AppConfig.MAP_CLUSTER_THRESHOLD:
            marker_cluster = plugins.MarkerCluster(name="Boreholes")
            for point in points:
                folium.Marker(
                    location=point["loc"],
                    popup=point["popup"],
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(marker_cluster)
            marker_cluster.add_to(m)
        else:
            for point in points:
                folium.Marker(
                    location=point["loc"],
                    popup=point["popup"],
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(m)

        # Add selected points
        for point in selected_points:
            folium.Marker(
                location=point["loc"],
                popup=point["popup"],
                icon=folium.Icon(color="red", icon="info-sign"),
            ).add_to(m)

        # Add controls
        folium.LayerControl().add_to(m)
        plugins.Fullscreen().add_to(m)

        # Fit bounds if points exist
        if points or selected_points:
            m.fit_bounds(self.bounds)

        return m
