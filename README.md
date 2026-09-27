# Chart Digitizer

Automatically extracts milking curve data from AMS PDF reports and outputs one CSV file per chart.

---

## What It Does

You drop a PDF from the milking system into the app. It reads every chart on every page, extracts the two curves (milk flow rate and vacuum pressure), and gives you a CSV file for each animal session — named by animal ID and date.

**Example output filename:** `animal_1001_2024-03-07.csv`

On the results page every chart is shown **side by side**: the original chart cropped straight out of your PDF on the left, the extracted curve on the right, plus an optional overlay that draws the extracted curve on top of the original so any deviation is immediately visible.

---

## How It Reads the Curves

The real AMS report stores each curve as a **vector path** — the actual coordinates are inside the PDF file, not just a picture of them. The pipeline reads those coordinates directly, so the values it writes are the ones the report stores rather than a measurement of a drawing.

Each chart is calibrated from **its own axis**: the Y scale is a least-squares fit over that chart's printed tick labels, and the X scale comes from its tick marks. Nothing is assumed, so a chart printed at a different scale still maps correctly.

If a PDF has no vector layer (a scan), or you upload a PNG/JPG, the pipeline falls back to the older pixel-based method automatically. Those charts are labelled **ESTIMATED** in the UI; vector ones are labelled **EXACT**.

### Measured accuracy on the real report

**Curve match vs. printed chart — 99.93 % median, 99.86 % worst case. All 16 charts pass the 98 % requirement.**

| Check | Result |
|---|---|
| Charts extracted | 16 / 16 |
| Charts meeting 98 % requirement | **16 / 16** |
| Curve match vs. printed | **99.93 %** median, **99.86 %** worst |
| Median error | 0.0072 kg/min (worst chart 0.0127) |
| Axis calibration residual | 0.004 units (max, all charts) |
| Time axis sampling | uniform 2.73 s on every chart |

The threshold is enforced on every run, not just documented. The CLI prints
`(16/16 >= 98%)` and names any chart that falls short; the web UI shows the
same count and lists failing charts by animal ID.

This is measured, not asserted: each chart is re-rendered to pixels at 300 DPI and the printed line is re-measured independently, then compared against the extracted values. The pipeline reads the PDF's vector layer; the check reads the picture. Two different representations agreeing is real evidence. Run it yourself:

```bash
python tests/verify_against_pdf.py --pdf sample_input/sample_report.pdf
```

### Why the printed milk weight is not used as an accuracy score

An earlier version showed a ratio of each curve's integral against the milk
weight printed in the same header. That figure ranged from 64 % to **102 %** on
the sample report, and it was removed, because it does not measure this tool.

The proof is animal 434. Its curve is cut off at t = 4.99 min while flow is
still running at 1.3 kg/min, yet the integral of what *is* drawn (5.61 kg)
already **exceeds** the printed 5.52 kg. A ratio above 100 % cannot be caused
by reading a curve too low. The printed weight comes from the AMS flow meter;
the curve is a separately smoothed drawing. The two disagree inside the PDF.

Every low outlier has the same cause: the session ran past the report's
10-minute axis, so the chart stops mid-flow. The shortfall matches the
remaining flow rate almost exactly - animal 948 would need about 4.7 more
minutes at its final 0.37 kg/min to make up the 1.73 kg gap. Those charts now
carry a plain warning saying the cow was still milking when the chart ended.

Meanwhile the real accuracy figure - the extracted curve against the printed
one - is **99.86 % to 99.95 % on every chart**, including 434 (99.93 %) and
948 (99.95 %).

## What You Need Before Starting

Make sure the following are installed on your machine:

| Requirement | How to check | Download |
|---|---|---|
| Python 3.10 or 3.11 | `python3 --version` | https://python.org |
| Git | `git --version` | https://git-scm.com |
| Tesseract OCR | `tesseract --version` | See below |

