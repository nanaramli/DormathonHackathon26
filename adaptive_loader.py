"""
adaptive_loader.py - Load user-provided CSV/Excel files with adaptive column mapping.

This module is the core of Phase 2.  It:
    1. Inspects user-provided files (via file_inspector)
    2. Maps detected columns to RichBuddy's expected fields (via column_mapper)
    3. Auto-detects whether a file is invoice-like or transaction-like
    4. Loads and standardizes the data into the format Phase 1 modules expect
    5. Infers missing fields where possible (e.g., transaction type from sign)
    6. Validates and reports adaptation decisions transparently

The output is a standardized dataset dict compatible with the Phase 1
orchestrator and analysis modules.
"""

import csv
import os
import re
from datetime import datetime
from typing import Any

from file_inspector import inspect_file, FileInspectionError
from column_mapper import (
    map_invoice_columns,
    map_transaction_columns,
    INVOICE_FIELDS,
    TRANSACTION_FIELDS,
    get_required_invoice_fields,
    get_required_transaction_fields,
    _normalize,
    _is_income_expense_keyword,
)


class AdaptiveLoadError(Exception):
    """Raised when user-provided data cannot be loaded or is insufficient."""


def load_user_file(path: str) -> dict[str, Any]:
    """Load a single user-provided file and return an inspection + mapping report.

    Returns:
        {
            "inspection": dict,       # from file_inspector
            "best_match": str,        # "invoices" | "transactions"
            "invoice_mapping": dict,  # column mapping for invoice fields
            "transaction_mapping": dict,  # column mapping for transaction fields
            "mapping_used": dict,     # the mapping that was selected
            "adaptation_notes": [list of transparency notes],
        }
    """
    inspection = inspect_file(path)
    inv_mapping = map_invoice_columns(inspection)
    tx_mapping = map_transaction_columns(inspection)

    # Score both mappings to auto-detect file type
    inv_score = _score_mapping(inv_mapping, list(INVOICE_FIELDS.keys()))
    tx_score = _score_mapping(tx_mapping, list(TRANSACTION_FIELDS.keys()))

    notes: list[str] = []

    if inv_score >= tx_score:
        best_match = "invoices"
        mapping_used = inv_mapping
        notes.append(f"File detected as invoice-like (match score {inv_score} vs {tx_score} for transactions).")
    else:
        best_match = "transactions"
        mapping_used = tx_mapping
        notes.append(f"File detected as transaction-like (match score {tx_score} vs {inv_score} for invoices).")

    # Add mapping notes
    notes.extend(mapping_used.get("mapping_notes", []))

    # Report missing critical fields
    if best_match == "invoices":
        required = get_required_invoice_fields()
        missing_required = [f for f in required if mapping_used["mapping"].get(f) is None]
        if missing_required:
            notes.append(
                f"WARNING: Required invoice field(s) missing: {', '.join(missing_required)}. "
                f"Invoice analysis may be limited."
            )
    else:
        required = get_required_transaction_fields()
        missing_required = [f for f in required if mapping_used["mapping"].get(f) is None]
        if missing_required:
            notes.append(
                f"WARNING: Required transaction field(s) missing: {', '.join(missing_required)}. "
                f"Transaction analysis may be limited."
            )

    # Report unmapped columns
    if mapping_used["unmapped_columns"]:
        notes.append(
            f"Unmapped columns (not used in analysis): {', '.join(mapping_used['unmapped_columns'])}."
        )

    return {
        "inspection": inspection,
        "best_match": best_match,
        "invoice_mapping": inv_mapping,
        "transaction_mapping": tx_mapping,
        "mapping_used": mapping_used,
        "adaptation_notes": notes,
    }


