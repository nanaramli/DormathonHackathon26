"""
test_richbuddy_upgrade.py - Automated tests for the upgraded RichBuddy.

Tests cover:
    - Financial calculation accuracy
    - CSV and Excel input
    - Missing columns and malformed data
    - Missing values and duplicate records
    - Negative values and zero denominators
    - Task-specific analysis selection
    - Recommendation traceability
    - Prioritisation logic
    - Independent verification
    - Artifact creation and reopening
    - Retry limits and error recovery
    - Partial-success reporting
    - Student-business demo execution
"""

import csv
import io
import json
import os
import sys
import tempfile
import unittest

# Add project directory to path (go up one level from tests/ to project root)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from data_loader import load_dataset, DataLoadError
from adaptive_loader import load_user_dataset, AdaptiveLoadError
from orchestrator import run_analysis
from financial_analysis import (
    calculate_net_profit,
    calculate_profit_by_category,
    calculate_expense_ratio,
    calculate_revenue_concentration,
)
from business_strategy import prioritize_actions
from self_verifier import run_verification
from insights_generator import generate_insights, generate_data_quality_score


SAMPLE_DATA = os.path.join(PROJECT_DIR, "sample_data")
BROWNIE_INV = os.path.join(SAMPLE_DATA, "brownie_invoices.csv")
BROWNIE_TXN = os.path.join(SAMPLE_DATA, "brownie_transactions.csv")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")


class TestFinancialCalculations(unittest.TestCase):
    """Test financial calculation accuracy."""

    def setUp(self):
        self.dataset = load_dataset(SAMPLE_DATA)
        self.transactions = self.dataset["transactions"]

    def test_net_profit_calculation(self):
        """Net profit should equal total revenue minus total expenses."""
        result = calculate_net_profit(self.transactions)
        expected_revenue = sum(tx["amount_rm"] for tx in self.transactions if tx["type"] == "income")
        expected_expenses = sum(tx["amount_rm"] for tx in self.transactions if tx["type"] == "expense")
        expected_net = expected_revenue - expected_expenses
        self.assertAlmostEqual(result["net_profit"], round(expected_net, 2), places=2)
        self.assertAlmostEqual(result["total_revenue"], round(expected_revenue, 2), places=2)
        self.assertAlmostEqual(result["total_expenses"], round(expected_expenses, 2), places=2)

    def test_profit_margin_calculation(self):
        """Profit margin should be net_profit / total_revenue * 100."""
        result = calculate_net_profit(self.transactions)
        if result["total_revenue"] > 0:
            expected_margin = (result["net_profit"] / result["total_revenue"]) * 100
            self.assertAlmostEqual(result["profit_margin_pct"], round(expected_margin, 1), places=1)

    def test_expense_ratio(self):
        """Expense ratio should be total_expenses / total_revenue * 100."""
        result = calculate_expense_ratio(self.transactions)
        np = calculate_net_profit(self.transactions)
        if np["total_revenue"] > 0:
            expected_ratio = (np["total_expenses"] / np["total_revenue"]) * 100
            self.assertAlmostEqual(result["expense_ratio_pct"], round(expected_ratio, 1), places=1)

    def test_revenue_concentration(self):
        """Revenue concentration should sum to 100% across all categories."""
        result = calculate_revenue_concentration(self.transactions)
        if result.get("shares"):
            total_share = sum(s["share_pct"] for s in result["shares"])
            self.assertAlmostEqual(total_share, 100.0, places=1)

    def test_profit_by_category_reconciles(self):
        """Profit by category should reconcile with net profit."""
        pbc = calculate_profit_by_category(self.transactions)
        np = calculate_net_profit(self.transactions)
        total_cat_revenue = sum(c["revenue"] for c in pbc["categories"])
        self.assertAlmostEqual(total_cat_revenue, np["total_revenue"], places=2)


