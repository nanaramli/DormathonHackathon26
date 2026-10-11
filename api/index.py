"""
Vercel serverless entry point.

Vercel looks for a WSGI/ASGI app object named `app` in this file.
We import the Flask app from the parent directory (project root).
"""

import sys
import os

# Add the project root to sys.path so we can import all RichBuddy modules
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Tell web_app.py that we are running on Vercel (use /tmp for writable dirs)
os.environ["VERCEL"] = "1"

from web_app import app  # noqa: E402
