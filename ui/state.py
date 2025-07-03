"""Centralized state management for the application."""

import streamlit as st
from typing import Any, Dict, Optional, List, Tuple
import logging
from dataclasses import dataclass, field
from core.ags_parser import AGSData

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """Container for application state."""

    # Data state
    ags_data: Optional[AGSData] = None
    selected_boreholes: List[str] = field(default_factory=list)
    current_view: str = "map"  # map, section, or log

    # UI state
    show_labels: bool = True
    show_legend: bool = True
    vertical_exaggeration: float = 1.0

    # Map state
    map_center: Optional[Tuple[float, float]] = None
    map_zoom: Optional[int] = None
    drawn_shapes: List[Dict] = field(default_factory=list)

    # Plot state
    section_fig: Optional[Any] = None
    log_fig: Optional[Any] = None
    current_log_bh: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "ags_data": self.ags_data,
            "selected_boreholes": self.selected_boreholes,
            "current_view": self.current_view,
            "show_labels": self.show_labels,
            "show_legend": self.show_legend,
            "vertical_exaggeration": self.vertical_exaggeration,
            "map_center": self.map_center,
            "map_zoom": self.map_zoom,
            "drawn_shapes": self.drawn_shapes,
            "section_fig": self.section_fig,
            "log_fig": self.log_fig,
            "current_log_bh": self.current_log_bh,
        }


def init_session_state(defaults: Optional[Dict[str, Any]] = None) -> None:
    """Initialize session state with default values."""
    state = AppState()
    state_dict = state.to_dict()

    if defaults:
        state_dict.update(defaults)

    for key, value in state_dict.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_state(key: str, default: Any = None) -> Any:
    """Get a value from session state."""
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """Set a value in session state."""
    try:
        st.session_state[key] = value
    except Exception as e:
        logger.error(f"Error setting state {key}: {str(e)}")


def reset_view_state() -> None:
    """Reset view-specific state variables."""
    view_states = ["current_log_bh", "drawn_shapes", "section_fig", "log_fig"]
    for key in view_states:
        if key in st.session_state:
            del st.session_state[key]


def get_selected_boreholes() -> List[str]:
    """Get the currently selected boreholes."""
    return st.session_state.get("selected_boreholes", [])


def has_data() -> bool:
    """Check if any AGS data is loaded."""
    return bool(st.session_state.get("ags_data"))


# Make everything available at package level
__all__ = [
    "AppState",
    "init_session_state",
    "get_state",
    "set_state",
    "reset_view_state",
    "get_selected_boreholes",
    "has_data",
]
