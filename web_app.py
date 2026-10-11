"""
web_app.py - Flask web application for RichBuddy.

Wraps the existing Phase 1 + Phase 2 analysis modules into an interactive
web dashboard.  Users can:
  - Upload CSV/Excel business data files
  - Run any of the 5 analysis types via buttons or free-text instruction
  - View results with charts and tables
  - Download generated reports and CSV files
"""

import os
import tempfile
import shutil
from datetime import datetime
import typing

from flask import Flask, request, jsonify, render_template, send_file, send_from_directory

# Import existing RichBuddy modules (they live in the same directory)
from data_loader import load_dataset, DataLoadError, describe_dataset
from adaptive_loader import load_user_dataset, AdaptiveLoadError
from orchestrator import run_analysis
from intent_router import get_supported_intents

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")

for d in (OUTPUT_DIR, UPLOAD_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/intents")
def api_intents():
    """Return the list of supported analysis intents."""
    return jsonify({"intents": get_supported_intents()})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Accept uploaded CSV/Excel files and load them via the adaptive loader."""
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files provided"}), 400

    saved_paths: list[str] = []
    session_dir = tempfile.mkdtemp(dir=UPLOAD_DIR)

    for f in files:
        filename = f.filename
        if not filename:
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".csv", ".xlsx", ".xls"):
            return jsonify({
                "error": f"Unsupported file type '{ext}' for '{filename}'. Supported: .csv, .xlsx, .xls"
            }), 400
        save_path = os.path.join(session_dir, filename)
        f.save(save_path)
        saved_paths.append(save_path)

    if not saved_paths:
        return jsonify({"error": "No valid files were uploaded"}), 400

    try:
        dataset = load_user_dataset(saved_paths)
    except (AdaptiveLoadError, Exception) as e:
        shutil.rmtree(session_dir, ignore_errors=True)
        return jsonify({"error": str(e)}), 400

    summary = describe_dataset(dataset)
    adaptation = dataset.get("adaptation_report", {})
    notes = adaptation.get("all_notes", [])

    # Build a concise file-mapping summary
    file_summaries = []
    for fr in adaptation.get("files", []):
        insp = fr["inspection"]
        file_summaries.append({
            "filename": insp["filename"],
            "format": insp["format"],
            "row_count": insp["row_count"],
            "detected_as": fr["best_match"],
            "columns": [c["name"] for c in insp["columns"]],
        })

    # Clean up uploaded temp files after loading (data is in memory)
    shutil.rmtree(session_dir, ignore_errors=True)

    return jsonify({
        "success": True,
        "summary": _json_safe(summary),
        "invoice_count": len(dataset["invoices"]),
        "transaction_count": len(dataset["transactions"]),
        "file_summaries": file_summaries,
        "adaptation_notes": notes,
    })


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Run an analysis instruction on uploaded or sample data.

    Expected JSON body:
        {
            "instruction": "...",
            "files": [<base64 or multipart already uploaded>],
            "use_sample": true|false
        }

    The frontend sends files first via /api/upload, gets back a session token,
    then calls /api/analyze with the instruction.  To keep things simple,
    the frontend re-uploads files alongside the analyze request OR
    uses sample data.
    """
    # ------------------------------------------------------------------
    # Determine data source: uploaded files only (sample data removed)
    # ------------------------------------------------------------------
    instruction = request.form.get("instruction", "").strip()
    files = request.files.getlist("files")

    # Validate instruction
    if not instruction:
        return jsonify({"error": "No instruction provided"}), 400

    # Load dataset from uploaded files
    dataset = None
    adaptation_notes: list[str] = []

    if files and any(f.filename for f in files):
        saved_paths: list[str] = []
        session_dir = tempfile.mkdtemp(dir=UPLOAD_DIR)
        for f in files:
            if not f.filename:
                continue
            save_path = os.path.join(session_dir, f.filename)
            f.save(save_path)
            saved_paths.append(save_path)
        try:
            dataset = load_user_dataset(saved_paths)
            adaptation_notes = dataset.get("adaptation_report", {}).get("all_notes", [])
        except (AdaptiveLoadError, Exception) as e:
            shutil.rmtree(session_dir, ignore_errors=True)
            return jsonify({"error": str(e)}), 400
        shutil.rmtree(session_dir, ignore_errors=True)
    else:
        return jsonify({"error": "No data source. Please upload files."}), 400

    # ------------------------------------------------------------------
    # Run the analysis pipeline
    # ------------------------------------------------------------------
    try:
        result = run_analysis(instruction, dataset, OUTPUT_DIR)
    except (DataLoadError, AdaptiveLoadError) as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {e}"}), 500

    # Serialize the result for JSON
    response = _serialize_result(result)
    response["adaptation_notes"] = adaptation_notes

    return jsonify(response)


@app.route("/api/download/<path:filename>")
def api_download(filename):
    """Download a generated report or CSV file from the output directory."""
    safe_name = os.path.basename(filename)
    full_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.isfile(full_path):
        return jsonify({"error": f"File not found: {safe_name}"}), 404
    return send_from_directory(OUTPUT_DIR, safe_name, as_attachment=True)


@app.route("/api/output-files")
def api_output_files():
    """List all files in the output directory, newest first."""
    if not os.path.isdir(OUTPUT_DIR):
        return jsonify({"files": []})
    files = []
    for name in os.listdir(OUTPUT_DIR):
        path = os.path.join(OUTPUT_DIR, name)
        if os.path.isfile(path):
            stat = os.stat(path)
            files.append({
                "name": name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    files.sort(key=lambda f: f["modified"], reverse=True)
    return jsonify({"files": files})


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def _json_safe(obj: typing.Any) -> typing.Any:
    """Recursively convert an object so it is JSON-serializable."""
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    else:
        return str(obj)


def _serialize_result(result: dict) -> dict:
    """Convert the orchestrator result dict into a JSON-friendly structure."""
    safe = _json_safe(result)
    # Separate file paths for download links
    safe["report_download"] = os.path.basename(result.get("report_path", "")) if result.get("report_path") else None
    safe["csv_downloads"] = [os.path.basename(p) for p in result.get("csv_paths", [])]
    return safe


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  RichBuddy Web Application")
    print("  Starting server on http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
