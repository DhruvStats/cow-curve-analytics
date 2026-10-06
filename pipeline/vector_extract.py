"""
vector_extract.py

Exact curve extraction from vector AMS PDFs.

The real AMS report does not merely *draw a picture* of each milking session —
it stores every curve as a vector path with explicit coordinates, and every
axis tick as real text. That means the underlying numbers are already inside
the file: rasterising the page and guessing the curve back out of coloured
pixels (pipeline.py) throws information away and then tries to recover it.

This module reads the numbers directly.

Why this matters (measured on the real report, animal 1001):
    pixel/CV path : peak flow 5.96 kg/min, curve runs to t = 10.0 min
    vector path   : peak flow 1.71 kg/min, curve ends at t = 3.95 min
    printed chart : peak flow ~1.7  kg/min, curve ends at ~4.0 min

The CV number was wrong in two independent ways, both structural:

  1. The blue Y-axis tick labels ("0".."9" up the left edge) are drawn in the
     *same* pure blue (RGB 0,0,1 / HSV hue 120, sat 255) as the Flusso curve.
     They sit inside the detected plot box, so the HSV mask swallowed them and
     the label "9" near the top dragged the curve's apparent peak to ~6.
  2. `anchor_end` invented a flat zero tail out to t = 10 for a session that
     actually stopped at t = 3.95.

Neither is fixable by tuning thresholds — the tick glyphs are colour-identical
to the curve. Reading the vector layer sidesteps both.

Per-chart calibration is derived from that chart's own axis text, never
assumed, so a chart with a non-standard range still maps correctly:
  Y: least-squares fit over the chart's own "0".."9" tick glyph centres
     (max residual measured at 0.004 units across all 16 real charts)
  X: the black axis frame, cross-checked against the tick label row

Public API:
    has_vector_curves(doc)   -> bool
    extract_page(page, idx)  -> list[ChartData]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

# --- Layout / parsing constants ------------------------------------------

# Layout values come from settings.py, the single place where anything
# tunable lives. Imported by name so the code below reads unchanged.
try:
    from . import settings
except ImportError:                        # pragma: no cover - script/CLI use
    import settings

GRID_ROWS = settings.GRID_ROWS
GRID_COLS = settings.GRID_COLS
CHARTS_PER_PAGE = settings.CHARTS_PER_PAGE
ROW_BUCKET_PT = settings.ROW_BUCKET_PT
HEADER_PAD_PT = settings.HEADER_PAD_PT
COLUMN_OVERLAP_PT = settings.COLUMN_OVERLAP_PT

# Curve colour tests, in PDF DeviceRGB (0..1). The report uses pure blue
# (0,0,1) and a dark green (0, 0.627, 0.039). Generous margins so a slightly
# different AMS firmware palette still classifies, while staying far away from
# the greys (0.75) and black (0) used for grid and frame.
def _is_blue(c) -> bool:
    return (c[2] > settings.BLUE_MIN_B
            and c[0] < settings.BLUE_MAX_R
            and c[1] < settings.BLUE_MAX_G
            # Blue must lead red, or a purple trace drawn alongside the flow
            # curve is counted as part of it.
            and c[2] - c[0] > settings.CHANNEL_DOMINANCE)


def _is_green(c) -> bool:
    return (c[1] > settings.GREEN_MIN_G
            and c[0] < settings.GREEN_MAX_R
            and c[2] < settings.GREEN_MAX_B
            and c[1] - c[0] > settings.CHANNEL_DOMINANCE)


def _near(c, target, tol=settings.TRACE_COLOUR_TOL) -> bool:
    """Match a stroke against a trace colour taken from the chart's legend."""
    return (abs(c[0] - target[0]) <= tol
            and abs(c[1] - target[1]) <= tol
            and abs(c[2] - target[2]) <= tol)


def _is_conduct(c) -> bool:
    return _near(c, settings.COLOUR_CONDUCTIVITY)


