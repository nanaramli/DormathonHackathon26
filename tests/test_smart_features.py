"""
test_smart_features.py - Tests for the SMART column mapping and expense detection.

Tests the enhancements that make RichBuddy "know everything" when handling
any simple student Excel file:

1. Pass 4: Value-based type column remapping (Type with product names -> category)
2. Pass 5: Amount priority refinement (Sales preferred over Unit Price)
3. Smart expense detection in unmapped columns (Modal, Cost, etc.)
4. Quantity & unit_price field recognition
5. Amount computation from quantity x unit_price fallback
"""

import os
import sys
import tempfile
import unittest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from column_mapper import (
    map_transaction_columns,
    map_invoice_columns,
    _is_income_expense_keyword,
)
from file_inspector import inspect_file
from adaptive_loader import (
    load_user_dataset,
    _detect_unmapped_expenses,
    _try_extract_number,
)


def _make_inspection(columns, rows=None):
    """Build a minimal inspection dict for testing."""
    col_list = []
    for idx, (name, samples) in enumerate(columns):
        col_list.append({
            "name": name,
            "index": idx,
            "sample_values": samples,
            "inferred_type": "text" if any(
                not s.replace(".", "").replace("-", "").isdigit()
                for s in samples
            ) else "number",
        })
    return {
        "path": "<test>",
        "filename": "test.xlsx",
        "format": "xlsx",
        "row_count": len(rows) if rows else 10,
        "columns": col_list,
    }


class TestIsIncomeExpenseKeyword(unittest.TestCase):
    """Test the _is_income_expense_keyword helper."""

    def test_recognizes_english_income(self):
        self.assertTrue(_is_income_expense_keyword("income"))
        self.assertTrue(_is_income_expense_keyword("Income"))
        self.assertTrue(_is_income_expense_keyword("credit"))
        self.assertTrue(_is_income_expense_keyword("revenue"))

    def test_recognizes_english_expense(self):
        self.assertTrue(_is_income_expense_keyword("expense"))
        self.assertTrue(_is_income_expense_keyword("Expense"))
        self.assertTrue(_is_income_expense_keyword("cost"))
        self.assertTrue(_is_income_expense_keyword("payment"))

    def test_recognizes_malay_income(self):
        self.assertTrue(_is_income_expense_keyword("pendapatan"))
        self.assertTrue(_is_income_expense_keyword("hasil"))
        self.assertTrue(_is_income_expense_keyword("jualan"))

    def test_recognizes_malay_expense(self):
        self.assertTrue(_is_income_expense_keyword("kos"))
        self.assertTrue(_is_income_expense_keyword("belanja"))
        self.assertTrue(_is_income_expense_keyword("pengeluaran"))

    def test_rejects_product_names(self):
        self.assertFalse(_is_income_expense_keyword("Ramen Ori"))
        self.assertFalse(_is_income_expense_keyword("Ramen Cheese"))
        self.assertFalse(_is_income_expense_keyword("Nasi Lemak"))
        self.assertFalse(_is_income_expense_keyword("Kopi O"))

    def test_rejects_empty(self):
        self.assertFalse(_is_income_expense_keyword(""))
        self.assertFalse(_is_income_expense_keyword("  "))


