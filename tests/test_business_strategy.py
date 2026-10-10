"""
Tests for business_strategy.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_strategy import prioritize_actions


# Findings that simulate a real analysis output
SAMPLE_FINDINGS = {
    "net_profit": {
        "total_revenue": 11000.0,
        "total_expenses": 2200.0,
        "net_profit": 8800.0,
        "profit_margin_pct": 80.0,
    },
    "profit_by_category": {
        "categories": [
            {
                "category": "Design",
                "revenue": 4100.0,
                "direct_cost": 150.0,
                "overhead_cost": 141.64,
                "total_cost": 291.64,
                "profit": 3808.36,
                "profit_margin_pct": 92.9,
                "is_loss_making": False,
            },
            {
                "category": "Printing",
                "revenue": 6900.0,
                "direct_cost": 1670.0,
                "overhead_cost": 238.36,
                "total_cost": 1908.36,
                "profit": 4991.64,
                "profit_margin_pct": 72.3,
                "is_loss_making": False,
            },
        ],
        "allocation_method": "Direct expenses are assigned to mapped income category.",
        "total_revenue": 11000.0,
        "total_cost": 2200.0,
        "total_profit": 8800.0,
    },
    "outstanding": {
        "total_outstanding": 3000.0,
        "overdue_amount": 2200.0,
        "pending_amount": 800.0,
        "overdue_invoices": [
            {"invoice_id": "INV007", "customer_name": "Customer D", "balance_due_rm": 1200.0},
            {"invoice_id": "INV008", "customer_name": "Student Club", "balance_due_rm": 1000.0},
        ],
        "pending_invoices": [
            {"invoice_id": "INV009", "customer_name": "Customer E", "balance_due_rm": 800.0},
        ],
        "collection_rate_pct": 78.6,
    },
    "expense_ratio": {
        "expense_ratio_pct": 20.0,
        "top_expense_categories": [
            {"category": "Supplies", "amount": 1550.0},
            {"category": "Marketing", "amount": 200.0},
        ],
        "top_expense_category": "Supplies",
        "top_expense_amount": 1550.0,
    },
    "revenue_concentration": {
        "category_shares": {"Design": 37.3, "Printing": 62.7},
        "top_category": "Printing",
        "top_category_share_pct": 62.7,
        "is_concentrated": True,
    },
}


class TestPrioritizeActions(unittest.TestCase):
    def test_returns_list(self):
        actions = prioritize_actions(SAMPLE_FINDINGS)
        self.assertIsInstance(actions, list)

    def test_actions_sorted_by_priority(self):
        actions = prioritize_actions(SAMPLE_FINDINGS)
        priorities = [a["priority"] for a in actions]
        self.assertEqual(priorities, sorted(priorities))

    def test_overdue_action_is_priority_1(self):
        actions = prioritize_actions(SAMPLE_FINDINGS)
        priority1 = [a for a in actions if a["priority"] == 1]
        self.assertTrue(len(priority1) > 0)
        self.assertIn("overdue", priority1[0]["title"].lower())

    def test_each_action_has_required_fields(self):
        actions = prioritize_actions(SAMPLE_FINDINGS)
        for a in actions:
            self.assertIn("priority", a)
            self.assertIn("title", a)
            self.assertIn("finding", a)
            self.assertIn("recommendation", a)
            self.assertIn("rationale", a)
            self.assertIn("data_source", a)

    def test_max_5_actions(self):
        actions = prioritize_actions(SAMPLE_FINDINGS)
        self.assertLessEqual(len(actions), 5)

    def test_empty_findings_returns_empty(self):
        actions = prioritize_actions({})
        self.assertEqual(len(actions), 0)

    def test_loss_making_action_when_losses_exist(self):
        findings = dict(SAMPLE_FINDINGS)
        findings["profit_by_category"] = {
            "categories": [
                {"category": "Bad Product", "revenue": 100.0, "direct_cost": 0,
                 "overhead_cost": 0, "total_cost": 0, "profit": -50.0,
                 "profit_margin_pct": -50.0, "is_loss_making": True},
            ],
            "allocation_method": "test",
            "total_revenue": 100.0,
            "total_cost": 0,
            "total_profit": -50.0,
        }
        actions = prioritize_actions(findings)
        loss_action = [a for a in actions if "loss" in a["title"].lower()]
        self.assertTrue(len(loss_action) > 0)


if __name__ == "__main__":
    unittest.main()
