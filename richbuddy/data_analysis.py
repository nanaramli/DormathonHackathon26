"""
data_analysis.py - General data analysis functions for RichBuddy.

This module provides non-financial analytical functions that inspect the raw
dataset, aggregate values, and surface patterns.  Financial calculations
(profit, margins, etc.) live in ``financial_analysis.py`` to keep concerns
separated.
"""

from collections import defaultdict
from typing import Any


def analyze_revenue_by_category(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate total revenue per income category.

    Returns:
        {
            "by_category": {category: total_revenue},
            "total_revenue": float,
            "categories": [sorted list of categories],
        }
    """
    by_cat: dict[str, float] = defaultdict(float)
    for tx in transactions:
        if tx["type"] == "income":
            by_cat[tx["category"]] += tx["amount_rm"]

    total = sum(by_cat.values())
    return {
        "by_category": dict(by_cat),
        "total_revenue": round(total, 2),
        "categories": sorted(by_cat.keys()),
    }


def analyze_expense_by_category(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate total expenses per expense category.

    Returns:
        {
            "by_category": {category: total_expense},
            "total_expense": float,
            "categories": [sorted list of categories],
        }
    """
    by_cat: dict[str, float] = defaultdict(float)
    for tx in transactions:
        if tx["type"] == "expense":
            by_cat[tx["category"]] += tx["amount_rm"]

    total = sum(by_cat.values())
    return {
        "by_category": dict(by_cat),
        "total_expense": round(total, 2),
        "categories": sorted(by_cat.keys()),
    }


def analyze_monthly_trends(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyse revenue and expenses by month.

    Returns:
        {
            "months": [list of "YYYY-MM" strings],
            "income_by_month": {month: total},
            "expense_by_month": {month: total},
            "net_by_month": {month: total},
        }
    """
    income_by_month: dict[str, float] = defaultdict(float)
    expense_by_month: dict[str, float] = defaultdict(float)

    for tx in transactions:
        month = tx["date"][:7]  # "YYYY-MM"
        if tx["type"] == "income":
            income_by_month[month] += tx["amount_rm"]
        else:
            expense_by_month[month] += tx["amount_rm"]

    all_months = sorted(set(list(income_by_month.keys()) + list(expense_by_month.keys())))
    net_by_month = {
        m: round(income_by_month.get(m, 0) - expense_by_month.get(m, 0), 2)
        for m in all_months
    }

    return {
        "months": all_months,
        "income_by_month": {m: round(income_by_month.get(m, 0), 2) for m in all_months},
        "expense_by_month": {m: round(expense_by_month.get(m, 0), 2) for m in all_months},
        "net_by_month": net_by_month,
    }


def analyze_invoice_status(invoices: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise invoice status distribution.

    Returns:
        {
            "by_status": {status: count},
            "by_status_amount": {status: total_invoice_amount},
            "total_invoiced": float,
            "total_paid": float,
            "total_outstanding": float,
        }
    """
    by_status: dict[str, int] = defaultdict(int)
    by_status_amount: dict[str, float] = defaultdict(float)

    for inv in invoices:
        by_status[inv["status"]] += 1
        by_status_amount[inv["status"]] += inv["invoice_amount_rm"]

    total_invoiced = sum(inv["invoice_amount_rm"] for inv in invoices)
    total_paid = sum(inv["amount_paid_rm"] for inv in invoices)
    total_outstanding = sum(inv["balance_due_rm"] for inv in invoices)

    return {
        "by_status": dict(by_status),
        "by_status_amount": {k: round(v, 2) for k, v in by_status_amount.items()},
        "total_invoiced": round(total_invoiced, 2),
        "total_paid": round(total_paid, 2),
        "total_outstanding": round(total_outstanding, 2),
    }


def analyze_customer_breakdown(invoices: list[dict[str, Any]]) -> dict[str, Any]:
    """Break down invoiced amounts and outstanding balances by customer.

    Returns:
        {
            "customers": [sorted list of customer names],
            "invoiced_by_customer": {customer: total},
            "outstanding_by_customer": {customer: total},
        }
    """
    invoiced: dict[str, float] = defaultdict(float)
    outstanding: dict[str, float] = defaultdict(float)

    for inv in invoices:
        cust = inv["customer_name"]
        invoiced[cust] += inv["invoice_amount_rm"]
        outstanding[cust] += inv["balance_due_rm"]

    return {
        "customers": sorted(invoiced.keys()),
        "invoiced_by_customer": {k: round(v, 2) for k, v in invoiced.items()},
        "outstanding_by_customer": {k: round(v, 2) for k, v in outstanding.items()},
    }


def analyze_transaction_detail(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return transactions sorted by date for reporting purposes."""
    return sorted(transactions, key=lambda t: t["date"])


def analyze_category_summary(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Produce a per-category summary table combining income and expense data.

    Each row: {category, income, expense, net, transaction_count}
    """
    cat_data: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"income": 0.0, "expense": 0.0, "count": 0}
    )
    for tx in transactions:
        cat = tx["category"]
        cat_data[cat]["count"] += 1
        if tx["type"] == "income":
            cat_data[cat]["income"] += tx["amount_rm"]
        else:
            cat_data[cat]["expense"] += tx["amount_rm"]

    rows = []
    for cat in sorted(cat_data.keys()):
        d = cat_data[cat]
        rows.append({
            "category": cat,
            "income_rm": round(d["income"], 2),
            "expense_rm": round(d["expense"], 2),
            "net_rm": round(d["income"] - d["expense"], 2),
            "transaction_count": d["count"],
        })
    return rows
