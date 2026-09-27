"""
generate_code_explainer.py
Generates the Chart Digitizer — Code Explainer PDF.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)

OUT = "/Users/dawarhasnain/Desktop/Thesis Work/chart_digitizer/Chart_Digitizer_Code_Explainer.pdf"

W, H = A4

# ── Colours ───────────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1a3a5c")
MID_BLUE    = colors.HexColor("#2563eb")
LIGHT_BLUE  = colors.HexColor("#dbeafe")
ACCENT      = colors.HexColor("#e2e8f0")
CODE_BG     = colors.HexColor("#f1f5f9")
WHITE       = colors.white
DARK_TEXT   = colors.HexColor("#1e293b")
MUTED       = colors.HexColor("#64748b")
LIGHT_GREEN = colors.HexColor("#dcfce7")
WARN_BG     = colors.HexColor("#fffbeb")

# ── Styles ────────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

styles = {
    "cover_title": S("cover_title",
        fontSize=30, textColor=WHITE, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceAfter=8),
    "cover_sub": S("cover_sub",
        fontSize=13, textColor=LIGHT_BLUE, alignment=TA_CENTER,
        fontName="Helvetica", spaceAfter=5),
    "cover_meta": S("cover_meta",
        fontSize=10, textColor=ACCENT, alignment=TA_CENTER,
        fontName="Helvetica", spaceAfter=3),
    "sec_label": S("sec_label",
        fontSize=12, textColor=WHITE, fontName="Helvetica-Bold",
        spaceBefore=0, spaceAfter=0),
    "file_title": S("file_title",
        fontSize=11, textColor=DARK_BLUE, fontName="Helvetica-Bold",
        spaceBefore=4, spaceAfter=3),
    "body": S("body",
        fontSize=9.5, textColor=DARK_TEXT, fontName="Helvetica",
        leading=15, spaceAfter=5, alignment=TA_JUSTIFY),
    "bullet": S("bullet",
        fontSize=9.5, textColor=DARK_TEXT, fontName="Helvetica",
        leading=14, spaceAfter=3, leftIndent=16, bulletIndent=4),
    "sub_bullet": S("sub_bullet",
        fontSize=9, textColor=DARK_TEXT, fontName="Helvetica",
        leading=13, spaceAfter=2, leftIndent=30, bulletIndent=4),
    "code": S("code",
        fontSize=8, textColor=DARK_BLUE, fontName="Courier",
        leading=12, spaceAfter=1, leftIndent=8),
    "caption": S("caption",
        fontSize=8, textColor=MUTED, fontName="Helvetica-Oblique",
        alignment=TA_CENTER, spaceAfter=4),
    "tag": S("tag",
        fontSize=8, textColor=MID_BLUE, fontName="Helvetica-Bold",
        spaceAfter=2),
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def section_bar(number, title):
    cell = Paragraph(f"  {number}.  {title}", styles["sec_label"])
    t = Table([[cell]], colWidths=[W - 3*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK_BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 0.25*cm)])


def file_header(filename, role):
    """Filename chip + one-line role description."""
    chip = Table([[Paragraph(f"  {filename}  ", styles["tag"])]],
                 colWidths=[len(filename)*0.22*cm + 0.6*cm])
    chip.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
    ]))
    return KeepTogether([
        chip,
        Spacer(1, 0.1*cm),
        Paragraph(f"<b>Role:</b> {role}", styles["body"]),
    ])


def code_block(lines):
    """Shaded code block."""
    rows = [[Paragraph(l, styles["code"])] for l in lines]
    t = Table(rows, colWidths=[W - 3*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), CODE_BG),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    return KeepTogether([t, Spacer(1, 0.2*cm)])


def on_first_page(canvas, doc):
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(MID_BLUE)
    canvas.rect(0, 0, W, 3*cm, fill=1, stroke=0)


def on_later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, H - 1.1*cm, W, 1.1*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(WHITE)
    canvas.drawString(1.5*cm, H - 0.72*cm, "CHART DIGITIZER")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W - 1.5*cm, H - 0.72*cm, "Code Explainer  ·  University of Naples Federico II")
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, W, 0.9*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(W/2, 0.32*cm, f"Page {doc.page}  ·  MSc Data Science  ·  Confidential")
    canvas.restoreState()


# ── Story ─────────────────────────────────────────────────────────────────────
story = []

# ── COVER ─────────────────────────────────────────────────────────────────────
story += [
    Spacer(1, 4*cm),
    Paragraph("Chart Digitizer", styles["cover_title"]),
    Spacer(1, 0.3*cm),
    Paragraph("Files, Scripts &amp; Code Explainer", styles["cover_sub"]),
    Spacer(1, 1.2*cm),
    HRFlowable(width="55%", thickness=1, color=MID_BLUE, hAlign="CENTER"),
    Spacer(1, 1.2*cm),
    Paragraph("University of Naples Federico II", styles["cover_meta"]),
    Paragraph("MSc Data Science", styles["cover_meta"]),
    Paragraph("Supervisor: Prof. Schiano Lo Moriello", styles["cover_meta"]),
    Spacer(1, 0.4*cm),
    Paragraph("June 2026", styles["cover_meta"]),
    PageBreak(),
]

# ── SECTION 1 — Project File Map ──────────────────────────────────────────────
story += [section_bar(1, "Project File Map")]

story.append(Paragraph(
    "The entire project lives inside the <font name='Courier'>chart_digitizer/</font> directory. "
    "Below is the complete file tree with a one-line description of every file.",
    styles["body"]))
story.append(Spacer(1, 0.15*cm))

tree = [
    ("chart_digitizer/",                     "Project root"),
    ("  ├── app.py",                         "Flask web server — REST API backend"),
    ("  ├── start.sh",                       "One-command local launch script"),
    ("  ├── Dockerfile",                     "Docker container definition for deployment"),
    ("  ├── requirements.txt",               "Python dependency list"),
    ("  ├── generate_explainer.py",          "Generates the technical explainer PDF"),
    ("  ├── generate_code_explainer.py",     "Generates this document"),
    ("  ├── pipeline/",                      ""),
    ("  │   └── pipeline.py",               "Core CV extraction pipeline"),
    ("  ├── synthetic/",                     ""),
    ("  │   ├── synthetic_pdf_generator.py","Generates synthetic test PDFs with ground truth"),
    ("  │   └── synthetic_generator.py",    "Legacy PNG-based chart generator"),
    ("  ├── tests/",                         ""),
    ("  │   └── evaluate_accuracy.py",      "Benchmarks pipeline output vs ground truth"),
    ("  └── frontend/",                      ""),
    ("      └── index.html",                "Drag-and-drop single-file web UI"),
]

tree_data = [[Paragraph(f"<font name='Courier'>{f}</font>", styles["code"]),
              Paragraph(d, styles["body"])] for f, d in tree]
tree_table = Table(tree_data, colWidths=[7.5*cm, 8.5*cm])
tree_table.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),(-1,-1), CODE_BG),
    ("TOPPADDING",    (0,0),(-1,-1), 3),
    ("BOTTOMPADDING", (0,0),(-1,-1), 3),
    ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ("LINEAFTER",     (0,0),(0,-1),  0.5, colors.HexColor("#cbd5e1")),
]))
story += [tree_table, Spacer(1, 0.5*cm)]


# ── SECTION 2 — synthetic_pdf_generator.py ───────────────────────────────────
story += [section_bar(2, "synthetic_pdf_generator.py")]
story += [
    file_header("synthetic/synthetic_pdf_generator.py",
                "Generates realistic AMS milking PDFs for pipeline testing, with embedded text and known ground truth."),
    Spacer(1, 0.2*cm),

    Paragraph("<b>Why this file exists</b>", styles["file_title"]),
    Paragraph(
        "Only one real PDF was provided by the company. To test and measure pipeline accuracy "
        "rigorously, we need PDFs where the exact curve coordinates are known in advance. "
        "This script generates an unlimited number of such PDFs.",
        styles["body"]),

    Paragraph("<b>Key design decision — Matplotlib PDF backend</b>", styles["file_title"]),
    Paragraph(
        "Matplotlib is normally used to render charts to screen or PNG. By switching its backend "
        "to <font name='Courier'>pdf</font>, it writes a real PDF with vector graphics and "
        "<b>embedded searchable text</b>. This means PyMuPDF can later extract the animal ID, "
        "date, and time directly — exactly as it does from the real company PDF.",
        styles["body"]),
]
story += [code_block([
    "import matplotlib",
    "matplotlib.use('pdf')   # switch to PDF backend before importing pyplot",
    "import matplotlib.pyplot as plt",
])]

story += [
    Paragraph("<b>Curve generators</b>", styles["file_title"]),
    Paragraph("<b>generate_flusso()</b> — milk flow rate (blue curve):", styles["bullet"]),
    Paragraph("Creates a bell-shaped curve: rises quickly to a peak, holds briefly, then falls to zero. "
              "Peak height, timing, and fall width are randomised. A taper function forces the curve to "
              "zero at the start and after the session duration. Gaussian noise is added for realism.",
              styles["sub_bullet"]),
    Paragraph("<b>generate_pressione()</b> — vacuum pressure (green curve):", styles["bullet"]),
    Paragraph("Creates a plateau curve: rises steeply from zero, holds at a high value (~7–9), "
              "then drops sharply at the end of the session. Ripple noise added throughout.",
              styles["sub_bullet"]),
    Paragraph("Both functions support a <font name='Courier'>flat=True</font> mode for edge-case "
              "testing (dry cows or unit-off scenarios).", styles["bullet"]),

    Spacer(1, 0.2*cm),
    Paragraph("<b>render_chart()</b>", styles["file_title"]),
    Paragraph(
        "Draws one chart onto a Matplotlib Axes object. The critical detail is how the header "
        "text is placed. Two <font name='Courier'>ax.annotate()</font> calls are used with "
        "<font name='Courier'>xycoords='axes fraction'</font> — this anchors text relative to "
        "the axes box, so it always appears just above the top spine regardless of which grid "
        "row the chart occupies.",
        styles["body"]),
]
story += [code_block([
    "ax.annotate('Numero Azienda 07010142    Animale: 1001  ...',",
    "    xy=(0, 1), xycoords='axes fraction',",
    "    xytext=(0, 12), textcoords='offset points',",
    "    fontsize=5, family='monospace')",
])]

story += [
    Paragraph("<b>Three scenarios</b>", styles["file_title"]),
]
scen_data = [
    ["Scenario", "Pages", "Charts", "What it tests"],
    ["baseline",  "1", "8",  "Normal sessions — happy path"],
    ["multipage", "3", "24", "Multi-page iteration + CSV filename collision handling"],
    ["edge",      "2", "16", "Flat curves, short sessions, duplicate animal IDs"],
]
scen_t = Table(scen_data, colWidths=[3*cm, 1.5*cm, 1.8*cm, 9.7*cm])
scen_t.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),(-1,0),  DARK_BLUE),
    ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
    ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
    ("FONTSIZE",      (0,0),(-1,-1), 9),
    ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_BLUE]),
    ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",    (0,0),(-1,-1), 5),
    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ("ALIGN",         (1,0),(2,-1),  "CENTER"),
]))
story += [scen_t, Spacer(1, 0.3*cm),
          Paragraph(
              "<b>Ground truth output:</b> a <font name='Courier'>ground_truth.json</font> file "
              "is saved alongside the PDFs. It contains the exact (time, value) arrays for every "
              "curve on every chart — used by the accuracy evaluator.",
              styles["body"]),
          Spacer(1, 0.4*cm)]


# ── SECTION 3 — synthetic_generator.py ───────────────────────────────────────
story += [section_bar(3, "synthetic_generator.py")]
story += [
    file_header("synthetic/synthetic_generator.py",
                "Legacy PNG-based chart generator. Kept for visual inspection and backwards compatibility."),
    Spacer(1, 0.2*cm),
    Paragraph(
        "This was the first generator built. It uses the same curve generation logic but renders "
        "to PNG instead of PDF. Because PNGs have no embedded text, the pipeline must use "
        "Tesseract OCR to read metadata — which is slower and less reliable than native text "
        "extraction. The PDF generator supersedes this for all testing purposes, but the PNG "
        "generator remains useful for quickly previewing what synthetic charts look like.",
        styles["body"]),
    Paragraph(
        "Usage: <font name='Courier'>python synthetic_generator.py --pages 2 --out ./output --seed 42</font>",
        styles["body"]),
    Spacer(1, 0.4*cm),
]


# ── SECTION 4 — pipeline.py ───────────────────────────────────────────────────
story += [section_bar(4, "pipeline/pipeline.py")]
story += [
    file_header("pipeline/pipeline.py",
                "The core of the project. Extracts Flusso and Pressione curve data from every chart in a PDF or image."),
    Spacer(1, 0.2*cm),
    Paragraph(
        "This file contains eight distinct functional components, each handling one step of the "
        "extraction pipeline. They are called in sequence by the top-level "
        "<font name='Courier'>run_pipeline()</font> function.",
        styles["body"]),
    Spacer(1, 0.15*cm),
]

components = [
    ("load_pages()",
     "Input handler.",
     "Accepts a file path. If the file is a PDF, PyMuPDF rasterises each page to a BGR "
     "image at 150 DPI. If the file is a PNG or JPEG, OpenCV loads it directly. Returns "
     "a list of NumPy arrays — one per page."),

    ("extract_metadata_from_pdf_page()",
     "Native PDF text extraction — no OCR.",
     "Calls PyMuPDF's get_text('blocks') to retrieve all text blocks with their bounding "
     "box coordinates. Scans for blocks containing 'Animale:' and merges them with nearby "
     "blocks to capture 'Data:' and 'Ora:' (which sometimes appear in a separate block). "
     "Sorts results by Y-then-X position to match the grid order. Returns 8 metadata dicts."),

    ("slice_page_with_pdf_boundaries()",
     "Accurate cell slicing using PDF text positions.",
     "Instead of dividing the page into equal-height rows (which fails when chart heights "
     "vary), this function uses the actual Y coordinates of the embedded header text to "
     "find where each row starts. It then cuts the page into 8 cells — 4 rows x 2 columns. "
     "Falls back to equal-height slicing for PNG inputs."),

    ("detect_plot_area()",
     "Axis frame detection.",
     "Binarises the chart cell and uses morphological kernels to detect long horizontal and "
     "vertical lines. The innermost detected lines define the plot area bounding box: "
     "x_left, x_right, y_top, y_bottom. These pixel coordinates are passed to AxisTransform."),

    ("AxisTransform class",
     "Pixel-to-data coordinate mapping.",
     "A simple class initialised with the plot area pixel bounds and the known data ranges "
     "(X: 0-10 min, Y: 0-9 for both axes). The px_to_data() method applies linear "
     "interpolation. Y is inverted because image coordinates increase downward while data "
     "Y increases upward."),

    ("extract_curve_pixels()",
     "HSV colour isolation.",
     "Converts the plot region from BGR to HSV colour space, then applies cv2.inRange() "
     "with tuned HSV bounds for blue (Flusso) and green (Pressione). Morphological "
     "open-then-close cleans up noise. Returns pixel (x,y) coordinates of the curve."),

    ("pixels_to_curve()",
     "Pixel cloud to ordered curve.",
     "For each X column in the pixel cloud, takes the median Y value — robust to "
     "anti-aliasing where a curve spans 2-3 pixels vertically. Interpolates across "
     "columns where no pixel was detected. Samples 300 evenly-spaced points and maps "
     "each through AxisTransform to get (time_min, value) pairs. Curves are anchored "
     "to the plot origin (0, 0), and the flow curve is extended flat to the session "
     "end once it has returned to the axis — recovering segments drawn over the "
     "black axis lines that the colour mask cannot see."),

    ("process_chart()",
     "Single-chart orchestrator.",
     "Calls detect_plot_area, AxisTransform, extract_curve_pixels, and pixels_to_curve "
     "for one cell. Combines both curves into a Pandas DataFrame and writes the CSV. "
     "Uses metadata from the PDF text extraction (or OCR fallback). Handles filename "
     "collisions by appending a time suffix."),

    ("run_pipeline()",
     "Top-level entry point.",
     "Iterates over pages. For PDF inputs: calls extract_metadata_from_pdf_page and "
     "slice_page_with_pdf_boundaries. For image inputs: calls ocr_full_page and "
     "slice_page_into_charts. Then calls process_chart for each of the 8 cells per page."),
]

for name, role, detail in components:
    row_data = [
        [Paragraph(f"<font name='Courier'><b>{name}</b></font>", styles["body"]),
         Paragraph(f"<i>{role}</i>", styles["body"])],
        [Paragraph(detail, styles["body"]), ""],
    ]
    t = Table(row_data, colWidths=[4.5*cm, 11.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  LIGHT_BLUE),
        ("BACKGROUND",    (0,1),(-1,1),  CODE_BG),
        ("SPAN",          (0,1),(-1,1)),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story += [t, Spacer(1, 0.18*cm)]

story.append(Spacer(1, 0.3*cm))


# ── SECTION 5 — evaluate_accuracy.py ─────────────────────────────────────────
story += [section_bar(5, "tests/evaluate_accuracy.py")]
story += [
    file_header("tests/evaluate_accuracy.py",
                "Benchmarks the pipeline's output against synthetic ground truth. Produces a quantitative accuracy report."),
    Spacer(1, 0.2*cm),
    Paragraph("<b>How it works:</b>", styles["file_title"]),
    Paragraph(
        "Loads <font name='Courier'>ground_truth.json</font> produced by the synthetic PDF generator. "
        "For each chart, finds the matching CSV by animal ID and date. Then for each curve:",
        styles["body"]),
    Paragraph("1. Takes the ground truth (time, value) arrays from JSON.", styles["bullet"]),
    Paragraph("2. Takes the pipeline's extracted (time, value) arrays from CSV.", styles["bullet"]),
    Paragraph("3. Interpolates the ground truth at the pipeline's time points using "
              "<font name='Courier'>np.interp()</font>.", styles["bullet"]),
    Paragraph("4. Computes MAE = mean(|predicted - ground_truth|).", styles["bullet"]),
    Paragraph("5. Computes coverage = (t_max - t_min) / (gt_t_max - gt_t_min).", styles["bullet"]),
    Spacer(1, 0.2*cm),
    Paragraph("<b>Metrics reported:</b>", styles["file_title"]),
    Paragraph("• Detection rate — how many charts had both curves successfully extracted", styles["bullet"]),
    Paragraph("• MAE mean, median, and max — for both Flusso and Pressione independently", styles["bullet"]),
    Paragraph("• Coverage mean — what fraction of the X-axis was captured", styles["bullet"]),
    Spacer(1, 0.2*cm),
    Paragraph("<b>Results on 48 synthetic charts (6 pages, 3 PDFs):</b>", styles["file_title"]),
]

acc_data = [
    ["Metric",                    "Flusso",           "Pressione"],
    ["Detection rate",            "100%",             "100%"],
    ["MAE — median",              "0.07 kg/min",      "0.12 × 0.1 bar"],
    ["MAE — mean",                "0.44 kg/min",      "0.27 × 0.1 bar"],
    ["Coverage — mean",           "98.8%",            "99.3%"],
    ["Warnings",                  "0",                "0"],
]
acc_t = Table(acc_data, colWidths=[6*cm, 5*cm, 5*cm])
acc_t.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),(-1,0),  DARK_BLUE),
    ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
    ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
    ("FONTSIZE",      (0,0),(-1,-1), 9),
    ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GREEN]),
    ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",    (0,0),(-1,-1), 5),
    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ("ALIGN",         (1,0),(-1,-1), "CENTER"),
]))
story += [acc_t, Spacer(1, 0.4*cm)]


# ── SECTION 6 — app.py ────────────────────────────────────────────────────────
story += [section_bar(6, "app.py")]
story += [
    file_header("app.py",
                "Flask web server. Wraps the pipeline in a REST API so it can be driven from a browser."),
    Spacer(1, 0.2*cm),
    Paragraph("<b>Job model</b>", styles["file_title"]),
    Paragraph(
        "Each upload creates a job with a unique UUID. Jobs are stored in a Python dict in memory. "
        "The pipeline runs in a <b>background thread</b> so the HTTP response returns immediately "
        "and the browser can poll for progress.",
        styles["body"]),

    Paragraph("<b>API endpoints</b>", styles["file_title"]),
]

endpoints = [
    ("POST /upload",              "Save the uploaded PDF/PNG, create a job ID, start pipeline in background thread, return job ID."),
    ("GET  /status/<job_id>",     "Return job status (queued/running/done/error), list of output CSV filenames, and any warnings."),
    ("GET  /download/<id>/<file>","Stream a single CSV file to the browser as a download."),
    ("GET  /download-all/<id>",   "Zip all CSVs for a job and stream the ZIP archive."),
    ("GET  /",                    "Serve index.html (the frontend)."),
]
ep_data = [[Paragraph(f"<font name='Courier'>{e}</font>", styles["code"]),
            Paragraph(d, styles["body"])] for e, d in endpoints]
ep_t = Table(ep_data, colWidths=[5.5*cm, 10.5*cm])
ep_t.setStyle(TableStyle([
    ("ROWBACKGROUNDS",(0,0),(-1,-1), [WHITE, CODE_BG]),
    ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",    (0,0),(-1,-1), 5),
    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
]))
story += [ep_t, Spacer(1, 0.4*cm)]


# ── SECTION 7 — frontend/index.html ──────────────────────────────────────────
story += [section_bar(7, "frontend/index.html")]
story += [
    file_header("frontend/index.html",
                "The entire user interface in a single file. No framework, no build step, no dependencies."),
    Spacer(1, 0.2*cm),
    Paragraph("<b>UI flow — step by step:</b>", styles["file_title"]),
    Paragraph("1. User drops a PDF onto the drop zone or clicks to browse.", styles["bullet"]),
    Paragraph("2. Clicking <b>Run Extraction</b> sends a multipart POST to <font name='Courier'>/upload</font>.", styles["bullet"]),
    Paragraph("3. JavaScript receives the job ID and starts polling "
              "<font name='Courier'>/status/&lt;job_id&gt;</font> every 1.2 seconds.", styles["bullet"]),
    Paragraph("4. A progress bar animates between 15% and 85% while the pipeline is running.", styles["bullet"]),
    Paragraph("5. When status is <font name='Courier'>done</font>, the file list is rendered — "
              "one download link per CSV plus a Download all as ZIP button.", styles["bullet"]),
    Paragraph("6. Any pipeline warnings (e.g. OCR fallback) appear in an amber box below.", styles["bullet"]),
    Spacer(1, 0.2*cm),
    Paragraph(
        "The entire UI is ~250 lines of vanilla HTML/CSS/JS. No React, no Vue, no npm. "
        "This keeps the project dependency-free on the frontend and trivially portable.",
        styles["body"]),
    Spacer(1, 0.4*cm),
]


# ── SECTION 8 — start.sh & Dockerfile ────────────────────────────────────────
story += [section_bar(8, "start.sh  &  Dockerfile")]
story += [
    file_header("start.sh",
                "One-command local launch script for development use."),
    Spacer(1, 0.1*cm),
    Paragraph(
        "Activates the Python virtual environment if present, then starts Flask on port 5001. "
        "Port 5001 is used instead of 5000 to avoid conflict with macOS AirPlay Receiver "
        "which occupies port 5000 by default.",
        styles["body"]),
]
story += [code_block([
    "#!/bin/bash",
    "PORT=${1:-5001}",
    "source ../venv/bin/activate",
    "echo 'Open your browser at: http://localhost:$PORT'",
    "PORT=$PORT python3 app.py",
])]

story += [
    Spacer(1, 0.2*cm),
    file_header("Dockerfile",
                "Defines the production container for self-hosted deployment on the farm's network."),
    Spacer(1, 0.1*cm),
    Paragraph(
        "Uses <font name='Courier'>python:3.11-slim</font> as base. Installs Tesseract OCR at "
        "the system level (required for PNG fallback), then installs all Python dependencies. "
        "Exposes port 5000 and runs <font name='Courier'>python app.py</font> on container start.",
        styles["body"]),
]
story += [code_block([
    "FROM python:3.11-slim",
    "RUN apt-get update && apt-get install -y tesseract-ocr libgl1 libglib2.0-0",
    "WORKDIR /app",
    "COPY requirements.txt .",
    "RUN pip install --no-cache-dir -r requirements.txt",
    "COPY . .",
    "EXPOSE 5000",
    "CMD [\"python\", \"app.py\"]",
])]
story.append(Spacer(1, 0.4*cm))


# ── SECTION 9 — How it all connects ──────────────────────────────────────────
story += [section_bar(9, "How All Files Connect")]
story += [
    Paragraph(
        "The diagram below shows how data flows through the system from a user uploading "
        "a PDF to receiving CSV files in their browser.",
        styles["body"]),
    Spacer(1, 0.2*cm),
]

flow = [
    ["User (browser)", "→", "frontend/index.html"],
    ["frontend/index.html", "→", "POST /upload  (app.py)"],
    ["app.py", "→", "pipeline/pipeline.py  (background thread)"],
    ["pipeline.py", "→", "PyMuPDF  (text extraction + rasterisation)"],
    ["pipeline.py", "→", "OpenCV  (cell slicing + colour isolation)"],
    ["pipeline.py", "→", "NumPy  (coordinate mapping)"],
    ["pipeline.py", "→", "Pandas  (CSV write)"],
    ["app.py", "→", "GET /status  →  frontend shows file list"],
    ["frontend", "→", "GET /download  →  CSV saved to user's machine"],
]

flow_data = [[
    Paragraph(f"<font name='Courier'>{a}</font>", styles["code"]),
    Paragraph(b, styles["body"]),
    Paragraph(f"<font name='Courier'>{c}</font>", styles["code"]),
] for a, b, c in flow]

flow_t = Table(flow_data, colWidths=[5.2*cm, 1.2*cm, 9.6*cm])
flow_t.setStyle(TableStyle([
    ("ROWBACKGROUNDS",(0,0),(-1,-1), [WHITE, CODE_BG]),
    ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",    (0,0),(-1,-1), 4),
    ("BOTTOMPADDING", (0,0),(-1,-1), 4),
    ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ("ALIGN",         (1,0),(1,-1),  "CENTER"),
    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
]))
story += [flow_t, Spacer(1, 0.4*cm)]


# ── BUILD ─────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT,
    pagesize=A4,
    leftMargin=1.5*cm, rightMargin=1.5*cm,
    topMargin=1.8*cm,  bottomMargin=1.5*cm,
    title="Chart Digitizer — Code Explainer",
    author="University of Naples Federico II",
    subject="MSc Data Science Thesis",
)
doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
print(f"PDF saved → {OUT}")
