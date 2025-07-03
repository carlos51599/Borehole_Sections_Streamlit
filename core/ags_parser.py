"""AGS file parsing and data management."""

import streamlit as st
from typing import List, Dict, Any, Iterator
import pandas as pd
import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from core.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass
class AGSData:
    """Container for AGS data groups."""

    geol_df: pd.DataFrame
    loca_df: pd.DataFrame
    abbr_df: pd.DataFrame

    @property
    def has_valid_data(self) -> bool:
        """Check if the data is valid for plotting."""
        return not (self.geol_df.empty or self.loca_df.empty)

    def optimize_memory(self) -> None:
        """Optimize memory usage of dataframes."""
        if AppConfig.USE_CATEGORICAL:
            # Convert string columns to categorical
            for df in [self.geol_df, self.loca_df, self.abbr_df]:
                for col in df.select_dtypes(include=["object"]):
                    df[col] = df[col].astype("category")


def chunk_csv(content: str, chunk_size: int) -> Iterator[List[str]]:
    """Generator to read CSV content in chunks."""
    lines = content.splitlines()
    for i in range(0, len(lines), chunk_size):
        yield lines[i : i + chunk_size]


@st.cache_data(ttl=AppConfig.CACHE_TTL, max_entries=AppConfig.CACHE_MAX_ENTRIES)
def parse_ags_file(content: str, filename: str) -> Dict[str, pd.DataFrame]:
    """
    Parse AGS file content into DataFrames.

    Args:
        content: AGS file content as string
        filename: Name of the file (for logging)

    Returns:
        Dictionary of group names to DataFrames
    """
    try:
        groups: Dict[str, List[List[str]]] = {}
        current_group = None
        headings = []

        # Process file in chunks
        for chunk in chunk_csv(content, AppConfig.LARGE_DF_CHUNK_SIZE):
            parsed_chunk = list(csv.reader(chunk, delimiter=",", quotechar='"'))

            for row in parsed_chunk:
                if not row:
                    continue

                if row[0] == "GROUP" and len(row) > 1:
                    current_group = row[1]
                    if current_group not in groups:
                        groups[current_group] = []
                    continue

                if current_group:
                    if row[0] == "HEADING":
                        headings = row[1:]
                    elif row[0] == "DATA":
                        groups[current_group].append(row[1 : len(headings) + 1])

        # Convert to DataFrames with required columns only
        result = {}
        for group, data in groups.items():
            if group in AppConfig.AGS_REQUIRED_COLUMNS:
                df = pd.DataFrame(data, columns=headings)
                # Only keep required columns
                required_cols = AppConfig.AGS_REQUIRED_COLUMNS[group]
                df = df[required_cols]
                result[group] = df

        return result

    except Exception as e:
        logger.error(f"Error parsing AGS file {filename}: {str(e)}")
        raise


@st.cache_data(ttl=AppConfig.CACHE_TTL)
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

        # Combine results
        combined = {
            "GEOL": pd.concat([r["GEOL"] for r in results if "GEOL" in r]),
            "LOCA": pd.concat([r["LOCA"] for r in results if "LOCA" in r]),
            "ABBR": pd.concat([r["ABBR"] for r in results if "ABBR" in r]),
        }

        data = AGSData(
            geol_df=combined["GEOL"], loca_df=combined["LOCA"], abbr_df=combined["ABBR"]
        )
        data.optimize_memory()
        return data

    except Exception as e:
        logger.error(f"Error parsing multiple AGS files: {str(e)}")
        raise
