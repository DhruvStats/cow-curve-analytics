"""
app.py — Flask backend for the Chart Digitizer web app.

Endpoints:
  POST /upload        — accept PDF, run pipeline, return job ID
  GET  /status/<id>   — poll job progress
  GET  /download/<id>/<filename> — download a CSV
  GET  /files/<id>    — list output files for a job
  GET  /              — serve the frontend
"""

import json
import os
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file

# Make sure pipeline module is importable
sys.path.insert(0, str(Path(__file__).parent / "pipeline"))
from pipeline import (run_pipeline, CHART_IMAGE_SUBDIR,
                      accuracy_pct, ACCURACY_THRESHOLD_PCT)
import settings

app = Flask(__name__, static_folder="frontend", static_url_path="")

UPLOAD_DIR = Path(__file__).parent / "uploads"
OUTPUT_DIR = Path(__file__).parent / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

# Cap uploads. A runaway PDF would otherwise spawn a worker thread that runs
# for a very long time with no way to cancel it. Flask returns 413 above this.
MAX_UPLOAD_MB = 64
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# In-memory job store  {job_id: {status, progress, total, results, error}}
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def count_expected_charts(input_path: str) -> int:
    """Expected chart count (pages × 8 for PDFs, 8 for single images)."""
    try:
        if Path(input_path).suffix.lower() == ".pdf":
            import fitz
            with fitz.open(input_path) as doc:
                return doc.page_count * 8
    except Exception:
        pass
    return 8


def run_job(job_id: str, input_path: str, out_dir: str):
    """Run pipeline in a background thread and update job state."""
    try:
        expected = count_expected_charts(input_path)
        with jobs_lock:
            jobs[job_id]["status"] = "running"
            jobs[job_id]["total"]  = expected

        results = run_pipeline(input_path, out_dir)

        with jobs_lock:
            jobs[job_id]["status"]  = "done"
            jobs[job_id]["results"] = results
            jobs[job_id]["total"]   = len(results)

    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"]  = str(e)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# Bumped whenever the CSV format or the API shape changes. The page checks it
# and tells the user to restart if the running process is older than the files
# on disk: Python loads app.py and pipeline.py once at startup, so editing them
# while a server is running leaves the new HTML talking to old code.
BUILD_ID = "2026-10-06-bounded-calibration"


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/build")
def build():
    """Identify the code this process is actually running."""
    return jsonify({
        "build": BUILD_ID,
        "csv_columns": ["curve", "time_min", "value"],
        "accuracy_threshold": ACCURACY_THRESHOLD_PCT,
        # The page reads its measurement rules from here rather than keeping
        # its own copies, so settings.py stays the single source of truth.
        "flow_threshold": settings.FLOW_THRESHOLD_KG_MIN,
        "attached_pressure": settings.ATTACHED_PRESSURE,
        "curve_flow": settings.CURVE_FLOW,
        "curve_pressure": settings.CURVE_PRESSURE,
        # Present only on builds that bound the printed-weight calibration, so
        # a stale deploy is obvious from this endpoint alone.
        "calibration_bounded": True,
        "pen_half_width_kg_min": settings.PEN_HALF_WIDTH_KG_MIN,
    })


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    job_id   = str(uuid.uuid4())
    ext      = Path(f.filename).suffix.lower()
    filename = f"input_{job_id}{ext}"
    input_path = str(UPLOAD_DIR / filename)
    out_dir    = str(OUTPUT_DIR / job_id)
    os.makedirs(out_dir, exist_ok=True)

    f.save(input_path)

    with jobs_lock:
        jobs[job_id] = {
            "status":   "queued",
            "progress": 0,
            "total":    0,
            "results":  [],
            "error":    None,
            "input":    f.filename,
        }

    thread = threading.Thread(target=run_job, args=(job_id, input_path, out_dir), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/status/<job_id>")
def status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)

    if job is None:
        return jsonify({"error": "Job not found"}), 404

    # Build file list if done; while running, report charts written so far.
    # The listing is taken from the job's own results first and only falls back
    # to scanning the directory: a stale or half-written output folder from an
    # earlier run would otherwise make a finished job look empty.
    files = []
    progress = 0
    out_dir = OUTPUT_DIR / job_id
    results = job.get("results", [])

    if job["status"] == "done":
        named = [r["csv_file"] for r in results if r.get("csv_file")]
        on_disk = set()
        try:
            on_disk = {f.name for f in out_dir.iterdir() if f.suffix == ".csv"}
        except OSError:
            pass
        # Keep only files that really exist, then add anything on disk the
        # results did not mention, so nothing is hidden either way.
        files = sorted(set(named) & on_disk) if named else sorted(on_disk)
        if not files:
            files = sorted(on_disk)
    elif job["status"] == "running" and out_dir.exists():
        try:
            progress = sum(1 for f in out_dir.iterdir() if f.suffix == ".csv")
        except OSError:
            progress = 0

    return jsonify({
        "status":   job["status"],
        "total":    job["total"],
        "progress": progress,
        "files":    files,
        "error":    job["error"],
        "input":    job.get("input", ""),
        "warnings": _collect_warnings(results),
        # Per-chart detail drives the side-by-side view: which crop belongs to
        # which CSV, whether the numbers came from the vector layer or from CV,
        # and the accuracy figures shown under each chart.
        "charts":   _chart_payload(results),
        "summary":  _summarise(results),
    })


