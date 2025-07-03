"""Configuration settings for the application."""

import streamlit as st
from dataclasses import dataclass
from typing import Dict, Any, ClassVar


@dataclass
class AppConfig:
    """Application configuration settings."""

    # Coordinate Reference Systems
    DEFAULT_CRS: ClassVar[str] = "EPSG:27700"  # British National Grid
    WGS84_CRS: ClassVar[str] = "EPSG:4326"  # WGS84 (GPS coordinates)

    # Map Settings
    MAP_DEFAULT_ZOOM: ClassVar[int] = 17
    MAP_DEFAULT_STYLE: ClassVar[str] = "OpenStreetMap"
    MAP_ALTERNATIVE_STYLE: ClassVar[str] = "Esri.WorldImagery"
    MAP_CLUSTER_THRESHOLD: ClassVar[int] = 50  # Number of points before clustering
    MAP_TILE_CACHE_TTL: ClassVar[int] = 3600  # Tile cache timeout in seconds

    # Plot Settings
    PLOT_DPI: ClassVar[int] = 100
    DEFAULT_FIGURE_SIZE: ClassVar[tuple] = (10, 6)
    BOREHOLE_COLUMN_WIDTH: ClassVar[int] = 4
    LABEL_FONTSIZE: ClassVar[int] = 8
    USE_FAST_STYLE: ClassVar[bool] = True  # Use matplotlib fast style

    # Cache Settings
    CACHE_TTL: ClassVar[int] = 3600  # Cache timeout in seconds
    CACHE_MAX_ENTRIES: ClassVar[int] = 1000  # Maximum cache entries
    LARGE_DF_CHUNK_SIZE: ClassVar[int] = 10000  # Chunk size for large dataframes

    # Performance Settings
    ENABLE_PARALLEL: ClassVar[bool] = True  # Enable parallel processing
    MAX_WORKERS: ClassVar[int] = 4  # Maximum number of parallel workers
    WEBGL_POINT_THRESHOLD: ClassVar[int] = 1000  # Points before switching to WebGL

    # Memory Settings
    USE_CATEGORICAL: ClassVar[bool] = True  # Use categorical dtypes for strings
    AGS_REQUIRED_COLUMNS: ClassVar[Dict] = {  # Only load these columns
        "GEOL": ["LOCA_ID", "GEOL_TOP", "GEOL_BASE", "GEOL_LEG"],
        "LOCA": ["LOCA_ID", "LOCA_GL", "LOCA_FDEP", "LOCA_LAT", "LOCA_LON"],
        "ABBR": ["ABBR_CODE", "ABBR_DESC"],
    }

    # Debug Settings
    DEBUG_MODE: ClassVar[bool] = False  # Enable detailed debug logging
    PROFILE_PERFORMANCE: ClassVar[bool] = False  # Enable performance profiling
    MONITOR_MEMORY: ClassVar[bool] = False  # Track memory usage

    # File Settings
    ALLOWED_EXTENSIONS: ClassVar[list] = [".ags"]
    ENCODING: ClassVar[str] = "utf-8"

    # UI Settings
    GRID_COLUMNS: ClassVar[int] = 6

    # Instance settings (can be overridden)
    map_settings: Dict[str, Any] = None
    plot_settings: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize instance settings."""
        if self.map_settings is None:
            self.map_settings = self.get_map_settings()
        if self.plot_settings is None:
            self.plot_settings = self.get_plot_settings()

    @staticmethod
    def get_plot_settings() -> Dict[str, Any]:
        """Get default plot settings."""
        return {
            "figure_size": AppConfig.DEFAULT_FIGURE_SIZE,
            "dpi": AppConfig.PLOT_DPI,
            "show_labels": True,
            "column_width": AppConfig.BOREHOLE_COLUMN_WIDTH,
            "label_fontsize": AppConfig.LABEL_FONTSIZE,
        }

    @staticmethod
    def get_map_settings() -> Dict[str, Any]:
        """Get default map settings."""
        return {
            "zoom": AppConfig.MAP_DEFAULT_ZOOM,
            "base_style": AppConfig.MAP_DEFAULT_STYLE,
            "satellite_style": AppConfig.MAP_ALTERNATIVE_STYLE,
        }


@st.cache_resource
def get_config() -> AppConfig:
    """Get application configuration singleton."""
    if "config" not in st.session_state:
        st.session_state.config = AppConfig()
    return st.session_state.config


__all__ = ["AppConfig", "get_config"]
