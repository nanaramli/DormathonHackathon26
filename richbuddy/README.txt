================================================================
  RichBuddy - Autonomous Business Co-Pilot
  Folder Structure Guide
================================================================

This file explains what each folder and file in the richbuddy/
directory is for, so you always know where to find things.


FOLDER STRUCTURE
================

richbuddy/
|
|-- *.py                          Source code modules (see below)
|
|-- run.bat                       Windows launcher script for CLI
|-- README.txt                    This file
|-- __init__.py                   Python package marker (empty)
|
|-- sample_data/                  Built-in sample data (Phase 1)
|   |-- invoices.csv              Sample invoices (ISO date format)
|   |-- transactions.csv          Sample transactions
|
|-- test_data/                    Test data files (Phase 2 testing)
|   |-- test_invoices.csv         Test invoices with different column names
|   |-- test_invoices.xlsx        Excel version of test invoices
|   |-- test_transactions.csv     Test transactions
|   |-- test_transactions.xlsx    Excel version of test transactions
|   |-- test_regional.csv         Regional data with Region column
|   |-- test_regional.xlsx        Excel version of regional data
|   |-- test_regional_invoices.csv  Regional invoices
|   |-- test_combined.csv         Combined file (no type column)
|   |-- test_user_invoices.csv    User-format invoices
|   |-- test_user_transactions.csv  User-format transactions
|   |-- test_excel_transactions.xlsx  Excel transactions
|
|-- tests/                        Automated test suite (157 tests)
|   |-- run_tests.py              Test runner script
|   |-- test_data_loader.py       Phase 1 data loader tests
|   |-- test_intent_router.py     Phase 1 intent router tests
|   |-- test_financial_analysis.py  Phase 1 financial tests
|   |-- test_business_strategy.py   Phase 1 strategy tests
|   |-- test_orchestrator.py      Phase 1 orchestrator tests
|   |-- test_phase2.py            Phase 2 adaptive loader tests
|
|-- templates/                    Web app HTML templates
|   |-- index.html                Main dashboard page
|
|-- static/                       Web app static assets
|   |-- css/style.css             Stylesheet
|   |-- js/app.js                 Frontend JavaScript
|
|-- uploads/                      Temporary uploaded files (web app)
|                                 (auto-created, files are temp)
|
|-- output/                       Generated reports (auto-created)
|                                 (text reports + CSV files)


SOURCE CODE MODULES
===================

Core Analysis (Phase 1):
  data_loader.py        - Loads and validates CSV data files
  intent_router.py      - Matches user instructions to analysis types
  data_analysis.py      - Revenue, expenses, trends, status breakdowns
  financial_analysis.py - Net profit, margins, outstanding balances
  business_strategy.py  - Converts findings into prioritized actions
  orchestrator.py       - Coordinates the full analysis pipeline
  file_generator.py     - Generates text reports and CSV output files
  main.py               - CLI entry point (--data, --file, --interactive)

Phase 2 (Adaptive File Loading):
  file_inspector.py     - Inspects CSV/Excel files, extracts schema
  column_mapper.py      - Maps arbitrary column names to expected fields
  adaptive_loader.py    - Auto-detects file type, infers missing fields

Web Application:
  web_app.py            - Flask server wrapping all analysis modules


HOW TO RUN
==========

1. Web App (recommended):
   python web_app.py
   Then open http://127.0.0.1:5000 in your browser

2. CLI with sample data:
   run.bat "Analyse my overall business performance"
   or: run.bat --interactive

3. CLI with your own file:
   run.bat --file "C:\path\to\your_data.csv" "Analyse my overall business performance"

4. Run tests:
   cd tests
   python run_tests.py
================================================================
