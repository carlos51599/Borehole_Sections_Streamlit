import pandas as pd
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import transform as shapely_transform
import pyproj


def filter_selection_by_shape(geom, loca_df):
    if geom is None:
        return pd.DataFrame()
    if geom["type"] == "Rectangle":
        coords = geom["coordinates"][0]
        lons = [pt[0] for pt in coords]
        lats = [pt[1] for pt in coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        return loca_df[
            (loca_df["lat"] >= min_lat)
            & (loca_df["lat"] <= max_lat)
            & (loca_df["lon"] >= min_lon)
            & (loca_df["lon"] <= max_lon)
        ]
    elif geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
        poly = Polygon([(lon, lat) for lon, lat in coords])
        mask = loca_df.apply(
            lambda row: poly.contains(Point(row["lon"], row["lat"])), axis=1
        )
        return loca_df[mask]
    elif geom["type"] == "LineString":
        coords = geom["coordinates"]
        line = LineString([(lon, lat) for lon, lat in coords])
        buffer_m = 50  # Buffer in meters
        median_lat = loca_df["lat"].median()
        median_lon = loca_df["lon"].median()
        utm_zone = int((median_lon + 180) / 6) + 1
        utm_crs = f"EPSG:{32600 + utm_zone if median_lat >= 0 else 32700 + utm_zone}"
        project = pyproj.Transformer.from_crs(
            "epsg:4326", utm_crs, always_xy=True
        ).transform
        line_utm = shapely_transform(project, line)
        buffer_utm = line_utm.buffer(buffer_m)
        mask = loca_df.apply(
            lambda row: buffer_utm.contains(
                shapely_transform(project, Point(row["lon"], row["lat"]))
            ),
            axis=1,
        )
        return loca_df[mask]
    return pd.DataFrame()
