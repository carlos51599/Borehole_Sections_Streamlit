from pyproj import Transformer
import streamlit as st


def latlon_to_osgb36(lon, lat):
    """Convert WGS84 lon/lat to OSGB36 easting/northing (EPSG:27700)."""
    transformer = Transformer.from_crs("epsg:4326", "epsg:27700", always_xy=True)
    return transformer.transform(lon, lat)


def osgb36_to_latlon(easting, northing):
    """Convert OSGB36 easting/northing to WGS84 lat/lon."""
    transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy=True)
    return transformer.transform(easting, northing)[::-1]


def get_session_state(key, default):
    """Get a value from Streamlit session state, or set it to default if missing."""
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def assign_color_map(unique_keys, cmap_name="tab20"):
    """Assign a color from a matplotlib colormap to each unique key."""
    import matplotlib.pyplot as plt

    cmap = plt.get_cmap(cmap_name)
    return {key: cmap(i % cmap.N) for i, key in enumerate(unique_keys)}


def safe_temp_path(fname, tmp_dir="/tmp"):
    """Create a safe temp file path for a given filename."""
    import os

    base = os.path.basename(fname)
    return os.path.join(tmp_dir, base)


def euclidean_distance(x1, y1, x2, y2):
    """Compute Euclidean distance between two points."""
    from math import hypot

    return hypot(x2 - x1, y2 - y1)
