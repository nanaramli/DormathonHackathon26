"""
file_generator.py - Generate report and CSV output files for RichBuddy.

This module writes the results of analysis into real, usable files:
    - Text reports (.txt) with human-readable findings and recommendations
    - CSV files with structured data tables

All files are written to a dedicated output directory.
"""

import csv
import os
from datetime import datetime
from typing import Any


def ensure_output_dir(output_dir: str) -> str:
    """Create the output directory if it doesn't exist and return its path."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _timestamp() -> str:
    """Return a filesystem-safe timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def generate_text_report(
    result: dict[str, Any],
    output_dir: str,
) -> str:
    """Write a comprehensive text report for an analysis result.

    The *result* dict is produced by the orchestrator and contains:
        - intent, instruction, confidence
        - findings (dict of analysis outputs)
        - actions (list of prioritised recommendations)
        - dataset_summary
        - data_notes (limitations / transparency notes)

    Returns the path to the generated .txt file.
    """
    ensure_output_dir(output_dir)
    ts = _timestamp()
    intent_label = result.get("intent", "unknown")
    filename = f"richbuddy_report_{intent_label}_{ts}.txt"
    filepath = os.path.join(output_dir, filename)

    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("  RichBuddy - Business Analysis Report")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"Generated:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Instruction:      {result.get('instruction', 'N/A')}")
    lines.append(f"Intent:           {intent_label}")
    lines.append(f"Confidence:       {result.get('confidence', 'N/A')}")
    lines.append(f"Intent Method:    {result.get('method', 'N/A')}")
    if result.get("method") == "rule_based":
        lines.append(
            "                  (Rule-based intent recognition -- no LLM was used.)"
        )
    lines.append("")

    # --- Dataset summary ---
    ds = result.get("dataset_summary", {})
    if ds:
        lines.append("-" * 72)
        lines.append("  Dataset Summary")
        lines.append("-" * 72)
        lines.append(f"  Invoices:         {ds.get('invoice_count', 0)}")
        lines.append(f"  Transactions:     {ds.get('transaction_count', 0)}")
        lines.append(f"  Income records:   {ds.get('income_transaction_count', 0)}")
        lines.append(f"  Expense records:  {ds.get('expense_transaction_count', 0)}")
        lines.append(f"  Income categories:   {', '.join(ds.get('income_categories', []))}")
        lines.append(f"  Expense categories:  {', '.join(ds.get('expense_categories', []))}")
        lines.append(f"  Invoice statuses:    {', '.join(ds.get('invoice_statuses', []))}")
        lines.append("")

    # --- Findings ---
    findings = result.get("findings", {})
    if findings:
        lines.append("-" * 72)
        lines.append("  Analysis Findings")
        lines.append("-" * 72)
        lines.append("")
        lines.append(_format_findings(findings, indent="  "))
        lines.append("")

    # --- Actions / Recommendations ---
    actions = result.get("actions", [])
    if actions:
        lines.append("-" * 72)
        lines.append("  Prioritised Business Recommendations")
        lines.append("-" * 72)
        lines.append("")
        for a in actions:
            lines.append(f"  Priority {a['priority']}: {a['title']}")
            lines.append(f"    Finding:         {a['finding']}")
            lines.append(f"    Recommendation:  {a['recommendation']}")
            lines.append(f"    Why it matters:  {a['rationale']}")
            lines.append(f"    Data source:     {a['data_source']}")
            lines.append("")

    # --- Data notes / transparency ---
    notes = result.get("data_notes", [])
    if notes:
        lines.append("-" * 72)
        lines.append("  Data Notes & Limitations")
        lines.append("-" * 72)
        lines.append("")
        for note in notes:
            lines.append(f"  - {note}")
        lines.append("")

    lines.append("=" * 72)
    lines.append("  End of Report")
    lines.append("=" * 72)
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


