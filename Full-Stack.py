#!/usr/bin/env python3
"""
Merged script: Find and adjust duplicate coordinates.
Opens chosen file, detects duplicates by lat/lon, adjusts duplicates by 1-20m offsets avoiding collisions,
repeats until no duplicates, saves updated file and mapping CSV.
Requires pandas, pyproj.
"""

import os
import sys
import random
import pathlib
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np

try:
    from pyproj import Geod
except ImportError:
    print("Missing dependency: pyproj. Install with 'pip install pyproj'.")
    sys.exit(1)

# Settings
MIN_OFFSET_M = 1.0
MAX_OFFSET_M = 100.0
MAX_ITERATIONS = 20
MAX_TRIES_PER_ADJUSTMENT = 100
OUTPUT_DECIMALS = 4
DUPLICATE_PRECISION = 8  # decimals for detecting duplicates

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def pause(msg="Press Enter to continue..."):
    input(msg)

def browse_for_file(start_dir: Path = Path.cwd()) -> Optional[Path]:
    # Same as in find_duplicates.py
    cur = start_dir.resolve()
    while True:
        clear()
        print("Choose file (navigate folders). Type 'back' to cancel.")
        dirs = [p for p in cur.iterdir() if p.is_dir()]
        files = [p for p in cur.iterdir() if p.is_file()]
        dirs.sort()
        files.sort()
        print(f"Current folder: {cur}")
        print()
        print("Directories:")
        for i, d in enumerate(dirs, 1):
            print(f"  D{i:>2}: {d.name}/")
        print()
        print("Files:")
        file_map = {}
        fcount = 0
        for f in files:
            if f.suffix.lower() in (".xlsx", ".xlsm", ".xls", ".csv"):
                fcount += 1
                print(f"  F{fcount:>2}: {f.name}")
                file_map[fcount] = f
        if fcount == 0:
            print("  (No supported files in this folder)")
        print()
        print("Commands:")
        print("  cd <D#>   - enter directory number (e.g., cd D1)")
        print("  up        - go to parent folder")
        print("  open <F#> - select file number (e.g., open F2)")
        print("  path <full-path> - type or paste full path to file")
        print("  back      - cancel file selection")
        choice = input("\nEnter command: ").strip()
        if not choice:
            continue
        if choice.lower() == "back":
            return None
        if choice.lower() == "up":
            if cur.parent != cur:
                cur = cur.parent
            continue
        if choice.lower().startswith("cd "):
            token = choice[3:].strip()
            if token.upper().startswith("D"):
                try:
                    num = int(token[1:])
                    if 1 <= num <= len(dirs):
                        cur = dirs[num - 1]
                    else:
                        print("Invalid directory number.")
                        pause()
                except Exception:
                    print("Invalid directory command.")
                    pause()
                continue
            else:
                new = cur / token
                if new.is_dir():
                    cur = new
                else:
                    print("Directory not found.")
                    pause()
                continue
        if choice.lower().startswith("open "):
            token = choice[5:].strip()
            if token.upper().startswith("F"):
                try:
                    num = int(token[1:])
                    if num in file_map:
                        return file_map[num]
                    else:
                        print("Invalid file number.")
                        pause()
                except Exception:
                    print("Invalid open command.")
                    pause()
                continue
            else:
                print("Use 'open F#' to select a file.")
                pause()
                continue
        if choice.lower().startswith("path "):
            path_str = choice[5:].strip().strip('"').strip("'")
            p = Path(path_str)
            if p.exists() and p.is_file():
                return p
            else:
                print("Path not found or not a file.")
                pause()
                continue
        print("Unrecognized command.")
        pause()

def load_file(file_path: Path) -> pd.DataFrame:
    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path, engine="openpyxl")
    return df

def detect_lat_lon_columns(df: pd.DataFrame) -> Tuple[str, str]:
    cols = list(df.columns)
    lower = [c.lower() for c in cols]
    lat_candidates = [cols[i] for i, c in enumerate(lower) if "lat" in c]
    lon_candidates = [cols[i] for i, c in enumerate(lower) if "lon" in c or "lng" in c or "long" in c]
    if lat_candidates and lon_candidates:
        return lat_candidates[0], lon_candidates[0]
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) >= 2:
        return numeric_cols[0], numeric_cols[1]
    raise ValueError("Could not detect latitude/longitude columns. Ensure column names include 'lat' and 'lon' or file contains at least two numeric columns.")

def find_duplicate_groups(df: pd.DataFrame, lat_col: str, lon_col: str) -> dict:
    coords = df[[lat_col, lon_col]].round(DUPLICATE_PRECISION)
    grouped = coords.groupby([lat_col, lon_col]).groups
    return {k: v.tolist() for k, v in grouped.items() if len(v) > 1}

