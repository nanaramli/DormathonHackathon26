"""
Tests for file_generator.py and orchestrator.py (end-to-end)
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from file_generator import (
    generate_text_report,
    generate_csv_file,
    generate_analysis_csvs,
    ensure_output_dir,
)
from orchestrator import run_analysis
from data_loader import load_dataset


SAMPLE_INVOICES_CSV = """invoice_id,customer_name,issue_date,due_date,invoice_amount_rm,amount_paid_rm,balance_due_rm,status
INV001,Customer A,2026-09-02,2026-09-09,1500.0,1500.0,0.0,paid
INV002,Campus Club,2026-09-05,2026-09-12,2200.0,2200.0,0.0,paid
INV003,Customer B,2026-09-10,2026-09-17,800.0,800.0,0.0,paid
INV004,Student Society,2026-09-15,2026-09-22,3000.0,3000.0,0.0,paid
INV005,Customer C,2026-09-21,2026-09-28,1800.0,1800.0,0.0,paid
INV006,Campus Office,2026-09-26,2026-10-03,1700.0,1700.0,0.0,paid
INV007,Customer D,2026-09-20,2026-09-27,1200.0,0.0,1200.0,overdue
INV008,Student Club,2026-09-24,2026-10-01,1000.0,0.0,1000.0,overdue
INV009,Customer E,2026-10-01,2026-10-20,800.0,0.0,800.0,pending
"""

SAMPLE_TRANSACTIONS_CSV = """transaction_id,date,type,category,description,amount_rm,invoice_id
T001,2026-09-02,income,Design,Logo design project,1500.0,INV001
T002,2026-09-03,expense,Supplies,Printing paper and ink,450.0,
T003,2026-09-05,income,Printing,Club event banners,2200.0,INV002
T004,2026-09-07,expense,Marketing,Social media ads,200.0,
T005,2026-09-10,income,Design,Business card design,800.0,INV003
T006,2026-09-12,expense,Transport,Delivery and fuel,120.0,
T007,2026-09-15,income,Printing,University merchandise,3000.0,INV004
T008,2026-09-18,expense,Supplies,T-shirts and printing materials,1100.0,
T009,2026-09-21,income,Design,Social media package,1800.0,INV005
T010,2026-09-24,expense,Utilities,Internet and electricity,180.0,
T011,2026-09-26,income,Printing,Flyers and brochures,1700.0,INV006
T012,2026-09-28,expense,Software,Design software subscription,150.0,
"""


def _create_sample_dataset(tmpdir):
    """Create sample CSV files in tmpdir and return the loaded dataset."""
    inv_path = os.path.join(tmpdir, "invoices.csv")
    tx_path = os.path.join(tmpdir, "transactions.csv")
    with open(inv_path, "w") as f:
        f.write(SAMPLE_INVOICES_CSV)
    with open(tx_path, "w") as f:
        f.write(SAMPLE_TRANSACTIONS_CSV)
    return load_dataset(tmpdir)


class TestEnsureOutputDir(unittest.TestCase):
    def test_creates_directory(self):
        tmpdir = tempfile.mkdtemp()
        out = os.path.join(tmpdir, "nested", "output")
        result = ensure_output_dir(out)
        self.assertTrue(os.path.isdir(out))
        self.assertEqual(result, out)


class TestGenerateCSVFile(unittest.TestCase):
    def test_writes_csv_with_header(self):
        tmpdir = tempfile.mkdtemp()
        rows = [{"name": "A", "value": 1}, {"name": "B", "value": 2}]
        path = generate_csv_file(rows, "test.csv", tmpdir)
        self.assertTrue(os.path.isfile(path))
        with open(path, "r") as f:
            content = f.read()
        self.assertIn("name,value", content)
        self.assertIn("A,1", content)
        self.assertIn("B,2", content)

    def test_empty_rows_writes_note(self):
        tmpdir = tempfile.mkdtemp()
        path = generate_csv_file([], "empty.csv", tmpdir)
        self.assertTrue(os.path.isfile(path))


class TestGenerateTextReport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")

    def test_report_file_exists(self):
        result = {
            "intent": "overall_performance",
            "instruction": "test instruction",
            "confidence": "high",
            "method": "rule_based",
            "findings": {"net_profit": {"total_revenue": 11000.0, "total_expenses": 2200.0, "net_profit": 8800.0, "profit_margin_pct": 80.0}},
            "actions": [{"priority": 1, "title": "Test Action", "finding": "test finding", "recommendation": "do X", "rationale": "because Y", "data_source": "test"}],
            "dataset_summary": {"invoice_count": 9, "transaction_count": 12},
            "data_notes": ["This is a note."],
        }
        path = generate_text_report(result, self.outdir)
        self.assertTrue(os.path.isfile(path))
        with open(path, "r") as f:
            content = f.read()
        self.assertIn("RichBuddy", content)
        self.assertIn("test instruction", content)
        self.assertIn("Test Action", content)
        self.assertIn("rule_based", content)
        self.assertIn("This is a note.", content)

    def test_report_filename_contains_intent(self):
        result = {
            "intent": "profit_loss_products",
            "instruction": "test",
            "confidence": "medium",
            "method": "rule_based",
            "findings": {},
            "actions": [],
            "dataset_summary": {},
            "data_notes": [],
        }
        path = generate_text_report(result, self.outdir)
        self.assertIn("profit_loss_products", os.path.basename(path))


class TestRunAnalysisOverallPerformance(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")
        self.dataset = _create_sample_dataset(self.tmpdir)

    def test_returns_result_dict(self):
        result = run_analysis(
            "Analyse my overall business performance",
            self.dataset,
            self.outdir,
        )
        self.assertIsInstance(result, dict)

    def test_intent_is_overall_performance(self):
        result = run_analysis(
            "Analyse my overall business performance",
            self.dataset,
            self.outdir,
        )
        self.assertEqual(result["intent"], "overall_performance")

    def test_findings_contain_net_profit(self):
        result = run_analysis(
            "Analyse my overall business performance",
            self.dataset,
            self.outdir,
        )
        self.assertIn("net_profit", result["findings"])
        np = result["findings"]["net_profit"]
        self.assertAlmostEqual(np["total_revenue"], 11000.0, places=2)
        self.assertAlmostEqual(np["net_profit"], 8800.0, places=2)

    def test_report_file_generated(self):
        result = run_analysis(
            "Analyse my overall business performance",
            self.dataset,
            self.outdir,
        )
        self.assertTrue(os.path.isfile(result["report_path"]))

    def test_csv_files_generated(self):
        result = run_analysis(
            "Analyse my overall business performance",
            self.dataset,
            self.outdir,
        )
        self.assertTrue(len(result["csv_paths"]) > 0)
        for path in result["csv_paths"]:
            self.assertTrue(os.path.isfile(path))


class TestRunAnalysisProfitLoss(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")
        self.dataset = _create_sample_dataset(self.tmpdir)

    def test_intent_is_profit_loss(self):
        result = run_analysis(
            "Which products are making the most profit, and which are losing money?",
            self.dataset,
            self.outdir,
        )
        self.assertEqual(result["intent"], "profit_loss_products")

    def test_findings_contain_profit_by_category(self):
        result = run_analysis(
            "Which products are profitable?",
            self.dataset,
            self.outdir,
        )
        self.assertIn("profit_by_category", result["findings"])

    def test_data_notes_mention_allocation(self):
        result = run_analysis(
            "Which products are profitable?",
            self.dataset,
            self.outdir,
        )
        notes_text = " ".join(result["data_notes"])
        self.assertIn("estimate", notes_text.lower())


class TestRunAnalysisRegional(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")
        self.dataset = _create_sample_dataset(self.tmpdir)

    def test_intent_is_regional(self):
        result = run_analysis(
            "Compare my sales across regions",
            self.dataset,
            self.outdir,
        )
        self.assertEqual(result["intent"], "regional_comparison")

    def test_data_notes_explain_missing_region(self):
        result = run_analysis(
            "Compare my sales across regions",
            self.dataset,
            self.outdir,
        )
        notes_text = " ".join(result["data_notes"])
        self.assertIn("region", notes_text.lower())


class TestRunAnalysisReturns(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")
        self.dataset = _create_sample_dataset(self.tmpdir)

    def test_intent_is_returns(self):
        result = run_analysis(
            "Analyse product returns",
            self.dataset,
            self.outdir,
        )
        self.assertEqual(result["intent"], "returns_analysis")

    def test_data_notes_explain_missing_returns(self):
        result = run_analysis(
            "Analyse product returns",
            self.dataset,
            self.outdir,
        )
        notes_text = " ".join(result["data_notes"])
        self.assertIn("return", notes_text.lower())


class TestRunAnalysisPriorityActions(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")
        self.dataset = _create_sample_dataset(self.tmpdir)

    def test_intent_is_priority(self):
        result = run_analysis(
            "What are the three most important actions I should take?",
            self.dataset,
            self.outdir,
        )
        self.assertEqual(result["intent"], "priority_actions")

    def test_actions_are_generated(self):
        result = run_analysis(
            "What are the three most important actions I should take?",
            self.dataset,
            self.outdir,
        )
        self.assertTrue(len(result["actions"]) > 0)

    def test_actions_are_prioritized(self):
        result = run_analysis(
            "What are the three most important actions I should take?",
            self.dataset,
            self.outdir,
        )
        priorities = [a["priority"] for a in result["actions"]]
        self.assertEqual(priorities, sorted(priorities))

    def test_overdue_action_is_priority_1(self):
        result = run_analysis(
            "What are the three most important actions I should take?",
            self.dataset,
            self.outdir,
        )
        p1 = [a for a in result["actions"] if a["priority"] == 1]
        self.assertTrue(len(p1) > 0)
        self.assertIn("overdue", p1[0]["title"].lower())


class TestRunAnalysisUnknown(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tmpdir, "output")
        self.dataset = _create_sample_dataset(self.tmpdir)

    def test_smart_auto_fallback_handled(self):
        result = run_analysis(
            "What is the weather today?",
            self.dataset,
            self.outdir,
        )
        self.assertEqual(result["intent"], "smart_auto")
        self.assertTrue(len(result["data_notes"]) > 0)
        # Should still generate a report
        self.assertTrue(os.path.isfile(result["report_path"]))


if __name__ == "__main__":
    unittest.main()