def load_user_dataset(
    file_paths: list[str],
) -> dict[str, Any]:
    """Load one or more user-provided files into a standardized dataset.

    Accepts:
        - One file (auto-detected as invoice-like or transaction-like)
        - Two files (one invoices, one transactions -- auto-sorted)

    Returns a dataset dict compatible with Phase 1 orchestrator:
        {
            "invoices": [list of standardized invoice dicts],
            "transactions": [list of standardized transaction dicts],
            "data_dir": str (or "user_provided"),
            "adaptation_report": dict (full transparency about what was mapped),
        }
    """
    if not file_paths:
        raise AdaptiveLoadError("No files provided.")

    all_notes: list[str] = []
    invoices: list[dict[str, Any]] = []
    transactions: list[dict[str, Any]] = []

    # Load and classify each file
    file_reports: list[dict[str, Any]] = []
    for path in file_paths:
        try:
            report = load_user_file(path)
            file_reports.append(report)
            all_notes.extend(report["adaptation_notes"])

            # Load the actual data using the mapped columns
            inspection = report["inspection"]
            mapping = report["mapping_used"]["mapping"]

            if report["best_match"] == "invoices":
                inv_data = _load_and_standardize_invoices(inspection, mapping, all_notes)
                invoices.extend(inv_data)
            else:
                tx_data = _load_and_standardize_transactions(inspection, mapping, all_notes)
                # SMART: Detect expense entries in unmapped columns
                expense_txs = _detect_unmapped_expenses(inspection, mapping, all_notes)
                if expense_txs:
                    tx_data.extend(expense_txs)
                    all_notes.append(
                        f"SMART: {len(expense_txs)} expense transaction(s) "
                        f"detected from unmapped columns and added to dataset."
                    )
                transactions.extend(tx_data)
        except FileInspectionError as e:
            raise AdaptiveLoadError(f"Cannot inspect file '{path}': {e}")

    # If only one file was provided and it was detected as one type,
    # check if it also contains the other type's data
    if len(file_paths) == 1:
        if invoices and not transactions:
            all_notes.append(
                "Only invoice data was detected. Transaction-level analysis "
                "(income/expense breakdown) will be limited. For full analysis, "
                "provide a transactions file as well."
            )
        elif transactions and not invoices:
            all_notes.append(
                "Only transaction data was detected. Invoice-level analysis "
                "(outstanding balances, collection rate) will be limited. "
                "For full analysis, provide an invoices file as well."
            )

    if not invoices and not transactions:
        raise AdaptiveLoadError(
            "No usable data was found in the provided file(s). "
            "Ensure your file contains columns like amount, date, category, "
            "or invoice amount, status, customer."
        )

    return {
        "invoices": invoices,
        "transactions": transactions,
        "data_dir": "user_provided",
        "adaptation_report": {
            "files": file_reports,
            "all_notes": all_notes,
        },
    }


# ---------------------------------------------------------------------------
# Internal: load and standardize data using mapped columns
# ---------------------------------------------------------------------------
def _load_and_standardize_invoices(
    inspection: dict[str, Any],
    mapping: dict[str, str | None],
    notes: list[str],
) -> list[dict[str, Any]]:
    """Load invoice data from an inspection result using the column mapping."""
    # Read raw data from the file
    raw_rows = _read_raw_data(inspection)

    if not raw_rows:
        return []

    # Build column name -> index map
    col_indices = {col["name"]: col["index"] for col in inspection["columns"]}

    standardized: list[dict[str, Any]] = []
    for i, row in enumerate(raw_rows, start=2):  # row 1 is header
        try:
            inv = _standardize_invoice_row(row, col_indices, mapping, i, notes)
            if inv:
                standardized.append(inv)
        except ValueError as e:
            notes.append(f"Row {i}: skipped -- {e}")

    return standardized


