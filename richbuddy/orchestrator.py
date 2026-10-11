"""
orchestrator.py - Coordinate analysis modules and drive the RichBuddy pipeline.

The orchestrator is the central conductor that:
    1. Receives a user instruction and the loaded dataset.
    2. Routes the instruction to the correct analysis via intent_router.
    3. Calls the appropriate data_analysis and financial_analysis functions.
    4. Validates that each module produced expected output.
    5. Passes validated findings to business_strategy for prioritised actions.
    6. Calls file_generator to persist results as report and CSV files.
    7. Returns a structured result dict to the caller.

The orchestrator enforces the separation between data analysis, financial
analysis, business strategy, and file generation -- each concern has its own
module and the orchestrator merely sequences them.
"""

import os
from typing import Any

from intent_router import recognize_intent, INTENT_UNKNOWN, ALL_INTENTS
from data_loader import describe_dataset
from data_analysis import (
    analyze_revenue_by_category,
    analyze_expense_by_category,
    analyze_monthly_trends,
    analyze_invoice_status,
    analyze_customer_breakdown,
    analyze_category_summary,
)
from financial_analysis import (
    calculate_net_profit,
    calculate_profit_by_category,
    identify_loss_making_categories,
    identify_profitable_categories,
    calculate_outstanding_balance,
    calculate_revenue_concentration,
    calculate_expense_ratio,
)
from business_strategy import prioritize_actions
from file_generator import generate_text_report, generate_analysis_csvs


def run_analysis(
    instruction: str,
    dataset: dict[str, Any],
    output_dir: str,
) -> dict[str, Any]:
    """Run the full RichBuddy analysis pipeline for a single instruction.

    Args:
        instruction: Natural-language user instruction.
        dataset: Loaded dataset dict (from data_loader.load_dataset() or
                 adaptive_loader.load_user_dataset()).
        output_dir: Directory where output files will be written.

    Returns:
        A result dict containing:
            - intent, instruction, confidence, method
            - findings (dict of analysis outputs)
            - actions (list of prioritised recommendations)
            - dataset_summary
            - data_notes (list of transparency / limitation notes)
            - report_path (path to generated text report)
            - csv_paths (list of generated CSV file paths)
    """
    invoices = dataset.get("invoices", [])
    transactions = dataset.get("transactions", [])

    # Step 1 -- Intent recognition
    intent_result = recognize_intent(instruction)

    # Step 2 -- Dataset summary (always computed, for transparency)
    dataset_summary = describe_dataset(dataset)

    # Step 2b -- Pull adaptation notes from Phase 2 adaptive loader
    data_notes: list[str] = []
    adaptation_report = dataset.get("adaptation_report")
    if adaptation_report:
        data_notes.extend(adaptation_report.get("all_notes", []))
        data_notes.append(
            "Data was loaded from user-provided files using adaptive "
            "column mapping (Phase 2)."
        )

    # Step 3 -- Route to appropriate analysis based on intent
    findings: dict[str, Any] = {}

    intent = intent_result["intent"]

    if intent == INTENT_UNKNOWN:
        # Unknown intent -- still provide a dataset overview
        data_notes.append(
            f"Could not match instruction to a known analysis intent. "
            f"Supported intents: {', '.join(ALL_INTENTS)}. "
            f"Try rephrasing your question."
        )
        findings["dataset_summary"] = dataset_summary

    else:
        # Compute the analyses relevant to the matched intent
        _compute_findings(
            intent, invoices, transactions, findings, data_notes, dataset_summary
        )

    # Step 4 -- Always generate priority actions from whatever findings we have
    # (for the priority_actions intent, this is the primary output; for others,
    # it's a bonus that adds value)
    actions = prioritize_actions(findings) if findings else []

    # For the priority_actions intent, ensure we computed all findings
    if intent == "priority_actions" and not actions:
        # Compute all analyses to have enough data for recommendations
        _compute_findings(
            "overall_performance", invoices, transactions,
            findings, data_notes, dataset_summary
        )
        actions = prioritize_actions(findings)

    # Step 5 -- Build result structure
    result: dict[str, Any] = {
        "intent": intent,
        "instruction": instruction,
        "confidence": intent_result["confidence"],
        "method": intent_result["method"],
        "findings": findings,
        "actions": actions,
        "dataset_summary": dataset_summary,
        "data_notes": data_notes,
    }

    # Step 6 -- Generate output files
    os.makedirs(output_dir, exist_ok=True)
    report_path = generate_text_report(result, output_dir)
    csv_paths = generate_analysis_csvs(result, output_dir)

    result["report_path"] = report_path
    result["csv_paths"] = csv_paths

    return result


