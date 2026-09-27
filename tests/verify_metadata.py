"""
verify_metadata.py

Check the metadata the pipeline reads against the text printed in the PDF.

The curve check (verify_against_pdf.py) proves the numbers are right. This
proves the *labels* are right: that the milk quantity, date, session time,
farm, GNR, BIMO and LE the pipeline extracts are character-for-character what
the report prints for that chart.

The CSV files themselves hold curve data only (curve, time_min, value); the
metadata travels in the pipeline result, drives the CSV filename and is shown
in the web UI. So this checks the extracted values, not CSV columns.

Parses the PDF independently of the pipeline — its own regexes, its own chart
ordering — so a bug in the extractor cannot hide by being reproduced here.

Exit code is 0 only when every field of every chart matches.

Usage:
    python verify_metadata.py --pdf ../sample_input/sample_report.pdf
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))

import fitz  # noqa: E402
import vector_extract as ve  # noqa: E402

_ANIMAL = re.compile(r"Animale[:\s]*(\d+)")
_MILK = re.compile(r"latte[:\s]*([\d.,]+)\s*kg", re.IGNORECASE)
_DATE = re.compile(r"Data[:\s]*(\d{1,2})\.(\d{1,2})\.(\d{4})")
_ORA = re.compile(r"Ora[:\s]*(\d{2}):(\d{2}):(\d{2})")
_GNR = re.compile(r"GNR[:\s]*(\w+)")
_BIMO = re.compile(r"BIMO\s*=\s*(\w+)")
_LE = re.compile(r"LE\s*=\s*(\w+)")
_FARM = re.compile(r"Numero\s+Azienda\s*(\w+)")

FIELDS = ["farm", "animal_id", "date", "date_printed",
          "time", "milk_kg", "gnr", "bimo", "le"]


def read_truth(pdf_path: str) -> dict:
    """
    Per-chart header values, read straight from the PDF text.

    Keyed by (animal id, HHMM) because one animal can be milked more than once
    on the same date, and the two sessions must not be conflated.
    """
    doc = fitz.open(pdf_path)
    truth = {}

    for pno in range(doc.page_count):
        page = doc[pno]
        width = page.rect.width
        blocks = page.get_text("blocks")

        heads = [(b[1], b[0], b[4]) for b in blocks if _ANIMAL.search(b[4])]
        heads.sort(key=lambda e: (round(e[0] / 20) * 20, e[1] > width / 2))
        row_tops = sorted({round(h[0]) for h in heads})

        for hy, hx, txt in heads:
            cx0, cx1 = (0, width / 2) if hx < width / 2 else (width / 2, width)
            y0 = hy - 6
            ri = row_tops.index(round(hy))
            y1 = (row_tops[ri + 1] - 6) if ri + 1 < len(row_tops) else page.rect.height

            full = txt + " " + " ".join(
                b[4] for b in blocks
                if cx0 <= (b[0] + b[2]) / 2 < cx1 and y0 <= (b[1] + b[3]) / 2 <= y1
            )

            dm, om = _DATE.search(full), _ORA.search(full)
            am, mm = _ANIMAL.search(full), _MILK.search(full)
            if not (dm and om and am and mm):
                continue

            key = (am.group(1), om.group(1) + om.group(2))
            truth[key] = {
                "farm": _FARM.search(full).group(1) if _FARM.search(full) else None,
                "animal_id": am.group(1),
                "date": f"{dm.group(3)}-{dm.group(2).zfill(2)}-{dm.group(1).zfill(2)}",
                "date_printed": f"{dm.group(1).zfill(2)}.{dm.group(2).zfill(2)}.{dm.group(3)}",
                "time": f"{om.group(1)}:{om.group(2)}:{om.group(3)}",
                "milk_kg": float(mm.group(1).replace(",", ".")),
                "gnr": _GNR.search(full).group(1) if _GNR.search(full) else None,
                "bimo": _BIMO.search(full).group(1) if _BIMO.search(full) else None,
                "le": _LE.search(full).group(1) if _LE.search(full) else None,
            }

    doc.close()
    return truth


def check(pdf_path: str) -> int:
    truth = read_truth(pdf_path)

    doc = fitz.open(pdf_path)
    extracted = []
    for pno in range(doc.page_count):
        extracted.extend(ve.extract_page(doc[pno], pno))
    doc.close()

    if not extracted:
        print("No charts extracted from the PDF.")
        return 1

    failures = 0
    for cd in extracted:
        label = f"animal {cd.animal_id} @ {cd.time_full or cd.time}"
        got = {
            "farm": cd.farm,
            "animal_id": cd.animal_id,
            "date": cd.date,
            "date_printed": cd.date_printed,
            "time": cd.time_full,
            "milk_kg": cd.milk_kg,
            "gnr": cd.gnr,
            "bimo": cd.bimo,
            "le": cd.le,
        }

        exp = truth.get((str(cd.animal_id), str(cd.time)))
        if exp is None:
            print(f"  [FAIL] {label}: no matching chart found in the PDF text")
            failures += 1
            continue

        diffs = []
        for c in FIELDS:
            if c == "milk_kg":
                if got[c] is None or abs(float(got[c]) - float(exp[c])) > 1e-9:
                    diffs.append((c, exp[c], got[c]))
            elif str(got[c]) != str(exp[c]):
                diffs.append((c, exp[c], got[c]))

        if diffs:
            print(f"  [FAIL] {label}")
            for c, e, g in diffs:
                print(f"           {c}: printed {e!r}, extracted {g!r}")
            failures += 1

    print(f"\n{'=' * 58}")
    print("  Extracted metadata vs. the printed report")
    print(f"{'=' * 58}")
    print(f"  Charts checked : {len(extracted)}")
    print(f"  Charts in PDF  : {len(truth)}")
    print(f"  Fields/chart   : {len(FIELDS)} ({', '.join(FIELDS)})")
    if failures:
        print(f"  Result         : {failures} chart(s) FAILED")
    else:
        print(f"  Result         : ALL MATCH - "
              f"{len(extracted) * len(FIELDS)} field checks, 0 mismatches")
    print(f"{'=' * 58}\n")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(
        description="Verify CSV metadata against the printed PDF")
    ap.add_argument("--pdf", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.pdf):
        print(f"Not found: {args.pdf}")
        sys.exit(1)
    sys.exit(check(args.pdf))


if __name__ == "__main__":
    main()
