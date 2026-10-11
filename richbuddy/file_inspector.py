"""
file_inspector.py - Inspect any CSV or Excel file and report its structure.

This module is the entry point for Phase 2's "inspect the uploaded data"
requirement.  It reads any supported file, extracts column names, infers
data types, samples values, and returns a structured metadata report.

Supported formats:
    - CSV  (.csv)
    - Excel (.xlsx, .xls)  [requires openpyxl, available in the venv]
"""

import csv
import os
from typing import Any


class FileInspectionError(Exception):
    """Raised when a file cannot be inspected."""


def inspect_file(path: str) -> dict[str, Any]:
    """Inspect a CSV or Excel file and return its structural metadata.

    Returns:
        {
            "path": str,
            "filename": str,
            "format": "csv" | "xlsx" | "xls",
            "row_count": int,          # data rows (excluding header)
            "columns": [               # list of column descriptors
                {
                    "name": str,       # original column name
                    "index": int,      # 0-based position
                    "sample_values": [list of up to 3 non-empty values],
                    "inferred_type": "text" | "number" | "date" | "empty",
                },
                ...
            ],
            "sheet_names": [list],     # for Excel only
            "sheet_used": str,         # for Excel: which sheet was inspected
        }
    """
    if not os.path.isfile(path):
        raise FileInspectionError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _inspect_csv(path)
    elif ext in (".xlsx", ".xls"):
        return _inspect_excel(path)
    else:
        raise FileInspectionError(
            f"Unsupported file format '{ext}'. Supported: .csv, .xlsx, .xls"
        )


def _inspect_csv(path: str) -> dict[str, Any]:
    """Inspect a CSV file."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            raise FileInspectionError(f"File is empty: {path}")

        rows = list(reader)

    return _build_inspection_result(path, "csv", headers, rows, sheet_names=None)


def _inspect_excel(path: str) -> dict[str, Any]:
    """Inspect an Excel file (requires openpyxl)."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise FileInspectionError(
            "openpyxl is required to read Excel files but is not installed. "
            "Install it with: pip install openpyxl"
        )

    wb = load_workbook(path, read_only=True, data_only=True)
    sheet_names = wb.sheetnames

    if not sheet_names:
        raise FileInspectionError(f"Excel file has no sheets: {path}")

    # Use the first sheet by default
    ws = wb[sheet_names[0]]
    rows = list(ws.iter_rows(values_only=True))

    if not rows:
        raise FileInspectionError(f"Excel file first sheet is empty: {path}")

    # Convert all values to strings for consistency
    headers = [str(v) if v is not None else "" for v in rows[0]]
    data_rows = []
    for row in rows[1:]:
        data_rows.append([str(v) if v is not None else "" for v in row])

    wb.close()

    result = _build_inspection_result(
        path, "xlsx", headers, data_rows,
        sheet_names=sheet_names,
        sheet_used=sheet_names[0],
    )
    return result


def _build_inspection_result(
    path: str,
    fmt: str,
    headers: list[str],
    rows: list[list[str]],
    sheet_names: list[str] | None = None,
    sheet_used: str | None = None,
) -> dict[str, Any]:
    """Build the inspection result dict from raw headers and rows."""
    columns = []
    for idx, header in enumerate(headers):
        sample_values = []
        type_hints = []
        for row in rows[:50]:  # sample up to 50 rows
            if idx < len(row):
                val = str(row[idx]).strip() if row[idx] is not None else ""
                if val:
                    sample_values.append(val)
                    type_hints.append(_infer_value_type(val))
                if len(sample_values) >= 3:
                    break

        inferred_type = _infer_column_type(type_hints, sample_values)

        columns.append({
            "name": header.strip(),
            "index": idx,
            "sample_values": sample_values,
            "inferred_type": inferred_type,
        })

    result: dict[str, Any] = {
        "path": path,
        "filename": os.path.basename(path),
        "format": fmt,
        "row_count": len(rows),
        "columns": columns,
    }
    if sheet_names:
        result["sheet_names"] = sheet_names
        result["sheet_used"] = sheet_used or sheet_names[0]

    return result


def _infer_value_type(value: str) -> str:
    """Infer the type of a single string value."""
    value = value.strip()
    if not value:
        return "empty"

    # Try number
    try:
        float(value)
        return "number"
    except ValueError:
        pass

    # Try date (common formats)
    import re
    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}$",
        r"^\d{2}/\d{2}/\d{4}$",
        r"^\d{1,2}/\d{1,2}/\d{4}$",
        r"^\d{4}/\d{2}/\d{2}$",
        r"^\d{2}\.\d{2}\.\d{4}$",
    ]
    for pattern in date_patterns:
        if re.match(pattern, value):
            return "date"

    return "text"


def _infer_column_type(type_hints: list[str], samples: list[str]) -> str:
    """Infer the dominant type of a column from its value type hints."""
    if not samples:
        return "empty"

    type_counts: dict[str, int] = {}
    for t in type_hints:
        type_counts[t] = type_counts.get(t, 0) + 1

    # Pick the most common type
    dominant = max(type_counts, key=type_counts.get)

    # If text and number are close, lean toward text (safer)
    if dominant == "number" and type_counts.get("text", 0) > 0:
        if type_counts["text"] / len(type_hints) > 0.3:
            return "text"

    return dominant


def format_inspection_summary(inspection: dict[str, Any]) -> str:
    """Return a human-readable summary of the inspection result."""
    lines = []
    lines.append(f"File: {inspection['filename']}")
    lines.append(f"Format: {inspection['format']}")
    lines.append(f"Data rows: {inspection['row_count']}")
    if "sheet_used" in inspection:
        lines.append(f"Sheet: {inspection['sheet_used']} (available: {', '.join(inspection.get('sheet_names', []))})")
    lines.append(f"Columns ({len(inspection['columns'])}):")
    for col in inspection["columns"]:
        samples_str = ", ".join(col["sample_values"][:3]) if col["sample_values"] else "(empty)"
        lines.append(f"  [{col['index']}] {col['name']}  ({col['inferred_type']})  e.g.: {samples_str}")
    return "\n".join(lines)