class TestPass4TypeRemapping(unittest.TestCase):
    """Test Pass 4: value-based type column remapping."""

    def test_type_with_product_names_remapped_to_category(self):
        """A 'Type' column containing product names should be remapped to category."""
        inspection = _make_inspection([
            ("Date", ["2024-10-25", "2024-10-26"]),
            ("Type", ["Ramen Ori", "Ramen Cheese", "Ramen Stew"]),
            ("Quantity", ["1", "2", "2"]),
            ("Unit Price (RM)", ["6", "6", "6"]),
            ("Sales", ["6", "12", "12"]),
        ])
        result = map_transaction_columns(inspection)
        mapping = result["mapping"]

        # Type should be None (remapped away)
        self.assertIsNone(mapping["type"],
                          "Type column with product names should be remapped away")

        # Category should now be "Type"
        self.assertEqual(mapping["category"], "Type",
                         "Product name column should be remapped to category")

        # Verify SMART note was generated
        smart_notes = [n for n in result["mapping_notes"] if "SMART" in n]
        self.assertTrue(any("remapped to 'category'" in n for n in smart_notes))

    def test_type_with_income_expense_kept_as_type(self):
        """A 'Type' column with actual income/expense values should stay as type."""
        inspection = _make_inspection([
            ("Date", ["2024-01-01", "2024-01-02"]),
            ("Type", ["income", "expense", "income"]),
            ("Amount", ["100", "50", "200"]),
            ("Category", ["Design", "Software", "Design"]),
        ])
        result = map_transaction_columns(inspection)
        mapping = result["mapping"]

        # Type should remain mapped to "Type"
        self.assertEqual(mapping["type"], "Type")
        # Category should be "Category" (not remapped)
        self.assertEqual(mapping["category"], "Category")

    def test_type_with_malay_income_expense_kept(self):
        """Malay income/expense keywords should keep type mapping."""
        inspection = _make_inspection([
            ("Date", ["2024-01-01", "2024-01-02"]),
            ("Type", ["pendapatan", "kos", "pendapatan"]),
            ("Amount", ["100", "50", "200"]),
        ])
        result = map_transaction_columns(inspection)
        mapping = result["mapping"]

        self.assertEqual(mapping["type"], "Type",
                         "Malay income/expense keywords should keep type mapping")


class TestPass5AmountPriority(unittest.TestCase):
    """Test Pass 5: amount priority refinement."""

    def test_sales_preferred_over_unit_price(self):
        """When both 'Sales' and 'Unit Price' columns exist, amount -> Sales."""
        inspection = _make_inspection([
            ("Date", ["2024-10-25"]),
            ("Type", ["Ramen Ori"]),
            ("Quantity", ["1"]),
            ("Unit Price (RM)", ["6"]),
            ("Sales", ["6"]),
        ])
        result = map_transaction_columns(inspection)
        mapping = result["mapping"]

        self.assertEqual(mapping["amount"], "Sales",
                         "Amount should map to 'Sales' (total), not 'Unit Price'")

    def test_unit_price_used_when_no_sales(self):
        """When only 'Unit Price' exists (no Sales), amount -> Unit Price as fallback."""
        inspection = _make_inspection([
            ("Date", ["2024-10-25"]),
            ("Type", ["Ramen Ori"]),
            ("Quantity", ["1"]),
            ("Unit Price (RM)", ["6"]),
        ])
        result = map_transaction_columns(inspection)
        mapping = result["mapping"]

        # With no Sales column, unit_price gets mapped to unit_price field
        # and amount has no match (no total column)
        self.assertEqual(mapping.get("unit_price"), "Unit Price (RM)")
        # Amount should be None (no Sales/Total column)
        self.assertIsNone(mapping.get("amount"))

    def test_new_sales_alias_recognized(self):
        """The 'sales' alias should be recognized for the amount field."""
        inspection = _make_inspection([
            ("Date", ["2024-01-01"]),
            ("Sales", ["100", "200", "300"]),
        ])
        result = map_transaction_columns(inspection)
        self.assertEqual(result["mapping"]["amount"], "Sales")

    def test_malay_jualan_alias_recognized(self):
        """The Malay 'jualan' alias should be recognized for the amount field."""
        inspection = _make_inspection([
            ("Tarikh", ["2024-01-01"]),
            ("Jualan", ["100", "200", "300"]),
        ])
        result = map_transaction_columns(inspection)
        self.assertEqual(result["mapping"]["amount"], "Jualan")
        self.assertEqual(result["mapping"]["date"], "Tarikh")


