"""
generate_explainer.py
Generates the Chart Digitizer technical explainer PDF.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus import PageBreak

OUT = "/Users/dawarhasnain/Desktop/Thesis Work/chart_digitizer/Chart_Digitizer_Explainer.pdf"

# ── Colours ──────────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1a3a5c")
MID_BLUE    = colors.HexColor("#2563eb")
LIGHT_BLUE  = colors.HexColor("#dbeafe")
ACCENT      = colors.HexColor("#e2e8f0")
WHITE       = colors.white
DARK_TEXT   = colors.HexColor("#1e293b")
MUTED       = colors.HexColor("#64748b")
SUCCESS     = colors.HexColor("#16a34a")
LIGHT_GREEN = colors.HexColor("#dcfce7")

W, H = A4

# ── Styles ───────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def style(name, parent="Normal", **kw):
    s = ParagraphStyle(name, parent=base[parent], **kw)
    return s

S = {
    "cover_title": style("cover_title",
        fontSize=28, textColor=WHITE, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceAfter=8),
    "cover_sub": style("cover_sub",
        fontSize=14, textColor=LIGHT_BLUE, alignment=TA_CENTER,
        fontName="Helvetica", spaceAfter=6),
    "cover_meta": style("cover_meta",
        fontSize=10, textColor=ACCENT, alignment=TA_CENTER,
        fontName="Helvetica"),
    "section": style("section",
        fontSize=13, textColor=WHITE, fontName="Helvetica-Bold",
        spaceBefore=2, spaceAfter=2),
    "body": style("body",
        fontSize=9.5, textColor=DARK_TEXT, fontName="Helvetica",
        leading=15, spaceAfter=6, alignment=TA_JUSTIFY),
    "bullet": style("bullet",
        fontSize=9.5, textColor=DARK_TEXT, fontName="Helvetica",
        leading=14, spaceAfter=3, leftIndent=14,
        bulletIndent=4),
    "code": style("code",
        fontSize=8.5, textColor=DARK_BLUE, fontName="Courier",
        leading=13, spaceAfter=2, leftIndent=10),
    "caption": style("caption",
        fontSize=8, textColor=MUTED, fontName="Helvetica-Oblique",
        alignment=TA_CENTER, spaceAfter=4),
    "footer_text": style("footer_text",
        fontSize=7.5, textColor=MUTED, fontName="Helvetica",
        alignment=TA_CENTER),
}


# ── Header / Footer ──────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # Top bar
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, H - 1.1*cm, W, 1.1*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(WHITE)
    canvas.drawString(1.5*cm, H - 0.72*cm, "CHART DIGITIZER")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W - 1.5*cm, H - 0.72*cm,
        "Technical Explainer  ·  University of Naples Federico II")

    # Bottom bar
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, W, 0.9*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(W/2, 0.32*cm,
        f"Page {doc.page}  ·  Confidential — MSc Data Science Thesis")
    canvas.restoreState()

def on_first_page(canvas, doc):
    # Solid dark-blue cover background
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Accent strip at bottom of cover
    canvas.setFillColor(MID_BLUE)
    canvas.rect(0, 0, W, 3.5*cm, fill=1, stroke=0)


# ── Section header helper ─────────────────────────────────────────────────────
def section_header(number, title):
    """Returns a KeepTogether block: coloured bar + title."""
    bar = Table([[Paragraph(f"  {number}. {title}", S["section"])]],
                colWidths=[W - 3*cm])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK_BLUE),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return KeepTogether([bar, Spacer(1, 0.3*cm)])


# ── Build story ──────────────────────────────────────────────────────────────
story = []

# ── COVER PAGE ───────────────────────────────────────────────────────────────
story += [
    Spacer(1, 4.5*cm),
    Paragraph("Chart Digitizer", S["cover_title"]),
    Spacer(1, 0.3*cm),
    Paragraph("Automated Milking Session Data Extraction System", S["cover_sub"]),
    Spacer(1, 1.2*cm),
    HRFlowable(width="60%", thickness=1, color=MID_BLUE, hAlign="CENTER"),
    Spacer(1, 1.2*cm),
    Paragraph("Technical Explainer", S["cover_meta"]),
    Spacer(1, 0.4*cm),
    Paragraph("University of Naples Federico II", S["cover_meta"]),
    Paragraph("MSc Data Science", S["cover_meta"]),
    Spacer(1, 0.3*cm),
    Paragraph("Supervisor: Prof. Schiano Lo Moriello", S["cover_meta"]),
    Spacer(1, 0.5*cm),
    Paragraph("June 2026", S["cover_meta"]),
    PageBreak(),
]

# ── SECTION 1 — Project Overview ─────────────────────────────────────────────
story += [
    section_header(1, "Project Overview"),
    Paragraph(
        "Chart Digitizer is an offline web application that automatically extracts "
        "curve data from Automated Milking System (AMS) PDF reports produced by a "
        "farming company. The system eliminates manual transcription of milking data, "
        "enabling direct digital analysis of milk flow and vacuum pressure measurements "
        "for each animal session.",
        S["body"]),
    Spacer(1, 0.2*cm),
    Paragraph("Each PDF page contains <b>8 charts</b> arranged in a fixed 2-column × 4-row grid. "
              "Each chart represents one milking session for one animal and displays two curves:",
              S["body"]),
    Paragraph("• <b>Flusso</b> (blue) — milk flow rate in kg/min, Y-axis 0–9", S["bullet"]),
    Paragraph("• <b>Pressione assoluta</b> (green) — absolute vacuum pressure in 0.1 bar, Y-axis 0–9", S["bullet"]),
    Paragraph("• <b>X-axis</b> — milking duration in minutes, range 0–10", S["bullet"]),
    Spacer(1, 0.3*cm),
    Paragraph(
        "The pipeline outputs <b>one CSV file per chart</b>, named by animal ID and session date. "
        "Example: <font name='Courier'>animal_1001_2024-03-07.csv</font>. "
        "When two sessions for the same animal occur on the same date, a time suffix is appended: "
        "<font name='Courier'>animal_948_2024-03-07_0500.csv</font>.",
        S["body"]),

    Spacer(1, 0.4*cm),
]

# ── SECTION 2 — System Architecture ─────────────────────────────────────────
story += [
    section_header(2, "System Architecture"),
    Paragraph(
        "The system uses a <b>classical Computer Vision pipeline</b> rather than deep learning. "
        "This decision was made because the PDF format is fixed and consistent, no large labeled "
        "dataset is available or required, the pipeline is fully explainable (satisfying academic "
        "requirements), and it runs entirely offline with zero internet dependency.",
        S["body"]),

    Spacer(1, 0.25*cm),
    Paragraph("<b>Pipeline Steps</b>", S["body"]),
    Paragraph("1. <b>PDF Rasterisation</b> — PyMuPDF converts each PDF page to a high-resolution "
              "bitmap image at 150 DPI for image processing.", S["bullet"]),
    Paragraph("2. <b>Native Text Extraction</b> — PyMuPDF reads embedded text directly from the PDF "
              "(no OCR needed for real PDFs). Chart headers containing animal ID, date, and time are "
              "extracted with exact bounding-box positions.", S["bullet"]),
    Paragraph("3. <b>Accurate Cell Slicing</b> — Row boundaries are derived from the Y-coordinates "
              "of embedded text blocks, ensuring correct alignment even when chart heights vary. "
              "Each page is sliced into 8 individual chart cells.", S["bullet"]),
    Paragraph("4. <b>Per-Chart Processing</b> — For each cell: axis calibration via line detection, "
              "HSV colour isolation (blue channel for Flusso, green for Pressione), column-by-column "
              "pixel extraction, and coordinate mapping from pixel space to data space.", S["bullet"]),
    Paragraph("5. <b>CSV Export</b> — Pandas writes the extracted (time, value) pairs to a "
              "named CSV file. Two rows per time point: one for each curve.", S["bullet"]),

    Spacer(1, 0.3*cm),
    Paragraph("<b>Deployment Architecture</b>", S["body"]),
    Paragraph(
        "The system is packaged as a <b>self-hosted web application</b>. A Flask Python backend "
        "exposes a REST API; a lightweight HTML/CSS/JS frontend provides a drag-and-drop interface. "
        "The entire stack runs in a Docker container on a machine within the farm's local network. "
        "Farm staff visit a local URL (e.g. http://milking.local) from any browser on the network — "
        "no installation required, and no data leaves the premises.",
        S["body"]),

    Spacer(1, 0.4*cm),
]

# ── SECTION 3 — Tech Stack ───────────────────────────────────────────────────
story += [
    section_header(3, "Technology Stack"),
    Spacer(1, 0.1*cm),
]

stack_data = [
    ["Layer", "Tool / Library"],
    ["PDF Rasterisation",       "PyMuPDF (fitz)"],
    ["Metadata Extraction",     "PyMuPDF native text — no OCR for real PDFs"],
    ["Image Processing",        "OpenCV (opencv-python)"],
    ["OCR Fallback",            "Tesseract + pytesseract (PNG inputs)"],
    ["Coordinate Mathematics",  "NumPy"],
    ["CSV Export",              "Pandas"],
    ["Synthetic Chart Generation", "Matplotlib (PDF backend — embedded text)"],
    ["Web Backend",             "Python Flask"],
    ["Frontend",                "HTML / CSS / Vanilla JavaScript"],
    ["Containerisation",        "Docker"],
]

stack_table = Table(stack_data, colWidths=[6.2*cm, 9.8*cm])
stack_table.setStyle(TableStyle([
    ("BACKGROUND",   (0,0), (-1,0),  DARK_BLUE),
    ("TEXTCOLOR",    (0,0), (-1,0),  WHITE),
    ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
    ("FONTSIZE",     (0,0), (-1,-1), 9),
    ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_BLUE]),
    ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("LEFTPADDING",  (0,0), (-1,-1), 8),
]))
story += [stack_table, Spacer(1, 0.4*cm)]


# ── SECTION 4 — Accuracy Results ─────────────────────────────────────────────
story += [
    section_header(4, "Accuracy Results"),
    Paragraph(
        "The pipeline was validated against synthetic PDFs generated with a known ground truth. "
        "Synthetic charts mimic the real company PDF format exactly — same layout, embedded text "
        "headers, axis ranges, and curve shapes — allowing quantitative accuracy measurement. "
        "Every extracted curve is anchored at the plot origin (t = 0, value 0); the flow curve's "
        "return to zero is likewise extended to the end of the session window, recovering the "
        "segments that are drawn over the black axis lines and invisible to colour masking.",
        S["body"]),
    Spacer(1, 0.2*cm),
]

acc_data = [
    ["Metric",                          "Result"],
    ["Charts extracted",                "48 / 48  (100%)"],
    ["Warnings",                        "0"],
    ["Flusso MAE — median",             "0.11 kg/min"],
    ["Flusso MAE — mean",               "0.12 kg/min"],
    ["Pressione MAE — median",          "0.20 × 0.1 bar"],
    ["Pressione MAE — mean",            "0.19 × 0.1 bar"],
    ["Flusso curve coverage",           "100.0 %"],
    ["Pressione curve coverage",        "98.4 %"],
]

acc_table = Table(acc_data, colWidths=[8*cm, 8*cm])
acc_table.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0),  DARK_BLUE),
    ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
    ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
    ("FONTSIZE",      (0,0), (-1,-1), 9),
    ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_GREEN]),
    ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 8),
]))
story += [acc_table, Spacer(1, 0.2*cm),
          Paragraph("MAE = Mean Absolute Error versus known ground-truth coordinates.", S["caption"]),
          Spacer(1, 0.3*cm)]


# ── SECTION 5 — Test Suite ───────────────────────────────────────────────────
story += [
    section_header(5, "Test Suite"),
    Paragraph(
        "Three synthetic PDF scenarios are generated by "
        "<font name='Courier'>synthetic_pdf_generator.py</font>, each with an accompanying "
        "JSON ground truth file containing exact curve coordinates:",
        S["body"]),
    Spacer(1, 0.15*cm),
]

test_data = [
    ["File",                        "Pages", "Charts", "Purpose"],
    ["synthetic_1_baseline.pdf",    "1",     "8",
     "Happy-path validation — normal sessions, typical curve shapes"],
    ["synthetic_2_multipage.pdf",   "3",     "24",
     "Multi-page iteration and CSV collision handling (time suffix)"],
    ["synthetic_3_edge.pdf",        "2",     "16",
     "Edge cases: flat curves, short sessions, duplicate animal IDs"],
    ["Total",                       "6",     "48", ""],
]

test_table = Table(test_data, colWidths=[5.2*cm, 1.4*cm, 1.6*cm, 7.8*cm])
test_table.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0),  DARK_BLUE),
    ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
    ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
    ("FONTSIZE",      (0,0), (-1,-1), 8.5),
    ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_BLUE]),
    ("BACKGROUND",    (0,-1),(-1,-1), ACCENT),
    ("FONTNAME",      (0,-1),(-1,-1), "Helvetica-Bold"),
    ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ("ALIGN",         (1,0), (2,-1),  "CENTER"),
]))
story += [test_table, Spacer(1, 0.4*cm)]


# ── SECTION 6 — Deployment ───────────────────────────────────────────────────
story += [
    section_header(6, "Deployment"),
    Paragraph(
        "The system is designed for <b>self-hosted, offline deployment</b> on the farm's "
        "local network. Data privacy is guaranteed — no animal data leaves the premises.",
        S["body"]),
    Spacer(1, 0.15*cm),
    Paragraph("<b>Deployment flow:</b>", S["body"]),
    Paragraph("1. Docker container runs on a machine on the farm's network.", S["bullet"]),
    Paragraph("2. Farm staff open a browser and navigate to the assigned local URL "
              "(e.g. <font name='Courier'>http://milking.local</font> or the machine's IP).", S["bullet"]),
    Paragraph("3. User drags and drops the AMS PDF onto the upload area.", S["bullet"]),
    Paragraph("4. Pipeline runs server-side; progress is shown in real time.", S["bullet"]),
    Paragraph("5. CSV files appear as individual download links + a single ZIP download.", S["bullet"]),
    Spacer(1, 0.25*cm),
    Paragraph("<b>Local development access:</b>", S["body"]),
    Paragraph(
        "<font name='Courier'>http://localhost:5001</font> — launch with "
        "<font name='Courier'>./start.sh</font> from the project directory.",
        S["body"]),
    Spacer(1, 0.4*cm),
]


# ── SECTION 7 — File Structure ───────────────────────────────────────────────
story += [
    section_header(7, "Project File Structure"),
    Spacer(1, 0.1*cm),
]

files = [
    ("synthetic/synthetic_pdf_generator.py",
     "Generates synthetic test PDFs with embedded text and ground truth JSON"),
    ("synthetic/synthetic_generator.py",
     "Legacy PNG generator (used for image-only testing)"),
    ("pipeline/pipeline.py",
     "Full CV extraction pipeline — rasterisation, slicing, colour isolation, CSV export"),
    ("tests/evaluate_accuracy.py",
     "Benchmarks pipeline output against ground truth JSON, reports MAE and coverage"),
    ("app.py",
     "Flask web backend — upload, job queue, status polling, CSV download endpoints"),
    ("frontend/index.html",
     "Single-file drag-and-drop web UI with real-time progress and file list"),
    ("Dockerfile",
     "Docker container definition for self-hosted deployment"),
    ("start.sh",
     "One-command local launch script"),
]

file_data = [["File", "Purpose"]] + [[f, d] for f, d in files]
file_table = Table(file_data, colWidths=[6.8*cm, 9.2*cm])
file_table.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0),  DARK_BLUE),
    ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
    ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
    ("FONTSIZE",      (0,0), (-1,-1), 8.5),
    ("FONTNAME",      (0,1), (0,-1),  "Courier"),
    ("FONTNAME",      (1,1), (1,-1),  "Helvetica"),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_BLUE]),
    ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
]))
story += [file_table, Spacer(1, 0.4*cm)]


# ── SECTION 8 — CSV Output Format ────────────────────────────────────────────
story += [
    section_header(8, "CSV Output Format"),
    Paragraph(
        "Each output CSV contains three columns. Rows are interleaved for both curves:",
        S["body"]),
    Spacer(1, 0.1*cm),
    Paragraph("curve,time_min,value", S["code"]),
    Paragraph("Flusso_kg_min,0.043,0.000", S["code"]),
    Paragraph("Flusso_kg_min,0.115,0.177", S["code"]),
    Paragraph("Pressione_assoluta_0.1bar,0.115,9.000", S["code"]),
    Paragraph("Pressione_assoluta_0.1bar,0.231,8.943", S["code"]),
    Spacer(1, 0.2*cm),
    Paragraph(
        "<b>Filename convention:</b> <font name='Courier'>animal_{ID}_{YYYY-MM-DD}.csv</font>  "
        "— or with time suffix if the same animal has multiple sessions on the same date: "
        "<font name='Courier'>animal_{ID}_{YYYY-MM-DD}_{HHMM}.csv</font>",
        S["body"]),
    Spacer(1, 0.5*cm),
]


# ── BUILD ─────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT,
    pagesize=A4,
    leftMargin=1.5*cm,
    rightMargin=1.5*cm,
    topMargin=1.8*cm,
    bottomMargin=1.5*cm,
    title="Chart Digitizer — Technical Explainer",
    author="University of Naples Federico II",
    subject="MSc Data Science Thesis",
)

doc.build(
    story,
    onFirstPage=on_first_page,
    onLaterPages=on_page,
)
print(f"PDF saved → {OUT}")
