import streamlit as st
from section_plot import plot_section_from_ags
from sklearn.decomposition import PCA
import pyproj


def generate_section_plot(filtered_ids, selected, filename_map):
    section_fig = None
    id_to_file = selected.set_index("LOCA_ID")["ags_file"].to_dict()
    section_line = None
    last_shape = st.session_state.get("last_drawn_shape", {})
    if last_shape.get("type") == "LineString":
        coords = last_shape.get("coordinates", [])
        if (
            coords
            and "lat" in selected.columns
            and "lon" in selected.columns
            and "LOCA_NATE" in selected.columns
            and "LOCA_NATN" in selected.columns
        ):
            transformer = pyproj.Transformer.from_crs(
                "epsg:4326", "epsg:27700", always_xy=True
            )
            section_line = [transformer.transform(lon, lat) for lon, lat in coords]
    elif (
        selected is not None
        and not selected.empty
        and "LOCA_NATE" in selected.columns
        and "LOCA_NATN" in selected.columns
        and not selected[["LOCA_NATE", "LOCA_NATN"]].isnull().any().any()
    ):
        pca = PCA(n_components=2)
        pca_coords = pca.fit_transform(selected[["LOCA_NATE", "LOCA_NATN"]])
        mean_coords = selected[["LOCA_NATE", "LOCA_NATN"]].mean().values
        direction = pca.components_[0]
        length = max(pca_coords[:, 0]) - min(pca_coords[:, 0])
        buffer = 0.2 * length
        start = mean_coords + direction * (-length / 2 - buffer)
        end = mean_coords + direction * (length / 2 + buffer)
        section_line = (tuple(start), tuple(end))

    for fname, content in filename_map.items():
        ids_for_file = [bh for bh in filtered_ids if id_to_file.get(bh) == fname]
        if not ids_for_file:
            continue
        ags_temp_path = f"/tmp/{fname}"
        with open(ags_temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        section_fig = plot_section_from_ags(
            ags_file=ags_temp_path,
            filter_loca_ids=ids_for_file,
            section_line=section_line,
        )
        if section_fig:
            st.pyplot(section_fig)
        else:
            st.warning(f"No section plot generated for {fname}. Check GEOL data.")
    return section_fig
