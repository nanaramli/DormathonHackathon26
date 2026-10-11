"""
smart_planner.py - Goal determination and dynamic execution planning.

This module analyses a free-text user instruction and determines:
    1. What the user wants (the goal)
    2. Which analyses are relevant
    3. Whether to reconcile records, draft messages, build an action plan
    4. A human-readable summary of the determined plan

Unlike the intent_router (which maps to one of 6 fixed intents), the smart
planner decomposes the instruction into individual *capabilities* and builds
a custom execution plan.  This means any prompt -- even one that doesn't
match any predefined intent -- gets a meaningful, end-to-end response.

Design principles:
    - Every instruction gets a plan (never returns "unknown")
    - Vague instructions default to "run everything" (full review)
    - Specific instructions only run what's relevant (fast, focused)
    - The plan is transparent -- the user can see what was determined
"""

import re
from typing import Any


# ---------------------------------------------------------------------------
# Capability definitions
# ---------------------------------------------------------------------------
# Each capability has:
#   - keywords: patterns to match in the instruction (literal or regex)
#   - description: what this capability does
#   - always_if_vague: if True, included when the instruction is vague/unmatched

CAPABILITIES: list[dict[str, Any]] = [
    {
        "id": "financial_overview",
        "keywords": [
            "sale", "revenue", "expense", "cost", "profit", "money",
            "income", "spending", "budget", "financial", "performance",
            "health", "how am i", "how.*doing", "overall", "summary",
            "overview", "total", "earn", "burn", "cash flow", "cashflow",
            "margin", "bottom line", "p&l", "profit and loss",
            # Malay: jualan, perbelanjaan, untung, duit, pendapatan, kos, prestasi
            "jualan", "perbelanjaan", "untung", "duit", "pendapatan",
            "kos", "prestasi", "keseluruhan", "ringkasan", "aliran.*tunai",
            "jumlah.*keseluruhan",
        ],
        "description": "Revenue, expenses, profit margins, and cash flow overview",
        "always_if_vague": True,
    },
    {
        "id": "invoice_status",
        "keywords": [
            "invoice", "unpaid", "overdue", "paid", "haven.*paid",
            "balance", "outstanding", "payment", "collect", "owe",
            "owed", "who hasn", "who has not", "chase", "follow up",
            "followup", "settle", "pending", "partial",
            # Malay: invois, tertunggak, berbayar, baki, bayaran, menunggu
            "invois", "tertunggak", "berbayar", "baki", "bayaran",
            "menunggu", "belum.*bayar", "kejar.*bayaran",
        ],
        "description": "Invoice payment status and outstanding balances",
        "always_if_vague": True,
    },
    {
        "id": "profitability",
        "keywords": [
            "profit", "profitable", "loss", "losing money", "loss-making",
            "margin", "which product", "which service", "best product",
            "worst product", "making money", "product.*performance",
            "category.*profit", "most profitable", "least profitable",
            # Malay: untung, rugi, produk untung, produk rugi
            "untung", "rugi", "produk.*untung", "produk.*rugi",
            "paling.*untung", "produk.*mana", "prestasi.*produk",
            "buat.*duit",
        ],
        "description": "Which products/services make or lose money",
        "always_if_vague": True,
    },
    {
        "id": "regional",
        "keywords": [
            "region", "area", "location", "geographic", "where",
            "compare.*region", "across region", "by location",
            "territory", "zone", "branch",
            # Malay: kawasan, negeri, banding kawasan, lokasi, cawangan
            "kawasan", "negeri", "banding.*kawasan", "banding.*negeri",
            "lokasi", "cawangan", "setiap.*kawasan", "perbandingan",
        ],
        "description": "Sales and profitability across regions",
        "always_if_vague": False,
    },
    {
        "id": "returns",
        "keywords": [
            "return", "refund", "product return", "returns analysis",
            "returned", "return rate", "chargeback", "rma",
            # Malay: pemulangan, refund, pulangkan
            "pemulangan", "pulangkan", "kadar.*pemulangan",
        ],
        "description": "Product returns and refund analysis",
        "always_if_vague": False,
    },
    {
        "id": "reconciliation",
        "keywords": [
            "reconcile", "reconciliation", "match", "cross-check",
            "cross check", "verify", "check.*record", "accurate",
            "correct", "consistent", "missing", "discrepanc",
            "integrity", "complete", "all.*there", "everything.*match",
            # Malay: rinci, semak, betul, tepat, integriti
            "rinci", "semak.*rekod", "betul", "tepat", "integriti",
            "padan", "cException", "tengok.*betul",
        ],
        "description": "Cross-check invoices against transactions for data integrity",
        "always_if_vague": True,
    },
    {
        "id": "customer_messages",
        "keywords": [
            "message", "follow up", "followup", "contact", "remind",
            "chase", "email", "whatsapp", "draft", "write.*message",
            "send.*message", "tell.*customer", "message.*customer",
            "template", "communication", "reach out", "notify",
            "reminder", "follow-up",
            # Malay: mesej, hubungi, peringatkan, draf, kejar
            "mesej", "hubungi", "peringatkan", "draf.*mesej",
            "kejar.*pelanggan", "maklum.*pelanggan",
        ],
        "description": "Draft customer follow-up messages (WhatsApp/Email, ready to send)",
        "always_if_vague": True,
    },
    {
        "id": "action_plan",
        "keywords": [
            "plan", "action", "priority", "urgent", "task", "todo",
            "to-do", "what should i do", "next step", "help me",
            "advise", "advice", "recommend", "recommendation",
            "improve", "suggestion", "what.*do", "guide", "checklist",
            "steps", "strategy", "roadmap", "before class",
            "handle.*business", "take care", "manage",
            # Malay: pelan, tindakan, keutamaan, cadangan, langkah
            "pelan", "tindakan", "keutamaan", "cadangan",
            "langkah.*seterusnya", "apa.*perlu.*buat",
            "perbaiki.*perniagaan", "ubat.*perniagaan",
        ],
        "description": "Prioritized action plan with time estimates",
        "always_if_vague": True,
    },
    {
        "id": "cost_optimization",
        "keywords": [
            "reduce cost", "save money", "cheaper", "optimi", "cut cost",
            "lower expense", "reduce expense", "spend less", "cost sav",
            "efficiency", "streamline", "trim",
            # Malay: kurang kos, jimat, murah, kurang perbelanjaan
            "kurang.*kos", "jimat", "murah", "kurang.*perbelanjaan",
            "cekap", "penjimatan",
        ],
        "description": "Identify cost-saving opportunities",
        "always_if_vague": False,
    },
    {
        "id": "growth",
        "keywords": [
            "grow", "increase revenue", "more sales", "expand",
            "scale", "diversif", "new customer", "market",
            "opportunity", "potential", "upsell", "cross-sell",
            "acquire",
            # Malay: tumbuh, tambah jualan, kembang, pelanggan baru
            "tumbuh", "tambah.*jualan", "kembang", "pelanggan.*baru",
            "peluang", "potensi",
        ],
        "description": "Growth opportunities and revenue expansion ideas",
        "always_if_vague": False,
    },
    {
        "id": "customer_breakdown",
        "keywords": [
            "customer", "who bought", "client", "top customer",
            "customer breakdown", "customer list", "buyer",
            "patron", "account",
            # Malay: pelanggan, klien, pembeli, senarai pelanggan
            "pelanggan", "klien", "pembeli", "senarai.*pelanggan",
        ],
        "description": "Customer-level sales breakdown",
        "always_if_vague": False,
    },
]


