"""
make_demos.py — build demo AMS reports with known ground truth.

Every demo is drawn to the same spec as the real report: A4, 2x4 grid, the same
blue (0,0,1 at 1.44pt) and green (0,0.627,0.039 at 0.36pt) strokes, the same
grey grid, the same Italian header, the same 0-10 min / 0-9 unit axes and the
same 0,20 threshold line.

Only the numbers change: animal ids, milk weights, and the shape of the curves.
Because the generator knows exactly what it drew, each PDF ships with a JSON of
true values, so the extractor's output can be scored rather than eyeballed.

The point is to test the extractor on charts it has never seen, including ones
built to be awkward: very short sessions, very low flow, spiky traces and
sessions that run off the right-hand edge.

Usage:
    python make_demos.py --out <folder>
"""

import argparse
import json
import math
import os
import random

import fitz

# --- Geometry copied from the real report, in PDF points --------------------

PAGE_W, PAGE_H = 595.32, 841.92
COL_X = [41.76, 316.92]          # plot left edge, per column
PLOT_W = 264.12                  # 41.76 -> 305.88
ROW_TOP = [14.8, 213.8, 412.8, 611.7]   # header baseline per row
PLOT_TOP_OFF = 20.6              # header to plot top
PLOT_H = 157.20                  # value 9 down to value 0, as printed

T_MIN, T_MAX = 0.0, 10.0
V_MIN, V_MAX = 0.0, 9.0

BLUE = (0.0, 0.0, 1.0)
GREEN = (0.0, 0.6275, 0.0392)
GREY = (0.7529, 0.7529, 0.7529)
BLACK = (0.0, 0.0, 0.0)

FLOW_PITCH = 0.0454              # minutes between flow samples (2.7 s)
PRESS_PITCH = 0.1863             # minutes between pressure samples (11 s)
THRESHOLD = 0.20                 # the printed "0,20" line

FARM = "07010142"


def x_of(t, col):
    return COL_X[col] + (t - T_MIN) / (T_MAX - T_MIN) * PLOT_W


def y_of(v, row):
    top = ROW_TOP[row] + PLOT_TOP_OFF
    return top + (V_MAX - v) / (V_MAX - V_MIN) * PLOT_H


# --- Curve shapes -----------------------------------------------------------

def flow_curve(kind, rng):
    """Return (times, values) for one milking session."""
    if kind == "normal":
        peak, rise, hold, fall = rng.uniform(1.4, 2.6), 0.5, rng.uniform(2.0, 4.0), 1.2
    elif kind == "short":
        peak, rise, hold, fall = rng.uniform(1.0, 2.0), 0.3, rng.uniform(0.6, 1.4), 0.6
    elif kind == "low":
        peak, rise, hold, fall = rng.uniform(0.4, 0.8), 0.6, rng.uniform(3.0, 5.0), 1.5
    elif kind == "long":
        peak, rise, hold, fall = rng.uniform(1.2, 2.0), 0.6, rng.uniform(6.0, 8.0), 1.5
    elif kind == "truncated":
        # still flowing when the axis runs out
        peak, rise, hold, fall = rng.uniform(0.7, 1.1), 0.8, 12.0, 2.0
    else:
        peak, rise, hold, fall = 1.5, 0.5, 3.0, 1.0

    end = min(rise + hold + fall, T_MAX)
    n = int(end / FLOW_PITCH) + 1
    ts, vs = [], []
    for i in range(n):
        t = round(i * FLOW_PITCH, 4)
        if t > T_MAX:
            break
        if t < rise:
            v = peak * (t / rise)
        elif t < rise + hold:
            # gentle decline with a little texture, as a real trace has
            frac = (t - rise) / hold
            v = peak * (1.0 - 0.35 * frac) + 0.05 * math.sin(t * 7.0)
        else:
            frac = (t - rise - hold) / max(fall, 1e-6)
            v = peak * 0.65 * max(0.0, 1.0 - frac)
        v += rng.uniform(-0.02, 0.02)
        ts.append(t)
        vs.append(max(0.0, min(V_MAX, round(v, 4))))
    return ts, vs