def _standardize_invoice_row(
    row: list[str],
    col_indices: dict[str, int],
    mapping: dict[str, str | None],
    row_num: int,
    notes: list[str],
) -> dict[str, Any] | None:
    """Convert a raw row into a standardized invoice dict."""
    def get_val(field: str) -> str:
        col_name = mapping.get(field)
        if col_name is None or col_name not in col_indices:
            return ""
        idx = col_indices[col_name]
        if idx >= len(row):
            return ""
        return str(row[idx]).strip() if row[idx] is not None else ""

    # Amount is required
    amount_str = get_val("invoice_amount")
    if not amount_str:
        return None  # skip empty rows

    amount = _parse_amount(amount_str, "invoice_amount", row_num)

    # Paid amount (optional, default 0)
    paid_str = get_val("amount_paid")
    if paid_str:
        amount_paid = _parse_amount(paid_str, "amount_paid", row_num)
    else:
        amount_paid = 0.0
        # If status is "paid", assume fully paid
        status = get_val("status")
        normalized_status = _normalize_invoice_status(status)
        if normalized_status == "paid":
            amount_paid = amount

    # Balance due (optional, compute if missing)
    balance_str = get_val("balance_due")
    if balance_str:
        balance_due = _parse_amount(balance_str, "balance_due", row_num)
    else:
        balance_due = amount - amount_paid

    # Status (optional, infer if missing)
    status = _normalize_invoice_status(get_val("status"))
    if not status:
        status = _infer_invoice_status(amount, amount_paid, balance_due)

    # Dates (optional, validate if present)
    issue_date = _validate_date(get_val("issue_date"), "issue_date", row_num) or ""
    due_date = _validate_date(get_val("due_date"), "due_date", row_num) or ""

    return {
        "invoice_id": get_val("invoice_id") or f"ROW{row_num}",
        "customer_name": get_val("customer_name") or "Unknown",
        "issue_date": issue_date,
        "due_date": due_date,
        "invoice_amount_rm": round(amount, 2),
        "amount_paid_rm": round(amount_paid, 2),
        "balance_due_rm": round(balance_due, 2),
        "status": status,
        # Pass through optional Phase 2 fields if detected
        "region": get_val("region") or "",
        "product": get_val("product") or "",
    }


def _load_and_standardize_transactions(
    inspection: dict[str, Any],
    mapping: dict[str, str | None],
    notes: list[str],
) -> list[dict[str, Any]]:
    """Load transaction data from an inspection result using the column mapping."""
    raw_rows = _read_raw_data(inspection)

    if not raw_rows:
        return []

    col_indices = {col["name"]: col["index"] for col in inspection["columns"]}

    # Check if type column exists; if not, we'll infer from amount sign
    has_type_column = mapping.get("type") is not None
    if not has_type_column:
        notes.append(
            "No 'type' column detected. Transaction type (income/expense) "
            "will be inferred from amount sign (positive = income, "
            "negative = expense)."
        )

    standardized: list[dict[str, Any]] = []
    for i, row in enumerate(raw_rows, start=2):
        try:
            tx = _standardize_transaction_row(
                row, col_indices, mapping, i, notes, has_type_column
            )
            if tx:
                standardized.append(tx)
        except ValueError as e:
            notes.append(f"Row {i}: skipped -- {e}")

    return standardized


