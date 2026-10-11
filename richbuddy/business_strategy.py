"""
business_strategy.py - Convert analytical findings into prioritised actions.

This module takes the structured findings produced by the data and financial
analysis modules and translates them into practical, evidence-based
recommendations suitable for student entrepreneurs.

Each recommendation includes:
    - priority: 1 (highest), 2, or 3
    - title: short action title
    - finding: the evidence from the data that motivates this action
    - recommendation: what the user should do
    - rationale: why it matters and what impact it could have
    - data_source: which analysis produced the supporting evidence
"""

from typing import Any


def prioritize_actions(findings: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate prioritised business recommendations from analysis findings.

    The *findings* dict is produced by the orchestrator and may contain keys
    matching any of the supported analysis intents.  This function examines
    each finding, extracts actionable insights, and returns them sorted by
    priority.
    """
    actions: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Priority 1 -- Cash flow / overdue invoices (highest urgency)
    # ------------------------------------------------------------------
    if "outstanding" in findings:
        out = findings["outstanding"]
        if out["overdue_amount"] > 0:
            overdue_names = ", ".join(
                f"{inv['invoice_id']} ({inv['customer_name']}, RM{inv['balance_due_rm']:.2f})"
                for inv in out["overdue_invoices"]
            )
            actions.append({
                "priority": 1,
                "title": "Chase overdue invoices immediately",
                "finding": (
                    f"RM{out['overdue_amount']:.2f} is overdue across "
                    f"{len(out['overdue_invoices'])} invoice(s): {overdue_names}. "
                    f"The collection rate is {out['collection_rate_pct']:.1f}%."
                ),
                "recommendation": (
                    "Contact the customers listed above and request immediate "
                    "payment. Consider setting up payment reminders or follow-up "
                    "procedures for future invoices."
                ),
                "rationale": (
                    "Overdue invoices mean money you have already earned is not "
                    "in your bank account. For a small business, even a few weeks "
                    "of delayed payment can create cash-flow problems that affect "
                    "your ability to buy materials or pay for services."
                ),
                "data_source": "outstanding_balance_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 2 -- Reduce the highest expense category
    # ------------------------------------------------------------------
    if "expense_ratio" in findings:
        er = findings["expense_ratio"]
        top = er["top_expense_categories"][0] if er["top_expense_categories"] else None
        if top:
            actions.append({
                "priority": 2,
                "title": f"Review and optimise {top['category']} costs",
                "finding": (
                    f"{top['category']} is your largest expense at RM{top['amount']:.2f}, "
                    f"contributing to an overall expense ratio of "
                    f"{er['expense_ratio_pct']:.1f}% of revenue."
                ),
                "recommendation": (
                    f"Examine your {top['category'].lower()} spending and look for "
                    "cheaper suppliers, bulk-buy discounts, or items you can defer. "
                    "Even a 10-15% reduction in this category would meaningfully "
                    "improve your bottom line."
                ),
                "rationale": (
                    "Cutting your largest cost category has the biggest impact on "
                    "profit. Small businesses often overpay for supplies or services "
                    "because they don't shop around -- a quick review can yield "
                    "immediate savings."
                ),
                "data_source": "expense_ratio_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 2 -- Revenue concentration risk
    # ------------------------------------------------------------------
    if "revenue_concentration" in findings:
        rc = findings["revenue_concentration"]
        if rc["is_concentrated"]:
            actions.append({
                "priority": 2,
                "title": f"Diversify revenue beyond {rc['top_category']}",
                "finding": (
                    f"{rc['top_category']} accounts for {rc['top_category_share_pct']:.1f}% "
                    f"of total revenue, indicating high concentration risk."
                ),
                "recommendation": (
                    "Develop your other service category or add a complementary "
                    "offering so that no single category dominates your revenue. "
                    "Aim for a more balanced split (e.g., no category above 60%)."
                ),
                "rationale": (
                    "Relying too heavily on one revenue stream is risky -- if "
                    "demand for that service drops, your income drops with it. "
                    "Diversification makes your business more resilient."
                ),
                "data_source": "revenue_concentration_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 3 -- Expand the most profitable category
    # ------------------------------------------------------------------
    if "profit_by_category" in findings:
        pbc = findings["profit_by_category"]
        profitable = [c for c in pbc["categories"] if not c["is_loss_making"]]
        if profitable:
            best = max(profitable, key=lambda c: c["profit"])
            actions.append({
                "priority": 3,
                "title": f"Expand your most profitable service: {best['category']}",
                "finding": (
                    f"{best['category']} generates RM{best['revenue']:.2f} in revenue "
                    f"with an estimated profit margin of {best['profit_margin_pct']:.1f}% "
                    f"(profit: RM{best['profit']:.2f})."
                ),
                "recommendation": (
                    f"Invest more marketing effort into {best['category'].lower()} "
                    "services. Look for ways to scale this offering -- new customers, "
                    "higher pricing, or complementary add-ons."
                ),
                "rationale": (
                    "Your most profitable category is where you get the best return "
                    "for your effort. Doubling down on it is usually more effective "
                    "than trying to fix a weaker category."
                ),
                "data_source": "profit_by_category_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 3 -- Address loss-making categories
    # ------------------------------------------------------------------
    if "profit_by_category" in findings:
        pbc = findings["profit_by_category"]
        losses = [c for c in pbc["categories"] if c["is_loss_making"]]
        if losses:
            loss_desc = ", ".join(
                f"{c['category']} (RM{c['profit']:.2f})" for c in losses
            )
            actions.append({
                "priority": 3,
                "title": "Address or discontinue loss-making categories",
                "finding": f"The following categories are estimated to be loss-making: {loss_desc}.",
                "recommendation": (
                    "For each loss-making category, either raise prices, reduce "
                    "costs, or consider discontinuing the offering if it cannot be "
                    "made profitable."
                ),
                "rationale": (
                    "Products or services that cost more than they earn drain your "
                    "business. Stopping the bleed is often more valuable than "
                    "growing profitable areas."
                ),
                "data_source": "profit_by_category_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 3 -- Improve collection process
    # ------------------------------------------------------------------
    if "outstanding" in findings:
        out = findings["outstanding"]
        if out["pending_amount"] > 0 and out["overdue_amount"] == 0:
            actions.append({
                "priority": 3,
                "title": "Set up a payment-reminder system",
                "finding": (
                    f"RM{out['pending_amount']:.2f} is pending in unpaid invoices. "
                    f"Collection rate is {out['collection_rate_pct']:.1f}%."
                ),
                "recommendation": (
                    "Create a simple reminder process: send a friendly nudge a few "
                    "days before the due date and follow up immediately if payment "
                    "is late."
                ),
                "rationale": (
                    "Preventing invoices from becoming overdue is much easier than "
                    "chasing them after the fact. A reminder system is low-effort "
                    "and high-impact for cash flow."
                ),
                "data_source": "outstanding_balance_analysis",
            })

    # Sort by priority (1 = highest urgency)
    actions.sort(key=lambda a: a["priority"])

    # Cap at top 5 for readability
    return actions[:5]
