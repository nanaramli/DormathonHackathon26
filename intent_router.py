"""
intent_router.py - Rule-based natural-language intent recognition for RichBuddy.

This module maps free-text user instructions to one of several known analysis
intents using keyword matching.  It is designed to work **without an LLM** --
when no LLM is available, simple rules provide a transparent fallback.

The router is intentionally conservative: if it cannot confidently match an
intent, it returns ``"unknown"`` so the orchestrator can ask the user to
rephrase.
"""

import re
from typing import Any


# ---------------------------------------------------------------------------
# Supported intents
# ---------------------------------------------------------------------------
INTENT_OVERALL_PERFORMANCE = "overall_performance"
INTENT_PROFIT_LOSS_PRODUCTS = "profit_loss_products"
INTENT_REGIONAL_COMPARISON = "regional_comparison"
INTENT_RETURNS_ANALYSIS = "returns_analysis"
INTENT_PRIORITY_ACTIONS = "priority_actions"
INTENT_UNKNOWN = "unknown"

ALL_INTENTS = [
    INTENT_OVERALL_PERFORMANCE,
    INTENT_PROFIT_LOSS_PRODUCTS,
    INTENT_REGIONAL_COMPARISON,
    INTENT_RETURNS_ANALYSIS,
    INTENT_PRIORITY_ACTIONS,
]


# ---------------------------------------------------------------------------
# Keyword rules -- ordered by specificity (most specific first)
# ---------------------------------------------------------------------------
INTENT_RULES: list[dict[str, Any]] = [
    {
        "intent": INTENT_PRIORITY_ACTIONS,
        "keywords": [
            "most important action", "priority action", "what should i do",
            "recommend", "recommendation", "actions i should take",
            "improve my business", "next step", "what to do",
            "top 3 action", "three action", "prioriti",
        ],
        "description": "Prioritised business recommendations and action plan",
    },
    {
        "intent": INTENT_RETURNS_ANALYSIS,
        "keywords": [
            "return", "refund", "product return", "returns analysis",
            "returned", "return rate",
        ],
        "description": "Analysis of product returns and their relationship to sales",
    },
    {
        "intent": INTENT_REGIONAL_COMPARISON,
        "keywords": [
            "region", "compare.*region", "across region", "regional",
            "compare.*location", "by location", "geographic",
            "compare.*area", "across area",
        ],
        "description": "Comparison of sales and profitability across regions",
    },
    {
        "intent": INTENT_PROFIT_LOSS_PRODUCTS,
        "keywords": [
            "profit", "losing money", "loss-making", "loss making",
            "most profit", "profitable", "which product",
            "product.*profit", "product.*loss", "making money",
            "product.*performance", "best product", "worst product",
        ],
        "description": "Identification of profitable and loss-making products/services",
    },
    {
        "intent": INTENT_OVERALL_PERFORMANCE,
        "keywords": [
            "overall", "business performance", "summary", "overview",
            "how is my business", "general", "total",
            "business health", "performance", "how.*doing",
            "analyse my", "analyze my", "report",
        ],
        "description": "Overall business performance analysis",
    },
]


def recognize_intent(instruction: str) -> dict[str, Any]:
    """Map a natural-language instruction to an analysis intent.

    Returns a dict with keys:
        - intent: one of the INTENT_* constants
        - confidence: "high" (keyword exact match) or "low" (partial match)
        - matched_keywords: list of keyword patterns that triggered the match
        - instruction: the original instruction text
        - method: "rule_based" (transparent disclosure)
    """
    text = instruction.lower().strip()

    if not text:
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": "low",
            "matched_keywords": [],
            "instruction": instruction,
            "method": "rule_based",
        }

    matched_intent = INTENT_UNKNOWN
    matched_keywords: list[str] = []
    confidence = "low"

    for rule in INTENT_RULES:
        rule_matches: list[str] = []
        for kw in rule["keywords"]:
            if ".*" in kw:
                # regex keyword
                if re.search(kw, text):
                    rule_matches.append(kw)
            else:
                # literal substring
                if kw in text:
                    rule_matches.append(kw)

        if rule_matches:
            # First matching rule wins (rules are ordered by specificity)
            matched_intent = rule["intent"]
            matched_keywords = rule_matches
            # "high" confidence if 2+ keywords matched or an exact phrase matched
            confidence = "high" if len(rule_matches) >= 2 else "medium"
            break

    return {
        "intent": matched_intent,
        "confidence": confidence,
        "matched_keywords": matched_keywords,
        "instruction": instruction,
        "method": "rule_based",
        "description": _intent_description(matched_intent),
    }


def _intent_description(intent: str) -> str:
    """Human-readable description of what an intent does."""
    for rule in INTENT_RULES:
        if rule["intent"] == intent:
            return rule["description"]
    return "Unknown or unsupported analysis request"


def get_supported_intents() -> list[dict[str, str]]:
    """Return a list of supported intents with descriptions (for help text)."""
    return [
        {"intent": r["intent"], "description": r["description"]}
        for r in INTENT_RULES
    ]
