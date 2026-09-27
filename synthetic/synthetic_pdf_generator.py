"""
synthetic_pdf_generator.py

Generates synthetic AMS milking-session PDFs that are structurally identical
to the real company PDF:
  - A4 portrait, 2 columns × 4 rows = 8 charts per page
  - Embedded text headers (Numero Azienda, Animale, Data, Ora, etc.)
  - Vector curves: blue = Flusso, green = Pressione assoluta
  - Right-side metadata block (GNR, BIMO, LE)
  - Axis frames, tick marks, grid lines

Because Matplotlib's PDF backend embeds fonts as real text, PyMuPDF's
native text extraction works on the output — no OCR needed.

Ground truth is saved as JSON alongside each PDF.

Usage:
    python synthetic_pdf_generator.py --scenario all --out ./pdf_output
    python synthetic_pdf_generator.py --scenario baseline --out ./pdf_output
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("pdf")          # PDF backend — vector output, embedded text
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


# ---------------------------------------------------------------------------
# Constants matching real PDF layout
# ---------------------------------------------------------------------------
FARM_NUMBER   = "07010142"
GRID_ROWS     = 4
GRID_COLS     = 2
CHARTS_PER_PAGE = GRID_ROWS * GRID_COLS

# A4 portrait in inches at 72 DPI
FIG_W, FIG_H  = 595 / 72, 842 / 72   # ≈ 8.26 × 11.69 inches

X_MIN, X_MAX  = 0.0, 10.0
Y_MIN, Y_MAX  = 0.0, 9.0


# ---------------------------------------------------------------------------
# Curve generators
# ---------------------------------------------------------------------------

def generate_flusso(
    n_points: int = 300,
    peak_value: float | None = None,
    session_duration: float | None = None,
    flat: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Blue curve — milk flow rate (kg/min).
    Modes:
      normal  : smooth bell with flat top, starts/ends at 0
      flat    : nearly zero throughout (very short session / dry cow)
    """
    t = np.linspace(X_MIN, X_MAX, n_points)

    if flat:
        flow = np.random.uniform(0, 0.3, n_points)
        flow = np.clip(flow, Y_MIN, Y_MAX)
        return t, flow

    peak_t   = random.uniform(1.5, 3.5)
    peak_v   = peak_value or random.uniform(3.0, 8.5)
    dur      = session_duration or random.uniform(5.0, 9.5)
    rise_w   = random.uniform(0.8, 1.8)
    fall_w   = random.uniform(1.5, 3.0)

    rise = np.exp(-((t - peak_t) ** 2) / (2 * rise_w ** 2))
    fall = np.exp(-((t - (peak_t + fall_w)) ** 2) / (2 * fall_w ** 2))
    flow = peak_v * np.maximum(rise, fall * 0.6)

    # Taper to zero at start and after session_duration
    taper_start = np.minimum(t / 0.4, 1.0)
    taper_end   = np.minimum(np.maximum(dur - t, 0) / 0.4, 1.0)
    flow = flow * taper_start * taper_end

    flow += np.random.normal(0, 0.04, n_points)
    flow  = np.clip(flow, Y_MIN, Y_MAX)
    return t, flow


