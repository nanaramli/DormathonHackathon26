<<<<<<< HEAD
# RichBuddy — Autonomous Business Co-Pilot for Student Entrepreneurs

**Dormathon 2026 | Track 2: WorkBuddy (Agentic Solutions)**

RichBuddy is a rule-based business intelligence agent that helps student entrepreneurs understand their business finances, identify profit improvement opportunities, and take affordable action — all without needing an LLM or internet connection.

## Features

- **10-step autonomous workflow** — interprets your goal, inspects data, plans analysis, executes calculations, generates recommendations, validates data quality, produces insights, creates output files, self-verifies, and delivers verified business reports
- **Self-verification engine** — independently recalculates all financial totals from raw data, reopens every output file to validate it, and never reports success if a critical check fails
- **Student-focused recommendations** — practical actions using WhatsApp follow-ups, Instagram promotion, bulk buying from Giant/Tesco, affordable price increases (RM1-2), and exam-season awareness
- **Adaptive column mapping** — automatically detects and maps column names (English + Malay) to the standard schema, handles CSV and Excel files
- **Smart insights** — AI-like insight cards tagged CRITICAL, IMPORTANT, or GOOD, sorted by priority
- **Verified deliverables** — generates business_action_report.md, prioritised_recommendations.csv, execution_summary.json, and business_findings.csv — each reopened and validated after writing
- **Bounded error recovery** — retries failed analysis steps (max 1 retry) with fallback to overall performance analysis
- **Malay language support** — recognises Malay keywords in both intent routing and smart planning
- **Data quality scoring** — scores data completeness 0-100 with letter grades A-D

## Tech Stack

- **Backend:** Python 3.13, Flask
- **Frontend:** HTML, CSS, vanilla JavaScript, Chart.js
- **Data:** openpyxl (Excel), csv module (CSV)
- **Testing:** unittest (172 tests across 7 suites)

## Getting Started

### Prerequisites

- Python 3.11+ 
- Flask, openpyxl (install via pip)

### Installation

```bash
cd richbuddy
pip install flask openpyxl
```

### Run the Web App

```bash
python web_app.py
```

Then open http://localhost:5000 in your browser.

Or use the batch file:

```bat
run_web.bat
```

### Run Tests

```bash
python -m unittest tests.test_richbuddy_upgrade -v       # 39 new tests
python -m unittest discover tests -v                      # all 172 tests
```

## How to Use

1. **Type your question** — e.g., "Analyse my overall business performance" or "Which products are making profit and losing money?"
2. **Upload your data files** — CSV or Excel, invoices and/or transactions (you can upload multiple files one at a time)
3. **Click Analyze** — RichBuddy runs the full 10-step pipeline automatically
4. **Review results** — KPI cards, recommended actions, charts, tables, insights, and downloadable files

## Supported File Formats

### CSV Files
- Invoice files: invoice_id, customer_name, invoice_amount, status, issue_date, due_date
- Transaction files: transaction_id, date, type (income/expense), category, description, amount

### Excel Files
- .xlsx and .xls supported
- Column names auto-detected (case-insensitive, supports aliases)

### Column Aliases
RichBuddy recognises many column name variations:
- Amount: amount, total, sales, jumlah, hasil
- Date: date, tarikh, issued
- Type: type, jenis
- Status: status, berbayar, tertunggak, menunggu

## Project Structure

