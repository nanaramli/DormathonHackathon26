"""
Tests for data_loader.py

Run with:  python -m pytest tests/test_data_loader.py
    or:    python tests/run_tests.py
"""

import os
import sys
import tempfile
import unittest

# Add project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import (
    load_invoices,
    load_transactions,
    load_dataset,
    describe_dataset,
    DataLoadError,
)


SAMPLE_INVOICES_CSV = """invoice_id,customer_name,issue_date,due_date,invoice_amount_rm,amount_paid_rm,balance_due_rm,status
INV001,Customer A,2026-09-02,2026-09-09,1500.0,1500.0,0.0,paid
INV002,Campus Club,2026-09-05,2026-09-12,2200.0,2200.0,0.0,paid
INV007,Customer D,2026-09-20,2026-09-27,1200.0,0.0,1200.0,overdue
"""

SAMPLE_TRANSACTIONS_CSV = """transaction_id,date,type,category,description,amount_rm,invoice_id
T001,2026-09-02,income,Design,Logo design project,1500.0,INV001
T002,2026-09-03,expense,Supplies,Printing paper and ink,450.0,
T003,2026-09-05,income,Printing,Club event banners,2200.0,INV002
"""


class TestLoadInvoices(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "invoices.csv")
        with open(self.path, "w") as f:
            f.write(SAMPLE_INVOICES_CSV)

    def test_loads_correct_number_of_rows(self):
        invoices = load_invoices(self.path)
        self.assertEqual(len(invoices), 3)

    def test_parses_float_fields(self):
        invoices = load_invoices(self.path)
        self.assertIsInstance(invoices[0]["invoice_amount_rm"], float)
        self.assertEqual(invoices[0]["invoice_amount_rm"], 1500.0)

    def test_parses_status_lowercase(self):
        invoices = load_invoices(self.path)
        self.assertEqual(invoices[0]["status"], "paid")
        self.assertEqual(invoices[2]["status"], "overdue")

    def test_missing_file_raises_error(self):
        with self.assertRaises(DataLoadError):
            load_invoices("/nonexistent/path/file.csv")

    def test_missing_column_raises_error(self):
        bad_path = os.path.join(self.tmpdir, "bad.csv")
        with open(bad_path, "w") as f:
            f.write("invoice_id,customer_name\nA,B\n")
        with self.assertRaises(DataLoadError):
            load_invoices(bad_path)

    def test_invalid_status_raises_error(self):
        bad_path = os.path.join(self.tmpdir, "bad_status.csv")
        with open(bad_path, "w") as f:
            f.write("invoice_id,customer_name,issue_date,due_date,invoice_amount_rm,amount_paid_rm,balance_due_rm,status\n")
            f.write("INV001,A,2026-09-02,2026-09-09,100.0,100.0,0.0,weird\n")
        with self.assertRaises(DataLoadError):
            load_invoices(bad_path)


class TestLoadTransactions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "transactions.csv")
        with open(self.path, "w") as f:
            f.write(SAMPLE_TRANSACTIONS_CSV)

    def test_loads_correct_number_of_rows(self):
        txs = load_transactions(self.path)
        self.assertEqual(len(txs), 3)

    def test_parses_types(self):
        txs = load_transactions(self.path)
        self.assertEqual(txs[0]["type"], "income")
        self.assertEqual(txs[1]["type"], "expense")

    def test_empty_invoice_id_allowed(self):
        txs = load_transactions(self.path)
        self.assertEqual(txs[1]["invoice_id"], "")
        self.assertEqual(txs[0]["invoice_id"], "INV001")

    def test_invalid_type_raises_error(self):
        bad_path = os.path.join(self.tmpdir, "bad.csv")
        with open(bad_path, "w") as f:
            f.write("transaction_id,date,type,category,description,amount_rm,invoice_id\n")
            f.write("T001,2026-09-02,revenue,Design,Test,100.0,\n")
        with self.assertRaises(DataLoadError):
            load_transactions(bad_path)


class TestLoadDataset(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        inv_path = os.path.join(self.tmpdir, "invoices.csv")
        tx_path = os.path.join(self.tmpdir, "transactions.csv")
        with open(inv_path, "w") as f:
            f.write(SAMPLE_INVOICES_CSV)
        with open(tx_path, "w") as f:
            f.write(SAMPLE_TRANSACTIONS_CSV)

    def test_loads_both_files(self):
        ds = load_dataset(self.tmpdir)
        self.assertEqual(len(ds["invoices"]), 3)
        self.assertEqual(len(ds["transactions"]), 3)

    def test_cross_validation_catches_bad_reference(self):
        bad_tx = os.path.join(self.tmpdir, "transactions_bad_ref.csv")
        with open(bad_tx, "w") as f:
            f.write("transaction_id,date,type,category,description,amount_rm,invoice_id\n")
            f.write("T001,2026-09-02,income,Design,Test,100.0,NONEXIST\n")
        # Temporarily rename
        real_tx = os.path.join(self.tmpdir, "transactions.csv")
        os.rename(real_tx, real_tx + ".bak")
        os.rename(bad_tx, real_tx)
        with self.assertRaises(DataLoadError):
            load_dataset(self.tmpdir)


class TestDescribeDataset(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        inv_path = os.path.join(self.tmpdir, "invoices.csv")
        tx_path = os.path.join(self.tmpdir, "transactions.csv")
        with open(inv_path, "w") as f:
            f.write(SAMPLE_INVOICES_CSV)
        with open(tx_path, "w") as f:
            f.write(SAMPLE_TRANSACTIONS_CSV)

    def test_describes_correct_counts(self):
        ds = load_dataset(self.tmpdir)
        desc = describe_dataset(ds)
        self.assertEqual(desc["invoice_count"], 3)
        self.assertEqual(desc["transaction_count"], 3)
        self.assertEqual(desc["income_transaction_count"], 2)
        self.assertEqual(desc["expense_transaction_count"], 1)

    def test_reports_no_region_data(self):
        ds = load_dataset(self.tmpdir)
        desc = describe_dataset(ds)
        self.assertFalse(desc["has_region_data"])

    def test_reports_no_returns_data(self):
        ds = load_dataset(self.tmpdir)
        desc = describe_dataset(ds)
        self.assertFalse(desc["has_returns_data"])


if __name__ == "__main__":
    unittest.main()
