import streamlit as st
from section_plot import plot_section_from_ags
from sklearn.decomposition import PCA
import pyproj
import os
import tempfile
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd


@st.cache_data
def calculate_section_line(
    selected_df: pd.DataFrame, last_shape: Dict[str, Any] = None
) -> Optional[List[Tuple[float, float]]]:
    """
    Calculate the section line either from a drawn line or using PCA.
    Uses caching to avoid recalculating for the same inputs.
    """
    if last_shape and last_shape.get("type") == "LineString":
        coords = last_shape.get("coordinates", [])
        if coords and all(
            col in selected_df.columns
            for col in ["lat", "lon", "LOCA_NATE", "LOCA_NATN"]
        ):
            transformer = pyproj.Transformer.from_crs(
                "epsg:4326", "epsg:27700", always_xy=True
            )
            return [transformer.transform(lon, lat) for lon, lat in coords]

    # If no line drawn, use PCA to determine section line
    if (
        not selected_df.empty
        and "LOCA_NATE" in selected_df.columns
        and "LOCA_NATN" in selected_df.columns
        and not selected_df[["LOCA_NATE", "LOCA_NATN"]].isnull().any().any()
    ):
        try:
            pca = PCA(n_components=2)
            coords = selected_df[["LOCA_NATE", "LOCA_NATN"]].values
            pca_coords = pca.fit_transform(coords)
            mean_coords = coords.mean(axis=0)
            direction = pca.components_[0]

            # Calculate section line length with buffer
            length = np.ptp(pca_coords[:, 0])  # max - min
            buffer = 0.2 * length
            total_length = length + 2 * buffer

            # Calculate start and end points
            start = mean_coords - direction * (total_length / 2)
            end = mean_coords + direction * (total_length / 2)

            return [(start[0], start[1]), (end[0], end[1])]
        except Exception as e:
            st.error(f"Error calculating section line: {str(e)}")
            return None

    return None


@st.cache_data
def prepare_file_data(
    filtered_ids: List[str], selected: pd.DataFrame, filename_map: Dict[str, str]
) -> Dict[str, List[str]]:
    """
    Prepare and cache the mapping of files to borehole IDs.
    """
    id_to_file = selected.set_index("LOCA_ID")["ags_file"].to_dict()
    file_to_ids = {}

    for fname in filename_map:
        ids = [bh for bh in filtered_ids if id_to_file.get(bh) == fname]
        if ids:
            file_to_ids[fname] = ids

    return file_to_ids


def generate_section_plot(
    filtered_ids: List[str],
    selected: pd.DataFrame,
    filename_map: Dict[str, str],
    show_labels: bool = True,
) -> Optional[plt.Figure]:
    """
    Generate a geological section plot from selected boreholes.

    Args:
        filtered_ids: List of selected borehole IDs
        selected: DataFrame containing selected borehole data
        filename_map: Dictionary mapping filenames to AGS content
        show_labels: Whether to show labels on the plot

    Returns:
        matplotlib Figure object or None if plot generation fails
    """
    try:
        if not filtered_ids:
            st.warning("No boreholes selected for section plot.")
            return None

        # Calculate section line
        section_line = calculate_section_line(
            selected, st.session_state.get("last_drawn_shape", {})
        )
        if not section_line:
            st.warning("Could not determine section line orientation.")
            return None

        # Prepare file data
        file_to_ids = prepare_file_data(filtered_ids, selected, filename_map)
        if not file_to_ids:
            st.warning("No valid files found for selected boreholes.")
            return None

        # Process each file
        for fname, content in filename_map.items():
            if fname not in file_to_ids:
                continue

            # Write AGS content to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".ags", delete=False
            ) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            try:
                # Generate plot for this file
                return plot_section_from_ags(
                    temp_path, file_to_ids[fname], section_line, show_labels=show_labels
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass

    except Exception as e:
        st.error(f"Error generating section plot: {str(e)}")
        return None