def _collect_warnings(results: list) -> list:
    out = []
    for r in results:
        if r.get("warnings"):
            label = f"Page {r['page']+1} Chart {r['chart']+1}"
            out.append({"chart": label, "warnings": r["warnings"]})
    return out


def _chart_payload(results: list) -> list:
    """Shape pipeline results for the UI, one entry per chart."""
    out = []
    for r in results:
        out.append({
            "page":        r.get("page"),
            "chart":       r.get("chart"),
            "csv_file":    r.get("csv_file"),
            "image_file":  r.get("image_file"),
            "animal_id":   r.get("animal_id"),
            "date":        r.get("date"),
            "date_printed": r.get("date_printed"),
            "time":        r.get("time"),
            "time_full":   r.get("time_full"),
            "farm":        r.get("farm"),
            "milk_kg":     r.get("milk_kg"),
            "gnr":         r.get("gnr"),
            "bimo":        r.get("bimo"),
            "le":          r.get("le"),
            "source":      r.get("source", "cv"),
            "metrics":     r.get("metrics", {}),
            "calibration": r.get("calibration", {}),
            "yield_ratio": r.get("yield_ratio"),
            "milk_scale": r.get("milk_scale"),
            "milk_calibrated": r.get("milk_calibrated"),
            "milk_uncalibrated_reason": r.get("milk_uncalibrated_reason"),
            "milk_measured_kg": r.get("milk_measured_kg"),
            "milk_pct_of_printed": r.get("milk_pct_of_printed"),
            "measured_only": r.get("measured_only"),
            "reaches_axis_end": r.get("reaches_axis_end"),
            "fidelity":    r.get("fidelity", {}),
            "accuracy_pct": _accuracy_pct(r),
            "warnings":    r.get("warnings", []),
        })
    return out


# Single definition, shared with the CLI, so the web app and the terminal can
# never disagree about what "accuracy" means.
_accuracy_pct = accuracy_pct


