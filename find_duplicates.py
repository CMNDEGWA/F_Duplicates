# find_duplicates_flexible.py
import sys
from pathlib import Path
import pandas as pd
import string

def column_letter(idx):
    # 0 -> A, 1 -> B, ...
    letters = ""
    while True:
        idx, rem = divmod(idx, 26)
        letters = chr(ord("A") + rem) + letters
        if idx == 0:
            break
        idx -= 1
    return letters

def list_headers(df):
    headers = list(df.columns)
    rows = []
    for i, h in enumerate(headers):
        rows.append((column_letter(i), i, str(h)))
    return rows

def parse_selection(sel, headers_map):
    # sel may be letters (A,B), indices (1,2) or names; allow up to 3 columns
    parts = [p.strip() for p in sel.replace(";", ",").split(",") if p.strip()]
    chosen = []
    for p in parts:
        # letter form
        p_up = p.upper()
        if p_up in headers_map["by_letter"]:
            chosen.append(headers_map["by_letter"][p_up])
            continue
        # 1-based index form
        if p.isdigit():
            idx = int(p) - 1
            if 0 <= idx < len(headers_map["by_index"]):
                chosen.append(headers_map["by_index"][idx])
                continue
        # name form (case-insensitive)
        match = headers_map["by_name"].get(p.lower())
        if match is not None:
            chosen.append(match)
            continue
        # partial name match (case-insensitive)
        partials = [v for k,v in headers_map["by_name"].items() if p.lower() == k]
        if partials:
            chosen.append(partials[0])
            continue
        raise ValueError(f"Could not interpret selection: '{p}'")
    if len(chosen) == 0:
        raise ValueError("No columns selected.")
    if len(chosen) > 3:
        raise ValueError("Maximum 3 columns allowed.")
    # ensure unique
    chosen_unique = []
    for c in chosen:
        if c not in chosen_unique:
            chosen_unique.append(c)
    return chosen_unique

def find_duplicates_on_columns(df, cols):
    # Trim whitespace for string columns
    df2 = df.copy()
    for c in cols:
        if df2[c].dtype == object:
            df2[c] = df2[c].astype(str).str.strip()
    # Build composite key from original cell content (no rounding)
    key = df2[cols].astype(str).agg("||".join, axis=1)
    dup_mask = key.duplicated(keep=False)
    result = df.loc[dup_mask].copy()
    return result, cols

def filename_for_cols(base, cols):
    safe = "_".join([str(c).replace(" ", "_") for c in cols])
    return f"{base}_{safe}.csv"

def interactive_choice(df):
    headers = list_headers(df)
    print("\nAvailable columns:")
    for letter, idx, name in headers:
        print(f"  {letter:>3}  {idx+1:>3}  {name}")
    # build lookup maps
    by_letter = {column_letter(i): col for i, col in enumerate(df.columns)}
    by_index = list(df.columns)
    by_name = {str(col).lower(): col for col in df.columns}
    headers_map = {"by_letter": by_letter, "by_index": by_index, "by_name": by_name}
    print("\nChoose up to 3 columns to use for duplicate detection.")
    print("You can enter letters (A,B), numbers (1,2) or header names (Code,Latitude).")
    sel = input("Columns (comma-separated): ").strip()
    chosen = parse_selection(sel, headers_map)
    return chosen

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_duplicates_flexible.py input.xlsx [out.csv]")
        sys.exit(1)
    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print("Input file not found:", input_path)
        sys.exit(1)
    df = pd.read_excel(input_path, engine="openpyxl")
    chosen = interactive_choice(df)
    print(f"\nSelected columns: {chosen}\nFinding duplicates where ALL selected columns match exactly...")
    duplicates, cols = find_duplicates_on_columns(df, chosen)
    if duplicates.empty:
        print("No duplicates found for the selected columns.")
        sys.exit(0)
    out_name = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path(filename_for_cols("duplicates", chosen))
    # Round lat/lon to 5 decimals in output if those columns are present
    out_df = duplicates.copy()
    for c in ["Latitude", "latitude", "LATITUDE"]:
        if c in out_df.columns:
            out_df[c] = pd.to_numeric(out_df[c], errors="coerce").map(
                lambda x: f"{x:.5f}" if pd.notna(x) else out_df[c]
            )
            # only apply once
            break
    for c in ["Longitude", "longitude", "LONGITUDE"]:
        if c in out_df.columns:
            out_df[c] = pd.to_numeric(out_df[c], errors="coerce").map(
                lambda x: f"{x:.5f}" if pd.notna(x) else out_df[c]
            )
            break
    out_df.to_csv(out_name, index=False)
    print(f"Saved {len(out_df)} duplicate rows to: {out_name}")

if __name__ == "__main__":
    main()
