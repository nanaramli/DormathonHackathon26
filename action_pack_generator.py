"""
action_pack_generator.py - Generate customer messages and a 30-minute action plan.

This module produces the "business action pack" — the final deliverable of
the full business review workflow:

    1. Customer Messages  — personalized follow-up messages for each
       customer with overdue or pending invoices, ready to copy-paste
       into WhatsApp/Email.

    2. Action Plan        — a prioritized list of tasks with estimated
       time for each, designed to be completed in ~30 minutes.

    3. Action Pack Summary — a one-page overview tying everything together.

The tone is friendly but professional — suitable for student entrepreneurs
running a campus business.
"""

from typing import Any
from datetime import datetime


def generate_customer_messages(
    invoices: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate follow-up messages for customers with unpaid invoices.

    Returns a list of message dicts:
        {
            "customer_name": str,
            "invoice_id": str,
            "amount_owed": float,
            "issue_date": str,
            "due_date": str,
            "status": str,        # overdue / pending / partial
            "channel": str,       # suggested channel (WhatsApp / Email)
            "subject": str,       # message subject/title
            "message": str,       # full message body (ready to send)
            "priority": int,     # 1 = most urgent
        }
    """
    messages = []

    # Sort by urgency: overdue first, then pending, then partial
    overdue = [inv for inv in invoices if inv.get("status") == "overdue"]
    pending = [inv for inv in invoices if inv.get("status") == "pending"]
    partial = [inv for inv in invoices if inv.get("status") == "partial"]

    # Sort each group by balance descending (biggest amounts first)
    overdue.sort(key=lambda i: i.get("balance_due_rm", 0), reverse=True)
    pending.sort(key=lambda i: i.get("balance_due_rm", 0), reverse=True)
    partial.sort(key=lambda i: i.get("balance_due_rm", 0), reverse=True)

    all_unpaid = overdue + pending + partial

    for i, inv in enumerate(all_unpaid, start=1):
        customer = inv.get("customer_name", "Customer")
        inv_id = inv.get("invoice_id", "")
        balance = inv.get("balance_due_rm", 0)
        inv_amount = inv.get("invoice_amount_rm", 0)
        paid = inv.get("amount_paid_rm", 0)
        due_date = inv.get("due_date", "")
        issue_date = inv.get("issue_date", "")
        status = inv.get("status", "pending")

        # Determine priority
        if status == "overdue":
            priority = 1
            channel = "WhatsApp"
            urgency = "overdue"
        elif status == "partial":
            priority = 2
            channel = "WhatsApp"
            urgency = "partially unpaid"
        else:
            priority = 3
            channel = "Email"
            urgency = "not yet due"

        # Build the message
        subject = f"Following up on Invoice {inv_id} ({urgency.capitalize()})"

        if status == "overdue":
            greeting = f"Hi {customer},"
            body = (
                f"I hope you're doing well! I'm following up on Invoice {inv_id} "
                f"for RM{inv_amount:.2f}, which was due on {due_date}. "
            )
            if paid > 0:
                body += (
                    f"I've received a partial payment of RM{paid:.2f}, "
                    f"leaving a balance of RM{balance:.2f}. "
                )
            else:
                body += f"The outstanding balance is RM{balance:.2f}. "
            body += (
                f"Could you please arrange payment at your earliest convenience? "
                f"If there are any issues or questions about the invoice, "
                f"just let me know — happy to help. Thank you!"
            )
            closing = "Best regards,\n[Your Name]"

        elif status == "partial":
            greeting = f"Hi {customer},"
            body = (
                f"Thank you for the partial payment of RM{paid:.2f} towards "
                f"Invoice {inv_id} (total: RM{inv_amount:.2f}). "
                f"The remaining balance is RM{balance:.2f}, due by {due_date}. "
                f"Just a friendly reminder to settle the balance when you get a chance. "
                f"Let me know if you need anything!"
            )
            closing = "Thanks again,\n[Your Name]"

        else:  # pending
            greeting = f"Hi {customer},"
            body = (
                f"Just a quick reminder about Invoice {inv_id} for RM{inv_amount:.2f}, "
                f"due on {due_date}. No rush — just wanted to make sure "
                f"you have all the details. The balance of RM{balance:.2f} "
                f"can be paid via bank transfer or e-wallet. Let me know "
                f"if you need the payment details again!"
            )
            closing = "Thanks,\n[Your Name]"

        message = f"{greeting}\n\n{body}\n\n{closing}"

        messages.append({
            "customer_name": customer,
            "invoice_id": inv_id,
            "amount_owed": round(balance, 2),
            "invoice_amount": round(inv_amount, 2),
            "amount_paid": round(paid, 2),
            "issue_date": issue_date,
            "due_date": due_date,
            "status": status,
            "channel": channel,
            "subject": subject,
            "message": message,
            "priority": priority,
        })

    return messages


def generate_action_plan(
    reconciliation: dict[str, Any],
    findings: dict[str, Any],
    actions: list[dict[str, Any]],
    customer_messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate a prioritized action plan with time estimates.

    Returns a list of action plan items:
        {
            "step": int,
            "title": str,
            "detail": str,
            "estimated_minutes": int,
            "category": str,   # "reconciliation" | "cash_flow" | "cost" | "growth" | "follow_up"
            "priority": int,   # 1 = highest
        }
    """
    plan: list[dict[str, Any]] = []
    step = 1

    # ---- Step 1: Fix critical reconciliation issues ----
    recon_summary = reconciliation.get("summary", {})
    if recon_summary.get("critical_count", 0) > 0:
        critical = [i for i in reconciliation.get("issues", []) if i["severity"] == "critical"]
        plan.append({
            "step": step,
            "title": f"Fix {len(critical)} critical data issue(s)",
            "detail": "; ".join(i["description"] for i in critical[:3]),
            "estimated_minutes": 5,
            "category": "reconciliation",
            "priority": 1,
        })
        step += 1

    # ---- Step 2: Send customer follow-up messages ----
    if customer_messages:
        overdue_count = sum(1 for m in customer_messages if m["status"] == "overdue")
        total_time = min(len(customer_messages) * 2, 10)
        plan.append({
            "step": step,
            "title": f"Send {len(customer_messages)} customer follow-up message(s)",
            "detail": (
                f"{overdue_count} overdue, "
                f"{sum(1 for m in customer_messages if m['status'] == 'pending')} pending. "
                f"Messages are pre-drafted in the customer_messages file."
            ),
            "estimated_minutes": total_time,
            "category": "follow_up",
            "priority": 1,
        })
        step += 1

    # ---- Step 3: Address amount mismatches ----
    mismatches = reconciliation.get("amount_mismatches", [])
    if mismatches:
        plan.append({
            "step": step,
            "title": f"Resolve {len(mismatches)} amount mismatch(es)",
            "detail": (
                "Invoice amounts don't match linked transactions. "
                "Check whether the invoice or transaction amount is wrong."
            ),
            "estimated_minutes": 3,
            "category": "reconciliation",
            "priority": 2,
        })
        step += 1

    # ---- Step 4: Review top expense category ----
    if "expense_ratio" in findings:
        er = findings["expense_ratio"]
        plan.append({
            "step": step,
            "title": f"Review {er['top_expense_category']} costs (top expense)",
            "detail": (
                f"{er['top_expense_category']} = RM{er['top_expense_amount']:.2f} "
                f"({er['expense_ratio_pct']}% of revenue). "
                f"Look for cheaper suppliers or bulk discounts."
            ),
            "estimated_minutes": 5,
            "category": "cost",
            "priority": 2,
        })
        step += 1

    # ---- Step 5: Expand most profitable category ----
    if "profit_by_category" in findings:
        pbc = findings["profit_by_category"]
        profitable = [c for c in pbc["categories"] if not c["is_loss_making"]]
        if profitable:
            best = max(profitable, key=lambda c: c["profit"])
            plan.append({
                "step": step,
                "title": f"Plan growth for {best['category']} (most profitable)",
                "detail": (
                    f"{best['category']} has {best['profit_margin_pct']}% margin. "
                    f"Brainstorm 1-2 ways to get more customers or raise prices."
                ),
                "estimated_minutes": 3,
                "category": "growth",
                "priority": 3,
            })
            step += 1

    # ---- Step 6: Record orphan invoice transactions ----
    orphan_invs = reconciliation.get("orphan_invoices", [])
    if orphan_invs:
        plan.append({
            "step": step,
            "title": f"Record {len(orphan_invs)} missing income transaction(s)",
            "detail": (
                f"{len(orphan_invs)} invoice(s) have no linked income transaction. "
                f"Record them to keep your books accurate."
            ),
            "estimated_minutes": 2,
            "category": "reconciliation",
            "priority": 3,
        })
        step += 1

    # ---- Step 7: Quick review of revenue concentration ----
    if "revenue_concentration" in findings:
        rc = findings["revenue_concentration"]
        if rc["is_concentrated"]:
            plan.append({
                "step": step,
                "title": f"Plan to diversify beyond {rc['top_category']}",
                "detail": (
                    f"{rc['top_category']} = {rc['top_category_share_pct']}% of revenue. "
                    f"Think about adding a complementary service."
                ),
                "estimated_minutes": 2,
                "category": "growth",
                "priority": 3,
            })
            step += 1

    # Calculate total time
    total_min = sum(item["estimated_minutes"] for item in plan)

    # Add summary item
    plan.insert(0, {
        "step": 0,
        "title": f"Business Action Plan (~{total_min} minutes)",
        "detail": (
            f"{len(plan)} tasks to complete. "
            f"Estimated total time: {total_min} minutes. "
            f"Customer messages are pre-drafted and ready to send."
        ),
        "estimated_minutes": 0,
        "category": "summary",
        "priority": 0,
    })

    # Re-number steps
    for i, item in enumerate(plan):
        if item["step"] == 0:
            continue
        item["step"] = i

    return plan


def generate_action_pack_summary(
    reconciliation: dict[str, Any],
    findings: dict[str, Any],
    actions: list[dict[str, Any]],
    customer_messages: list[dict[str, Any]],
    action_plan: list[dict[str, Any]],
    instruction: str,
) -> str:
    """Generate a one-page text summary of the entire business action pack."""
    lines = []
    lines.append("=" * 72)
    lines.append("  RichBuddy Business Action Pack")
    lines.append("  Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  Instruction: {instruction}")
    lines.append("")

    # Reconciliation summary
    rs = reconciliation.get("summary", {})
    lines.append("-" * 72)
    lines.append("  1. DATA RECONCILIATION")
    lines.append("-" * 72)
    lines.append(f"  Status: {'PASS' if rs.get('is_reconciled') else 'ISSUES FOUND'}")
    lines.append(f"  Issues: {rs.get('total_issues', 0)} "
                 f"({rs.get('critical_count', 0)} critical, "
                 f"{rs.get('warning_count', 0)} warnings, "
                 f"{rs.get('info_count', 0)} info)")
    if reconciliation.get("orphan_invoices"):
        lines.append(f"  Orphan invoices (no income transaction): {len(reconciliation['orphan_invoices'])}")
    if reconciliation.get("orphan_transactions"):
        lines.append(f"  Orphan transactions (unknown invoice ref): {len(reconciliation['orphan_transactions'])}")
    if reconciliation.get("amount_mismatches"):
        lines.append(f"  Amount mismatches: {len(reconciliation['amount_mismatches'])}")
    lines.append("")

    # Financial overview
    lines.append("-" * 72)
    lines.append("  2. FINANCIAL OVERVIEW")
    lines.append("-" * 72)
    if "net_profit" in findings:
        np = findings["net_profit"]
        lines.append(f"  Revenue:        RM {np['total_revenue']:,.2f}")
        lines.append(f"  Expenses:       RM {np['total_expenses']:,.2f}")
        lines.append(f"  Net Profit:     RM {np['net_profit']:,.2f}")
        lines.append(f"  Margin:         {np['profit_margin_pct']}%")
    if "outstanding" in findings:
        out = findings["outstanding"]
        lines.append(f"  Outstanding:    RM {out['total_outstanding']:,.2f}")
        lines.append(f"  Overdue:        RM {out['overdue_amount']:,.2f}")
        lines.append(f"  Collection:     {out['collection_rate_pct']}%")
    if "expense_ratio" in findings:
        er = findings["expense_ratio"]
        lines.append(f"  Expense Ratio:  {er['expense_ratio_pct']}%")
        lines.append(f"  Top Expense:    {er['top_expense_category']} (RM{er['top_expense_amount']:.2f})")
    lines.append("")

    # Customer messages
    lines.append("-" * 72)
    lines.append("  3. CUSTOMER FOLLOW-UP MESSAGES")
    lines.append("-" * 72)
    if customer_messages:
        lines.append(f"  {len(customer_messages)} message(s) drafted and ready to send:")
        for m in customer_messages:
            lines.append(f"    P{m['priority']} | {m['customer_name']} | {m['invoice_id']} | "
                         f"RM{m['amount_owed']:.2f} ({m['status']}) | via {m['channel']}")
    else:
        lines.append("  All invoices are paid. No follow-up messages needed.")
    lines.append("")

    # Action plan
    lines.append("-" * 72)
    lines.append("  4. ACTION PLAN")
    lines.append("-" * 72)
    for item in action_plan:
        if item["step"] == 0:
            lines.append(f"  {item['title']}")
            lines.append(f"  {item['detail']}")
            lines.append("")
        else:
            lines.append(f"  Step {item['step']}: {item['title']} ({item['estimated_minutes']} min)")
            lines.append(f"    {item['detail']}")
            lines.append("")

    # Files
    lines.append("-" * 72)
    lines.append("  5. FILES IN THIS ACTION PACK")
    lines.append("-" * 72)
    lines.append("  - action_pack_summary.txt     (this file)")
    lines.append("  - customer_messages.txt       (pre-drafted messages to copy-paste)")
    lines.append("  - customer_messages.csv       (structured message data)")
    lines.append("  - action_plan.csv             (structured action plan)")
    lines.append("  - richbuddy_report_*.txt      (full analysis report)")
    lines.append("  - *.csv                       (category, profit, invoice data)")
    lines.append("")
    lines.append("=" * 72)
    lines.append("  You can finish this in 30 minutes. Go get it done!")
    lines.append("=" * 72)
    lines.append("")

    return "\n".join(lines)