def _standardize_transaction_row(
    row: list[str],
    col_indices: dict[str, int],
    mapping: dict[str, str | None],
    row_num: int,
    notes: list[str],
    has_type_column: bool,
) -> dict[str, Any] | None:
    """Convert a raw row into a standardized transaction dict."""
    def get_val(field: str) -> str:
        col_name = mapping.get(field)
        if col_name is None or col_name not in col_indices:
            return ""
        idx = col_indices[col_name]
        if idx >= len(row):
            return ""
        return str(row[idx]).strip() if row[idx] is not None else ""

    # Amount is required
    amount_str = get_val("amount")
    if not amount_str:
        # SMART FALLBACK: try computing amount from quantity x unit_price
        qty_str = get_val("quantity")
        price_str = get_val("unit_price")
        if qty_str and price_str:
            try:
                qty = _parse_amount(qty_str, "quantity", row_num)
                price = _parse_amount(price_str, "unit_price", row_num)
                amount = qty * price
                notes.append(
                    f"Row {row_num}: amount computed from quantity ({qty}) "
                    f"x unit_price ({price}) = {amount:.2f}."
                )
            except ValueError:
                return None
        else:
            return None  # skip empty rows
    else:
        amount = _parse_amount(amount_str, "amount", row_num)

    # Type (infer if missing)
    if has_type_column:
        tx_type = get_val("type").lower().strip()
        if tx_type not in ("income", "expense"):
            # Try to normalize common alternatives (English + Malay)
            if tx_type in ("credit", "in", "receipt", "revenue", "sale", "sales",
                           "pendapatan", "pendaptan", "hasil", "jualan"):
                tx_type = "income"
            elif tx_type in ("debit", "out", "payment", "cost", "spend", "bill",
                             "perbelanjaan", "perbelanja", "belanja", "pengeluaran"):
                tx_type = "expense"
            else:
                # Infer from amount sign as fallback
                tx_type = "income" if amount >= 0 else "expense"
                notes.append(
                    f"Row {row_num}: unknown type '{get_val('type')}' "
                    f"inferred as '{tx_type}' from amount sign."
                )
    else:
        tx_type = "income" if amount >= 0 else "expense"
        amount = abs(amount)  # store as positive

    # Date (optional)
    date = _validate_date(get_val("date"), "date", row_num) or ""

    return {
        "transaction_id": get_val("transaction_id") or f"ROW{row_num}",
        "date": date,
        "type": tx_type,
        "category": get_val("category") or "Uncategorized",
        "description": get_val("description") or "",
        "amount_rm": round(abs(amount), 2),
        "invoice_id": get_val("invoice_id"),
        # Pass through optional Phase 2 fields if detected
        "region": get_val("region") or "",
        "product": get_val("product") or "",
        "quantity": get_val("quantity") or "",
        "unit_price": get_val("unit_price") or "",
    }


# ---------------------------------------------------------------------------
# Internal: utilities
# ---------------------------------------------------------------------------
def _read_raw_data(inspection: dict[str, Any]) -> list[list[str]]:
    """Read raw data rows from the inspected file."""
    path = inspection["path"]
    fmt = inspection["format"]

    if fmt == "csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            return [row for row in reader]
    elif fmt in ("xlsx", "xls"):
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb[inspection.get("sheet_used", wb.sheetnames[0])]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        # Skip header row
        data_rows = []
        for row in rows[1:]:
            data_rows.append([str(v) if v is not None else "" for v in row])
        return data_rows

    return []


def _parse_amount(value: str, field_name: str, row_num: int) -> float:
    """Parse a string into a float amount, handling common formats."""
    value = value.strip()
    # Remove currency symbols and thousands separators
    value = value.replace("RM", "").replace("rm", "")
    value = value.replace("MYR", "").replace("myr", "")
    value = value.replace("$", "")
    value = value.replace(",", "")
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        raise ValueError(
            f"cannot parse '{value}' as number for {field_name}"
        )


def _validate_date(value: str, field_name: str, row_num: int) -> str | None:
    """Validate a date string in common formats, return ISO format or None."""
    value = value.strip()
    if not value:
        return None

    # Try common date formats
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If no format matched, return the original string
    return value


def _infer_invoice_status(amount: float, paid: float, balance: float) -> str:
    """Infer invoice status from payment amounts."""
    if balance <= 0 or paid >= amount:
        return "paid"
    if paid > 0:
        return "partial"  # not in the standard set but informative
    return "pending"