def _is_temp(c) -> bool:
    return _near(c, settings.COLOUR_TEMPERATURE)


_ANIMAL_RE = re.compile(r"Animale[:\s]*(\d+)", re.IGNORECASE)
_ANIMAL_RE2 = re.compile(r"\bID[:\s]*(\d+)", re.IGNORECASE)
_DATA_DATE_RE = re.compile(
    r"Data[:\s]*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", re.IGNORECASE
)
_DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
# Seconds are optional in the pattern but captured when present, so the CSV can
# carry the session time exactly as the report prints it (e.g. "03:58:23")
# rather than silently truncating to the minute.
_ORA_RE = re.compile(r"Ora[:\s]*(\d{1,2}):(\d{2})(?::(\d{2}))?", re.IGNORECASE)
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_MILK_RE = re.compile(r"latte[:\s]*([\d.,]+)\s*kg", re.IGNORECASE)
_FARM_RE = re.compile(r"Numero\s+Azienda\s*([\w]+)", re.IGNORECASE)
_GNR_RE = re.compile(r"GNR[:\s]*(\w+)", re.IGNORECASE)
_BIMO_RE = re.compile(r"BIMO\s*=\s*(\w+)", re.IGNORECASE)
_LE_RE = re.compile(r"LE\s*=\s*(\w+)", re.IGNORECASE)

_INT_RE = re.compile(r"^\d{1,2}$")


@dataclass
class ChartData:
    """One milking chart: metadata, both curves, and provenance."""

    page: int
    chart: int
    animal_id: str | None = None
    date: str | None = None
    date_printed: str | None = None
    time: str | None = None
    time_full: str | None = None
    milk_kg: float | None = None
    gnr: str | None = None
    bimo: str | None = None
    le: str | None = None
    farm: str | None = None

    # Clip rectangle in PDF points (x0, y0, x1, y1) for cropping the original.
    clip: tuple[float, float, float, float] | None = None

    flusso_t: list[float] = field(default_factory=list)
    flusso_v: list[float] = field(default_factory=list)
    pressione_t: list[float] = field(default_factory=list)
    pressione_v: list[float] = field(default_factory=list)

    # Extra traces, present only in reports that plot them. Each carries its
    # own right-hand axis, so these are never mixed into the milk figures.
    conduct_t: list[float] = field(default_factory=list)
    conduct_v: list[float] = field(default_factory=list)
    temp_t: list[float] = field(default_factory=list)
    temp_v: list[float] = field(default_factory=list)

    source: str = "vector"
    warnings: list[str] = field(default_factory=list)
    calib: dict = field(default_factory=dict)

    # True when the flow curve is still high where the time axis ends, i.e. the
    # drawing reaches the right edge of the plot. Recorded rather than warned
    # about; it explains why such a chart's area can fall short of the printed
    # weight.
    reaches_axis_end: bool = False


# --- Detection ------------------------------------------------------------

def has_vector_curves(doc, probe_pages: int = 1) -> bool:
    """
    True when the document stores its curves as vector paths.

    Decides which extraction path the pipeline takes. A scanned or
    image-only PDF has no coloured strokes and falls through to CV.
    Requires a meaningful number of coloured segments so that a stray
    coloured logo on an otherwise scanned page does not trigger the
    vector path.
    """
    try:
        for pno in range(min(probe_pages, doc.page_count)):
            hits = 0
            for g in doc[pno].get_drawings():
                col = g.get("color")
                if col and (_is_blue(col) or _is_green(col)):
                    hits += 1
                    if hits >= 20:
                        return True
    except Exception:
        return False
    return False


# --- Calibration ----------------------------------------------------------