def pressure_curve(flow_end, rng):
    """Vacuum: rises fast, holds near 4.5, drops when the cluster comes off."""
    n = int(min(flow_end + 0.2, T_MAX) / PRESS_PITCH) + 1
    plateau = rng.uniform(4.3, 4.6)
    ts, vs = [], []
    for i in range(n):
        t = round(i * PRESS_PITCH, 4)
        if t > T_MAX:
            break
        if t < 0.25:
            v = plateau * (t / 0.25)
        else:
            v = plateau + rng.uniform(-0.12, 0.12)
        ts.append(t)
        vs.append(max(0.0, min(V_MAX, round(v, 4))))
    return ts, vs


def integrate(ts, vs):
    return sum((vs[i] + vs[i - 1]) / 2 * (ts[i] - ts[i - 1])
               for i in range(1, len(ts)))


# --- Drawing ----------------------------------------------------------------

def draw_chart(page, row, col, meta, flow, press):
    left, right = COL_X[col], COL_X[col] + PLOT_W
    top = ROW_TOP[row] + PLOT_TOP_OFF
    bottom = top + PLOT_H

    # grid: 19 verticals (every 0.5 min), 19 horizontals (every 0.5 units)
    for i in range(19):
        x = left + i * (PLOT_W / 18)
        page.draw_line(fitz.Point(x, top), fitz.Point(x, bottom),
                       color=GREY, width=0.375)
    for i in range(19):
        y = top + i * (PLOT_H / 18)
        page.draw_line(fitz.Point(left, y), fitz.Point(right, y),
                       color=GREY, width=0.375)

    # frame and tick marks
    page.draw_rect(fitz.Rect(left, top, right, bottom), color=BLACK, width=0.375)
    for i in range(21):
        x = left + i * (PLOT_W / 20)
        page.draw_line(fitz.Point(x, bottom), fitz.Point(x, bottom + 2.2),
                       color=BLACK, width=0.375)

    # the printed end-of-milking threshold
    ty = y_of(THRESHOLD, row)
    page.draw_line(fitz.Point(left, ty), fitz.Point(right, ty),
                   color=BLACK, width=0.375, dashes="[2 2] 0")
    # The real report prints a tiny "0,20" caption on this line. It is left
    # off here: at this size PyMuPDF groups it with the nearby "0" tick label
    # into a single text block, which would stop the calibrator reading that
    # tick. The extractor never reads the caption, only the dashed line and
    # the tick numbers, so omitting it changes nothing being tested.

    # y tick labels 0..9 - these are what the extractor calibrates from
    for v in range(10):
        page.insert_text(fitz.Point(left - 5.2, y_of(v, row) + 2.4), str(v),
                         fontname="helv", fontsize=6.7, color=BLUE)
    # x tick labels
    for t in range(11):
        page.insert_text(fitz.Point(x_of(t, col) - 1.6, bottom + 7.6), str(t),
                         fontname="helv", fontsize=5.6, color=BLACK)

    # axis titles
    page.insert_text(fitz.Point(left - 3.8, ROW_TOP[row] + 13.8),
                     "Flusso[kg/min]", fontname="helv", fontsize=5.6, color=BLUE)
    page.insert_text(fitz.Point(left + 1.0, ROW_TOP[row] + 19.8),
                     "pressione assoluta [0.1bar]", fontname="helv",
                     fontsize=4.4, color=GREEN)
    page.insert_text(fitz.Point(right - 46, bottom + 12.4),
                     "Durata mungitura [min]", fontname="helv",
                     fontsize=5.6, color=BLACK)

    # header, in the exact wording the parser looks for
    page.insert_text(fitz.Point(left + 48, ROW_TOP[row] + 5.2),
                     "Numero Azienda %s    Animale: %s         .............." %
                     (FARM, meta["animal_id"]),
                     fontname="helv", fontsize=6.7, color=BLACK)
    page.insert_text(fitz.Point(left + 48, ROW_TOP[row] + 13.0),
                     "Quantità di latte: %.2f kg    Data: %s   Ora: %s" %
                     (meta["milk_kg"], meta["date_printed"], meta["time"]),
                     fontname="hebo", fontsize=6.7, color=BLACK)

    # right-hand block
    for i, line in enumerate(("GNR: %s" % meta["gnr"],
                              "BIMO = %s" % meta["bimo"],
                              "LE     = %s" % meta["le"])):
        page.insert_text(fitz.Point(right - 45, top + 24 + i * 10),
                         line, fontname="helv", fontsize=6.7, color=BLACK)

    # the curves themselves
    for (ts, vs), colour, width in ((press, GREEN, 0.36), (flow, BLUE, 1.44)):
        for i in range(1, len(ts)):
            page.draw_line(fitz.Point(x_of(ts[i - 1], col), y_of(vs[i - 1], row)),
                           fitz.Point(x_of(ts[i], col), y_of(vs[i], row)),
                           color=colour, width=width)