class TestQuantityAndUnitPriceFields(unittest.TestCase):
    """Test that quantity and unit_price are recognized as fields."""

    def test_quantity_mapped(self):
        """Quantity column should be mapped to the quantity field."""
        inspection = _make_inspection([
            ("Date", ["2024-01-01"]),
            ("Quantity", ["1", "2", "3"]),
            ("Sales", ["6", "12", "18"]),
        ])
        result = map_transaction_columns(inspection)
        self.assertEqual(result["mapping"]["quantity"], "Quantity")

    def test_qty_alias_mapped(self):
        """'Qty' should be recognized as an alias for quantity."""
        inspection = _make_inspection([
            ("Date", ["2024-01-01"]),
            ("Qty", ["1", "2", "3"]),
            ("Sales", ["6", "12", "18"]),
        ])
        result = map_transaction_columns(inspection)
        self.assertEqual(result["mapping"]["quantity"], "Qty")

    def test_unit_price_mapped(self):
        """Unit Price column should be mapped to the unit_price field."""
        inspection = _make_inspection([
            ("Date", ["2024-01-01"]),
            ("Unit Price (RM)", ["6", "6", "6"]),
            ("Sales", ["6", "12", "18"]),
        ])
        result = map_transaction_columns(inspection)
        self.assertEqual(result["mapping"]["unit_price"], "Unit Price (RM)")


class TestTryExtractNumber(unittest.TestCase):
    """Test the _try_extract_number helper."""

    def test_plain_number(self):
        self.assertEqual(_try_extract_number("77"), 77.0)

    def test_with_rm_prefix(self):
        self.assertEqual(_try_extract_number("RM 77"), 77.0)
        self.assertEqual(_try_extract_number("rm 77"), 77.0)
        self.assertEqual(_try_extract_number("Rm 77"), 77.0)

    def test_with_myr_prefix(self):
        self.assertEqual(_try_extract_number("MYR 77"), 77.0)

    def test_decimal(self):
        self.assertEqual(_try_extract_number("77.50"), 77.5)

    def test_with_parentheses(self):
        self.assertEqual(_try_extract_number("77 (20 packs)"), 77.0)

    def test_with_text_prefix(self):
        self.assertEqual(_try_extract_number("Modal: 77"), 77.0)
        self.assertEqual(_try_extract_number("modal rm77"), 77.0)

    def test_with_comma(self):
        self.assertEqual(_try_extract_number("1,000"), 1000.0)

    def test_no_number_returns_none(self):
        self.assertIsNone(_try_extract_number("Modal"))
        self.assertIsNone(_try_extract_number("no numbers here"))

    def test_empty_returns_none(self):
        self.assertIsNone(_try_extract_number(""))
        self.assertIsNone(_try_extract_number(None))


