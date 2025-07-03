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
        # Add a clickable link to show log in the popup
        html = f"""
        <b>{row['LOCA_ID']}</b><br>
        GL: {row.get('LOCA_GL', '?')}<br>
        Depth: {row.get('LOCA_FDEP', '?')}<br>
        <a href='#' onclick=\"window.parent.postMessage({{type: 'show_log', loca_id: '{row['LOCA_ID']}' }}, '*');return false;\">Log</a>
        """
        Marker(
            location=(row["lat"], row["lon"]),
            tooltip=text,
            popup=folium.Popup(html, max_width=250),
            icon=Icon(color="blue", icon="info-sign"),
        ).add_to(m)

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
        if geom_type == "Polygon" and coords:
            folium.Polygon(
                locations=[(lat, lon) for lon, lat in coords[0]],
                color="green",
                fill=True,
                fill_opacity=0.2,
            ).add_to(m)
        elif geom_type == "Rectangle" and coords:
            folium.Polygon(
                locations=[(lat, lon) for lon, lat in coords[0]],
                color="green",
                fill=True,
                fill_opacity=0.2,
            ).add_to(m)
        elif geom_type == "LineString" and coords:
            # Draw the polyline (keep it visible after drawing)
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
            length = max(pca_coords[:, 0]) - min(pca_coords[:, 0])
            buffer = 0.2 * length
            start = mean_coords + direction * (-length / 2 - buffer)
            end = mean_coords + direction * (length / 2 + buffer)
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

    return m