def _summarise(results: list) -> dict:
    """Job-level accuracy roll-up shown at the top of the results panel."""
    if not results:
        return {}
    extracted = [r for r in results if r.get("csv_file")]
    vector = sum(1 for r in extracted if r.get("source") == "vector")
    ratios = [r["yield_ratio"] for r in extracted
              if isinstance(r.get("yield_ratio"), (int, float))]
    resids = [
        r["calibration"].get("y_residual")
        for r in extracted
        if isinstance(r.get("calibration"), dict)
        and isinstance(r["calibration"].get("y_residual"), (int, float))
    ]
    summary = {
        "charts_total":     len(results),
        "charts_extracted": len(extracted),
        "vector_charts":    vector,
        "cv_charts":        len(extracted) - vector,
    }

    # Headline figure: how closely the extracted curves reproduce the printed
    # ones. This is what the digitiser is responsible for.
    accs = [a for a in (_accuracy_pct(r) for r in extracted) if a is not None]
    if accs:
        accs.sort()
        summary["accuracy_pct"] = round(accs[len(accs) // 2], 2)
        summary["accuracy_worst"] = round(accs[0], 2)
        # Explicit pass/fail against the agreed threshold, so the guarantee is
        # checked on every run rather than taken on trust. A chart that ever
        # fell short would be named here instead of hiding behind the median.
        summary["accuracy_threshold"] = ACCURACY_THRESHOLD_PCT
        summary["charts_passing"] = sum(1 for a in accs
                                        if a >= ACCURACY_THRESHOLD_PCT)
        summary["charts_below_threshold"] = [
            {"animal_id": r.get("animal_id"),
             "page": r.get("page"), "chart": r.get("chart"),
             "accuracy_pct": _accuracy_pct(r)}
            for r in extracted
            if (_accuracy_pct(r) or 0) < ACCURACY_THRESHOLD_PCT
        ]

    fid_meds = [
        r["fidelity"]["flusso"]["median"]
        for r in extracted
        if (r.get("fidelity") or {}).get("flusso")
    ]
    if fid_meds:
        fid_meds.sort()
        summary["fidelity_median"] = round(fid_meds[len(fid_meds) // 2], 4)
        summary["fidelity_worst"] = round(fid_meds[-1], 4)

    # Milk totals for the whole report: what the AMS printed, and what the
    # drawn curves add up to. Shown as two figures rather than a ratio - a
    # per-chart percentage reads like an extraction fault when the two simply
    # disagree in the source.
    printed = [r["milk_kg"] for r in extracted
               if isinstance(r.get("milk_kg"), (int, float))]
    curve = [
        r["metrics"]["flusso"]["integral"]
        for r in extracted
        if isinstance((r.get("metrics") or {}).get("flusso"), dict)
        and isinstance(r["metrics"]["flusso"].get("integral"), (int, float))
    ]
    if printed:
        summary["milk_printed_total"] = round(sum(printed), 2)
    if curve:
        summary["milk_curve_total"] = round(sum(curve), 2)

    # The same comparison over charts the time axis did not cut off. Those four
    # are low because their curve stops mid-session in the source PDF, so
    # including them understates how well the rest reproduce their weights.
    def _truncated(r):
        return bool(r.get("reaches_axis_end"))

    complete = [
        r for r in extracted
        if not _truncated(r)
        and isinstance(r.get("milk_kg"), (int, float))
        and isinstance((r.get("metrics") or {}).get("flusso"), dict)
    ]
    if complete:
        pm = sum(r["milk_kg"] for r in complete)
        cm = sum(r["metrics"]["flusso"]["integral"] for r in complete)
        if pm:
            summary["milk_pct_complete"] = round(100.0 * cm / pm, 2)
            summary["complete_charts"] = len(complete)
            # The page needs the total as well, to say how many sessions the
            # time axis cut off rather than just how many it did not.
            summary["chart_count"] = len(extracted)

    # How many charts the printed-weight calibration actually accepted. A
    # refused chart is reported as measured, so these two counts are what the
    # headline accuracy figure rests on.
    calibrated = [r for r in extracted if r.get("milk_calibrated")]
    refused = [r for r in extracted
               if r.get("milk_uncalibrated_reason") == "exceeds_pen_width"]
    if extracted:
        summary["charts_calibrated"] = len(calibrated)
        summary["charts_measured_only"] = len(refused)

    if ratios:
        summary["yield_ratio_median"] = round(sorted(ratios)[len(ratios) // 2], 4)
    if resids:
        summary["calib_residual_max"] = round(max(resids), 5)
    return summary


def _safe_job_file(job_id: str, *parts: str):
    """
    Resolve a path inside one job's output directory, or None.

    Both components come from the URL, so each is resolved and checked to be
    contained by the job directory. Without this a crafted name could walk out
    of the output tree and read arbitrary files.
    """
    try:
        base = (OUTPUT_DIR / job_id).resolve()
        if not str(base).startswith(str(OUTPUT_DIR.resolve())):
            return None
        target = base.joinpath(*parts).resolve()
        if not str(target).startswith(str(base)):
            return None
        return target if target.is_file() else None
    except (OSError, ValueError):
        return None


@app.route("/download/<job_id>/<filename>")
def download(job_id: str, filename: str):
    file_path = _safe_job_file(job_id, filename)
    if file_path is None:
        return jsonify({"error": "File not found"}), 404
    return send_file(str(file_path), as_attachment=True, download_name=filename)


@app.route("/chart-image/<job_id>/<filename>")
def chart_image(job_id: str, filename: str):
    """
    Serve one chart cropped from the uploaded PDF.

    Shown beside the extracted curve so the original and the extraction can be
    compared directly. Served inline rather than as an attachment.
    """
    file_path = _safe_job_file(job_id, CHART_IMAGE_SUBDIR, filename)
    if file_path is None:
        return jsonify({"error": "Image not found"}), 404
    return send_file(str(file_path), mimetype="image/png")


@app.route("/download-all/<job_id>")
def download_all(job_id: str):
    """Return all CSVs as a zip archive."""
    import zipfile
    import io

    out_dir = OUTPUT_DIR / job_id
    csv_files = list(out_dir.glob("*.csv"))
    if not csv_files:
        return jsonify({"error": "No files available"}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for csv_path in csv_files:
            zf.write(csv_path, csv_path.name)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"charts_{job_id[:8]}.zip",
    )


# ---------------------------------------------------------------------------
# Dev server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Chart Digitizer running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
