# Required libraries: matplotlib, pandas
try:
    import matplotlib.pyplot as plt
except ImportError:
    print("You need to install the 'matplotlib' library. Run: pip install matplotlib")
    exit(1)
try:
    import pandas as pd
except ImportError:
    print("You need to install the 'pandas' library. Run: pip install pandas")
    exit(1)
import csv
import numpy as np

import os
import re

# Path to AGS file (robust to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGS_FILE = r"C:\Users\dea29431.RSKGAD\OneDrive - Rsk Group Limited\Documents\Geotech\AGS Section\FLRG - 2025-05-20 1711 - Preliminary data - 4.ags"


def parse_ags_geol_section(filepath):
    """Parse the AGS file and extract GEOL, LOCA, and ABBR group data as DataFrames."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Use csv.reader for robust parsing
    def parse_lines(lines):
        return list(csv.reader(lines, delimiter=",", quotechar='"'))

    parsed = parse_lines(lines)
    # Parse GEOL
    geol_headings = []
    geol_data = []
    in_geol = False
    for row in parsed:
        if row and row[0] == "GROUP" and len(row) > 1 and row[1] == "GEOL":
            in_geol = True
            continue
        if in_geol and row and row[0] == "HEADING":
            geol_headings = row[1:]
            continue
        if in_geol and row and row[0] == "DATA":
            geol_data.append(row[1 : len(geol_headings) + 1])
            continue
        if in_geol and row and row[0] == "GROUP" and (len(row) < 2 or row[1] != "GEOL"):
            break
    geol_df = pd.DataFrame(geol_data, columns=geol_headings)
    if "LOCA_ID" in geol_df.columns:
        geol_df["LOCA_ID"] = geol_df["LOCA_ID"].str.strip()
    for col in ["GEOL_TOP", "GEOL_BASE"]:
        if col in geol_df.columns:
            geol_df[col] = pd.to_numeric(geol_df[col], errors="coerce")

    # Parse LOCA
    loca_headings = []
    loca_data = []
    in_loca = False
    for row in parsed:
        if row and row[0] == "GROUP" and len(row) > 1 and row[1] == "LOCA":
            in_loca = True
            continue
        if in_loca and row and row[0] == "HEADING":
            loca_headings = row[1:]
            continue
        if in_loca and row and row[0] == "DATA":
            loca_data.append(row[1 : len(loca_headings) + 1])
            continue
        if in_loca and row and row[0] == "GROUP" and (len(row) < 2 or row[1] != "LOCA"):
            break
    loca_df = pd.DataFrame(loca_data, columns=loca_headings)
    if "LOCA_ID" in loca_df.columns:
        loca_df["LOCA_ID"] = loca_df["LOCA_ID"].str.strip()
    for col in ["LOCA_NATE", "LOCA_NATN"]:
        if col in loca_df.columns:
            loca_df[col] = pd.to_numeric(loca_df[col], errors="coerce")

    # Parse ABBR
    abbr_headings = []
    abbr_data = []
    in_abbr = False
    for row in parsed:
        if row and row[0] == "GROUP" and len(row) > 1 and row[1] == "ABBR":
            in_abbr = True
            continue
        if in_abbr and row and row[0] == "HEADING":
            abbr_headings = row[1:]
            continue
        if in_abbr and row and row[0] == "DATA":
            abbr_data.append(row[1 : len(abbr_headings) + 1])
            continue
        if in_abbr and row and row[0] == "GROUP" and (len(row) < 2 or row[1] != "ABBR"):
            break
    abbr_df = pd.DataFrame(abbr_data, columns=abbr_headings) if abbr_headings else None
    return geol_df, loca_df, abbr_df


def plot_borehole_sections(
    geol_df, loca_df, abbr_df=None, ags_title=None, section_line=None
):
    """Plot a section for each borehole using real X coordinates from LOCA_NATE (Easting) in LOCA group.
    The bottom axis is distance in meters (relative to the first borehole), and the same GEOL_LEG code
    uses the same color across all boreholes.
    """
    # Merge X/Y coordinates into geol_df
    merged = geol_df.merge(
        loca_df[["LOCA_ID", "LOCA_NATE", "LOCA_NATN"]],
        left_on="LOCA_ID",
        right_on="LOCA_ID",
        how="left",
    )
    # Warn if any boreholes have missing coordinates
    missing_coords = merged[merged["LOCA_NATE"].isna() | merged["LOCA_NATN"].isna()][
        "LOCA_ID"
    ].unique()
    if len(missing_coords) > 0:
        print(
            f"Warning: The following LOCA_IDs have missing coordinates and will be skipped: {missing_coords}"
        )
    # Remove rows with missing coordinates
    merged = merged.dropna(subset=["LOCA_NATE", "LOCA_NATN"])
    if merged.empty:
        print("No boreholes with valid coordinates to plot.")
        return
    # Merge ground level (LOCA_GL) into merged DataFrame
    if "LOCA_GL" in loca_df.columns:
        merged = merged.merge(loca_df[["LOCA_ID", "LOCA_GL"]], on="LOCA_ID", how="left")
        merged["LOCA_GL"] = pd.to_numeric(merged["LOCA_GL"], errors="coerce")
    else:
        merged["LOCA_GL"] = 0.0  # fallback if missing
    # Calculate elevation for each interval (ELEV = LOCA_GL - depth)
    merged["ELEV_TOP"] = merged["LOCA_GL"] - merged["GEOL_TOP"].abs()
    merged["ELEV_BASE"] = merged["LOCA_GL"] - merged["GEOL_BASE"].abs()
    # Get unique boreholes and their X/Y (Easting/Northing)
    borehole_x = merged.groupby("LOCA_ID")["LOCA_NATE"].first().sort_values()
    borehole_y = (
        merged.groupby("LOCA_ID")["LOCA_NATN"].first().reindex(borehole_x.index)
    )
    boreholes = borehole_x.index.tolist()
    x_coords = borehole_x.values
    y_coords = borehole_y.values

    # If section_line is provided, project boreholes onto this line or polyline for section orientation
    if section_line is not None:
        try:
            from shapely.geometry import LineString, Point
        except ImportError:
            print("You need to install the 'shapely' library. Run: pip install shapely")
            exit(1)
        # section_line: either ((x0, y0), (x1, y1)) or [(x0, y0), (x1, y1), ...]
        if isinstance(section_line, (list, tuple)) and len(section_line) > 2:
            # Polyline: project each borehole onto the closest point along the polyline
            line = LineString(section_line)
            rel_x = []
            for x, y in zip(x_coords, y_coords):
                point = Point(x, y)
                rel_x.append(line.project(point))
            bh_x_map = dict(zip(boreholes, rel_x))
        else:
            # Two-point line: keep old logic
            import numpy as np

            (x0, y0), (x1, y1) = section_line
            dx = x1 - x0
            dy = y1 - y0
            line_length = np.hypot(dx, dy)
            if line_length == 0:
                # Fallback to default orientation if degenerate
                rel_x = x_coords - x_coords[0]
            else:
                # Project each borehole onto the regression line
                rel_x = ((x_coords - x0) * dx + (y_coords - y0) * dy) / line_length
            bh_x_map = dict(zip(boreholes, rel_x))
    else:
        # Default: use easting as section orientation
        rel_x = x_coords - x_coords[0]
        bh_x_map = dict(zip(boreholes, rel_x))
    # Get ground level for each borehole
    bh_gl_map = merged.groupby("LOCA_ID")["LOCA_GL"].first().to_dict()
    # Assign a color to each unique GEOL_LEG code
    unique_leg = merged["GEOL_LEG"].unique()
    color_map = {leg: plt.cm.tab20(i % 20) for i, leg in enumerate(unique_leg)}
    # Build a label for each GEOL_LEG using ABBR group if available
    leg_label_map = {}
    for leg in unique_leg:
        label = leg  # fallback
        if (
            abbr_df is not None
            and "ABBR_CODE" in abbr_df.columns
            and "ABBR_DESC" in abbr_df.columns
        ):
            abbr_match = abbr_df[abbr_df["ABBR_CODE"] == str(leg)]
            if not abbr_match.empty:
                label = abbr_match["ABBR_DESC"].iloc[0]
        else:
            # fallback to previous logic: first fully capitalized word(s) in GEOL_DESC
            descs = merged.loc[merged["GEOL_LEG"] == leg, "GEOL_DESC"]
            for desc in descs:
                match = re.search(r"([A-Z]{2,}(?: [A-Z]{2,})*)", str(desc))
                if match:
                    label = match.group(1)
                    break
        leg_label_map[leg] = f"{label} ({leg})"
    width = 1.0  # width of each borehole
    fig, ax = plt.subplots(figsize=(max(8, len(boreholes) * 1.5), 6))
    legend_labels_added = set()
    for i, bh in enumerate(boreholes):
        debug_msgs = []
        bh_x = bh_x_map[bh]
        bh_df = (
            merged[merged["LOCA_ID"] == bh]
            .sort_values("GEOL_TOP")
            .reset_index(drop=True)
        )
        intervals_plotted = 0
        intervals_labelled = 0
        labelled_groups = []
        # Group consecutive intervals with the same GEOL_LEG
        prev_leg = None
        group_start_idx = None
        for idx, row in bh_df.iterrows():
            leg = row["GEOL_LEG"]
            color = color_map.get(leg, (0.7, 0.7, 0.7, 1))
            # Only suppress repeated legend entries, not text labels
            legend_label = (
                leg_label_map[leg] if leg not in legend_labels_added else None
            )
            ax.fill_betweenx(
                [row["ELEV_TOP"], row["ELEV_BASE"]],
                bh_x - width / 2,
                bh_x + width / 2,
                color=color,
                alpha=0.7,
                label=legend_label,
            )
            intervals_plotted += 1
            if legend_label is not None:
                legend_labels_added.add(leg)
            # Grouping logic for labeling
            if prev_leg != leg:
                # If ending a previous group, label it
                if prev_leg is not None and group_start_idx is not None:
                    group_rows = bh_df.iloc[group_start_idx:idx]
                    if not group_rows.empty:
                        group_top = group_rows.iloc[0]["ELEV_TOP"]
                        group_base = group_rows.iloc[-1]["ELEV_BASE"]
                        label_elev = (group_top + group_base) / 2
                        ax.text(
                            bh_x,
                            label_elev,
                            str(prev_leg),  # Only show the code
                            ha="center",
                            va="center",
                            fontsize=8,
                            color="k",
                            rotation=90,
                        )
                        intervals_labelled += 1
                        labelled_groups.append(
                            (
                                prev_leg,
                                group_rows.iloc[0]["GEOL_TOP"],
                                group_rows.iloc[-1]["GEOL_BASE"],
                                label_elev,
                                bh_x,
                            )
                        )
                    else:
                        debug_msgs.append(
                            f"  Warning: Skipped empty group for {prev_leg} in {bh}"
                        )
                # Start new group
                prev_leg = leg
                group_start_idx = idx
        # After loop, label the last group (even if only one interval)
        if prev_leg is not None and group_start_idx is not None:
            group_rows = bh_df.iloc[group_start_idx:]
            if not group_rows.empty:
                group_top = group_rows.iloc[0]["ELEV_TOP"]
                group_base = group_rows.iloc[-1]["ELEV_BASE"]
                label_elev = (group_top + group_base) / 2
                ax.text(
                    bh_x,
                    label_elev,
                    str(prev_leg),  # Only show the code
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="k",
                    rotation=90,
                )
                intervals_labelled += 1
                labelled_groups.append(
                    (
                        prev_leg,
                        group_rows.iloc[0]["GEOL_TOP"],
                        group_rows.iloc[-1]["GEOL_BASE"],
                        label_elev,
                        bh_x,
                    )
                )
            else:
                debug_msgs.append(
                    f"  Warning: Skipped empty group for {prev_leg} in {bh}"
                )
        if intervals_labelled == 0:
            debug_msgs.append(f"  Warning: No labels placed for borehole {bh}")
        if intervals_plotted == 0:
            debug_msgs.append(f"  Warning: No intervals plotted for borehole {bh}")
        # Only print debug info if something went wrong
        if debug_msgs:
            print(f"\nProcessing borehole: {bh}")
            for msg in debug_msgs:
                print(msg)
            print(
                f"  Plotted {intervals_plotted} intervals, labelled {intervals_labelled} groups for borehole {bh}"
            )
            for g in labelled_groups:
                print(
                    f"    Group: GEOL_LEG={g[0]}, Depth {g[1]} to {g[2]}, Elev {g[3]:.2f}, X={g[4]}"
                )
    # Draw ground level line connecting the tops of boreholes, ordered by rel_x (section axis)
    import numpy as np

    # Sort boreholes by rel_x (section axis)
    rel_x = np.array(rel_x)
    sorted_indices = np.argsort(rel_x)
    sorted_boreholes = [boreholes[i] for i in sorted_indices]
    sorted_x = [bh_x_map[bh] for bh in sorted_boreholes]
    ground_levels = [bh_gl_map[bh] for bh in sorted_boreholes]
    ax.plot(
        sorted_x,
        ground_levels,
        color="k",
        lw=2,
        linestyle="-",
        zorder=10,
        label="Ground Level",
    )

    # Move borehole labels above the plot area, below the title
    # Remove previous label placement inside the plot
    # Instead, use annotation in axes coordinates
    label_y = 1.02  # just below the title, in axes fraction
    max_label_len = max(len(str(bh)) for bh in boreholes) if boreholes else 0
    # Estimate vertical space needed for labels (in axes fraction)
    label_height = 0.04 + 0.01 * min(max_label_len, 20)  # scale for long labels
    # Ensure rel_x is a numpy array for .min()/.max() support
    import numpy as np

    rel_x = np.array(rel_x)
    for i, bh in enumerate(boreholes):
        bh_x = bh_x_map[bh]
        x_axes = (bh_x - (rel_x.min() - 2)) / ((rel_x.max() + 2) - (rel_x.min() - 2))
        ax.annotate(
            bh,
            xy=(x_axes, label_y),
            xycoords=("axes fraction", "axes fraction"),
            ha="center",
            va="bottom",
            fontsize=9,
            rotation=90,
            annotation_clip=False,
        )

    # Set the plot title above the borehole labels, using the AGS filename (without .ags)
    if ags_title is None:
        ags_filename = os.path.basename(AGS_FILE)
        if ags_filename.lower().endswith(".ags"):
            ags_title = ags_filename[:-4]
        else:
            ags_title = ags_filename
    # Place the title above the labels, with extra padding
    ax.set_title(f"{ags_title}", pad=60 + label_height * 100)

    # Remove connecting lines and hatches (skip that code)
    # Set uniform x-axis (distance) labels at multiples of 5 or 10
    total_length = rel_x.max() - rel_x.min()
    # Choose step size: 10 if total_length > 50, else 5, else 1
    if total_length > 50:
        step = 10
    elif total_length > 15:
        step = 5
    else:
        step = 1
    x_start = int(np.floor(rel_x.min() / step) * step)
    x_end = int(np.ceil(rel_x.max() / step) * step)
    x_tick_vals = np.arange(x_start, x_end + step, step)
    ax.set_xticks(x_tick_vals)
    ax.set_xticklabels([f"{int(x)}" for x in x_tick_vals])
    ax.set_xlabel("Distance along section (m)")
    ax.set_ylabel("Elevation (m)")
    # Set y-limits to show all elevations (highest at top, lowest at bottom)
    elev_max = merged[["ELEV_TOP", "ELEV_BASE"]].max().max()
    elev_min = merged[["ELEV_TOP", "ELEV_BASE"]].min().min()
    ax.set_ylim(elev_min - 0.5, elev_max + 1.5)
    ax.set_xlim(rel_x.min() - 2, rel_x.max() + 2)
    # Create a legend for GEOL_LEG codes with descriptive labels
    seen_labels = set()
    handles = []
    for leg in unique_leg:
        label = leg_label_map[leg]
        if label not in seen_labels:
            handles.append(
                plt.Line2D([0], [0], color=color_map[leg], lw=6, label=label)
            )
            seen_labels.add(label)
    ax.legend(
        handles=handles,
        title="Geology (from GEOL_DESC)",
        bbox_to_anchor=(1.01, 1),
        loc="upper left",
    )
    plt.tight_layout()
    plt.show()
    return fig


def plot_section_from_ags(ags_file, filter_loca_ids=None, section_line=None):
    """Parse AGS file and plot section for optionally filtered LOCA_IDs. Returns the matplotlib figure."""
    geol_df, loca_df, abbr_df = parse_ags_geol_section(ags_file)
    if filter_loca_ids is not None:
        # Filter both dataframes to only include selected LOCA_IDs
        geol_df = geol_df[geol_df["LOCA_ID"].isin(filter_loca_ids)]
        loca_df = loca_df[loca_df["LOCA_ID"].isin(filter_loca_ids)]
    if geol_df.empty or loca_df.empty:
        print("No boreholes to plot after filtering.")
        return None
    ags_filename = os.path.basename(ags_file)
    if ags_filename.lower().endswith(".ags"):
        ags_title = ags_filename[:-4]
    else:
        ags_title = ags_filename
    return plot_borehole_sections(
        geol_df, loca_df, abbr_df, ags_title=ags_title, section_line=section_line
    )


if __name__ == "__main__":
    from contextlib import redirect_stdout, redirect_stderr

    output_file = os.path.join(SCRIPT_DIR, "section_output.txt")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            with redirect_stdout(f), redirect_stderr(f):
                try:
                    # You can pass a list of LOCA_IDs to plot only selected boreholes
                    plot_section_from_ags(AGS_FILE)
                except Exception:
                    import traceback

                    traceback.print_exc()
    except Exception as e:
        # If an error occurs before the file is opened, print to terminal
        print(f"Error: {e}")