def _normalize_invoice_status(raw: str) -> str:
    """Normalize invoice status values from English and Malay to standard terms.

    Standard statuses: paid, overdue, pending, partial, cancelled.
    """
    raw = raw.lower().strip()
    if not raw:
        return ""

    # Direct match (already standard)
    if raw in ("paid", "overdue", "pending", "partial", "cancelled", "cancel"):
        return raw

    # English alternatives
    english_map = {
        "settled": "paid", "complete": "paid", "completed": "paid",
        "done": "paid", "closed": "paid", "cleared": "paid",
        "late": "overdue", "unpaid": "overdue", "pastdue": "overdue",
        "open": "pending", "notpaid": "pending", "waiting": "pending",
        "halfpaid": "partial", "partiallypaid": "partial", "partialpayment": "partial",
    }

    # Malay alternatives
    malay_map = {
        "dibayar": "paid", "telahdibayar": "paid", "selesai": "paid",
        "tertunggak": "overdue", "lewat": "overdue", "tunggakan": "overdue",
        "belumbayar": "pending", "belum": "pending", "menunggu": "pending",
        "sebahagian": "partial", "sebahagiandibayar": "partial",
        "dibatalkan": "cancelled", "batal": "cancelled",
    }

    # Check normalized (no spaces) version
    norm = raw.replace(" ", "").replace(".", "").replace("-", "")

    if raw in english_map:
        return english_map[raw]
    if raw in malay_map:
        return malay_map[raw]
    if norm in english_map:
        return english_map[norm]
    if norm in malay_map:
        return malay_map[norm]

    # Fallback: return as-is (analysis may still work with unknown statuses)
    return raw


def _score_mapping(mapping: dict[str, Any], all_fields: list[str]) -> int:
    """Score a mapping by counting how many fields were successfully mapped."""
    score = 0
    for field in all_fields:
        if mapping["mapping"].get(field) is not None:
            score += 1
    return score


# ---------------------------------------------------------------------------
# SMART: Expense detection in unmapped columns
# ---------------------------------------------------------------------------
_EXPENSE_HEADER_KEYWORDS: set[str] = {
    # English
    "modal", "expense", "cost", "spent", "expenditure", "outlay", "outgoing",
    "overhead", "capital", "investment", "spending",
    # Malay
    "kos", "belanja", "perbelanjaan", "pengeluaran", "belian", "modalawal",
    "perbelanjaantambahan",
}


