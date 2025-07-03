"""Coordinate transformation and validation utilities."""

import streamlit as st
from typing import Tuple
from pyproj import Transformer
import logging
from core.config import AppConfig

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
    transformer = get_transformer(AppConfig.WGS84_CRS, AppConfig.DEFAULT_CRS)
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
    transformer = get_transformer(AppConfig.DEFAULT_CRS, AppConfig.WGS84_CRS)
    try:
        return transformer.transform(easting, northing)[::-1]
    except Exception as e:
        logger.error(f"Error converting coordinates ({easting}, {northing}): {str(e)}")
        raise


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
