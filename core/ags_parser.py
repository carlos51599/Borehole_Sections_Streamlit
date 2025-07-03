"""AGS file parsing and data management."""

import streamlit as st
from typing import List, Dict, Any, Iterator, Optional, Union, Set
import pandas as pd
import csv
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from core.config import AppConfig
import os
import time
from functools import wraps


def log_timing(func):
    """Decorator to log function execution time for performance monitoring."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        # Only log timing for operations that take more than 0.1 seconds
        if duration > 0.1:
            logger.info(f"{func.__name__} took {duration:.2f}s")
        return result

    return wrapper


# Get module logger
logger = logging.getLogger(__name__)


@dataclass
class AGSGroup:
    """Container for an AGS data group with metadata."""

    name: str
    headings: List[str]
    units: Dict[str, str]
    types: Dict[str, str]
    data: List[Dict[str, str]]


@dataclass
class AGSData:
    """Container for AGS data groups."""

    geol_df: pd.DataFrame
    loca_df: pd.DataFrame
    abbr_df: pd.DataFrame

    # Columns that should not be converted to categorical
    NUMERIC_COLUMNS = {
        "LOCA": [
            "LOCA_NATE",
            "LOCA_NATN",
            "LOCA_LAT",
            "LOCA_LON",
            "LOCA_GL",
            "LOCA_FDEP",
        ],
        "GEOL": ["GEOL_TOP", "GEOL_BASE"],
    }

    @property
    def has_valid_data(self) -> bool:
        """Check if the data is valid for plotting."""
        return not (self.geol_df.empty or self.loca_df.empty)

    def optimize_memory(self) -> None:
        """Optimize memory usage of dataframes while preserving numeric columns."""
        if AppConfig.USE_CATEGORICAL:
            # Process each dataframe with its specific numeric columns
            for df_name, df in [
                ("GEOL", self.geol_df),
                ("LOCA", self.loca_df),
                ("ABBR", self.abbr_df),
            ]:
                # Get numeric columns for this group
                numeric_cols = set(self.NUMERIC_COLUMNS.get(df_name, []))

                # Convert only non-numeric string columns to categorical
                for col in df.columns:
                    if col not in numeric_cols and df[col].dtype == "object":
                        df[col] = df[col].astype("category")


def get_numeric_columns(headings: List[str], types: Dict[str, str]) -> List[str]:
    """
    Get list of columns that should be numeric based on AGS type codes.

    AGS numeric types:
    - 0DP: Integer
    - 1DP, 2DP, 3DP, 4DP, 5DP, 6DP: Decimal places
    - MC: Machine-controlled number
    - SF: Significant figures
    - SCI: Scientific notation
    - 2NO, 3NO, 4NO: Number of digits
    """
    numeric_types = {
        "0DP",
        "1DP",
        "2DP",
        "3DP",
        "4DP",
        "5DP",
        "6DP",
        "MC",
        "SF",
        "SCI",
        "2NO",
        "3NO",
        "4NO",
    }
    return [
        col for col in headings if types.get(col, "").strip().upper() in numeric_types
    ]


@log_timing
def parse_ags_group(content: str, group_name: str) -> Optional[AGSGroup]:
    """
    Parse an AGS group with its metadata.

    Args:
        content: AGS file content as string
        group_name: Name of the group to parse (e.g., 'LOCA', 'GEOL')

    Returns:
        AGSGroup object containing the parsed data and metadata, or None if not found
    """
    try:
        lines = content.splitlines()
        rows = list(csv.reader(lines, delimiter=",", quotechar='"'))

        in_group = False
        headings: List[str] = []
        units: Dict[str, str] = {}
        types: Dict[str, str] = {}
        data: List[Dict[str, str]] = []

        for row in rows:
            if not row or len(row) < 2:  # Skip empty or malformed rows
                continue

            # Handle GROUP marker
            if row[0] == "GROUP":
                if in_group:  # End of current group
                    break
                in_group = row[1] == group_name
                continue

            if in_group:
                if row[0] == "HEADING":
                    headings = [
                        str(h).strip() for h in row[1:]
                    ]  # Ensure clean headings
                elif row[0] == "UNIT":
                    units = dict(zip(headings, row[1:]))
                elif row[0] == "TYPE":
                    types = dict(zip(headings, row[1:]))
                elif row[0] == "DATA":
                    # Create a dictionary mapping headers to values
                    values = row[1 : len(headings) + 1]
                    # Pad with empty strings if needed
                    while len(values) < len(headings):
                        values.append("")
                    # Clean values and create row dict
                    values = [str(v).strip() for v in values]
                    data_row = dict(zip(headings, values))
                    data.append(data_row)

        if not headings or not data:
            logger.warning(f"No valid data found for group {group_name}")
            return None

        # Validate data structure
        if any(len(row) != len(headings) for row in data):
            logger.warning(f"Inconsistent data structure in group {group_name}")
            return None

        return AGSGroup(
            name=group_name, headings=headings, units=units, types=types, data=data
        )

    except Exception as e:
        logger.error(f"Error parsing group {group_name}: {str(e)}")
        return None


def chunk_csv(content: str, chunk_size: int) -> Iterator[List[str]]:
    """Generator to read CSV content in chunks."""
    lines = content.splitlines()
    for i in range(0, len(lines), chunk_size):
        yield lines[i : i + chunk_size]


def validate_required_columns(group: str, available_cols: Set[str]) -> bool:
    """
    Validate that all required columns for a group are available.

    Args:
        group: AGS group name (e.g., 'GEOL', 'LOCA')
        available_cols: Set of available column names

    Returns:
        True if all required columns are available
    """
    required = set(AppConfig.AGS_REQUIRED_COLUMNS.get(group, []))
    missing = required - available_cols
    if missing:
        logger.warning(
            f"Missing required columns for {group}: {missing}. "
            f"Available: {available_cols}"
        )
        return False
    return True


def clean_coordinate(val: str) -> Optional[float]:
    """
    Clean and validate a coordinate value.

    Args:
        val: String value to clean

    Returns:
        Float value if valid, None if invalid
    """
    try:
        if pd.isna(val) or val == "":
            return None

        # Remove any whitespace and handle special characters
        val = str(val).strip().replace(",", "")

        # Convert to float
        coord = float(val)
        return coord

    except (ValueError, TypeError) as e:
        logger.debug(f"Could not clean coordinate value '{val}': {e}")
        return None


@log_timing
def convert_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert easting/northing to lat/lon coordinates.

    Args:
        df: DataFrame with LOCA_NATE and LOCA_NATN columns

    Returns:
        DataFrame with added lat and lon columns
    """
    try:
        from utils.coordinates import osgb36_to_latlon

        # Create a copy and convert coordinates to numeric
        df = df.copy()

        # Clean and convert coordinates
        for col in ["LOCA_NATE", "LOCA_NATN"]:
            if col in df.columns:
                df[col] = df[col].apply(clean_coordinate)

        # Check if coordinates exist and are valid
        if not all(col in df.columns for col in ["LOCA_NATE", "LOCA_NATN"]):
            logger.warning("Missing coordinate columns LOCA_NATE and/or LOCA_NATN")
            return df

        # Drop rows with invalid coordinates
        invalid_mask = df[["LOCA_NATE", "LOCA_NATN"]].isna().any(axis=1)
        n_invalid = invalid_mask.sum()
        if n_invalid > 0:
            logger.warning(f"Found {n_invalid} rows with invalid coordinates")

        df = df[~invalid_mask].copy()
        if df.empty:
            logger.error("No valid coordinates found after cleaning")
            return df

        # Convert coordinates
        try:
            # Initialize lat/lon columns
            df["lat"] = pd.NA
            df["lon"] = pd.NA

            # Convert all valid coordinates
            for idx, row in df.iterrows():
                try:
                    lat, lon = osgb36_to_latlon(
                        float(row["LOCA_NATE"]), float(row["LOCA_NATN"])
                    )
                    df.at[idx, "lat"] = lat
                    df.at[idx, "lon"] = lon
                except Exception as e:
                    logger.debug(
                        f"Failed to convert coordinates for row {idx}: {str(e)}"
                    )
                    continue

            # Log results
            n_converted = df[["lat", "lon"]].notna().all(axis=1).sum()
            logger.info(f"Successfully converted {n_converted}/{len(df)} coordinates")

            if n_converted > 0:
                # Log a sample for verification
                sample = df[df[["lat", "lon"]].notna().all(axis=1)].head(1)
                for _, row in sample.iterrows():
                    logger.debug(
                        f"Sample conversion - "
                        f"E/N: {row['LOCA_NATE']}/{row['LOCA_NATN']} -> "
                        f"Lat/Lon: {row['lat']:.6f}/{row['lon']:.6f}"
                    )
            return df

        except Exception as e:
            logger.error(f"Error during coordinate conversion: {str(e)}")
            return df

    except Exception as e:
        logger.error(f"Error in coordinate conversion setup: {str(e)}")
        return df


