"""
score_demos.py — run the extractor over the demo reports and score it.

Each demo PDF was drawn from known curves, so this can compare what came out
against what went in, rather than against another estimate. It checks three
things separately, because they can fail independently:

  metadata   animal id, milk weight, date, time, GNR/BIMO/LE
  curve      extracted flow against the true flow, sampled on a common grid
  milk       area under the extracted curve against the printed weight

Usage:
    python score_demos.py --demos demo_reports --project <chart_digitizer dir>
"""

import argparse
import glob
import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd


def score_one(pdf, truth, pipeline_mod, vector_mod):
    out_dir = tempfile.mkdtemp(prefix="score_")
    results = pipeline_mod.run_pipeline(pdf, out_dir)

    by_key = {}
    for r in results:
        if r.get("csv_file"):
            by_key.setdefault(str(r["animal_id"]), []).append(r)

    rows = []
    for t in truth:
        cand = by_key.get(str(t["animal_id"]), [])
        if not cand:
            rows.append({"animal": t["animal_id"], "found": False})
            continue
        r = cand.pop(0)

        df = pd.read_csv(os.path.join(out_dir, r["csv_file"]))
        f = df[df.curve == pipeline_mod.CURVE_FLOW]
        got_t = f.time_min.values
        got_v = f.value.values

        # curve agreement on a shared grid, over the true session only
        lo, hi = 0.0, min(t["flow_end"], got_t.max())
        grid = np.linspace(lo, hi, 200)
        true_i = np.interp(grid, t["flow_t"], t["flow_v"])
        got_i = np.interp(grid, got_t, got_v)
        err = np.abs(got_i - true_i)

        area = float(np.trapezoid(got_v, got_t))

        rows.append({
            "animal": t["animal_id"],
            "kind": t["kind"],
            "found": True,
            "meta_ok": (str(r["animal_id"]) == str(t["animal_id"])
                        and abs((r.get("milk_kg") or 0) - t["milk_kg"]) < 1e-6
                        and r.get("date") == t["date"]
                        and (r.get("time_full") or "") == t["time"]
                        and str(r.get("gnr")) == t["gnr"]
                        and str(r.get("bimo")) == t["bimo"]
                        and str(r.get("le")) == t["le"]),
            "curve_mean": float(err.mean()),
            "curve_max": float(err.max()),
            "peak_err": abs(float(got_v.max()) - t["peak_flow"]),
            "end_err": abs(float(got_t.max()) - t["flow_end"]),
            "milk_pct": 100.0 * area / t["milk_kg"] if t["milk_kg"] else 0.0,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demos", default="demo_reports")
    ap.add_argument("--project", required=True)
    args = ap.parse_args()

    sys.path.insert(0, os.path.join(args.project, "pipeline"))
    import pipeline as pipeline_mod
    import vector_extract as vector_mod

    truth_all = json.load(open(os.path.join(args.demos, "all_truth.json")))

    grand = []
    for name in sorted(truth_all):
        pdf = os.path.join(args.demos, name + ".pdf")
        if not os.path.exists(pdf):
            continue
        rows = score_one(pdf, truth_all[name], pipeline_mod, vector_mod)
        grand.extend(rows)

        ok = [r for r in rows if r.get("found")]
        meta_ok = sum(1 for r in ok if r["meta_ok"])
        milk = np.array([r["milk_pct"] for r in ok])
        cmean = np.array([r["curve_mean"] for r in ok])

        print("\n%s  (%d charts)" % (name, len(rows)))
        print("  found            : %d / %d" % (len(ok), len(rows)))
        print("  metadata exact   : %d / %d" % (meta_ok, len(ok)))
        print("  milk vs printed  : %.2f%% median, worst %.2f%%"
              % (np.median(milk), milk[np.argmax(np.abs(milk - 100))]))
        print("  curve mean error : %.4f kg/min (worst chart %.4f)"
              % (cmean.mean(), cmean.max()))
        print("  peak error       : max %.4f kg/min"
              % max(r["peak_err"] for r in ok))
        print("  session end error: max %.3f min"
              % max(r["end_err"] for r in ok))

    ok = [r for r in grand if r.get("found")]
    milk = np.array([r["milk_pct"] for r in ok])
    cmean = np.array([r["curve_mean"] for r in ok])
    print("\n" + "=" * 58)
    print("  OVERALL across %d charts" % len(grand))
    print("=" * 58)
    print("  charts found     : %d / %d" % (len(ok), len(grand)))
    print("  metadata exact   : %d / %d"
          % (sum(1 for r in ok if r["meta_ok"]), len(ok)))
    print("  milk accuracy    : %.2f%% median, %.2f%% worst"
          % (np.median(milk), milk[np.argmax(np.abs(milk - 100))]))
    print("  curve mean error : %.4f kg/min" % cmean.mean())
    print("  curve worst error: %.4f kg/min" % cmean.max())
    print("=" * 58)


if __name__ == "__main__":
    main()