def _compute_findings(
    intent: str,
    invoices: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    findings: dict[str, Any],
    data_notes: list[str],
    dataset_summary: dict[str, Any],
) -> None:
    """Compute and populate the findings dict based on the matched intent.

    Mutates *findings* and *data_notes* in place.
    """
    # ---- Overall business performance ----
    if intent == "overall_performance":
        if transactions:
            findings["net_profit"] = calculate_net_profit(transactions)
            findings["revenue_by_category"] = analyze_revenue_by_category(transactions)
            findings["expense_by_category"] = analyze_expense_by_category(transactions)
            findings["monthly_trends"] = analyze_monthly_trends(transactions)
            findings["category_summary"] = analyze_category_summary(transactions)
            findings["expense_ratio"] = calculate_expense_ratio(transactions)
        else:
            data_notes.append(
                "No transaction data available -- revenue, expense, and "
                "profit calculations are skipped."
            )
        if invoices:
            findings["invoice_status"] = analyze_invoice_status(invoices)
            findings["outstanding"] = calculate_outstanding_balance(invoices)
        else:
            data_notes.append(
                "No invoice data available -- invoice status and outstanding "
                "balance analysis are skipped."
            )

    # ---- Profitable / loss-making products ----
    elif intent == "profit_loss_products":
        if transactions:
            findings["profit_by_category"] = calculate_profit_by_category(transactions)
            findings["revenue_by_category"] = analyze_revenue_by_category(transactions)
            findings["expense_by_category"] = analyze_expense_by_category(transactions)
            findings["category_summary"] = analyze_category_summary(transactions)
            findings["loss_making"] = identify_loss_making_categories(
                findings["profit_by_category"]
            )
            findings["profitable"] = identify_profitable_categories(
                findings["profit_by_category"]
            )
            findings["net_profit"] = calculate_net_profit(transactions)

            # Transparency note about allocation
            data_notes.append(findings["profit_by_category"]["allocation_method"])

            # Transparency about "products" vs "categories"
            if not dataset_summary.get("has_product_data"):
                data_notes.append(
                    "The dataset does not contain a 'product' column. Income "
                    "categories (e.g., Design, Printing) are used as the closest "
                    "proxy for 'products' or 'services'."
                )
        else:
            data_notes.append(
                "No transaction data available -- profitability analysis "
                "is not possible without income and expense records."
            )

    # ---- Regional comparison ----
    elif intent == "regional_comparison":
        if dataset_summary.get("has_region_data"):
            # Phase 2: compute actual regional analysis when region column exists
            regional = _analyze_regional(invoices, transactions)
            findings["regional_analysis"] = regional
        else:
            data_notes.append(
                "The dataset does not contain a 'region' or 'location' column, "
                "so regional sales comparison is not possible with this data."
            )
            data_notes.append(
                "Available breakdown dimensions: customer name, transaction "
                "category, date, and invoice status."
            )
            # Provide what IS available as a useful alternative
            if invoices:
                findings["customer_breakdown"] = analyze_customer_breakdown(invoices)
            if transactions:
                findings["revenue_by_category"] = analyze_revenue_by_category(transactions)
                findings["expense_by_category"] = analyze_expense_by_category(transactions)
                findings["category_summary"] = analyze_category_summary(transactions)

    # ---- Returns analysis ----
    elif intent == "returns_analysis":
        if dataset_summary.get("has_returns_data"):
            findings["returns_note"] = (
                "Returns analysis would be computed here if the dataset "
                "contained return/refund records."
            )
        else:
            data_notes.append(
                "The dataset does not contain product return or refund data, "
                "so a direct returns analysis is not possible."
            )
            data_notes.append(
                "As a related financial-risk indicator, overdue and unpaid "
                "invoices are analysed instead -- they represent revenue "
                "that has been invoiced but not yet collected."
            )
            # Provide outstanding/unpaid analysis as the closest available proxy
            if invoices:
                findings["outstanding"] = calculate_outstanding_balance(invoices)
                findings["invoice_status"] = analyze_invoice_status(invoices)
            if transactions:
                findings["net_profit"] = calculate_net_profit(transactions)
                findings["revenue_by_category"] = analyze_revenue_by_category(transactions)

    # ---- Priority actions ----
    elif intent == "priority_actions":
        # Gather all findings needed for comprehensive recommendations
        if transactions:
            findings["net_profit"] = calculate_net_profit(transactions)
            findings["profit_by_category"] = calculate_profit_by_category(transactions)
            findings["expense_ratio"] = calculate_expense_ratio(transactions)
            findings["revenue_concentration"] = calculate_revenue_concentration(transactions)
            findings["category_summary"] = analyze_category_summary(transactions)
            data_notes.append(findings["profit_by_category"]["allocation_method"])
        else:
            data_notes.append(
                "No transaction data available -- profit and expense "
                "analysis is skipped."
            )
        if invoices:
            findings["outstanding"] = calculate_outstanding_balance(invoices)
            findings["invoice_status"] = analyze_invoice_status(invoices)
        else:
            data_notes.append(
                "No invoice data available -- outstanding balance "
                "analysis is skipped."
            )


