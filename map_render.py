import folium
from folium.plugins import Draw
from folium import Marker, Icon, TileLayer, LayerControl, PolyLine
from sklearn.decomposition import PCA
import streamlit as st


def render_map(loca_df, transformer, selected_boreholes):
    map_center = st.session_state.get("map_center")
    map_zoom = st.session_state.get("map_zoom", 17)
    if not map_center:
        map_center = [loca_df["lat"].median(), loca_df["lon"].median()]
    m = folium.Map(location=map_center, zoom_start=map_zoom, tiles=None)
    TileLayer("OpenStreetMap", name="Base Map").add_to(m)
    TileLayer("Esri.WorldImagery", name="Satellite").add_to(m)

    for _, row in loca_df.iterrows():
        text = f"{row['LOCA_ID']} | GL: {row.get('LOCA_GL', '?')} | Depth: {row.get('LOCA_FDEP', '?')}"
        # Popup with only borehole info (no log button or form)
        popup_html = f"""
        <b>{row['LOCA_ID']}</b><br>
        GL: {row.get('LOCA_GL', '?')}<br>
        Depth: {row.get('LOCA_FDEP', '?')}<br>
        """
        popup = folium.Popup(popup_html, max_width=250)
        marker = Marker(
            location=(row["lat"], row["lon"]),
            tooltip=text,
            popup=popup,
            icon=Icon(color="blue", icon="info-sign"),
        )
        # Attach LOCA_ID as a property for st_folium click access
        marker.add_child(
            folium.GeoJson(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row["lon"], row["lat"]],
                    },
                    "properties": {"LOCA_ID": row["LOCA_ID"]},
                },
                name=None,
                tooltip=None,
                popup=None,
            )
        )
        marker.add_to(m)

    draw_options = {
        "polyline": True,
        "circle": False,
        "marker": False,
        "circlemarker": False,
        "rectangle": True,
        "polygon": True,
    }
    edit_options = {"edit": False, "remove": False}
    draw = Draw(export=True, draw_options=draw_options, edit_options=edit_options)
    draw.add_to(m)
    LayerControl().add_to(m)

    drawn_shape = st.session_state.get("last_drawn_shape")
    if drawn_shape:
        geom_type = drawn_shape.get("type")
        coords = drawn_shape.get("coordinates")
        # Polygon
        if geom_type == "Polygon" and coords:
            folium.Polygon(
                locations=[(lat, lon) for lon, lat in coords[0]],
                color="green",
                fill=True,
                fill_opacity=0.2,
            ).add_to(m)
        # Rectangle
        elif geom_type == "Rectangle" and coords:
            folium.Polygon(
                locations=[(lat, lon) for lon, lat in coords[0]],
                color="green",
                fill=True,
                fill_opacity=0.2,
            ).add_to(m)
        # LineString
        elif geom_type == "LineString" and coords:
            folium.PolyLine(
                locations=[
                    (coords[i][1], coords[i][0]) for i in range(len(coords))
                ],  # [lat, lon]
                color="red",
                weight=3,
                opacity=0.8,
                tooltip="Drawn polyline",
            ).add_to(m)
            # Draw the buffer zone (appears after drawing, not during)
            try:
                from shapely.geometry import LineString
                from shapely.ops import transform as shapely_transform
                import pyproj
                import numpy as np

                # Project to UTM for accurate buffering
                lats = [lat for lon, lat in coords]
                lons = [lon for lon, lat in coords]
                median_lat = np.median(lats)
                median_lon = np.median(lons)
                utm_zone = int((median_lon + 180) / 6) + 1
                utm_crs = (
                    f"EPSG:{32600 + utm_zone if median_lat >= 0 else 32700 + utm_zone}"
                )
                project = pyproj.Transformer.from_crs(
                    "epsg:4326", utm_crs, always_xy=True
                ).transform
                project_back = pyproj.Transformer.from_crs(
                    utm_crs, "epsg:4326", always_xy=True
                ).transform
                line = LineString([(lon, lat) for lon, lat in coords])
                line_utm = shapely_transform(project, line)
                buffer_utm = line_utm.buffer(50)  # 50m buffer
                buffer_latlon = shapely_transform(project_back, buffer_utm)
                folium.GeoJson(
                    buffer_latlon.__geo_interface__,
                    style_function=lambda x: {
                        "fillColor": "#3388ff",
                        "color": "#3388ff",
                        "weight": 1,
                        "fillOpacity": 0.15,
                    },
                    tooltip="Buffer zone (50m)",
                ).add_to(m)
            except Exception as e:
                print(f"Could not draw buffer: {e}")
            # Note: Buffer zone cannot be shown during drawing due to frontend limitations.
        # Circle
        elif geom_type == "Circle" and coords:
            # Expecting drawn_shape to have 'center' and 'radius' keys
            center = drawn_shape.get("center")
            radius = drawn_shape.get("radius")
            # If not present, try to infer from coordinates (GeoJSON style: [lon, lat])
            if not center and coords:
                center = coords  # [lon, lat]
            if center:
                # Make radius proportional to map zoom for visibility
                map_zoom = st.session_state.get("map_zoom", 17)
                # At zoom 17, 50m is visible; scale with zoom (lower zoom = larger area)
                base_radius = 50  # meters at zoom 17
                zoom_factor = 2 ** (17 - map_zoom)
                display_radius = base_radius * zoom_factor
                # If a radius is provided in the shape, use it, else use display_radius
                folium.Circle(
                    location=(center[1], center[0]),  # (lat, lon)
                    radius=radius if radius else display_radius,
                    color="orange",
                    fill=True,
                    fill_opacity=0.25,
                    tooltip=f"Selection radius: {int(radius if radius else display_radius)} m",
                ).add_to(m)

    if (
        selected_boreholes is not None
        and not selected_boreholes.empty
        and st.session_state.get("last_drawn_shape", {}).get("type")
        in ["Rectangle", "Polygon"]
    ):
        if (
            "LOCA_NATE" not in selected_boreholes.columns
            or "LOCA_NATN" not in selected_boreholes.columns
        ):
            pass
        elif selected_boreholes[["LOCA_NATE", "LOCA_NATN"]].isnull().any().any():
            pass
        elif len(selected_boreholes) < 2:
            pass  # Not enough boreholes for PCA
        else:
            pca = PCA(n_components=2)
            pca_coords = pca.fit_transform(
                selected_boreholes[["LOCA_NATE", "LOCA_NATN"]]
            )
            selected_boreholes["pca_x"] = pca_coords[:, 0]
            selected_boreholes = selected_boreholes.sort_values("pca_x")

            mean_coords = selected_boreholes[["LOCA_NATE", "LOCA_NATN"]].mean().values
            direction = pca.components_[0]
            # Draw the section axis line with a length proportional to the map window size (approximate)
            # Use the map's current zoom to estimate a reasonable length in meters
            map_zoom = st.session_state.get("map_zoom", 17)
            import math

            map_center = st.session_state.get("map_center")
            if map_center:
                center_lat = map_center[0]
            else:
                center_lat = loca_df["lat"].median()
            # At zoom 17, map width is about 1km; scale with zoom (lower zoom = larger area)
            base_length = 1000  # meters
            zoom_factor = 2 ** (17 - map_zoom)
            axis_length_m = (
                base_length * zoom_factor
            ) / 3  # Reduce to a third of previous length
            # Direction vector (unit)
            direction_unit = direction / (direction**2).sum() ** 0.5
            start = mean_coords - direction_unit * (axis_length_m / 2)
            end = mean_coords + direction_unit * (axis_length_m / 2)
            latlon_start = transformer.transform(start[0], start[1])[::-1]
            latlon_end = transformer.transform(end[0], end[1])[::-1]
            PolyLine(
                locations=[latlon_start, latlon_end],
                color="red",
                weight=2,
                opacity=0.8,
                dash_array="5, 5",
                tooltip="PCA section line",
            ).add_to(m)

    # --- Remove previous section selection and axis line if a log plot is being shown ---
    import pandas as pd

    if st.session_state.get("show_log_loca_id"):
        st.session_state["last_drawn_shape"] = None
        st.session_state["last_shape_hash"] = None
        st.session_state["selected_boreholes"] = pd.DataFrame()

    return m
