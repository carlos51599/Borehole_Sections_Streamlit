from pyproj import Transformer
import streamlit as st
from typing import Tuple, Any, Dict, List, Optional
import matplotlib.pyplot as plt
import os
from math import hypot
import numpy as np
import logging
from functools import lru_cache


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_resource
def get_transformer(from_crs: str, to_crs: str) -> Transformer:
    """
    Get a cached coordinate transformer.

    Args:
        from_crs: Source CRS (e.g., "epsg:4326")
        to_crs: Target CRS (e.g., "epsg:27700")

    Returns:
        Transformer object
    """
    try:
        return Transformer.from_crs(from_crs, to_crs, always_xy=True)
    except Exception as e:
        logger.error(f"Error creating transformer {from_crs} -> {to_crs}: {str(e)}")
        raise


@st.cache_data
def latlon_to_osgb36(lon: float, lat: float) -> Tuple[float, float]:
    """
    Convert WGS84 lon/lat to OSGB36 easting/northing (EPSG:27700).

    Args:
        lon: Longitude in WGS84
        lat: Latitude in WGS84

    Returns:
        Tuple of (easting, northing)
    """
    transformer = get_transformer("epsg:4326", "epsg:27700")
    try:
        return transformer.transform(lon, lat)
    except Exception as e:
        logger.error(f"Error converting coordinates ({lon}, {lat}): {str(e)}")
        raise


@st.cache_data
def osgb36_to_latlon(easting: float, northing: float) -> Tuple[float, float]:
    """
    Convert OSGB36 easting/northing to WGS84 lat/lon.

    Args:
        easting: Easting in OSGB36
        northing: Northing in OSGB36

    Returns:
        Tuple of (latitude, longitude)
    """
    transformer = get_transformer("epsg:27700", "epsg:4326")
    try:
        return transformer.transform(easting, northing)[::-1]
    except Exception as e:
        logger.error(f"Error converting coordinates ({easting}, {northing}): {str(e)}")
        raise


def get_session_state(key: str, default: Any) -> Any:
    """
    Get a value from Streamlit session state, or set it to default if missing.

    Args:
        key: Session state key
        default: Default value if key doesn't exist

    Returns:
        Value from session state or default
    """
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


@st.cache_data
def assign_color_map(
    unique_keys: List[str], cmap_name: str = "tab20"
) -> Dict[str, Tuple[float, ...]]:
    """
    Assign a color from a matplotlib colormap to each unique key.

    Args:
        unique_keys: List of unique identifiers
        cmap_name: Name of matplotlib colormap to use

    Returns:
        Dictionary mapping keys to RGBA colors
    """
    try:
        cmap = plt.get_cmap(cmap_name)
        return {key: tuple(cmap(i % cmap.N)) for i, key in enumerate(unique_keys)}
    except Exception as e:
        logger.error(f"Error creating color map: {str(e)}")
        # Fallback to grayscale if colormap fails
        return {key: (0.7, 0.7, 0.7, 1.0) for key in unique_keys}


def safe_temp_path(fname: str, tmp_dir: str = "/tmp") -> str:
    """
    Create a safe temp file path for a given filename.

    Args:
        fname: Original filename
        tmp_dir: Directory for temporary files

    Returns:
        Safe temporary file path
    """
    if not os.path.isdir(tmp_dir):
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        os.makedirs(tmp_dir, exist_ok=True)

    base = os.path.basename(fname)
    return os.path.join(tmp_dir, base)


@lru_cache(maxsize=1024)
def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Compute Euclidean distance between two points.

    Args:
        x1, y1: Coordinates of first point
        x2, y2: Coordinates of second point

    Returns:
        Distance between points
    """
    return hypot(x2 - x1, y2 - y1)


def validate_coordinates(
    easting: float,
    northing: float,
    min_e: float = 0,
    max_e: float = 700000,
    min_n: float = 0,
    max_n: float = 1300000,
) -> bool:
    """
    Validate that coordinates are within reasonable bounds for UK.

    Args:
        easting: Easting coordinate
        northing: Northing coordinate
        min_e, max_e: Valid easting range
        min_n, max_n: Valid northing range

    Returns:
        True if coordinates are valid
    """
    return min_e <= easting <= max_e and min_n <= northing <= max_n