```
richbuddy/
├── web_app.py                 # Flask web server
├── orchestrator.py            # 10-step autonomous pipeline coordinator
├── self_verifier.py           # Independent verification engine (24+ checks)
├── deliverable_generator.py   # Verified business deliverable generation
├── business_strategy.py       # Student-focused recommendation engine
├── intent_router.py           # Rule-based intent recognition (EN + Malay)
├── smart_planner.py           # Dynamic plan builder (EN + Malay)
├── data_loader.py             # Standard CSV/Excel loader
├── adaptive_loader.py         # Adaptive multi-file loader with column mapping
├── column_mapper.py           # 5-pass column detection system
├── financial_analysis.py      # Net profit, margins, category profitability
├── data_analysis.py           # Revenue, expense, monthly trends, invoices
├── insights_generator.py      # AI-like insight cards and data quality scoring
├── file_generator.py          # Text report and CSV output generation
├── reconciliation.py          # Invoice vs transaction reconciliation
├── action_pack_generator.py   # Customer messages and action plans
├── file_inspector.py          # File format detection
├── main.py                    # CLI entry point
├── run_web.bat                # Batch file to start web server
├── templates/
│   └── index.html             # Web UI
├── static/
│   ├── css/style.css          # Styling
│   └── js/app.js              # Frontend logic
├── sample_data/
│   ├── brownie_invoices.csv   # Student brownie business demo (20 invoices)
│   ├── brownie_transactions.csv  # Demo transactions (40 records)
│   ├── invoices.csv           # Basic sample data
│   └── transactions.csv       # Basic sample data
├── test_data/                 # Additional test datasets
│   ├── invois_melayu.csv      # Malay-language test data
│   └── transaksi_melayu.csv   # Malay transactions
├── tests/                     # 172 automated tests
│   ├── test_richbuddy_upgrade.py    # 39 tests (calculations, verification, demo)
│   ├── test_business_strategy.py    # Recommendation logic tests
│   ├── test_financial_analysis.py   # Financial calculation tests
│   ├── test_data_loader.py          # Data loading tests
│   ├── test_intent_router.py        # Intent recognition tests
│   ├── test_orchestrator.py         # Pipeline integration tests
│   └── test_smart_features.py       # Adaptive mapping tests
├── output/                    # Generated analysis files
└── README.md                  # This file
```

## The 10-Step Autonomous Workflow

```
Step 1:  Interpret Goal        → Recognize intent (rule-based, EN + Malay)
Step 2:  Inspect Dataset       → Detect columns, data quality, adaptation notes
Step 3:  Build Plan            → Smart planner or specific intent routing
Step 4:  Execute Analysis      → Calculate metrics, identify opportunities
         ↳ retry (max 1)       → Fallback to overall_performance on failure
Step 5:  Generate Recommendations → Student-focused, prioritised actions
Step 6:  Validate Data Quality → Score 0-100, grade A-D, flag issues
Step 7:  Generate Insights     → CRITICAL / IMPORTANT / GOOD insight cards
Step 8:  Generate Output Files → Text report, category/profit/invoice CSVs
Step 9:  Self-Verification     → 24+ independent checks (recalculate, validate)
Step 10: Generate Deliverables → Report .md, recommendations .csv, summary .json
         ↓
Final status: SUCCESS / PARTIAL_SUCCESS / FAILED
```

## Verification Checks (24+)

### Input checks
- Data loaded successfully
- Required columns present (invoices + transactions)
- No duplicate invoice IDs
- No negative transaction amounts

### Calculation checks
- Total revenue independently recalculated and matched
- Total expenses independently recalculated and matched
- Net profit = revenue - expenses (verified)
- Profit margin mathematically correct
- Category totals reconcile with overall revenue
- No zero-denominator division errors

### Recommendation checks
- All recommendations have required fields
- All priorities are valid (1, 2, or 3)
- Findings contain supporting figures (RM or %)
- Recommendations traceable to actual analysis findings

### Artifact checks
- All output files exist and are non-empty
- CSV files can be reopened and parsed
- JSON files are valid and parseable
- Report contains required sections

## Limitations

- Rule-based only (no LLM) — works offline, deterministic, no API costs
- Expense allocation is proportional when explicit cost-of-goods-sold is not available
- Malay support is keyword-based (not full NLP)
- No multi-currency support (RM only)
- Old output files auto-cleaned after 24 hours (keeps 5 most recent)

## License

Built for Dormathon 2026 Hackathon.
=======
# DormathonHackathon26
Dormathon Hackathon 10-11 Oct 2026
# RichBuddy 🐱💰
### Autonomous Business Co-Pilot for Student Entrepreneurs

---

## Problem Statement

Student entrepreneurs and small business owners collect sales records every day, but the data is hard to read. Spreadsheets don't show what is working or why, so low-margin products and declining categories go unnoticed until they have already drained profit.

When everything seems important, choosing what to fix first becomes a guessing game instead of a strategy. Doing the calculations by hand also takes hours away from studying, marketing and serving customers, the work that actually grows the business.

## Solution

RichBuddy is an AI co-pilot that does the analysis so the owner doesn't have to.

The user uploads their sales file and describes what they want to know in everyday language. From that single request, the agent works out its own plan, analyses the data, and produces a finished report with charts, a clear written summary and recommended next steps.

The owner stays in charge by approving the plan and reviewing the draft before anything is final.

Built on WorkBuddy, RichBuddy turns scattered sales records into straightforward guidance on what is selling, what is profitable and what to do next, saving hours of manual work and making business decisions easier for people without an analytics background.

>>>>>>> 9c3244f6deda47eb808a93ce4b508491868dfaac