class TestExpenseDetection(unittest.TestCase):
    """Test smart expense detection in unmapped columns."""

    def test_detect_expense_with_header(self):
        """Expense with header 'Modal' and value '77' in same column."""
        inspection = {
            "path": "<test>",
            "filename": "test.csv",
            "format": "csv",
            "row_count": 2,
            "columns": [
                {"name": "Date", "index": 0, "sample_values": ["2024-01-01"], "inferred_type": "date"},
                {"name": "Sales", "index": 1, "sample_values": ["100"], "inferred_type": "number"},
                {"name": "Modal", "index": 2, "sample_values": ["77"], "inferred_type": "number"},
            ],
        }
        # Create a temp CSV file for _read_raw_data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("Date,Sales,Modal\n")
            f.write("2024-01-01,100,77\n")
            inspection["path"] = f.name

        try:
            mapping = {"date": "Date", "amount": "Sales", "modal": None}
            notes = []
            expenses = _detect_unmapped_expenses(inspection, mapping, notes)
            self.assertEqual(len(expenses), 1)
            self.assertEqual(expenses[0]["amount_rm"], 77.0)
            self.assertEqual(expenses[0]["type"], "expense")
            self.assertTrue(any("Modal" in n for n in notes))
        finally:
            os.unlink(inspection["path"])

    def test_detect_expense_adjacent_columns(self):
        """Expense label in one column, value in adjacent column (student style)."""
        inspection = {
            "path": "<test>",
            "filename": "test.csv",
            "format": "csv",
            "row_count": 3,
            "columns": [
                {"name": "Date", "index": 0, "sample_values": ["2024-01-01"], "inferred_type": "date"},
                {"name": "Sales", "index": 1, "sample_values": ["100"], "inferred_type": "number"},
                {"name": "", "index": 2, "sample_values": ["Modal"], "inferred_type": "text"},
                {"name": "", "index": 3, "sample_values": ["Rm 77"], "inferred_type": "text"},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("Date,Sales,,\n")
            f.write("2024-01-01,100,Modal,Rm 77\n")
            f.write("2024-01-02,50,,\n")
            inspection["path"] = f.name

        try:
            mapping = {"date": "Date", "amount": "Sales"}
            notes = []
            expenses = _detect_unmapped_expenses(inspection, mapping, notes)
            self.assertEqual(len(expenses), 1)
            self.assertEqual(expenses[0]["amount_rm"], 77.0)
            self.assertEqual(expenses[0]["type"], "expense")
            self.assertTrue(any("Column 2 -> Column 3" in n or "Modal" in n for n in notes))
        finally:
            os.unlink(inspection["path"])

    def test_detect_expense_english_keyword(self):
        """English expense keyword 'cost' in header."""
        inspection = {
            "path": "<test>",
            "filename": "test.csv",
            "format": "csv",
            "row_count": 2,
            "columns": [
                {"name": "Date", "index": 0, "sample_values": ["2024-01-01"], "inferred_type": "date"},
                {"name": "Sales", "index": 1, "sample_values": ["100"], "inferred_type": "number"},
                {"name": "Cost", "index": 2, "sample_values": ["50"], "inferred_type": "number"},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("Date,Sales,Cost\n")
            f.write("2024-01-01,100,50\n")
            inspection["path"] = f.name

        try:
            mapping = {"date": "Date", "amount": "Sales"}
            notes = []
            expenses = _detect_unmapped_expenses(inspection, mapping, notes)
            self.assertEqual(len(expenses), 1)
            self.assertEqual(expenses[0]["amount_rm"], 50.0)
        finally:
            os.unlink(inspection["path"])

    def test_no_expense_when_no_keywords(self):
        """No expense detected when unmapped columns have no expense keywords."""
        inspection = {
            "path": "<test>",
            "filename": "test.csv",
            "format": "csv",
            "row_count": 2,
            "columns": [
                {"name": "Date", "index": 0, "sample_values": ["2024-01-01"], "inferred_type": "date"},
                {"name": "Sales", "index": 1, "sample_values": ["100"], "inferred_type": "number"},
                {"name": "Notes", "index": 2, "sample_values": ["hello"], "inferred_type": "text"},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("Date,Sales,Notes\n")
            f.write("2024-01-01,100,hello\n")
            inspection["path"] = f.name

        try:
            mapping = {"date": "Date", "amount": "Sales"}
            notes = []
            expenses = _detect_unmapped_expenses(inspection, mapping, notes)
            self.assertEqual(len(expenses), 0)
        finally:
            os.unlink(inspection["path"])


class TestAmountComputationFallback(unittest.TestCase):
    """Test amount computation from quantity x unit_price."""

    def test_amount_computed_from_qty_x_price(self):
        """When no amount column but qty + unit_price exist, compute amount."""
        inspection = _make_inspection([
            ("Date", ["2024-01-01", "2024-01-02"]),
            ("Product", ["Ramen Ori", "Ramen Cheese"]),
            ("Quantity", ["2", "3"]),
            ("Unit Price", ["6", "5"]),
        ])
        # Build a temp CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("Date,Product,Quantity,Unit Price\n")
            f.write("2024-01-01,Ramen Ori,2,6\n")
            f.write("2024-01-02,Ramen Cheese,3,5\n")
            temp_path = f.name

        inspection["path"] = temp_path
        try:
            dataset = load_user_dataset([temp_path])
            txs = dataset["transactions"]
            self.assertEqual(len(txs), 2)
            # Row 1: 2 * 6 = 12
            self.assertEqual(txs[0]["amount_rm"], 12.0)
            # Row 2: 3 * 5 = 15
            self.assertEqual(txs[1]["amount_rm"], 15.0)
        finally:
            os.unlink(temp_path)


class TestInvoiceFieldsSalesAlias(unittest.TestCase):
    """Test that 'sales' is recognized in invoice fields too."""

    def test_sales_alias_in_invoice_amount(self):
        """'Sales' should be recognized as an alias for invoice_amount."""
        inspection = _make_inspection([
            ("Invoice ID", ["INV-001"]),
            ("Customer", ["John"]),
            ("Sales", ["100", "200"]),
        ])
        result = map_invoice_columns(inspection)
        self.assertEqual(result["mapping"]["invoice_amount"], "Sales")


if __name__ == "__main__":
    unittest.main()
