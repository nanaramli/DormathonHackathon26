@echo off
REM ============================================================
REM  RichBuddy Launcher - Phase 1 + Phase 2
REM
REM  Phase 1 (sample data):
REM    run.bat "Analyse my overall business performance."
REM    run.bat --interactive
REM
REM  Phase 2 (user-provided files):
REM    run.bat --file "C:\path\to\your_data.csv" "Analyse my overall business performance"
REM    run.bat --file invoices.xlsx --file transactions.csv "Which products are profitable?"
REM
REM  NOTE: If --file is used, --data is ignored automatically.
REM ============================================================

set PYTHON=C:\Users\HP\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe
set DATA=C:\Users\HP\WorkBuddy AI\2026-10-10-15-52-22\richbuddy\sample_data

cd /d "C:\Users\HP\WorkBuddy AI\2026-10-10-15-52-22\richbuddy"

REM Check if --file is in the arguments; if so, don't pass --data
echo %* | find /i "--file" >nul
if %errorlevel% equ 0 (
    %PYTHON% main.py %*
) else (
    %PYTHON% main.py --data "%DATA%" %*
)
