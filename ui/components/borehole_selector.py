"""
UI component for managing borehole selection state from map interactions.
"""

import streamlit as st
import pandas as pd
import logging
from ..state import get_state, set_state
from visualization.mapping.map_utils import filter_selection_by_shape

logger = logging.getLogger(__name__)


class BoreholeSelector:
    """Handles borehole selection state from map interactions."""

    def __init__(self, loca_df: pd.DataFrame):
        """
        Initialize the borehole selector.

        Args:
            loca_df: Location data DataFrame
        """
        self.loca_df = loca_df.copy()
        self.borehole_ids = sorted(loca_df["LOCA_ID"].unique())

    def render(self) -> pd.DataFrame:
        """
        Handle map-based borehole selection.

        Returns:
            DataFrame of selected boreholes
        """
        try:
            # Handle drawn shapes
            drawn_shapes = get_state("drawn_shapes")
            if drawn_shapes:
                filtered_df, _ = filter_selection_by_shape(drawn_shapes, self.loca_df)
                if not filtered_df.empty:
                    n_selected = len(filtered_df)
                    st.write(
                        f"Selected {n_selected} borehole{'s' if n_selected != 1 else ''}"
                    )

                    if st.button("Clear Selection"):
                        set_state("drawn_shapes", None)
                        filtered_df = pd.DataFrame()

                    return filtered_df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error handling borehole selection: {str(e)}")
            return pd.DataFrame()