def _y_calibration(blocks, x0, x1, y0, y1):
    """
    Fit PDF-y -> data-value from the chart's own Y tick labels.

    The ticks "0".."9" are separate text blocks in a single left-edge column.
    Taking the glyph bounding-box centre and least-squares fitting against the
    printed values gives the mapping without assuming the 0..9 range, so a
    rescaled chart calibrates correctly too.

    Returns (slope, intercept, n_ticks, max_residual) or None.
    """
    cands = []
    for b in blocks:
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if not (x0 <= cx < x1 and y0 <= cy <= y1):
            continue
        t = b[4].strip()
        if _INT_RE.match(t):
            cands.append((float(t), (b[1] + b[3]) / 2, b[0]))

    if len(cands) < 3:
        return None

    # Keep only the leftmost column of numerals. Digits printed *inside* the
    # plot (the report prints a binary status row) would otherwise be read as
    # ticks and wreck the fit.
    xmin = min(c[2] for c in cands)
    ticks = [c for c in cands if c[2] - xmin < 6.0]
    if len(ticks) < 3:
        return None

    # Distinct values only; a repeated value carries no calibration info.
    seen: dict[float, float] = {}
    for val, cy, _ in ticks:
        seen.setdefault(val, cy)
    if len(seen) < 3:
        return None

    ys = np.array(list(seen.values()), dtype=float)
    vs = np.array(list(seen.keys()), dtype=float)
    slope, intercept = np.polyfit(ys, vs, 1)
    resid = float(np.abs(np.polyval([slope, intercept], ys) - vs).max())
    return float(slope), float(intercept), len(seen), resid


def _y_calibration_coloured(page, rgb, x0, x1, y0, y1, tol=0.08):
    """
    Fit PDF-y -> data-value from tick labels printed in a given colour.

    Some herds' reports carry extra traces on their own right-hand axes -
    conductivity in mS/cm, temperature in degrees C - and print each axis's
    numerals in the same colour as its curve. Selecting ticks by colour rather
    than by position is what makes those axes readable: two of them share the
    right edge, so a leftmost-column rule cannot separate them, while the
    colours are exact and stated in the legend.

    Returns (slope, intercept, n_ticks, max_residual) or None.
    """
    want = tuple(rgb)
    cands: dict[float, float] = {}
    try:
        info = page.get_text("dict")
    except Exception:
        return None

    for blk in info.get("blocks", []):
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                t = span.get("text", "").strip()
                if not _INT_RE.match(t):
                    continue
                c = span.get("color", 0)
                sr = ((c >> 16) & 255) / 255.0
                sg = ((c >> 8) & 255) / 255.0
                sb = (c & 255) / 255.0
                if (abs(sr - want[0]) > tol or abs(sg - want[1]) > tol
                        or abs(sb - want[2]) > tol):
                    continue
                bx = span["bbox"]
                cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
                if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                    continue
                cands.setdefault(float(t), cy)

    if len(cands) < 3:
        return None

    ys = np.array(list(cands.values()), dtype=float)
    vs = np.array(list(cands.keys()), dtype=float)
    slope, intercept = np.polyfit(ys, vs, 1)
    resid = float(np.abs(np.polyval([slope, intercept], ys) - vs).max())
    return float(slope), float(intercept), len(cands), resid


def _tick_value_range(blocks, x0, x1, y0, y1):
    """
    Lowest and highest printed Y tick value for this chart.

    Used to clamp extracted values to the range the chart actually shows,
    rather than to a hard-coded 0..9.
    """
    vals = []
    for b in blocks:
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if not (x0 <= cx < x1 and y0 <= cy <= y1):
            continue
        t = b[4].strip()
        if _INT_RE.match(t):
            vals.append((float(t), b[0]))
    if len(vals) < 3:
        return None, None
    xmin = min(v[1] for v in vals)
    col = [v[0] for v in vals if v[1] - xmin < 6.0]
    if len(col) < 3:
        return None, None
    return float(min(col)), float(max(col))