@st.cache_data(ttl=AppConfig.CACHE_TTL, max_entries=AppConfig.CACHE_MAX_ENTRIES)
@log_timing
def parse_ags_file(content: str, filename: str) -> Dict[str, pd.DataFrame]:
    """Parse AGS file content into DataFrames."""
    try:
        result = {}
        for group_name in AppConfig.AGS_REQUIRED_COLUMNS:
            group = parse_ags_group(content, group_name)
            if group and group.data:
                # Convert to DataFrame
                df = pd.DataFrame(group.data)

                # Get required columns for this group
                required_cols = AppConfig.AGS_REQUIRED_COLUMNS[group_name]

                # For LOCA group, handle coordinate columns
                if group_name == "LOCA":
                    # Try OSGB36 coordinates first
                    coord_cols = ["LOCA_NATE", "LOCA_NATN"]
                    if all(col in df.columns for col in coord_cols):
                        # Convert coordinates
                        for col in coord_cols:
                            df[col] = pd.to_numeric(df[col], errors="coerce")

                        # Only convert if both columns exist and are valid
                        invalid_mask = df[coord_cols].isna().any(axis=1)
                        if not invalid_mask.all():  # If at least some valid coordinates
                            df = convert_coordinates(df)

                    # If OSGB36 coordinates are missing/invalid, try lat/lon
                    lat_lon_cols = ["LOCA_LAT", "LOCA_LON"]
                    if all(col in df.columns for col in lat_lon_cols):
                        logger.info("Using LOCA_LAT/LOCA_LON columns for coordinates")
                        # Convert to numeric and validate
                        for col in lat_lon_cols:
                            df[col] = pd.to_numeric(df[col], errors="coerce")

                        # Copy to standardized column names
                        df["lat"] = df["LOCA_LAT"]
                        df["lon"] = df["LOCA_LON"]

                        # Basic coordinate validation
                        invalid_mask = (
                            df[["lat", "lon"]].isna().any(axis=1)
                            | (df["lat"] < -90)
                            | (df["lat"] > 90)
                            | (df["lon"] < -180)
                            | (df["lon"] > 180)
                        )

                        if invalid_mask.any():
                            logger.warning(
                                f"{invalid_mask.sum()} locations have invalid lat/lon coordinates"
                            )

                    if not any(col in df.columns for col in ["lat", "lon"]):
                        logger.warning(
                            f"No valid coordinates found in {filename}. "
                            f"Available columns: {df.columns.tolist()}"
                        )

                # Check if all required columns are present
                missing = [col for col in required_cols if col not in df.columns]
                if missing:
                    logger.warning(
                        f"Missing required columns for {group_name} in {filename}: {missing}. "
                        f"Available columns: {df.columns.tolist()}"
                    )
                    continue

                # Convert numeric columns based on AGS type codes
                numeric_cols = get_numeric_columns(df.columns.tolist(), group.types)
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                if not df.empty:
                    result[group_name] = df
                    logger.info(
                        f"Successfully parsed {group_name} group from {filename}: "
                        f"{len(df)} rows, {len(df.columns)} columns"
                    )
                else:
                    logger.warning(f"No valid data for {group_name} in {filename}")

        if not result:
            raise ValueError(f"No valid data found in file {filename}")

        return result

    except Exception as e:
        logger.error(f"Error parsing AGS file {filename}: {str(e)}")
        raise


