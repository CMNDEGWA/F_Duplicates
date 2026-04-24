#!/usr/bin/env python3
"""
Adjust duplicate coordinates (lat, lon) by random offsets between 1 and 20 meters.
Terminal-based file selection menu and summary output.

Dependencies:
  pip install pandas openpyxl numpy
"""

import os
import sys
import math
import random
import pathlib
import pandas as pd
import numpy as np

# Settings
MIN_OFFSET_M = 1.0
MAX_OFFSET_M = 20.0
EARTH_RADIUS_M = 6371000.0  # mean Earth radius

def list_data_files(folder="."):
    exts = (".xlsx", ".xls", ".csv")
    files = [f for f in os.listdir(folder) if f.lower().endswith(exts)]
    return files

def choose_file(files):
    if not files:
        print("No .xlsx/.xls/.csv files found in current directory.")
        sys.exit(1)
    print("Select input file:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f}")
    choice = input(f"Enter number (1-{len(files)}): ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(files):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        sys.exit(1)
    return files[idx]

def load_file(path):
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    return df

def ensure_latlon_columns(df):
    # Try common names; require at least two columns that look like lat/lon
    cols = [c for c in df.columns]
    lower = [c.lower() for c in cols]
    lat_candidates = [cols[i] for i, c in enumerate(lower) if "lat" in c]
    lon_candidates = [cols[i] for i, c in enumerate(lower) if "lon" in c or "lng" in c or "long" in c]
    if lat_candidates and lon_candidates:
        return lat_candidates[0], lon_candidates[0]
    # fallback: if exactly two numeric columns aside from code, take them
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) >= 2:
        return numeric_cols[0], numeric_cols[1]
    raise ValueError("Could not detect latitude/longitude columns. Make sure column names include 'lat' and 'lon' or file contains numeric lat/lon columns.")

def meters_to_dlat_dlon(lat_deg, meters_north, meters_east):
    # converts small displacements in meters to delta degrees
    lat_rad = math.radians(lat_deg)
    dlat = (meters_north / EARTH_RADIUS_M) * (180.0 / math.pi)
    dlon = (meters_east / (EARTH_RADIUS_M * math.cos(lat_rad))) * (180.0 / math.pi)
    return dlat, dlon

def offset_point(lat, lon, offset_m, bearing_deg):
    # Returns new lat, lon after moving offset_m at bearing_deg from original point.
    # Use small-angle approximation by converting meters into north/east components.
    bearing_rad = math.radians(bearing_deg)
    meters_north = offset_m * math.cos(bearing_rad)
    meters_east = offset_m * math.sin(bearing_rad)
    dlat, dlon = meters_to_dlat_dlon(lat, meters_north, meters_east)
    return lat + dlat, lon + dlon

def adjust_duplicates(df, lat_col, lon_col, seed=None):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    coords = df[[lat_col, lon_col]].round(8)  # rounding to avoid float noise when detecting duplicates
    # find groups of identical coordinates
    grouped = coords.groupby([lat_col, lon_col]).indices
    # Prepare new columns
    new_lats = df[lat_col].astype(float).to_numpy().copy()
    new_lons = df[lon_col].astype(float).to_numpy().copy()
    n_adjusted = 0
    for (lat_val, lon_val), indices in grouped.items():
        if len(indices) <= 1:
            continue
        # For the first occurrence keep it unchanged, adjust the rest
        for idx_in_group, row_idx in enumerate(indices):
            if idx_in_group == 0:
                continue
            offset_m = random.uniform(MIN_OFFSET_M, MAX_OFFSET_M)
            bearing = random.uniform(0.0, 360.0)
            new_lat, new_lon = offset_point(float(lat_val), float(lon_val), offset_m, bearing)
            new_lats[row_idx] = new_lat
            new_lons[row_idx] = new_lon
            n_adjusted += 1
    df_out = df.copy()
    df_out[lat_col] = new_lats
    df_out[lon_col] = new_lons
    return df_out, n_adjusted

def main():
    print("Duplicate Coordinate Adjuster — Terminal")
    files = list_data_files(".")
    file_name = choose_file(files)
    print(f"Loading '{file_name}'...")
    df = load_file(file_name)
    try:
        lat_col, lon_col = ensure_latlon_columns(df)
    except ValueError as e:
        print("Error:", e)
        print("Columns found:", list(df.columns))
        sys.exit(1)
    print(f"Detected latitude column: '{lat_col}', longitude column: '{lon_col}'")
    total_rows = len(df)
    # Count duplicates
    coord_counts = df.groupby([lat_col, lon_col]).size().reset_index(name="count")
    dup_groups = coord_counts[coord_counts["count"] > 1]
    total_duplicate_rows = int(dup_groups["count"].sum())
    total_duplicate_groups = len(dup_groups)
    print(f"Rows: {total_rows}, Duplicate groups: {total_duplicate_groups}, Duplicate rows (including originals): {total_duplicate_rows}")
    if total_duplicate_groups == 0:
        print("No duplicates found. Exiting.")
        sys.exit(0)
    seed_in = input("Enter integer seed for reproducible offsets (or press Enter for random): ").strip()
    seed = int(seed_in) if seed_in != "" else None
    df_adj, n_adjusted = adjust_duplicates(df, lat_col, lon_col, seed=seed)
    out_path = pathlib.Path(file_name).with_name(pathlib.Path(file_name).stem + "_adjusted.xlsx")
    df_adj.to_excel(out_path, index=False)
    print(f"Adjusted {n_adjusted} duplicate rows. Saved adjusted file as: {out_path.name}")
    print("Done.")

if __name__ == "__main__":
    main()
