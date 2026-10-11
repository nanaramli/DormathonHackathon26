"""
column_mapper.py - Map detected file columns to RichBuddy's expected fields.

This module implements the "identify available columns" requirement of Phase 2.
It takes an inspection result (from file_inspector) and maps each detected column
to one of RichBuddy's expected fields using alias matching and normalization.

The mapper is designed to handle files where column names differ from the
sample dataset (e.g., "Amount" instead of "amount_rm", "Customer" instead of
"customer_name", "Type" instead of "type").

If a required field cannot be found, the mapper reports it as missing so the
adaptive loader can decide whether analysis is still possible.
"""

import re
from typing import Any


# ---------------------------------------------------------------------------
# Expected fields and their aliases
# ---------------------------------------------------------------------------
# Each field has a list of alias patterns.  The mapper normalizes column names
# (lowercase, remove punctuation/spaces) and checks if any alias matches.
# ---------------------------------------------------------------------------

INVOICE_FIELDS: dict[str, list[str]] = {
    "invoice_id": [
        "invoiceid", "invoiceno", "invoicenumber", "invno", "invnumber",
        "invoiceref", "ref", "reference", "invoice", "invoicecode",
    ],
    "customer_name": [
        "customername", "customer", "client", "clientname", "buyer",
        "buyername", "billto", "recipient", "party", "name",
    ],
    "issue_date": [
        "issuedate", "date", "invoicedate", "createddate", "dateissued",
        "datecreated", "raiseddate", "transactiondate",
    ],
    "due_date": [
        "duedate", "duedate", "paymentdate", "paymentdue", "deadline",
        "expecteddate", "duedate",
    ],
    "invoice_amount": [
        "invoiceamountrm", "amount", "total", "invoicetotal", "invoiceamount",
        "value", "subtotal", "grandtotal", "amountdue", "billamount",
        "charge", "fee", "price", "invoicevalue",
    ],
    "amount_paid": [
        "amountpaidrm", "paid", "amountpaid", "paymentreceived", "paidamount",
        "received", "payment", "amountpaidrm",
    ],
    "balance_due": [
        "balanceduerm", "balance", "balancedue", "outstanding", "unpaid",
        "remaining", "remainingbalance", "amountdue", "amountowing",
        "bal",
    ],
    "status": [
        "status", "state", "paymentstatus", "invoicestatus", "paidstatus",
    ],
    "region": [
        "region", "location", "area", "zone", "territory", "branch",
        "city", "state", "country",
    ],
    "product": [
        "product", "productname", "item", "itemname", "service",
        "servicename", "sku",
    ],
}

TRANSACTION_FIELDS: dict[str, list[str]] = {
    "transaction_id": [
        "transactionid", "txid", "txno", "id", "ref", "reference",
        "transactionno", "transactionnumber", "entryid",
    ],
    "date": [
        "date", "transactiondate", "txdate", "entrydate", "postingdate",
        "recorddate",
    ],
    "type": [
        "type", "transactiontype", "txtype", "flow", "direction",
        "entrytype", "categorytype",
    ],
    "category": [
        "category", "product", "service", "item", "itemname",
        "productname", "classification", "group", "tag",
    ],
    "description": [
        "description", "details", "memo", "note", "notes", "remarks",
        "comment", "narration", "particulars",
    ],
    "amount": [
        "amountrm", "amount", "value", "price", "total", "cost",
        "sum", "figure", "debit", "credit",
    ],
    "invoice_id": [
        "invoiceid", "invoiceref", "refinvoice", "linkedinvoice",
        "invoice", "invno", "invoicenumber", "link", "linkedinv",
    ],
    "region": [
        "region", "location", "area", "zone", "territory", "branch",
        "city", "state", "country",
    ],
}


def _normalize(name: str) -> str:
    """Normalize a column name: lowercase, remove spaces, underscores, hyphens."""
    name = name.lower().strip()
    # Remove common separators and punctuation
    name = re.sub(r"[\s_\-./()]+", "", name)
    return name


