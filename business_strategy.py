"""
business_strategy.py - Convert analytical findings into prioritised,
evidence-backed recommendations for student entrepreneurs.

This module takes structured findings and translates them into practical,
affordable actions that students can implement while balancing studies
and limited resources.

Each recommendation includes:
    - priority: 1 (highest), 2, or 3
    - title: short action title
    - finding: the evidence from the data that motivates this action
    - recommendation: what the user should do
    - rationale: why it matters and what impact it could have
    - data_source: which analysis produced the supporting evidence
    - implementation_effort: low / medium / strategic
"""

from typing import Any


def prioritize_actions(findings: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate prioritised, student-focused recommendations from findings.

    Returns recommendations sorted by priority (1 = highest urgency).
    Only returns recommendations that are supported by actual findings.
    Never invents customer demand, guaranteed savings, or future profit.
    """
    actions: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Priority 1 -- Cash flow / overdue invoices (urgent for students)
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
                "title": "Follow up on overdue payments this week",
                "finding": (
                    f"RM{out['overdue_amount']:.2f} is overdue across "
                    f"{len(out['overdue_invoices'])} invoice(s): {overdue_names}. "
                    f"Your collection rate is {out['collection_rate_pct']:.1f}%."
                ),
                "recommendation": (
                    "Send a friendly WhatsApp message to each customer with an "
                    "overdue invoice. Keep it casual but clear -- mention the "
                    "amount and ask when they can transfer. Most students pay "
                    "quickly once reminded."
                ),
                "rationale": (
                    "As a student, every ringgit matters for cash flow. Overdue "
                    "payments mean money you've already earned by baking isn't "
                    "available to buy ingredients for your next batch. Following "
                    "up personally is the single highest-impact action you can take."
                ),
                "data_source": "outstanding_balance_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 1 -- Business is operating at a loss
    # ------------------------------------------------------------------
    if "net_profit" in findings:
        np = findings["net_profit"]
        if np.get("net_profit", 0) < 0:
            actions.append({
                "priority": 1,
                "title": "Your business is losing money -- act now",
                "finding": (
                    f"Your total revenue is RM{np.get('total_revenue', 0):.2f} but "
                    f"expenses are RM{np.get('total_expenses', 0):.2f}, resulting "
                    f"in a net loss of RM{abs(np.get('net_profit', 0)):.2f}."
                ),
                "recommendation": (
                    "Two immediate options: (1) raise prices by RM1-2 per item -- "
                    "students rarely notice small increases, or (2) find cheaper "
                    "ingredients by buying in bulk from wholesale shops like "
                    "Giant or Tesco instead of convenience stores."
                ),
                "rationale": (
                    "Operating at a loss while studying is unsustainable. The "
                    "longer it continues, the more of your own money you're "
                    "spending. Even a small price increase or ingredient swap can "
                    "flip the business to profitability."
                ),
                "data_source": "net_profit_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 2 -- Highest expense category needs review
    # ------------------------------------------------------------------
    if "expense_ratio" in findings:
        er = findings["expense_ratio"]
        top = er["top_expense_categories"][0] if er["top_expense_categories"] else None
        if top:
            actions.append({
                "priority": 2,
                "title": f"Reduce your biggest cost: {top['category']}",
                "finding": (
                    f"{top['category']} is your largest expense at "
                    f"RM{top['amount']:.2f}, making up a significant portion "
                    f"of your overall expense ratio of {er['expense_ratio_pct']:.1f}%."
                ),
                "recommendation": (
                    f"Review your {top['category'].lower()} spending. For a "
                    "student business, try: buying ingredients in bulk with a "
                    "friend who also sells food, comparing prices between 2-3 "
                    "shops, or switching to a cheaper brand for items where "
                    "quality difference is minimal."
                ),
                "rationale": (
                    "Cutting your largest cost category has the biggest impact "
                    "on profit. Student businesses often overpay because they buy "
                    "small quantities from nearby shops -- a quick price "
                    "comparison can save RM10-20 per week."
                ),
                "data_source": "expense_ratio_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 2 -- Focus on most profitable product
    # ------------------------------------------------------------------
    if "profit_by_category" in findings:
        pbc = findings["profit_by_category"]
        profitable = [c for c in pbc["categories"] if not c["is_loss_making"]]
        if profitable:
            best = max(profitable, key=lambda c: c["profit"])
            actions.append({
                "priority": 2,
                "title": f"Focus on your best-seller: {best['category']}",
                "finding": (
                    f"{best['category']} generates RM{best['revenue']:.2f} in "
                    f"revenue with an estimated profit of RM{best['profit']:.2f} "
                    f"(margin: {best['profit_margin_pct']:.1f}%)."
                ),
                "recommendation": (
                    f"Promote {best['category']} more on your Instagram or "
                    "WhatsApp status. Consider offering a bundle deal (e.g., "
                    "'buy 2 get 1 free' for the first 10 customers) to increase "
                    "volume on your most profitable item."
                ),
                "rationale": (
                    "Your best-selling product is where you get the most return "
                    "for your baking time. As a busy student, focus your limited "
                    "marketing effort on what already works rather than trying "
                    "to push slower-selling items."
                ),
                "data_source": "profit_by_category_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 2 -- Revenue concentration risk
    # ------------------------------------------------------------------
    if "revenue_concentration" in findings:
        rc = findings["revenue_concentration"]
        if rc["is_concentrated"]:
            actions.append({
                "priority": 2,
                "title": f"Don't rely too much on {rc['top_category']}",
                "finding": (
                    f"{rc['top_category']} accounts for "
                    f"{rc['top_category_share_pct']:.1f}% of your total revenue, "
                    f"which is high concentration risk."
                ),
                "recommendation": (
                    "Promote your other products more actively. Try introducing "
                    "a new flavor or product variation to attract different "
                    "customers. Aim for no single product to exceed 50% of revenue."
                ),
                "rationale": (
                    "If demand for one product drops -- maybe exam season ends "
                    "and fewer students buy -- your income drops with it. "
                    "Having 2-3 products that each contribute meaningfully makes "
                    "your business more resilient."
                ),
                "data_source": "revenue_concentration_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 3 -- Address loss-making products
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
                "title": "Stop or fix products that lose money",
                "finding": f"The following products are estimated to lose money: {loss_desc}.",
                "recommendation": (
                    "For each loss-making product: either raise the price by "
                    "RM1-2, reduce the portion size, or stop selling it. Your "
                    "time as a student is limited -- don't spend it baking things "
                    "that cost more than they earn."
                ),
                "rationale": (
                    "Loss-making products consume your ingredients and time "
                    "without generating profit. Stopping them frees up capacity "
                    "for products that actually make money."
                ),
                "data_source": "profit_by_category_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 3 -- Set up payment reminders (preventive)
    # ------------------------------------------------------------------
    if "outstanding" in findings:
        out = findings["outstanding"]
        if out["pending_amount"] > 0 and out["overdue_amount"] == 0:
            actions.append({
                "priority": 3,
                "title": "Set up simple payment reminders",
                "finding": (
                    f"RM{out['pending_amount']:.2f} is pending in unpaid "
                    f"invoices. Collection rate is {out['collection_rate_pct']:.1f}%."
                ),
                "recommendation": (
                    "Create a simple reminder system: set a phone alarm for "
                    "invoice due dates and send a quick WhatsApp nudge the day "
                    "before. For student customers, a friendly reminder works "
                    "better than a formal follow-up."
                ),
                "rationale": (
                    "Preventing invoices from becoming overdue is much easier "
                    "than chasing them after the fact. A reminder system takes "
                    "5 minutes to set up and saves hours of awkward follow-ups."
                ),
                "data_source": "outstanding_balance_analysis",
            })

    # ------------------------------------------------------------------
    # Priority 3 -- Declining revenue trend
    # ------------------------------------------------------------------
    if "monthly_trends" in findings:
        mt = findings["monthly_trends"]
        if mt.get("months") and len(mt["months"]) >= 2:
            months = mt["months"]
            first_net = mt.get("net_by_month", {}).get(months[0], 0)
            last_net = mt.get("net_by_month", {}).get(months[-1], 0)
            if last_net < first_net and first_net > 0:
                decline_pct = ((first_net - last_net) / first_net) * 100
                actions.append({
                    "priority": 3,
                    "title": "Investigate why revenue is declining",
                    "finding": (
                        f"Net profit dropped from RM{first_net:.2f} in {months[0]} "
                        f"to RM{last_net:.2f} in {months[-1]} (-{decline_pct:.1f}%)."
                    ),
                    "recommendation": (
                        "Ask yourself: is it exam season? Did a new competitor "
                        "start selling nearby? Did you post less on Instagram? "
                        "Identify the likely cause before trying to fix it."
                    ),
                    "rationale": (
                        "Revenue declines are common for student businesses due "
                        "to exam cycles, holidays, or social media fatigue. "
                        "Understanding the cause helps you decide whether to "
                        "push harder or wait for the cycle to turn."
                    ),
                    "data_source": "monthly_trends_analysis",
                })

    # Sort by priority (1 = highest urgency)
    actions.sort(key=lambda a: a["priority"])

    # Cap at top 5 for readability
    return actions[:5]
