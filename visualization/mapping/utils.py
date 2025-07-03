"""
Map utility functions.
"""

import pandas as pd
import streamlit as st
from shapely.geometry import Point, Polygon, LineString
import numpy as np
import logging


logger = logging.getLogger(__name__)


@st.cache_data
def filter_by_shape(df: pd.DataFrame, shape: dict) -> pd.DataFrame:
    """
    Filter locations by drawn shape.

    Args:
        df: DataFrame with lat/lon coordinates
        shape: Dictionary with shape type and coordinates

    Returns:
        Filtered DataFrame
    """
    try:
        if df.empty or not shape:
            return pd.DataFrame()

        # Create geometry based on shape type
        if shape["type"] == "Rectangle":
            return filter_by_rectangle(df, shape)
        elif shape["type"] == "Polygon":
            return filter_by_polygon(df, shape)
        elif shape["type"] == "LineString":
            return filter_by_line(df, shape)

        logger.warning(f"Unsupported shape type: {shape['type']}")
        return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error filtering by shape: {str(e)}")
        return pd.DataFrame()


def filter_by_rectangle(df: pd.DataFrame, shape: dict) -> pd.DataFrame:
    """Filter locations by rectangle."""
    try:
        coords = shape["coordinates"][0]
        lons, lats = zip(*coords)

        return df[
            (df["lon"] >= min(lons))
            & (df["lon"] <= max(lons))
            & (df["lat"] >= min(lats))
            & (df["lat"] <= max(lats))
        ]
    except Exception as e:
        logger.error(f"Error filtering by rectangle: {str(e)}")
        return pd.DataFrame()


def filter_by_polygon(df: pd.DataFrame, shape: dict) -> pd.DataFrame:
    """Filter locations by polygon."""
    try:
        poly = Polygon(shape["coordinates"][0])
        points = [Point(row["lon"], row["lat"]) for _, row in df.iterrows()]
        mask = [pt.within(poly) for pt in points]
        return df[mask]
    except Exception as e:
        logger.error(f"Error filtering by polygon: {str(e)}")
        return pd.DataFrame()


def filter_by_line(
    df: pd.DataFrame, shape: dict, buffer_distance: float = 50
) -> pd.DataFrame:
    """
    Filter locations near a line.

    Args:
        df: DataFrame with lat/lon coordinates
        shape: Dictionary with line coordinates
        buffer_distance: Distance in meters to search from line

    Returns:
        DataFrame of locations within buffer distance of line
    """
    try:
        # Create line
        line = LineString(shape["coordinates"])

        # Create points
        points = [Point(row["lon"], row["lat"]) for _, row in df.iterrows()]

        # Calculate distances (approximate using degrees)
        # 1 degree ~ 111km at equator, so buffer of 50m ≈ 0.00045 degrees
        buffer = buffer_distance / 111000  # Convert meters to degrees
        buffered = line.buffer(buffer)

        # Filter points within buffer
        mask = [pt.within(buffered) for pt in points]
        return df[mask]

    except Exception as e:
        logger.error(f"Error filtering by line: {str(e)}")
        return pd.DataFrame()
