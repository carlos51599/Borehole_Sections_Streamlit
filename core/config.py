"""Configuration settings for the application."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AppConfig:
    """Application configuration settings."""

    # Coordinate Reference Systems
    DEFAULT_CRS = "EPSG:27700"  # British National Grid
    WGS84_CRS = "EPSG:4326"  # WGS84 (GPS coordinates)

    # Map Settings
    MAP_DEFAULT_ZOOM = 17
    MAP_DEFAULT_STYLE = "OpenStreetMap"
    MAP_ALTERNATIVE_STYLE = "Esri.WorldImagery"
    MAP_CLUSTER_THRESHOLD = 50  # Number of points before clustering
    MAP_TILE_CACHE_TTL = 3600  # Tile cache timeout in seconds

    # Plot Settings
    PLOT_DPI = 100
    DEFAULT_FIGURE_SIZE = (10, 6)
    BOREHOLE_COLUMN_WIDTH = 4
    LABEL_FONTSIZE = 8
    USE_FAST_STYLE = True  # Use matplotlib fast style

    # Cache Settings
    CACHE_TTL = 3600  # Cache timeout in seconds
    CACHE_MAX_ENTRIES = 1000  # Maximum cache entries
    LARGE_DF_CHUNK_SIZE = 10000  # Chunk size for large dataframes

    # Performance Settings
    ENABLE_PARALLEL = True  # Enable parallel processing
    MAX_WORKERS = 4  # Maximum number of parallel workers
    WEBGL_POINT_THRESHOLD = 1000  # Points before switching to WebGL

    # Memory Settings
    USE_CATEGORICAL = True  # Use categorical dtypes for strings
    AGS_REQUIRED_COLUMNS = {  # Only load these columns
        "GEOL": ["LOCA_ID", "GEOL_TOP", "GEOL_BASE", "GEOL_LEG"],
        "LOCA": ["LOCA_ID", "LOCA_GL", "LOCA_FDEP", "LOCA_LAT", "LOCA_LON"],
        "ABBR": ["ABBR_CODE", "ABBR_DESC"],
    }

    # Debug Settings
    DEBUG_MODE = False  # Enable detailed debug logging
    PROFILE_PERFORMANCE = False  # Enable performance profiling
    LOG_LEVEL = "INFO"  # Default log level
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MONITOR_MEMORY = False  # Track memory usage
    LOG_FILE = "app.log"  # Log file location

    # File Settings
    ALLOWED_EXTENSIONS = [".ags"]
    ENCODING = "utf-8"

    # UI Settings
    GRID_COLUMNS = 6

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

    @staticmethod
    def init_logging() -> None:
        """Initialize logging configuration."""
        import logging
        import sys

        # Set up logging format
        formatter = logging.Formatter(AppConfig.LOG_FORMAT)

        # File handler
        file_handler = logging.FileHandler(AppConfig.LOG_FILE)
        file_handler.setFormatter(formatter)

        # Stream handler (console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)

        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(AppConfig.LOG_LEVEL)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)

        # Set debug level if debug mode is enabled
        if AppConfig.DEBUG_MODE:
            root_logger.setLevel(logging.DEBUG)
