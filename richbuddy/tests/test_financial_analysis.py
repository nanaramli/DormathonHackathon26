"""
Tests for data_analysis.py and financial_analysis.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_analysis import (
    analyze_revenue_by_category,
    analyze_expense_by_category,
    analyze_monthly_trends,
    analyze_invoice_status,
    analyze_customer_breakdown,
    analyze_category_summary,
)
from financial_analysis import (
    calculate_net_profit,
    calculate_profit_by_category,
    identify_loss_making_categories,
    identify_profitable_categories,
    calculate_outstanding_balance,
    calculate_revenue_concentration,
    calculate_expense_ratio,
)


# Sample data matching the real dataset structure
SAMPLE_TRANSACTIONS = [
    {"transaction_id": "T001", "date": "2026-09-02", "type": "income", "category": "Design", "description": "Logo", "amount_rm": 1500.0, "invoice_id": "INV001"},
    {"transaction_id": "T002", "date": "2026-09-03", "type": "expense", "category": "Supplies", "description": "Paper", "amount_rm": 450.0, "invoice_id": ""},
    {"transaction_id": "T003", "date": "2026-09-05", "type": "income", "category": "Printing", "description": "Banners", "amount_rm": 2200.0, "invoice_id": "INV002"},
    {"transaction_id": "T004", "date": "2026-09-07", "type": "expense", "category": "Marketing", "description": "Ads", "amount_rm": 200.0, "invoice_id": ""},
    {"transaction_id": "T005", "date": "2026-09-10", "type": "income", "category": "Design", "description": "Cards", "amount_rm": 800.0, "invoice_id": "INV003"},
    {"transaction_id": "T006", "date": "2026-09-12", "type": "expense", "category": "Transport", "description": "Fuel", "amount_rm": 120.0, "invoice_id": ""},
    {"transaction_id": "T007", "date": "2026-09-15", "type": "income", "category": "Printing", "description": "Merch", "amount_rm": 3000.0, "invoice_id": "INV004"},
    {"transaction_id": "T008", "date": "2026-09-18", "type": "expense", "category": "Supplies", "description": "T-shirts", "amount_rm": 1100.0, "invoice_id": ""},
    {"transaction_id": "T009", "date": "2026-09-21", "type": "income", "category": "Design", "description": "Social", "amount_rm": 1800.0, "invoice_id": "INV005"},
    {"transaction_id": "T010", "date": "2026-09-24", "type": "expense", "category": "Utilities", "description": "Internet", "amount_rm": 180.0, "invoice_id": ""},
    {"transaction_id": "T011", "date": "2026-09-26", "type": "income", "category": "Printing", "description": "Flyers", "amount_rm": 1700.0, "invoice_id": "INV006"},
    {"transaction_id": "T012", "date": "2026-09-28", "type": "expense", "category": "Software", "description": "Subscription", "amount_rm": 150.0, "invoice_id": ""},
]

SAMPLE_INVOICES = [
    {"invoice_id": "INV001", "customer_name": "Customer A", "issue_date": "2026-09-02", "due_date": "2026-09-09", "invoice_amount_rm": 1500.0, "amount_paid_rm": 1500.0, "balance_due_rm": 0.0, "status": "paid"},
    {"invoice_id": "INV002", "customer_name": "Campus Club", "issue_date": "2026-09-05", "due_date": "2026-09-12", "invoice_amount_rm": 2200.0, "amount_paid_rm": 2200.0, "balance_due_rm": 0.0, "status": "paid"},
    {"invoice_id": "INV003", "customer_name": "Customer B", "issue_date": "2026-09-10", "due_date": "2026-09-17", "invoice_amount_rm": 800.0, "amount_paid_rm": 800.0, "balance_due_rm": 0.0, "status": "paid"},
    {"invoice_id": "INV004", "customer_name": "Student Society", "issue_date": "2026-09-15", "due_date": "2026-09-22", "invoice_amount_rm": 3000.0, "amount_paid_rm": 3000.0, "balance_due_rm": 0.0, "status": "paid"},
    {"invoice_id": "INV005", "customer_name": "Customer C", "issue_date": "2026-09-21", "due_date": "2026-09-28", "invoice_amount_rm": 1800.0, "amount_paid_rm": 1800.0, "balance_due_rm": 0.0, "status": "paid"},
    {"invoice_id": "INV006", "customer_name": "Campus Office", "issue_date": "2026-09-26", "due_date": "2026-10-03", "invoice_amount_rm": 1700.0, "amount_paid_rm": 1700.0, "balance_due_rm": 0.0, "status": "paid"},
    {"invoice_id": "INV007", "customer_name": "Customer D", "issue_date": "2026-09-20", "due_date": "2026-09-27", "invoice_amount_rm": 1200.0, "amount_paid_rm": 0.0, "balance_due_rm": 1200.0, "status": "overdue"},
    {"invoice_id": "INV008", "customer_name": "Student Club", "issue_date": "2026-09-24", "due_date": "2026-10-01", "invoice_amount_rm": 1000.0, "amount_paid_rm": 0.0, "balance_due_rm": 1000.0, "status": "overdue"},
    {"invoice_id": "INV009", "customer_name": "Customer E", "issue_date": "2026-10-01", "due_date": "2026-10-20", "invoice_amount_rm": 800.0, "amount_paid_rm": 0.0, "balance_due_rm": 800.0, "status": "pending"},
]


class TestAnalyzeRevenueByCategory(unittest.TestCase):
    def test_total_revenue(self):
        result = analyze_revenue_by_category(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["total_revenue"], 11000.0, places=2)

    def test_design_revenue(self):
        result = analyze_revenue_by_category(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["by_category"]["Design"], 4100.0, places=2)

    def test_printing_revenue(self):
        result = analyze_revenue_by_category(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["by_category"]["Printing"], 6900.0, places=2)

    def test_categories_list(self):
        result = analyze_revenue_by_category(SAMPLE_TRANSACTIONS)
        self.assertEqual(sorted(result["categories"]), ["Design", "Printing"])


class TestAnalyzeExpenseByCategory(unittest.TestCase):
    def test_total_expense(self):
        result = analyze_expense_by_category(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["total_expense"], 2200.0, places=2)

    def test_supplies_expense(self):
        result = analyze_expense_by_category(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["by_category"]["Supplies"], 1550.0, places=2)

    def test_categories_list(self):
        result = analyze_expense_by_category(SAMPLE_TRANSACTIONS)
        self.assertEqual(
            sorted(result["categories"]),
            ["Marketing", "Software", "Supplies", "Transport", "Utilities"],
        )


class TestAnalyzeMonthlyTrends(unittest.TestCase):
    def test_single_month(self):
        result = analyze_monthly_trends(SAMPLE_TRANSACTIONS)
        self.assertEqual(result["months"], ["2026-09"])

    def test_monthly_income(self):
        result = analyze_monthly_trends(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["income_by_month"]["2026-09"], 11000.0, places=2)

    def test_monthly_expense(self):
        result = analyze_monthly_trends(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["expense_by_month"]["2026-09"], 2200.0, places=2)

    def test_monthly_net(self):
        result = analyze_monthly_trends(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["net_by_month"]["2026-09"], 8800.0, places=2)


class TestAnalyzeInvoiceStatus(unittest.TestCase):
    def test_status_counts(self):
        result = analyze_invoice_status(SAMPLE_INVOICES)
        self.assertEqual(result["by_status"]["paid"], 6)
        self.assertEqual(result["by_status"]["overdue"], 2)
        self.assertEqual(result["by_status"]["pending"], 1)

    def test_total_invoiced(self):
        result = analyze_invoice_status(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["total_invoiced"], 14000.0, places=2)

    def test_total_paid(self):
        result = analyze_invoice_status(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["total_paid"], 11000.0, places=2)

    def test_total_outstanding(self):
        result = analyze_invoice_status(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["total_outstanding"], 3000.0, places=2)


class TestCalculateNetProfit(unittest.TestCase):
    def test_net_profit(self):
        result = calculate_net_profit(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["total_revenue"], 11000.0, places=2)
        self.assertAlmostEqual(result["total_expenses"], 2200.0, places=2)
        self.assertAlmostEqual(result["net_profit"], 8800.0, places=2)

    def test_profit_margin(self):
        result = calculate_net_profit(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["profit_margin_pct"], 80.0, places=1)


class TestCalculateProfitByCategory(unittest.TestCase):
    def test_design_revenue(self):
        result = calculate_profit_by_category(SAMPLE_TRANSACTIONS)
        design = [c for c in result["categories"] if c["category"] == "Design"][0]
        self.assertAlmostEqual(design["revenue"], 4100.0, places=2)

    def test_printing_revenue(self):
        result = calculate_profit_by_category(SAMPLE_TRANSACTIONS)
        printing = [c for c in result["categories"] if c["category"] == "Printing"][0]
        self.assertAlmostEqual(printing["revenue"], 6900.0, places=2)

    def test_design_direct_cost(self):
        result = calculate_profit_by_category(SAMPLE_TRANSACTIONS)
        design = [c for c in result["categories"] if c["category"] == "Design"][0]
        # Software (150) is direct to Design
        self.assertAlmostEqual(design["direct_cost"], 150.0, places=2)

    def test_printing_direct_cost(self):
        result = calculate_profit_by_category(SAMPLE_TRANSACTIONS)
        printing = [c for c in result["categories"] if c["category"] == "Printing"][0]
        # Supplies (1550) + Transport (120) = 1670
        self.assertAlmostEqual(printing["direct_cost"], 1670.0, places=2)

    def test_no_loss_making_categories(self):
        result = calculate_profit_by_category(SAMPLE_TRANSACTIONS)
        losses = identify_loss_making_categories(result)
        self.assertEqual(len(losses), 0)  # Both categories are profitable

    def test_total_profit_matches(self):
        result = calculate_profit_by_category(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["total_profit"], 8800.0, places=2)

    def test_allocation_method_documented(self):
        result = calculate_profit_by_category(SAMPLE_TRANSACTIONS)
        self.assertTrue(result["allocation_method"])
        self.assertIn("estimate", result["allocation_method"].lower())


class TestCalculateOutstandingBalance(unittest.TestCase):
    def test_total_outstanding(self):
        result = calculate_outstanding_balance(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["total_outstanding"], 3000.0, places=2)

    def test_overdue_amount(self):
        result = calculate_outstanding_balance(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["overdue_amount"], 2200.0, places=2)

    def test_pending_amount(self):
        result = calculate_outstanding_balance(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["pending_amount"], 800.0, places=2)

    def test_collection_rate(self):
        result = calculate_outstanding_balance(SAMPLE_INVOICES)
        # 11000 / 14000 * 100 = 78.57... -> 78.6
        self.assertAlmostEqual(result["collection_rate_pct"], 78.6, places=1)

    def test_overdue_invoice_count(self):
        result = calculate_outstanding_balance(SAMPLE_INVOICES)
        self.assertEqual(len(result["overdue_invoices"]), 2)

    def test_pending_invoice_count(self):
        result = calculate_outstanding_balance(SAMPLE_INVOICES)
        self.assertEqual(len(result["pending_invoices"]), 1)


class TestCalculateRevenueConcentration(unittest.TestCase):
    def test_top_category(self):
        result = calculate_revenue_concentration(SAMPLE_TRANSACTIONS)
        self.assertEqual(result["top_category"], "Printing")

    def test_top_category_share(self):
        result = calculate_revenue_concentration(SAMPLE_TRANSACTIONS)
        # 6900 / 11000 * 100 = 62.7...
        self.assertAlmostEqual(result["top_category_share_pct"], 62.7, places=1)

    def test_is_concentrated(self):
        result = calculate_revenue_concentration(SAMPLE_TRANSACTIONS)
        self.assertTrue(result["is_concentrated"])  # 62.7% > 60%


class TestCalculateExpenseRatio(unittest.TestCase):
    def test_expense_ratio(self):
        result = calculate_expense_ratio(SAMPLE_TRANSACTIONS)
        # 2200 / 11000 * 100 = 20.0
        self.assertAlmostEqual(result["expense_ratio_pct"], 20.0, places=1)

    def test_top_expense_category(self):
        result = calculate_expense_ratio(SAMPLE_TRANSACTIONS)
        self.assertEqual(result["top_expense_category"], "Supplies")

    def test_top_expense_amount(self):
        result = calculate_expense_ratio(SAMPLE_TRANSACTIONS)
        self.assertAlmostEqual(result["top_expense_amount"], 1550.0, places=2)


class TestAnalyzeCategorySummary(unittest.TestCase):
    def test_row_count(self):
        rows = analyze_category_summary(SAMPLE_TRANSACTIONS)
        # Design, Printing, Supplies, Marketing, Transport, Utilities, Software
        self.assertEqual(len(rows), 7)

    def test_design_row(self):
        rows = analyze_category_summary(SAMPLE_TRANSACTIONS)
        design = [r for r in rows if r["category"] == "Design"][0]
        self.assertAlmostEqual(design["income_rm"], 4100.0, places=2)
        self.assertAlmostEqual(design["expense_rm"], 0.0, places=2)
        self.assertAlmostEqual(design["net_rm"], 4100.0, places=2)

    def test_supplies_row(self):
        rows = analyze_category_summary(SAMPLE_TRANSACTIONS)
        supplies = [r for r in rows if r["category"] == "Supplies"][0]
        self.assertAlmostEqual(supplies["income_rm"], 0.0, places=2)
        self.assertAlmostEqual(supplies["expense_rm"], 1550.0, places=2)
        self.assertAlmostEqual(supplies["net_rm"], -1550.0, places=2)


class TestAnalyzeCustomerBreakdown(unittest.TestCase):
    def test_customer_count(self):
        result = analyze_customer_breakdown(SAMPLE_INVOICES)
        self.assertEqual(len(result["customers"]), 9)

    def test_customer_a_invoiced(self):
        result = analyze_customer_breakdown(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["invoiced_by_customer"]["Customer A"], 1500.0, places=2)

    def test_customer_d_outstanding(self):
        result = analyze_customer_breakdown(SAMPLE_INVOICES)
        self.assertAlmostEqual(result["outstanding_by_customer"]["Customer D"], 1200.0, places=2)


if __name__ == "__main__":
    unittest.main()
