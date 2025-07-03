"""
UI component for selecting boreholes and managing their state.
"""

import streamlit as st
from typing import List, Optional, Dict
import pandas as pd
import logging
from ..state import get_state, set_state
from core.config import get_config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BoreholeSelector:
    """
    UI component for borehole selection and management.
    """

    def __init__(self, loca_df: pd.DataFrame):
        """
        Initialize the borehole selector.

        Args:
            loca_df: Location data DataFrame
        """
        self.loca_df = loca_df
        self.borehole_ids = sorted(loca_df["LOCA_ID"].unique())

    @st.cache_data
    def _get_borehole_info(self, bh_id: str) -> str:
        """Get formatted info string for a borehole."""
        try:
            bh = self.loca_df[self.loca_df["LOCA_ID"] == bh_id].iloc[0]
            return (
                f"{bh_id} "
                f"(GL: {bh['LOCA_GL']:.1f}m, "
                f"Depth: {bh['LOCA_FDEP']:.1f}m)"
            )
        except Exception as e:
            logger.error(f"Error getting info for borehole {bh_id}: {str(e)}")
            return bh_id

    def render(
        self, key: str = "borehole_selector", default: Optional[List[str]] = None
    ) -> List[str]:
        """
        Render the borehole selection UI.

        Args:
            key: Unique key for the component
            default: Default selected boreholes

        Returns:
            List of selected borehole IDs
        """
        try:
            st.write("### Select Boreholes")

            col1, col2 = st.columns([4, 1])

            with col1:
                # Create selection options with info
                options = {self._get_borehole_info(bh): bh for bh in self.borehole_ids}

                selected = st.multiselect(
                    "Choose boreholes for the section:",
                    options=list(options.keys()),
                    default=default,
                    key=f"{key}_multiselect",
                )

                # Convert display names back to IDs
                selected_ids = [options[sel] for sel in selected]

            with col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("Select All", key=f"{key}_select_all"):
                    set_state(f"{key}_multiselect", list(options.keys()))
                    selected_ids = self.borehole_ids

                if st.button("Clear", key=f"{key}_clear"):
                    set_state(f"{key}_multiselect", [])
                    selected_ids = []

            # Store selection in state
            set_state("selected_boreholes", selected_ids)
            set_state("last_selection_change", key)  # Track changes

            return selected_ids

        except Exception as e:
            logger.error(f"Error rendering borehole selector: {str(e)}")
            st.error("Error displaying borehole selection interface")
            return default or []
