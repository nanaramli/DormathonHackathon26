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
        # Malay: nombor invois, no invois, rujukan invois
        "invois", "noinvois", "nomborinvois", "rujukaninvois",
    ],
    "customer_name": [
        "customername", "customer", "client", "clientname", "buyer",
        "buyername", "billto", "recipient", "party", "name",
        # Malay: nama pelanggan, pelanggan, nama klien
        "namapelanggan", "pelanggan", "namaklien", "pembeli",
    ],
    "issue_date": [
        "issuedate", "date", "invoicedate", "createddate", "dateissued",
        "datecreated", "raiseddate", "transactiondate",
        # Malay: tarikh terbit, tarikh invois, tarikh cipta
        "tarikh", "tarkihterbit", "tarkihinvois", "tarikhcipta", "tarikhdikeluarkan",
    ],
    "due_date": [
        "duedate", "duedate", "paymentdate", "paymentdue", "deadline",
        "expecteddate", "duedate",
        # Malay: tarikh akhir, tarikh perlu bayar, tarikh mati
        "tarikhakhir", "tarikhperlubayar", "tarikhmati", "tarikhtamat",
    ],
    "invoice_amount": [
        "invoiceamountrm", "amount", "total", "invoicetotal", "invoiceamount",
        "value", "subtotal", "grandtotal", "amountdue", "billamount",
        "sales", "totalsales", "charge", "fee", "invoicevalue",
        # Malay: jumlah, jumlah bayaran, nilai, jumlah keseluruhan, jualan
        "jumlah", "jumlahbayaran", "nilai", "jumlahkeseluruhan", "caj", "harga", "jualan",
    ],
    "amount_paid": [
        "amountpaidrm", "paid", "amountpaid", "paymentreceived", "paidamount",
        "received", "payment", "amountpaidrm",
        # Malay: bayaran diterima, jumlah dibayar, bayar
        "dibayar", "bayaranditerima", "jumlahdibayar", "terimabayaran",
    ],
    "balance_due": [
        "balanceduerm", "balance", "balancedue", "outstanding", "unpaid",
        "remaining", "remainingbalance", "amountdue", "amountowing",
        "bal",
        # Malay: baki, baki tertunggak, tertunggak
        "baki", "bakitertunggak", "tertunggak", "bakiuntaibayar",
    ],
    "status": [
        "status", "state", "paymentstatus", "invoicestatus", "paidstatus",
        # Malay: status bayaran, status invois
        "statusbayaran", "statusinvois",
    ],
    "region": [
        "region", "location", "area", "zone", "territory", "branch",
        "city", "state", "country",
        # Malay: kawasan, wilayah, cawangan, negeri, bandar
        "kawasan", "wilayah", "cawangan", "negeri", "bandar",
    ],
    "product": [
        "product", "productname", "item", "itemname", "service",
        "servicename", "sku",
        # Malay: produk, nama produk, barang, perkhidmatan
        "produk", "namaproduk", "barang", "perkhidmatan",
    ],
}

TRANSACTION_FIELDS: dict[str, list[str]] = {
    "transaction_id": [
        "transactionid", "txid", "txno", "id", "ref", "reference",
        "transactionno", "transactionnumber", "entryid",
        # Malay: nombor transaksi, rujukan transaksi
        "nombortransaksi", "rujukantransaksi", "notransaksi",
    ],
    "date": [
        "date", "transactiondate", "txdate", "entrydate", "postingdate",
        "recorddate",
        # Malay: tarikh, tarikh transaksi
        "tarikh", "tarikhtransaksi",
    ],
    "type": [
        "type", "transactiontype", "txtype", "flow", "direction",
        "entrytype", "categorytype",
        # Malay: jenis, jenis transaksi
        "jenis", "jenistransaksi", "jeniskategori",
    ],
    "category": [
        "category", "product", "service", "item", "itemname",
        "productname", "classification", "group", "tag", "menu",
        # Malay: kategori, produk, perkhidmatan, kumpulan, menu
        "kategori", "produk", "perkhidmatan", "kumpulan", "klasifikasi",
    ],
    "description": [
        "description", "details", "memo", "note", "notes", "remarks",
        "comment", "narration", "particulars", "nama", "name",
        # Malay: penerangan, butiran, catatan, keterangan, nama
        "penerangan", "butiran", "catatan", "keterangan", "ulasan",
    ],
    "amount": [
        # High priority: total/actual transaction amounts (matched first)
        "amountrm", "amount", "total", "totalsales", "totalamount",
        "sales", "sum", "figure",
        # Malay: jumlah (total), hasil (revenue), jualan (sales)
        "jumlah", "jumlahjualan", "hasil", "jualan",
        # Medium priority: generic value
        "value", "nilai",
        # Lower priority: per-unit prices (only if no total/sales column)
        "price", "harga", "cost", "kos",
        # Accounting terms
        "debit", "credit", "kredit",
    ],
    "quantity": [
        "quantity", "qty", "count", "unitssold", "unitcount",
        "amountsold", "bilsold",
        # Malay: kuantiti, bilangan, kiraan
        "kuantiti", "bilangan", "kiraan",
    ],
    "unit_price": [
        "unitprice", "priceperunit", "rate", "rateperunit", "unitcost",
        # Malay: harga seunit, kos seunit
        "hargaseunit", "kosseunit",
    ],
    "invoice_id": [
        "invoiceid", "invoiceref", "refinvoice", "linkedinvoice",
        "invoice", "invno", "invoicenumber", "link", "linkedinv",
        # Malay: invois berkaitan, rujukan invois
        "invois", "invoisberkaitan", "rujukaninvois",
    ],
    "region": [
        "region", "location", "area", "zone", "territory", "branch",
        "city", "state", "country",
        # Malay: kawasan, wilayah, cawangan, negeri, bandar
        "kawasan", "wilayah", "cawangan", "negeri", "bandar",
    ],
}


