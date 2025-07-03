import csv
import pandas as pd
import os
import streamlit as st
from typing import List, Tuple, Dict
from utils import safe_temp_path


@st.cache_data
def parse_group(content: str, group_name: str) -> pd.DataFrame:
    """
    Parse an AGS group into a DataFrame with caching for better performance.

    Args:
        content: AGS file content as string
        group_name: Name of the AGS group to parse (e.g., 'LOCA', 'GEOL')

    Returns:
        pandas DataFrame containing the parsed group data
    """
    try:
        lines = content.splitlines()
        parsed = list(csv.reader(lines, delimiter=",", quotechar='"'))
        headings = []
        data = []
        in_group = False

        for row in parsed:
            if not row:
                continue

            if row[0] == "GROUP" and len(row) > 1:
                in_group = row[1] == group_name
                continue

            if in_group:
                if row[0] == "HEADING":
                    headings = row[1:]
                elif row[0] == "DATA":
                    data.append(row[1 : len(headings) + 1])
                elif row[0] == "GROUP":
                    break

        if not headings or not data:
            return pd.DataFrame()

        return pd.DataFrame(data, columns=headings)
    except Exception as e:
        st.error(f"Error parsing {group_name} group: {str(e)}")
        return pd.DataFrame()


@st.cache_data
def load_all_loca_data(
    ags_files: List[Tuple[str, str]],
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Load and process all location data from AGS files with caching.

    Args:
        ags_files: List of tuples containing (filename, content)

    Returns:
        Tuple of (DataFrame with all location data, map of filenames to contents)
    """
    all_loca = []
    filename_map = {}
    existing_ids = set()

    for fname, content in ags_files:
        try:
            loca_df = parse_group(content, "LOCA")
            if loca_df.empty:
                st.warning(f"No LOCA group found in {fname}")
                continue

            # Convert coordinates to numeric
            for col in ["LOCA_NATE", "LOCA_NATN"]:
                if col in loca_df.columns:
                    loca_df[col] = pd.to_numeric(loca_df[col], errors="coerce")

            # Drop rows with missing coordinates
            invalid_count = loca_df[["LOCA_NATE", "LOCA_NATN"]].isna().any(axis=1).sum()
            if invalid_count > 0:
                st.warning(
                    f"{invalid_count} locations in {fname} have invalid coordinates"
                )
            loca_df = loca_df.dropna(subset=["LOCA_NATE", "LOCA_NATN"])

            if loca_df.empty:
                st.warning(f"No valid locations found in {fname}")
                continue

            # Handle duplicate IDs
            suffix = os.path.splitext(fname)[0][:19]
            loca_df["original_LOCA_ID"] = loca_df["LOCA_ID"].copy()
            loca_df["LOCA_ID"] = loca_df["LOCA_ID"].apply(
                lambda x: f"{x}_{suffix}" if x in existing_ids else x
            )
            existing_ids.update(loca_df["LOCA_ID"].tolist())

            # Store processed data
            loca_df["ags_file"] = fname
            all_loca.append(loca_df)
            filename_map[fname] = content

        except Exception as e:
            st.error(f"Error processing {fname}: {str(e)}")
            continue

    if not all_loca:
        return pd.DataFrame(), {}

    result_df = pd.concat(all_loca, ignore_index=True)
    return result_df, filename_map
