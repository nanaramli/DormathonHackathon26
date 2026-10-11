@echo off
REM ============================================================
REM  RichBuddy Web App Launcher
REM
REM  Starts the Flask web server on http://127.0.0.1:5000
REM  Open your browser to: http://localhost:5000
REM
REM  Press Ctrl+C to stop the server.
REM ============================================================

set PYTHON=C:\Users\HP\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe

cd /d "C:\Users\HP\WorkBuddy AI\2026-10-10-15-52-22\richbuddy"

echo ============================================================
echo   RichBuddy Web Application
echo   Starting server on http://127.0.0.1:5000
echo   Open your browser to: http://localhost:5000
echo   Press Ctrl+C to stop.
echo ============================================================

%PYTHON% web_app.py
pause
