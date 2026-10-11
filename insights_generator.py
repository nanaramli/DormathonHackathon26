"""
insights_generator.py - Generate AI-like plain-language insights from analysis findings.

Produces Smart Insight cards that explain:
- What the data shows (Finding)
- What it means (Recommendation)
- Why it matters (Rationale)

This is a rule-based insight engine that mimics LLM-style explanations.
"""


def generate_insights(findings: dict, dataset_summary: dict = None) -> list[dict]:
    """Generate smart insights from analysis findings.

    Returns a list of insight cards, each with:
        - priority (1-3, where 1 is highest)
        - category (string)
        - title (string)
        - finding (plain-language description)
        - recommendation (what to do)
        - rationale (why it matters)
    """
    insights = []

    # 1. Net Profit insight
    np = findings.get("net_profit")
    if np:
        margin = np.get("profit_margin_pct", 0)
        net = np.get("net_profit", 0)
        if net < 0:
            insights.append({
                "priority": 1,
                "category": "Profitability",
                "title": "Business is operating at a loss",
                "finding": f"Your total revenue is RM {np.get('total_revenue', 0):.2f} but expenses are RM {np.get('total_expenses', 0):.2f}, resulting in a net loss of RM {abs(net):.2f}.",
                "recommendation": "Review your top expense categories and identify where costs can be reduced. Consider raising prices or finding cheaper suppliers.",
                "rationale": "Operating at a loss means the business is burning cash. Without intervention, this is unsustainable long-term.",
            })
        elif margin < 10:
            insights.append({
                "priority": 2,
                "category": "Profitability",
                "title": "Profit margin is thin",
                "finding": f"Your net profit is RM {net:.2f} with a profit margin of only {margin:.1f}%. Industry healthy margins are typically 15-25%.",
                "recommendation": "Look for ways to increase margin — raise prices on top sellers, reduce variable costs, or promote higher-margin products.",
                "rationale": "A thin margin means small changes in costs or revenue have outsized impact on profitability. A 5% cost increase could turn profit into loss.",
            })
        else:
            insights.append({
                "priority": 3,
                "category": "Profitability",
                "title": "Healthy profit margin",
                "finding": f"Your net profit is RM {net:.2f} with a profit margin of {margin:.1f}%. This indicates a profitable operation.",
                "recommendation": "Maintain current operations. Consider reinvesting profits into growth — marketing, new product lines, or expanding to new regions.",
                "rationale": "A healthy margin gives you buffer against downturns and resources for growth. Protect it by monitoring expense ratios.",
            })

    # 2. Revenue concentration insight
    rc = findings.get("revenue_concentration")
    if rc:
        top_cat = rc.get("top_category", "Unknown")
        top_share = rc.get("top_category_share_pct", 0)
        if rc.get("is_concentrated", False):
            insights.append({
                "priority": 1,
                "category": "Revenue Risk",
                "title": f"Revenue is over-concentrated in '{top_cat}'",
                "finding": f"'{top_cat}' generates {top_share:.1f}% of your total revenue. Having more than 60% from one source is high concentration risk.",
                "recommendation": "Diversify your revenue streams. Promote other categories, develop new offerings, or target different customer segments.",
                "rationale": "If demand for '{top_cat}' drops, your revenue collapses. Diversification spreads risk and stabilises income.".replace("'{top_cat}'", f"'{top_cat}'"),
            })
        else:
            insights.append({
                "priority": 3,
                "category": "Revenue Risk",
                "title": "Revenue is well-diversified",
                "finding": f"Your top category '{top_cat}' accounts for {top_share:.1f}% of revenue, indicating a healthy revenue spread.",
                "recommendation": "Continue supporting all categories equally. Monitor for any single category growing past 50% share.",
                "rationale": "Diversified revenue means no single category can sink the business. This is a sign of resilience.",
            })

    # 3. Outstanding invoices insight
    out = findings.get("outstanding")
    if out:
        total_out = out.get("total_outstanding", 0)
        overdue = out.get("overdue_amount", 0)
        collection_rate = out.get("collection_rate_pct", 100)
        if overdue > 0:
            insights.append({
                "priority": 1,
                "category": "Cash Flow",
                "title": "Overdue invoices need follow-up",
                "finding": f"You have RM {overdue:.2f} in overdue invoices. Your collection rate is {collection_rate:.1f}%.",
                "recommendation": "Send follow-up messages to overdue customers immediately. Prioritise the largest overdue amounts first.",
                "rationale": "Overdue invoices tie up working capital. The longer they remain unpaid, the harder they are to collect.",
            })
        elif total_out > 0:
            insights.append({
                "priority": 2,
                "category": "Cash Flow",
                "title": "Pending invoices to monitor",
                "finding": f"You have RM {total_out:.2f} in pending (not yet overdue) invoices. Collection rate is {collection_rate:.1f}%.",
                "recommendation": "Keep an eye on these. Set reminders for due dates so you can follow up the moment they become overdue.",
                "rationale": "Staying on top of pending invoices prevents them from becoming overdue. Proactive collection improves cash flow.",
            })

    # 4. Expense ratio insight
    er = findings.get("expense_ratio")
    if er:
        ratio = er.get("expense_ratio_pct", 0)
        top_expense = er.get("top_expense_category", "Unknown")
        if ratio > 80:
            insights.append({
                "priority": 1,
                "category": "Cost Control",
                "title": f"Expenses are eating your revenue ({ratio:.1f}%)",
                "finding": f"Your total expenses are {ratio:.1f}% of revenue. The biggest cost is '{top_expense}'.",
                "recommendation": f"Focus on reducing '{top_expense}' costs. Even a 10% reduction here would significantly improve your bottom line.",
                "rationale": "When expenses exceed 80% of revenue, there's very little room for error. A small revenue dip or cost increase tips you into loss.",
            })
        elif ratio > 60:
            insights.append({
                "priority": 2,
                "category": "Cost Control",
                "title": "Expense ratio is moderate",
                "finding": f"Expenses are {ratio:.1f}% of revenue. Top expense: '{top_expense}'.",
                "recommendation": "Your cost structure is workable but not optimal. Look for efficiency gains in your top expense categories.",
                "rationale": "A moderate expense ratio leaves room for profit but also room for improvement. Optimising costs directly increases profit.",
            })

    # 5. Profit by category / loss-making products
    pbc = findings.get("profit_by_category")
    if pbc and pbc.get("categories"):
        loss_cats = [c for c in pbc["categories"] if c.get("is_loss_making")]
        profit_cats = [c for c in pbc["categories"] if not c.get("is_loss_making")]
        if loss_cats:
            names = ", ".join(c["category"] for c in loss_cats)
            insights.append({
                "priority": 1,
                "category": "Product Performance",
                "title": f"Loss-making categories: {names}",
                "finding": f"{len(loss_cats)} of {len(pbc['categories'])} categories are operating at a loss.",
                "recommendation": "Either increase prices, reduce costs, or discontinue these categories. Every loss-making category drags down overall profit.",
                "rationale": "Loss-making products consume resources without generating return. Cutting them frees up capacity for profitable ones.",
            })
        if profit_cats:
            best = max(profit_cats, key=lambda c: c.get("profit", 0))
            insights.append({
                "priority": 2,
                "category": "Product Performance",
                "title": f"Most profitable: '{best['category']}'",
                "finding": f"'{best['category']}' generates the highest profit at RM {best.get('profit', 0):.2f} with a {best.get('profit_margin_pct', 0):.1f}% margin.",
                "recommendation": f"Double down on '{best['category']}'. Increase its visibility, run promotions, and ensure supply meets demand.",
                "rationale": "Your most profitable product is your growth engine. Investing in it yields the highest return per ringgit spent.",
            })

    # 6. Regional analysis insight
    ra = findings.get("regional_analysis")
    if ra and ra.get("regions"):
        best_region = max(ra["regions"], key=lambda r: r.get("revenue", 0))
        worst_region = min(ra["regions"], key=lambda r: r.get("revenue", 0))
        if best_region.get("region") != worst_region.get("region"):
            insights.append({
                "priority": 2,
                "category": "Regional Performance",
                "title": f"Best region: '{best_region['region']}', needs attention: '{worst_region['region']}'",
                "finding": f"'{best_region['region']}' leads with RM {best_region.get('revenue', 0):.2f} revenue. '{worst_region['region']}' is lowest at RM {worst_region.get('revenue', 0):.2f}.",
                "recommendation": f"Study what works in '{best_region['region']}' and replicate it in '{worst_region['region']}'. Consider targeted promotions in the underperforming region.",
                "rationale": "Regional disparities reveal best practices and growth opportunities. Closing the gap can unlock significant revenue.",
            })

    # 7. Monthly trends insight
    mt = findings.get("monthly_trends")
    if mt and mt.get("months") and len(mt["months"]) >= 2:
        months = mt["months"]
        net_by_month = mt.get("net_by_month", {})
        first_net = net_by_month.get(months[0], 0)
        last_net = net_by_month.get(months[-1], 0)
        if last_net > first_net:
            growth = ((last_net - first_net) / abs(first_net) * 100) if first_net != 0 else 100
            insights.append({
                "priority": 2,
                "category": "Trend Analysis",
                "title": "Revenue trend is improving",
                "finding": f"Net profit grew from RM {first_net:.2f} in {months[0]} to RM {last_net:.2f} in {months[-1]} (+{growth:.1f}%).",
                "recommendation": "Maintain momentum. Identify what drove the growth and double down on it.",
                "rationale": "Positive momentum means your strategies are working. Sustaining growth compounds over time.",
            })
        elif last_net < first_net:
            decline = ((first_net - last_net) / abs(first_net) * 100) if first_net != 0 else 100
            insights.append({
                "priority": 1,
                "category": "Trend Analysis",
                "title": "Revenue trend is declining",
                "finding": f"Net profit dropped from RM {first_net:.2f} in {months[0]} to RM {last_net:.2f} in {months[-1]} (-{decline:.1f}%).",
                "recommendation": "Investigate the decline immediately. Check if it's seasonal, competitive, or operational. Act before it worsens.",
                "rationale": "Declining trends compound. The earlier you identify and address the cause, the less damage is done.",
            })

    # 8. Data quality insight
    dq = findings.get("data_quality")
    if dq:
        score = dq.get("score", 100)
        if score < 70:
            issues = dq.get("issues", [])
            issue_text = "; ".join(issues[:3]) if issues else "Multiple data quality issues detected."
            insights.append({
                "priority": 1,
                "category": "Data Quality",
                "title": f"Data quality score is {score}/100",
                "finding": issue_text,
                "recommendation": "Fix data issues before relying on these insights. Garbage in, garbage out — analysis is only as good as the data.",
                "rationale": "Low-quality data leads to misleading conclusions. Improving data quality improves decision quality.",
            })

    # Sort by priority (1 = highest)
    insights.sort(key=lambda x: x["priority"])
    return insights


