"""
Core section rendering functionality for geological borehole sections.
"""

import streamlit as st
from typing import Tuple, List, Optional, Dict
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
from .utils import create_figure, setup_axes, add_grid, format_labels
from core.config import AppConfig


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use fast style if enabled
if AppConfig.USE_FAST_STYLE:
    plt.style.use("fast")


@dataclass
class SectionDimensions:
    """Container for section plot dimensions"""

    width: float
    height: float
    min_elevation: float
    max_elevation: float
    distances: List[float]


class SectionRenderer:
    """
    Class for rendering geological section plots.

    This class handles the rendering of geological cross-sections from borehole data.
    It provides methods for calculating section dimensions, plotting boreholes and
    their geological layers, and managing visual elements like labels and legends.

    The renderer caches calculations and plot components for better performance.

    Attributes:
        geol_df (pd.DataFrame): DataFrame containing geological layer data
        loca_df (pd.DataFrame): DataFrame containing borehole location data
        abbr_df (pd.DataFrame): DataFrame containing abbreviation definitions
    """

    def __init__(
        self, geol_df: pd.DataFrame, loca_df: pd.DataFrame, abbr_df: pd.DataFrame
    ) -> None:
        """
        Initialize the section renderer.

        Args:
            geol_df: DataFrame containing geological layer data with columns:
                    LOCA_ID, GEOL_TOP, GEOL_BASE, GEOL_LEG
            loca_df: DataFrame containing borehole locations with columns:
                    LOCA_ID, LOCA_GL, LOCA_FDEP
            abbr_df: DataFrame containing abbreviation definitions with columns:
                    ABBR_CODE, ABBR_DESC
        """
        self.geol_df = geol_df
        self.loca_df = loca_df
        self.abbr_df = abbr_df
        self._setup_color_cache()

    def _setup_color_cache(self) -> None:
        """Setup cached color mapping for geological legends."""
        unique_legs = self.geol_df["GEOL_LEG"].unique()
        cmap = plt.cm.get_cmap("tab20")
        self.color_map = {leg: cmap(i % 20) for i, leg in enumerate(unique_legs)}

    @st.cache_data(ttl=AppConfig.CACHE_TTL)
    def calculate_dimensions(
        self,
        boreholes: List[str],
        vertical_exaggeration: float = 1.0,
    ) -> SectionDimensions:
        """
        Calculate optimized dimensions for the section plot.

        This method computes the optimal dimensions for the section plot based on:
        - Ground levels of the boreholes
        - Maximum depth of geological data
        - Desired vertical exaggeration
        - Optional fixed section width

        The calculations are cached for better performance.

        Args:
            boreholes: List of borehole IDs to include in the section
            vertical_exaggeration: Factor to exaggerate vertical scale,
                                 useful for highlighting subtle changes

        Returns:
            SectionDimensions object containing:
            - width: Plot width in plotting units
            - height: Plot height in plotting units
            - min_elevation: Minimum elevation for plot limits
            - max_elevation: Maximum elevation for plot limits
            - distances: List of horizontal distances for each borehole

        Raises:
            ValueError: If no valid borehole data is found
            KeyError: If required columns are missing from DataFrames
        """
        try:
            # Vectorized operations for better performance
            mask = self.loca_df["LOCA_ID"].isin(boreholes)
            ground_levels = self.loca_df.loc[mask, "LOCA_GL"].fillna(0).values

            geol_mask = self.geol_df["LOCA_ID"].isin(boreholes)
            min_depth = self.geol_df.loc[geol_mask, "GEOL_BASE"].max()

            if pd.isna(min_depth):
                min_depth = 0

            min_elev = ground_levels.min() - abs(min_depth)
            max_elev = ground_levels.max()

            # Add buffer
            elev_range = max_elev - min_elev
            buffer = elev_range * 0.1
            min_elev -= buffer
            max_elev += buffer

            # Calculate horizontal distances
            distances = np.linspace(0, 100, len(boreholes))

            # Calculate dimensions
            width = max(8, len(boreholes) * 1.5)
            height = width * vertical_exaggeration * 0.6

            return SectionDimensions(
                width=width,
                height=height,
                min_elevation=min_elev,
                max_elevation=max_elev,
                distances=distances.tolist(),
            )

        except Exception as e:
            logger.error(f"Error calculating dimensions: {str(e)}")
            raise

    def _create_layer_patches(
        self,
        geol_data: pd.DataFrame,
        x_pos: float,
        gl: float,
        width: float,
    ) -> Tuple[List[plt.Rectangle], List[Dict]]:
        """Vectorized creation of layer patches."""
        tops = gl - np.abs(geol_data["GEOL_TOP"].astype(float).values)
        bases = gl - np.abs(geol_data["GEOL_BASE"].astype(float).values)
        legs = geol_data["GEOL_LEG"].values

        patches = []
        labels = []

        for top, base, leg in zip(tops, bases, legs):
            rect = plt.Rectangle(
                (x_pos - width / 2, base),
                width,
                top - base,
                facecolor=self.color_map.get(leg, (0.7, 0.7, 0.7, 1.0)),
                edgecolor="black",
                linewidth=0.5,
            )
            patches.append(rect)
            labels.append(
                {
                    "x": x_pos + width / 2 + 0.5,
                    "y": (top + base) / 2,
                    "text": leg,
                }
            )

        return patches, labels

    @st.cache_data
    def render_section(
        self,
        boreholes: List[str],
        dimensions: SectionDimensions,
        title: Optional[str] = None,
        show_grid: bool = True,
        show_labels: bool = True,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        Render the geological section plot.

        This method creates a complete geological section visualization including:
        - Ground level markers for each borehole
        - Geological layers with proper symbology
        - Borehole labels and descriptions
        - Grid lines and axes labels
        - Optional title

        The rendering is cached for better performance. Changes to input parameters
        will trigger a re-render.

        Args:
            boreholes: List of borehole IDs to include in the section
            dimensions: SectionDimensions object with plot sizing information
            title: Optional title for the plot
            show_grid: Whether to display grid lines (default: True)
            show_labels: Whether to show borehole and layer labels (default: True)

        Returns:
            Tuple containing:
            - matplotlib Figure object
            - matplotlib Axes object with the rendered section

        Raises:
            ValueError: If borehole data is missing or inconsistent
            RuntimeError: If rendering fails
        """
        try:
            # Create figure
            fig, ax = create_figure(
                figsize=(dimensions.width / 2, dimensions.height / 2)
            )

            # Setup axes
            setup_axes(
                ax,
                xlim=(0, dimensions.width),
                ylim=(dimensions.min_elevation, dimensions.max_elevation),
                title=title,
            )

            # Add grid
            add_grid(ax)

            # Plot boreholes
            for bh_id, distance in zip(boreholes, dimensions.distances):
                self._plot_borehole(ax, bh_id, distance)

            # Format labels
            format_labels(ax)

            return fig, ax

        except Exception as e:
            logger.error(f"Error rendering section: {str(e)}")
            raise

    def _plot_borehole(self, ax: plt.Axes, bh_id: str, distance: float) -> None:
        """Plot a single borehole on the section."""
        try:
            # Get borehole data
            bh_geol = self.geol_df[self.geol_df["LOCA_ID"] == bh_id]
            bh_loca = self.loca_df[self.loca_df["LOCA_ID"] == bh_id].iloc[0]

            # Plot ground level
            ground_level = float(bh_loca["LOCA_GL"])
            ax.plot([distance], [ground_level], "k^")

            # Plot geology
            patches, labels = self._create_layer_patches(
                bh_geol, distance, ground_level, width=1
            )
            for patch in patches:
                ax.add_patch(patch)

            # Add legend text
            for label in labels:
                ax.text(
                    label["x"],
                    label["y"],
                    label["text"],
                    verticalalignment="center",
                )

            # Add borehole ID
            ax.text(distance, ground_level + 1, bh_id, horizontalalignment="center")

        except Exception as e:
            logger.error(f"Error plotting borehole {bh_id}: {str(e)}")
            raise
