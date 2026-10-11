"""
intent_router.py - Rule-based natural-language intent recognition for RichBuddy.

This module maps free-text user instructions to one of several known analysis
intents using keyword matching.  It is designed to work **without an LLM** --
when no LLM is available, simple rules provide a transparent fallback.

The router works in two layers:
    1. Try to match one of the 6 specific intents (overall performance,
       profit/loss, regional, returns, priority actions, full review).
    2. If no specific intent matches, fall back to **smart_auto** -- the
       smart_planner decomposes the instruction into individual capabilities
       and builds a custom execution plan.  This means *any* instruction gets
       a meaningful, end-to-end response.
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
INTENT_FULL_BUSINESS_REVIEW = "full_business_review"
INTENT_SMART_AUTO = "smart_auto"
INTENT_UNKNOWN = "unknown"

ALL_INTENTS = [
    INTENT_OVERALL_PERFORMANCE,
    INTENT_PROFIT_LOSS_PRODUCTS,
    INTENT_REGIONAL_COMPARISON,
    INTENT_RETURNS_ANALYSIS,
    INTENT_PRIORITY_ACTIONS,
    INTENT_FULL_BUSINESS_REVIEW,
    INTENT_SMART_AUTO,
]


# ---------------------------------------------------------------------------
# Keyword rules -- ordered by specificity (most specific first)
# ---------------------------------------------------------------------------
INTENT_RULES: list[dict[str, Any]] = [
    {
        "intent": INTENT_FULL_BUSINESS_REVIEW,
        "keywords": [
            "handle my business", "before class", "action pack",
            "handle everything", "full review", "end to end",
            "review my", "reconcile", "draft.*message", "draft.*customer",
            "business action plan", "prepare.*plan",
            "review.*sales.*expenses.*invoices", "review.*latest",
            "haven't paid", "haven.*paid",
            # Malay: semakan penuh, draf mesej pelanggan, belum bayar
            "semakanpenuh", "semakperniagaan", "draf.*mesej", "draf.*pelanggan",
            "rinci", "belum.*bayar", "pelanggan.*tidakbayar",
            "pelan.*tindakan", "urus.*perniagaan", "semua.*benda",
        ],
        "description": "Full autonomous business review: reconcile records, identify issues, draft customer messages, and generate a 30-minute action plan",
    },
    {
        "intent": INTENT_PRIORITY_ACTIONS,
        "keywords": [
            "most important action", "priority action", "what should i do",
            "recommend", "recommendation", "actions i should take",
            "improve my business", "next step", "what to do",
            "top 3 action", "three action", "prioriti",
            # Malay: tindakan keutamaan, apa perlu buat, cadangan
            "tindakankeutamaan", "apa.*perlu.*buat", "cadangan",
            "tindakan.*penting", "ubahtercanggih", "perbaiki.*perniagaan",
            "langkah.*seterusnya", "perlu.*buat",
        ],
        "description": "Prioritised business recommendations and action plan",
    },
    {
        "intent": INTENT_RETURNS_ANALYSIS,
        "keywords": [
            "return", "refund", "product return", "returns analysis",
            "returned", "return rate",
            # Malay: pemulangan, refund, kadar pemulangan
            "pemulangan", "pulangkan", "kadar.*pemulangan",
            "pemulangan.*produk",
        ],
        "description": "Analysis of product returns and their relationship to sales",
    },
    {
        "intent": INTENT_REGIONAL_COMPARISON,
        "keywords": [
            "region", "compare.*region", "across region", "regional",
            "compare.*location", "by location", "geographic",
            "compare.*area", "across area",
            # Malay: kawasan, banding kawasan, negeri, lokasi
            "kawasan", "banding.*kawasan", "banding.*negeri", "negeri",
            "banding.*lokasi", "geografi", "banding.*area", "setiap.*kawasan",
            "perbandingan.*kawasan", "perbandingan.*negeri",
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
            # Malay: untung, rugi, produk untung, produk rugi
            "untung", "rugi", "produk.*untung", "produk.*rugi",
            "paling.*untung", "produk.*mana", "prestasi.*produk",
            "produk.*terbaik", "produk.*teruk", "buat.*duit",
            "untung.*rugi",
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
            # Malay: keseluruhan, prestasi perniagaan, ringkasan, laporan
            "keseluruhan", "prestasi.*perniagaan", "ringkasan",
            "gambaran.*keseluruhan", "macam.*mana.*perniagaan",
            "laporan", "analisa", "keseluruhan.*perniagaan",
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
        - description: human-readable description
    """
    text = instruction.lower().strip()

    if not text:
        return {
            "intent": INTENT_SMART_AUTO,
            "confidence": "low",
            "matched_keywords": [],
            "instruction": instruction,
            "method": "rule_based",
            "description": "Empty instruction -- smart planner will default to full review",
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

    # If no specific intent matched, use smart_auto (never return "unknown")
    if matched_intent == INTENT_UNKNOWN:
        return {
            "intent": INTENT_SMART_AUTO,
            "confidence": "low",
            "matched_keywords": [],
            "instruction": instruction,
            "method": "rule_based",
            "description": (
                "Smart auto-detection: RichBuddy will analyse your instruction, "
                "determine the goal, and execute the relevant analyses end-to-end"
            ),
        }

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
    if intent == INTENT_SMART_AUTO:
        return "Smart auto-detection: determine the goal from the instruction and execute end-to-end"
    return "Unknown or unsupported analysis request"


def get_supported_intents() -> list[dict[str, str]]:
    """Return a list of supported intents with descriptions (for help text)."""
    result = [
        {"intent": r["intent"], "description": r["description"]}
        for r in INTENT_RULES
    ]
    result.append({
        "intent": INTENT_SMART_AUTO,
        "description": "Smart auto-detection: any instruction gets analysed and executed end-to-end",
    })
    return result
