"""
Tests for Phase 2 modules: file_inspector, column_mapper, adaptive_loader.

These tests verify that RichBuddy can:
    1. Inspect CSV and Excel files of arbitrary structure
    2. Map detected columns to expected fields using alias matching
    3. Load user-provided files with different column names
    4. Infer missing fields (type, status, balance)
    5. Generate valid analysis output from adaptively-loaded data
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from file_inspector import inspect_file, FileInspectionError, format_inspection_summary
from column_mapper import (
    map_invoice_columns,
    map_transaction_columns,
    map_columns,
    INVOICE_FIELDS,
    TRANSACTION_FIELDS,
)
from adaptive_loader import (
    load_user_file,
    load_user_dataset,
    AdaptiveLoadError,
    format_adaptation_report,
)
from orchestrator import run_analysis


# ---------------------------------------------------------------------------
# Test data files with DIFFERENT column names than the sample dataset
# This simulates a user uploading their own files.
# ---------------------------------------------------------------------------
CSV_INVOICES_DIFFERENT_NAMES = """Invoice No,Customer,Date Issued,Payment Due,Total Amount,Paid Amount,Balance,Payment Status
INV001,Acme Corp,2026-09-02,2026-09-09,1500.00,1500.00,0.00,Paid
INV002,Beta LLC,2026-09-05,2026-09-12,2200.00,2200.00,0.00,Paid
INV003,Gamma Inc,2026-09-10,2026-09-17,800.00,0.00,800.00,Overdue
INV004,Delta Co,2026-09-15,2026-09-22,3000.00,3000.00,0.00,Paid
"""

CSV_TRANSACTIONS_DIFFERENT_NAMES = """Tx ID,Date,Entry Type,Category,Description,Amount,Linked Invoice
TX001,2026-09-02,Income,Design,Logo project,1500.00,INV001
TX002,2026-09-03,Expense,Supplies,Paper and ink,450.00,
TX003,2026-09-05,Income,Printing,Banners,2200.00,INV002
TX004,2026-09-07,Expense,Marketing,Ads,200.00,
TX005,2026-09-10,Income,Design,Cards,800.00,INV003
TX006,2026-09-12,Expense,Transport,Fuel,120.00,
"""

# A combined file with both income and expense, no "type" column,
# using positive/negative amounts to indicate direction
CSV_COMBINED_NO_TYPE = """Date,Description,Category,Amount
2026-09-02,Logo project,Design,1500.00
2026-09-03,Paper and ink,Supplies,-450.00
2026-09-05,Banners,Printing,2200.00
2026-09-07,Ads,Marketing,-200.00
2026-09-10,Cards,Design,800.00
2026-09-12,Fuel,Transport,-120.00
"""

# A file with region data
CSV_WITH_REGION = """Invoice No,Customer,Region,Total Amount,Paid Amount,Status
INV001,North Corp,North,1500.00,1500.00,Paid
INV002,South LLC,South,2200.00,0.00,Overdue
INV003,East Inc,East,800.00,800.00,Paid
INV004,West Co,West,3000.00,3000.00,Paid
"""


def _write_temp_csv(content: str, tmpdir: str, filename: str = "test.csv") -> str:
    """Write content to a temp CSV file and return its path."""
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Tests: file_inspector
# ---------------------------------------------------------------------------
class TestInspectCSVFile(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = _write_temp_csv(CSV_INVOICES_DIFFERENT_NAMES, self.tmpdir, "invoices.csv")

    def test_returns_correct_format(self):
        result = inspect_file(self.path)
        self.assertEqual(result["format"], "csv")

    def test_returns_correct_row_count(self):
        result = inspect_file(self.path)
        self.assertEqual(result["row_count"], 4)

    def test_returns_column_names(self):
        result = inspect_file(self.path)
        names = [c["name"] for c in result["columns"]]
        self.assertIn("Invoice No", names)
        self.assertIn("Customer", names)
        self.assertIn("Total Amount", names)

    def test_infers_number_type(self):
        result = inspect_file(self.path)
        amount_col = [c for c in result["columns"] if c["name"] == "Total Amount"][0]
        self.assertEqual(amount_col["inferred_type"], "number")

    def test_infers_date_type(self):
        result = inspect_file(self.path)
        date_col = [c for c in result["columns"] if c["name"] == "Date Issued"][0]
        self.assertEqual(date_col["inferred_type"], "date")

    def test_missing_file_raises_error(self):
        with self.assertRaises(FileInspectionError):
            inspect_file("/nonexistent/file.csv")

    def test_unsupported_format_raises_error(self):
        bad_path = os.path.join(self.tmpdir, "test.txt")
        with open(bad_path, "w") as f:
            f.write("hello")
        with self.assertRaises(FileInspectionError):
            inspect_file(bad_path)

    def test_sample_values_returned(self):
        result = inspect_file(self.path)
        customer_col = [c for c in result["columns"] if c["name"] == "Customer"][0]
        self.assertTrue(len(customer_col["sample_values"]) > 0)
        self.assertIn("Acme Corp", customer_col["sample_values"])


class TestInspectExcelFile(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "test.xlsx")
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest("openpyxl not available")

        wb = Workbook()
        ws = wb.active
        ws.title = "Sales Data"
        ws.append(["Invoice No", "Customer", "Amount"])
        ws.append(["INV001", "Acme", 1500.0])
        ws.append(["INV002", "Beta", 2200.0])
        wb.save(self.path)
        wb.close()

    def test_returns_xlsx_format(self):
        result = inspect_file(self.path)
        self.assertEqual(result["format"], "xlsx")

    def test_returns_row_count(self):
        result = inspect_file(self.path)
        self.assertEqual(result["row_count"], 2)

    def test_returns_sheet_names(self):
        result = inspect_file(self.path)
        self.assertIn("sheet_names", result)
        self.assertIn("Sales Data", result["sheet_names"])

    def test_returns_columns(self):
        result = inspect_file(self.path)
        names = [c["name"] for c in result["columns"]]
        self.assertIn("Invoice No", names)
        self.assertIn("Amount", names)


# ---------------------------------------------------------------------------
# Tests: column_mapper
# ---------------------------------------------------------------------------
class TestMapInvoiceColumns(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = _write_temp_csv(CSV_INVOICES_DIFFERENT_NAMES, self.tmpdir)

    def test_maps_invoice_id(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["invoice_id"], "Invoice No")

    def test_maps_customer_name(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["customer_name"], "Customer")

    def test_maps_invoice_amount(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["invoice_amount"], "Total Amount")

    def test_maps_amount_paid(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["amount_paid"], "Paid Amount")

    def test_maps_balance_due(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["balance_due"], "Balance")

    def test_maps_status(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["status"], "Payment Status")

    def test_maps_issue_date(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["issue_date"], "Date Issued")

    def test_maps_due_date(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        self.assertEqual(mapping["mapping"]["due_date"], "Payment Due")

    def test_reports_missing_fields(self):
        inspection = inspect_file(self.path)
        mapping = map_invoice_columns(inspection)
        # Region and product should not be found
        self.assertIsNone(mapping["mapping"]["region"])
        self.assertIsNone(mapping["mapping"]["product"])
        self.assertIn("region", mapping["missing_fields"])
        self.assertIn("product", mapping["missing_fields"])


class TestMapTransactionColumns(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = _write_temp_csv(CSV_TRANSACTIONS_DIFFERENT_NAMES, self.tmpdir)

    def test_maps_transaction_id(self):
        inspection = inspect_file(self.path)
        mapping = map_transaction_columns(inspection)
        self.assertEqual(mapping["mapping"]["transaction_id"], "Tx ID")

    def test_maps_type(self):
        inspection = inspect_file(self.path)
        mapping = map_transaction_columns(inspection)
        self.assertEqual(mapping["mapping"]["type"], "Entry Type")

    def test_maps_amount(self):
        inspection = inspect_file(self.path)
        mapping = map_transaction_columns(inspection)
        self.assertEqual(mapping["mapping"]["amount"], "Amount")

    def test_maps_invoice_ref(self):
        inspection = inspect_file(self.path)
        mapping = map_transaction_columns(inspection)
        self.assertEqual(mapping["mapping"]["invoice_id"], "Linked Invoice")

    def test_maps_description(self):
        inspection = inspect_file(self.path)
        mapping = map_transaction_columns(inspection)
        self.assertEqual(mapping["mapping"]["description"], "Description")


# ---------------------------------------------------------------------------
# Tests: adaptive_loader
# ---------------------------------------------------------------------------
class TestLoadUserFile(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.inv_path = _write_temp_csv(CSV_INVOICES_DIFFERENT_NAMES, self.tmpdir, "invoices.csv")
        self.tx_path = _write_temp_csv(CSV_TRANSACTIONS_DIFFERENT_NAMES, self.tmpdir, "transactions.csv")

    def test_detects_invoice_file(self):
        report = load_user_file(self.inv_path)
        self.assertEqual(report["best_match"], "invoices")

    def test_detects_transaction_file(self):
        report = load_user_file(self.tx_path)
        self.assertEqual(report["best_match"], "transactions")

    def test_invoice_mapping_has_amount(self):
        report = load_user_file(self.inv_path)
        mapping = report["mapping_used"]["mapping"]
        self.assertIsNotNone(mapping["invoice_amount"])

    def test_adaptation_notes_generated(self):
        report = load_user_file(self.inv_path)
        self.assertTrue(len(report["adaptation_notes"]) > 0)


class TestLoadUserDataset(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.inv_path = _write_temp_csv(CSV_INVOICES_DIFFERENT_NAMES, self.tmpdir, "invoices.csv")
        self.tx_path = _write_temp_csv(CSV_TRANSACTIONS_DIFFERENT_NAMES, self.tmpdir, "transactions.csv")

    def test_loads_two_files(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        self.assertEqual(len(ds["invoices"]), 4)
        self.assertEqual(len(ds["transactions"]), 6)

    def test_invoices_have_standardized_fields(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        inv = ds["invoices"][0]
        self.assertIn("invoice_id", inv)
        self.assertIn("customer_name", inv)
        self.assertIn("invoice_amount_rm", inv)
        self.assertIn("amount_paid_rm", inv)
        self.assertIn("balance_due_rm", inv)
        self.assertIn("status", inv)

    def test_transactions_have_standardized_fields(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        tx = ds["transactions"][0]
        self.assertIn("transaction_id", tx)
        self.assertIn("date", tx)
        self.assertIn("type", tx)
        self.assertIn("category", tx)
        self.assertIn("amount_rm", tx)

    def test_invoice_amounts_correct(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        self.assertAlmostEqual(ds["invoices"][0]["invoice_amount_rm"], 1500.0, places=2)
        self.assertAlmostEqual(ds["invoices"][1]["invoice_amount_rm"], 2200.0, places=2)

    def test_transaction_types_correct(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        self.assertEqual(ds["transactions"][0]["type"], "income")
        self.assertEqual(ds["transactions"][1]["type"], "expense")

    def test_transaction_amounts_correct(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        self.assertAlmostEqual(ds["transactions"][0]["amount_rm"], 1500.0, places=2)

    def test_overdue_invoice_has_balance(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        overdue = [i for i in ds["invoices"] if i["status"] == "overdue"][0]
        self.assertAlmostEqual(overdue["balance_due_rm"], 800.0, places=2)
        self.assertAlmostEqual(overdue["amount_paid_rm"], 0.0, places=2)

    def test_adaptation_report_present(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        self.assertIn("adaptation_report", ds)
        self.assertIn("all_notes", ds["adaptation_report"])
        self.assertTrue(len(ds["adaptation_report"]["all_notes"]) > 0)

    def test_data_source_is_user_provided(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        self.assertEqual(ds["data_dir"], "user_provided")

    def test_single_file_only_invoices(self):
        ds = load_user_dataset([self.inv_path])
        self.assertEqual(len(ds["invoices"]), 4)
        self.assertEqual(len(ds["transactions"]), 0)

    def test_single_file_only_transactions(self):
        ds = load_user_dataset([self.tx_path])
        self.assertEqual(len(ds["invoices"]), 0)
        self.assertEqual(len(ds["transactions"]), 6)


class TestLoadUserDatasetCombinedNoType(unittest.TestCase):
    """Test a single combined file where type is inferred from amount sign."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = _write_temp_csv(CSV_COMBINED_NO_TYPE, self.tmpdir, "combined.csv")

    def test_detects_as_transactions(self):
        ds = load_user_dataset([self.path])
        self.assertTrue(len(ds["transactions"]) > 0)
        self.assertEqual(len(ds["invoices"]), 0)

    def test_infers_income_from_positive(self):
        ds = load_user_dataset([self.path])
        income_txs = [t for t in ds["transactions"] if t["type"] == "income"]
        self.assertTrue(len(income_txs) > 0)

    def test_infers_expense_from_negative(self):
        ds = load_user_dataset([self.path])
        expense_txs = [t for t in ds["transactions"] if t["type"] == "expense"]
        self.assertTrue(len(expense_txs) > 0)

    def test_amounts_are_positive(self):
        ds = load_user_dataset([self.path])
        for tx in ds["transactions"]:
            self.assertGreater(tx["amount_rm"], 0)


