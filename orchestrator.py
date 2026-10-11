"""
orchestrator.py - Coordinate analysis modules and drive the RichBuddy pipeline.

The orchestrator is the central conductor of an autonomous multi-step workflow:
    1. Interpret the student's business goal (intent recognition).
    2. Inspect the available dataset and determine what can be analysed.
    3. Build a task-specific execution plan.
    4. Select the relevant analysis operations.
    5. Execute calculations and analyses.
    6. Evaluate the results against the original request.
    7. Generate evidence-backed recommendations.
    8. Create the required output files.
    9. Independently verify calculations and generated artifacts (self_verifier).
   10. Recover from appropriate errors and report the final status.

Each step is tracked with its status, inputs, outputs, errors, and verification
results in an execution log.
"""

import os
import traceback
from typing import Any

from intent_router import (
    recognize_intent,
    ALL_INTENTS,
    INTENT_FULL_BUSINESS_REVIEW,
    INTENT_SMART_AUTO,
)
from smart_planner import build_plan, format_plan
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
from reconciliation import reconcile_records
from action_pack_generator import (
    generate_customer_messages,
    generate_action_plan,
    generate_action_pack_summary,
)
from insights_generator import generate_insights, generate_data_quality_score
from self_verifier import run_verification
from deliverable_generator import generate_deliverables


