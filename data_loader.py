import csv
import pandas as pd
import os
from utils import get_session_state, safe_temp_path


def parse_group(content, group_name):
    lines = content.splitlines()
    parsed = list(csv.reader(lines, delimiter=",", quotechar='"'))
    headings = []
    data = []
    in_group = False
    for row in parsed:
        if row and row[0] == "GROUP" and len(row) > 1 and row[1] == group_name:
            in_group = True
            continue
        if in_group and row and row[0] == "HEADING":
            headings = row[1:]
            continue
        if in_group and row and row[0] == "DATA":
            data.append(row[1 : len(headings) + 1])
            continue
        if (
            in_group
            and row
            and row[0] == "GROUP"
            and (len(row) < 2 or row[1] != group_name)
        ):
            break
    df = pd.DataFrame(data, columns=headings)
    return df


def load_all_loca_data(ags_files):
    all_loca = []
    filename_map = {}
    existing_ids = set()
    for fname, content in ags_files:
        loca_df = parse_group(content, "LOCA")
        for col in ["LOCA_NATE", "LOCA_NATN"]:
            if col in loca_df.columns:
                loca_df[col] = pd.to_numeric(loca_df[col], errors="coerce")
        loca_df = loca_df.dropna(subset=["LOCA_NATE", "LOCA_NATN"])

        suffix = os.path.splitext(fname)[0][:19]
        loca_df["original_LOCA_ID"] = loca_df["LOCA_ID"]
        loca_df["LOCA_ID"] = loca_df["LOCA_ID"].apply(
            lambda x: f"{x}_{suffix}" if x in existing_ids else x
        )
        existing_ids.update(loca_df["LOCA_ID"].tolist())

        loca_df["ags_file"] = fname
        all_loca.append(loca_df)
        filename_map[fname] = content

    return pd.concat(all_loca, ignore_index=True), filename_map
