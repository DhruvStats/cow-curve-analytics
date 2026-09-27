"""
synthetic_generator.py

Generates synthetic AMS (Automated Milking System) chart pages that mimic
the real PDF format: 8 charts per page arranged in a 2-column x 4-row grid.

Each chart contains:
  - A header with animal ID, date, time, milk quantity, BIMO, LE, GNR fields
  - Two curves:
      * Flusso (blue)       — milk flow rate, kg/min,      Y-axis: 0–9
      * Pressione (green)   — absolute vacuum, 0.1 bar,    Y-axis: 0–9
  - X-axis: Durata mungitura, 0–10 minutes

Ground truth (exact data coordinates) is saved alongside each generated page
as a JSON file, enabling quantitative pipeline accuracy measurement.

Usage:
    python synthetic_generator.py --pages 3 --out ./output
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


# ---------------------------------------------------------------------------
# Constants that mirror the real PDF layout
# ---------------------------------------------------------------------------
FARM_NUMBER = "07010142"
CHARTS_PER_PAGE = 8
COLS = 2
ROWS = 4

X_MIN, X_MAX = 0.0, 10.0       # minutes
Y_MIN, Y_MAX = 0.0, 9.0        # kg/min  /  0.1 bar

# Figure size chosen so each chart cell is approximately the same pixel density
# as the real PDF when rasterised at 150 DPI.
FIG_W, FIG_H = 16.0, 22.0      # inches


# ---------------------------------------------------------------------------
# Curve generators
# ---------------------------------------------------------------------------

def generate_flusso(n_points: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """
    Milk flow rate curve: rises quickly, plateaus, then declines.
    Shape: smooth bell with a flat top, always starts and ends near 0.
    """
    t = np.linspace(X_MIN, X_MAX, n_points)

    peak_time = random.uniform(1.5, 3.5)
    peak_value = random.uniform(4.0, 8.5)
    rise_width = random.uniform(0.8, 1.8)
    fall_width = random.uniform(1.5, 3.5)

    rise = np.exp(-((t - peak_time) ** 2) / (2 * rise_width ** 2))
    fall = np.exp(-((t - (peak_time + fall_width)) ** 2) / (2 * fall_width ** 2))
    flow = peak_value * np.maximum(rise, fall * 0.6)

    # Force start/end to zero
    taper = np.minimum(t / 0.5, 1.0) * np.minimum((X_MAX - t) / 0.5, 1.0)
    flow = flow * taper

    # Add slight noise
    flow += np.random.normal(0, 0.05, n_points)
    flow = np.clip(flow, Y_MIN, Y_MAX)

    return t, flow


def generate_pressione(n_points: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """
    Absolute vacuum pressure curve: rises fast to ~8–9, stays high with
    minor fluctuations, then drops sharply at end of session.
    """
    t = np.linspace(X_MIN, X_MAX, n_points)

    plateau = random.uniform(7.5, 9.0)
    rise_end = random.uniform(0.3, 0.8)
    drop_start = random.uniform(8.5, 9.5)

    pressure = np.where(
        t < rise_end,
        plateau * (t / rise_end),
        np.where(
            t < drop_start,
            plateau,
            plateau * np.maximum(0, (X_MAX - t) / (X_MAX - drop_start))
        )
    )

    # Realistic ripple
    ripple = np.random.normal(0, 0.12, n_points)
    pressure = pressure + ripple
    pressure = np.clip(pressure, Y_MIN, Y_MAX)

    return t, pressure


# ---------------------------------------------------------------------------
# Single chart renderer
# ---------------------------------------------------------------------------

def render_chart(ax: plt.Axes, metadata: dict, flusso: tuple, pressione: tuple) -> None:
    """
    Draw one chart onto a Matplotlib Axes object, matching the real PDF style.
    Header text is placed via ax.annotate in axes-fraction coordinates so it
    always sits at a fixed relative position just above the top axis border,
    making OCR cropping consistent across all grid rows.
    """
    t_f, y_f = flusso
    t_p, y_p = pressione

    # --- Curves ---
    ax.plot(t_f, y_f, color="#1a6faf", linewidth=1.2, label="Flusso")

    ax_r = ax.twinx()
    ax_r.plot(t_p, y_p, color="#2ca02c", linewidth=1.2, label="Pressione assoluta")
    ax_r.set_ylim(Y_MIN, Y_MAX)
    ax_r.set_yticks(range(int(Y_MIN), int(Y_MAX) + 1))
    ax_r.tick_params(axis="y", labelsize=6)

    # --- Left axis ---
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1))
    ax.set_yticks(range(int(Y_MIN), int(Y_MAX) + 1))
    ax.tick_params(axis="both", labelsize=6)
    ax.set_xlabel("Durata mungitura (min)", fontsize=6)
    ax.set_ylabel("Flusso (kg/min)", fontsize=6, color="#1a6faf")
    ax_r.set_ylabel("Pressione assoluta (0.1 bar)", fontsize=6, color="#2ca02c")

    # --- Grid ---
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)

    # --- Header text ---
    # Use annotate with axes-fraction coords so the text always lands at a
    # fixed distance above the top spine, regardless of which grid row this
    # chart occupies. This makes the OCR crop position predictable.
    header = (
        f"Az. {FARM_NUMBER}   "
        f"ID: {metadata['animal_id']}   "
        f"{metadata['date']}  {metadata['time']}   "
        f"Latte: {metadata['milk_kg']:.1f} kg   "
        f"BIMO: {metadata['bimo']}   "
        f"LE: {metadata['le']}   "
        f"GNR: {metadata['gnr']}"
    )
    ax.annotate(
        header,
        xy=(0, 1), xycoords="axes fraction",
        xytext=(0, 4), textcoords="offset points",
        fontsize=5.5, family="monospace",
        va="bottom", ha="left",
    )


# ---------------------------------------------------------------------------
# Page generator
# ---------------------------------------------------------------------------

def generate_page(page_index: int, base_date: datetime) -> dict:
    """
    Generate one page (8 charts) and return a dict with:
      - 'fig': the Matplotlib Figure
      - 'ground_truth': list of 8 ground-truth dicts
    """
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    fig.suptitle(
        f"Az. {FARM_NUMBER} — Pagina {page_index + 1}",
        fontsize=9, y=0.995
    )

    gs = gridspec.GridSpec(
        ROWS, COLS,
        figure=fig,
        hspace=0.55,
        wspace=0.35,
        left=0.07, right=0.93,
        top=0.97, bottom=0.03
    )

    ground_truth = []

    for i in range(CHARTS_PER_PAGE):
        row, col = divmod(i, COLS)
        ax = fig.add_subplot(gs[row, col])

        # --- Metadata ---
        animal_id = random.randint(100, 9999)
        session_date = base_date + timedelta(minutes=random.randint(0, 1440))
        metadata = {
            "animal_id": animal_id,
            "date": session_date.strftime("%d/%m/%Y"),
            "time": session_date.strftime("%H:%M"),
            "milk_kg": round(random.uniform(2.0, 18.0), 1),
            "bimo": random.choice(["0", "1"]),
            "le": random.choice(["0", "1"]),
            "gnr": str(random.randint(1, 5)),
            "farm": FARM_NUMBER,
            "page": page_index,
            "chart_index": i,
        }

        # --- Curves ---
        flusso = generate_flusso()
        pressione = generate_pressione()

        render_chart(ax, metadata, flusso, pressione)

        ground_truth.append({
            "metadata": metadata,
            "flusso": {
                "time_min": flusso[0].tolist(),
                "value": flusso[1].tolist(),
            },
            "pressione": {
                "time_min": pressione[0].tolist(),
                "value": pressione[1].tolist(),
            },
        })

    return {"fig": fig, "ground_truth": ground_truth}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic AMS chart pages.")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to generate")
    parser.add_argument("--out", type=str, default="./output", help="Output directory")
    parser.add_argument("--dpi", type=int, default=150, help="Rasterisation DPI")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    os.makedirs(args.out, exist_ok=True)

    base_date = datetime(2024, 3, 7, 5, 0)

    all_ground_truth = []

    for p in range(args.pages):
        print(f"Generating page {p + 1}/{args.pages}...")
        result = generate_page(p, base_date + timedelta(days=p))

        # Save PNG
        img_path = os.path.join(args.out, f"page_{p + 1:03d}.png")
        result["fig"].savefig(img_path, dpi=args.dpi, bbox_inches="tight")
        plt.close(result["fig"])
        print(f"  Saved: {img_path}")

        all_ground_truth.append(result["ground_truth"])

    # Save ground truth JSON
    gt_path = os.path.join(args.out, "ground_truth.json")
    with open(gt_path, "w") as f:
        json.dump(all_ground_truth, f, indent=2)
    print(f"\nGround truth saved: {gt_path}")
    print("Done.")


if __name__ == "__main__":
    main()