# ---------------------------------------------------------------------------
# Vague/generic instruction detection
# ---------------------------------------------------------------------------
VAGUE_PATTERNS = [
    r"^help\b",
    r"help me",
    r"what.*going on",
    r"what.*happening",
    r"check my",
    r"look at my",
    r"see my",
    r"review my",
    r"go through my",
    r"analyse my",  # British
    r"analyze my",  # American
    r"give me.*report",
    r"show me.*business",
    r"full review",
    r"everything",
    r"handle.*business",
    r"take care.*business",
    r"manage my business",
    r"before class",
    r"busy.*week",
    r"don.*have time",
    r"quick.*look",
    r"status update",
    r"where.*stand",
    r"how.*doing",
    r"business health",
    # Malay vague patterns
    r"tolong.*saya",
    r"semak.*perniagaan",
    r"tengok.*perniagaan",
    r"analisa.*perniagaan",
    r"laporan.*perniagaan",
    r"semua.*benda",
    r"urus.*perniagaan",
    r"macam.*mana.*perniagaan",
]


def _is_vague(instruction: str) -> bool:
    """Determine if the instruction is vague/generic (no specific ask)."""
    text = instruction.lower().strip()
    for pattern in VAGUE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _match_capability(cap_id: str, text: str) -> list[str]:
    """Check if any keywords for a capability match the instruction text."""
    for cap in CAPABILITIES:
        if cap["id"] != cap_id:
            continue
        matched: list[str] = []
        for kw in cap["keywords"]:
            if ".*" in kw or "." in kw and not kw.isalnum():
                # regex keyword
                try:
                    if re.search(kw, text):
                        matched.append(kw)
                except re.error:
                    pass
            else:
                # literal substring
                if kw in text:
                    matched.append(kw)
        return matched
    return []