def map_columns(
    inspection: dict[str, Any],
    field_aliases: dict[str, list[str]],
) -> dict[str, Any]:
    """Map detected columns to expected fields.

    Args:
        inspection: Result from file_inspector.inspect_file().
        field_aliases: Either INVOICE_FIELDS or TRANSACTION_FIELDS.

    Returns:
        {
            "mapping": {field_name: detected_column_name | None},
            "unmapped_columns": [list of detected columns not mapped],
            "missing_fields": [list of expected fields not found],
            "mapping_notes": [list of transparency notes],
        }
    """
    detected_cols = {col["name"]: _normalize(col["name"]) for col in inspection["columns"]}
    mapping: dict[str, str | None] = {}
    claimed_cols: set[str] = set()  # columns already matched (won't re-match)
    notes: list[str] = []

    # Build list of (field, aliases) in order
    field_list = list(field_aliases.items())

    # ---- Pass 1: Exact matches only (highest priority) ----
    for field, aliases in field_list:
        if field in mapping:
            continue
        for col_name, norm in detected_cols.items():
            if col_name in claimed_cols:
                continue
            if norm in aliases or norm == field.replace("_", ""):
                mapping[field] = col_name
                claimed_cols.add(col_name)
                break

    # ---- Pass 2: Alias is a substring of the column name ----
    # (e.g., alias "date" in column "transactiondate") — but NOT the reverse,
    # to prevent "amount" matching "amountpaid".
    for field, aliases in field_list:
        if field in mapping:
            continue
        for col_name, norm in detected_cols.items():
            if col_name in claimed_cols:
                continue
            for alias in aliases:
                # alias must be a meaningful substring (len >= 4) of column name
                if len(alias) >= 4 and alias in norm:
                    mapping[field] = col_name
                    claimed_cols.add(col_name)
                    notes.append(
                        f"Field '{field}' mapped to column '{col_name}' via "
                        f"substring match (alias '{alias}' in '{norm}')."
                    )
                    break
            if field in mapping:
                break

    # ---- Pass 3: Field name is a substring of column name ----
    # (e.g., field "category" in column "transactioncategory")
    for field, aliases in field_list:
        if field in mapping:
            continue
        field_norm = field.replace("_", "")
        for col_name, norm in detected_cols.items():
            if col_name in claimed_cols:
                continue
            if len(field_norm) >= 4 and field_norm in norm:
                mapping[field] = col_name
                claimed_cols.add(col_name)
                notes.append(
                    f"Field '{field}' mapped to column '{col_name}' via "
                    f"fuzzy match ('{field_norm}' in '{norm}')."
                )
                break

    # ---- Fill in None for unmatched fields ----
    for field in field_aliases:
        if field not in mapping:
            mapping[field] = None

    unmapped = [col["name"] for col in inspection["columns"] if col["name"] not in claimed_cols]
    missing = [f for f, c in mapping.items() if c is None]

    return {
        "mapping": mapping,
        "unmapped_columns": unmapped,
        "missing_fields": missing,
        "mapping_notes": notes,
    }


def map_invoice_columns(inspection: dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper for mapping invoice-like files."""
    return map_columns(inspection, INVOICE_FIELDS)


def map_transaction_columns(inspection: dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper for mapping transaction-like files."""
    return map_columns(inspection, TRANSACTION_FIELDS)


def get_required_invoice_fields() -> list[str]:
    """Fields required for meaningful invoice analysis."""
    return ["invoice_amount"]


def get_required_transaction_fields() -> list[str]:
    """Fields required for meaningful transaction analysis."""
    return ["amount"]


def get_recommended_invoice_fields() -> list[str]:
    """Fields that make invoice analysis more complete (but not strictly required)."""
    return ["invoice_id", "customer_name", "issue_date", "status", "amount_paid", "balance_due"]


def get_recommended_transaction_fields() -> list[str]:
    """Fields that make transaction analysis more complete (but not strictly required)."""
    return ["date", "type", "category", "description"]