@st.cache_data(ttl=AppConfig.CACHE_TTL)
@log_timing
def parse_multiple_ags_files(files: List[Any]) -> AGSData:
    """Parse multiple AGS files in parallel."""
    try:
        if AppConfig.ENABLE_PARALLEL and len(files) > 1:
            with ThreadPoolExecutor(max_workers=AppConfig.MAX_WORKERS) as executor:
                results = list(
                    executor.map(
                        lambda f: parse_ags_file(f.getvalue().decode(), f.name), files
                    )
                )
        else:
            results = [parse_ags_file(f.getvalue().decode(), f.name) for f in files]

        # Initialize empty DataFrames
        combined = {
            "GEOL": pd.DataFrame(),
            "LOCA": pd.DataFrame(),
            "ABBR": pd.DataFrame(),
        }

        # Track existing IDs to handle duplicates
        existing_ids = set()

        # Combine results
        for result in results:
            for group in ["GEOL", "LOCA", "ABBR"]:
                if group in result and not result[group].empty:
                    df = result[group].copy()

                    # Special handling for LOCA group
                    if group == "LOCA":
                        # Check for coordinate columns
                        coord_cols = ["LOCA_NATE", "LOCA_NATN"]
                        if all(col in df.columns for col in coord_cols):
                            # Convert coordinates only if both columns exist
                            df = convert_coordinates(df)
                        else:
                            logger.warning(
                                "Skipping coordinate conversion - missing coordinate columns"
                            )

                        # Handle duplicate IDs
                        df["original_LOCA_ID"] = df["LOCA_ID"].copy()
                        suffix = os.path.splitext(files[0].name)[0][:19]
                        df["LOCA_ID"] = df["LOCA_ID"].apply(
                            lambda x: f"{x}_{suffix}" if x in existing_ids else x
                        )
                        existing_ids.update(df["LOCA_ID"].tolist())

                    # Combine with existing data
                    if combined[group].empty:
                        combined[group] = df
                    else:
                        combined[group] = pd.concat(
                            [combined[group], df], ignore_index=True
                        )

        # Validate combined data
        if combined["GEOL"].empty or combined["LOCA"].empty:
            raise ValueError("No valid GEOL or LOCA data found in files")

        # Create AGSData object and optimize memory
        data = AGSData(
            geol_df=combined["GEOL"], loca_df=combined["LOCA"], abbr_df=combined["ABBR"]
        )
        data.optimize_memory()
        return data

    except Exception as e:
        logger.error(f"Error parsing multiple AGS files: {str(e)}")
        raise


def parse_ags_files(files: Union[List[Any], Any]) -> Optional[AGSData]:
    """
    Parse one or more AGS files and return combined data.

    Args:
        files: Single file or list of files from st.file_uploader

    Returns:
        AGSData object containing combined data from all files, or None if error
    """
    try:
        if not files:
            return None

        # Convert single file to list
        if not isinstance(files, list):
            files = [files]

        return parse_multiple_ags_files(files)

    except Exception as e:
        logger.error(f"Error processing AGS files: {str(e)}")
        return None


# For backwards compatibility
__all__ = ["AGSData", "parse_ags_files", "parse_ags_file", "parse_multiple_ags_files"]
