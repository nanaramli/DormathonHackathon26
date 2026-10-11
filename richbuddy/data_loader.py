"""
data_loader.py - Load and validate CSV business data for RichBuddy.

This module is responsible for reading the sample business dataset (invoices.csv
and transactions.csv), validating column structure, parsing data types, and
returning clean, structured data for downstream analysis modules.

All loading uses Python's standard-library ``csv`` module -- no third-party
dependencies are required.
"""

import csv
import os
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Expected column schemas -- used to validate that loaded files have the
# required structure before analysis proceeds.
# ---------------------------------------------------------------------------
INVOICE_COLUMNS = {
    "invoice_id", "customer_name", "issue_date", "due_date",
    "invoice_amount_rm", "amount_paid_rm", "balance_due_rm", "status",
}

TRANSACTION_COLUMNS = {
    "transaction_id", "date", "type", "category",
    "description", "amount_rm", "invoice_id",
}

VALID_INVOICE_STATUSES = {"paid", "overdue", "pending", "cancelled"}
VALID_TRANSACTION_TYPES = {"income", "expense"}


class DataLoadError(Exception):
    """Raised when a data file cannot be loaded or fails validation."""


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def _parse_float(value: str, field_name: str, row_num: int) -> float:
    """Parse a string into a float, raising DataLoadError on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        raise DataLoadError(
            f"Row {row_num}: cannot parse '{value}' as float for field '{field_name}'"
        )


def _parse_date(value: str, field_name: str, row_num: int) -> str:
    """Parse a date string (YYYY-MM-DD), returning the ISO string.

    We store dates as strings to keep things simple, but validate that the
    format is correct so downstream date arithmetic won't break.
    """
    value = value.strip()
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        raise DataLoadError(
            f"Row {row_num}: invalid date '{value}' for field '{field_name}' "
            f"(expected YYYY-MM-DD)"
        )


def _read_csv(path: str) -> list[dict[str, str]]:
    """Read a CSV file and return rows as list of dicts (string values)."""
    if not os.path.isfile(path):
        raise DataLoadError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise DataLoadError(f"File is empty or has no header: {path}")
        return list(reader)


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------
def load_invoices(path: str) -> list[dict[str, Any]]:
    """Load and validate invoices.csv.

    Returns a list of dicts with parsed fields:
        invoice_id (str), customer_name (str), issue_date (str),
        due_date (str), invoice_amount_rm (float), amount_paid_rm (float),
        balance_due_rm (float), status (str)
    """
    raw_rows = _read_csv(path)
    if not raw_rows:
        raise DataLoadError(f"No data rows in invoices file: {path}")

    # Validate columns
    headers = set(raw_rows[0].keys())
    missing = INVOICE_COLUMNS - headers
    if missing:
        raise DataLoadError(
            f"Invoices file missing required columns: {sorted(missing)}"
        )

    invoices: list[dict[str, Any]] = []
    for i, row in enumerate(raw_rows, start=2):  # row 1 is header
        invoice_id = row["invoice_id"].strip()
        if not invoice_id:
            raise DataLoadError(f"Row {i}: invoice_id is empty")

        status = row["status"].strip().lower()
        if status not in VALID_INVOICE_STATUSES:
            raise DataLoadError(
                f"Row {i}: unknown invoice status '{row['status']}' "
                f"(expected one of {sorted(VALID_INVOICE_STATUSES)})"
            )

        invoices.append({
            "invoice_id": invoice_id,
            "customer_name": row["customer_name"].strip(),
            "issue_date": _parse_date(row["issue_date"], "issue_date", i),
            "due_date": _parse_date(row["due_date"], "due_date", i),
            "invoice_amount_rm": _parse_float(row["invoice_amount_rm"], "invoice_amount_rm", i),
            "amount_paid_rm": _parse_float(row["amount_paid_rm"], "amount_paid_rm", i),
            "balance_due_rm": _parse_float(row["balance_due_rm"], "balance_due_rm", i),
            "status": status,
        })

    return invoices


def load_transactions(path: str) -> list[dict[str, Any]]:
    """Load and validate transactions.csv.

    Returns a list of dicts with parsed fields:
        transaction_id (str), date (str), type (str),
        category (str), description (str), amount_rm (float),
        invoice_id (str or "")
    """
    raw_rows = _read_csv(path)
    if not raw_rows:
        raise DataLoadError(f"No data rows in transactions file: {path}")

    headers = set(raw_rows[0].keys())
    missing = TRANSACTION_COLUMNS - headers
    if missing:
        raise DataLoadError(
            f"Transactions file missing required columns: {sorted(missing)}"
        )

    transactions: list[dict[str, Any]] = []
    for i, row in enumerate(raw_rows, start=2):
        tx_id = row["transaction_id"].strip()
        if not tx_id:
            raise DataLoadError(f"Row {i}: transaction_id is empty")

        tx_type = row["type"].strip().lower()
        if tx_type not in VALID_TRANSACTION_TYPES:
            raise DataLoadError(
                f"Row {i}: unknown transaction type '{row['type']}' "
                f"(expected one of {sorted(VALID_TRANSACTION_TYPES)})"
            )

        category = row["category"].strip()
        if not category:
            raise DataLoadError(f"Row {i}: category is empty")

        transactions.append({
            "transaction_id": tx_id,
            "date": _parse_date(row["date"], "date", i),
            "type": tx_type,
            "category": category,
            "description": row["description"].strip(),
            "amount_rm": _parse_float(row["amount_rm"], "amount_rm", i),
            "invoice_id": row["invoice_id"].strip(),  # may be empty
        })

    return transactions


def load_dataset(data_dir: str) -> dict[str, Any]:
    """Load the complete business dataset from a directory.

    Expects ``invoices.csv`` and ``transactions.csv`` in *data_dir*.
    Returns a dict: {"invoices": [...], "transactions": [...], "data_dir": str}
    """
    invoices_path = os.path.join(data_dir, "invoices.csv")
    transactions_path = os.path.join(data_dir, "transactions.csv")

    invoices = load_invoices(invoices_path)
    transactions = load_transactions(transactions_path)

    # Cross-validate: every transaction with an invoice_id should reference
    # a real invoice.  This catches data-integrity issues early.
    invoice_ids = {inv["invoice_id"] for inv in invoices}
    for tx in transactions:
        ref = tx["invoice_id"]
        if ref and ref not in invoice_ids:
            raise DataLoadError(
                f"Transaction {tx['transaction_id']} references unknown "
                f"invoice '{ref}'"
            )

    return {
        "invoices": invoices,
        "transactions": transactions,
        "data_dir": data_dir,
    }


def describe_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    """Return a metadata summary describing what the loaded dataset contains.

    Used by the orchestrator to determine which analyses are possible and
    to be transparent about data limitations (e.g., no region column).
    """
    invoices = dataset.get("invoices", [])
    transactions = dataset.get("transactions", [])

    invoice_cols = set(invoices[0].keys()) if invoices else set()
    tx_cols = set(transactions[0].keys()) if transactions else set()

    income_txs = [t for t in transactions if t.get("type") == "income"]
    expense_txs = [t for t in transactions if t.get("type") == "expense"]

    income_categories = sorted({t["category"] for t in income_txs}) if income_txs else []
    expense_categories = sorted({t["category"] for t in expense_txs}) if expense_txs else []
    invoice_statuses = sorted({inv["status"] for inv in invoices}) if invoices else []

    all_cols = invoice_cols | tx_cols

    return {
        "invoice_count": len(invoices),
        "transaction_count": len(transactions),
        "income_transaction_count": len(income_txs),
        "expense_transaction_count": len(expense_txs),
        "income_categories": income_categories,
        "expense_categories": expense_categories,
        "invoice_statuses": invoice_statuses,
        "invoice_columns": sorted(invoice_cols),
        "transaction_columns": sorted(tx_cols),
        "has_region_data": any("region" in c for c in [invoice_cols, tx_cols]),
        "has_returns_data": any(
            kw in all_cols for kw in ["returns", "return", "refund", "returned"]
        ),
        "has_product_data": any(
            kw in all_cols for kw in ["product", "product_name", "item", "item_name", "sku"]
        ),
        "data_source": dataset.get("data_dir", "unknown"),
        "is_user_provided": dataset.get("data_dir") == "user_provided",
    }