def build_plan(instruction: str) -> dict[str, Any]:
    """Analyse a free-text instruction and build a dynamic execution plan.

    This is the core of the smart planner.  It:
        1. Scans the instruction for capability keywords
        2. If the instruction is vague, includes all 'always_if_vague' capabilities
        3. Builds a structured plan listing which analyses to run
        4. Generates a human-readable goal summary

    Returns a dict with:
        - goal: str — one-line description of what RichBuddy determined
        - capabilities: list[str] — ordered list of capability IDs to execute
        - capability_details: list[dict] — per-capability metadata
        - is_vague: bool — whether the instruction was vague/generic
        - matched_keywords: dict[str, list[str]] — keywords matched per capability
        - plan_steps: list[str] — human-readable step descriptions
        - include_reconciliation: bool
        - include_customer_messages: bool
        - include_action_plan: bool
        - include_files: bool — always True (we always generate files)
    """
    text = instruction.lower().strip()
    vague = _is_vague(text)

    # Match each capability
    selected: list[str] = []
    matched_keywords: dict[str, list[str]] = {}
    capability_details: list[dict[str, Any]] = []

    for cap in CAPABILITIES:
        cap_id = cap["id"]
        kws = _match_capability(cap_id, text)

        if kws:
            # Explicitly matched by keywords
            selected.append(cap_id)
            matched_keywords[cap_id] = kws
        elif vague and cap.get("always_if_vague"):
            # Vague instruction — include capabilities that should always run
            selected.append(cap_id)
            matched_keywords[cap_id] = ["(auto: vague instruction)"]

    # If nothing matched at all (truly empty or nonsense), default to full review
    if not selected:
        vague = True
        for cap in CAPABILITIES:
            if cap.get("always_if_vague"):
                selected.append(cap["id"])
                matched_keywords[cap["id"]] = ["(auto: no specific keywords found)"]

    # Build capability details
    for cap_id in selected:
        cap = next(c for c in CAPABILITIES if c["id"] == cap_id)
        capability_details.append({
            "id": cap_id,
            "description": cap["description"],
            "matched": matched_keywords.get(cap_id, []),
        })

    # Determine special flags
    include_reconciliation = "reconciliation" in selected
    include_customer_messages = (
        "customer_messages" in selected or "invoice_status" in selected
    )
    include_action_plan = "action_plan" in selected

    # Build goal summary
    goal = _build_goal_summary(selected, vague, text)

    # Build plan steps (human-readable)
    plan_steps = _build_plan_steps(
        selected, include_reconciliation, include_customer_messages,
        include_action_plan,
    )

    return {
        "goal": goal,
        "capabilities": selected,
        "capability_details": capability_details,
        "is_vague": vague,
        "matched_keywords": matched_keywords,
        "plan_steps": plan_steps,
        "include_reconciliation": include_reconciliation,
        "include_customer_messages": include_customer_messages,
        "include_action_plan": include_action_plan,
        "include_files": True,
    }


