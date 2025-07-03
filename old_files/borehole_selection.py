import streamlit as st
from typing import List
import pandas as pd
from math import ceil


@st.cache_data
def calculate_grid_layout(total_items: int, cols: int = 6) -> tuple[int, int]:
    """
    Calculate the optimal grid layout for the given number of items.

    Args:
        total_items: Total number of items to display
        cols: Maximum number of columns (default: 6)

    Returns:
        Tuple of (rows, actual_cols)
    """
    rows = ceil(total_items / cols)
    actual_cols = min(cols, total_items)
    return rows, actual_cols


def create_checkbox_style():
    """Add custom CSS to improve checkbox grid styling."""
    st.markdown(
        """
        <style>
        .stCheckbox {
            margin-bottom: 0.5rem;
        }
        .checkbox-container {
            padding: 0.5rem;
            border-radius: 0.3rem;
            background-color: #f0f2f6;
            margin-bottom: 0.5rem;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_checkbox_grid(selected: pd.DataFrame) -> List[str]:
    """
    Render a grid of checkboxes for borehole selection with improved layout and performance.

    Args:
        selected: DataFrame containing selected boreholes

    Returns:
        List of selected borehole IDs
    """
    if selected.empty:
        return []

    # Add custom styling
    create_checkbox_style()

    # Get list of borehole IDs
    selected_ids = selected["LOCA_ID"].tolist()

    # Calculate grid layout
    rows, cols = calculate_grid_layout(len(selected_ids))

    # Initialize list to store checked items
    checked_ids = []

    # Create select/deselect all button
    col1, col2 = st.columns([2, 8])
    with col1:
        select_all = st.checkbox("Select All", value=True, key="select_all_bh")

    # Render checkbox grid with tooltips
    for i in range(rows):
        row_cols = st.columns(6)
        for j in range(6):
            idx = i * 6 + j
            if idx >= len(selected_ids):
                break

            with row_cols[j]:
                bh = selected_ids[idx]
                # Get additional info for tooltip
                info = selected[selected["LOCA_ID"] == bh].iloc[0]
                tooltip = (
                    f"Ground Level: {info.get('LOCA_GL', 'N/A')}\n"
                    f"Final Depth: {info.get('LOCA_FDEP', 'N/A')}"
                )

                # Create checkbox with container for styling
                st.markdown('<div class="checkbox-container">', unsafe_allow_html=True)
                is_checked = st.checkbox(
                    bh, value=select_all, key=f"bh_{bh}", help=tooltip
                )
                st.markdown("</div>", unsafe_allow_html=True)

                if is_checked:
                    checked_ids.append(bh)

    return checked_ids