def _x_calibration(blocks, drawings, x0, x1, y0, y1):
    """
    Fit PDF-x -> time from the X tick label row, verified against the frame.

    The label row is the block of ascending integers lowest in the chart.
    Selecting by "lowest, ascending, >=5 labels" rejects data rows printed
    inside the plot area, which look similar but are neither ascending nor
    at the bottom.

    Returns (x_at_tmin, x_at_tmax, t_min, t_max) or None.
    """
    best = None
    for b in blocks:
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if not (x0 <= cx < x1 and y0 <= cy <= y1):
            continue
        if (b[2] - b[0]) < 100:
            continue
        labs = [s.strip() for s in b[4].split("\n") if s.strip()]
        if len(labs) < 5 or not all(l.isdigit() for l in labs):
            continue
        vals = [float(l) for l in labs]
        if not all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            continue
        if best is None or b[1] > best[0]:
            best = (b[1], b[0], b[2], vals)

    if best is None:
        return None

    _, bx0, bx1, vals = best
    # The label row spans slightly wider than the axis because the first and
    # last glyphs are centred on the end ticks. Pull in by half a glyph so the
    # span matches the axis rather than the text.
    half = (bx1 - bx0) / (len(vals) - 1) / 2.0
    return bx0 + half * 0.0, bx1 - half * 0.0, vals[0], vals[-1]