def run_analysis(
    instruction: str,
    dataset: dict[str, Any],
    output_dir: str,
) -> dict[str, Any]:
    """Run the full RichBuddy autonomous analysis pipeline.

    Implements a 10-step autonomous workflow with tracking, error recovery,
    and self-verification. Each step is logged with status, inputs, outputs,
    errors, and verification results.

    Args:
        instruction: Natural-language user instruction.
        dataset: Loaded dataset dict (from data_loader or adaptive_loader).
        output_dir: Directory where output files will be written.

    Returns:
        A result dict containing all findings, actions, verification results,
        execution log, and deliverable file paths.
    """
    # Execution log -- tracks every step
    execution_log: list[dict[str, Any]] = []
    errors_encountered: list[str] = []
    retries: list[dict[str, Any]] = []

    def _log_step(step_num, name, status, detail="", inputs=None, outputs=None, error=None):
        entry = {
            "step": step_num,
            "name": name,
            "status": status,
            "detail": detail,
            "inputs": inputs or {},
            "outputs": outputs or {},
        }
        if error:
            entry["error"] = error
            errors_encountered.append(f"Step {step_num} ({name}): {error}")
        execution_log.append(entry)

    invoices = dataset.get("invoices", [])
    transactions = dataset.get("transactions", [])

    # ================================================================
    # STEP 1: Interpret the student's business goal
    # ================================================================
    try:
        intent_result = recognize_intent(instruction)
        intent = intent_result["intent"]
        _log_step(1, "Interpret Goal", "completed",
                  detail=f"Intent: {intent} (confidence: {intent_result.get('confidence', 'N/A')})",
                  inputs={"instruction": instruction},
                  outputs={"intent": intent, "confidence": intent_result.get("confidence")})
    except Exception as e:
        intent_result = {"intent": INTENT_SMART_AUTO, "confidence": "low",
                         "method": "rule_based", "matched_keywords": [],
                         "instruction": instruction}
        intent = INTENT_SMART_AUTO
        _log_step(1, "Interpret Goal", "recovered",
                  detail=f"Intent recognition failed, defaulting to smart_auto: {e}",
                  error=str(e))

    # ================================================================
    # STEP 2: Inspect available dataset
    # ================================================================
    try:
        dataset_summary = describe_dataset(dataset)
        data_notes: list[str] = []
        adaptation_report = dataset.get("adaptation_report")
        if adaptation_report:
            data_notes.extend(adaptation_report.get("all_notes", []))
            data_notes.append("Data was loaded from user-provided files using adaptive column mapping.")
        _log_step(2, "Inspect Dataset", "completed",
                  detail=f"{len(invoices)} invoices, {len(transactions)} transactions, "
                         f"has_product={dataset_summary.get('has_product_data')}, "
                         f"has_region={dataset_summary.get('has_region_data')}",
                  inputs={"invoice_count": len(invoices), "transaction_count": len(transactions)},
                  outputs={"summary_keys": list(dataset_summary.keys())})
    except Exception as e:
        dataset_summary = {"invoice_count": len(invoices), "transaction_count": len(transactions)}
        data_notes = [f"Dataset inspection error: {e}"]
        _log_step(2, "Inspect Dataset", "recovered",
                  detail=f"Dataset summary failed, using minimal info: {e}",
                  error=str(e))

    # ================================================================
    # STEP 3: Build task-specific execution plan
    # ================================================================
    smart_plan: dict[str, Any] | None = None
    try:
        if intent == INTENT_SMART_AUTO:
            smart_plan = build_plan(instruction)
            _log_step(3, "Build Plan", "completed",
                      detail=f"Smart plan: {smart_plan['goal']}",
                      outputs={"capabilities": smart_plan.get("capabilities", []),
                               "goal": smart_plan.get("goal", "")})
        elif intent == INTENT_FULL_BUSINESS_REVIEW:
            _log_step(3, "Build Plan", "completed",
                      detail="Full business review: all analyses will be executed")
        else:
            _log_step(3, "Build Plan", "completed",
                      detail=f"Specific intent: {intent}")
    except Exception as e:
        _log_step(3, "Build Plan", "recovered",
                  detail=f"Plan building failed, defaulting to overall_performance: {e}",
                  error=str(e))

    # ================================================================
    # STEP 4: Select and execute analysis operations
    # ================================================================
    findings: dict[str, Any] = {}

    def _execute_analysis_with_retry(max_retries=1):
        """Execute analysis with bounded retry on failure."""
        for attempt in range(max_retries + 1):
            try:
                if intent == INTENT_SMART_AUTO and smart_plan:
                    _run_smart_plan(smart_plan, invoices, transactions, findings,
                                    data_notes, dataset_summary)
                    data_notes.append(f"Smart plan goal: {smart_plan['goal']}")
                elif intent == INTENT_FULL_BUSINESS_REVIEW:
                    _run_full_business_review(invoices, transactions, findings,
                                              data_notes, dataset_summary)
                else:
                    _compute_findings(intent, invoices, transactions, findings,
                                      data_notes, dataset_summary)
                return True
            except Exception as e:
                if attempt < max_retries:
                    retries.append({"step": 4, "attempt": attempt + 1, "error": str(e)})
                    # Retry with overall_performance as fallback
                    findings.clear()
                    data_notes.append(f"Analysis error on attempt {attempt + 1}: {e}. Retrying with fallback.")
                    try:
                        _compute_findings("overall_performance", invoices, transactions,
                                          findings, data_notes, dataset_summary)
                        return True
                    except Exception as e2:
                        data_notes.append(f"Fallback also failed: {e2}")
                        return False
                else:
                    raise

    try:
        success = _execute_analysis_with_retry(max_retries=1)
        if success:
            _log_step(4, "Execute Analysis", "completed",
                      detail=f"{len(findings)} analysis modules completed",
                      outputs={"findings_keys": list(findings.keys())})
        else:
            _log_step(4, "Execute Analysis", "partial",
                      detail="Analysis completed with fallback, some modules may be missing",
                      outputs={"findings_keys": list(findings.keys())})
    except Exception as e:
        _log_step(4, "Execute Analysis", "failed",
                  detail=f"Analysis execution failed: {e}",
                  error=str(e))

    # ================================================================
    # STEP 5: Evaluate results and generate recommendations
    # ================================================================
    try:
        actions = prioritize_actions(findings) if findings else []
        if intent == "priority_actions" and not actions:
            _compute_findings("overall_performance", invoices, transactions,
                              findings, data_notes, dataset_summary)
            actions = prioritize_actions(findings)
        _log_step(5, "Generate Recommendations", "completed",
                  detail=f"{len(actions)} recommendation(s) generated",
                  outputs={"action_count": len(actions)})
    except Exception as e:
        actions = []
        _log_step(5, "Generate Recommendations", "failed",
                  detail=f"Recommendation generation failed: {e}",
                  error=str(e))

    # ================================================================
    # STEP 6: Data quality scoring
    # ================================================================
    try:
        findings["data_quality"] = generate_data_quality_score(findings, dataset_summary)
        _log_step(6, "Validate Data Quality", "completed",
                  detail=f"Data quality score: {findings['data_quality']['score']}/100 "
                         f"(Grade {findings['data_quality']['grade']})")
    except Exception as e:
        findings["data_quality"] = {"score": 0, "grade": "D", "issues": [f"Validation error: {e}"]}
        _log_step(6, "Validate Data Quality", "failed",
                  detail=f"Data quality scoring failed: {e}",
                  error=str(e))

    # ================================================================
    # STEP 7: Generate smart insights
    # ================================================================
    try:
        smart_insights = generate_insights(findings, dataset_summary)
        _log_step(7, "Generate Insights", "completed",
                  detail=f"{len(smart_insights)} smart insights generated")
    except Exception as e:
        smart_insights = []
        _log_step(7, "Generate Insights", "failed",
                  detail=f"Insight generation failed: {e}",
                  error=str(e))

    # ================================================================
    # STEP 8: Generate output files
    # ================================================================
    os.makedirs(output_dir, exist_ok=True)
    _cleanup_output_dir(output_dir, keep=5)

    all_output_files: list[str] = []

    try:
        report_path = generate_text_report(
            {"intent": intent, "instruction": instruction,
             "confidence": intent_result["confidence"], "method": intent_result["method"],
             "findings": findings, "actions": actions,
             "dataset_summary": dataset_summary, "data_notes": data_notes},
            output_dir,
        )
        csv_paths = generate_analysis_csvs(
            {"intent": intent, "findings": findings, "actions": actions},
            output_dir,
        )
        all_output_files.append(report_path)
        all_output_files.extend(csv_paths)

        # Action pack files if needed
        include_pack = intent == INTENT_FULL_BUSINESS_REVIEW
        if smart_plan and (smart_plan.get("include_reconciliation") or
                           smart_plan.get("include_customer_messages") or
                           smart_plan.get("include_action_plan")):
            include_pack = True
        if include_pack:
            pack_result = {"findings": findings, "actions": actions, "instruction": instruction}
            pack_paths = _generate_action_pack_files(pack_result, output_dir)
            csv_paths.extend(pack_paths)
            all_output_files.extend(pack_paths)

        _log_step(8, "Generate Output Files", "completed",
                  detail=f"{len(all_output_files)} files generated",
                  outputs={"file_count": len(all_output_files),
                           "files": [os.path.basename(f) for f in all_output_files]})
    except Exception as e:
        report_path = ""
        csv_paths = []
        _log_step(8, "Generate Output Files", "failed",
                  detail=f"File generation failed: {e}",
                  error=str(e))

    # ================================================================
    # STEP 9: Independent self-verification
    # ================================================================
    # Build the full result for verification
    result: dict[str, Any] = {
        "intent": intent,
        "instruction": instruction,
        "confidence": intent_result["confidence"],
        "method": intent_result["method"],
        "findings": findings,
        "actions": actions,
        "dataset_summary": dataset_summary,
        "data_notes": data_notes,
        "smart_insights": smart_insights,
    }
    if smart_plan:
        result["smart_plan"] = smart_plan

    # Pipeline steps for UI
    pipeline_steps = [
        {"step": 1, "name": "Load Data", "status": "done",
         "detail": f"{len(invoices)} invoices, {len(transactions)} transactions loaded"},
        {"step": 2, "name": "Detect Intent", "status": "done",
         "detail": f"Intent: {intent} (confidence: {intent_result.get('confidence', 'N/A')})"},
        {"step": 3, "name": "Run Analysis", "status": "done",
         "detail": f"{len(findings)} analysis modules completed"},
        {"step": 4, "name": "Validate Data", "status": "done",
         "detail": f"Data quality score: {findings.get('data_quality', {}).get('score', 0)}/100 "
                   f"(Grade {findings.get('data_quality', {}).get('grade', 'N/A')})"},
        {"step": 5, "name": "Generate Insights", "status": "done",
         "detail": f"{len(smart_insights)} smart insights generated"},
    ]
    result["pipeline_steps"] = pipeline_steps

    try:
        verification_report = run_verification(result, dataset, all_output_files)
        _log_step(9, "Self-Verification", "completed",
                  detail=f"Verification: {verification_report['overall_status']} "
                         f"({verification_report['summary']['passed']}/{verification_report['summary']['total']} checks passed)",
                  outputs={"overall_status": verification_report["overall_status"],
                           "summary": verification_report["summary"]})
    except Exception as e:
        verification_report = {
            "checks": [], "summary": {"total": 0, "passed": 0, "failed_critical": 0,
                                      "failed_warning": 0, "skipped": 0},
            "overall_status": "FAIL",
            "errors": [f"Verification engine error: {e}"],
            "warnings": [],
        }
        _log_step(9, "Self-Verification", "failed",
                  detail=f"Verification failed: {e}",
                  error=str(e))

    # ================================================================
    # STEP 10: Generate verified business deliverables
    # ================================================================
    try:
        deliverables = generate_deliverables(
            result, verification_report, execution_log, output_dir,
        )
        all_output_files.extend(deliverables["files"])
        _log_step(10, "Generate Deliverables", "completed",
                  detail=f"{len(deliverables['files'])} deliverable files generated, "
                         f"validated: {deliverables['validated']}",
                  outputs={"files": [os.path.basename(f) for f in deliverables["files"]],
                           "validated": deliverables["validated"]})
    except Exception as e:
        deliverables = {"files": [], "report_path": None, "recommendations_path": None,
                        "execution_summary_path": None, "findings_path": None,
                        "validated": False, "validation_errors": [str(e)]}
        _log_step(10, "Generate Deliverables", "failed",
                  detail=f"Deliverable generation failed: {e}",
                  error=str(e))

    # ================================================================
    # Finalize result
    # ================================================================
    result["report_path"] = report_path
    result["csv_paths"] = csv_paths
    result["all_output_files"] = all_output_files
    result["verification"] = verification_report
    result["execution_log"] = execution_log
    result["deliverables"] = deliverables

    # Determine final status
    critical_errors = [e for e in errors_encountered if "failed" in execution_log and
                       execution_log[-1].get("status") == "failed"]
    if verification_report["overall_status"] == "PASS":
        result["final_status"] = "SUCCESS"
    elif verification_report["overall_status"] == "PARTIAL":
        result["final_status"] = "PARTIAL_SUCCESS"
    else:
        result["final_status"] = "FAILED"

    result["retries"] = retries

    return result