def generate_pressione(
    n_points: int = 300,
    plateau: float | None = None,
    session_duration: float | None = None,
    flat: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Green curve — absolute vacuum pressure (0.1 bar).
    Modes:
      normal : rises fast, holds plateau, drops sharply at end
      flat   : stays low (unit off / no vacuum)
    """
    t = np.linspace(X_MIN, X_MAX, n_points)

    if flat:
        pressure = np.random.uniform(0, 0.5, n_points)
        pressure = np.clip(pressure, Y_MIN, Y_MAX)
        return t, pressure

    plat     = plateau or random.uniform(7.0, 9.0)
    rise_end = random.uniform(0.3, 0.8)
    dur      = session_duration or random.uniform(5.0, 9.5)
    drop_len = random.uniform(0.3, 0.8)
    drop_start = dur - drop_len

    pressure = np.where(
        t < rise_end,
        plat * (t / rise_end),
        np.where(
            t < drop_start,
            plat,
            plat * np.maximum(0.0, (dur - t) / drop_len),
        ),
    )

    pressure += np.random.normal(0, 0.10, n_points)
    pressure  = np.clip(pressure, Y_MIN, Y_MAX)
    return t, pressure


# ---------------------------------------------------------------------------
# Single chart renderer
# ---------------------------------------------------------------------------

def render_chart(
    ax: plt.Axes,
    metadata: dict,
    flusso: tuple[np.ndarray, np.ndarray],
    pressione: tuple[np.ndarray, np.ndarray],
) -> None:
    """
    Render one chart onto `ax`, mimicking the real PDF style.
    Text is placed via ax.annotate / ax.text so Matplotlib's PDF backend
    embeds it as real searchable text — matching what PyMuPDF reads from
    the real company PDF.
    """
    t_f, y_f = flusso
    t_p, y_p = pressione

    # --- Twin axes ---
    ax_r = ax.twinx()

    # --- Curves ---
    ax.plot(t_f, y_f,   color="#1a6faf", linewidth=0.9, zorder=3)
    ax_r.plot(t_p, y_p, color="#2ca02c", linewidth=0.9, zorder=3)

    # --- Axis limits & ticks ---
    for a in (ax, ax_r):
        a.set_ylim(Y_MIN, Y_MAX)
        a.set_yticks(range(int(Y_MIN), int(Y_MAX) + 1))
        a.tick_params(axis="y", labelsize=5)

    ax.set_xlim(X_MIN, X_MAX)
    ax.set_xticks(range(int(X_MIN), int(X_MAX) + 1))
    ax.tick_params(axis="x", labelsize=5)

    # --- Axis labels ---
    ax.set_xlabel("Durata mungitura", fontsize=5, labelpad=1)
    ax.set_ylabel("Flusso[kg/min]",    fontsize=5, color="#1a6faf", labelpad=1)
    ax_r.set_ylabel("pressione assoluta [0.1bar]", fontsize=5,
                    color="#2ca02c", labelpad=1)

    # --- Grid ---
    ax.grid(True, linestyle="--", linewidth=0.3, alpha=0.5, zorder=0)

    # --- Header text (embedded, matches real PDF format exactly) ---
    # Line 1: farm + animal
    line1 = (
        f"Numero Azienda {FARM_NUMBER}    "
        f"Animale: {metadata['animal_id']}         .............."
    )
    # Line 2: milk quantity + date + time
    line2 = (
        f"Quantità di latte: {metadata['milk_kg']:.2f} kg    "
        f"Data: {metadata['date_it']}   "
        f"Ora: {metadata['time_full']}"
    )
    ax.annotate(line1, xy=(0, 1), xycoords="axes fraction",
                xytext=(0, 12), textcoords="offset points",
                fontsize=5, family="monospace", va="bottom", ha="left",
                annotation_clip=False)
    ax.annotate(line2, xy=(0, 1), xycoords="axes fraction",
                xytext=(0,  3), textcoords="offset points",
                fontsize=5, family="monospace", va="bottom", ha="left",
                annotation_clip=False)

    # --- Right-side metadata block (GNR, BIMO, LE) ---
    right_text = (
        f"GNR: {metadata['gnr']}\n"
        f"BIMO = {metadata['bimo']}\n"
        f"LE   = {metadata['le']}"
    )
    ax.text(0.98, 0.80, right_text,
            transform=ax.transAxes,
            fontsize=5, family="monospace",
            va="top", ha="right",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=1))


# ---------------------------------------------------------------------------
# Metadata factory
# ---------------------------------------------------------------------------

def make_metadata(
    base_date: datetime,
    animal_id: int | None = None,
    force_duplicate: bool = False,
) -> dict:
    """Generate one chart's metadata dict."""
    aid  = animal_id or random.randint(100, 9999)
    dt   = base_date + timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return {
        "animal_id":  str(aid),
        "date_it":    dt.strftime("%d.%m.%Y"),     # Italian format as in real PDF
        "date_iso":   dt.strftime("%Y-%m-%d"),
        "time_full":  dt.strftime("%H:%M:%S"),
        "time_hhmm":  dt.strftime("%H%M"),
        "milk_kg":    round(random.uniform(1.5, 18.0), 2),
        "bimo":       str(random.randint(0, 1)),
        "le":         str(random.randint(0, 1)),
        "gnr":        f"0{random.randint(10000, 99999)}",
        "farm":       FARM_NUMBER,
    }


# ---------------------------------------------------------------------------
# Page builder
# ---------------------------------------------------------------------------

def build_page(
    fig: plt.Figure,
    gs: gridspec.GridSpec,
    page_index: int,
    base_date: datetime,
    scenario: str,
) -> list[dict]:
    """
    Fill one page (8 charts) of the figure.
    Returns list of 8 ground-truth dicts.
    """
    ground_truth = []

    for i in range(CHARTS_PER_PAGE):
        row, col = divmod(i, GRID_COLS)
        ax = fig.add_subplot(gs[row, col])

        # --- Scenario-specific curve config ---
        flat_f = flat_p = False
        dup_animal = None

        if scenario == "edge":
            if i in (2, 3):           # very short sessions
                session_dur = random.uniform(1.0, 3.0)
                peak_val    = random.uniform(0.5, 2.0)
            elif i in (4, 5):         # flat / dry cow
                flat_f = flat_p = True
                session_dur = peak_val = None
            elif i in (6, 7):         # duplicate animal same date
                dup_animal = 948
                session_dur = peak_val = None
            else:
                session_dur = peak_val = None
        else:
            session_dur = peak_val = None

        meta = make_metadata(base_date, animal_id=dup_animal)
        flusso    = generate_flusso(flat=flat_f,
                                    peak_value=peak_val,
                                    session_duration=session_dur)
        pressione = generate_pressione(flat=flat_p,
                                       session_duration=session_dur)

        render_chart(ax, meta, flusso, pressione)

        ground_truth.append({
            "page":       page_index,
            "chart":      i,
            "metadata":   meta,
            "flusso":     {"time_min": flusso[0].tolist(),
                           "value":    flusso[1].tolist()},
            "pressione":  {"time_min": pressione[0].tolist(),
                           "value":    pressione[1].tolist()},
        })

    return ground_truth


# ---------------------------------------------------------------------------
# PDF generator
# ---------------------------------------------------------------------------

def generate_pdf(
    n_pages:  int,
    scenario: str,
    out_path: str,
    seed:     int | None = None,
) -> list[dict]:
    """
    Generate a single multi-page PDF and return all ground truth data.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    base_date = datetime(2024, 3, 7, 3, 0, 0)
    all_gt: list[dict] = []

    with matplotlib.backends.backend_pdf.PdfPages(out_path) as pdf:
        for p in range(n_pages):
            fig = plt.figure(figsize=(FIG_W, FIG_H))
            gs  = gridspec.GridSpec(
                GRID_ROWS, GRID_COLS,
                figure=fig,
                hspace=0.60,
                wspace=0.45,
                left=0.08, right=0.92,
                top=0.97,  bottom=0.03,
            )

            page_gt = build_page(
                fig, gs,
                page_index=p,
                base_date=base_date + timedelta(days=p),
                scenario=scenario,
            )
            all_gt.extend(page_gt)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            print(f"  Page {p + 1}/{n_pages} done")

    return all_gt


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = {
    "baseline": {
        "pages":       1,
        "description": "1 page, 8 normal sessions — happy-path validation",
        "filename":    "synthetic_1_baseline.pdf",
        "seed":        42,
    },
    "multipage": {
        "pages":       3,
        "description": "3 pages, 24 charts — multi-page iteration + CSV collision handling",
        "filename":    "synthetic_2_multipage.pdf",
        "seed":        7,
    },
    "edge": {
        "pages":       2,
        "description": "2 pages, 16 charts — short sessions, flat curves, duplicate animal IDs",
        "filename":    "synthetic_3_edge.pdf",
        "seed":        99,
    },
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic AMS PDF files for pipeline testing."
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
        help="Which scenario to generate (default: all)",
    )
    parser.add_argument(
        "--out", default="./pdf_output",
        help="Output directory",
    )
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    scenarios_to_run = (
        list(SCENARIOS.keys()) if args.scenario == "all"
        else [args.scenario]
    )

    all_ground_truth = {}

    for name in scenarios_to_run:
        cfg = SCENARIOS[name]
        out_path = os.path.join(args.out, cfg["filename"])
        print(f"\n[{name}] {cfg['description']}")
        print(f"  Output: {out_path}")

        gt = generate_pdf(
            n_pages=cfg["pages"],
            scenario=name,
            out_path=out_path,
            seed=cfg["seed"],
        )
        all_ground_truth[name] = gt
        print(f"  [ok] {cfg['pages']} page(s), {len(gt)} charts")

    # Save combined ground truth JSON
    gt_path = os.path.join(args.out, "ground_truth.json")
    with open(gt_path, "w") as f:
        json.dump(all_ground_truth, f, indent=2)
    print(f"\nGround truth → {gt_path}")
    print("Done.")


if __name__ == "__main__":
    import matplotlib.backends.backend_pdf
    main()
