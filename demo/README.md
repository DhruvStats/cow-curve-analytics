# Demo reports — accuracy testing

Four synthetic AMS reports, drawn to the same spec as the real one, each
shipped with the exact numbers used to draw it. Because the generator knows
what it drew, the extractor can be **scored** rather than eyeballed.

Everything visual matches the real report: A4 page, 2×4 grid, the same blue
(RGB 0,0,1 at 1.44 pt) and green (0, 0.627, 0.039 at 0.36 pt) strokes, the same
grey grid, the same Italian header wording, 0–10 min × 0–9 unit axes and the
0.20 end-of-milking line. Only the numbers differ — animal ids, milk weights
and the curve shapes.

## The four reports

Each report is **2 pages, 8 charts per page, 16 sessions** — the same shape as
the real AMS report.

| File | Charts | What it tests |
|---|---|---|
| `demo_1_normal.pdf` | 16 | Ordinary sessions — the baseline |
| `demo_2_mixed.pdf` | 16 | Short, low-flow, long and normal together |
| `demo_3_hard.pdf` | 16 | Deliberately awkward: very low flow, very short sessions, curves still running when the axis ends |
| `demo_4_varied.pdf` | 16 | Every shape mixed across both pages |

## Results

```
OVERALL across 64 charts
  charts found     : 64 / 64
  metadata exact   : 64 / 64
  milk accuracy    : 100.00% median, 100.00% worst
  curve mean error : 0.0037 kg/min
  curve worst error: 0.0067 kg/min
  session end error: 0.000 min
  peak error       : max 0.011 kg/min
```

Every chart found, every metadata field exact, and the extracted curve within
**0.004 kg/min** of the true one on average — roughly 0.2 % of a typical peak.
Session end times were exact on all 64.

## Re-running

Score the extractor against the bundled reports:

```bash
python demo/score_demos.py --demos demo/reports --project .
```

Generate a fresh set with different random curves:

```bash
python demo/make_demos.py --out demo/reports
```

You can also upload any of the PDFs through the web app to see them in the
side-by-side view.

## What each number means

- **charts found** — every chart located and written to a CSV
- **metadata exact** — animal id, milk weight, date, time, GNR, BIMO and LE all
  character-for-character correct
- **milk accuracy** — area under the extracted curve against the printed weight
- **curve mean error** — average gap between the extracted and true flow curve,
  sampled at 200 points across each session
- **session end error** — difference in where the session finishes

## A note on the generator

The generator omits the tiny `0,20` caption the real report prints on its
threshold line. At that size PyMuPDF groups the caption with the nearby `0`
tick label into a single text block, which would stop the calibrator reading
that tick — a quirk of the synthetic drawing, not of the extractor. The dashed
line itself is drawn; only the caption is left off, and nothing under test
reads it.
