import streamlit as st


def render_borehole_log(
    loca_id, filename_map, ags_files, show_labels=True, fig_height=2.5
):
    """Display a simple borehole log for the selected LOCA_ID."""
    # Find which AGS file this borehole belongs to
    ags_file = None
    for fname, content in filename_map.items():
        if loca_id in content:
            ags_file = fname
            break
    if ags_file is None:
        st.warning(f"Borehole {loca_id} not found in any AGS file.")
        return
    # Parse AGS file content for this borehole
    from section_plot import parse_ags_geol_section
    import tempfile
    import os

    ags_temp_path = os.path.join(tempfile.gettempdir(), ags_file)
    with open(ags_temp_path, "w", encoding="utf-8") as f:
        f.write(filename_map[ags_file])
    geol_df, loca_df, abbr_df = parse_ags_geol_section(ags_temp_path)
    # Filter for this borehole
    geol_bh = geol_df[geol_df["LOCA_ID"] == loca_id]
    loca_bh = loca_df[loca_df["LOCA_ID"] == loca_id]
    if geol_bh.empty or loca_bh.empty:
        st.warning(f"No data found for borehole {loca_id}.")
        return
    st.subheader(f"Borehole Log: {loca_id}")
    st.toast("Scroll down to see Borehole Log", icon="🔽")
    # Draw a single borehole log using the same style as section_plot
    import matplotlib.pyplot as plt
    import numpy as np

    # Prepare data for plotting
    gl = float(loca_bh.iloc[0]["LOCA_GL"]) if "LOCA_GL" in loca_bh.columns else 0.0
    width = 1.0
    # Calculate borehole length for dynamic scaling
    min_top = geol_bh["GEOL_TOP"].min()
    max_base = geol_bh["GEOL_BASE"].max()
    total_depth = abs(max_base - min_top)
    # Set a reasonable aspect ratio: width fixed, height based on depth (but capped)
    width_inches = 1.5
    min_height = 1.5
    max_height = fig_height
    height_inches = min(max(min_height, total_depth / 15), max_height)
    fig, ax = plt.subplots(
        figsize=(width_inches, height_inches), dpi=100, constrained_layout=False
    )
    # Make the plot area more compact by reducing margins
    plt.subplots_adjust(left=0.25, right=0.75, top=0.98, bottom=0.08)
    # Assign a color to each unique GEOL_LEG code
    unique_leg = geol_bh["GEOL_LEG"].unique()
    color_map = {leg: plt.cm.tab20(i % 20) for i, leg in enumerate(unique_leg)}
    # Build a label for each GEOL_LEG using ABBR group if available
    abbr_df = abbr_df if "abbr_df" in locals() else None
    leg_label_map = {}
    for leg in unique_leg:
        label = leg
        if (
            abbr_df is not None
            and "ABBR_CODE" in abbr_df.columns
            and "ABBR_DESC" in abbr_df.columns
        ):
            abbr_match = abbr_df[abbr_df["ABBR_CODE"] == str(leg)]
            if not abbr_match.empty:
                label = abbr_match["ABBR_DESC"].iloc[0]
        leg_label_map[leg] = f"{label} ({leg})"
    # Plot intervals, grouping continuous layers with the same GEOL_LEG
    bh_df = geol_bh.sort_values("GEOL_TOP").reset_index(drop=True)
    prev_leg = None
    group_start_idx = None
    legend_labels_added = set()
    for idx, row in bh_df.iterrows():
        leg = row["GEOL_LEG"]
        color = color_map.get(leg, (0.7, 0.7, 0.7, 1))
        elev_top = gl - abs(row["GEOL_TOP"])
        elev_base = gl - abs(row["GEOL_BASE"])
        # Grouping logic for labeling
        if prev_leg != leg:
            # If ending a previous group, label it
            if prev_leg is not None and group_start_idx is not None:
                group_rows = bh_df.iloc[group_start_idx:idx]
                if not group_rows.empty:
                    group_top = gl - abs(group_rows.iloc[0]["GEOL_TOP"])
                    group_base = gl - abs(group_rows.iloc[-1]["GEOL_BASE"])
                    label_elev = (group_top + group_base) / 2
                    if show_labels:
                        ax.text(
                            0,
                            label_elev,
                            str(prev_leg),
                            ha="center",
                            va="center",
                            fontsize=8,
                            color="k",
                            rotation=90,
                        )
                # Fill the grouped interval
                ax.fill_betweenx(
                    [group_top, group_base],
                    0 - width / 2,
                    0 + width / 2,
                    color=color_map.get(prev_leg, (0.7, 0.7, 0.7, 1)),
                    alpha=0.7,
                    label=(
                        leg_label_map[prev_leg]
                        if prev_leg not in legend_labels_added
                        else None
                    ),
                )
                legend_labels_added.add(prev_leg)
            # Start new group
            prev_leg = leg
            group_start_idx = idx
    # After loop, label and fill the last group
    if prev_leg is not None and group_start_idx is not None:
        group_rows = bh_df.iloc[group_start_idx:]
        if not group_rows.empty:
            group_top = gl - abs(group_rows.iloc[0]["GEOL_TOP"])
            group_base = gl - abs(group_rows.iloc[-1]["GEOL_BASE"])
            label_elev = (group_top + group_base) / 2
            if show_labels:
                ax.text(
                    0,
                    label_elev,
                    str(prev_leg),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="k",
                    rotation=90,
                )
            ax.fill_betweenx(
                [group_top, group_base],
                0 - width / 2,
                0 + width / 2,
                color=color_map.get(prev_leg, (0.7, 0.7, 0.7, 1)),
                alpha=0.7,
                label=(
                    leg_label_map[prev_leg]
                    if prev_leg not in legend_labels_added
                    else None
                ),
            )
            legend_labels_added.add(prev_leg)
    # Draw ground level line
    ax.plot([-width / 2, width / 2], [gl, gl], color="k", lw=2, label="Ground Level")
    ax.set_xlim(-width, width)
    elev_max = max(gl, geol_bh["GEOL_TOP"].apply(lambda d: gl - abs(d)).max())
    elev_min = min(gl, geol_bh["GEOL_BASE"].apply(lambda d: gl - abs(d)).min())
    ax.set_ylim(elev_min - 0.5, elev_max + 1.5)
    ax.set_xlabel("")
    ax.set_ylabel("Elevation (m)")
    ax.set_xticks([])
    # Legend to the right of the plot
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), title="Geology")
    plt.tight_layout(rect=[0, 0, 0.8, 1])
    # Make the log plot larger but still centered
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.pyplot(fig)