class TestLoadUserDatasetWithRegion(unittest.TestCase):
    """Test that region data is passed through."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = _write_temp_csv(CSV_WITH_REGION, self.tmpdir, "regional.csv")

    def test_region_field_present(self):
        ds = load_user_dataset([self.path])
        self.assertTrue(len(ds["invoices"]) > 0)
        inv = ds["invoices"][0]
        self.assertIn("region", inv)
        self.assertTrue(inv["region"])

    def test_region_values_correct(self):
        ds = load_user_dataset([self.path])
        regions = [i["region"] for i in ds["invoices"]]
        self.assertIn("North", regions)
        self.assertIn("South", regions)


# ---------------------------------------------------------------------------
# Tests: End-to-end with user-provided files
# ---------------------------------------------------------------------------
class TestEndToEndUserFiles(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")
        self.inv_path = _write_temp_csv(CSV_INVOICES_DIFFERENT_NAMES, self.tmpdir, "invoices.csv")
        self.tx_path = _write_temp_csv(CSV_TRANSACTIONS_DIFFERENT_NAMES, self.tmpdir, "transactions.csv")
        self.dataset = load_user_dataset([self.inv_path, self.tx_path])

    def test_overall_performance_works(self):
        result = run_analysis("Analyse my overall business performance", self.dataset, self.outdir)
        self.assertEqual(result["intent"], "overall_performance")
        self.assertIn("net_profit", result["findings"])
        self.assertIn("adaptive", " ".join(result["data_notes"]).lower())

    def test_profit_loss_works(self):
        result = run_analysis("Which products are profitable?", self.dataset, self.outdir)
        self.assertEqual(result["intent"], "profit_loss_products")
        self.assertIn("profit_by_category", result["findings"])

    def test_priority_actions_works(self):
        result = run_analysis("What are the three most important actions?", self.dataset, self.outdir)
        self.assertEqual(result["intent"], "priority_actions")
        self.assertTrue(len(result["actions"]) > 0)

    def test_report_files_generated(self):
        result = run_analysis("Analyse my overall business performance", self.dataset, self.outdir)
        self.assertTrue(os.path.isfile(result["report_path"]))
        self.assertTrue(len(result["csv_paths"]) > 0)

    def test_regional_analysis_with_region_data(self):
        # Load the regional CSV
        reg_path = _write_temp_csv(CSV_WITH_REGION, self.tmpdir, "regional.csv")
        ds = load_user_dataset([reg_path])
        result = run_analysis("Compare my sales across regions", ds, self.outdir)
        self.assertEqual(result["intent"], "regional_comparison")
        # Should have regional analysis since region data is present
        self.assertIn("regional_analysis", result["findings"])

    def test_transactions_only_works(self):
        ds = load_user_dataset([self.tx_path])
        result = run_analysis("Analyse my overall business performance", ds, self.outdir)
        self.assertIn("net_profit", result["findings"])
        # Should note that invoice data is missing
        self.assertIn("invoice", " ".join(result["data_notes"]).lower())

    def test_invoices_only_works(self):
        ds = load_user_dataset([self.inv_path])
        result = run_analysis("What are the three most important actions?", ds, self.outdir)
        # Should still work, just with limited actions
        self.assertTrue(os.path.isfile(result["report_path"]))


class TestFormatAdaptationReport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.inv_path = _write_temp_csv(CSV_INVOICES_DIFFERENT_NAMES, self.tmpdir, "invoices.csv")
        self.tx_path = _write_temp_csv(CSV_TRANSACTIONS_DIFFERENT_NAMES, self.tmpdir, "transactions.csv")

    def test_returns_readable_text(self):
        ds = load_user_dataset([self.inv_path, self.tx_path])
        report = format_adaptation_report(ds)
        self.assertIn("Data Adaptation Report", report)
        self.assertIn("invoices.csv", report)
        self.assertIn("transactions.csv", report)
        self.assertIn("Column Mapping", report)


if __name__ == "__main__":
    unittest.main()
