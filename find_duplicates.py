# find_duplicates_coordinates.py
import sys
from pathlib import Path
import pandas as pd

def find_code_duplicates(df, code_col):
    codes = df[code_col].astype(str).str.strip()
    return df[codes.duplicated(keep=False)].copy()

def find_coordinate_duplicates_exact(df, lat_col, lon_col, output_precision=5):
    # Use original cell values (as strings) for exact matching.
    # Convert to string preserving original formatting as much as possible.
    lat_orig = df[lat_col].astype(str)
    lon_orig = df[lon_col].astype(str)
    coord_key = lat_orig + "||" + lon_orig  # delimiter unlikely to appear in numeric cells
    df2 = df.copy()
    df2["_coord_key"] = coord_key
    dup_mask = df2["_coord_key"].duplicated(keep=False)
    result = df2[dup_mask].copy()
    # For output, format numeric lat/lon to fixed output_precision decimals.
    # If conversion to numeric fails (non-numeric), keep the original string.
    def fmt_series(orig_series):
        num = pd.to_numeric(orig_series, errors="coerce")
        formatted = num.round(output_precision).map(lambda x: f"{x:.{output_precision}f}" if pd.notna(x) else None)
        # where conversion failed, fall back to the original string
        return formatted.where(formatted.notna(), orig_series)
    if not result.empty:
        result[lat_col] = fmt_series(result[lat_col])
        result[lon_col] = fmt_series(result[lon_col])
    return result.drop(columns=["_coord_key"])

def find_and_save(input_path: Path,
                  out_code_csv: Path = Path("duplicates_by_code.csv"),
                  out_coord_csv: Path = Path("duplicates_by_coordinate.csv"),
                  code_col=None, lat_col=None, lon_col=None,
                  output_precision: int = 5):
    df = pd.read_excel(input_path, engine="openpyxl")
    cols_map = {c.lower(): c for c in df.columns}
    if code_col is None:
        if "code" in cols_map:
            code_col = cols_map["code"]
        else:
            raise ValueError("No 'Code' column found.")
    if lat_col is None:
        if "latitude" in cols_map:
            lat_col = cols_map["latitude"]
        else:
            raise ValueError("No 'Latitude' column found.")
    if lon_col is None:
        if "longitude" in cols_map:
            lon_col = cols_map["longitude"]
        else:
            raise ValueError("No 'Longitude' column found.")
    df[code_col] = df[code_col].astype(str).str.strip()
    # Code duplicates
    dup_codes = find_code_duplicates(df, code_col)
    if dup_codes.empty:
        print("No duplicate Codes found.")
    else:
        dup_codes.sort_values(by=code_col, inplace=True)
        dup_codes.to_csv(out_code_csv, index=False)
        print(f"Saved {len(dup_codes)} duplicate rows by Code to: {out_code_csv}")
    # Coordinate duplicates: exact match on both Latitude and Longitude as they appear in the sheet
    dup_coords = find_coordinate_duplicates_exact(df, lat_col, lon_col, output_precision=output_precision)
    if dup_coords.empty:
        print("No duplicate coordinates found.")
    else:
        # build a sort key from the formatted lat/lon for readability
        dup_coords["__coord"] = dup_coords[lat_col].astype(str) + "," + dup_coords[lon_col].astype(str)
        dup_coords.sort_values(by="__coord", inplace=True)
        dup_coords.drop(columns="__coord", inplace=True)
        dup_coords.to_csv(out_coord_csv, index=False)
        print(f"Saved {len(dup_coords)} duplicate rows by coordinate to: {out_coord_csv}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_duplicates_coordinates.py input.xlsx [out_code.csv] [out_coord.csv] [output_precision]")
        sys.exit(1)
    inp = Path(sys.argv[1])
    out_code = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path("duplicates_by_code.csv")
    out_coord = Path(sys.argv[3]) if len(sys.argv) >= 4 else Path("duplicates_by_coordinate.csv")
    output_precision = int(sys.argv[4]) if len(sys.argv) >= 5 else 5
    if not inp.exists():
        print("Input file not found:", inp)
        sys.exit(1)
    find_and_save(inp, out_code, out_coord, output_precision=output_precision)
