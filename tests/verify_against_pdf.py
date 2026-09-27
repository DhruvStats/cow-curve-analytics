"""
verify_against_pdf.py

Ground-truth-free accuracy check: measure the extracted CSVs against the
*printed pixels* of the PDF they came from.

The synthetic suite (evaluate_accuracy.py) can only score synthetic files,
because it needs a ground-truth JSON. This script needs nothing but the real
report: it re-renders each chart at high resolution, finds the drawn curve by
colour, converts those pixels to data units using the same axis calibration
the pipeline derived, and compares against the CSV.

That makes it a genuine independent check. The pipeline reads the PDF's vector
layer; this reads the rasterised picture. Agreement between two different
representations is real evidence, not a tautology.

A second, fully independent check is also reported: the integral of each flow
curve against the milk quantity printed in that chart's own header, a number
the AMS measured separately and the extraction never looks at.

Usage:
    python verify_against_pdf.py --pdf ../sample_input/sample_report.pdf
    python verify_against_pdf.py --pdf report.pdf --csv ./csv_out --dpi 300
"""

import argparse
import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))

import fitz  # noqa: E402
import vector_extract as ve  # noqa: E402
from pipeline import run_pipeline  # noqa: E402

# Sampling resolution for the pixel probe. Higher than the pipeline's own
# raster DPI so a stroke is several pixels wide and its centre is well defined.
VERIFY_DPI = 300

# Colour tests on the rendered image (RGB 0..255).
def _is_blue_px(r, g, b):
    return b > 150 and r < 90 and g < 90


def _is_green_px(r, g, b):
    return g > 90 and r < 90 and b < 90


def _curve_from_pixels(img, box, t_grid, colour_test, v_top, v_bottom):
    """
    Read one curve's value at each requested time straight off the image.

    Scans the column inside the plot box and takes the *lowest* run of matching
    pixels. Both curves share their colour with the chart's own axis labels,
    which sit above the plot; taking the lowest run keeps the probe on the
    curve instead of averaging it with the text.
    """
    h, w = img.shape[:2]
    y_top = int(box["top"] * h)
    y_bot = int(box["bottom"] * h)
    out = []

    for t in t_grid:
        frac = (t - box["t_min"]) / (box["t_max"] - box["t_min"])
        x = int(round((box["left"] + frac * (box["right"] - box["left"])) * w))
        if not (0 <= x < w):
            out.append(np.nan)
            continue

        ys = [y for y in range(max(0, y_top), min(h, y_bot + 1))
              if colour_test(*img[y, x][:3])]
        if not ys:
            out.append(np.nan)
            continue

        runs, cur = [], [ys[0]]
        for prev, cy in zip(ys, ys[1:]):
            if cy - prev <= 2:
                cur.append(cy)
            else:
                runs.append(cur)
                cur = [cy]
        runs.append(cur)

        y_mid = float(np.mean(runs[-1]))
        val = (box["bottom"] - y_mid / h) / (box["bottom"] - box["top"])
        out.append(v_bottom + val * (v_top - v_bottom))

    return np.array(out, dtype=float)


def _interp_csv(df, curve_name, t_grid):
    sub = df[df["curve"] == curve_name]
    if len(sub) < 2:
        return np.full(len(t_grid), np.nan)
    return np.interp(t_grid, sub["time_min"].values, sub["value"].values,
                     left=np.nan, right=np.nan)


