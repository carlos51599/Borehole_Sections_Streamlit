import streamlit as st
from typing import Tuple, List, Dict, Optional
import matplotlib.pyplot as plt
import pandas as pd
import csv
import numpy as np
import os
import re
from pathlib import Path
import logging
from dataclasses import dataclass


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AGSData:
    """Container for AGS data groups"""

    geol_df: pd.DataFrame
    loca_df: pd.DataFrame
    abbr_df: pd.DataFrame


@st.cache_data
def parse_ags_geol_section(filepath: str) -> AGSData:
    """
    Parse the AGS file and extract GEOL, LOCA, and ABBR group data as DataFrames.
    Cached for better performance.

    Args:
        filepath: Path to AGS file

    Returns:
        AGSData object containing parsed DataFrames
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        parsed = list(csv.reader(lines, delimiter=",", quotechar='"'))

        # Parse each group
        geol_df = _parse_group(parsed, "GEOL")
        loca_df = _parse_group(parsed, "LOCA")
        abbr_df = _parse_group(parsed, "ABBR")

        # Convert numeric columns
        _convert_numeric_columns(geol_df, ["GEOL_TOP", "GEOL_BASE"])
        _convert_numeric_columns(loca_df, ["LOCA_GL", "LOCA_FDEP"])

        return AGSData(geol_df, loca_df, abbr_df)

    except Exception as e:
        logger.error(f"Error parsing AGS file {filepath}: {str(e)}")
        raise


@st.cache_data
def _parse_group(parsed_lines: List[List[str]], group_name: str) -> pd.DataFrame:
    """Parse a specific group from AGS data."""
    headings = []
    data = []
    in_group = False

    for row in parsed_lines:
        if not row:
            continue

        if row[0] == "GROUP" and len(row) > 1:
            if row[1] == group_name:
                in_group = True
            elif in_group:
                break
            continue

        if in_group:
            if row[0] == "HEADING":
                headings = row[1:]
            elif row[0] == "DATA":
                data.append(row[1 : len(headings) + 1])

    return pd.DataFrame(data, columns=headings)


def _convert_numeric_columns(df: pd.DataFrame, columns: List[str]) -> None:
    """Convert specified columns to numeric, handling errors."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


@st.cache_data
def calculate_section_dimensions(
    boreholes: List[str],
    geol_df: pd.DataFrame,
    loca_df: pd.DataFrame,
    buffer_factor: float = 0.1,
) -> Tuple[float, float, float, float]:
    """
    Calculate section dimensions with caching.

    Args:
        boreholes: List of borehole IDs
        geol_df: Geology DataFrame
        loca_df: Location DataFrame
        buffer_factor: Vertical buffer factor

    Returns:
        Tuple of (min_elev, max_elev, min_dist, max_dist)
    """
    try:
        # Filter for selected boreholes
        geol_bh = geol_df[geol_df["LOCA_ID"].isin(boreholes)]
        loca_bh = loca_df[loca_df["LOCA_ID"].isin(boreholes)]

        # Calculate ground levels
        ground_levels = loca_bh["LOCA_GL"].fillna(0).values

        # Calculate elevations
        min_depth = geol_bh["GEOL_BASE"].max()
        if pd.isna(min_depth):
            min_depth = 0

        min_elev = ground_levels.min() - abs(min_depth)
        max_elev = ground_levels.max()

        # Add buffer
        elev_range = max_elev - min_elev
        buffer = elev_range * buffer_factor
        min_elev -= buffer
        max_elev += buffer

        return min_elev, max_elev, 0, 100  # Default horizontal scale 0-100

    except Exception as e:
        logger.error(f"Error calculating section dimensions: {str(e)}")
        raise


@st.cache_data
def create_color_scheme(unique_legs: List[str]) -> Dict[str, Tuple[float, ...]]:
    """Create a cached color scheme for geological legends."""
    cmap = plt.cm.tab20
    return {leg: cmap(i % 20) for i, leg in enumerate(unique_legs)}


