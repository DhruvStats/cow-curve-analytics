"""
pipeline.py

Classical CV pipeline for extracting curve data from AMS milking chart PDFs.

Steps per page:
  1. Rasterise PDF page to image (PyMuPDF) or load PNG directly
  2. Crop into 8 chart cells (fixed 2x4 grid)
  3. Per chart cell:
       a. Detect plot area bounding box (axis lines)
       b. OCR the header to extract animal ID, date, time
       c. Isolate Flusso curve  (blue)  by HSV colour mask
       d. Isolate Pressione curve (green) by HSV colour mask
       e. Extract skeleton pixel coords column-by-column
       f. Map pixel → data coordinates using axis calibration
       g. Write CSV  animal_{ID}_{YYYY-MM-DD}[_{HHMM}].csv

Usage:
    python pipeline.py --input page_001.png --out ./csv_output
    python pipeline.py --input report.pdf  --out ./csv_output
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    from . import vector_extract           # package import
except ImportError:                        # pragma: no cover - script/CLI use
    import vector_extract                  # flat import (app.py, CLI)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Every tunable value lives in settings.py. They are imported by name so the
# code below reads unchanged, and so there is exactly one place to look when
# something about the report format changes.
try:
    from . import settings
except ImportError:                        # pragma: no cover - script/CLI use
    import settings

GRID_ROWS = settings.GRID_ROWS
GRID_COLS = settings.GRID_COLS
CHARTS_PER_PAGE = settings.CHARTS_PER_PAGE

# Fallback axis range for the CV path only. The vector path reads each chart's
# real range from its own printed tick labels and never uses these.
X_DATA_MIN, X_DATA_MAX = 0.0, 10.0
Y_DATA_MIN, Y_DATA_MAX = 0.0, 9.0

RASTER_DPI = settings.RASTER_DPI
CROP_DPI = settings.CROP_DPI
FIDELITY_DPI = settings.FIDELITY_DPI
RUN_FIDELITY_CHECK = settings.RUN_FIDELITY_CHECK
ACCURACY_THRESHOLD_PCT = settings.ACCURACY_THRESHOLD_PCT
CHART_IMAGE_SUBDIR = settings.CHART_IMAGE_SUBDIR
CSV_TIME_STEP_MIN = settings.CSV_TIME_STEP_MIN
CSV_DECIMALS = settings.CSV_DECIMALS
CALIBRATE_TO_PRINTED_MILK = settings.CALIBRATE_TO_PRINTED_MILK
MIN_CURVE_COVERAGE = settings.MIN_CURVE_COVERAGE
CURVE_FLOW = settings.CURVE_FLOW
CURVE_PRESSURE = settings.CURVE_PRESSURE

# HSV ranges for the CV fallback path, where colours are matched in a
# rasterised image rather than read from the vector layer.
BLUE_HSV_LOW = np.array([95, 60, 60])
BLUE_HSV_HIGH = np.array([135, 255, 255])
GREEN_HSV_LOW = np.array([40, 40, 40])
GREEN_HSV_HIGH = np.array([90, 255, 255])


def accuracy_pct(result: dict) -> float | None:
    """
    Curve-match accuracy for one chart, as a percentage.

    Expressed against the chart's full value range rather than against the
    local value: a fixed absolute error means the same whether it lands on a
    peak or in a trough, whereas a percentage-of-value would blow up to
    meaningless numbers wherever the curve passes near zero.
    """
    fid = (result.get("fidelity") or {}).get("flusso")
    if not fid:
        return None
    box = (result.get("calibration") or {}).get("box") or {}
    span = (box.get("v_top", Y_DATA_MAX) or Y_DATA_MAX) - \
           (box.get("v_bottom", Y_DATA_MIN) or Y_DATA_MIN)
    if span <= 0:
        return None
    return round(max(0.0, 100.0 * (1.0 - fid["median"] / span)), 2)

# ---------------------------------------------------------------------------
# PDF / image loading
# ---------------------------------------------------------------------------

def load_pages(input_path: str, dpi: int = RASTER_DPI) -> list[np.ndarray]:
    """Return a list of BGR numpy arrays, one per page."""
    ext = Path(input_path).suffix.lower()

    if ext == ".pdf":
        if not HAS_FITZ:
            raise RuntimeError("PyMuPDF (fitz) is required to read PDFs. pip install pymupdf")
        doc = fitz.open(input_path)
        pages = []
        for page in doc:
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
            pages.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        doc.close()
        return pages

    elif ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
        img = cv2.imread(input_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {input_path}")
        return [img]

    else:
        raise ValueError(f"Unsupported input format: {ext}")


# ---------------------------------------------------------------------------
# Page → chart cells
# ---------------------------------------------------------------------------

def slice_page_into_charts(page: np.ndarray) -> list[np.ndarray]:
    """
    Divide a page image into CHARTS_PER_PAGE cells using the fixed 2x4 grid.
    Returns a list of 8 BGR images ordered left-to-right, top-to-bottom.
    """
    h, w = page.shape[:2]

    # Small top margin for the page-level title
    top_margin    = int(h * 0.015)
    bottom_margin = int(h * 0.005)
    left_margin   = int(w * 0.005)
    right_margin  = int(w * 0.005)

    usable_h = h - top_margin - bottom_margin
    usable_w = w - left_margin - right_margin

    cell_h = usable_h // GRID_ROWS
    cell_w = usable_w // GRID_COLS

    cells = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            y0 = top_margin + row * cell_h
            y1 = y0 + cell_h
            x0 = left_margin + col * cell_w
            x1 = x0 + cell_w
            cells.append(page[y0:y1, x0:x1].copy())

    return cells


# ---------------------------------------------------------------------------
# Plot area detection
# ---------------------------------------------------------------------------

def detect_plot_area(cell: np.ndarray) -> tuple[int, int, int, int]:
    """
    Detect the bounding box of the actual plot area (inside the axes) by
    finding the dominant horizontal and vertical axis lines.

    Returns (x_left, y_top, x_right, y_bottom) in pixel coordinates
    relative to the cell image.
    Falls back to a conservative estimate if detection fails.
    """
    h, w = cell.shape[:2]
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)

    # Binarise: dark lines on light background
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    # --- Horizontal lines ---
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 4, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    h_proj = np.sum(h_lines, axis=1)

    # --- Vertical lines ---
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 4))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    v_proj = np.sum(v_lines, axis=0)

    # Find axis candidates: strongest lines in each projection
    # We expect the bottom axis and top boundary for horizontal,
    # left axis and right boundary for vertical.
    h_thresh = max(h_proj) * 0.3 if max(h_proj) > 0 else 1
    v_thresh = max(v_proj) * 0.3 if max(v_proj) > 0 else 1

    h_candidates = np.where(h_proj > h_thresh)[0]
    v_candidates = np.where(v_proj > v_thresh)[0]

    # Fallback margins
    fallback_top    = int(h * 0.15)
    fallback_bottom = int(h * 0.88)
    fallback_left   = int(w * 0.08)
    fallback_right  = int(w * 0.88)

    if len(h_candidates) >= 2:
        # Skip page-edge noise only. The morphological opening above already
        # removes text, and a 10% cutoff was discarding the plot's top frame
        # in tall cells (leaving just the x-axis → degenerate box → wrong
        # fallback margins and a large vertical calibration bias).
        valid_h = h_candidates[(h_candidates > h * 0.03) & (h_candidates < h * 0.97)]
        y_top    = int(valid_h.min()) if len(valid_h) > 0 else fallback_top
        y_bottom = int(valid_h.max()) if len(valid_h) > 0 else fallback_bottom
    else:
        y_top, y_bottom = fallback_top, fallback_bottom

    if len(v_candidates) >= 2:
        valid_v = v_candidates[(v_candidates > w * 0.03) & (v_candidates < w * 0.97)]
        x_left  = int(valid_v.min()) if len(valid_v) > 0 else fallback_left
        x_right = int(valid_v.max()) if len(valid_v) > 0 else fallback_right
    else:
        x_left, x_right = fallback_left, fallback_right

    # Sanity check: plot area must be at least 20% of cell dimensions
    if (x_right - x_left) < w * 0.20:
        x_left, x_right = fallback_left, fallback_right
    if (y_bottom - y_top) < h * 0.20:
        y_top, y_bottom = fallback_top, fallback_bottom

    return x_left, y_top, x_right, y_bottom


# ---------------------------------------------------------------------------
# Coordinate transform
# ---------------------------------------------------------------------------

class AxisTransform:
    """Maps pixel coordinates inside the plot area to data coordinates."""

    def __init__(
        self,
        px_left: int, px_right: int,
        px_top: int,  px_bottom: int,
        x_min: float = X_DATA_MIN, x_max: float = X_DATA_MAX,
        y_min: float = Y_DATA_MIN, y_max: float = Y_DATA_MAX,
    ):
        self.px_left   = px_left
        self.px_right  = px_right
        self.px_top    = px_top
        self.px_bottom = px_bottom
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

    def px_to_data(self, px_x: float, px_y: float) -> tuple[float, float]:
        """Convert pixel (x, y) → data (x, y)."""
        px_w = self.px_right  - self.px_left
        px_h = self.px_bottom - self.px_top

        if px_w == 0 or px_h == 0:
            return 0.0, 0.0

        data_x = self.x_min + (px_x - self.px_left)  / px_w * (self.x_max - self.x_min)
        # Y axis is inverted in image coordinates
        data_y = self.y_max - (px_y - self.px_top)   / px_h * (self.y_max - self.y_min)

        data_x = float(np.clip(data_x, self.x_min, self.x_max))
        data_y = float(np.clip(data_y, self.y_min, self.y_max))
        return round(data_x, 4), round(data_y, 4)


# ---------------------------------------------------------------------------
# Colour-based curve extraction
# ---------------------------------------------------------------------------

def extract_curve_pixels(
    plot_region: np.ndarray,
    hsv_low: np.ndarray,
    hsv_high: np.ndarray,
) -> np.ndarray | None:
    """
    Given the cropped plot region (BGR), extract pixels matching the HSV range.
    Returns an (N, 2) array of (x, y) pixel coordinates relative to plot_region,
    or None if no sufficient curve is found.
    """
    hsv = cv2.cvtColor(plot_region, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, hsv_low, hsv_high)

    # Clean up noise
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    coords = np.column_stack(np.where(mask > 0))  # (row, col)
    if len(coords) == 0:
        return None

    # Check coverage
    h, w = plot_region.shape[:2]
    x_coverage = (coords[:, 1].max() - coords[:, 1].min()) / w
    if x_coverage < MIN_CURVE_COVERAGE:
        return None

    # Return as (x, y) = (col, row)
    return coords[:, [1, 0]]


def pixels_to_curve(
    pixels: np.ndarray,
    transform: AxisTransform,
    n_samples: int = 300,
    anchor_origin: bool = True,
    anchor_end: bool = False,
) -> tuple[list[float], list[float]]:
    """
    Convert raw pixel cloud → sampled curve (time_min, value) lists.

    For each x column, take the median y of all matching pixels (robust to
    anti-aliasing and minor noise), then map to data coordinates.
    Outputs are sampled at n_samples evenly-spaced x positions.

    When ``anchor_origin`` is True the curve is pinned to the plot origin
    (time=0, value=0). The colour mask loses the ramp-up segment near the
    origin because the curve there is drawn over the black axis lines, so the
    leftmost detected pixel lands several percent into the plot. We inject the
    plot's bottom-left corner as a known control point — the axis transform
    maps it exactly to data (0, 0) — and sample from the left axis, so every
    curve starts at (0, 0) and ramps smoothly to the first detected pixel.

    When ``anchor_end`` is True the curve is pinned to the plot's bottom-right
    corner → data (time=X_DATA_MAX, value=0). This is the mirror of the origin
    problem: the Flusso flow curve returns to ~0 partway through and then runs
    flat along the x-axis to the end of the session, where those pixels are
    again lost over the axis line. Only enable this for curves that physically
    return to zero (Flusso), not ones that stay elevated (Pressione). A guard
    keeps it from fabricating a long flat tail on a poorly-detected fragment.
    """
    if pixels is None or len(pixels) == 0:
        return [], []

    # Group by column (x pixel)
    x_cols = pixels[:, 0]
    y_rows = pixels[:, 1]

    col_min = int(x_cols.min())
    col_max = int(x_cols.max())

    col_to_y = {}
    for col in range(col_min, col_max + 1):
        ys = y_rows[x_cols == col]
        if len(ys) > 0:
            col_to_y[col] = int(np.median(ys))

    if len(col_to_y) < 2:
        return [], []

    # Pin the curve to the plot origin. In plot-region coordinates the
    # bottom-left corner is (col=0, row=plot_height); px_to_data sends that to
    # data (0, 0). Extending col_min to 0 makes the time axis start at 0 and
    # np.interp below draws the missing ramp from the origin to the first pixel.
    plot_width  = transform.px_right  - transform.px_left
    plot_height = transform.px_bottom - transform.px_top
    if anchor_origin:
        col_to_y[0] = int(plot_height)
        col_min = 0

    # Pin the flow curve's tail to the bottom-right corner → data (X_MAX, 0).
    # Guard: only extend when the last detected point has already returned to
    # the axis (value near 0) — then the flat zero tail is physically implied
    # (session ended), whether the session was short or ran the full window.
    # A curve that ends mid-air is a detection fragment and is left alone.
    if anchor_end and plot_width > 0 and plot_height > 0:
        last_row = col_to_y[max(k for k in col_to_y if k > 0)]
        if last_row >= 0.88 * plot_height:
            col_to_y[int(plot_width)] = int(plot_height)
            col_max = int(plot_width)

    # Interpolate across all columns in range
    all_cols = np.arange(col_min, col_max + 1)
    known_cols = np.array(sorted(col_to_y.keys()))
    known_rows = np.array([col_to_y[c] for c in known_cols])
    interp_rows = np.interp(all_cols, known_cols, known_rows)

    # Sample n_samples points evenly
    indices = np.linspace(0, len(all_cols) - 1, min(n_samples, len(all_cols)), dtype=int)
    sampled_cols = all_cols[indices]
    sampled_rows = interp_rows[indices]

    times, values = [], []
    for px_x, px_y in zip(sampled_cols, sampled_rows):
        t, v = transform.px_to_data(
            px_x + transform.px_left,
            px_y + transform.px_top,
        )
        times.append(t)
        values.append(v)

    return times, values


# ---------------------------------------------------------------------------
# OCR metadata extraction
# ---------------------------------------------------------------------------

# Temp dir for OCR images — must be outside /tmp to avoid sandbox restrictions
_OCR_TMP_DIR = Path(__file__).parent.parent / ".ocr_tmp"
_OCR_TMP_DIR.mkdir(exist_ok=True)

_ocr_counter = 0


def _tesseract_ocr(gray_img: np.ndarray, psm: int = 6) -> str:
    """Call tesseract directly via subprocess using a local temp file."""
    global _ocr_counter
    _ocr_counter += 1
    tmp_path = str(_OCR_TMP_DIR / f"ocr_{os.getpid()}_{_ocr_counter}.png")
    try:
        cv2.imwrite(tmp_path, gray_img)
        result = subprocess.run(
            ["tesseract", tmp_path, "stdout", "--psm", str(psm)],
            capture_output=True,
            timeout=10,
        )
        return result.stdout.decode("utf-8", errors="replace")
    except Exception:
        return ""
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


_DATE_RE     = re.compile(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b")
_TIME_RE     = re.compile(r"\b(\d{1,2}):(\d{2})\b")
# Real PDF uses "Animale: 1001"; synthetic uses "ID: 1001"
_ANIMAL_RE   = re.compile(r"Animale[:\s]*(\d+)", re.IGNORECASE)
_ANIMAL_RE2  = re.compile(r"\bID[:\s]*(\d+)", re.IGNORECASE)
# Real PDF uses "Data: 07.03.2024"
_DATA_DATE_RE = re.compile(r"Data[:\s]*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", re.IGNORECASE)


def ocr_header(cell: np.ndarray) -> dict:
    """
    Extract metadata from the chart header.
    Locates the title text row dynamically so the crop works for all grid rows
    regardless of how much blank padding sits above the title line.
    Returns dict with keys: animal_id, date, time (strings, may be None).
    """
    h, w = cell.shape[:2]

    # OCR the top 55% of the cell at 3× upscale.
    # Using a generous crop so the header is captured for all grid rows in
    # both synthetic and real PDFs. Regex finds fields anywhere in the text.
    region = cell[0 : int(h * 0.55), :]
    scale  = 3
    rh, rw = region.shape[:2]
    big  = cv2.resize(region, (rw * scale, rh * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    text = _tesseract_ocr(thresh, psm=6)

    # --- Animal ID ---
    # Real PDF: "Animale: 1001"   Synthetic: "ID: 1001"
    animal_id = None
    for pattern in (_ANIMAL_RE, _ANIMAL_RE2):
        m = pattern.search(text)
        if m:
            animal_id = m.group(1)
            break

    # --- Date ---
    # Try "Data: DD.MM.YYYY" first (real PDF), then generic DD/MM/YYYY
    date_str = None
    m = _DATA_DATE_RE.search(text) or _DATE_RE.search(text)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        if len(year) == 2:
            year = "20" + year
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # --- Time ---
    # Real PDF: "Ora: HH:MM:SS"   Synthetic: "HH:MM"
    time_str = None
    ora_m = re.search(r"Ora[:\s]*(\d{1,2}):(\d{2})", text, re.IGNORECASE)
    if ora_m:
        time_str = f"{ora_m.group(1).zfill(2)}{ora_m.group(2)}"
    else:
        m = _TIME_RE.search(text)
        if m:
            time_str = f"{m.group(1).zfill(2)}{m.group(2)}"

    return {
        "animal_id": animal_id,
        "date": date_str,
        "time": time_str,
        "raw_ocr": text.strip(),
    }


# ---------------------------------------------------------------------------
# CSV naming
# ---------------------------------------------------------------------------

_used_names: dict[str, int] = {}


def make_csv_name(meta: dict, chart_index: int) -> str:
    """Build output CSV filename from metadata, with collision avoidance."""
    aid  = meta.get("animal_id") or f"unknown_{chart_index}"
    date = meta.get("date")      or "unknown_date"

    base = f"animal_{aid}_{date}"

    if base in _used_names:
        _used_names[base] += 1
        time_sfx = meta.get("time") or f"{_used_names[base]:04d}"
        return f"{base}_{time_sfx}.csv"

    _used_names[base] = 0
    return f"{base}.csv"


# ---------------------------------------------------------------------------
# Per-chart processor
# ---------------------------------------------------------------------------

def process_chart(
    cell: np.ndarray,
    chart_index: int,
    page_index: int,
    out_dir: str,
    meta_hint: dict | None = None,
) -> dict:
    """
    Full pipeline for a single chart cell.
    Returns a result dict summarising what was extracted.
    """
    result = {
        "page": page_index,
        "chart": chart_index,
        "csv_file": None,
        "animal_id": None,
        "date": None,
        "flusso_points": 0,
        "pressione_points": 0,
        "warnings": [],
    }

    # 1. Metadata — prefer page-level OCR hint, fall back to per-cell OCR
    if meta_hint and (meta_hint.get("animal_id") or meta_hint.get("date")):
        meta = meta_hint
    else:
        meta = ocr_header(cell)

    result["animal_id"] = meta["animal_id"]
    result["date"]      = meta["date"]

    if meta["animal_id"] is None:
        result["warnings"].append("OCR could not read animal ID")
    if meta["date"] is None:
        result["warnings"].append("OCR could not read date")

    # 2. Plot area detection
    x_left, y_top, x_right, y_bottom = detect_plot_area(cell)
    transform = AxisTransform(x_left, x_right, y_top, y_bottom)
    plot_region = cell[y_top:y_bottom, x_left:x_right]

    if plot_region.size == 0:
        result["warnings"].append("Empty plot region detected: skipping chart")
        return result

    # 3. Curve extraction — Flusso (blue)
    # Flow returns to zero and runs flat along the x-axis to the session end,
    # so anchor its tail to (X_DATA_MAX, 0) to recover the axis-occluded tail.
    blue_px = extract_curve_pixels(plot_region, BLUE_HSV_LOW, BLUE_HSV_HIGH)
    flusso_t, flusso_v = pixels_to_curve(blue_px, transform, anchor_end=True)

    if len(flusso_t) == 0:
        result["warnings"].append("Flusso curve not detected")

    # 4. Curve extraction — Pressione (green)
    green_px = extract_curve_pixels(plot_region, GREEN_HSV_LOW, GREEN_HSV_HIGH)
    pressione_t, pressione_v = pixels_to_curve(green_px, transform)

    if len(pressione_t) == 0:
        result["warnings"].append("Pressione curve not detected")

    # 5. Build DataFrame
    # Same three columns as the vector path, so a CSV has one schema whatever
    # route produced it.
    df = _build_long_csv(flusso_t, flusso_v, pressione_t, pressione_v)

    if df is None:
        result["warnings"].append("No curve data extracted")
        return result

    # 6. Write CSV
    csv_name = make_csv_name(meta, chart_index)
    csv_path = os.path.join(out_dir, csv_name)
    df.to_csv(csv_path, index=False)

    result["csv_file"]        = csv_name
    result["flusso_points"]   = len(flusso_t)
    result["pressione_points"] = len(pressione_t)

    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def extract_metadata_from_pdf_page(fitz_page) -> list[dict]:
    """
    Extract chart metadata directly from a PyMuPDF page using embedded text.
    No OCR required — the PDF already contains searchable text.

    Returns a list of CHARTS_PER_PAGE metadata dicts sorted by grid order
    (left-to-right, top-to-bottom) matching slice_page_into_charts cell order.
    Each dict has: animal_id, date, time, y_pt (Y position in PDF points),
                   x_pt (X position in PDF points).
    """
    blocks = fitz_page.get_text("blocks")
    entries = []

    for idx, b in enumerate(blocks):
        text = b[4]
        m_animal = _ANIMAL_RE.search(text)
        if not m_animal:
            continue

        animal_id = m_animal.group(1)
        x0, y0 = b[0], b[1]  # top-left of block in PDF points

        # Merge with the next 1-2 blocks in case Data/Ora are in a separate block
        # (happens when header lines are rendered as separate annotate calls)
        search_text = text
        for lookahead in range(1, 3):
            if idx + lookahead < len(blocks):
                next_text = blocks[idx + lookahead][4]
                # Only merge if the next block is close (within 20 pt vertically)
                next_y = blocks[idx + lookahead][1]
                if abs(next_y - y0) < 20:
                    search_text += " " + next_text

        date_str = None
        m = _DATA_DATE_RE.search(search_text) or _DATE_RE.search(search_text)
        if m:
            day, month, year = m.group(1), m.group(2), m.group(3)
            if len(year) == 2:
                year = "20" + year
            date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        time_str = None
        ora_m = re.search(r"Ora[:\s]*(\d{1,2}):(\d{2})", search_text, re.IGNORECASE)
        if ora_m:
            time_str = f"{ora_m.group(1).zfill(2)}{ora_m.group(2)}"
        else:
            t_m = _TIME_RE.search(search_text)
            if t_m:
                time_str = f"{t_m.group(1).zfill(2)}{t_m.group(2)}"

        entries.append({
            "animal_id": animal_id,
            "date": date_str,
            "time": time_str,
            "y_pt": y0,
            "x_pt": x0,
            "raw_ocr": search_text.strip(),
        })

    if not entries:
        return [{"animal_id": None, "date": None, "time": None}] * CHARTS_PER_PAGE

    # Sort by row (y), then column (x) — matches cell order
    page_w = fitz_page.rect.width
    col_mid = page_w / 2
    entries.sort(key=lambda e: (round(e["y_pt"] / 20) * 20, e["x_pt"] > col_mid))

    # Pad to CHARTS_PER_PAGE
    while len(entries) < CHARTS_PER_PAGE:
        entries.append({"animal_id": None, "date": None, "time": None})

    return entries[:CHARTS_PER_PAGE]


def slice_page_with_pdf_boundaries(page_img: np.ndarray, fitz_page, dpi: int) -> list[np.ndarray]:
    """
    Slice a rasterised page into chart cells using the Y boundaries derived
    from embedded PDF text positions.  This is more accurate than equal-height
    slicing when the PDF renderer adds variable spacing between charts.
    """
    h, w = page_img.shape[:2]
    scale = dpi / 72.0
    page_h_pt = fitz_page.rect.height
    page_w_pt = fitz_page.rect.width

    blocks = fitz_page.get_text("blocks")
    header_ys = sorted(set(
        round(b[1])
        for b in blocks
        if _ANIMAL_RE.search(b[4])
    ))

    if len(header_ys) < GRID_ROWS:
        # Fall back to equal-height slicing
        return slice_page_into_charts(page_img)

    # Derive row boundaries: row starts at each header y, ends just before next
    row_starts_pt = sorted(header_ys)

    cells = []
    for row in range(GRID_ROWS):
        y0_pt = row_starts_pt[row] - 2          # 2pt above header
        y1_pt = (row_starts_pt[row + 1] - 2
                 if row + 1 < len(row_starts_pt)
                 else page_h_pt)

        y0_px = max(0, int(y0_pt * scale))
        y1_px = min(h, int(y1_pt * scale))

        col_w_px = w // GRID_COLS
        for col in range(GRID_COLS):
            x0_px = col * col_w_px
            x1_px = x0_px + col_w_px
            cells.append(page_img[y0_px:y1_px, x0_px:x1_px].copy())

    return cells


def ocr_full_page(page: np.ndarray) -> list[dict]:
    """Fallback: OCR-based page metadata extraction (used for image-only inputs)."""
    h, w = page.shape[:2]
    scale = 2
    big  = cv2.resize(page, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = _tesseract_ocr(thresh, psm=6)

    results: list[dict] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines) and len(results) < CHARTS_PER_PAGE:
        line = lines[i]
        animal_match = _ANIMAL_RE.search(line) or _ANIMAL_RE2.search(line)
        if animal_match:
            block = " ".join(lines[i:i+3])
            animal_id = animal_match.group(1)
            date_str = None
            m = _DATA_DATE_RE.search(block) or _DATE_RE.search(block)
            if m:
                day, month, year = m.group(1), m.group(2), m.group(3)
                if len(year) == 2:
                    year = "20" + year
                date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            time_str = None
            ora_m = re.search(r"Ora[:\s]*(\d{1,2}):(\d{2})", block, re.IGNORECASE)
            if ora_m:
                time_str = f"{ora_m.group(1).zfill(2)}{ora_m.group(2)}"
            results.append({"animal_id": animal_id, "date": date_str, "time": time_str})
            i += 2
            continue
        i += 1

    while len(results) < CHARTS_PER_PAGE:
        results.append({"animal_id": None, "date": None, "time": None})
    return results


def _calibrate_to_printed_milk(f_t, f_v, milk_kg, y_slope=None):
    """
    Scale the flow curve so its area equals the milk weight printed on the
    chart, when the required correction is small enough to be real.

    The AMS measures that weight with its flow meter and prints it in the
    header; it is the machine's own statement of the session total. The drawn
    line has width (1.44pt, a few percent of area over a session), so the true
    curve lies somewhere inside it and a small scale moves within that band.

    A large correction means something else is going on - most often the
    session ran past the right edge of the time axis, so milk was never drawn
    at all. Stretching the visible part to cover it would invent flow the chart
    does not show, so those curves are returned untouched.

    The bound is the ink itself. Half the pen width is the most any single
    reading can honestly be out by; over a session of length T that accounts
    for at most PEN_HALF_WIDTH_KG_MIN * T kilograms of area. A gap wider than
    that cannot be explained by where inside the stroke the true line sits, so
    it is refused rather than applied.

    Returns (values, scale, applied, reason) where reason is None when the
    scale was applied and a short tag otherwise, so callers can report why a
    curve was left as measured.
    """
    v = np.asarray(f_v, dtype=float)
    t = np.asarray(f_t, dtype=float)

    if len(t) < 2 or not milk_kg or milk_kg <= 0:
        return v, 1.0, False, "no_printed_weight"

    area = float(np.trapezoid(v, t))
    if area <= 0:
        return v, 1.0, False, "no_area"

    scale = milk_kg / area
    if not CALIBRATE_TO_PRINTED_MILK:
        return v, scale, False, "disabled"

    # The most area the pen's own width can account for over this session.
    #
    # Half a pen width is a distance on the page, so what it is worth in kg/min
    # depends on the chart's own vertical scale. Taking it from this chart's
    # calibration keeps the bound correct whatever axis a report uses: on a
    # 0-9 axis the same 1.44pt stroke spans 0.0779 kg/min, on a 0-7 axis
    # 0.0468. A fixed figure would be too tight on one and too loose on the
    # other, and wrong outright on a scale neither report uses.
    if y_slope:
        half_pen = abs(float(y_slope)) * settings.PEN_WIDTH_PT / 2.0
    else:
        half_pen = settings.PEN_HALF_WIDTH_KG_MIN

    duration = float(t[-1] - t[0])
    allowed = half_pen * duration * settings.CALIBRATION_TOLERANCE
    gap = abs(milk_kg - area)

    if gap > allowed:
        # Beyond ink ambiguity. Leave the measurement alone and say so; the
        # scale is still returned so the shortfall can be reported.
        return v, scale, False, "exceeds_pen_width"

    return v * scale, scale, True, None


def _build_long_csv(f_t, f_v, p_t, p_v, step: float = CSV_TIME_STEP_MIN,
                    milk_kg: float | None = None, extra=None):
    """
    Build the output table in long form: curve, time_min, value.

    Each curve keeps its own time axis — they are not sampled together in the
    source (the AMS records flow about every 2.7 s and vacuum about every
    11 s), and long form means neither has to be stretched onto the other's
    grid or padded with blanks.

    Within a curve the times are the *union* of a fixed `step` grid and every
    real vertex. That distinction matters: resampling onto a fixed grid alone
    would discard the measured points falling between grid lines and
    re-interpolate them, costing about 0.005 kg/min. Keeping the true vertices
    and laying the grid on top gives the same density with zero loss.

    Each curve starts at t = 0.

    Returns a DataFrame with columns curve / time_min / value, or None.
    """
    frames = []

    # Flow alone when FLOW_ONLY is set: the file carries the curve the system
    # is for, and nothing the AMS happens to plot beside it.
    series = [(CURVE_FLOW, f_t, f_v)]
    if not settings.FLOW_ONLY:
        series.append((CURVE_PRESSURE, p_t, p_v))
        series.extend(extra or [])

    for name, t_raw, v_raw in series:
        t = np.asarray(t_raw, float)
        v = np.asarray(v_raw, float)
        if len(t) < 2:
            continue

        t_end = float(t.max())
        if t_end <= 0:
            continue

        # A plain even grid, so the file is easy to read and every chart has a
        # predictable row spacing. Values between grid points are interpolated
        # from the measured vertices, which are only ~2.7s apart, so a 0.1 min
        # step loses no visible detail while cutting the file to about a fifth
        # of its former size.
        times = np.round(np.arange(0.0, t_end + 1e-9, step), 4)
        if times[-1] < t_end - 1e-9:
            times = np.append(times, round(t_end, 4))

        vals = np.interp(times, t, v)

        # Re-fit the flow curve to the printed weight on the sampled grid.
        # Calibrating against the dense vertices and then resampling leaves a
        # small residue, because the grid integrates very slightly differently;
        # doing it here makes the number in the file exact.
        if name == CURVE_FLOW and milk_kg:
            area = float(np.trapezoid(vals, times))
            if area > 0:
                k = milk_kg / area
                if abs(k - 1.0) <= 1e-3:
                    vals = vals * k

        frames.append(pd.DataFrame({
            "curve": name,
            "time_min": times,
            "value": np.round(vals, CSV_DECIMALS),
        }))

    if not frames:
        return None

    return pd.concat(frames, ignore_index=True)


def _series_metrics(t: list[float], v: list[float]) -> dict:
    """Summary statistics for one extracted curve, used by the accuracy panel."""
    if not t:
        return {"points": 0}
    arr_t = np.asarray(t, dtype=float)
    arr_v = np.asarray(v, dtype=float)
    return {
        "points": len(t),
        "t_min": round(float(arr_t.min()), 4),
        "t_max": round(float(arr_t.max()), 4),
        "v_min": round(float(arr_v.min()), 4),
        "v_max": round(float(arr_v.max()), 4),
        "v_mean": round(float(arr_v.mean()), 4),
        "integral": round(float(np.trapezoid(arr_v, arr_t)), 4),
    }


def _measure_curve_fidelity(fitz_page, cd, dpi: int = FIDELITY_DPI) -> dict | None:
    """
    Measure the extracted curve against the chart as actually printed.

    This is the figure that says how good the digitisation is. The pipeline
    reads the PDF's vector layer; this re-renders the same chart to pixels and
    re-measures the drawn line independently, then reports the disagreement in
    data units. Two different representations agreeing is real evidence.

    Deliberately distinct from the yield cross-check, which compares against
    the milk weight printed in the header. That weight comes from the AMS flow
    meter and does not always agree with the AMS's own drawn curve, so it
    measures the report's internal consistency, not this extraction.

    Returns {curve: {mean, median, max, n}} in data units, or None.
    """
    box = (cd.calib or {}).get("box")
    if not box or not cd.clip:
        return None

    try:
        pix = fitz_page.get_pixmap(
            matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0),
            clip=fitz.Rect(*cd.clip), colorspace=fitz.csRGB)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
    except Exception:
        return None

    h, w = img.shape[:2]
    y_top, y_bot = int(box["top"] * h), int(box["bottom"] * h)
    v_top = box.get("v_top", Y_DATA_MAX)
    v_bot = box.get("v_bottom", Y_DATA_MIN)
    t_min, t_max = cd.calib["t_min"], cd.calib["t_max"]
    if t_max <= t_min or y_bot <= y_top:
        return None

    def probe(x_px, is_match):
        """Value of the lowest matching run in this column, or None.

        Both curves share their colour with the chart's axis labels, which sit
        above the plot box; taking the lowest run keeps the probe on the curve
        rather than averaging it with text.
        """
        ys = [y for y in range(max(0, y_top), min(h, y_bot + 1))
              if is_match(img[y, x_px])]
        if not ys:
            return None
        run = [ys[-1]]
        for y in reversed(ys[:-1]):
            if run[-1] - y <= 2:
                run.append(y)
            else:
                break
        y_mid = sum(run) / len(run)
        frac = (box["bottom"] - y_mid / h) / (box["bottom"] - box["top"])
        return v_bot + frac * (v_top - v_bot)

    def is_blue(p):
        return p[2] > 150 and p[0] < 90 and p[1] < 90

    def is_green(p):
        return p[1] > 90 and p[0] < 90 and p[2] < 90

    out = {}
    for key, ts, vs, match in (
        ("flusso", cd.flusso_t, cd.flusso_v, is_blue),
        ("pressione", cd.pressione_t, cd.pressione_v, is_green),
    ):
        if len(ts) < 3:
            continue
        lo, hi = min(ts), max(ts)
        span = hi - lo
        if span <= 0:
            continue
        # Skip the outermost 5%: there the stroke is clipped by the axis frame
        # and a pixel probe is not meaningful.
        grid = np.linspace(lo + span * 0.05, hi - span * 0.05, 40)
        ref = np.interp(grid, ts, vs)

        diffs = []
        for t, expected in zip(grid, ref):
            frac = (t - t_min) / (t_max - t_min)
            x_px = int(round((box["left"] + frac *
                              (box["right"] - box["left"])) * w))
            if not (0 <= x_px < w):
                continue
            got = probe(x_px, match)
            if got is not None:
                diffs.append(abs(got - expected))

        if len(diffs) >= 5:
            arr = np.asarray(diffs)
            out[key] = {
                "mean": round(float(arr.mean()), 4),
                "median": round(float(np.median(arr)), 4),
                "max": round(float(arr.max()), 4),
                "n": len(diffs),
            }

    return out or None


def _render_chart_image(fitz_page, clip, img_path: str, dpi: int = CROP_DPI) -> bool:
    """
    Crop one chart out of the original page and save it as a PNG.

    This is the visual reference the UI shows beside the extracted curve. It
    is rendered from the source PDF, not redrawn from the extracted numbers,
    so it can actually reveal an extraction mistake.
    """
    try:
        rect = fitz.Rect(*clip)
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = fitz_page.get_pixmap(matrix=mat, clip=rect, colorspace=fitz.csRGB)
        pix.save(img_path)
        return True
    except Exception:
        return False


def _run_vector(fitz_doc, out_dir: str, img_dir: str) -> list[dict]:
    """
    Exact extraction path: read curves straight out of the PDF vector layer.

    Used whenever the document actually stores its curves as paths, which is
    the case for the real AMS report. See vector_extract for why this beats
    re-measuring the drawing in pixels.
    """
    all_results: list[dict] = []

    for page_idx in range(fitz_doc.page_count):
        fitz_page = fitz_doc[page_idx]
        charts = vector_extract.extract_page(fitz_page, page_idx)
        print(f"\n[Page {page_idx + 1}/{fitz_doc.page_count}]  "
              f"{len(charts)} chart(s), vector layer")

        for cd in charts:
            print(f"  Chart {cd.chart + 1}/{len(charts)} ...", end=" ", flush=True)

            result = {
                "page": cd.page,
                "chart": cd.chart,
                "csv_file": None,
                "image_file": None,
                "animal_id": cd.animal_id,
                "date": cd.date,
                "date_printed": cd.date_printed,
                "time": cd.time,
                "time_full": cd.time_full,
                "farm": cd.farm,
                "milk_kg": cd.milk_kg,
                "gnr": cd.gnr,
                "bimo": cd.bimo,
                "le": cd.le,
                "source": cd.source,
                "flusso_points": len(cd.flusso_t),
                "pressione_points": len(cd.pressione_t),
                "warnings": list(cd.warnings),
                "calibration": cd.calib,
                "reaches_axis_end": bool(getattr(cd, "reaches_axis_end", False)),
            }

            # Match the curve's area to the milk weight the AMS printed on the
            # same chart, when the needed correction is small enough to sit
            # inside the drawn line's own width.
            flusso_v, milk_scale, milk_applied, milk_reason = \
                _calibrate_to_printed_milk(
                    cd.flusso_t, cd.flusso_v, cd.milk_kg,
                    y_slope=(cd.calib or {}).get("y_slope"))
            result["milk_scale"] = round(float(milk_scale), 4)
            result["milk_calibrated"] = bool(milk_applied)
            result["milk_uncalibrated_reason"] = milk_reason

            # A refused scale means the drawing is short of the printed weight
            # by more than the ink can explain. Record it as measured so the
            # chart reports what it actually shows.
            if milk_reason == "exceeds_pen_width":
                result["measured_only"] = True
                if cd.milk_kg:
                    measured = float(np.trapezoid(
                        np.asarray(flusso_v, dtype=float),
                        np.asarray(cd.flusso_t, dtype=float)))
                    result["milk_measured_kg"] = round(measured, 3)
                    result["milk_pct_of_printed"] = round(
                        100.0 * measured / cd.milk_kg, 1)
            result["metrics"] = {
                "flusso": _series_metrics(cd.flusso_t, flusso_v),
                "pressione": _series_metrics(cd.pressione_t, cd.pressione_v),
            }

            # Crop the original chart for side-by-side comparison.
            meta_for_name = {"animal_id": cd.animal_id, "date": cd.date,
                             "time": cd.time}
            if cd.clip:
                img_name = f"chart_p{cd.page}_{cd.chart}.png"
                if _render_chart_image(fitz_page, cd.clip,
                                       os.path.join(img_dir, img_name)):
                    result["image_file"] = img_name

            # One row per time, both curves side by side, starting at t = 0.
            extra_series = []
            if getattr(cd, "conduct_t", None):
                extra_series.append(
                    (settings.CURVE_CONDUCTIVITY, cd.conduct_t, cd.conduct_v))
            if getattr(cd, "temp_t", None):
                extra_series.append(
                    (settings.CURVE_TEMPERATURE, cd.temp_t, cd.temp_v))

            df = _build_long_csv(cd.flusso_t, flusso_v,
                                 cd.pressione_t, cd.pressione_v,
                                 milk_kg=cd.milk_kg if milk_applied else None,
                                 extra=extra_series)

            if df is not None:
                csv_name = make_csv_name(meta_for_name, cd.chart)
                df.to_csv(os.path.join(out_dir, csv_name), index=False)
                result["csv_file"] = csv_name
                result["csv_rows"] = len(df)

                # Independent cross-check: integrating the flow curve should
                # reproduce the milk quantity printed in the header. It is a
                # figure the AMS measured separately, so agreement is real
                # evidence the calibration is right.
                integ = result["metrics"]["flusso"].get("integral")
                if cd.milk_kg and integ:
                    result["yield_ratio"] = round(integ / cd.milk_kg, 4)

                # How closely the CSV reproduces the printed curve. This is the
                # digitisation's own accuracy, independent of whether the
                # report's milk weight agrees with its own drawing.
                if RUN_FIDELITY_CHECK:
                    fid = _measure_curve_fidelity(fitz_page, cd)
                    if fid:
                        result["fidelity"] = fid

            status = result["csv_file"] or "SKIPPED"
            warn = f"  [!] {'; '.join(result['warnings'])}" if result["warnings"] else ""
            print(f"{status}{warn}")

            all_results.append(result)

    return all_results


def _run_cv(input_path: str, out_dir: str, img_dir: str,
            fitz_doc, dpi: int) -> list[dict]:
    """
    Pixel-based fallback: rasterise and recover the curves by colour.

    Used for scanned PDFs and for PNG/JPG uploads, where there is no vector
    layer to read. Less accurate than the vector path — the curve is measured
    from a drawing rather than read — so results are tagged source="cv" and
    the UI marks them as estimated.
    """
    pages = load_pages(input_path, dpi=dpi)
    all_results: list[dict] = []

    for page_idx, page in enumerate(pages):
        print(f"\n[Page {page_idx + 1}/{len(pages)}]  CV fallback")

        fitz_page = fitz_doc[page_idx] if fitz_doc else None

        if fitz_page:
            page_meta = extract_metadata_from_pdf_page(fitz_page)
            cells     = slice_page_with_pdf_boundaries(page, fitz_page, dpi)
        else:
            page_meta = ocr_full_page(page)
            cells     = slice_page_into_charts(page)

        for chart_idx, cell in enumerate(cells):
            print(f"  Chart {chart_idx + 1}/{len(cells)} ...", end=" ", flush=True)
            meta_hint = page_meta[chart_idx] if chart_idx < len(page_meta) else None
            result = process_chart(cell, chart_idx, page_idx, out_dir,
                                   meta_hint=meta_hint)
            result["source"] = "cv"

            # Save the cell itself as the visual reference, so the UI can show
            # the original next to the extracted curve on this path too.
            img_name = f"chart_p{page_idx}_{chart_idx}.png"
            try:
                cv2.imwrite(os.path.join(img_dir, img_name), cell)
                result["image_file"] = img_name
            except Exception:
                pass

            status = result["csv_file"] or "SKIPPED"
            warn = f"  [!] {'; '.join(result['warnings'])}" if result["warnings"] else ""
            print(f"{status}{warn}")

            all_results.append(result)

    return all_results


def run_pipeline(input_path: str, out_dir: str, dpi: int = RASTER_DPI) -> list[dict]:
    """
    Run the full pipeline on a PDF or image file.

    Takes the exact vector path when the PDF stores its curves as paths, and
    falls back to the pixel/CV path otherwise. Returns a list of result dicts
    (one per chart across all pages).
    """
    os.makedirs(out_dir, exist_ok=True)
    img_dir = os.path.join(out_dir, CHART_IMAGE_SUBDIR)
    os.makedirs(img_dir, exist_ok=True)
    _used_names.clear()

    is_pdf = Path(input_path).suffix.lower() == ".pdf"
    fitz_doc = fitz.open(input_path) if (is_pdf and HAS_FITZ) else None

    try:
        use_vector = bool(fitz_doc) and vector_extract.has_vector_curves(fitz_doc)

        if use_vector:
            results = _run_vector(fitz_doc, out_dir, img_dir)
            # A vector PDF whose charts could not be located at all is better
            # served by the pixel path than by returning nothing.
            if results:
                return results
            print("Vector layer yielded no charts; falling back to CV.")

        return _run_cv(input_path, out_dir, img_dir, fitz_doc, dpi)

    finally:
        if fitz_doc:
            fitz_doc.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AMS Chart Digitizer — CV Pipeline")
    parser.add_argument("--input",  required=True, help="Input PDF or image file")
    parser.add_argument("--out",    default="./csv_output", help="Output directory for CSV files")
    parser.add_argument("--dpi",    type=int, default=RASTER_DPI, help="PDF rasterisation DPI")
    parser.add_argument("--report", action="store_true", help="Save a JSON summary report")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    print(f"Input : {args.input}")
    print(f"Output: {args.out}")
    print(f"DPI   : {args.dpi}")

    results = run_pipeline(args.input, args.out, dpi=args.dpi)

    total   = len(results)
    success = sum(1 for r in results if r["csv_file"])
    skipped = total - success

    print(f"\n{'='*50}")
    print(f"Done. {success}/{total} charts extracted, {skipped} skipped.")

    # Report curve-match accuracy per chart and enforce the threshold, so a
    # regression fails the run instead of being averaged away.
    accs = []
    failed = []
    for r in results:
        acc = accuracy_pct(r)
        if acc is None:
            continue
        accs.append(acc)
        if acc < ACCURACY_THRESHOLD_PCT:
            failed.append((r.get("animal_id"), acc))

    if accs:
        accs_sorted = sorted(accs)
        median = accs_sorted[len(accs_sorted) // 2]
        print(f"Curve match vs printed: median {median:.2f}%, "
              f"worst {accs_sorted[0]:.2f}%  "
              f"({len(accs) - len(failed)}/{len(accs)} "
              f">= {ACCURACY_THRESHOLD_PCT}%)")
        if failed:
            for aid, acc in failed:
                print(f"  BELOW THRESHOLD: animal {aid} at {acc:.2f}%")

    if args.report:
        report_path = os.path.join(args.out, "pipeline_report.json")
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
