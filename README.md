## Duplicate Coordinate Finder and Adjuster

### Description for find_duplicates.py

This program finds duplicate rows by Code and by exact coordinate pairs (Latitude + Longitude) in an Excel (.xlsx) file.
    Writes two CSV outputs:
        duplicates_by_code.csv — all rows where the Code value appears more than once.
        duplicates_by_coordinate.csv — all rows where both Latitude and Longitude match exactly; Latitude/Longitude in the CSV are rounded/formatted to 5 decimal places.

Requirements

Python 3.8+
    pandas, openpyxl
        Install: pip install pandas openpyxl

Usage

    Basic: python find_duplicates_coordinates.py input.xlsx
    Specify output filenames and precision: python find_duplicates_coordinates.py input.xlsx duplicates_by_code.csv duplicates_by_coordinate.csv 5


### Description for Full-Stack.py

This program processes CSV or Excel files to find and resolve duplicate coordinate rows based on latitude and longitude. It detects duplicates by exact coordinate matches (rounded to 8 decimal places for precision), adjusts duplicate positions by random geodesic offsets (1-100 meters) to avoid collisions, and iterates until no duplicates remain or a maximum iteration limit is reached. Outputs include the initial duplicates and the final merged file with unique coordinates.

Key features:
- Automatic detection of latitude/longitude columns (by name or numeric type).
- Accurate meter-based offsets using `pyproj` for geodesic calculations.
- Collision avoidance to prevent new duplicates.
- Interactive file browser or command-line file specification.
- All coordinates rounded to 4 decimal places in outputs.

### Requirements

- Python 3.8+
- pandas, openpyxl, pyproj, numpy
- Install: `pip install pandas openpyxl pyproj numpy`

### Usage

- **Interactive mode**: Run `python Full-Stack.py` and use the file browser to select a file. Columns are auto-detected or prompted for selection.
- **Command-line mode**: 
  - `python Full-Stack.py path/to/file.csv` (auto-detect or prompt for columns).
  - `python Full-Stack.py path/to/file.xlsx lat_column lon_column` (specify column names explicitly).

The script supports CSV and Excel files (.xlsx, .xls, .xlsm).

### Behavior

- **Column Detection**: Searches for columns containing "lat" and "lon" (case-insensitive). Falls back to the first two numeric columns if not found.
- **Duplicate Detection**: Identifies groups of rows with identical lat/lon (after rounding to 8 decimals).
- **Adjustment Process**:
  - Keeps the first row in each duplicate group unchanged.
  - Offsets subsequent rows by 1-100 meters in random directions using geodesic calculations.
  - Retries up to 100 times per row to find a collision-free position (checked at 4-decimal precision).
  - If no position is found, warns and keeps the original (rounded).
  - Repeats the process up to 20 iterations until no duplicates remain.
- **Rounding**: All coordinates in output files are rounded to 4 decimal places.
- **File Handling**: Preserves the input file format for the merged output.

### Output Files

- `<input_name>_initial_duplicates.csv`: All duplicate rows from the original file, with coordinates rounded to 4 decimals.
- `<input_name>_merged.csv` (or .xlsx): The final file with adjusted coordinates, all unique and rounded to 4 decimals.

### Notes

- The script uses the WGS84 ellipsoid for accurate distance calculations.
- Dense datasets may result in warnings if collision-free positions are hard to find; increase offset range or retries if needed.
- Original file is not modified; backups are not created automatically.
- For large files, processing may take time due to iterative adjustments.

### License

Use freely; no warranty.

