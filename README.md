# AGS Borehole Section Viewer

An interactive Streamlit web application for visualizing and plotting borehole sections from AGS files, with advanced map-based selection and customizable section axes.

## Features

- **Interactive map selection:** Rectangle, polygon, or polyline (with buffer) for borehole selection using Folium.
- **Section plotting:** Plot sections along regression lines or custom-drawn axes, including support for polylines and buffer zones.
- **Downloadable plots:** Export section plots as images or data.
- **Robust session state:** Seamless user experience with persistent selections and settings.
- **Modular codebase:** All logic is separated into focused modules for maintainability and testing.

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd Streamlit_Azure
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the app:**
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
Streamlit_Azure/
├── app.py                  # Main Streamlit app entry point
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── .gitignore              # Git ignore rules
├── .gitattributes          # Git attributes for cross-platform
├── data_loader.py          # AGS parsing and data loading
├── map_utils.py            # Map selection/filtering logic
├── section_plot.py         # Section plotting backend
├── section_logic.py        # Section plot orchestration
├── map_render.py           # Map rendering logic
├── borehole_selection.py   # Borehole selection UI
├── utils.py                # Utility functions
└── ... (other modules, tests, or configs)
```

## Development Notes
- Place AGS files in a suitable data directory or upload via the app interface.
- Keep logic modular; add new modules for new features.
- For deployment, consider adding a `Dockerfile` and `.streamlit/config.toml`.

## Contributing
Pull requests and issues are welcome! Please follow best practices for Python and Streamlit development.

## License
MIT License (or specify your license here).