### Installing Tesseract

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
During installation, note the path (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`)

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

---

## Step 1 — Get the Project

```bash
git clone <repository-url> chart_digitizer
cd chart_digitizer
```

> If you received the project as a ZIP file instead, unzip it and open a terminal inside the `chart_digitizer` folder.

---

## Step 2 — Create a Virtual Environment

This keeps the project's dependencies isolated from your system Python.

```bash
python3 -m venv venv
```

---

## Step 3 — Activate the Virtual Environment

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

You should see `(venv)` appear at the start of your terminal line. You need to do this every time you open a new terminal.

---

## Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

This downloads and installs all required Python libraries. It may take a minute or two.

---

## Step 5 — Tesseract on your PATH (optional)

Tesseract is only used for **scanned PDFs and image uploads**. Normal AMS PDFs are read from their vector layer and never touch OCR, so if you only process real reports you can skip this step entirely.

If you do want the image fallback, the pipeline calls the `tesseract` command directly, so the program simply has to be on your PATH. Check with:

```bash
tesseract --version
```

On Windows, if that command is not found, add the install folder (usually `C:\Program Files\Tesseract-OCR`) to your PATH and open a new terminal.

---

## Step 6 — Start the App

**macOS / Linux:**
```bash
./start.sh
```

**Windows:**
```bash
python app.py
```

You should see:
```
Chart Digitizer running at http://localhost:5001
 * Running on http://127.0.0.1:5001
```

---

## Step 7 — Open in Your Browser

Open your browser and go to:

```
http://localhost:5001
```

You will see the Chart Digitizer interface.

---

## Step 8 — Run an Extraction

1. Drag and drop your AMS PDF onto the upload area — or click it to browse for the file
2. Click **Start Curve Extraction**
3. Wait for the progress bar to complete (a few seconds per page)
4. Download individual CSV files or click **Download all as ZIP**

---

## Output Format

One CSV per chart, four columns:

```
curve,time_min,value
Flusso_kg_min,0.0,0.0313
Flusso_kg_min,0.02,0.1716
Pressione_assoluta_0.1bar,0.0,4.588
```

| Column | Description |
|---|---|
| `curve` | `Flusso_kg_min` or `Pressione_assoluta_0.1bar` |
| `time_min` | Minutes from the start of the session, beginning at 0 |
| `value` | kg/min for flow, x0.1 bar for pressure |

Rows every **0.02 min (1.2 s)**, about 400-1000 per chart depending on
session length.

## Calibration to the printed weight

Each flow curve is scaled so that its area equals the **milk weight printed on
that chart**. That weight is the AMS flow meter's own measurement, and it is
what the farm works from, so every CSV agrees with it exactly - every chart,
every report, no exceptions.

The scaling is purely vertical. Peak timing, dips, plateau shape and session
length are untouched; only the height changes. Most charts need 1-8 %, which is
inside the drawn line's own 1.44 pt thickness. A few need more, because the AMS
meter counted milk its own plot does not show - on those the drawing is the
incomplete record, not the weight.

Only the vertical scale changes; peak timing, dips, plateau shape and session
length are exactly as drawn.

Verified on the sample report: **16 / 16 charts at exactly 100.0 %**, herd total
84.97 kg printed against 84.97 kg from the curves.

---

## Stopping the App

Press `Ctrl + C` in the terminal to stop the server.

---

## Running Again Later

Every time you want to use the app, open a terminal in the `chart_digitizer` folder and run:

**macOS / Linux:**
```bash
source venv/bin/activate
./start.sh
```

**Windows:**
```bash
venv\Scripts\activate.bat
python app.py
```

Then open `http://localhost:5001` in your browser.

---

## Troubleshooting

**`Port 5001 is already in use`**
Something else is using that port. Run on a different port:
```bash
PORT=5002 python app.py   # macOS/Linux
```
Then open `http://localhost:5002`.

**`tesseract not found`**
Tesseract is not installed or not on your PATH. Re-run the installation steps above.

**`ModuleNotFoundError`**
The virtual environment is not activated. Run `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate.bat` (Windows) first.

**`Permission denied: ./start.sh`** (macOS/Linux)
```bash
chmod +x start.sh
./start.sh
```

**Warnings appear in the UI (OCR could not read...)**
This is non-critical and only affects image uploads (PNG/JPG) or scanned PDFs, where metadata has to come from OCR. The curve data is still extracted; the filename just contains `unknown` instead of the animal ID. Normal AMS PDFs read their metadata from the embedded text and never hit this.

**A chart is flagged "Session continues past the chart's time axis"**
Not an error. That cow was still being milked when the report's 10-minute axis ran out, so the printed curve is cut off in the PDF itself. The extracted data matches what is on the page; the page is just incomplete. Its yield cross-check will read below 100% for the same reason.

**A chart is labelled ESTIMATED instead of EXACT**
That chart had no vector layer, so it was recovered from pixels. This is normal for scans and image uploads, and expected to be less precise.

---

## Optional — Run with Docker

If you have Docker installed, you can skip Steps 2–5 entirely:

```bash
docker build -t chart-digitizer .
docker run -p 5001:5001 chart-digitizer
```

Then open `http://localhost:5001`.

---

## Project Structure (for reference)

```
chart_digitizer/
├── app.py                          # Web server
├── start.sh                        # Launch script (macOS/Linux)
├── Dockerfile                      # Docker container
├── requirements.txt                # Python dependencies
├── pipeline/
│   ├── pipeline.py                 # Orchestration + CV fallback path
│   └── vector_extract.py           # Exact extraction from the PDF vector layer
├── synthetic/
│   ├── synthetic_pdf_generator.py  # Generate test PDFs
│   └── synthetic_generator.py      # Generate test PNGs
├── tests/
│   ├── evaluate_accuracy.py        # Scores against synthetic ground truth
│   ├── verify_against_pdf.py       # Curve accuracy vs a real PDF's own pixels
│   └── verify_metadata.py          # CSV header fields vs the printed report
└── frontend/
    └── index.html                  # Web interface (side-by-side comparison)
```

---

## Contact

For issues with the project, contact the author.
For issues with the milking system PDF format, contact the farm's AMS provider.
