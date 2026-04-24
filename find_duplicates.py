# F_Dups_console.py
from __future__ import annotations
import os
import sys
from pathlib import Path
import math
from typing import List, Optional

try:
    import pandas as pd  # type: ignore[import]
except ImportError:
    print("Missing dependency: pandas. Install it with 'pip install pandas openpyxl'.")
    sys.exit(1)

APP_NAME = "F_Dups"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def pause(msg="Press Enter to continue..."):
    input(msg)

def column_letter(idx: int) -> str:
    letters = ""
    while True:
        idx, rem = divmod(idx, 26)
        letters = chr(ord("A") + rem) + letters
        if idx == 0:
            break
        idx -= 1
    return letters

def list_headers(df: pd.DataFrame):
    return [(column_letter(i), i, str(h)) for i, h in enumerate(df.columns)]

def print_header(title):
    clear()
    print(f"{APP_NAME} — {title}")
    print("=" * (len(APP_NAME) + 4 + len(title)))
    print()

def parse_selection(sel: str, df: pd.DataFrame) -> List[str]:
    parts = [p.strip() for p in sel.replace(";", ",").split(",") if p.strip()]
    chosen = []
    headers = list(df.columns)
    letter_map = {column_letter(i): headers[i] for i in range(len(headers))}
    name_map = {str(h).lower(): h for h in headers}
    for p in parts:
        pu = p.upper()
        if pu in letter_map:
            chosen.append(letter_map[pu])
            continue
        if p.isdigit():
            idx = int(p) - 1
            if 0 <= idx < len(headers):
                chosen.append(headers[idx])
                continue
            else:
                raise ValueError(f"Index out of range: {p}")
        pl = p.lower()
        if pl in name_map:
            chosen.append(name_map[pl])
            continue
        raise ValueError(f"Could not interpret selection: '{p}'")
    uniq = []
    for c in chosen:
        if c not in uniq:
            uniq.append(c)
    return uniq

def try_format_number(v, precision):
    try:
        if v is None:
            return ""
        if isinstance(v, float) and math.isnan(v):
            return ""
        num = float(v)
    except Exception:
        return str(v)
    return f"{num:.{precision}f}"

def format_latlon_in_df(out_df: pd.DataFrame) -> pd.DataFrame:
    lat_candidates = [c for c in out_df.columns if c.lower() == "latitude"]
    lon_candidates = [c for c in out_df.columns if c.lower() == "longitude"]
    if lat_candidates:
        lat_col = lat_candidates[0]
        out_df[lat_col] = out_df[lat_col].apply(lambda v: try_format_number(v, 5))
    if lon_candidates:
        lon_col = lon_candidates[0]
        out_df[lon_col] = out_df[lon_col].apply(lambda v: try_format_number(v, 5))
    return out_df

