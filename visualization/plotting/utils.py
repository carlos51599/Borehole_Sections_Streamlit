"""
Utility functions for plotting geological sections and borehole logs.
"""

import streamlit as st
import matplotlib.pyplot as plt
from typing import Tuple, Optional
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_resource
def create_figure(
    figsize: Tuple[float, float] = (10, 6)
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Create a new matplotlib figure and axes with the specified size.
    Cached for better performance.

    Args:
        figsize: Figure dimensions (width, height) in inches

    Returns:
        Tuple of (Figure, Axes)
    """
    try:
        fig, ax = plt.subplots(figsize=figsize)
        return fig, ax
    except Exception as e:
        logger.error(f"Error creating figure: {str(e)}")
        raise


@st.cache_data
def setup_axes(
    ax: plt.Axes,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    xlabel: str = "Distance (m)",
    ylabel: str = "Elevation (mAOD)",
    title: Optional[str] = None,
) -> None:
    """
    Configure axes limits, labels and title.
    Cached for better performance.

    Args:
        ax: Matplotlib axes to configure
        xlim: X-axis limits (min, max)
        ylim: Y-axis limits (min, max)
        xlabel: X-axis label
        ylabel: Y-axis label
        title: Plot title (optional)
    """
    try:
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if title:
            ax.set_title(title)
    except Exception as e:
        logger.error(f"Error setting up axes: {str(e)}")
        raise


@st.cache_data
def add_grid(ax: plt.Axes, major: bool = True, minor: bool = True) -> None:
    """
    Add grid lines to the plot.
    Cached for better performance.

    Args:
        ax: Matplotlib axes to add grid to
        major: Whether to show major grid lines
        minor: Whether to show minor grid lines
    """
    try:
        if major:
            ax.grid(True, which="major", linestyle="-", alpha=0.6)
        if minor:
            ax.grid(True, which="minor", linestyle=":", alpha=0.3)
        ax.minorticks_on()
    except Exception as e:
        logger.error(f"Error adding grid: {str(e)}")
        raise


@st.cache_data
def format_labels(ax: plt.Axes, rotation: float = 45) -> None:
    """
    Format axis labels for better readability.
    Cached for better performance.

    Args:
        ax: Matplotlib axes to format
        rotation: Rotation angle for x-axis labels
    """
    try:
        plt.setp(ax.get_xticklabels(), rotation=rotation, ha="right")
    except Exception as e:
        logger.error(f"Error formatting labels: {str(e)}")
        raise