def generate_data_quality_score(findings: dict, dataset_summary: dict = None) -> dict:
    """Assess data quality and return a score with issues list."""
    issues = []
    score = 100

    ds = dataset_summary or {}

    # Check completeness
    invoice_count = ds.get("invoice_count", 0)
    txn_count = ds.get("transaction_count", 0)
    if invoice_count == 0 and txn_count == 0:
        issues.append("No data records found")
        score -= 50
    elif invoice_count < 3:
        issues.append(f"Very few invoices ({invoice_count}) — results may not be representative")
        score -= 15
    elif txn_count < 5:
        issues.append(f"Very few transactions ({txn_count}) — analysis may be incomplete")
        score -= 10

    # Check reconciliation issues
    recon = findings.get("reconciliation")
    if recon:
        summary = recon.get("summary", {})
        total_issues = summary.get("total_issues", 0)
        critical = summary.get("critical_count", 0)
        if critical > 0:
            issues.append(f"{critical} critical data integrity issue(s) found")
            score -= min(critical * 10, 30)
        elif total_issues > 0:
            issues.append(f"{total_issues} minor data issue(s) flagged")
            score -= min(total_issues * 3, 15)

    # Check for missing key fields
    if ds and not ds.get("has_product_data"):
        issues.append("No product/category column — income categories used as proxy")
        score -= 5
    if ds and not ds.get("has_returns_data"):
        issues.append("No returns data — overdue invoices used as risk proxy")
        score -= 5

    # Check for empty findings (indicates analysis couldn't run properly)
    findings_keys = [k for k in findings.keys() if k != "data_quality"]
    if len(findings_keys) == 0:
        issues.append("Analysis produced no findings — data may be incompatible")
        score -= 40
    elif len(findings_keys) <= 2:
        issues.append("Limited analysis output — data may be too sparse for full insights")
        score -= 15

    score = max(0, min(100, score))
    return {
        "score": score,
        "issues": issues,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D",
    }
