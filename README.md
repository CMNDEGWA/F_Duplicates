## Project Explained in Detail

### Description

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

Behavior

    Column detection is case-insensitive for headers: Code, Latitude, Longitude.
    Code duplicates: trims whitespace and treats values as strings.
    Coordinate duplicates: detected by exact match of the original Latitude and Longitude cell values (no rounding used for matching).
    Output formatting: Latitude and Longitude in the coordinate CSV are rounded to 5 decimal places and saved as fixed-width strings (trailing zeros preserved). Non-numeric coordinate cells are left as their original strings.

Output files

    duplicates_by_code.csv
    duplicates_by_coordinate.csv

Notes

    The script reads the first sheet of the Excel file.
    If your columns have different header names, pass the excel and optional filenames; otherwise rename headers to Code, Latitude, Longitude.

License

    Use freely; no warranty.