def _build_goal_summary(
    capabilities: list[str], vague: bool, text: str,
) -> str:
    """Generate a one-line description of the determined goal."""
    if vague and len(capabilities) >= 5:
        return (
            "Full business review: analyse everything, identify issues, "
            "draft customer messages, and prepare a prioritized action plan."
        )

    parts = []
    if "financial_overview" in capabilities:
        parts.append("financial performance")
    if "profitability" in capabilities:
        parts.append("profitability by category")
    if "invoice_status" in capabilities:
        parts.append("invoice/payment status")
    if "regional" in capabilities:
        parts.append("regional comparison")
    if "returns" in capabilities:
        parts.append("returns analysis")
    if "reconciliation" in capabilities:
        parts.append("data reconciliation")
    if "customer_messages" in capabilities:
        parts.append("customer follow-up messages")
    if "action_plan" in capabilities:
        parts.append("prioritized action plan")
    if "cost_optimization" in capabilities:
        parts.append("cost-saving opportunities")
    if "growth" in capabilities:
        parts.append("growth opportunities")
    if "customer_breakdown" in capabilities:
        parts.append("customer breakdown")

    if not parts:
        return "General business analysis and review."

    if len(parts) == 1:
        return f"Analyse {parts[0]}."
    if len(parts) <= 3:
        return "Analyse " + ", ".join(parts) + "."
    return (
        "Comprehensive review covering " + ", ".join(parts) + "."
    )


def _build_plan_steps(
    capabilities: list[str],
    include_reconciliation: bool,
    include_customer_messages: bool,
    include_action_plan: bool,
) -> list[str]:
    """Build a list of human-readable execution steps."""
    steps = []

    if include_reconciliation or "reconciliation" in capabilities:
        steps.append("Cross-check invoices against transactions for data integrity")
    if "financial_overview" in capabilities or "profitability" in capabilities:
        steps.append("Calculate revenue, expenses, profit, and margins")
    if "profitability" in capabilities:
        steps.append("Identify profitable and loss-making categories")
    if "invoice_status" in capabilities:
        steps.append("Analyse invoice payment status and outstanding balances")
    if "customer_breakdown" in capabilities:
        steps.append("Break down sales by customer")
    if "regional" in capabilities:
        steps.append("Compare sales and profitability across regions")
    if "returns" in capabilities:
        steps.append("Analyse product returns and refund patterns")
    if "cost_optimization" in capabilities:
        steps.append("Identify cost-saving opportunities in top expense categories")
    if "growth" in capabilities:
        steps.append("Identify growth opportunities and diversification options")
    if include_customer_messages:
        steps.append("Draft customer follow-up messages (WhatsApp/Email)")
    if include_action_plan:
        steps.append("Generate prioritized action plan with time estimates")
    steps.append("Save all results as downloadable files")

    return steps


def format_plan(plan: dict[str, Any]) -> str:
    """Format a plan as human-readable text (for CLI or notes)."""
    lines = []
    lines.append("=" * 60)
    lines.append("  Smart Plan: Goal Determination")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Goal: {plan['goal']}")
    lines.append(f"  Vague instruction: {'YES' if plan['is_vague'] else 'NO'}")
    lines.append(f"  Capabilities detected: {len(plan['capabilities'])}")
    lines.append("")
    lines.append("  Execution Steps:")
    for i, step in enumerate(plan["plan_steps"], 1):
        lines.append(f"    {i}. {step}")
    lines.append("")
    lines.append("  Detected Capabilities:")
    for detail in plan["capability_details"]:
        kws = ", ".join(detail["matched"][:3])
        if len(detail["matched"]) > 3:
            kws += f" (+{len(detail['matched']) - 3} more)"
        lines.append(f"    - {detail['id']}: {detail['description']}")
        lines.append(f"      Matched: {kws}")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
