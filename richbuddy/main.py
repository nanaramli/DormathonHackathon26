"""
main.py - Command-line entry point for RichBuddy (Phase 1 + Phase 2).

Usage:
    # Phase 1: Use sample dataset
    python main.py --data /path/to/csv/files "Analyse my overall business performance"
    python main.py --interactive

    # Phase 2: Use user-provided files
    python main.py --file /path/to/your_data.csv "Analyse my overall business performance"
    python main.py --file invoices.xlsx --file transactions.csv "Which products are profitable?"

If no --data or --file flag is given, RichBuddy looks for invoices.csv and
transactions.csv in the default sample-data directory.

Intent recognition is rule-based (no LLM required).
"""

import os
import sys
from typing import Optional

from data_loader import load_dataset, DataLoadError, describe_dataset
from adaptive_loader import load_user_dataset, AdaptiveLoadError, format_adaptation_report
from orchestrator import run_analysis
from intent_router import get_supported_intents


# Default location of the sample dataset
DEFAULT_DATA_DIR = os.path.join(
    os.path.expanduser("~"), "Downloads", "bizpilot_sample_csv_files"
)

# Output directory (relative to this file's location)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def print_header():
    print()
    print("=" * 60)
    print("  RichBuddy - Autonomous Business Co-Pilot")
    print("  Phase 1 + Phase 2: Prompt-Based + User-Provided Files")
    print("=" * 60)
    print()
    print("  Intent recognition: Rule-based (no LLM)")
    print("  Supported formats:  CSV, Excel (.xlsx)")
    print()


def print_help():
    print("Supported analysis tasks:")
    print()
    for item in get_supported_intents():
        print(f"  - {item['intent']}")
        print(f"      {item['description']}")
    print()
    print("Example instructions:")
    print('  "Analyse my overall business performance."')
    print('  "Which products are making the most profit, and which are losing money?"')
    print('  "Compare my sales and profitability across regions."')
    print('  "Analyse product returns and explain how they relate to sales."')
    print('  "What are the three most important actions I should take to improve my business?"')
    print()
    print("Data sources:")
    print("  --data <dir>         Use sample CSV files in a directory (Phase 1)")
    print("  --file <path>        Use a user-provided CSV or Excel file (Phase 2)")
    print("                       (can be repeated for multiple files)")
    print()


def print_result_summary(result: dict):
    """Print a concise console summary of the analysis result."""
    print()
    print("-" * 60)
    print("  ANALYSIS COMPLETE")
    print("-" * 60)
    print(f"  Intent:     {result['intent']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Method:     {result['method']}")

    findings = result.get("findings", {})

    # Print key numbers if available
    if "net_profit" in findings:
        np = findings["net_profit"]
        print()
        print(f"  Total Revenue:    RM {np['total_revenue']:,.2f}")
        print(f"  Total Expenses:   RM {np['total_expenses']:,.2f}")
        print(f"  Net Profit:       RM {np['net_profit']:,.2f}")
        print(f"  Profit Margin:    {np['profit_margin_pct']:.1f}%")

    if "outstanding" in findings:
        out = findings["outstanding"]
        print()
        print(f"  Outstanding Balance:   RM {out['total_outstanding']:,.2f}")
        print(f"  Overdue Amount:        RM {out['overdue_amount']:,.2f}")
        print(f"  Collection Rate:       {out['collection_rate_pct']:.1f}%")

    if "profit_by_category" in findings:
        pbc = findings["profit_by_category"]
        print()
        print("  Profitability by Category:")
        for cat in pbc["categories"]:
            status = "LOSS" if cat["is_loss_making"] else "PROFIT"
            print(
                f"    {cat['category']:15s}  Revenue: RM{cat['revenue']:>8,.2f}  "
                f"Profit: RM{cat['profit']:>8,.2f}  "
                f"Margin: {cat['profit_margin_pct']:>5.1f}%  [{status}]"
            )

    if "regional_analysis" in findings:
        ra = findings["regional_analysis"]
        print()
        print(f"  Regional Analysis ({ra['total_regions']} regions):")
        for r in ra["regions"]:
            print(
                f"    {r['region']:15s}  Revenue: RM{r['revenue']:>8,.2f}  "
                f"Profit: RM{r['profit']:>8,.2f}  "
                f"Margin: {r['profit_margin_pct']:>5.1f}%"
            )

    # Print data notes
    notes = result.get("data_notes", [])
    if notes:
        print()
        print("  Data Notes:")
        for note in notes:
            print(f"    - {note}")

    # Print recommendations
    actions = result.get("actions", [])
    if actions:
        print()
        print("  Prioritised Recommendations:")
        for a in actions:
            print(f"    [{a['priority']}] {a['title']}")
            print(f"        Finding: {a['finding']}")

    # Print output files
    print()
    print("  Output Files:")
    print(f"    Report: {result.get('report_path', 'N/A')}")
    for csv_path in result.get("csv_paths", []):
        print(f"    CSV:    {csv_path}")

    print()
    print("-" * 60)
    print()


