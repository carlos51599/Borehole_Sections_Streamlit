import pandas as pd
import streamlit as st
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import transform as shapely_transform
import pyproj
from typing import Dict, Any, Optional
import numpy as np
import logging
from functools import lru_cache


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_resource
def get_utm_transformer(median_lat: float, median_lon: float) -> pyproj.Transformer:
    """
    Get a cached UTM transformer for the given coordinates.

    Args:
        median_lat: Median latitude
        median_lon: Median longitude

    Returns:
        Transformer for converting to/from UTM
    """
    utm_zone = int((median_lon + 180) / 6) + 1
    utm_crs = f"EPSG:{32600 + utm_zone if median_lat >= 0 else 32700 + utm_zone}"
    return pyproj.Transformer.from_crs("epsg:4326", utm_crs, always_xy=True)


@st.cache_data
def create_geometry(_geom: Dict[str, Any]) -> Optional[Polygon]:
    """
    Create a cached geometry object from coordinates.

    Args:
        _geom: Dictionary containing geometry type and coordinates

    Returns:
        Shapely geometry object or None if invalid
    """
    try:
        if _geom["type"] == "Rectangle":
            coords = _geom["coordinates"][0]
            return Polygon(coords)
        elif _geom["type"] == "Polygon":
            coords = _geom["coordinates"][0]
            return Polygon(coords)
        elif _geom["type"] == "LineString":
            coords = _geom["coordinates"]
            return LineString(coords)
    except Exception as e:
        logger.error(f"Error creating geometry: {str(e)}")
        return None


def filter_selection_by_shape(
    geom: Dict[str, Any], loca_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Filter locations based on a geometric shape.

    Args:
        geom: Dictionary containing geometry type and coordinates
        loca_df: DataFrame containing borehole locations

    Returns:
        Filtered DataFrame
    """
    try:
        if geom is None or loca_df.empty:
            return pd.DataFrame()

        if geom["type"] == "Rectangle":
            return _filter_by_rectangle(geom, loca_df)
        elif geom["type"] == "Polygon":
            return _filter_by_polygon(geom, loca_df)
        elif geom["type"] == "LineString":
            return _filter_by_line(geom, loca_df)

        return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error filtering by shape: {str(e)}")
        st.error("Error filtering boreholes. Please try a different selection.")
        return pd.DataFrame()


@st.cache_data
def _filter_by_rectangle(geom: Dict[str, Any], loca_df: pd.DataFrame) -> pd.DataFrame:
    """Filter locations by rectangle."""
    coords = geom["coordinates"][0]
    lons, lats = zip(*coords)
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    return loca_df[
        (loca_df["lat"] >= min_lat)
        & (loca_df["lat"] <= max_lat)
        & (loca_df["lon"] >= min_lon)
        & (loca_df["lon"] <= max_lon)
    ]


@st.cache_data
def _filter_by_polygon(geom: Dict[str, Any], loca_df: pd.DataFrame) -> pd.DataFrame:
    """Filter locations by polygon."""
    poly = create_geometry(geom)
    if poly is None:
        return pd.DataFrame()

    # Vectorized point creation for better performance
    points = loca_df.apply(lambda row: Point(row["lon"], row["lat"]), axis=1)
    mask = points.apply(poly.contains)
    return loca_df[mask]


@st.cache_data
def _filter_by_line(
    geom: Dict[str, Any], loca_df: pd.DataFrame, buffer_m: float = 50
) -> pd.DataFrame:
    """Filter locations by line with buffer."""
    line = create_geometry(geom)
    if line is None:
        return pd.DataFrame()

    # Get UTM transformer for the area
    transformer = get_utm_transformer(loca_df["lat"].median(), loca_df["lon"].median())

    # Transform geometries to UTM for accurate buffering
    line_utm = shapely_transform(transformer.transform, line)
    buffer_utm = line_utm.buffer(buffer_m)

    # Vectorized point transformation and containment check
    points_utm = loca_df.apply(
        lambda row: shapely_transform(
            transformer.transform, Point(row["lon"], row["lat"])
        ),
        axis=1,
    )
    mask = points_utm.apply(buffer_utm.contains)
    return loca_df[mask]
