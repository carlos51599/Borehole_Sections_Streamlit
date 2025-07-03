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


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize session state and default values
init_session_state(
    {
        "ags_files": None,
        "selected_boreholes": [],
        "show_log": False,
        "current_log_bh": None,
        "map_bounds": None,
        "map_center": None,
        "map_zoom": 13,
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
        col1, col2 = st.columns([2, 1])

        with col1:
            # Render map
            st.write("### Location Map")
            map_obj = map_renderer.create_map(
                selected_boreholes=get_state("selected_boreholes"),
                zoom_start=get_state("map_zoom", 13),
            )
            st_map = st_folium(map_obj, width=600, returned_objects=["bounds", "zoom"])

            # Update map state
            if st_map.get("bounds"):
                set_state("map_bounds", st_map["bounds"])
            if st_map.get("zoom"):
                set_state("map_zoom", st_map["zoom"])

        with col2:
            # Borehole selection
            selected_boreholes = borehole_selector.render(
                default=get_state("selected_boreholes")
            )
            set_state("selected_boreholes", selected_boreholes)

        # Section controls and plot
        if selected_boreholes:
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
