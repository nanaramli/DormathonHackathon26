# RichBuddy - Autonomous Business Co-Pilot for Student Entrepreneurs

Dormathon Hackathon, 10-11 Oct 2026

RichBuddy analyses business data (invoices + transactions) and produces
prioritised recommendations for student entrepreneurs. No LLM required --
intent recognition is rule-based.

## Quick Start

```bash
# Web app (recommended)
python web_app.py          # opens at http://127.0.0.1:5000

# CLI with sample data
python main.py --interactive

# CLI with your own file
python main.py --file your_data.xlsx "Analyse my overall business performance"

# Run tests
cd tests && python run_tests.py
```

## Folder Structure

```
richbuddy/
|-- *.py                     Source code (14 modules, see below)
|-- run.bat                  Windows CLI launcher
|-- .gitignore
|
|-- sample_data/             Built-in sample data
|   |-- invoices.csv, transactions.csv          Phase 1 defaults
|   |-- student_invoices.xlsx, student_transactions.xlsx, student_combined.xlsx
|   |-- malay_invoices.xlsx, malay_transactions.xlsx
|
|-- test_data/               Phase 2 test files (various column name formats)
|-- tests/                   157 automated tests
|-- templates/index.html     Web dashboard
|-- static/css/style.css, static/js/app.js
|-- uploads/                 Temp uploaded files (auto-cleaned)
|-- output/                  Generated reports (auto-created)
```

## Source Modules

**Phase 1 (core analysis):**
- `data_loader.py` — CSV loading, column validation, cross-reference checks
- `intent_router.py` — Rule-based keyword matching for 5 analysis intents
- `data_analysis.py` — Revenue/expense by category, monthly trends, invoice status
- `financial_analysis.py` — Net profit, profit by category, outstanding balances
- `business_strategy.py` — Converts findings into P1/P2/P3 recommendations
- `orchestrator.py` — Coordinates intent -> analysis -> strategy -> file generation
- `file_generator.py` — Text reports + CSV output
- `main.py` — CLI entry point

**Phase 2 (adaptive file loading):**
- `file_inspector.py` — Inspects CSV/Excel, extracts columns, infers types
- `column_mapper.py` — 3-pass alias matching (English + Malay column names)
- `adaptive_loader.py` — Auto-detects file type, infers missing fields

**Web app:**
- `web_app.py` — Flask server wrapping all modules

## Supported Analysis Types

1. Overall business performance
2. Profit/loss by product (category)
3. Regional comparison
4. Returns analysis
5. Priority actions / recommendations
