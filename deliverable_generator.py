"""
deliverable_generator.py - Generate verified business deliverables for RichBuddy.

For each completed task, generates:
1. business_action_report.md  - Full Markdown report with instruction, dataset,
   metrics, findings, recommendations, verification results, limitations, status.
2. prioritised_recommendations.csv  - Structured, evidence-backed recommendations.
3. execution_summary.json  - Planned/completed steps, failures, retries,
   validation outcomes, output paths, final status.
4. business_findings.csv  - When it adds practical value (per-category breakdown).

All files are written to a safe output directory. Files are reopened and
validated before reporting completion.
"""

import csv
import json
import os
from datetime import datetime
from typing import Any


def generate_deliverables(
    result: dict[str, Any],
    verification_report: dict[str, Any],
    execution_log: list[dict[str, Any]],
    output_dir: str,
) -> dict[str, Any]:
    """Generate all verified business deliverables.

    Args:
        result: The orchestrator result dict (findings, actions, dataset_summary, etc.)
        verification_report: Output from self_verifier.run_verification()
        execution_log: List of step dicts from the autonomous workflow
        output_dir: Directory where files will be written

    Returns:
        dict with:
            - files: list of generated file paths
            - report_path: path to business_action_report.md
            - recommendations_path: path to prioritised_recommendations.csv
            - execution_summary_path: path to execution_summary.json
            - findings_path: path to business_findings.csv (or None)
            - validated: bool - whether all files were reopened successfully
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    generated_files: list[str] = []
    validation_errors: list[str] = []

    # ==================================================================
    # 1. business_action_report.md
    # ==================================================================
    report_path = os.path.join(output_dir, f"business_action_report_{ts}.md")
    _write_report(result, verification_report, report_path)
    generated_files.append(report_path)

    # Validate: reopen and check non-empty
    if not _validate_text_file(report_path):
        validation_errors.append(f"Report file invalid: {report_path}")

    # ==================================================================
    # 2. prioritised_recommendations.csv
    # ==================================================================
    recs_path = os.path.join(output_dir, f"prioritised_recommendations_{ts}.csv")
    _write_recommendations_csv(result, recs_path)
    generated_files.append(recs_path)

    if not _validate_csv_file(recs_path):
        validation_errors.append(f"Recommendations CSV invalid: {recs_path}")

    # ==================================================================
    # 3. execution_summary.json
    # ==================================================================
    summary_path = os.path.join(output_dir, f"execution_summary_{ts}.json")
    _write_execution_summary(result, verification_report, execution_log, summary_path)
    generated_files.append(summary_path)

    if not _validate_json_file(summary_path):
        validation_errors.append(f"Execution summary JSON invalid: {summary_path}")

    # ==================================================================
    # 4. business_findings.csv (when it adds practical value)
    # ==================================================================
    findings_path = None
    findings = result.get("findings", {})
    if "category_summary" in findings or "profit_by_category" in findings:
        findings_path = os.path.join(output_dir, f"business_findings_{ts}.csv")
        _write_findings_csv(findings, findings_path)
        generated_files.append(findings_path)

        if not _validate_csv_file(findings_path):
            validation_errors.append(f"Findings CSV invalid: {findings_path}")

    return {
        "files": generated_files,
        "report_path": report_path,
        "recommendations_path": recs_path,
        "execution_summary_path": summary_path,
        "findings_path": findings_path,
        "validated": len(validation_errors) == 0,
        "validation_errors": validation_errors,
    }


# ==========================================================================
# Report writer (Markdown)
# ==========================================================================
def _write_report(
    result: dict[str, Any],
    verification: dict[str, Any],
    filepath: str,
) -> None:
    """Write the business_action_report.md file."""
    findings = result.get("findings", {})
    actions = result.get("actions", [])
    ds = result.get("dataset_summary", {})
    notes = result.get("data_notes", [])
    insights = result.get("smart_insights", [])
    pipeline = result.get("pipeline_steps", [])
    np = findings.get("net_profit", {})
    dq = findings.get("data_quality", {})

    lines: list[str] = []
    lines.append("# RichBuddy Business Action Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Final Status:** {verification.get('overall_status', 'UNKNOWN')}")
    lines.append("")

    # --- Instruction ---
    lines.append("## 1. Instruction")
    lines.append("")
    lines.append(f"> {result.get('instruction', 'N/A')}")
    lines.append(f"- **Intent detected:** {result.get('intent', 'N/A')}")
    lines.append(f"- **Confidence:** {result.get('confidence', 'N/A')}")
    lines.append(f"- **Method:** {result.get('method', 'N/A')} (rule-based, no LLM required)")
    lines.append("")

    # --- Dataset details ---
    lines.append("## 2. Dataset Details")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Invoices | {ds.get('invoice_count', 0)} |")
    lines.append(f"| Transactions | {ds.get('transaction_count', 0)} |")
    lines.append(f"| Income records | {ds.get('income_transaction_count', 0)} |")
    lines.append(f"| Expense records | {ds.get('expense_transaction_count', 0)} |")
    income_cats = ds.get("income_categories", [])
    lines.append(f"| Income categories | {', '.join(income_cats) if income_cats else 'N/A'} |")
    expense_cats = ds.get("expense_categories", [])
    lines.append(f"| Expense categories | {', '.join(expense_cats) if expense_cats else 'N/A'} |")
    lines.append("")

    # --- Key metrics ---
    lines.append("## 3. Key Metrics")
    lines.append("")
    if np:
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Revenue | RM {np.get('total_revenue', 0):.2f} |")
        lines.append(f"| Total Expenses | RM {np.get('total_expenses', 0):.2f} |")
        lines.append(f"| Net Profit | RM {np.get('net_profit', 0):.2f} |")
        lines.append(f"| Profit Margin | {np.get('profit_margin_pct', 0):.1f}% |")
        lines.append("")
    else:
        lines.append("_No financial totals available for this dataset._")
        lines.append("")

    # Data quality
    if dq:
        lines.append(f"**Data Quality Score:** {dq.get('score', 0)}/100 (Grade {dq.get('grade', 'N/A')})")
        if dq.get("issues"):
            lines.append("")
            for issue in dq["issues"]:
                lines.append(f"- {issue}")
        lines.append("")

    # --- Findings ---
    lines.append("## 4. Findings")
    lines.append("")
    if findings:
        # Category summary
        cat_sum = findings.get("category_summary", [])
        if cat_sum:
            lines.append("### Category Summary")
            lines.append("")
            lines.append("| Category | Income (RM) | Expense (RM) | Net (RM) |")
            lines.append("|----------|-------------|-------------|----------|")
            for c in cat_sum:
                lines.append(
                    f"| {c.get('category', 'N/A')} | {c.get('income_rm', 0):.2f} | "
                    f"{c.get('expense_rm', 0):.2f} | {c.get('net_rm', 0):.2f} |"
                )
            lines.append("")

        # Profit by category
        pbc = findings.get("profit_by_category", {})
        if pbc and pbc.get("categories"):
            lines.append("### Profit by Category")
            lines.append("")
            lines.append("| Category | Revenue (RM) | Profit (RM) | Margin (%) | Status |")
            lines.append("|----------|-------------|-------------|------------|--------|")
            for c in pbc["categories"]:
                status = "Loss" if c.get("is_loss_making") else "Profit"
                lines.append(
                    f"| {c.get('category', 'N/A')} | {c.get('revenue', 0):.2f} | "
                    f"{c.get('profit', 0):.2f} | {c.get('profit_margin_pct', 0):.1f}% | {status} |"
                )
            lines.append("")

        # Monthly trends
        mt = findings.get("monthly_trends", {})
        if mt and mt.get("months"):
            lines.append("### Monthly Trends")
            lines.append("")
            lines.append("| Month | Income (RM) | Expense (RM) | Net (RM) |")
            lines.append("|-------|-------------|-------------|----------|")
            for m in mt["months"]:
                lines.append(
                    f"| {m} | {mt['income_by_month'].get(m, 0):.2f} | "
                    f"{mt['expense_by_month'].get(m, 0):.2f} | "
                    f"{mt['net_by_month'].get(m, 0):.2f} |"
                )
            lines.append("")

        # Outstanding invoices
        out = findings.get("outstanding", {})
        if out:
            lines.append("### Outstanding Invoices")
            lines.append("")
            lines.append(f"- Total outstanding: RM {out.get('total_outstanding', 0):.2f}")
            lines.append(f"- Overdue amount: RM {out.get('overdue_amount', 0):.2f}")
            lines.append(f"- Collection rate: {out.get('collection_rate_pct', 0):.1f}%")
            lines.append("")

        # Regional analysis
        ra = findings.get("regional_analysis", {})
        if ra and ra.get("regions"):
            lines.append("### Regional Analysis")
            lines.append("")
            lines.append("| Region | Revenue (RM) | Expense (RM) | Profit (RM) | Margin (%) |")
            lines.append("|--------|-------------|-------------|-------------|------------|")
            for r in ra["regions"]:
                lines.append(
                    f"| {r.get('region', 'N/A')} | {r.get('revenue', 0):.2f} | "
                    f"{r.get('expense', 0):.2f} | {r.get('profit', 0):.2f} | "
                    f"{r.get('profit_margin_pct', 0):.1f}% |"
                )
            lines.append("")
    else:
        lines.append("_No findings available for this dataset._")
        lines.append("")

    # --- Recommendations ---
    lines.append("## 5. Recommended Actions")
    lines.append("")
    if actions:
        for i, a in enumerate(actions, 1):
            lines.append(f"### Action {i}: {a.get('title', 'N/A')} (Priority {a.get('priority', 'N/A')})")
            lines.append("")
            lines.append(f"**Problem/Opportunity:** {a.get('finding', 'N/A')}")
            lines.append(f"**Recommended Action:** {a.get('recommendation', 'N/A')}")
            lines.append(f"**Why It Matters:** {a.get('rationale', 'N/A')}")
            lines.append(f"**Data Source:** {a.get('data_source', 'N/A')}")
            lines.append(f"**Implementation Effort:** {_effort_label(a.get('priority', 3))}")
            lines.append("")
    else:
        lines.append("_No recommendations could be generated from the available data._")
        lines.append("")

    # --- Smart Insights ---
    if insights:
        lines.append("## 6. Smart Insights")
        lines.append("")
        for ins in insights:
            badge = {"1": "CRITICAL", "2": "IMPORTANT", "3": "GOOD"}.get(str(ins.get("priority", 3)), "INFO")
            lines.append(f"**[{badge}] {ins.get('title', 'N/A')}** ({ins.get('category', 'N/A')})")
            lines.append(f"- **Finding:** {ins.get('finding', 'N/A')}")
            lines.append(f"- **Recommendation:** {ins.get('recommendation', 'N/A')}")
            lines.append(f"- **Rationale:** {ins.get('rationale', 'N/A')}")
            lines.append("")

    # --- Verification ---
    lines.append("## 7. Verification Results")
    lines.append("")
    checks = verification.get("checks", [])
    if checks:
        lines.append("| Check | Status | Severity | Detail |")
        lines.append("|------|--------|----------|--------|")
        for c in checks:
            status_emoji = "PASS" if c["status"] == "PASS" else "FAIL"
            lines.append(
                f"| {c.get('description', 'N/A')} | {status_emoji} | "
                f"{c.get('severity', 'N/A')} | {c.get('detail', 'N/A')} |"
            )
        lines.append("")
        summary = verification.get("summary", {})
        lines.append(f"**Overall Status:** {verification.get('overall_status', 'N/A')}")
        lines.append(f"**Checks:** {summary.get('passed', 0)} passed, "
                      f"{summary.get('failed_critical', 0)} critical failures, "
                      f"{summary.get('failed_warning', 0)} warnings, "
                      f"{summary.get('skipped', 0)} skipped out of {summary.get('total', 0)} total")
        lines.append("")
    else:
        lines.append("_No verification checks were run._")
        lines.append("")

    # --- Limitations ---
    lines.append("## 8. Limitations & Notes")
    lines.append("")
    if notes:
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    else:
        lines.append("_No limitations noted._")
        lines.append("")

    # --- Pipeline ---
    if pipeline:
        lines.append("## 9. Execution Pipeline")
        lines.append("")
        lines.append("| Step | Name | Status | Detail |")
        lines.append("|------|------|--------|--------|")
        for s in pipeline:
            lines.append(
                f"| {s.get('step', '?')} | {s.get('name', 'N/A')} | "
                f"{s.get('status', 'N/A')} | {s.get('detail', '')} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("*Generated by RichBuddy - Autonomous Business Co-Pilot for Student Entrepreneurs*")
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ==========================================================================
# Recommendations CSV writer
# ==========================================================================
def _write_recommendations_csv(result: dict[str, Any], filepath: str) -> None:
    """Write prioritised_recommendations.csv."""
    actions = result.get("actions", [])
    fieldnames = [
        "priority", "title", "finding", "recommendation",
        "rationale", "data_source", "implementation_effort",
    ]

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for a in actions:
            writer.writerow({
                "priority": a.get("priority", ""),
                "title": a.get("title", ""),
                "finding": a.get("finding", ""),
                "recommendation": a.get("recommendation", ""),
                "rationale": a.get("rationale", ""),
                "data_source": a.get("data_source", ""),
                "implementation_effort": _effort_label(a.get("priority", 3)),
            })


# ==========================================================================
# Execution summary JSON writer
# ==========================================================================
def _write_execution_summary(
    result: dict[str, Any],
    verification: dict[str, Any],
    execution_log: list[dict[str, Any]],
    filepath: str,
) -> None:
    """Write execution_summary.json."""
    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "instruction": result.get("instruction", ""),
        "intent": result.get("intent", ""),
        "confidence": result.get("confidence", ""),
        "method": result.get("method", ""),
        "final_status": verification.get("overall_status", "UNKNOWN"),
        "execution_log": execution_log,
        "verification": {
            "overall_status": verification.get("overall_status", "UNKNOWN"),
            "summary": verification.get("summary", {}),
            "errors": verification.get("errors", []),
            "warnings": verification.get("warnings", []),
        },
        "output_files": result.get("csv_paths", []) + [result.get("report_path", "")],
        "dataset_summary": {
            "invoice_count": result.get("dataset_summary", {}).get("invoice_count", 0),
            "transaction_count": result.get("dataset_summary", {}).get("transaction_count", 0),
        },
        "key_metrics": {},
        "recommendations_count": len(result.get("actions", [])),
        "insights_count": len(result.get("smart_insights", [])),
        "data_quality": result.get("findings", {}).get("data_quality", {}),
    }

    # Add key metrics
    np = result.get("findings", {}).get("net_profit", {})
    if np:
        summary["key_metrics"] = {
            "total_revenue": np.get("total_revenue", 0),
            "total_expenses": np.get("total_expenses", 0),
            "net_profit": np.get("net_profit", 0),
            "profit_margin_pct": np.get("profit_margin_pct", 0),
        }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)


# ==========================================================================
# Findings CSV writer
# ==========================================================================
def _write_findings_csv(findings: dict[str, Any], filepath: str) -> None:
    """Write business_findings.csv with category-level breakdown."""
    rows: list[dict[str, Any]] = []

    # Use profit_by_category if available (most detailed)
    pbc = findings.get("profit_by_category", {})
    if pbc and pbc.get("categories"):
        for c in pbc["categories"]:
            rows.append({
                "category": c.get("category", ""),
                "revenue_rm": c.get("revenue", 0),
                "allocated_expense_rm": c.get("total_cost", c.get("direct_cost", 0)),
                "profit_rm": c.get("profit", 0),
                "profit_margin_pct": c.get("profit_margin_pct", 0),
                "is_loss_making": c.get("is_loss_making", False),
            })
    else:
        # Fall back to category_summary
        cat_sum = findings.get("category_summary", [])
        for c in cat_sum:
            rows.append({
                "category": c.get("category", ""),
                "revenue_rm": c.get("income_rm", 0),
                "allocated_expense_rm": c.get("expense_rm", 0),
                "profit_rm": c.get("net_rm", 0),
                "profit_margin_pct": "",
                "is_loss_making": c.get("net_rm", 0) < 0,
            })

    if not rows:
        rows = [{"note": "No category-level findings available"}]

    fieldnames = list(rows[0].keys())
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ==========================================================================
# Validation helpers
# ==========================================================================
def _validate_text_file(filepath: str) -> bool:
    """Reopen a text/markdown file and verify it's non-empty."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return len(content) > 50  # At least a minimal report
    except Exception:
        return False


def _validate_csv_file(filepath: str) -> bool:
    """Reopen a CSV file and verify it can be parsed."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        return len(rows) >= 1  # At least a header
    except Exception:
        return False


def _validate_json_file(filepath: str) -> bool:
    """Reopen a JSON file and verify it can be parsed."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except Exception:
        return False


def _effort_label(priority: int) -> str:
    """Map priority to implementation effort label."""
    if priority == 1:
        return "Low effort, high impact (do this week)"
    elif priority == 2:
        return "Medium effort, moderate impact (do this month)"
    else:
        return "Strategic, ongoing consideration"
