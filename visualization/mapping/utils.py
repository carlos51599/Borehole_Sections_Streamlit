"""
Mapping utilities for handling coordinates and shapes.
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point
import logging
from utils.coordinates import transform_coordinates


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_data
def filter_by_polygon(
    df: pd.DataFrame,
    polygon_coords: List[List[float]],
    lat_col: str = "LOCA_LAT",
    lon_col: str = "LOCA_LON",
) -> pd.DataFrame:
    """
    Filter DataFrame to only include points within a polygon.
    Cached for better performance.

    Args:
        df: DataFrame containing point coordinates
        polygon_coords: List of [lat, lon] pairs defining polygon vertices
        lat_col: Name of latitude column
        lon_col: Name of longitude column

    Returns:
        DataFrame filtered to points within polygon

    Raises:
        ValueError: If polygon coordinates are invalid
    """
    try:
        # Validate inputs
        if not polygon_coords or len(polygon_coords) < 3:
            raise ValueError("Polygon must have at least 3 vertices")

        # Create polygon
        poly = Polygon([(p[1], p[0]) for p in polygon_coords])

        # Create mask for points inside polygon
        points = [Point(row[lon_col], row[lat_col]) for _, row in df.iterrows()]
        mask = [point.within(poly) for point in points]

        return df[mask]

    except Exception as e:
        logger.error(f"Error filtering by polygon: {str(e)}")
        raise


@st.cache_data
def calculate_line_distances(
    points: List[Tuple[float, float]], coordinate_system: str = "OSGB36"
) -> np.ndarray:
    """
    Calculate cumulative distances along a line of points.
    Cached for better performance.

    Args:
        points: List of (lat, lon) or (easting, northing) coordinates
        coordinate_system: Coordinate system of input points

    Returns:
        Array of cumulative distances in meters

    Raises:
        ValueError: If points list is empty or invalid
    """
    try:
        if not points or len(points) < 2:
            raise ValueError("At least 2 points required")

        # Transform to proper coordinate system if needed
        if coordinate_system.upper() not in ["OSGB36", "BNG"]:
            points = [
                transform_coordinates(
                    p[0], p[1], from_sys=coordinate_system, to_sys="OSGB36"
                )
                for p in points
            ]

        # Calculate distances
        points = np.array(points)
        diffs = np.diff(points, axis=0)
        distances = np.sqrt((diffs**2).sum(axis=1))

        return np.concatenate(([0], np.cumsum(distances)))

    except Exception as e:
        logger.error(f"Error calculating line distances: {str(e)}")
        raise


@st.cache_data
def interpolate_points(
    start: Tuple[float, float], end: Tuple[float, float], num_points: int = 100
) -> List[Tuple[float, float]]:
    """
    Create evenly spaced points along a line.
    Cached for better performance.

    Args:
        start: Starting point coordinates (x, y)
        end: Ending point coordinates (x, y)
        num_points: Number of points to generate

    Returns:
        List of interpolated point coordinates

    Raises:
        ValueError: If input coordinates are invalid
    """
    try:
        # Validate inputs
        if not all(isinstance(p, (int, float)) for p in start + end):
            raise ValueError("Coordinates must be numeric")

        # Create interpolated points
        x = np.linspace(start[0], end[0], num_points)
        y = np.linspace(start[1], end[1], num_points)

        return list(zip(x, y))

    except Exception as e:
        logger.error(f"Error interpolating points: {str(e)}")
        raise
