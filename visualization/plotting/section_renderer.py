"""Section plotting functionality."""

import streamlit as st
from typing import List, Tuple
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)

# Use fast style for better performance
plt.style.use("fast")


@dataclass
class SectionDimensions:
    """Container for section dimensions."""

    width: float
    height: float
    min_elevation: float
    max_elevation: float
    distances: List[float]


class SectionRenderer:
    """Handles geological section plotting."""

    def __init__(
        self, geol_df: pd.DataFrame, loca_df: pd.DataFrame, abbr_df: pd.DataFrame
    ):
        """Initialize with AGS dataframes."""
        self.geol_df = geol_df
        self.loca_df = loca_df
        self.abbr_df = abbr_df
        self._setup_colors()

    def _setup_colors(self) -> None:
        """Set up color mapping for geology types."""
        unique_legs = self.geol_df["GEOL_LEG"].unique()
        cmap = plt.cm.get_cmap("tab20")
        self.color_map = {leg: cmap(i % 20) for i, leg in enumerate(unique_legs)}

    @st.cache_data
    def calculate_dimensions(
        self,
        boreholes: List[str],
        vertical_exaggeration: float = 1.0,
    ) -> SectionDimensions:
        """Calculate section dimensions."""
        try:
            # Filter to selected boreholes
            loca = self.loca_df[self.loca_df["LOCA_ID"].isin(boreholes)]
            if loca.empty:
                raise ValueError("No valid boreholes selected")

            # Calculate elevations
            ground_levels = pd.to_numeric(loca["LOCA_GL"], errors="coerce")
            final_depths = pd.to_numeric(loca["LOCA_FDEP"], errors="coerce")

            if ground_levels.isna().all() or final_depths.isna().all():
                raise ValueError("No valid elevation data")

            min_elevation = (ground_levels - final_depths).min()
            max_elevation = ground_levels.max()

            # Calculate horizontal distances (simple linear spacing)
            distances = np.linspace(0, 100 * len(boreholes), len(boreholes))

            # Calculate dimensions
            width = max(1000, distances[-1])
            height = (max_elevation - min_elevation) * vertical_exaggeration

            return SectionDimensions(
                width=width,
                height=height,
                min_elevation=min_elevation,
                max_elevation=max_elevation,
                distances=distances.tolist(),
            )

        except Exception as e:
            logger.error(f"Error calculating section dimensions: {e}")
            raise

    def render_section(
        self,
        boreholes: List[str],
        vertical_exaggeration: float = 1.0,
        fig_width: float = 12,
        fig_height: float = 8,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Render the geological section."""
        try:
            # Calculate dimensions
            dims = self.calculate_dimensions(boreholes, vertical_exaggeration)

            # Create figure
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))

            # Plot each borehole
            for bh_id, distance in zip(boreholes, dims.distances):
                self._plot_borehole(ax, bh_id, distance, dims)

            # Setup axes and grid
            ax.set_xlim(-50, dims.distances[-1] + 50)
            ax.set_ylim(dims.min_elevation - 5, dims.max_elevation + 5)
            ax.grid(True, linestyle="--", alpha=0.7)

            # Labels
            ax.set_xlabel("Distance (m)")
            ax.set_ylabel("Elevation (mAOD)")
            ax.set_title("Geological Section", pad=20)

            return fig, ax

        except Exception as e:
            logger.error(f"Error rendering section: {e}")
            raise

    def _plot_borehole(
        self, ax: plt.Axes, bh_id: str, distance: float, dims: SectionDimensions
    ) -> None:
        """Plot a single borehole."""
        try:
            # Get borehole data
            loca = self.loca_df[self.loca_df["LOCA_ID"] == bh_id].iloc[0]
            geol = self.geol_df[self.geol_df["LOCA_ID"] == bh_id]

            ground_level = float(loca["LOCA_GL"])
            final_depth = float(loca["LOCA_FDEP"])

            # Plot borehole shaft
            ax.plot(
                [distance, distance],
                [ground_level, ground_level - final_depth],
                "k-",
                linewidth=1,
            )

            # Plot ground level marker
            ax.plot(
                [distance - 2, distance + 2],
                [ground_level, ground_level],
                "k-",
                linewidth=2,
            )

            # Plot geology layers
            for _, layer in geol.iterrows():
                top = float(layer["GEOL_TOP"])
                base = float(layer["GEOL_BASE"])
                legend = str(layer["GEOL_LEG"])

                # Rectangle for layer
                width = 4  # meters
                rect = plt.Rectangle(
                    (distance - width / 2, ground_level - base),
                    width,
                    base - top,
                    facecolor=self.color_map.get(legend, "gray"),
                    edgecolor="black",
                    linewidth=0.5,
                    alpha=0.7,
                )
                ax.add_patch(rect)

            # Add borehole ID
            ax.text(
                distance,
                dims.max_elevation + 1,
                bh_id,
                ha="center",
                va="bottom",
                rotation=45,
            )

        except Exception as e:
            logger.warning(f"Error plotting borehole {bh_id}: {e}")
            # Continue with other boreholes

    def add_section_captions(
        self, ax: plt.Axes, selected_boreholes: pd.DataFrame, dims: SectionDimensions
    ) -> None:
        """Add captions to sections."""
        try:
            # Example caption: Average depth of boreholes
            avg_depth = (
                selected_boreholes["LOCA_FDEP"] - selected_boreholes["LOCA_GL"]
            ).mean()
            caption = f"Avg. Depth: {avg_depth:.1f} m"

            # Add caption text
            ax.text(
                dims.distances[-1] - 10,
                dims.min_elevation + 2,
                caption,
                ha="right",
                va="bottom",
                fontsize=10,
                color="blue",
            )

        except Exception as e:
            logger.warning(f"Error adding section captions: {e}")