def _tick_x(drawings, x0, x1, y0, y1, baseline, hint_x0=None, hint_x1=None):
    """
    X extent from the axis tick marks — the most precise anchor available.

    Ticks are short black verticals hanging below the axis baseline at an
    exactly regular pitch (13.2pt in the real report, 21 ticks spanning
    0..10 min, i.e. one every half minute). Their first and last positions
    are the true ends of the data range, whereas gridlines can overrun by a
    fraction of a point and glyph boxes are positioned by text metrics.

    Returns (x_first, x_last, n_ticks) or None.
    """
    xs = []
    for g in drawings:
        col = g.get("color")
        if col is None or max(col) > 0.25:
            continue
        for it in g["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if abs(a.x - b.x) >= 0.3:
                continue
            length = abs(a.y - b.y)
            if not (0.4 < length < 7.0):
                continue
            top = min(a.y, b.y)
            # Must hang off the axis line, not float inside the plot.
            if not (x0 <= a.x <= x1 and baseline - 8 <= top <= baseline + 4):
                continue
            xs.append(round(a.x, 2))

    xs = sorted(set(xs))

    # Drop ticks belonging to the neighbouring chart. The widened geometry
    # window reaches past the column edge and catches the tail of the previous
    # chart's tick row; those ticks continue at the same pitch but are offset
    # by a smaller gap (11.0 vs 13.2 in the real report), so a pitch test
    # alone lets them through and shifts the origin — seen as a chart
    # starting at t = 0.844 instead of 0. The label row gives the chart's own
    # approximate span, which separates the two runs unambiguously.
    # The label row is centred on the end ticks, so it tracks them to within
    # about a glyph half-width. A tight fixed pad keeps the chart's own first
    # and last tick while excluding the neighbour's, which lies a full tick
    # pitch outside.
    if hint_x0 is not None and hint_x1 is not None:
        pad = 3.0
        xs = [x for x in xs if hint_x0 - pad <= x <= hint_x1 + pad]

    if len(xs) < 5:
        return None

    # Require a consistent pitch; an irregular set is not a tick row.
    diffs = np.diff(xs)
    med = float(np.median(diffs))
    if med <= 0 or float(np.max(np.abs(diffs - med))) > med * 0.25:
        return None

    return float(xs[0]), float(xs[-1]), len(xs)


def _frame_x(drawings, x0, x1, y0, y1):
    """
    Plot frame extent in x, taken from the grey gridlines.

    Gridlines are drawn edge to edge at a regular pitch, so their common
    start/end x is the plot's left and right boundary. Used as the fallback
    when tick marks cannot be read.
    """
    xs0, xs1 = [], []
    for g in drawings:
        col = g.get("color")
        if col is None:
            continue
        if not all(abs(c - 0.75) < 0.08 for c in col):
            continue
        for it in g["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            # Test the segment itself, not the path's bounding rect: one path
            # object can carry many gridlines, so its rect may spill past this
            # chart even when every segment we want lies inside.
            if abs(a.y - b.y) >= 0.25 or abs(a.x - b.x) <= 40:
                continue
            sx0, sx1 = min(a.x, b.x), max(a.x, b.x)
            if not (x0 <= sx0 and sx1 <= x1 + 1 and y0 <= a.y <= y1 + 4):
                continue
            xs0.append(sx0)
            xs1.append(sx1)
    if len(xs0) < 3:
        return None
    return float(np.median(xs0)), float(np.median(xs1))


# --- Curve geometry -------------------------------------------------------

def _collect_points(drawings, x0, x1, y0, y1, colour_test):
    """
    Gather every vertex of the matching-coloured paths in this chart.

    Curves arrive as many short subpaths, so points are pooled and then
    ordered by x. Both line ('l') and curve ('c') items are handled; for
    Béziers the on-curve endpoints are used, since control points can sit
    off the drawn stroke and would distort the trace.
    """
    pts: list[tuple[float, float]] = []

    def keep(px, py):
        # Filter per vertex rather than per path. A single path object may hold
        # segments from more than one chart, so rejecting on its bounding rect
        # would drop whole curves.
        return x0 <= px <= x1 + 1 and y0 <= py <= y1 + 2

    for g in drawings:
        col = g.get("color")
        if col is None or not colour_test(col):
            continue
        for it in g["items"]:
            if it[0] == "l":
                cand = [(it[1].x, it[1].y), (it[2].x, it[2].y)]
            elif it[0] == "c":
                cand = [(it[1].x, it[1].y), (it[4].x, it[4].y)]
            elif it[0] == "re":
                rr = it[1]
                cand = [(rr.x0, (rr.y0 + rr.y1) / 2), (rr.x1, (rr.y0 + rr.y1) / 2)]
            else:
                continue
            pts.extend(q for q in cand if keep(*q))
    return pts


def _points_to_series(pts, fx, fy, decimals=4,
                      t_lo=None, t_hi=None, v_lo=None, v_hi=None):
    """
    Turn a pooled vertex cloud into a clean (time, value) series.

    Duplicate x values are collapsed by median. The AMS pen sometimes
    back-tracks a fraction of a point between subpaths, which would otherwise
    produce a non-monotonic time axis that breaks downstream interpolation and
    draws as a visible zig-zag.
    """
    if not pts:
        return [], []

    arr = np.array(sorted(set(pts)), dtype=float)
    t = fx(arr[:, 0])
    v = fy(arr[:, 1])

    # Clamp to the printed axis range. The plotted stroke can end a fraction
    # of a point past the final tick (about 1.6 s on a 10-minute axis) and the
    # pen can sit a hair below the zero line; both are rendering artefacts of
    # a finite stroke width, not measurements, and would otherwise surface as
    # impossible values such as t = 10.027 or a negative flow rate.
    if t_lo is not None and t_hi is not None:
        t = np.clip(t, t_lo, t_hi)
    if v_lo is not None and v_hi is not None:
        v = np.clip(v, v_lo, v_hi)

    order = np.argsort(t, kind="stable")
    t, v = t[order], v[order]

    # Collapse duplicate/near-duplicate times.
    out_t, out_v = [], []
    i = 0
    n = len(t)
    while i < n:
        j = i + 1
        while j < n and (t[j] - t[i]) < 1e-6:
            j += 1
        out_t.append(float(t[i]))
        out_v.append(float(np.median(v[i:j])))
        i = j

    return (
        [round(x, decimals) for x in out_t],
        [round(x, decimals) for x in out_v],
    )


# --- Metadata -------------------------------------------------------------

def _parse_header(text: str) -> dict:
    """Pull the header fields out of a chart's text. Same formats as the CV path."""
    out: dict = {
        "animal_id": None, "date": None, "time": None, "time_full": None,
        "milk_kg": None, "gnr": None, "bimo": None, "le": None,
        "farm": None, "date_printed": None,
    }

    m = _ANIMAL_RE.search(text) or _ANIMAL_RE2.search(text)
    if m:
        out["animal_id"] = m.group(1)

    m = _DATA_DATE_RE.search(text) or _DATE_RE.search(text)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        if len(year) == 2:
            year = "20" + year
        out["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        # Keep the date exactly as printed too, so the CSV can be checked
        # against the report without mentally reformatting it.
        out["date_printed"] = f"{day.zfill(2)}.{month.zfill(2)}.{year}"

    m = _ORA_RE.search(text) or _TIME_RE.search(text)
    if m:
        hh, mm = m.group(1).zfill(2), m.group(2)
        out["time"] = f"{hh}{mm}"
        ss = m.group(3) if m.re is _ORA_RE and m.lastindex and m.lastindex >= 3 else None
        out["time_full"] = f"{hh}:{mm}:{ss}" if ss else f"{hh}:{mm}"

    m = _FARM_RE.search(text)
    if m:
        out["farm"] = m.group(1)

    m = _MILK_RE.search(text)
    if m:
        try:
            out["milk_kg"] = float(m.group(1).replace(",", "."))
        except ValueError:
            pass

    for key, rx in (("gnr", _GNR_RE), ("bimo", _BIMO_RE), ("le", _LE_RE)):
        m = rx.search(text)
        if m:
            out[key] = m.group(1)

    return out


# --- Page extraction ------------------------------------------------------

def extract_page(page, page_index: int) -> list[ChartData]:
    """
    Extract every chart on one vector PDF page.

    Charts are located by their "Animale:" header rather than by assuming a
    fixed grid, so a page holding fewer than 8 charts (a short final page)
    yields exactly the charts that are present instead of blank cells.
    """
    W, H = page.rect.width, page.rect.height
    blocks = page.get_text("blocks")
    drawings = page.get_drawings()

    heads = []
    for b in blocks:
        m = _ANIMAL_RE.search(b[4]) or _ANIMAL_RE2.search(b[4])
        if m:
            heads.append({"y": b[1], "x": b[0], "text": b[4]})

    if not heads:
        return []

    heads.sort(key=lambda e: (round(e["y"] / ROW_BUCKET_PT) * ROW_BUCKET_PT,
                              e["x"] > W / 2))
    row_tops = sorted({round(h["y"]) for h in heads})

    charts: list[ChartData] = []

    for ci, head in enumerate(heads):
        left = head["x"] < W / 2
        # Strict half-page window: used for the visual crop and for choosing
        # which text belongs to this chart.
        cx0, cx1 = (0.0, W / 2) if left else (W / 2, W)
        # Widened window: used for geometry, because the left chart's frame
        # and curves cross the midpoint by a few points.
        x0 = cx0 if left else cx0 - COLUMN_OVERLAP_PT
        x1 = cx1 + COLUMN_OVERLAP_PT if left else cx1
        y0 = head["y"] - HEADER_PAD_PT
        ri = row_tops.index(round(head["y"]))
        y1 = (row_tops[ri + 1] - HEADER_PAD_PT) if ri + 1 < len(row_tops) else H

        cd = ChartData(page=page_index, chart=ci,
                       clip=(cx0, y0, cx1, y1))

        # Metadata: the header block plus anything else inside this chart, so
        # GNR/BIMO/LE (separate blocks on the right) are picked up too.
        texts = [head["text"]]
        for b in blocks:
            bcx, bcy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if cx0 <= bcx < cx1 and y0 <= bcy <= y1 and b[4] is not head["text"]:
                texts.append(b[4])
        meta = _parse_header("\n".join(texts))
        cd.animal_id = meta["animal_id"]
        cd.date = meta["date"]
        cd.time = meta["time"]
        cd.time_full = meta["time_full"]
        cd.date_printed = meta["date_printed"]
        cd.farm = meta["farm"]
        cd.milk_kg = meta["milk_kg"]
        cd.gnr, cd.bimo, cd.le = meta["gnr"], meta["bimo"], meta["le"]

        # --- calibration ---
        # Tick text is read from the strict window (the neighbouring chart's
        # ticks must not leak in); frame geometry from the widened one.
        ycal = _y_calibration(blocks, cx0, cx1, y0, y1)
        xcal = _x_calibration(blocks, drawings, cx0, cx1, y0, y1)
        frame = _frame_x(drawings, x0, x1, y0, y1)

        if ycal is None or xcal is None:
            cd.warnings.append("Axis calibration failed: chart skipped")
            cd.source = "none"
            charts.append(cd)
            continue

        slope, intercept, n_ticks, resid = ycal
        lab_x0, lab_x1, t_min, t_max = xcal
        x_source = "labels"

        # The y where the value is 0 — the axis baseline the ticks hang from.
        baseline = (0.0 - intercept) / slope if slope else y1

        # Best anchor first: the tick marks. Then the gridline frame. The
        # label row is the last resort, since glyph boxes are positioned by
        # text metrics and overshoot the axis by a fraction of a point.
        ticks = _tick_x(drawings, x0, x1, y0, y1, baseline,
                        hint_x0=lab_x0, hint_x1=lab_x1)
        if ticks is not None and (ticks[1] - ticks[0]) > 40:
            lab_x0, lab_x1 = ticks[0], ticks[1]
            x_source = f"ticks({ticks[2]})"
        elif frame is not None and (frame[1] - frame[0]) > 40:
            lab_x0, lab_x1 = frame
            x_source = "gridlines"

        if resid > 0.05:
            cd.warnings.append(f"Y calibration residual high ({resid:.3f})")

        span = lab_x1 - lab_x0
        if span <= 0:
            cd.warnings.append("Degenerate X axis: chart skipped")
            cd.source = "none"
            charts.append(cd)
            continue

        def fx(xs, _a=lab_x0, _s=span, _t0=t_min, _t1=t_max):
            return _t0 + (xs - _a) / _s * (_t1 - _t0)

        def fy(ys, _m=slope, _c=intercept):
            return _m * ys + _c

        # Value bounds from this chart's own Y ticks, so a chart printed with
        # a different scale clamps and plots against its own range.
        v_lo_t, v_hi_t = _tick_value_range(blocks, cx0, cx1, y0, y1)

        cd.calib = {
            "y_slope": slope, "y_intercept": intercept,
            "y_ticks": n_ticks, "y_residual": round(resid, 5),
            "x_left": lab_x0, "x_right": lab_x1,
            "t_min": t_min, "t_max": t_max,
            "x_source": x_source,
        }

        # Where the plot box sits inside the crop, as fractions of the cropped
        # image. The UI needs these to draw the extracted curve on top of the
        # original at the right place; they differ between the left and right
        # columns and cannot be assumed, because the left chart's plot area
        # runs past its own clip edge.
        # Widen the crop so the whole plot box is inside it. The left chart's
        # axis runs a few points past the page midpoint, so a strict half-page
        # crop would cut off the end of its curve and the overlay would not
        # line up with the image.
        cx1 = max(cx1, lab_x1 + 4.0)
        cx0 = min(cx0, lab_x0 - 4.0)
        cd.clip = (cx0, y0, cx1, y1)

        cw = cx1 - cx0
        ch = y1 - y0
        if cw > 0 and ch > 0 and slope:
            v_bot = 0.0 if v_lo_t is None else v_lo_t
            v_top = 9.0 if v_hi_t is None else v_hi_t
            y_at_top = (v_top - intercept) / slope
            y_at_bot = (v_bot - intercept) / slope
            cd.calib["box"] = {
                "left":   round((lab_x0 - cx0) / cw, 6),
                "right":  round((lab_x1 - cx0) / cw, 6),
                "top":    round((y_at_top - y0) / ch, 6),
                "bottom": round((y_at_bot - y0) / ch, 6),
                "v_top":  v_top,
                "v_bottom": v_bot,
            }

        # --- curves ---
        # Clip to this chart's own calibrated plot frame rather than to the
        # column window. The left chart's curve tail runs past the page
        # midpoint, so a window-based cut would graft its ending onto the
        # right-hand chart (seen as a spurious t = -1.23 start).
        gx0 = lab_x0 - 1.0
        gx1 = lab_x1 + 1.0
        blue = _collect_points(drawings, gx0, gx1, y0, y1, _is_blue)
        cd.flusso_t, cd.flusso_v = _points_to_series(
            blue, fx, fy, t_lo=t_min, t_hi=t_max, v_lo=v_lo_t, v_hi=v_hi_t)

        if not settings.FLOW_ONLY:
            green = _collect_points(drawings, gx0, gx1, y0, y1, _is_green)
            cd.pressione_t, cd.pressione_v = _points_to_series(
                green, fx, fy, t_lo=t_min, t_hi=t_max,
                v_lo=v_lo_t, v_hi=v_hi_t)

        if not cd.flusso_t:
            cd.warnings.append("Flusso curve not present in vector layer")
        if not settings.FLOW_ONLY and not cd.pressione_t:
            cd.warnings.append("Pressione curve not present in vector layer")

        # Conductivity and temperature, where the report plots them. Each has
        # its own right-hand axis, so each gets its own fit from the tick
        # labels printed in its own colour - reusing the flow axis here would
        # report conductivity in kg/min, which is how a purple trace once
        # turned into 896% of a chart's milk.
        if settings.EXTRACT_EXTRA_TRACES and not settings.FLOW_ONLY:
            for colour, test, t_attr, v_attr in (
                    (settings.COLOUR_CONDUCTIVITY, _is_conduct,
                     "conduct_t", "conduct_v"),
                    (settings.COLOUR_TEMPERATURE, _is_temp,
                     "temp_t", "temp_v")):
                pts = _collect_points(drawings, gx0, gx1, y0, y1, test)
                if not pts:
                    continue
                cal = _y_calibration_coloured(page, colour, x0, x1, y0, y1)
                if not cal:
                    continue
                s2, i2, n2, r2 = cal
                fy2 = lambda y, _s=s2, _i=i2: _s * y + _i
                ts, vs = _points_to_series(
                    pts, fx, fy2, t_lo=t_min, t_hi=t_max,
                    v_lo=None, v_hi=None)
                setattr(cd, t_attr, ts)
                setattr(cd, v_attr, vs)
                cd.calib[t_attr.replace("_t", "_axis")] = {
                    "slope": s2, "intercept": i2,
                    "ticks": n2, "residual": round(r2, 5)}

        # A curve that reaches the right edge of the time axis while flow is
        # still high is recorded on the chart data, not raised as a warning:
        # these are normal complete sessions for this herd, and flagging them
        # was noise. The flag stays available for anything downstream that
        # wants to treat those charts differently.
        if cd.flusso_t and cd.flusso_t[-1] >= t_max - 1e-6:
            ft = np.asarray(cd.flusso_t, dtype=float)
            fv = np.asarray(cd.flusso_v, dtype=float)
            tail = fv[ft >= ft.max() - 1.0]
            cd.reaches_axis_end = bool(len(tail) and float(tail.mean()) > 0.10)

        charts.append(cd)

    return charts