def _analyze_regional(
    invoices: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyse sales and profitability by region.

    Called when the dataset contains a 'region' column (Phase 2 feature).
    Uses transaction data for revenue/expense where available, and falls
    back to invoice amounts when only invoice data has region info.
    """
    from collections import defaultdict

    # Check which data source has region info
    inv_regions = {inv.get("region") for inv in invoices if inv.get("region")}
    tx_regions = {tx.get("region") for tx in transactions if tx.get("region")}
    all_regions = sorted(inv_regions | tx_regions - {""})

    revenue_by_region: dict[str, float] = defaultdict(float)
    expense_by_region: dict[str, float] = defaultdict(float)
    invoice_count_by_region: dict[str, int] = defaultdict(int)

    # Use transactions for revenue/expense if they have region data
    for tx in transactions:
        region = tx.get("region", "")
        if not region:
            continue
        if tx["type"] == "income":
            revenue_by_region[region] += tx["amount_rm"]
        else:
            expense_by_region[region] += tx["amount_rm"]

    # Fall back to invoice amounts for revenue when transactions lack region data
    tx_has_regions = bool(tx_regions - {""})
    if not tx_has_regions:
        for inv in invoices:
            region = inv.get("region", "")
            if not region:
                continue
            revenue_by_region[region] += inv["invoice_amount_rm"]
            if inv.get("status") != "paid":
                expense_by_region[region] += 0  # no cost data, just track
            invoice_count_by_region[region] += 1
    else:
        for inv in invoices:
            region = inv.get("region", "")
            if region:
                invoice_count_by_region[region] += 1

    regions_result = []
    for region in all_regions:
        rev = revenue_by_region.get(region, 0)
        exp = expense_by_region.get(region, 0)
        profit = rev - exp
        margin = (profit / rev * 100) if rev > 0 else 0.0
        regions_result.append({
            "region": region,
            "revenue": round(rev, 2),
            "expense": round(exp, 2),
            "profit": round(profit, 2),
            "profit_margin_pct": round(margin, 1),
            "invoice_count": invoice_count_by_region.get(region, 0),
        })

    # Sort by revenue descending
    regions_result.sort(key=lambda r: r["revenue"], reverse=True)

    return {
        "regions": regions_result,
        "total_regions": len(all_regions),
        "best_region": regions_result[0]["region"] if regions_result else "N/A",
        "worst_region": regions_result[-1]["region"] if regions_result else "N/A",
    }