def find_duplicates_on_columns(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    df2 = df.copy()
    for c in cols:
        if df2[c].dtype == object:
            df2[c] = df2[c].astype(str).str.strip()
    key = df2[cols].astype(str).agg("||".join, axis=1)
    dup_mask = key.duplicated(keep=False)
    result = df.loc[dup_mask].copy()
    return result

def browse_for_file(start_dir: Path = Path.cwd()) -> Optional[Path]:
    cur = start_dir.resolve()
    while True:
        print_header("Choose Excel file (navigate folders). Type 'back' to cancel.")
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
            if f.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
                fcount += 1
                print(f"  F{fcount:>2}: {f.name}")
                file_map[fcount] = f
        if fcount == 0:
            print("  (No Excel files in this folder)")
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

def display_columns_and_choose(df: pd.DataFrame) -> Optional[List[str]]:
    headers = list_headers(df)
    while True:
        print_header("Select up to 3 columns for duplicate detection (Back to cancel)")
        print("Available columns:")
        for letter, idx, name in headers:
            print(f"  {letter:>3}  {idx+1:>3}  {name}")
        print()
        print("Enter up to three columns separated by commas. You may use:")
        print(" - Column letters (A, B, ...)")
        print(" - 1-based indices (1, 2, ...)")
        print(" - Exact header names (case-insensitive)")
        print("Type 'back' to return.")
        sel = input("\nColumns: ").strip()
        if not sel:
            continue
        if sel.lower() == "back":
            return None
        try:
            chosen = parse_selection(sel, df)
            if len(chosen) > 3:
                print("Please select at most 3 columns.")
                pause()
                continue
            return chosen
        except ValueError as e:
            print("Error:", e)
            pause()

def save_duplicates_and_sorted(df: pd.DataFrame, duplicates: pd.DataFrame, selected_columns: List[str], orig_path: Path) -> None:
    try:
        # 1) Save a copy of the original file next to the original: <name>.orig.<ext>
        orig_backup = orig_path.with_name(orig_path.stem + ".orig" + orig_path.suffix)
        try:
            # Try writing data to Excel backup (data-only)
            df.to_excel(orig_backup, index=False, engine="openpyxl")
        except Exception:
            # fallback: binary copy
            from shutil import copy2
            copy2(orig_path, orig_backup)

        # 2) Save duplicates CSV
        safe_cols = "_".join([str(c).replace(" ", "_") for c in selected_columns]) or "cols"
        dup_name = Path.cwd() / f"duplicates_{safe_cols}.csv"
        dup_to_save = format_latlon_in_df(duplicates.copy())
        dup_to_save.to_csv(dup_name, index=False)

        # 3) Create original-sorted file: remove duplicates (rows that were part of any duplicate group) and sort by selected columns
        df2 = df.copy()
        for c in selected_columns:
            if df2[c].dtype == object:
                df2[c] = df2[c].astype(str).str.strip()
        key = df2[selected_columns].astype(str).agg("||".join, axis=1)
        dup_mask = key.duplicated(keep=False)
        kept = df.loc[~dup_mask].copy()
        if not kept.empty:
            try:
                kept_sorted = kept.sort_values(by=selected_columns, kind="stable")
            except Exception:
                kept_sorted = kept
        else:
            kept_sorted = kept
        sorted_name = Path.cwd() / f"{orig_path.stem}-sorted.csv"
        kept_to_save = format_latlon_in_df(kept_sorted.copy())
        kept_to_save.to_csv(sorted_name, index=False)

        print()
        print("Saved files:")
        print(f"  Original backup: {orig_backup}")
        print(f"  Duplicates CSV: {dup_name}")
        print(f"  Original (duplicates removed, sorted): {sorted_name}")
        pause()
    except Exception as e:
        print("Error saving files:", e)
        pause()

def main_menu():
    while True:
        print_header("Main Menu")
        print("1) Select Excel file")
        print("2) Quit")
        choice = input("\nChoose an option: ").strip()
        if choice == "1":
            file_path = browse_for_file()
            if file_path is None:
                continue
            try:
                df = pd.read_excel(file_path, engine="openpyxl")
            except Exception as e:
                print_header("Error reading file")
                print("Failed to open Excel file:", e)
                pause()
                continue
            cols = display_columns_and_choose(df)
            if cols is None:
                continue
            print_header("Confirm selection")
            print(f"File: {file_path}")
            print("Selected columns:")
            for c in cols:
                print(f"  - {c}")
            print()
            print("Options:")
            print("  1) Find duplicates now")
            print("  2) Back (choose different columns/file)")
            opt = input("\nChoose: ").strip()
            if opt == "2" or opt.lower() == "back":
                continue
            duplicates = find_duplicates_on_columns(df, cols)
            if duplicates.empty:
                print_header("No duplicates found")
                print(f"No duplicate rows where all of {cols} match exactly.")
                pause()
                continue
            print_header("Duplicates found")
            preview = format_latlon_in_df(duplicates.copy())
            print(preview.head(50).to_string(index=False))
            print()
            print(f"Total duplicate rows: {len(duplicates)}")
            print()
            print("Save options:")
            print("  1) Save duplicates and create original-sorted file (also make an original backup)")
            print("  2) Cancel")
            sopt = input("\nChoose: ").strip()
            if sopt == "1":
                save_duplicates_and_sorted(df, duplicates, cols, file_path)
                continue
            else:
                continue
        elif choice == "2" or choice.lower() in ("q", "quit", "exit"):
            print("Goodbye.")
            sys.exit(0)
        else:
            continue

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(0)
