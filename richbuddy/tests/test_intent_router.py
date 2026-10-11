"""
Tests for intent_router.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intent_router import (
    recognize_intent,
    INTENT_OVERALL_PERFORMANCE,
    INTENT_PROFIT_LOSS_PRODUCTS,
    INTENT_REGIONAL_COMPARISON,
    INTENT_RETURNS_ANALYSIS,
    INTENT_PRIORITY_ACTIONS,
    INTENT_UNKNOWN,
    get_supported_intents,
)


class TestRecognizeIntent(unittest.TestCase):

    def test_overall_performance(self):
        result = recognize_intent("Analyse my overall business performance.")
        self.assertEqual(result["intent"], INTENT_OVERALL_PERFORMANCE)
        self.assertEqual(result["method"], "rule_based")

    def test_overall_performance_variant(self):
        result = recognize_intent("Give me a summary of how my business is doing")
        self.assertEqual(result["intent"], INTENT_OVERALL_PERFORMANCE)

    def test_profit_loss_products(self):
        result = recognize_intent("Which products are making the most profit, and which are losing money?")
        self.assertEqual(result["intent"], INTENT_PROFIT_LOSS_PRODUCTS)

    def test_profit_loss_variant(self):
        result = recognize_intent("What are my most profitable products?")
        self.assertEqual(result["intent"], INTENT_PROFIT_LOSS_PRODUCTS)

    def test_regional_comparison(self):
        result = recognize_intent("Compare my sales and profitability across regions")
        self.assertEqual(result["intent"], INTENT_REGIONAL_COMPARISON)

    def test_regional_variant(self):
        result = recognize_intent("Show me regional performance")
        self.assertEqual(result["intent"], INTENT_REGIONAL_COMPARISON)

    def test_returns_analysis(self):
        result = recognize_intent("Analyse product returns and explain how they relate to sales.")
        self.assertEqual(result["intent"], INTENT_RETURNS_ANALYSIS)

    def test_returns_variant(self):
        result = recognize_intent("What is my refund rate?")
        self.assertEqual(result["intent"], INTENT_RETURNS_ANALYSIS)

    def test_priority_actions(self):
        result = recognize_intent("What are the three most important actions I should take to improve my business?")
        self.assertEqual(result["intent"], INTENT_PRIORITY_ACTIONS)

    def test_priority_actions_variant(self):
        result = recognize_intent("Give me recommendations to improve my business")
        self.assertEqual(result["intent"], INTENT_PRIORITY_ACTIONS)

    def test_unknown_intent(self):
        result = recognize_intent("What is the weather today?")
        self.assertEqual(result["intent"], INTENT_UNKNOWN)

    def test_empty_instruction(self):
        result = recognize_intent("")
        self.assertEqual(result["intent"], INTENT_UNKNOWN)

    def test_method_is_rule_based(self):
        result = recognize_intent("overall performance")
        self.assertEqual(result["method"], "rule_based")

    def test_confidence_levels(self):
        # Multiple keywords -> higher confidence
        result = recognize_intent("most important actions I should take to improve my business")
        self.assertEqual(result["intent"], INTENT_PRIORITY_ACTIONS)
        self.assertIn(result["confidence"], ["high", "medium"])


class TestGetSupportedIntents(unittest.TestCase):

    def test_returns_all_intents(self):
        intents = get_supported_intents()
        intent_names = [i["intent"] for i in intents]
        self.assertIn(INTENT_OVERALL_PERFORMANCE, intent_names)
        self.assertIn(INTENT_PROFIT_LOSS_PRODUCTS, intent_names)
        self.assertIn(INTENT_REGIONAL_COMPARISON, intent_names)
        self.assertIn(INTENT_RETURNS_ANALYSIS, intent_names)
        self.assertIn(INTENT_PRIORITY_ACTIONS, intent_names)

    def test_each_has_description(self):
        intents = get_supported_intents()
        for item in intents:
            self.assertTrue(item["description"])


if __name__ == "__main__":
    unittest.main()