def build(path, spec, seed):
    rng = random.Random(seed)
    doc = fitz.open()
    truth = []

    for pno, page_spec in enumerate(spec):
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        for idx, kind in enumerate(page_spec):
            row, col = divmod(idx, 2)
            flow = flow_curve(kind, rng)
            press = pressure_curve(flow[0][-1] if flow[0] else 1.0, rng)
            milk = round(integrate(*flow), 2)

            meta = {
                "animal_id": str(rng.randint(100, 9999)),
                "milk_kg": milk,
                "date_printed": "12.05.2025",
                "date": "2025-05-12",
                "time": "%02d:%02d:%02d" % (3 + idx // 2, rng.randint(0, 59),
                                            rng.randint(0, 59)),
                "gnr": "0%05d" % rng.randint(10000, 99999),
                "bimo": str(rng.randint(0, 1)),
                "le": str(rng.randint(0, 1)),
            }
            draw_chart(page, row, col, meta, flow, press)

            truth.append({
                "page": pno, "chart": idx, "kind": kind,
                "animal_id": meta["animal_id"],
                "milk_kg": milk,
                "date": meta["date"],
                "time": meta["time"],
                "gnr": meta["gnr"], "bimo": meta["bimo"], "le": meta["le"],
                "peak_flow": round(max(flow[1]), 4),
                "flow_end": round(flow[0][-1], 4),
                "flow_points": len(flow[0]),
                "flow_t": flow[0], "flow_v": flow[1],
            })

    doc.save(path, garbage=3, deflate=True)
    doc.close()
    return truth


SCENARIOS = {
    "demo_1_normal": ([["normal"] * 8], 11),
    "demo_2_mixed": ([["normal", "short", "low", "long",
                       "normal", "short", "long", "low"]], 22),
    "demo_3_hard": ([["low", "low", "short", "short",
                      "truncated", "truncated", "low", "short"]], 33),
    "demo_4_twopage": ([["normal", "long", "short", "low",
                         "normal", "normal", "long", "short"],
                        ["low", "normal", "truncated", "short",
                         "long", "low", "normal", "normal"]], 44),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo_reports")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    index = {}
    for name, (spec, seed) in SCENARIOS.items():
        pdf = os.path.join(args.out, name + ".pdf")
        truth = build(pdf, spec, seed)
        index[name] = truth
        with open(os.path.join(args.out, name + "_truth.json"), "w") as fh:
            json.dump(truth, fh, indent=1)
        print("%-18s %d page(s), %2d charts, %.2f kg total"
              % (name, len(spec), len(truth), sum(t["milk_kg"] for t in truth)))

    with open(os.path.join(args.out, "all_truth.json"), "w") as fh:
        json.dump(index, fh, indent=1)
    print("\nwritten to", args.out)


if __name__ == "__main__":
    main()