def adjust_duplicates(df: pd.DataFrame, lat_col: str, lon_col: str, geod: Geod, seed: Optional[int] = None) -> Tuple[pd.DataFrame, List[dict], int]:
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    df_adj = df.copy()
    mapping = []
    total_adjusted = 0

    # Get all existing coords rounded to OUTPUT_DECIMALS for collision check
    existing_coords = set()
    for idx in df.index:
        lat = round(float(df.at[idx, lat_col]), OUTPUT_DECIMALS)
        lon = round(float(df.at[idx, lon_col]), OUTPUT_DECIMALS)
        existing_coords.add((lat, lon))

    groups = find_duplicate_groups(df, lat_col, lon_col)

    for (lat_val, lon_val), indices in groups.items():
        # Keep first, adjust others
        for i, idx in enumerate(indices):
            if i == 0:
                continue  # keep first
            original_lat = float(df.at[idx, lat_col])
            original_lon = float(df.at[idx, lon_col])
            adjusted = False
            for _ in range(MAX_TRIES_PER_ADJUSTMENT):
                offset_m = random.uniform(MIN_OFFSET_M, MAX_OFFSET_M)
                bearing = random.uniform(0.0, 360.0)
                # Use geod.fwd: fwd(lon, lat, azimuth, distance)
                new_lon, new_lat, _ = geod.fwd(original_lon, original_lat, bearing, offset_m)
                new_lat_rounded = round(new_lat, OUTPUT_DECIMALS)
                new_lon_rounded = round(new_lon, OUTPUT_DECIMALS)
                if (new_lat_rounded, new_lon_rounded) not in existing_coords:
                    df_adj.at[idx, lat_col] = new_lat_rounded
                    df_adj.at[idx, lon_col] = new_lon_rounded
                    existing_coords.add((new_lat_rounded, new_lon_rounded))
                    mapping.append({
                        'original_lat': original_lat,
                        'original_lon': original_lon,
                        'adjusted_lat': new_lat_rounded,
                        'adjusted_lon': new_lon_rounded
                    })
                    adjusted = True
                    total_adjusted += 1
                    break
            if not adjusted:
                # If couldn't adjust without collision, keep original but warn
                print(f"Warning: Could not adjust duplicate at index {idx} without collision.")
                df_adj.at[idx, lat_col] = round(original_lat, OUTPUT_DECIMALS)
                df_adj.at[idx, lon_col] = round(original_lon, OUTPUT_DECIMALS)

    # Round all coordinates to output decimals
    df_adj[lat_col] = df_adj[lat_col].round(OUTPUT_DECIMALS)
    df_adj[lon_col] = df_adj[lon_col].round(OUTPUT_DECIMALS)

    return df_adj, mapping, total_adjusted

def process_file(file_path: Path) -> None:
    print(f"Loading '{file_path}'...")
    df = load_file(file_path)
    lat_col, lon_col = detect_lat_lon_columns(df)
    print(f"Detected latitude column: '{lat_col}', longitude column: '{lon_col}'")

    geod = Geod(ellps='WGS84')

    # Find initial duplicates
    initial_groups = find_duplicate_groups(df, lat_col, lon_col)
    if initial_groups:
        initial_duplicates = df.loc[sorted([idx for indices in initial_groups.values() for idx in indices])]
        initial_dup_path = file_path.with_name(file_path.stem + "_initial_duplicates.csv")
        initial_duplicates.to_csv(initial_dup_path, index=False)
        print(f"Saved initial duplicates: {initial_dup_path}")
    else:
        print("No initial duplicates found.")

    iteration = 0
    all_mappings = []
    while iteration < MAX_ITERATIONS:
        groups = find_duplicate_groups(df, lat_col, lon_col)
        if not groups:
            break
        print(f"Iteration {iteration + 1}: Found {sum(len(v) for v in groups.values())} duplicate rows in {len(groups)} groups.")
        df, mapping, adjusted = adjust_duplicates(df, lat_col, lon_col, geod)
        all_mappings.extend(mapping)
        print(f"Adjusted {adjusted} rows.")
        iteration += 1

    if iteration == MAX_ITERATIONS:
        print("Warning: Reached max iterations, duplicates may still exist.")

    # Save merged file (adjusted)
    merged_path = file_path.with_name(file_path.stem + "_merged" + file_path.suffix)
    df.to_csv(merged_path, index=False) if file_path.suffix.lower() == ".csv" else df.to_excel(merged_path, index=False, engine="openpyxl")
    print(f"Saved merged file: {merged_path}")

    # Save duplicate file (mapping of adjustments)
    if all_mappings:
        mapping_df = pd.DataFrame(all_mappings)
        duplicate_path = file_path.with_name(file_path.stem + "_duplicates.csv")
        mapping_df.to_csv(duplicate_path, index=False)
        print(f"Saved duplicates file: {duplicate_path}")
    else:
        print("No duplicates were adjusted.")

def main():
    print("Duplicate Coordinate Finder and Adjuster")
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return
    else:
        file_path = browse_for_file()
        if file_path is None:
            print("No file selected. Exiting.")
            return
    try:
        process_file(file_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    print("Done.")

if __name__ == "__main__":
    main()