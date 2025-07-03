"""Coordinate transformation utilities."""

import streamlit as st
from typing import Tuple
from pyproj import Transformer
import logging

logger = logging.getLogger(__name__)

# Constants for UK coordinate systems
OSGB36_CRS = "epsg:27700"  # British National Grid
WGS84_CRS = "epsg:4326"  # Standard lat/lon

# Constants for UK coordinate validation (OSGB36 / British National Grid)
UK_MIN_EASTING = 0
UK_MAX_EASTING = 700000  # Maximum easting in Great Britain
UK_MIN_NORTHING = 0
UK_MAX_NORTHING = 1300000  # Maximum northing in Great Britain


@st.cache_resource
def get_transformer(from_crs: str = OSGB36_CRS, to_crs: str = WGS84_CRS) -> Transformer:
    """Get a cached coordinate transformer."""
    try:
        return Transformer.from_crs(from_crs, to_crs, always_xy=True)
    except Exception as e:
        logger.error(f"Failed to create transformer: {e}")
        raise


def validate_coordinates(easting: float, northing: float) -> bool:
    """Check if coordinates are within reasonable UK bounds (OSGB36)."""
    try:
        # Handle edge cases and invalid input
        if easting is None or northing is None:
            return False

        # Convert to float if possible
        try:
            easting = float(easting)
            northing = float(northing)
        except (TypeError, ValueError):
            return False

        # First pass: basic range check with some tolerance
        # Allow slightly outside normal bounds for edge cases
        if not (
            UK_MIN_EASTING - 10000 <= easting <= UK_MAX_EASTING + 10000
            and UK_MIN_NORTHING - 10000 <= northing <= UK_MAX_NORTHING + 10000
        ):
            return False

        # Second pass: log warnings for unusual but not impossible values
        # Check for typical range of easting values (west to east)
        if not (75000 <= easting <= 660000):  # Slightly expanded range
            logger.warning(f"Easting {easting} outside typical UK range (80000-655000)")

        # Check for typical range of northing values (south to north)
        if not (0 <= northing <= 1225000):  # Slightly expanded range
            logger.warning(
                f"Northing {northing} outside typical UK range (5000-1220000)"
            )

        return True

    except Exception as e:
        logger.error(f"Coordinate validation error: {e}")
        return False


@st.cache_data
def osgb36_to_latlon(easting: float, northing: float) -> Tuple[float, float]:
    """Convert OSGB36 (British National Grid) to WGS84 lat/lon."""
    if not validate_coordinates(easting, northing):
        raise ValueError(f"Invalid UK coordinates: E={easting}, N={northing}")

    try:
        transformer = get_transformer()
        lon, lat = transformer.transform(easting, northing)
        return lat, lon  # Return as lat,lon for consistency with common usage
    except Exception as e:
        logger.error(f"Coordinate conversion failed: {e}")
        raise


@st.cache_data
def latlon_to_osgb36(lat: float, lon: float) -> Tuple[float, float]:
    """Convert WGS84 lat/lon to OSGB36 (British National Grid)."""
    try:
        transformer = get_transformer(WGS84_CRS, OSGB36_CRS)
        easting, northing = transformer.transform(lon, lat)
        if validate_coordinates(easting, northing):
            return easting, northing
        raise ValueError(
            f"Converted coordinates outside UK bounds: E={easting}, N={northing}"
        )
    except Exception as e:
        logger.error(f"Coordinate conversion failed: {e}")
        raise