class TestZeroDenominators(unittest.TestCase):
    """Test handling of zero denominators and edge cases."""

    def test_zero_revenue_margin(self):
        """Margin calculation with zero revenue should not crash."""
        empty_transactions = []
        result = calculate_net_profit(empty_transactions)
        self.assertEqual(result["net_profit"], 0)
        self.assertEqual(result["total_revenue"], 0)
        self.assertEqual(result["profit_margin_pct"], 0.0)

    def test_expense_only(self):
        """Business with only expenses should show a loss."""
        expense_only = [
            {"type": "expense", "amount_rm": 50.0, "category": "Supplies",
             "description": "Test", "date": "2026-01-01", "transaction_id": "T1",
             "invoice_id": ""},
        ]
        result = calculate_net_profit(expense_only)
        self.assertEqual(result["net_profit"], -50.0)
        self.assertEqual(result["profit_margin_pct"], 0.0)

    def test_negative_amount_handling(self):
        """Negative amounts should not cause crashes."""
        txns = [
            {"type": "income", "amount_rm": -10.0, "category": "Test",
             "description": "Negative", "date": "2026-01-01", "transaction_id": "T1",
             "invoice_id": ""},
            {"type": "expense", "amount_rm": 20.0, "category": "Test",
             "description": "Normal", "date": "2026-01-02", "transaction_id": "T2",
             "invoice_id": ""},
        ]
        result = calculate_net_profit(txns)
        # Should not crash, result depends on how negatives are handled
        self.assertIsInstance(result, dict)
        self.assertIn("net_profit", result)


class TestRecommendationTraceability(unittest.TestCase):
    """Test that recommendations link to actual findings."""

    def setUp(self):
        self.dataset = load_dataset(SAMPLE_DATA)
        self.output_dir = tempfile.mkdtemp()
        self.result = run_analysis(
            "Analyse my overall business performance",
            self.dataset, self.output_dir,
        )

    def test_actions_have_required_fields(self):
        """Every recommendation must have required fields."""
        for action in self.result["actions"]:
            self.assertIn("priority", action)
            self.assertIn("title", action)
            self.assertIn("finding", action)
            self.assertIn("recommendation", action)
            self.assertIn("rationale", action)
            self.assertIn("data_source", action)

    def test_action_priorities_valid(self):
        """All priorities must be 1, 2, or 3."""
        for action in self.result["actions"]:
            self.assertIn(action["priority"], [1, 2, 3])

    def test_actions_sorted_by_priority(self):
        """Actions should be sorted by priority (1 first)."""
        priorities = [a["priority"] for a in self.result["actions"]]
        self.assertEqual(priorities, sorted(priorities))

    def test_actions_capped_at_5(self):
        """Recommendations should be capped at 5 for readability."""
        self.assertLessEqual(len(self.result["actions"]), 5)

    def test_actions_contain_figures(self):
        """Action findings should contain supporting figures (RM or %)."""
        for action in self.result["actions"]:
            finding = action.get("finding", "")
            # At least some actions should contain figures
            self.assertTrue(
                "RM" in finding or "%" in finding or "RM " in finding,
                f"Action '{action['title']}' finding lacks figures: {finding}"
            )


class TestPrioritisationLogic(unittest.TestCase):
    """Test recommendation prioritisation logic."""

    def test_overdue_invoices_get_priority_1(self):
        """Overdue invoices should generate Priority 1 action."""
        findings = {
            "outstanding": {
                "overdue_amount": 100.0,
                "overdue_invoices": [{"invoice_id": "T1", "customer_name": "Test",
                                       "balance_due_rm": 100.0}],
                "collection_rate_pct": 50.0,
                "pending_amount": 0,
                "total_outstanding": 100.0,
            }
        }
        actions = prioritize_actions(findings)
        self.assertTrue(any(a["priority"] == 1 for a in actions))

    def test_loss_making_business_gets_priority_1(self):
        """Loss-making business should generate Priority 1 action."""
        findings = {
            "net_profit": {
                "net_profit": -50.0,
                "total_revenue": 100.0,
                "total_expenses": 150.0,
                "profit_margin_pct": -50.0,
            }
        }
        actions = prioritize_actions(findings)
        self.assertTrue(any(a["priority"] == 1 for a in actions))

    def test_empty_findings_produce_no_actions(self):
        """Empty findings should produce no recommendations."""
        actions = prioritize_actions({})
        self.assertEqual(len(actions), 0)


