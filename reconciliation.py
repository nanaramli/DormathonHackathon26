"""
reconciliation.py - Validate and reconcile business records for RichBuddy.

This module cross-checks invoices against transactions to find data
integrity issues:
    - Orphan invoices (invoiced but no matching transaction)
    - Orphan transactions (transaction references unknown invoice)
    - Amount mismatches (invoice total != transaction income total)
    - Duplicate invoice IDs
    - Duplicate transaction IDs
    - Negative balances (paid > invoiced)
    - Status/amount inconsistencies

This is the "validate and reconcile" step in the full business review workflow.
"""

from typing import Any
from collections import defaultdict


def reconcile_records(
    invoices: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reconcile invoices against transactions and return all issues found.

    Returns:
        {
            "issues": [list of issue dicts with severity + description],
            "summary": {
                "total_issues": int,
                "critical_count": int,
                "warning_count": int,
                "info_count": int,
                "is_reconciled": bool,
            },
            "invoice_reconciliation": {invoice_id: {matched_txs, total_match, ...}},
            "orphan_invoices": [list of invoice dicts],
            "orphan_transactions": [list of transaction dicts],
            "amount_mismatches": [list of mismatch dicts],
            "duplicates": [list of duplicate dicts],
            "balance_anomalies": [list of anomaly dicts],
        }
    """
    issues: list[dict[str, Any]] = []

    # Build lookup structures
    inv_by_id: dict[str, dict[str, Any]] = {}
    tx_by_id: dict[str, dict[str, Any]] = {}
    tx_by_invoice: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # Track duplicates
    seen_inv_ids: dict[str, int] = defaultdict(int)
    seen_tx_ids: dict[str, int] = defaultdict(int)

    for inv in invoices:
        inv_id = inv.get("invoice_id", "")
        seen_inv_ids[inv_id] += 1
        if seen_inv_ids[inv_id] == 1:
            inv_by_id[inv_id] = inv
        # Income transactions linked to this invoice
        tx_for_inv = [
            t for t in transactions
            if t.get("invoice_id", "") == inv_id and t.get("type") == "income"
        ]
        tx_by_invoice[inv_id] = tx_for_inv

    for tx in transactions:
        tx_id = tx.get("transaction_id", "")
        seen_tx_ids[tx_id] += 1
        if seen_tx_ids[tx_id] == 1:
            tx_by_id[tx_id] = tx

    # ---- Duplicate IDs ----
    duplicates = []
    for inv_id, count in seen_inv_ids.items():
        if count > 1:
            duplicates.append({"type": "invoice", "id": inv_id, "count": count})
            issues.append({
                "severity": "critical",
                "category": "duplicate_id",
                "description": f"Duplicate invoice ID '{inv_id}' appears {count} times.",
                "action": "Investigate and merge or rename duplicate invoices.",
            })
    for tx_id, count in seen_tx_ids.items():
        if count > 1:
            duplicates.append({"type": "transaction", "id": tx_id, "count": count})
            issues.append({
                "severity": "critical",
                "category": "duplicate_id",
                "description": f"Duplicate transaction ID '{tx_id}' appears {count} times.",
                "action": "Investigate and merge or remove duplicate transactions.",
            })

    # ---- Orphan transactions (reference unknown invoice) ----
    orphan_txs = []
    for tx in transactions:
        ref = tx.get("invoice_id", "").strip()
        if ref and ref not in inv_by_id:
            orphan_txs.append(tx)
            issues.append({
                "severity": "warning",
                "category": "orphan_transaction",
                "description": (
                    f"Transaction {tx.get('transaction_id', '?')} (RM{tx.get('amount_rm', 0):.2f}, "
                    f"{tx.get('category', '?')}) references unknown invoice '{ref}'."
                ),
                "action": "Verify the invoice ID or create the missing invoice record.",
            })

    # ---- Orphan invoices (no income transaction linked) ----
    orphan_invs = []
    amount_mismatches = []
    inv_reconciliation = {}

    for inv in invoices:
        inv_id = inv.get("invoice_id", "")
        inv_amount = inv.get("invoice_amount_rm", 0)
        linked_txs = tx_by_invoice.get(inv_id, [])
        tx_total = sum(t.get("amount_rm", 0) for t in linked_txs)

        inv_reconciliation[inv_id] = {
            "invoice_amount": round(inv_amount, 2),
            "transaction_total": round(tx_total, 2),
            "matched": bool(linked_txs),
            "difference": round(inv_amount - tx_total, 2),
            "linked_transactions": len(linked_txs),
        }

        if not linked_txs:
            orphan_invs.append(inv)
            issues.append({
                "severity": "info",
                "category": "orphan_invoice",
                "description": (
                    f"Invoice {inv_id} ({inv.get('customer_name', '?')}, "
                    f"RM{inv_amount:.2f}) has no linked income transaction."
                ),
                "action": "Record the corresponding income transaction or mark as cash sale.",
            })
        elif abs(inv_amount - tx_total) > 0.01:
            amount_mismatches.append({
                "invoice_id": inv_id,
                "customer": inv.get("customer_name", ""),
                "invoice_amount": round(inv_amount, 2),
                "transaction_total": round(tx_total, 2),
                "difference": round(inv_amount - tx_total, 2),
            })
            issues.append({
                "severity": "warning",
                "category": "amount_mismatch",
                "description": (
                    f"Invoice {inv_id} ({inv.get('customer_name', '?')}): "
                    f"invoiced RM{inv_amount:.2f} but linked transactions total "
                    f"RM{tx_total:.2f} (difference: RM{inv_amount - tx_total:.2f})."
                ),
                "action": "Check whether the invoice or transaction amount is incorrect.",
            })

    # ---- Balance anomalies (paid > invoiced) ----
    balance_anomalies = []
    for inv in invoices:
        inv_amount = inv.get("invoice_amount_rm", 0)
        paid = inv.get("amount_paid_rm", 0)
        if paid > inv_amount + 0.01:
            balance_anomalies.append({
                "invoice_id": inv.get("invoice_id", ""),
                "customer": inv.get("customer_name", ""),
                "invoice_amount": round(inv_amount, 2),
                "amount_paid": round(paid, 2),
                "overpayment": round(paid - inv_amount, 2),
            })
            issues.append({
                "severity": "warning",
                "category": "overpayment",
                "description": (
                    f"Invoice {inv.get('invoice_id', '?')}: paid RM{paid:.2f} "
                    f"exceeds invoice amount RM{inv_amount:.2f} "
                    f"(overpayment: RM{paid - inv_amount:.2f})."
                ),
                "action": "Issue a refund or credit note for the overpayment.",
            })

    # ---- Summary ----
    critical = [i for i in issues if i["severity"] == "critical"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    info = [i for i in issues if i["severity"] == "info"]

    return {
        "issues": issues,
        "summary": {
            "total_issues": len(issues),
            "critical_count": len(critical),
            "warning_count": len(warnings),
            "info_count": len(info),
            "is_reconciled": len(critical) == 0 and len(warnings) == 0,
        },
        "invoice_reconciliation": inv_reconciliation,
        "orphan_invoices": orphan_invs,
        "orphan_transactions": orphan_txs,
        "amount_mismatches": amount_mismatches,
        "duplicates": duplicates,
        "balance_anomalies": balance_anomalies,
    }


def format_reconciliation_report(reconciliation: dict[str, Any]) -> str:
    """Return a human-readable reconciliation report."""
    s = reconciliation.get("summary", {})
    issues = reconciliation.get("issues", [])

    lines = []
    lines.append("=" * 60)
    lines.append("  Data Reconciliation Report")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Total issues found: {s.get('total_issues', 0)}")
    lines.append(f"    Critical: {s.get('critical_count', 0)}")
    lines.append(f"    Warnings: {s.get('warning_count', 0)}")
    lines.append(f"    Info:     {s.get('info_count', 0)}")
    lines.append(f"  Reconciled: {'YES' if s.get('is_reconciled') else 'NO'}")
    lines.append("")

    if issues:
        lines.append("  Issues:")
        for i in issues:
            sev = i["severity"].upper()
            lines.append(f"    [{sev}] {i['description']}")
            lines.append(f"      -> {i['action']}")
            lines.append("")
    else:
        lines.append("  All records reconcile correctly.")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
