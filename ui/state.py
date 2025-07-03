"""Centralized state management for the application."""

import streamlit as st
from typing import Any, Dict, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def init_session_state(defaults: Optional[Dict[str, Any]] = None) -> None:
    """
    Initialize session state with default values.

    Args:
        defaults: Optional dictionary of default values
    """
    _defaults = {
        "ags_files": None,
        "show_labels": True,
        "selected_log_bh": None,
        "drawn_shapes": [],
        "last_shape_hash": None,
        "selected_boreholes": pd.DataFrame(),
        "map_center": None,
        "map_zoom": None,
        "last_drawn_shape": None,
        "log_fig": None,
        "show_log_loca_id": None,
        "current_view": "map",  # Track current view (map/section/log)
    }

    if defaults:
        _defaults.update(defaults)

    for key, value in _defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_state(key: str, default: Any = None) -> Any:
    """
    Get a value from session state.

    Args:
        key: Session state key
        default: Default value if key doesn't exist

    Returns:
        Value from session state or default
    """
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """
    Set a value in session state.

    Args:
        key: Session state key
        value: Value to set
    """
    try:
        st.session_state[key] = value
    except Exception as e:
        logger.error(f"Error setting state {key}: {str(e)}")


def reset_view_state() -> None:
    """Reset view-specific state variables."""
    view_states = ["selected_log_bh", "drawn_shapes", "last_shape_hash", "log_fig"]
    for key in view_states:
        if key in st.session_state:
            del st.session_state[key]


def get_selected_boreholes() -> pd.DataFrame:
    """Get the currently selected boreholes."""
    return st.session_state.get("selected_boreholes", pd.DataFrame())


def has_data() -> bool:
    """Check if any AGS files are loaded."""
    return bool(st.session_state.get("ags_files"))