def _try_extract_number(text: str) -> float | None:
    """Extract the first numeric value from a text string.

    Handles formats like: "77", "RM 77", "77.50", "RM77.00",
    "77 (20 packs)", "modal: 77", "rm 77.00 (20 packs)", etc.
    """
    if not text:
        return None
    cleaned = text
    # Remove currency symbols and common prefixes
    cleaned = re.sub(r"[Rr][Mm]\s*", "", cleaned)
    cleaned = re.sub(r"[Mm][Yy][Rr]\s*", "", cleaned)
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace(",", "")
    # Find the first number (integer or decimal)
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _detect_unmapped_expenses(
    inspection: dict[str, Any],
    mapping: dict[str, str | None],
    notes: list[str],
) -> list[dict[str, Any]]:
    """Detect expense entries in unmapped columns and create expense transactions.

    Scans columns that weren't mapped to any expected field, looking for
    expense-related headers (e.g., "Modal" in Malay, "Cost" in English) or
    cell values containing expense keywords. When found, extracts numeric
    values and creates synthetic expense transactions.

    Handles two student-style layouts:
    1. Same-cell: cell contains both label and value (e.g., "Modal: RM 77")
    2. Adjacent columns: label in one column, value in the next (e.g.,
       col[6]="Modal", col[7]="Rm 77" — common in informal student Excel)
    """
    mapped_col_names = {v for v in mapping.values() if v is not None}
    expense_transactions: list[dict[str, Any]] = []
    raw_rows = _read_raw_data(inspection)
    # Track cells already used as value sources (prevents duplicates)
    claimed_value_cells: set[tuple[int, int]] = set()

    for col in inspection["columns"]:
        col_name = col["name"]
        if col_name in mapped_col_names:
            continue  # skip mapped columns

        col_name_lower = col_name.lower().strip() if col_name else ""
        header_is_expense = any(
            kw in col_name_lower for kw in _EXPENSE_HEADER_KEYWORDS
        )
        display_name = col_name if col_name else f"Column {col['index']}"

        for row_idx, row in enumerate(raw_rows, start=2):
            if col["index"] >= len(row):
                continue
            cell = str(row[col["index"]]).strip() if row[col["index"]] else ""
            if not cell:
                continue

            cell_lower = cell.lower().strip()
            cell_has_expense = any(
                kw in cell_lower for kw in _EXPENSE_HEADER_KEYWORDS
            )

            # Skip if neither header nor cell has expense keyword
            if not (header_is_expense or cell_has_expense):
                continue

            # Skip if this cell was already claimed as a value source
            if (row_idx, col["index"]) in claimed_value_cells:
                continue

            # Try to extract number from this cell (same-cell layout)
            amount = _try_extract_number(cell)
            value_source = cell
            source_desc = display_name

            # If no number in this cell, check adjacent column to the right
            # (student-style label-value layout)
            if not amount:
                next_idx = col["index"] + 1
                if next_idx < len(row):
                    next_cell = (
                        str(row[next_idx]).strip()
                        if row[next_idx] else ""
                    )
                    if next_cell:
                        amount = _try_extract_number(next_cell)
                        if amount and amount > 0:
                            value_source = next_cell
                            next_col = next(
                                (c for c in inspection["columns"]
                                 if c["index"] == next_idx),
                                None,
                            )
                            next_display = (
                                next_col["name"]
                                if next_col and next_col["name"]
                                else f"Column {next_idx}"
                            )
                            source_desc = f"{display_name} -> {next_display}"
                            claimed_value_cells.add((row_idx, next_idx))

            if amount and amount > 0:
                expense_transactions.append({
                    "transaction_id": f"EXPENSE_C{col['index']}_R{row_idx}",
                    "date": "",
                    "type": "expense",
                    "category": "Capital/Initial Cost",
                    "description": f"Expense: {cell} = {value_source}",
                    "amount_rm": round(amount, 2),
                    "invoice_id": "",
                    "region": "",
                    "product": "",
                    "quantity": "",
                    "unit_price": "",
                })
                notes.append(
                    f"SMART: Detected expense in '{source_desc}': "
                    f"RM {amount:.2f} (from '{cell}' = '{value_source}')."
                )

    return expense_transactions


def format_adaptation_report(dataset: dict[str, Any]) -> str:
    """Return a human-readable summary of the adaptation process."""
    report = dataset.get("adaptation_report", {})
    notes = report.get("all_notes", [])
    files = report.get("files", [])

    lines = []
    lines.append("=" * 60)
    lines.append("  Data Adaptation Report")
    lines.append("=" * 60)
    lines.append("")

    for fr in files:
        insp = fr["inspection"]
        lines.append(f"File: {insp['filename']}")
        lines.append(f"  Format: {insp['format']}, Rows: {insp['row_count']}")
        lines.append(f"  Detected as: {fr['best_match']}")
        lines.append(f"  Columns found: {len(insp['columns'])}")

        mapping = fr["mapping_used"]["mapping"]
        lines.append("  Column Mapping:")
        for field, col in mapping.items():
            status = col if col else "(not found)"
            lines.append(f"    {field:20s} -> {status}")

        if fr["mapping_used"]["unmapped_columns"]:
            lines.append(f"  Unmapped: {', '.join(fr['mapping_used']['unmapped_columns'])}")
        lines.append("")

    if notes:
        lines.append("Adaptation Notes:")
        for note in notes:
            lines.append(f"  - {note}")
        lines.append("")

    lines.append(f"Loaded: {len(dataset.get('invoices', []))} invoices, "
                 f"{len(dataset.get('transactions', []))} transactions")
    lines.append("=" * 60)

    return "\n".join(lines)
