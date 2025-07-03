"""
Borehole log visualization module.
"""

import streamlit as st
from typing import Optional, Tuple, Dict, List
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
from .utils import create_figure, setup_axes, add_grid, format_labels


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LogDimensions:
    """Container for log plot dimensions"""

    width: float
    height: float
    depth_range: Tuple[float, float]
    margin: float = 0.1


class BoreholeLogRenderer:
    """Class for rendering detailed borehole logs"""

    def __init__(
        self, geol_df: pd.DataFrame, loca_df: pd.DataFrame, abbr_df: pd.DataFrame
    ):
        """
        Initialize the borehole log renderer.

        Args:
            geol_df: DataFrame containing geological data
            loca_df: DataFrame containing location data
            abbr_df: DataFrame containing abbreviation definitions
        """
        self.geol_df = geol_df
        self.loca_df = loca_df
        self.abbr_df = abbr_df

    @st.cache_data
    def calculate_dimensions(
        self, bh_id: str, width: float = 8, height: float = 12
    ) -> LogDimensions:
        """
        Calculate dimensions for the log plot.

        Args:
            bh_id: Borehole ID to plot
            width: Plot width in inches
            height: Plot height in inches

        Returns:
            LogDimensions object

        Raises:
            ValueError: If borehole data is not found
        """
        try:
            # Get borehole data
            geol_bh = self.geol_df[self.geol_df["LOCA_ID"] == bh_id]
            if geol_bh.empty:
                raise ValueError(f"No geological data found for borehole {bh_id}")

            # Calculate depth range
            min_depth = 0
            max_depth = geol_bh["GEOL_BASE"].max()
            if pd.isna(max_depth):
                max_depth = geol_bh["GEOL_TOP"].max()
            if pd.isna(max_depth):
                raise ValueError(f"No valid depth data for borehole {bh_id}")

            # Add margins
            margin = (max_depth - min_depth) * 0.1

            return LogDimensions(
                width=width,
                height=height,
                depth_range=(min_depth - margin, max_depth + margin),
                margin=margin,
            )

        except Exception as e:
            logger.error(f"Error calculating log dimensions: {str(e)}")
            raise

    def render_log(
        self,
        bh_id: str,
        dimensions: LogDimensions,
        show_legend: bool = True,
        show_grid: bool = True,
        dpi: int = 100,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        Create a detailed borehole log plot.

        Args:
            bh_id: Borehole ID to plot
            dimensions: Plot dimensions
            show_legend: Whether to show legend
            show_grid: Whether to show grid
            dpi: Plot resolution

        Returns:
            Tuple of (Figure, Axes)

        Raises:
            ValueError: If borehole data is invalid
        """
        try:
            # Create figure
            fig, ax = create_figure(
                figsize=(dimensions.width, dimensions.height), dpi=dpi
            )

            # Get borehole data
            geol_bh = self.geol_df[self.geol_df["LOCA_ID"] == bh_id]
            loca_info = self.loca_df[self.loca_df["LOCA_ID"] == bh_id].iloc[0]

            # Plot geological layers
            self._plot_layers(ax, geol_bh, loca_info)

            # Setup axes
            setup_axes(
                ax,
                xlim=(-2, 6),
                ylim=dimensions.depth_range[::-1],  # Reverse for depth
                xlabel="Description",
                ylabel="Depth (m)",
                title=f"Borehole Log: {bh_id}",
            )

            if show_grid:
                add_grid(ax)

            # Add legend if needed
            if show_legend:
                self._add_legend(ax, geol_bh)

            return fig, ax

        except Exception as e:
            logger.error(f"Error rendering borehole log: {str(e)}")
            raise

    def _plot_layers(
        self, ax: plt.Axes, geol_data: pd.DataFrame, loca_info: pd.Series
    ) -> None:
        """Plot geological layers for a borehole."""
        try:
            gl = float(loca_info.get("LOCA_GL", 0))

            for _, layer in geol_data.iterrows():
                top = float(layer["GEOL_TOP"])
                base = float(layer["GEOL_BASE"])
                leg = layer["GEOL_LEG"]
                desc = layer.get("GEOL_DESC", "")

                # Plot layer rectangle
                rect = plt.Rectangle(
                    (-1, top),
                    2,
                    base - top,
                    facecolor="white",
                    edgecolor="black",
                    linewidth=0.5,
                )
                ax.add_patch(rect)

                # Add legend code
                ax.text(-0.5, (top + base) / 2, leg, ha="center", va="center")

                # Add description
                if desc:
                    ax.text(
                        2.2,
                        (top + base) / 2,
                        desc,
                        ha="left",
                        va="center",
                        fontsize=8,
                        wrap=True,
                    )

        except Exception as e:
            logger.error(f"Error plotting layers: {str(e)}")
            raise

    def _add_legend(self, ax: plt.Axes, geol_data: pd.DataFrame) -> None:
        """Add a legend explaining geological codes."""
        try:
            legend_entries = []
            seen_codes = set()

            for _, layer in geol_data.iterrows():
                code = layer["GEOL_LEG"]
                if code in seen_codes:
                    continue
                seen_codes.add(code)

                # Get description from abbreviations
                if not self.abbr_df.empty:
                    desc = (
                        self.abbr_df[self.abbr_df["ABBR_CODE"] == code][
                            "ABBR_DESC"
                        ].iloc[0]
                        if not self.abbr_df[self.abbr_df["ABBR_CODE"] == code].empty
                        else code
                    )
                else:
                    desc = code

                # Create legend entry
                patch = plt.Rectangle(
                    (0, 0), 1, 1, facecolor="white", edgecolor="black"
                )
                legend_entries.append((patch, f"{code} - {desc}"))

            if legend_entries:
                ax.legend(
                    [item[0] for item in legend_entries],
                    [item[1] for item in legend_entries],
                    loc="center left",
                    bbox_to_anchor=(1.05, 0.5),
                    fontsize=8,
                )

        except Exception as e:
            logger.error(f"Error adding legend: {str(e)}")
            raise
