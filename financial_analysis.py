"""
financial_analysis.py - Financial calculations for RichBuddy.

This module computes financial indicators: net profit, profit margins,
per-category profitability, outstanding balances, and collection rates.

All calculations use **actual dataset values** -- nothing is invented.  When
the dataset lacks information needed for a particular calculation (e.g., cost
of goods sold per product), the module is transparent about the assumptions
it makes.
"""

from collections import defaultdict
from typing import Any

from data_analysis import (
    analyze_revenue_by_category,
    analyze_expense_by_category,
)


# ---------------------------------------------------------------------------
# Expense-allocation rules
# ---------------------------------------------------------------------------
# The sample dataset does not contain explicit cost-of-goods-sold per product.
# To estimate per-category profitability we map expense categories to income
# categories using reasonable business logic.  Expenses that cannot be tied to
# a single income category are treated as shared overhead and allocated by
# revenue proportion.
#
# This is an ESTIMATE and the output always discloses the allocation method.
# ---------------------------------------------------------------------------
EXPENSE_TO_INCOME_MAP: dict[str, str | None] = {
    "Supplies": "Printing",        # printing materials
    "Software": "Design",          # design software
    "Transport": "Printing",       # delivery for printing orders
    "Marketing": None,             # shared overhead
    "Utilities": None,             # shared overhead
}


def calculate_net_profit(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate overall net profit from income and expense transactions.

    Returns:
        {
            "total_revenue": float,
            "total_expenses": float,
            "net_profit": float,
            "profit_margin_pct": float,
        }
    """
    rev_data = analyze_revenue_by_category(transactions)
    exp_data = analyze_expense_by_category(transactions)

    total_revenue = rev_data["total_revenue"]
    total_expenses = exp_data["total_expense"]
    net_profit = total_revenue - total_expenses
    margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_expenses": round(total_expenses, 2),
        "net_profit": round(net_profit, 2),
        "profit_margin_pct": round(margin, 1),
    }


def calculate_profit_by_category(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Estimate profitability per income/service category.

    Direct expenses are allocated to their mapped income category.
    Shared overhead (Marketing, Utilities, etc.) is split across income
    categories in proportion to each category's revenue share.

    Returns:
        {
            "categories": [
                {
                    "category": str,
                    "revenue": float,
                    "direct_cost": float,
                    "overhead_cost": float,
                    "total_cost": float,
                    "profit": float,
                    "profit_margin_pct": float,
                    "is_loss_making": bool,
                },
                ...
            ],
            "allocation_method": str (human-readable explanation),
            "total_revenue": float,
            "total_cost": float,
            "total_profit": float,
        }
    """
    rev_data = analyze_revenue_by_category(transactions)
    exp_data = analyze_expense_by_category(transactions)

    revenue_by_cat = rev_data["by_category"]
    expense_by_cat = exp_data["by_category"]
    total_revenue = rev_data["total_revenue"]
    total_expense = exp_data["total_expense"]

    income_categories = sorted(revenue_by_cat.keys())

    # Separate expenses into "direct" and "overhead"
    direct_expenses: dict[str, float] = defaultdict(float)
    overhead_pool = 0.0

    for exp_cat, amount in expense_by_cat.items():
        mapped = EXPENSE_TO_INCOME_MAP.get(exp_cat)
        if mapped and mapped in revenue_by_cat:
            direct_expenses[mapped] += amount
        else:
            overhead_pool += amount

    # Allocate overhead by revenue share
    categories_result = []
    for inc_cat in income_categories:
        rev = revenue_by_cat[inc_cat]
        direct = direct_expenses.get(inc_cat, 0.0)
        rev_share = rev / total_revenue if total_revenue > 0 else 0.0
        overhead = overhead_pool * rev_share
        total_cost = direct + overhead
        profit = rev - total_cost
        margin = (profit / rev * 100) if rev > 0 else 0.0

        categories_result.append({
            "category": inc_cat,
            "revenue": round(rev, 2),
            "direct_cost": round(direct, 2),
            "overhead_cost": round(overhead, 2),
            "total_cost": round(total_cost, 2),
            "profit": round(profit, 2),
            "profit_margin_pct": round(margin, 1),
            "is_loss_making": profit < 0,
        })

    allocation_method = (
        "Direct expenses (Supplies->Printing, Software->Design, "
        "Transport->Printing) are assigned to their mapped income category. "
        "Shared overhead (Marketing, Utilities) is allocated by each "
        "category's revenue share. This is an estimate because the dataset "
        "does not contain explicit cost-of-goods-sold per product."
    )

    return {
        "categories": categories_result,
        "allocation_method": allocation_method,
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_expense, 2),
        "total_profit": round(total_revenue - total_expense, 2),
    }


