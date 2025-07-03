"""Borehole log visualization."""

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import logging


logger = logging.getLogger(__name__)


class BoreholeLogRenderer:
    """Handles borehole log visualization."""

    def __init__(
        self, geol_df: pd.DataFrame, loca_df: pd.DataFrame, abbr_df: pd.DataFrame
    ):
        """Initialize with AGS dataframes."""
        self.geol_df = geol_df
        self.loca_df = loca_df
        self.abbr_df = abbr_df
        self._setup_colors()

    def _setup_colors(self) -> None:
        """Setup color mapping for geology types."""
        unique_legs = self.geol_df["GEOL_LEG"].unique()
        cmap = plt.cm.get_cmap("tab20")
        self.color_map = {leg: cmap(i % 20) for i, leg in enumerate(unique_legs)}

    @st.cache_data
    def get_borehole_info(self, bh_id: str) -> dict:
        """Get basic info for a borehole."""
        try:
            loca = self.loca_df[self.loca_df["LOCA_ID"] == bh_id]
            if loca.empty:
                raise ValueError(f"Borehole {bh_id} not found")

            geol = self.geol_df[self.geol_df["LOCA_ID"] == bh_id]
            if geol.empty:
                raise ValueError(f"No geology data for borehole {bh_id}")

            ground_level = float(loca.iloc[0].get("LOCA_GL", 0))
            max_depth = float(geol["GEOL_BASE"].max())

            return {
                "ground_level": ground_level,
                "max_depth": max_depth,
                "location": loca.iloc[0].to_dict(),
                "geology": geol.sort_values("GEOL_TOP").to_dict("records"),
            }

        except Exception as e:
            logger.error(f"Error getting borehole info: {e}")
            raise

    def render_log(self, bh_id: str, show_labels: bool = True) -> plt.Figure:
        """Render a borehole log."""
        try:
            # Get borehole data
            info = self.get_borehole_info(bh_id)
            ground_level = info["ground_level"]
            max_depth = info["max_depth"]
            geology = pd.DataFrame(info["geology"])

            # Calculate dimensions
            height = max(6, max_depth * 0.23)  # scale with depth, min 6 inches
            width = 2.5  # fixed width

            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=100)
            plt.subplots_adjust(left=0.25, right=0.75, top=0.98, bottom=0.08)

            # Plot geology layers
            for _, layer in geology.iterrows():
                top = float(layer["GEOL_TOP"])
                base = float(layer["GEOL_BASE"])
                legend = str(layer["GEOL_LEG"])

                # Get description if available
                desc = legend
                if not self.abbr_df.empty:
                    match = self.abbr_df[self.abbr_df["ABBR_CODE"] == legend]
                    if not match.empty:
                        desc = f"{match.iloc[0]['ABBR_DESC']} ({legend})"

                # Plot layer
                rect = plt.Rectangle(
                    (-0.5, top),
                    1.0,  # width of log
                    base - top,
                    facecolor=self.color_map.get(legend, "gray"),
                    edgecolor="black",
                    linewidth=0.5,
                    label=desc if show_labels else None,
                )
                ax.add_patch(rect)

                # Add labels if requested
                if show_labels:
                    ax.text(
                        0.6,  # position right of log
                        (top + base) / 2,
                        desc,
                        va="center",
                        fontsize=8,
                    )

            # Setup axes
            ax.set_xlim(-0.6, 2.0 if show_labels else 0.6)
            ax.set_ylim(max_depth + 1, -1)

            # Grid and labels
            ax.grid(True, linestyle=":", alpha=0.5)
            ax.set_xticks([])
            ax.set_ylabel("Depth (m)")

            # Add title
            ax.set_title(
                f"Borehole: {bh_id}\nGround Level: {ground_level:.1f} mAOD", pad=10
            )

            return fig

        except Exception as e:
            logger.error(f"Error rendering borehole log: {e}")
            raise
