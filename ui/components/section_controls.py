"""
UI component for section visualization controls.
"""

import streamlit as st
from dataclasses import dataclass
import logging
from ..state import get_state, set_state
from core.config import get_config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SectionControlState:
    """Container for section control settings"""

    vertical_exaggeration: float
    show_labels: bool
    show_legend: bool
    dpi: int
    width: float
    height: float


class SectionControls:
    """
    UI component for section visualization controls.
    """

    def __init__(self):
        """Initialize the section controls."""
        pass

    def render(self, key: str = "section_controls") -> SectionControlState:
        """
        Render the section control UI.

        Args:
            key: Unique key for the component

        Returns:
            SectionControlState with current settings
        """
        try:
            # Get configuration
            config = get_config()
            plot_config = config["plot"]
            ui_config = config["ui"]

            st.write("### Section Controls")

            col1, col2 = st.columns(2)

            with col1:
                vert_exag = st.slider(
                    "Vertical Exaggeration",
                    min_value=1.0,
                    max_value=10.0,
                    value=get_state(
                        f"{key}_vert_exag", plot_config["vertical_exaggeration"]
                    ),
                    step=0.5,
                    key=f"{key}_vert_exag",
                )

                show_labels = st.checkbox(
                    "Show Labels",
                    value=get_state(f"{key}_show_labels", ui_config["show_labels"]),
                    key=f"{key}_show_labels",
                )

            with col2:
                show_legend = st.checkbox(
                    "Show Legend",
                    value=get_state(f"{key}_show_legend", ui_config["show_legend"]),
                    key=f"{key}_show_legend",
                )

                dpi = st.select_slider(
                    "Plot DPI",
                    options=[72, 100, 150, 200, 300],
                    value=get_state(f"{key}_dpi", plot_config["default_dpi"]),
                    key=f"{key}_dpi",
                )

            # Advanced options in expander
            with st.expander("Advanced Plot Settings"):
                width = st.number_input(
                    "Plot Width (inches)",
                    min_value=6.0,
                    max_value=plot_config["max_width"],
                    value=get_state(f"{key}_width", plot_config["default_width"]),
                    step=1.0,
                    key=f"{key}_width",
                )

                height = st.number_input(
                    "Plot Height (inches)",
                    min_value=4.0,
                    max_value=plot_config["max_height"],
                    value=get_state(f"{key}_height", plot_config["default_height"]),
                    step=1.0,
                    key=f"{key}_height",
                )

                if st.button("Reset to Defaults", key=f"{key}_reset"):
                    settings = [
                        "width",
                        "height",
                        "dpi",
                        "vert_exag",
                        "show_labels",
                        "show_legend",
                    ]
                    for setting in settings:
                        st.session_state.pop(f"{key}_{setting}", None)

            return SectionControlState(
                vertical_exaggeration=vert_exag,
                show_labels=show_labels,
                show_legend=show_legend,
                dpi=dpi,
                width=width,
                height=height,
            )

        except Exception as e:
            logger.error(f"Error rendering section controls: {str(e)}")
            st.error("Error displaying section control interface")
            return SectionControlState(2.0, True, True, 100, 12.0, 8.0)