def _normalize(name: str) -> str:
    """Normalize a column name: lowercase, remove spaces, underscores, hyphens."""
    name = name.lower().strip()
    # Remove common separators and punctuation
    name = re.sub(r"[\s_\-./()]+", "", name)
    return name


# ---------------------------------------------------------------------------
# Income/expense keyword sets for value-based type validation (Pass 4)
# ---------------------------------------------------------------------------
_INCOME_KEYWORDS: set[str] = {
    # English
    "income", "credit", "in", "receipt", "revenue", "sale", "sales",
    "inflow", "deposit", "earning", "gain", "profit", "incoming",
    # Malay
    "pendapatan", "hasil", "jualan", "penerimaan", "untung", "masuk",
}

_EXPENSE_KEYWORDS: set[str] = {
    # English
    "expense", "debit", "out", "payment", "cost", "spend", "bill",
    "outflow", "withdrawal", "loss", "outgoing", "purchase",
    # Malay
    "perbelanjaan", "belanja", "pengeluaran", "kos", "bayaran", "keluar",
    "belian",
}


def _is_income_expense_keyword(value: str) -> bool:
    """Check if a string value is a recognized income or expense keyword.

    Used by Pass 4 to determine whether a column mapped to `type` actually
    contains income/expense indicators or something else (e.g., product names).
    """
    value = value.lower().strip()
    # Remove common punctuation that might be attached
    value = re.sub(r"[\s_\-./()]+", "", value)
    return value in _INCOME_KEYWORDS or value in _EXPENSE_KEYWORDS


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

    # ---- Pass 4: Value-based validation (SMART RE-MAPPING) ----
    # If a column was mapped to `type` but its sample values aren't income/expense
    # keywords, the column likely contains product/item names or other text.
    # Remap it to `category` or `description` instead.
    # This handles files like student sales records where "Type" = product name.
    if mapping.get("type") is not None:
        type_col_name = mapping["type"]
        type_col = next(
            (c for c in inspection["columns"] if c["name"] == type_col_name),
            None,
        )
        if type_col:
            sample_vals = [
                v.lower().strip() for v in type_col.get("sample_values", [])
            ]
            if sample_vals:
                recognized = sum(
                    1 for v in sample_vals if _is_income_expense_keyword(v)
                )
                if recognized / len(sample_vals) < 0.3:
                    # Values aren't income/expense — remap to text field
                    claimed_cols.discard(type_col_name)
                    mapping["type"] = None
                    notes.append(
                        f"SMART: Column '{type_col_name}' was initially mapped to "
                        f"'type' but its values (e.g., {', '.join(sample_vals[:3])}) "
                        f"don't look like income/expense keywords. Remapping to a "
                        f"text field."
                    )
                    # Try category first (product names fit better as categories),
                    # then description as fallback
                    for target in ("category", "description"):
                        if mapping.get(target) is None:
                            mapping[target] = type_col_name
                            claimed_cols.add(type_col_name)
                            notes.append(
                                f"SMART: Column '{type_col_name}' remapped to "
                                f"'{target}'."
                            )
                            break

    # ---- Pass 5: Amount priority refinement (SMART SELECTION) ----
    # If `amount` was mapped to a per-unit-price column (e.g., "Unit Price"),
    # try to find a better total-amount column. If none found but quantity
    # exists, remap to unit_price so amount can be computed as qty x price.
    if mapping.get("amount") is not None:
        amount_col_name = mapping["amount"]
        amount_col_norm = _normalize(amount_col_name)
        # Check if the mapped column name looks like a per-unit price
        unit_price_indicators = ("price", "harga", "unitprice", "rate")
        is_likely_unit_price = any(
            ind in amount_col_norm for ind in unit_price_indicators
        )
        if is_likely_unit_price:
            # Look for a better total-amount column among unmapped columns
            total_indicators = (
                "total", "sales", "jualan", "hasil", "jumlah",
                "sum", "grandtotal", "subtotal",
            )
            found_better = False
            for col in inspection["columns"]:
                col_name = col["name"]
                if col_name in claimed_cols:
                    continue
                col_norm = _normalize(col_name)
                if any(ind in col_norm for ind in total_indicators):
                    # Found a better column — switch
                    claimed_cols.discard(amount_col_name)
                    mapping["amount"] = col_name
                    claimed_cols.add(col_name)
                    notes.append(
                        f"SMART: Amount field re-mapped from '{amount_col_name}' "
                        f"(per-unit price) to '{col_name}' (total amount) "
                        f"for better accuracy."
                    )
                    found_better = True
                    break

            # If no better total column found AND quantity column exists,
            # remap to unit_price so amount = quantity x unit_price can be computed
            if not found_better and mapping.get("quantity") is not None:
                claimed_cols.discard(amount_col_name)
                mapping["amount"] = None
                mapping["unit_price"] = amount_col_name
                notes.append(
                    f"SMART: Column '{amount_col_name}' looks like a per-unit "
                    f"price and a quantity column exists. Remapping to "
                    f"'unit_price' — amount will be computed as "
                    f"quantity x unit_price."
                )

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
    return ["date", "type", "category", "description", "quantity", "unit_price"]