def run_single(instruction: str, dataset: dict) -> dict:
    """Run a single analysis instruction and print results."""
    result = run_analysis(instruction, dataset, OUTPUT_DIR)
    print_result_summary(result)
    return result


def run_interactive(dataset: dict):
    """Run RichBuddy in interactive mode, accepting instructions until 'exit'."""
    print_header()
    ds = describe_dataset(dataset)
    print(f"  Data source:        {ds.get('data_source', 'unknown')}")
    print(f"  Output directory:   {OUTPUT_DIR}")
    print(f"  Dataset loaded:     {ds['invoice_count']} invoices, "
          f"{ds['transaction_count']} transactions.")
    print()
    print("  Type 'help' for supported tasks, 'exit' to quit.")
    print()

    while True:
        try:
            instruction = input("richbuddy> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("  Goodbye!")
            break

        if not instruction:
            continue
        if instruction.lower() in ("exit", "quit", "q"):
            print("  Goodbye!")
            break
        if instruction.lower() in ("help", "?"):
            print_help()
            continue

        result = run_analysis(instruction, dataset, OUTPUT_DIR)
        print_result_summary(result)


def main():
    args = sys.argv[1:]

    # Parse args
    data_dir = DEFAULT_DATA_DIR
    instruction: Optional[str] = None
    interactive = False
    user_files: list[str] = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--interactive" or arg == "-i":
            interactive = True
        elif arg == "--data" or arg == "-d":
            i += 1
            if i < len(args):
                data_dir = args[i]
            else:
                print("ERROR: --data requires a directory path")
                sys.exit(1)
        elif arg == "--file" or arg == "-f":
            i += 1
            if i < len(args):
                user_files.append(args[i])
            else:
                print("ERROR: --file requires a file path")
                sys.exit(1)
        elif arg == "--help" or arg == "-h":
            print_header()
            print_help()
            sys.exit(0)
        elif arg == "--output" or arg == "-o":
            i += 1
            if i < len(args):
                global OUTPUT_DIR
                OUTPUT_DIR = args[i]
        else:
            instruction = arg
        i += 1

    # Load dataset: Phase 2 (user files) takes priority over Phase 1 (sample data)
    dataset = None
    if user_files:
        print_header()
        print("  Loading user-provided files (Phase 2)...")
        print()
        try:
            dataset = load_user_dataset(user_files)
            print(format_adaptation_report(dataset))
            print()
        except AdaptiveLoadError as e:
            print(f"  ERROR: Could not load user-provided files: {e}")
            sys.exit(1)
    else:
        try:
            dataset = load_dataset(data_dir)
        except DataLoadError as e:
            if interactive or instruction:
                print(f"  ERROR: Could not load dataset: {e}")
                print(f"  Data directory: {data_dir}")
                sys.exit(1)
            else:
                print_header()
                print("  No data found. Use --data <dir> or --file <path>.")
                print()
                print_help()
                sys.exit(0)

    if interactive:
        run_interactive(dataset)
    elif instruction:
        if not user_files:
            print_header()
        run_single(instruction, dataset)
    else:
        print_header()
        print("  No instruction provided. Use --interactive or pass an instruction.")
        print()
        print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