def _run_smart_plan(
    plan: dict[str, Any],
    invoices: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    findings: dict[str, Any],
    data_notes: list[str],
    dataset_summary: dict[str, Any],
) -> None:
    """Execute a smart plan dynamically based on detected capabilities.

    Mutates *findings* and *data_notes* in place.
    """
    caps = plan.get("capabilities", [])
    recon_issues = None

    # 1. Reconciliation (if included)
    if plan.get("include_reconciliation") or "reconciliation" in caps:
        reconciliation = reconcile_records(invoices, transactions)
        findings["reconciliation"] = reconciliation
        recon_issues = reconciliation
        recon_summary = reconciliation["summary"]
        data_notes.append(
            f"Data reconciliation: {recon_summary['total_issues']} issue(s) found "
            f"({recon_summary['critical_count']} critical, "
            f"{recon_summary['warning_count']} warnings, "
            f"{recon_summary['info_count']} info). "
            f"Reconciled: {'YES' if recon_summary['is_reconciled'] else 'NO'}."
        )

    # 2. Financial overview
    if "financial_overview" in caps or "profitability" in caps or "cost_optimization" in caps:
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

    # 3. Profitability analysis
    if "profitability" in caps:
        if transactions:
            findings["profit_by_category"] = calculate_profit_by_category(transactions)
            findings["loss_making"] = identify_loss_making_categories(
                findings["profit_by_category"]
            )
            findings["profitable"] = identify_profitable_categories(
                findings["profit_by_category"]
            )
            data_notes.append(findings["profit_by_category"]["allocation_method"])

            if not dataset_summary.get("has_product_data"):
                data_notes.append(
                    "The dataset does not contain a 'product' column. Income "
                    "categories are used as the closest proxy for 'products' or 'services'."
                )

    # 4. Invoice status
    if "invoice_status" in caps or plan.get("include_customer_messages"):
        if invoices:
            findings["invoice_status"] = analyze_invoice_status(invoices)
            findings["outstanding"] = calculate_outstanding_balance(invoices)
        else:
            data_notes.append(
                "No invoice data available -- invoice status and outstanding "
                "balance analysis are skipped."
            )

    # 5. Revenue concentration
    if "financial_overview" in caps or "growth" in caps or "cost_optimization" in caps:
        if transactions:
            findings["revenue_concentration"] = calculate_revenue_concentration(transactions)

    # 6. Regional analysis
    if "regional" in caps:
        if dataset_summary.get("has_region_data"):
            findings["regional_analysis"] = _analyze_regional(invoices, transactions)
        else:
            data_notes.append(
                "The dataset does not contain a 'region' or 'location' column, "
                "so regional sales comparison is not possible with this data."
            )
            if invoices:
                findings["customer_breakdown"] = analyze_customer_breakdown(invoices)

    # 7. Returns analysis
    if "returns" in caps:
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
                "invoices are analysed instead."
            )
            if invoices and "outstanding" not in findings:
                findings["outstanding"] = calculate_outstanding_balance(invoices)
                findings["invoice_status"] = analyze_invoice_status(invoices)

    # 8. Customer breakdown
    if "customer_breakdown" in caps:
        if invoices:
            findings["customer_breakdown"] = analyze_customer_breakdown(invoices)
        if transactions:
            if "revenue_by_category" not in findings:
                findings["revenue_by_category"] = analyze_revenue_by_category(transactions)
                findings["expense_by_category"] = analyze_expense_by_category(transactions)
                findings["category_summary"] = analyze_category_summary(transactions)

    # 9. Customer messages (if included)
    customer_messages = []
    if plan.get("include_customer_messages"):
        customer_messages = generate_customer_messages(invoices, transactions)
        findings["customer_messages"] = customer_messages
        if customer_messages:
            data_notes.append(
                f"{len(customer_messages)} customer follow-up message(s) drafted "
                f"and ready to send."
            )
        else:
            data_notes.append("All invoices are paid -- no follow-up messages needed.")

    # 10. Action plan — DISABLED per user request (PLAN card removed from UI)
    # if plan.get("include_action_plan"):
    #     actions = prioritize_actions(findings)
    #     action_plan = generate_action_plan(
    #         recon_issues or {}, findings, actions, customer_messages
    #     )
    #     findings["action_plan"] = action_plan

    # Transparency notes for missing data
    if not dataset_summary.get("has_returns_data") and "returns" not in caps:
        if plan.get("include_action_plan") or "invoice_status" in caps:
            data_notes.append(
                "No returns data -- overdue invoices analysed as financial-risk indicator."
            )


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
            regional = _analyze_regional(invoices, transactions)
            findings["regional_analysis"] = regional
            # Also compute financial findings so KPIs and insights work
            if transactions:
                findings["net_profit"] = calculate_net_profit(transactions)
                findings["revenue_by_category"] = analyze_revenue_by_category(transactions)
                findings["expense_by_category"] = analyze_expense_by_category(transactions)
                findings["monthly_trends"] = analyze_monthly_trends(transactions)
                findings["category_summary"] = analyze_category_summary(transactions)
                findings["expense_ratio"] = calculate_expense_ratio(transactions)
                findings["revenue_concentration"] = calculate_revenue_concentration(transactions)
            if invoices:
                findings["invoice_status"] = analyze_invoice_status(invoices)
                findings["outstanding"] = calculate_outstanding_balance(invoices)
            data_notes.append(
                "Regional analysis completed with full financial breakdown. "
                "Additional insights generated from available data."
            )
        else:
            data_notes.append(
                "The dataset does not contain a 'region' or 'location' column, "
                "so regional sales comparison is not possible with this data."
            )
            data_notes.append(
                "Available breakdown dimensions: customer name, transaction "
                "category, date, and invoice status."
            )
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
            if invoices:
                findings["outstanding"] = calculate_outstanding_balance(invoices)
                findings["invoice_status"] = analyze_invoice_status(invoices)
            if transactions:
                findings["net_profit"] = calculate_net_profit(transactions)
                findings["revenue_by_category"] = analyze_revenue_by_category(transactions)

    # ---- Priority actions ----
    elif intent == "priority_actions":
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


