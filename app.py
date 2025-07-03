"""
Streamlit application for visualizing geological borehole sections.
"""

import streamlit as st
from streamlit_folium import st_folium
from io import BytesIO
import logging

from core.ags_parser import parse_ags_files
from visualization.mapping import MapRenderer
from visualization.plotting import SectionRenderer
from ui.components import BoreholeSelector, SectionControls
from ui.state import init_session_state, get_state, set_state
from core.config import AppConfig
from core.logging_config import setup_logging


# Configure logging and debug settings
AppConfig.DEBUG_MODE = True
AppConfig.PROFILE_PERFORMANCE = True

# Set up logging with debug flags from config
setup_logging(
    debug=AppConfig.DEBUG_MODE, log_file="app.log" if AppConfig.DEBUG_MODE else None
)

# Get logger for this module
logger = logging.getLogger(__name__)


# Initialize session state and default values
init_session_state(
    {
        "ags_files": None,
        "selected_boreholes": [],
        "show_log": False,
        "current_log_bh": None,
        "map_center": None,
        "map_zoom": 13,
        "drawn_shapes": None,
    }
)


def add_download_button(figure, filename, label="Download Plot"):
    """Common function for adding plot download buttons"""
    try:
        buffer = BytesIO()
        figure.savefig(buffer, format="png", bbox_inches="tight", dpi=300)
        buffer.seek(0)
        st.download_button(
            label=label,
            data=buffer,
            file_name=filename,
            mime="image/png",
            use_container_width=True,
        )
    except Exception as e:
        logger.error(f"Error creating download button: {str(e)}")
        st.error("Error creating download button")


def main():
    """Main application entry point"""
    # Set page to full width
    st.set_page_config(layout="wide")
    st.title("Borehole Section Viewer")

    # File upload
    uploaded_files = st.file_uploader(
        "Upload AGS Files",
        type=["ags"],
        accept_multiple_files=True,
        help="Select one or more AGS files containing borehole data",
    )

    if not uploaded_files:
        st.info("Please upload AGS files to begin")
        return

    try:
        # Parse AGS files
        ags_data = parse_ags_files(uploaded_files)
        if ags_data is None:
            st.error("Error parsing AGS files")
            return

        # Create renderers
        map_renderer = MapRenderer(ags_data.loca_df)
        section_renderer = SectionRenderer(
            ags_data.geol_df, ags_data.loca_df, ags_data.abbr_df
        )

        # Create UI components
        borehole_selector = BoreholeSelector(ags_data.loca_df)
        section_controls = SectionControls()

        # Layout the interface
        st.write("### Location Map")

        # Split into map and controls with map taking most space
        col1, col2 = st.columns([5, 1])

        with col1:
            # Create map with current state
            @st.cache_data
            def get_map(selected_ids):
                return map_renderer.create_map(
                    selected_boreholes=selected_ids,
                    zoom_start=st.session_state.get("map_zoom", 13),
                    center=st.session_state.get("map_center"),
                )

            # Get map with current state
            map_obj = get_map(get_state("selected_boreholes"))

            # Render map and get state
            map_data = st_folium(
                map_obj,
                width="100%",
                height=600,
                key="map",
                returned_objects=["last_active_drawing", "zoom", "center"],
            )

            # Handle map interactions
            if map_data:
                # Update map state
                if "zoom" in map_data:
                    st.session_state.map_zoom = map_data["zoom"]
                if "center" in map_data:
                    st.session_state.map_center = map_data["center"]

                # Handle drawings
                if map_data.get("last_active_drawing"):
                    set_state("drawn_shapes", map_data["last_active_drawing"])
                    st.rerun()

        with col2:
            if st.button("Clear Selection"):
                set_state("drawn_shapes", None)
                set_state("selected_boreholes", None)
                st.rerun()

            # Borehole selection from drawn shapes
            selected_boreholes = borehole_selector.render()
            if not selected_boreholes.empty:
                set_state("selected_boreholes", selected_boreholes)
                # Show selection count
                n_selected = len(selected_boreholes)
                st.write(
                    f"Selected: {n_selected} borehole{'s' if n_selected != 1 else ''}"
                )

        # Section controls and plot
        if not selected_boreholes.empty:
            st.write("---")

            # Get plot settings
            plot_settings = section_controls.render()

            # Calculate dimensions and render section
            dimensions = section_renderer.calculate_dimensions(
                selected_boreholes,
                section_width=plot_settings.width * plot_settings.dpi / 72,
                vertical_exaggeration=plot_settings.vertical_exaggeration,
            )

            fig, ax = section_renderer.render_section(
                selected_boreholes, dimensions, title="Geological Section"
            )

            # Display plot
            st.pyplot(fig)

            # Add download button
            add_download_button(fig, "section_plot.png", "Download Section Plot")
        else:
            st.info("Select boreholes to create a section")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("An error occurred while processing the data")


if __name__ == "__main__":
    main()
