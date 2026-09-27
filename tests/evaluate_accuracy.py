"""
evaluate_accuracy.py

Compares pipeline CSV output against synthetic ground truth JSON.
Computes per-curve MAE (Mean Absolute Error) and coverage metrics.

The ground truth file (synthetic/pdf_output/ground_truth.json) is a dict with
one key per dataset — "baseline", "multipage", "edge" — each holding a flat
list of chart dicts:
    {page, chart, metadata: {animal_id, date_iso, time_hhmm, ...},
     flusso:    {time_min: [...], value: [...]},
     pressione: {time_min: [...], value: [...]}}

Usage (from the tests/ directory):
    python evaluate_accuracy.py                    # evaluate all 3 datasets
    python evaluate_accuracy.py --dataset edge     # one dataset only
    python evaluate_accuracy.py --dataset baseline --csv /path/to/csv_dir
"""

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_GT = os.path.join(PROJECT_ROOT, "synthetic", "pdf_output", "ground_truth.json")

# Default CSV output directory for each dataset
DATASET_CSV_DIRS = {
    "baseline":  os.path.join(PROJECT_ROOT, "pipeline", "csv_synthetic_baseline"),
    "multipage": os.path.join(PROJECT_ROOT, "pipeline", "csv_synthetic_multipage"),
    "edge":      os.path.join(PROJECT_ROOT, "pipeline", "csv_synthetic_edge"),
}

CURVES = [
    ("Flusso_kg_min",             "flusso",    "kg/min"),
    ("Pressione_assoluta_0.1bar", "pressione", "x0.1 bar"),
]


def find_csv_for_chart(csv_dir: str, chart_gt: dict) -> str | None:
    """
    Locate the CSV written for a ground-truth chart.

    When the same animal has multiple sessions on one date the pipeline names
    the first file animal_{id}_{date}.csv and suffixes later ones with the
    session time (_HHMM). Prefer the exact time-suffix match so each ground
    truth session is scored against its own file, not just the first match.
    """
    aid  = str(chart_gt["metadata"]["animal_id"])
    date = chart_gt["metadata"]["date_iso"]
    hhmm = chart_gt["metadata"].get("time_hhmm")

    matches = sorted(glob.glob(os.path.join(csv_dir, f"animal_{aid}_{date}*.csv")))
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    if hhmm:
        for m in matches:
            if m.endswith(f"_{hhmm}.csv"):
                return m
    plain = os.path.join(csv_dir, f"animal_{aid}_{date}.csv")
    return plain if plain in matches else matches[0]


def evaluate_dataset(name: str, charts_gt: list, csv_dir: str) -> dict:
    """Score one dataset. Returns per-curve MAE and coverage lists."""
    stats = {csv_name: {"mae": [], "cov": []} for csv_name, _, _ in CURVES}
    found = 0

    for chart_gt in charts_gt:
        csv_path = find_csv_for_chart(csv_dir, chart_gt)
        if csv_path is None:
            meta = chart_gt["metadata"]
            print(f"  [MISSING] {name} page {chart_gt['page']} chart {chart_gt['chart']} "
                  f"(ID={meta['animal_id']}, date={meta['date_iso']})")
            continue

        found += 1
        df = pd.read_csv(csv_path)

        for csv_name, gt_key, _ in CURVES:
            gt_t = chart_gt[gt_key]["time_min"]
            gt_v = chart_gt[gt_key]["value"]
            pred = df[df["curve"] == csv_name]

            if len(pred) == 0:
                stats[csv_name]["mae"].append(None)
                stats[csv_name]["cov"].append(0.0)
                continue

            pred_t = pred["time_min"].values
            pred_v = pred["value"].values
            gt_interp = np.interp(pred_t, gt_t, gt_v)
            mae = float(np.mean(np.abs(pred_v - gt_interp)))
            coverage = (pred_t.max() - pred_t.min()) / (max(gt_t) - min(gt_t))

            stats[csv_name]["mae"].append(mae)
            stats[csv_name]["cov"].append(min(coverage, 1.0))

    stats["found"] = found
    stats["total"] = len(charts_gt)
    return stats


def print_report(all_stats: dict):
    total_found = sum(s["found"] for s in all_stats.values())
    total_gt    = sum(s["total"] for s in all_stats.values())

    print(f"\n{'='*55}")
    print("  Accuracy Report")
    print(f"{'='*55}")
    print(f"  Datasets evaluated     : {', '.join(all_stats)}")
    print(f"  Charts found in CSV    : {total_found} / {total_gt}")

    for csv_name, _, unit in CURVES:
        maes = [m for s in all_stats.values() for m in s[csv_name]["mae"]]
        covs = [c for s in all_stats.values() for c in s[csv_name]["cov"]]
        valid = [m for m in maes if m is not None]

        print(f"\n  {csv_name}")
        print(f"    Detected             : {len(valid)} / {total_found}")
        if valid:
            print(f"    MAE  (mean)          : {np.mean(valid):.4f}  {unit}")
            print(f"    MAE  (median)        : {np.median(valid):.4f}  {unit}")
            print(f"    MAE  (max)           : {np.max(valid):.4f}  {unit}")
            print(f"    Coverage (mean)      : {np.mean(covs)*100:.1f} %")
    print(f"{'='*55}\n")


def main():
    parser = argparse.ArgumentParser(description="Pipeline accuracy evaluator")
    parser.add_argument("--gt", default=DEFAULT_GT,
                        help="Path to ground_truth.json")
    parser.add_argument("--dataset", default="all",
                        choices=["all", *DATASET_CSV_DIRS],
                        help="Which synthetic dataset to evaluate")
    parser.add_argument("--csv", default=None,
                        help="CSV directory override (only with a single --dataset)")
    args = parser.parse_args()

    with open(args.gt) as f:
        gt = json.load(f)

    names = list(DATASET_CSV_DIRS) if args.dataset == "all" else [args.dataset]
    if args.csv and len(names) > 1:
        parser.error("--csv requires a single --dataset")

    all_stats = {}
    for name in names:
        csv_dir = args.csv or DATASET_CSV_DIRS[name]
        print(f"[{name}]  csv dir: {csv_dir}")
        all_stats[name] = evaluate_dataset(name, gt[name], csv_dir)

    print_report(all_stats)


if __name__ == "__main__":
    main()
