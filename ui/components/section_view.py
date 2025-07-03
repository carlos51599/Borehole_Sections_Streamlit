"""
Section view state management and UI controls.
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
import logging
from core.config import get_config
from ..state import get_state, set_state
from visualization.plotting import SectionRenderer


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SectionViewState:
    """Container for section view state"""

    selected_boreholes: List[str]
    section_line: Optional[List[Tuple[float, float]]]
    vertical_exaggeration: float
    show_labels: bool
    show_legend: bool
    width: float
    height: float


class SectionViewController:
    """Controller for section view state and UI"""

    def __init__(self):
        """Initialize the section view controller."""
        self.config = get_config()

    def init_state(self) -> None:
        """Initialize section view state."""
        if "section_view" not in st.session_state:
            st.session_state.section_view = {
                "selected_boreholes": [],
                "section_line": None,
                "vertical_exaggeration": self.config["plot"]["vertical_exaggeration"],
                "show_labels": self.config["ui"]["show_labels"],
                "show_legend": self.config["ui"]["show_legend"],
                "width": self.config["plot"]["default_width"],
                "height": self.config["plot"]["default_height"],
            }

    def get_state(self) -> SectionViewState:
        """Get current section view state."""
        self.init_state()
        return SectionViewState(**st.session_state.section_view)

    def update_state(self, **kwargs) -> None:
        """Update section view state."""
        self.init_state()
        st.session_state.section_view.update(kwargs)

    def handle_section_line_update(self, coords: List[Tuple[float, float]]) -> None:
        """
        Handle section line coordinate updates.

        Args:
            coords: List of coordinate pairs defining section line
        """
        try:
            if len(coords) < 2:
                logger.warning("Section line needs at least 2 points")
                return

            self.update_state(section_line=coords)

            # Calculate distances and update plot
            distances = np.cumsum(
                [
                    np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)
                    for p1, p2 in zip(coords[:-1], coords[1:])
                ]
            )
            set_state("section_distances", [0] + list(distances))

        except Exception as e:
            logger.error(f"Error updating section line: {str(e)}")
            st.error("Error updating section line")

    def render_controls(self) -> None:
        """Render section view controls."""
        try:
            st.sidebar.write("### Section View Controls")

            # Get current state
            state = self.get_state()

            # Plot controls
            exag = st.sidebar.slider(
                "Vertical Exaggeration",
                min_value=1.0,
                max_value=10.0,
                value=state.vertical_exaggeration,
                step=0.5,
            )

            show_labels = st.sidebar.checkbox("Show Labels", value=state.show_labels)

            show_legend = st.sidebar.checkbox("Show Legend", value=state.show_legend)

            # Advanced options
            with st.sidebar.expander("Advanced Options"):
                width = st.number_input(
                    "Plot Width (inches)",
                    min_value=6.0,
                    max_value=24.0,
                    value=state.width,
                )

                height = st.number_input(
                    "Plot Height (inches)",
                    min_value=4.0,
                    max_value=18.0,
                    value=state.height,
                )

            # Update state if changed
            self.update_state(
                vertical_exaggeration=exag,
                show_labels=show_labels,
                show_legend=show_legend,
                width=width,
                height=height,
            )

        except Exception as e:
            logger.error(f"Error rendering section controls: {str(e)}")
            st.error("Error displaying section controls")
