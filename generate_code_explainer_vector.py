"""
Build Cow_Curve_Analytics_Code_Explainer.pdf - a file-by-file walkthrough of
the code as it actually stands, in the same visual template as the technical
explainer.

Every function named here was read out of the source rather than remembered,
so the document and the repository do not drift apart.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, Table, TableStyle,
                                NextPageTemplate, PageBreak, KeepTogether)
from reportlab.lib.enums import TA_LEFT

NAVY = colors.HexColor("#1a3a5b")
ACCENT = colors.HexColor("#2462eb")
BODY = colors.HexColor("#1e293b")
MUTED = colors.HexColor("#64748b")
FOOT = colors.HexColor("#e2e8ef")
PALE = colors.HexColor("#dbeafe")
RULE = colors.HexColor("#cbd5e1")
ZEBRA = colors.HexColor("#f6f8fb")

W, H = A4
TITLE = "COW CURVE ANALYTICS"
SUB = "Code Explainer  •  University of Naples Federico II"

ss = {
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13,
                         textColor=colors.white, leading=16),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5,
                         textColor=BODY, leading=14, spaceBefore=6,
                         spaceAfter=3),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                           textColor=BODY, leading=14, spaceAfter=7,
                           alignment=TA_LEFT),
    "bul": ParagraphStyle("bul", fontName="Helvetica", fontSize=9.5,
                          textColor=BODY, leading=14, leftIndent=14,
                          bulletIndent=4, spaceAfter=3),
    "num": ParagraphStyle("num", fontName="Helvetica", fontSize=9.5,
                          textColor=BODY, leading=14, leftIndent=16,
                          bulletIndent=4, spaceAfter=5),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9,
                           textColor=BODY, leading=12),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=9,
                            textColor=colors.white, leading=12),
    "mono": ParagraphStyle("mono", fontName="Courier", fontSize=8.5,
                           textColor=BODY, leading=11.5),
    "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8.5,
                           textColor=MUTED, leading=12, spaceAfter=7),
}


def H2(n, t):
    tb = Table([[Paragraph("%d. %s" % (n, t), ss["h2"])]],
               colWidths=[510.2], rowHeights=[26])
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return KeepTogether([Spacer(1, 7), tb, Spacer(1, 9)])


def tbl(rows, widths):
    data = [[Paragraph(c, ss["cellb"]) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(str(c), ss["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), NAVY),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
          ("LEFTPADDING", (0, 0), (-1, -1), 7),
          ("RIGHTPADDING", (0, 0), (-1, -1), 7),
          ("LINEBELOW", (0, 1), (-1, -2), 0.4, RULE),
          ("BOX", (0, 0), (-1, -1), 0.5, RULE)]
    for i in range(2, len(data), 2):
        st.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(st))
    return t


def code(lines):
    t = Table([[Paragraph("<br/>".join(lines), ss["mono"])]], colWidths=[490])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ZEBRA),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def title_page(canv, doc):
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, 0, W, H, stroke=0, fill=1)
    canv.setFillColor(ACCENT)
    canv.rect(0, 0, W, 99.2, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 28)
    canv.drawString(56, H - 250, "Cow Curve Analytics")
    canv.setFillColor(PALE)
    canv.setFont("Helvetica", 14)
    canv.drawString(56, H - 280, "Code Explainer — File by File")
    canv.setFillColor(colors.HexColor("#e2e8f0"))
    canv.setFont("Helvetica", 10)
    canv.drawString(56, H - 306,
                    "What each module does, and how a request flows through it")
    canv.setStrokeColor(ACCENT)
    canv.setLineWidth(2)
    canv.line(56, H - 326, 196, H - 326)
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica", 11)
    y = H - 368
    for ln in ("University of Naples Federico II", "MSc Data Science",
               "Supervisor: Prof. Schiano Lo Moriello", "October 2026"):
        canv.drawString(56, y, ln)
        y -= 19
    canv.restoreState()


def inner_page(canv, doc):
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, H - 31.2, W, 31.2, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 8)
    canv.drawString(42.5, H - 14, TITLE)
    canv.setFont("Helvetica", 8)
    canv.drawString(42.5, H - 25, SUB)
    canv.setFillColor(FOOT)
    canv.rect(0, 0, W, 25.5, stroke=0, fill=1)
    canv.setFillColor(MUTED)
    canv.setFont("Helvetica", 7.5)
    canv.drawString(42.5, 10, "Page %d  •  Confidential — "
                    "MSc Data Science Thesis" % doc.page)
    canv.drawRightString(W - 42.5, 10, "Code as of build "
                         "2026-10-06-bounded-calibration")
    canv.restoreState()


def build(path):
    doc = BaseDocTemplate(path, pagesize=A4,
                          leftMargin=42.5, rightMargin=42.5,
                          topMargin=46, bottomMargin=36,
                          title="Cow Curve Analytics — Code Explainer",
                          author="DhruvStats")
    doc.addPageTemplates([
        PageTemplate(id="title", frames=[Frame(0, 0, W, H, id="blank")],
                     onPage=title_page),
        PageTemplate(id="inner",
                     frames=[Frame(42.5, 36, W - 85, H - 92, id="body")],
                     onPage=inner_page),
    ])
    s = [NextPageTemplate("inner"), PageBreak()]

    # ---------------- 1 ----------------
    s.append(H2(1, "File Map"))
    s.append(Paragraph(
        "Ten files carry the system. Everything else is generated output, "
        "sample data or deployment configuration.", ss["body"]))
    s.append(tbl([
        ["File", "Lines", "Responsibility"],
        ["pipeline/vector_extract.py", "686",
         "Reads curves from the PDF vector layer and calibrates both axes"],
        ["pipeline/pipeline.py", "1302",
         "Orchestration, integration, bounded calibration, CSV and images"],
        ["pipeline/settings.py", "159",
         "Every threshold and constant; the single source of truth"],
        ["app.py", "438",
         "Flask backend — upload, job registry, polling, downloads"],
        ["frontend/index.html", "1384",
         "Single-file UI, original and extracted charts side by side"],
        ["tests/verify_against_pdf.py", "233",
         "Independent re-measurement of the curves at 600 DPI"],
        ["tests/verify_metadata.py", "176",
         "Checks header fields against the PDF text layer"],
        ["demo/make_demos.py", "282",
         "Generates demo reports with ground truth"],
        ["demo/score_demos.py", "132",
         "Scores extraction against that ground truth"],
        ["Dockerfile, render.yaml", "35, 15",
         "Container build and one-click deployment"],
    ], [150, 46, 294]))

    # ---------------- 2 ----------------
    s.append(H2(2, "pipeline/vector_extract.py"))
    s.append(Paragraph(
        "The module that replaced pixel masking. It never rasterises; it asks "
        "the PDF what it drew.", ss["body"]))

    s.append(Paragraph("has_vector_curves(page)", ss["h3"]))
    s.append(Paragraph(
        "Gate function. Scans the drawing list for at least 20 strokes passing "
        "the blue or green test, and returns True if the page carries a real "
        "vector layer. A scanned or flattened PDF fails here and the raster "
        "path in pipeline.py is used instead.", ss["body"]))

    s.append(Paragraph("_is_blue(c) and _is_green(c)", ss["h3"]))
    s.append(Paragraph(
        "The only thing separating flow from pressure. Each is a three-part "
        "test on the stroke's DeviceRGB colour, with the limits held in "
        "settings.py:", ss["body"]))
    s.append(code([
        "def _is_blue(c):",
        "&nbsp;&nbsp;&nbsp;&nbsp;return (c[2] &gt; settings.BLUE_MIN_B      # blue  &gt; 0.55",
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;and c[0] &lt; settings.BLUE_MAX_R   # red   &lt; 0.45",
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;and c[1] &lt; settings.BLUE_MAX_G)  # green &lt; 0.45",
    ]))
    s.append(Paragraph(
        "A stroke failing all three tests is skipped entirely. There is no "
        "nearest-match fallback, so a colour change in the source produces an "
        "empty result rather than a quietly wrong one.", ss["note"]))

    s.append(Paragraph("_y_calibration(...) and _tick_value_range(...)", ss["h3"]))
    s.append(Paragraph(
        "Builds the vertical ruler. The axis tick labels sit at known heights, "
        "so a least-squares fit through those (y, value) pairs converts any "
        "coordinate to kg/min. Each chart is fitted on its own; the residual "
        "is carried into the result and stays below 0.004.", ss["body"]))

    s.append(Paragraph("_x_calibration(...), _tick_x(...), _frame_x(...)", ss["h3"]))
    s.append(Paragraph(
        "Builds the horizontal ruler without reading a single tick label. "
        "_tick_x finds the short vertical marks along the lower frame and "
        "_x_calibration detects their uniform pitch — 21 marks at 13.2 pt on "
        "the sample report. _frame_x locates the plot box by testing individual "
        "segments rather than path bounding boxes, which is what makes "
        "detection reliable when a chart overruns the page midpoint.",
        ss["body"]))

    s.append(Paragraph("_collect_points(...) and _points_to_series(...)", ss["h3"]))
    s.append(Paragraph(
        "_collect_points gathers every segment endpoint inside the chart box "
        "that passes the colour test — 86 points for a typical curve. "
        "_points_to_series sorts them by x, applies both calibrations and "
        "returns the (time, value) arrays.", ss["body"]))

    s.append(Paragraph("_parse_header(...) and extract_page(page, n)", ss["h3"]))
    s.append(Paragraph(
        "_parse_header reads animal ID, date, time and the printed milk weight "
        "from the text layer. extract_page is the entry point: it slices the "
        "page into the 4 × 2 grid, runs the steps above per cell, and returns "
        "a list of ChartData records carrying the series, the calibration, the "
        "crop rectangle and the reaches_axis_end flag.", ss["body"]))

    # ---------------- 3 ----------------
    s.append(H2(3, "pipeline/pipeline.py"))
    s.append(Paragraph(
        "Orchestrates extraction and owns everything that happens after the "
        "curve has been measured.", ss["body"]))

    s.append(Paragraph("run_pipeline(input_path, out_dir)", ss["h3"]))
    s.append(Paragraph(
        "Entry point used by both the web app and the command line. Opens the "
        "PDF, asks has_vector_curves whether the vector path applies, and "
        "dispatches to _run_vector or _run_cv accordingly.", ss["body"]))

    s.append(Paragraph("_calibrate_to_printed_milk(f_t, f_v, milk_kg)", ss["h3"]))
    s.append(Paragraph(
        "The most consequential function in the file, and the one most worth "
        "reading closely. The AMS prints its own measured weight on every "
        "chart. The drawn line has width, so the true curve lies somewhere "
        "inside the ink and a small scale legitimately moves within that band.",
        ss["body"]))
    s.append(Paragraph(
        "The bound is the ink itself. Half the pen width is the most any single "
        "reading can be out by, so over a session of length T it accounts for "
        "at most that much area:", ss["body"]))
    s.append(code([
        "duration = float(t[-1] - t[0])",
        "allowed&nbsp;&nbsp;= (settings.PEN_HALF_WIDTH_KG_MIN * duration",
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;* settings.CALIBRATION_TOLERANCE)",
        "gap&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= abs(milk_kg - area)",
        "",
        "if gap &gt; allowed:",
        "&nbsp;&nbsp;&nbsp;&nbsp;# Beyond ink ambiguity - leave it alone.",
        "&nbsp;&nbsp;&nbsp;&nbsp;return v, scale, False, \"exceeds_pen_width\"",
        "",
        "return v * scale, scale, True, None",
    ]))
    s.append(Paragraph(
        "A wider gap is not ink ambiguity; it is milk the chart never drew, "
        "which happens when the session ran past the right edge of the time "
        "axis. Those curves are returned exactly as measured, and the caller "
        "records milk_pct_of_printed so the chart reports the figure it "
        "actually reaches. On the sample report 10 of 16 charts calibrate "
        "inside the bound and 6 are refused.", ss["body"]))

    s.append(Paragraph("_build_long_csv(...)", ss["h3"]))
    s.append(Paragraph(
        "Resamples both series onto an even grid at CSV_TIME_STEP_MIN and "
        "writes the three columns. A second, tightly bounded re-fit (±0.1 %) "
        "runs here so the number in the file integrates exactly on the sampled "
        "grid rather than only on the dense vertices.", ss["body"]))

    s.append(Paragraph("_series_metrics, _measure_curve_fidelity, _render_chart_image",
                       ss["h3"]))
    s.append(Paragraph(
        "Peak, integral and duration per series; an optional re-measurement "
        "against the rasterised page, gated behind RUN_FIDELITY_CHECK because "
        "it costs about 32 seconds; and the chart crop used for the "
        "side-by-side comparison in the UI.", ss["body"]))

    # ---------------- 4 ----------------
    s.append(H2(4, "pipeline/settings.py"))
    s.append(Paragraph(
        "No threshold is written inline anywhere else. Changing behaviour means "
        "editing this file, which is what makes the system reproducible between "
        "runs and inspectable by a reviewer.", ss["body"]))
    s.append(tbl([
        ["Constant", "Value", "Governs"],
        ["GRID_ROWS, GRID_COLS", "4, 2", "Chart layout per page"],
        ["BLUE_MIN_B / MAX_R / MAX_G", "0.55 / 0.45 / 0.45",
         "Which strokes count as flow"],
        ["GREEN_MIN_G / MAX_R / MAX_B", "0.35 / 0.45 / 0.45",
         "Which strokes count as pressure"],
        ["CSV_TIME_STEP_MIN", "0.02", "Row spacing in the CSV"],
        ["CALIBRATE_TO_PRINTED_MILK", "True", "Whether to scale at all"],
        ["PEN_HALF_WIDTH_KG_MIN", "0.0389", "The calibration bound"],
        ["CALIBRATION_TOLERANCE", "1.15", "Headroom above that bound"],
        ["FLOW_THRESHOLD_KG_MIN", "0.20", "The AMS's own printed cut-off"],
        ["RUN_FIDELITY_CHECK", "False", "Skips the 32 s raster re-measurement"],
    ], [160, 110, 220]))

    # ---------------- 5 ----------------
    s.append(H2(5, "app.py"))
    s.append(Paragraph(
        "A small Flask service. No database, no external calls, no login.",
        ss["body"]))
    s.append(tbl([
        ["Route", "Purpose"],
        ["GET /", "Serves the single-page frontend"],
        ["GET /build",
         "Returns the build id and measurement rules, so a stale deployment is "
         "obvious without uploading anything"],
        ["POST /upload", "Accepts the PDF, starts a background job, returns its id"],
        ["GET /status/&lt;id&gt;", "Progress, per-chart payload and summary"],
        ["GET /download/&lt;id&gt;/&lt;file&gt;", "One CSV, path-guarded"],
        ["GET /chart-image/&lt;id&gt;/&lt;file&gt;", "The original chart crop"],
        ["GET /download-all/&lt;id&gt;", "Every CSV as one ZIP"],
    ], [168, 322]))
    s.append(Paragraph(
        "_chart_payload shapes one chart for the browser, including "
        "milk_uncalibrated_reason and milk_pct_of_printed so a refused chart "
        "can explain itself. _summarise aggregates the report and reports "
        "charts_calibrated against charts_measured_only. _safe_job_file "
        "resolves and confines every download path, so a crafted filename "
        "cannot escape the job directory.", ss["body"]))
    s.append(Paragraph(
        "The job registry is a dictionary inside the process, so the supplied "
        "configuration runs one gunicorn worker with several threads. Raising "
        "the worker count requires moving that registry to shared storage "
        "first.", ss["note"]))

    # ---------------- 6 ----------------
    s.append(H2(6, "frontend/index.html"))
    s.append(Paragraph(
        "One file, no build step and no framework, so it can be opened and read "
        "directly. It polls /status, renders each chart beside its original "
        "crop, and computes session statistics in the browser using the "
        "thresholds served by /build rather than its own copies.", ss["body"]))
    s.append(Paragraph(
        "A chart whose calibration was refused is labelled — “ran past axis” "
        "where the session continued beyond the chart, otherwise “as "
        "measured” — so a low percentage reads as a property of the source "
        "rather than an extraction fault.", ss["body"]))
    s.append(Paragraph(
        "Polling stops on a completed job, with a retry guard: a status of "
        "done with an empty file list is re-polled a few times rather than "
        "treated as a finished job, which is what previously produced the "
        "“0 CSV files generated” report.", ss["note"]))

    # ---------------- 7 ----------------
    s.append(H2(7, "Tests and Demo Data"))
    s.append(Paragraph(
        "Neither test shares code with the extractor, which is what makes them "
        "worth running.", ss["body"]))
    s.append(Paragraph(
        "<b>tests/verify_against_pdf.py</b> rasterises the report at 600 DPI — "
        "four times finer than the old pipeline ever worked at — and measures "
        "the curves again by an independent path. Agreement on the sample "
        "report is 0.0099 kg/min.", ss["body"]))
    s.append(Paragraph(
        "<b>tests/verify_metadata.py</b> re-reads every header field straight "
        "from the text layer and compares it with what the pipeline recorded.",
        ss["body"]))
    s.append(Paragraph(
        "<b>demo/make_demos.py</b> generates reports in the real layout, 2 pages "
        "× 8 charts, writing the exact curve coordinates to JSON first. "
        "<b>demo/score_demos.py</b> then scores extraction against that truth: "
        "0.0037 kg/min mean error over 64 charts. Because these contain no "
        "truncated session, all 16 charts in each calibrate inside the bound.",
        ss["body"]))

    # ---------------- 8 ----------------
    s.append(H2(8, "How a Request Flows"))
    for i, t in enumerate([
        "The browser POSTs the PDF to <font name='Courier'>/upload</font>. "
        "app.py saves it, creates a job id and starts a worker thread.",
        "<font name='Courier'>run_pipeline</font> opens the document and calls "
        "<font name='Courier'>has_vector_curves</font>. A real AMS report takes "
        "the vector path.",
        "For each page, <font name='Courier'>extract_page</font> slices the "
        "4 × 2 grid and, per chart, collects the coloured segments, fits both "
        "axes and parses the header.",
        "Back in pipeline.py the flow series is integrated, offered to "
        "<font name='Courier'>_calibrate_to_printed_milk</font> and either "
        "scaled within the ink bound or kept as measured with a reason.",
        "<font name='Courier'>_build_long_csv</font> writes the three columns; "
        "<font name='Courier'>_render_chart_image</font> saves the original "
        "crop for comparison.",
        "The browser polls <font name='Courier'>/status</font>, draws each "
        "chart beside its crop, and offers the CSVs individually or as one ZIP.",
    ], 1):
        s.append(Paragraph(t, ss["num"], bulletText="%d." % i))

    s.append(Spacer(1, 4))
    s.append(Paragraph(
        "Reading order for a reviewer: settings.py first, since it states every "
        "rule the system follows; then vector_extract.py for how a curve is "
        "recovered; then _calibrate_to_printed_milk for what is done with it "
        "afterwards, which is where the accuracy claim is decided.", ss["note"]))

    doc.build(s)
    print("written:", path)


if __name__ == "__main__":
    build("Cow_Curve_Analytics_Code_Explainer.pdf")