def verify(pdf_path: str, csv_dir: str | None, dpi: int) -> int:
    tmp_dir = None
    if csv_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="cd_verify_")
        csv_dir = tmp_dir
        print(f"No --csv given; running the pipeline into {csv_dir}\n")
        run_pipeline(pdf_path, csv_dir)

    doc = fitz.open(pdf_path)
    rows = []

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        charts = ve.extract_page(page, page_idx)

        for cd in charts:
            box = dict(cd.calib.get("box") or {})
            if not box or not cd.clip:
                continue
            box["t_min"] = cd.calib["t_min"]
            box["t_max"] = cd.calib["t_max"]

            csv_name = f"animal_{cd.animal_id}_{cd.date}"
            path = os.path.join(csv_dir, csv_name + ".csv")
            if not os.path.exists(path) and cd.time:
                path = os.path.join(csv_dir, f"{csv_name}_{cd.time}.csv")
            if not os.path.exists(path):
                print(f"  [MISSING CSV] {csv_name}")
                continue

            df = pd.read_csv(path)

            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0),
                                  clip=fitz.Rect(*cd.clip),
                                  colorspace=fitz.csRGB)
            img = np.frombuffer(pix.samples, dtype=np.uint8) \
                    .reshape(pix.h, pix.w, 3)

            v_top = box.get("v_top", 9.0)
            v_bot = box.get("v_bottom", 0.0)

            for curve, test, label in (
                ("Flusso_kg_min", _is_blue_px, "flusso"),
                ("Pressione_assoluta_0.1bar", _is_green_px, "pressione"),
            ):
                sub = df[df["curve"] == curve]
                if len(sub) < 2:
                    continue
                lo, hi = sub["time_min"].min(), sub["time_min"].max()
                # Stay clear of the very ends, where the stroke is clipped by
                # the axis frame and a pixel probe is not meaningful.
                span = hi - lo
                grid = np.linspace(lo + span * 0.05, hi - span * 0.05, 60)

                from_img = _curve_from_pixels(img, box, grid, test, v_top, v_bot)
                from_csv = _interp_csv(df, curve, grid)

                ok = ~(np.isnan(from_img) | np.isnan(from_csv))
                if ok.sum() < 5:
                    continue
                diff = np.abs(from_img[ok] - from_csv[ok])
                rows.append({
                    "animal": cd.animal_id,
                    "curve": label,
                    "n": int(ok.sum()),
                    "mean": float(diff.mean()),
                    "median": float(np.median(diff)),
                    "max": float(diff.max()),
                    "yield_ratio": (
                        float(np.trapezoid(sub["value"], sub["time_min"]) / cd.milk_kg)
                        if label == "flusso" and cd.milk_kg else None
                    ),
                })

    doc.close()

    if not rows:
        print("Nothing to verify.")
        return 1

    res = pd.DataFrame(rows)
    print(f"\n{'=' * 62}")
    print("  Pixel verification: extracted CSV vs. the printed chart")
    print(f"{'=' * 62}")
    for label in ("flusso", "pressione"):
        sub = res[res["curve"] == label]
        if sub.empty:
            continue
        unit = "kg/min" if label == "flusso" else "x0.1 bar"
        print(f"\n  {label}  ({len(sub)} charts, {int(sub['n'].sum())} probe points)")
        print(f"    mean abs error     : {sub['mean'].mean():.4f}  {unit}")
        print(f"    median abs error   : {sub['median'].median():.4f}  {unit}")
        print(f"    worst chart (max)  : {sub['max'].max():.4f}  {unit}")

    ratios = res[res["yield_ratio"].notna()]["yield_ratio"]
    if len(ratios):
        print(f"\n  Independent yield cross-check "
              f"(integral of flow vs printed kg)")
        print(f"    median             : {ratios.median() * 100:.1f} %")
        print(f"    charts within 10%  : "
              f"{int(((ratios - 1).abs() <= 0.10).sum())} / {len(ratios)}")
        print("    (values below 100% are usually sessions the report's "
              "10-minute\n     axis cut off, not extraction error)")
    print(f"{'=' * 62}\n")

    if tmp_dir:
        print(f"CSVs left in {tmp_dir}")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Verify extracted CSVs against the printed PDF pixels")
    ap.add_argument("--pdf", required=True, help="Source PDF")
    ap.add_argument("--csv", default=None,
                    help="Directory of already-extracted CSVs "
                         "(default: run the pipeline into a temp dir)")
    ap.add_argument("--dpi", type=int, default=VERIFY_DPI,
                    help="Rendering DPI for the pixel probe")
    args = ap.parse_args()

    if not os.path.exists(args.pdf):
        print(f"Not found: {args.pdf}")
        sys.exit(1)
    sys.exit(verify(args.pdf, args.csv, args.dpi))


if __name__ == "__main__":
    main()