def generate_csv_file(
    rows: list[dict[str, Any]],
    filename: str,
    output_dir: str,
) -> str:
    """Write a list of dicts to a CSV file.

    Returns the path to the generated file.
    """
    ensure_output_dir(output_dir)
    filepath = os.path.join(output_dir, filename)

    if not rows:
        # Write an empty file with a note
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["note"])
            writer.writerow(["No data available for this analysis."])
        return filepath

    fieldnames = list(rows[0].keys())
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def generate_analysis_csvs(
    result: dict[str, Any],
    output_dir: str,
) -> list[str]:
    """Generate all relevant CSV files for an analysis result.

    Returns a list of generated file paths.
    """
    ensure_output_dir(output_dir)
    ts = _timestamp()
    intent = result.get("intent", "unknown")
    findings = result.get("findings", {})
    files: list[str] = []

    # Category summary CSV (always useful)
    if "category_summary" in findings:
        rows = findings["category_summary"]
        path = generate_csv_file(
            rows, f"category_summary_{ts}.csv", output_dir
        )
        files.append(path)

    # Profit by category CSV
    if "profit_by_category" in findings:
        pbc = findings["profit_by_category"]
        rows = pbc["categories"]
        path = generate_csv_file(
            rows, f"profit_by_category_{ts}.csv", output_dir
        )
        files.append(path)

    # Invoice status CSV
    if "invoice_status" in findings:
        inv_st = findings["invoice_status"]
        rows = [
            {"status": k, "count": v, "total_amount_rm": inv_st["by_status_amount"].get(k, 0)}
            for k, v in inv_st["by_status"].items()
        ]
        path = generate_csv_file(
            rows, f"invoice_status_{ts}.csv", output_dir
        )
        files.append(path)

    # Outstanding invoices CSV
    if "outstanding" in findings:
        out = findings["outstanding"]
        rows = []
        for inv in out.get("overdue_invoices", []) + out.get("pending_invoices", []):
            rows.append({
                "invoice_id": inv["invoice_id"],
                "customer_name": inv["customer_name"],
                "issue_date": inv["issue_date"],
                "due_date": inv["due_date"],
                "invoice_amount_rm": inv["invoice_amount_rm"],
                "amount_paid_rm": inv["amount_paid_rm"],
                "balance_due_rm": inv["balance_due_rm"],
                "status": inv["status"],
            })
        if rows:
            path = generate_csv_file(
                rows, f"outstanding_invoices_{ts}.csv", output_dir
            )
            files.append(path)

    # Monthly trends CSV
    if "monthly_trends" in findings:
        mt = findings["monthly_trends"]
        rows = []
        for m in mt["months"]:
            rows.append({
                "month": m,
                "income_rm": mt["income_by_month"].get(m, 0),
                "expense_rm": mt["expense_by_month"].get(m, 0),
                "net_rm": mt["net_by_month"].get(m, 0),
            })
        path = generate_csv_file(
            rows, f"monthly_trends_{ts}.csv", output_dir
        )
        files.append(path)

    # Customer breakdown CSV
    if "customer_breakdown" in findings:
        cb = findings["customer_breakdown"]
        rows = []
        for cust in cb["customers"]:
            rows.append({
                "customer_name": cust,
                "invoiced_rm": cb["invoiced_by_customer"].get(cust, 0),
                "outstanding_rm": cb["outstanding_by_customer"].get(cust, 0),
            })
        path = generate_csv_file(
            rows, f"customer_breakdown_{ts}.csv", output_dir
        )
        files.append(path)

    # Actions CSV
    actions = result.get("actions", [])
    if actions:
        path = generate_csv_file(
            actions, f"recommendations_{ts}.csv", output_dir
        )
        files.append(path)

    return files


# ---------------------------------------------------------------------------
# Internal formatting helpers
# ---------------------------------------------------------------------------
def _format_findings(findings: dict[str, Any], indent: str = "") -> str:
    """Recursively format findings dict into readable text."""
    lines: list[str] = []

    for key, value in findings.items():
        label = key.replace("_", " ").title()
        if isinstance(value, dict):
            lines.append(f"{indent}{label}:")
            lines.append(_format_dict(value, indent + "  "))
        elif isinstance(value, list):
            lines.append(f"{indent}{label}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(_format_dict(item, indent + "  - "))
                else:
                    lines.append(f"{indent}  - {item}")
        else:
            lines.append(f"{indent}{label}: {value}")

    return "\n".join(lines)


def _format_dict(d: dict[str, Any], prefix: str = "") -> str:
    """Format a flat dict as key: value lines."""
    lines: list[str] = []
    for k, v in d.items():
        if isinstance(v, (list, dict)):
            # Skip nested structures in this simple formatter
            continue
        label = k.replace("_", " ").title()
        lines.append(f"{prefix}{label}: {v}")
    return "\n".join(lines)