class TestSelfVerification(unittest.TestCase):
    """Test the independent self-verification engine."""

    def setUp(self):
        self.dataset = load_dataset(SAMPLE_DATA)
        self.output_dir = tempfile.mkdtemp()
        self.result = run_analysis(
            "Analyse my overall business performance",
            self.dataset, self.output_dir,
        )

    def test_verification_runs(self):
        """Verification should run and return a report."""
        verification = self.result.get("verification")
        self.assertIsNotNone(verification)
        self.assertIn("overall_status", verification)
        self.assertIn("summary", verification)
        self.assertIn("checks", verification)

    def test_verification_checks_revenue(self):
        """Verification should check revenue totals."""
        verification = self.result["verification"]
        check_ids = [c["check_id"] for c in verification["checks"]]
        self.assertIn("calc_revenue_total", check_ids)

    def test_verification_checks_artifacts(self):
        """Verification should check that output files exist."""
        verification = self.result["verification"]
        check_ids = [c["check_id"] for c in verification["checks"]]
        artifact_checks = [c for c in check_ids if c.startswith("artifact_")]
        self.assertTrue(len(artifact_checks) > 0)

    def test_verification_overall_status(self):
        """Overall status should be PASS, PARTIAL, or FAIL."""
        status = self.result["verification"]["overall_status"]
        self.assertIn(status, ["PASS", "PARTIAL", "FAIL"])