def identify_loss_making_categories(
    profit_by_category: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return list of categories that are loss-making (profit < 0)."""
    return [c for c in profit_by_category["categories"] if c["is_loss_making"]]


def identify_profitable_categories(
    profit_by_category: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return list of categories sorted by profit (highest first)."""
    profitable = [c for c in profit_by_category["categories"] if not c["is_loss_making"]]
    return sorted(profitable, key=lambda c: c["profit"], reverse=True)


def calculate_outstanding_balance(
    invoices: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyse outstanding and overdue invoice balances.

    Returns:
        {
            "total_outstanding": float,
            "overdue_amount": float,
            "pending_amount": float,
            "overdue_invoices": [list of invoice dicts],
            "pending_invoices": [list of invoice dicts],
            "collection_rate_pct": float,  # collected / invoiced
        }
    """
    overdue = [inv for inv in invoices if inv["status"] == "overdue"]
    pending = [inv for inv in invoices if inv["status"] == "pending"]

    total_outstanding = sum(inv["balance_due_rm"] for inv in invoices)
    overdue_amount = sum(inv["balance_due_rm"] for inv in overdue)
    pending_amount = sum(inv["balance_due_rm"] for inv in pending)

    total_invoiced = sum(inv["invoice_amount_rm"] for inv in invoices)
    total_paid = sum(inv["amount_paid_rm"] for inv in invoices)
    collection_rate = (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0.0

    return {
        "total_outstanding": round(total_outstanding, 2),
        "overdue_amount": round(overdue_amount, 2),
        "pending_amount": round(pending_amount, 2),
        "overdue_invoices": overdue,
        "pending_invoices": pending,
        "collection_rate_pct": round(collection_rate, 1),
    }


def calculate_revenue_concentration(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyse revenue concentration by category (diversification check).

    Returns:
        {
            "category_shares": {category: share_pct},
            "top_category": str,
            "top_category_share_pct": float,
            "is_concentrated": bool,  # True if top category > 60%
        }
    """
    rev_data = analyze_revenue_by_category(transactions)
    total = rev_data["total_revenue"]
    shares = {}
    for cat, amt in rev_data["by_category"].items():
        shares[cat] = round(amt / total * 100, 1) if total > 0 else 0.0

    top_cat = max(shares, key=shares.get) if shares else "N/A"
    top_share = shares.get(top_cat, 0.0)

    return {
        "category_shares": shares,
        "top_category": top_cat,
        "top_category_share_pct": top_share,
        "is_concentrated": top_share > 60.0,
    }


def calculate_expense_ratio(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate the expense-to-revenue ratio and identify top cost centres.

    Returns:
        {
            "expense_ratio_pct": float,
            "top_expense_categories": [sorted by amount desc],
            "top_expense_category": str,
            "top_expense_amount": float,
        }
    """
    rev_data = analyze_revenue_by_category(transactions)
    exp_data = analyze_expense_by_category(transactions)

    total_rev = rev_data["total_revenue"]
    total_exp = exp_data["total_expense"]
    ratio = (total_exp / total_rev * 100) if total_rev > 0 else 0.0

    sorted_expenses = sorted(
        exp_data["by_category"].items(), key=lambda x: x[1], reverse=True
    )

    return {
        "expense_ratio_pct": round(ratio, 1),
        "top_expense_categories": [
            {"category": cat, "amount": round(amt, 2)} for cat, amt in sorted_expenses
        ],
        "top_expense_category": sorted_expenses[0][0] if sorted_expenses else "N/A",
        "top_expense_amount": round(sorted_expenses[0][1], 2) if sorted_expenses else 0.0,
    }