def _run_full_business_review(
    invoices: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    findings: dict[str, Any],
    data_notes: list[str],
    dataset_summary: dict[str, Any],
) -> None:
    """Run the full autonomous business review.

    Executes ALL analysis steps in sequence:
    1. Reconcile records (invoices vs transactions)
    2. Financial overview (revenue, expenses, profit, margins)
    3. Outstanding invoices & cash flow
    4. Profit by category
    5. Expense ratio & revenue concentration
    6. Regional analysis (if region data available)
    7. Generate customer follow-up messages
    8. Generate 30-minute action plan
    9. Generate action pack summary

    Mutates *findings* and *data_notes* in place.
    """
    # Step 1: Reconciliation
    reconciliation = reconcile_records(invoices, transactions)
    findings["reconciliation"] = reconciliation
    recon_summary = reconciliation["summary"]
    data_notes.append(
        f"Data reconciliation: {recon_summary['total_issues']} issue(s) found "
        f"({recon_summary['critical_count']} critical, "
        f"{recon_summary['warning_count']} warnings, "
        f"{recon_summary['info_count']} info). "
        f"Reconciled: {'YES' if recon_summary['is_reconciled'] else 'NO'}."
    )

    # Step 2: Financial overview
    if transactions:
        findings["net_profit"] = calculate_net_profit(transactions)
        findings["revenue_by_category"] = analyze_revenue_by_category(transactions)
        findings["expense_by_category"] = analyze_expense_by_category(transactions)
        findings["monthly_trends"] = analyze_monthly_trends(transactions)
        findings["category_summary"] = analyze_category_summary(transactions)
        findings["expense_ratio"] = calculate_expense_ratio(transactions)

    # Step 3: Outstanding invoices & cash flow
    if invoices:
        findings["invoice_status"] = analyze_invoice_status(invoices)
        findings["outstanding"] = calculate_outstanding_balance(invoices)

    # Step 4: Profit by category
    if transactions:
        findings["profit_by_category"] = calculate_profit_by_category(transactions)
        findings["loss_making"] = identify_loss_making_categories(
            findings["profit_by_category"]
        )
        findings["profitable"] = identify_profitable_categories(
            findings["profit_by_category"]
        )
        data_notes.append(findings["profit_by_category"]["allocation_method"])

    # Step 5: Revenue concentration
    if transactions:
        findings["revenue_concentration"] = calculate_revenue_concentration(transactions)

    # Step 6: Regional analysis (if region data available)
    if dataset_summary.get("has_region_data"):
        findings["regional_analysis"] = _analyze_regional(invoices, transactions)
    else:
        data_notes.append(
            "No region column detected — regional analysis skipped. "
            "Customer breakdown provided as alternative."
        )
        if invoices:
            findings["customer_breakdown"] = analyze_customer_breakdown(invoices)

    # Step 7: Generate customer follow-up messages
    customer_messages = generate_customer_messages(invoices, transactions)
    findings["customer_messages"] = customer_messages
    if customer_messages:
        data_notes.append(
            f"{len(customer_messages)} customer follow-up message(s) drafted "
            f"and ready to send."
        )
    else:
        data_notes.append("All invoices are paid — no follow-up messages needed.")

    # Step 8: Generate action plan — DISABLED per user request (PLAN card removed from UI)
    # actions = prioritize_actions(findings)
    # action_plan = generate_action_plan(
    #     reconciliation, findings, actions, customer_messages
    # )
    # findings["action_plan"] = action_plan

    # Transparency notes
    if not dataset_summary.get("has_product_data"):
        data_notes.append(
            "No 'product' column — income categories used as proxy for products."
        )
    if not dataset_summary.get("has_returns_data"):
        data_notes.append(
            "No returns data — overdue invoices analysed as financial-risk indicator."
        )