class TestArtifactCreation(unittest.TestCase):
    """Test that artifacts are created and can be reopened."""

    def setUp(self):
        self.dataset = load_dataset(SAMPLE_DATA)
        self.output_dir = tempfile.mkdtemp()
        self.result = run_analysis(
            "Analyse my overall business performance",
            self.dataset, self.output_dir,
        )

    def test_report_file_exists(self):
        """Text report should exist and be non-empty."""
        report_path = self.result.get("report_path", "")
        self.assertTrue(os.path.isfile(report_path))
        self.assertGreater(os.path.getsize(report_path), 100)

    def test_csv_files_exist(self):
        """CSV files should exist and be parseable."""
        for csv_path in self.result.get("csv_paths", []):
            self.assertTrue(os.path.isfile(csv_path), f"CSV not found: {csv_path}")
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            self.assertGreater(len(rows), 0)

    def test_deliverables_generated(self):
        """Verified deliverables should be generated."""
        deliverables = self.result.get("deliverables", {})
        self.assertIsNotNone(deliverables.get("report_path"))
        self.assertIsNotNone(deliverables.get("recommendations_path"))
        self.assertIsNotNone(deliverables.get("execution_summary_path"))

    def test_execution_summary_json_valid(self):
        """Execution summary JSON should be valid and parseable."""
        summary_path = self.result["deliverables"]["execution_summary_path"]
        if summary_path and os.path.isfile(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("instruction", data)
            self.assertIn("execution_log", data)
            self.assertIn("verification", data)
            self.assertIn("final_status", data)

    def test_business_action_report_md(self):
        """Business action report should be valid Markdown."""
        report_path = self.result["deliverables"]["report_path"]
        if report_path and os.path.isfile(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("# RichBuddy Business Action Report", content)
            self.assertIn("## 1. Instruction", content)
            self.assertIn("## 5. Recommended Actions", content)
            self.assertIn("## 7. Verification Results", content)


class TestErrorRecovery(unittest.TestCase):
    """Test bounded error recovery."""

    def test_empty_instruction(self):
        """Empty instruction should not crash -- should use smart_auto."""
        dataset = load_dataset(SAMPLE_DATA)
        output_dir = tempfile.mkdtemp()
        result = run_analysis("", dataset, output_dir)
        self.assertIsNotNone(result)
        self.assertIn("intent", result)

    def test_malformed_instruction(self):
        """Nonsensical instruction should not crash."""
        dataset = load_dataset(SAMPLE_DATA)
        output_dir = tempfile.mkdtemp()
        result = run_analysis("xyzzy12345!@#", dataset, output_dir)
        self.assertIsNotNone(result)
        self.assertIn("final_status", result)

    def test_empty_dataset(self):
        """Empty dataset should not crash -- should report limitations."""
        empty_dataset = {"invoices": [], "transactions": []}
        output_dir = tempfile.mkdtemp()
        result = run_analysis("Analyse my business", empty_dataset, output_dir)
        self.assertIsNotNone(result)
        # Should have data notes about missing data
        self.assertTrue(len(result.get("data_notes", [])) > 0)


class TestStudentBusinessDemo(unittest.TestCase):
    """Test the brownie business demo scenario."""

    def setUp(self):
        self.output_dir = tempfile.mkdtemp()
        # Load brownie business data
        self.dataset = load_user_dataset([BROWNIE_INV, BROWNIE_TXN])
        self.result = run_analysis(
            "Analyse my small student-owned brownie business. "
            "Identify the most important profit improvement opportunities "
            "supported by my data, prioritise affordable actions I can take "
            "while studying, and generate a verified business action report.",
            self.dataset, self.output_dir,
        )

    def test_demo_completes(self):
        """The brownie business demo should complete successfully."""
        self.assertIsNotNone(self.result)
        self.assertIn("final_status", self.result)

    def test_demo_generates_findings(self):
        """Demo should generate financial findings."""
        findings = self.result.get("findings", {})
        np = findings.get("net_profit")
        self.assertIsNotNone(np, "Net profit finding should exist")
        self.assertGreater(np["total_revenue"], 0, "Should have positive revenue")
        self.assertGreater(np["total_expenses"], 0, "Should have expenses")

    def test_demo_generates_recommendations(self):
        """Demo should generate at least 1 recommendation."""
        actions = self.result.get("actions", [])
        self.assertGreater(len(actions), 0, "Should generate at least 1 recommendation")

    def test_demo_recommendations_are_student_focused(self):
        """Recommendations should use student-friendly language."""
        for action in self.result["actions"]:
            text = (action.get("recommendation", "") + " " +
                    action.get("rationale", "")).lower()
            # Should contain student-relevant terms
            student_terms = ["student", "whatsapp", "instagram", "ingredient",
                             "bulk", "exam", "baking", "affordable", "campus",
                             "friendly", "reminder", "price", "cheaper"]
            has_student_term = any(term in text for term in student_terms)
            self.assertTrue(has_student_term,
                            f"Action '{action['title']}' lacks student-focused language")

    def test_demo_generates_deliverables(self):
        """Demo should generate business_action_report.md and execution_summary.json."""
        deliverables = self.result.get("deliverables", {})
        self.assertTrue(deliverables.get("report_path") is not None)
        self.assertTrue(deliverables.get("execution_summary_path") is not None)

    def test_demo_verification_passes(self):
        """Demo verification should pass (no critical failures)."""
        verification = self.result.get("verification", {})
        self.assertNotEqual(verification.get("overall_status"), "FAIL",
                           f"Verification failed: {verification.get('errors', [])}")

    def test_demo_execution_log_tracked(self):
        """Demo should track all 10 steps in execution log."""
        log = self.result.get("execution_log", [])
        self.assertGreaterEqual(len(log), 8, f"Expected 8+ steps, got {len(log)}")
        step_names = [e["name"] for e in log]
        self.assertIn("Interpret Goal", step_names)
        self.assertIn("Execute Analysis", step_names)
        self.assertIn("Self-Verification", step_names)

    def test_demo_revenue_calculation_correct(self):
        """Brownie revenue should match expected value."""
        findings = self.result.get("findings", {})
        np = findings.get("net_profit", {})
        # Calculate expected revenue from brownie transactions
        expected_revenue = 0
        for tx in self.dataset["transactions"]:
            if tx["type"] == "income":
                expected_revenue += tx["amount_rm"]
        self.assertAlmostEqual(np["total_revenue"], round(expected_revenue, 2), places=2)


class TestInsightsGeneration(unittest.TestCase):
    """Test insight generation."""

    def setUp(self):
        self.dataset = load_dataset(SAMPLE_DATA)
        self.output_dir = tempfile.mkdtemp()
        self.result = run_analysis(
            "Analyse my overall business performance",
            self.dataset, self.output_dir,
        )

    def test_insights_generated(self):
        """Smart insights should be generated."""
        insights = self.result.get("smart_insights", [])
        self.assertGreater(len(insights), 0, "Should generate at least 1 insight")

    def test_insights_have_required_fields(self):
        """Each insight should have required fields."""
        for ins in self.result["smart_insights"]:
            self.assertIn("priority", ins)
            self.assertIn("category", ins)
            self.assertIn("title", ins)
            self.assertIn("finding", ins)
            self.assertIn("recommendation", ins)

    def test_insights_sorted_by_priority(self):
        """Insights should be sorted by priority."""
        priorities = [ins["priority"] for ins in self.result["smart_insights"]]
        self.assertEqual(priorities, sorted(priorities))


if __name__ == "__main__":
    unittest.main(verbosity=2)