def plot_section_from_ags(
    filepath: str,
    boreholes: List[str],
    section_line: Optional[List[Tuple[float, float]]] = None,
    show_labels: bool = True,
    fig_size: Tuple[float, float] = None,
    dpi: int = 100,
) -> Optional[plt.Figure]:
    """
    Create a geological section plot from AGS data.

    Args:
        filepath: Path to AGS file
        boreholes: List of borehole IDs to include
        section_line: Optional section line coordinates
        show_labels: Whether to show labels
        fig_size: Optional figure size (width, height)
        dpi: DPI for the figure

    Returns:
        matplotlib Figure or None if error
    """
    try:
        # Parse AGS data
        ags_data = parse_ags_geol_section(filepath)

        # Filter for selected boreholes
        geol_bh = ags_data.geol_df[ags_data.geol_df["LOCA_ID"].isin(boreholes)]
        loca_bh = ags_data.loca_df[ags_data.loca_df["LOCA_ID"].isin(boreholes)]

        if geol_bh.empty or loca_bh.empty:
            logger.warning("No data found for selected boreholes")
            return None

        # Calculate section dimensions
        min_elev, max_elev, min_dist, max_dist = calculate_section_dimensions(
            boreholes, geol_bh, loca_bh
        )

        # Create figure
        if not fig_size:
            fig_size = (max(8, len(boreholes) * 1.5), 6)
        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)

        # Create color scheme
        unique_legs = geol_bh["GEOL_LEG"].unique()
        color_map = create_color_scheme(unique_legs)

        # Plot each borehole
        plot_boreholes(
            ax,
            boreholes,
            geol_bh,
            loca_bh,
            color_map,
            ags_data.abbr_df if not ags_data.abbr_df.empty else None,
            show_labels,
        )

        # Set plot limits and labels
        ax.set_ylim(min_elev, max_elev)
        ax.set_xlim(min_dist, max_dist)
        ax.set_xlabel("Distance along section (m)")
        ax.set_ylabel("Elevation (mOD)")

        # Add legend if showing labels
        if show_labels:
            add_legend(ax, color_map, ags_data.abbr_df)

        plt.tight_layout()
        return fig

    except Exception as e:
        logger.error(f"Error creating section plot: {str(e)}")
        return None


@st.cache_data
def plot_boreholes(
    ax: plt.Axes,
    boreholes: List[str],
    geol_df: pd.DataFrame,
    loca_df: pd.DataFrame,
    color_map: Dict[str, Tuple[float, ...]],
    abbr_df: Optional[pd.DataFrame] = None,
    show_labels: bool = True,
) -> None:
    """Plot individual boreholes with caching."""
    try:
        x_positions = np.linspace(0, 100, len(boreholes))

        for bh, x_pos in zip(boreholes, x_positions):
            # Get borehole data
            geol_bh = geol_df[geol_df["LOCA_ID"] == bh].sort_values("GEOL_TOP")
            loca_info = loca_df[loca_df["LOCA_ID"] == bh].iloc[0]

            # Plot ground level
            gl = float(loca_info.get("LOCA_GL", 0))
            ax.plot([x_pos, x_pos], [gl - 1, gl + 1], "k-", linewidth=2)

            # Add borehole ID
            if show_labels:
                ax.text(x_pos, gl + 2, bh, ha="center", va="bottom")

            # Plot geological layers
            plot_layers(ax, geol_bh, x_pos, gl, color_map, show_labels)

    except Exception as e:
        logger.error(f"Error plotting boreholes: {str(e)}")


def plot_layers(
    ax: plt.Axes,
    geol_df: pd.DataFrame,
    x_pos: float,
    gl: float,
    color_map: Dict[str, Tuple[float, ...]],
    show_labels: bool = True,
) -> None:
    """Plot geological layers for a single borehole."""
    width = 4  # Width of the borehole column

    for _, layer in geol_df.iterrows():
        try:
            top = gl - abs(float(layer["GEOL_TOP"]))
            base = gl - abs(float(layer["GEOL_BASE"]))
            leg = layer["GEOL_LEG"]

            # Plot layer rectangle
            rect = plt.Rectangle(
                (x_pos - width / 2, base),
                width,
                top - base,
                facecolor=color_map.get(leg, (0.7, 0.7, 0.7, 1.0)),
                edgecolor="black",
                linewidth=0.5,
            )
            ax.add_patch(rect)

            # Add layer label
            if show_labels:
                ax.text(
                    x_pos + width / 2 + 0.5,
                    (top + base) / 2,
                    leg,
                    va="center",
                    ha="left",
                    fontsize=8,
                )

        except Exception as e:
            logger.error(
                f"Error plotting layer {layer.get('GEOL_LEG', 'unknown')}: {str(e)}"
            )


def add_legend(
    ax: plt.Axes,
    color_map: Dict[str, Tuple[float, ...]],
    abbr_df: Optional[pd.DataFrame],
) -> None:
    """Add a legend to the plot."""
    legend_elements = []

    for leg, color in color_map.items():
        # Get description from ABBR if available
        if abbr_df is not None and "ABBR_CODE" in abbr_df.columns:
            desc = (
                abbr_df[abbr_df["ABBR_CODE"] == leg]["ABBR_DESC"].iloc[0]
                if not abbr_df[abbr_df["ABBR_CODE"] == leg].empty
                else leg
            )
        else:
            desc = leg

        patch = plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor="black")
        legend_elements.append((patch, f"{desc} ({leg})"))

    if legend_elements:
        ax.legend(
            [item[0] for item in legend_elements],
            [item[1] for item in legend_elements],
            loc="center left",
            bbox_to_anchor=(1.05, 0.5),
            fontsize=8,
        )