def _generate_action_pack_files(
    result: dict[str, Any],
    output_dir: str,
) -> list[str]:
    """Generate the action pack files: customer messages, action plan, summary."""
    import csv
    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []

    findings = result.get("findings", {})

    # 1. Customer messages text file (copy-paste ready)
    messages = findings.get("customer_messages", [])
    if messages:
        msg_path = os.path.join(output_dir, f"customer_messages_{ts}.txt")
        lines = []
        lines.append("=" * 60)
        lines.append("  Customer Follow-Up Messages (Ready to Send)")
        lines.append("=" * 60)
        lines.append("")
        for m in messages:
            lines.append(f"  [{m['channel']}] {m['subject']}")
            lines.append(f"  Priority: P{m['priority']} | Amount owed: RM{m['amount_owed']:.2f}")
            lines.append("")
            lines.append(m["message"])
            lines.append("")
            lines.append("-" * 60)
            lines.append("")
        with open(msg_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        paths.append(msg_path)

        # Also as CSV for structured use
        csv_path = os.path.join(output_dir, f"customer_messages_{ts}.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "priority", "customer_name", "invoice_id", "amount_owed",
                "invoice_amount", "amount_paid", "issue_date", "due_date",
                "status", "channel", "subject", "message",
            ])
            writer.writeheader()
            for m in messages:
                writer.writerow({k: m.get(k, "") for k in writer.fieldnames})
        paths.append(csv_path)

    # 2. Action plan CSV
    plan = findings.get("action_plan", [])
    if plan:
        plan_path = os.path.join(output_dir, f"action_plan_{ts}.csv")
        with open(plan_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "step", "title", "detail", "estimated_minutes", "category", "priority",
            ])
            writer.writeheader()
            for item in plan:
                writer.writerow({k: item.get(k, "") for k in writer.fieldnames})
        paths.append(plan_path)

    # 3. Action pack summary text file
    summary_text = generate_action_pack_summary(
        findings.get("reconciliation", {}),
        findings,
        result.get("actions", []),
        messages,
        plan,
        result.get("instruction", ""),
    )
    summary_path = os.path.join(output_dir, f"action_pack_summary_{ts}.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    paths.append(summary_path)

    return paths


def _cleanup_output_dir(output_dir: str, keep: int = 5) -> None:
    """Keep only the N most recent files in the output directory."""
    import os
    from datetime import datetime, timedelta

    if not os.path.isdir(output_dir):
        return

    files = []
    for name in os.listdir(output_dir):
        path = os.path.join(output_dir, name)
        if os.path.isfile(path):
            mtime = os.path.getmtime(path)
            files.append((path, mtime))

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)

    # Delete files beyond the keep limit AND older than 24 hours
    cutoff = (datetime.now() - timedelta(hours=24)).timestamp()
    for path, mtime in files[keep:]:
        if mtime < cutoff:
            try:
                os.remove(path)
            except OSError:
                pass

