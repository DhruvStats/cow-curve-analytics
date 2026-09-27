"""
generate_howto_guide.py
Generates HOW_TO_RUN.pdf — a step-by-step guide for running and testing
Chart Digitizer from a fresh copy of this package. Matches the visual
style of generate_explainer.py.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, PageBreak
)
from pathlib import Path

OUT = str(Path(__file__).parent / "HOW_TO_RUN.pdf")

# ── Colours (same palette as the technical explainer) ────────────────────────
DARK_BLUE   = colors.HexColor("#1a3a5c")
MID_BLUE    = colors.HexColor("#2563eb")
LIGHT_BLUE  = colors.HexColor("#dbeafe")
ACCENT      = colors.HexColor("#e2e8f0")
WHITE       = colors.white
DARK_TEXT   = colors.HexColor("#1e293b")
MUTED       = colors.HexColor("#64748b")
LIGHT_GREEN = colors.HexColor("#dcfce7")
CODE_BG     = colors.HexColor("#f1f5f9")

W, H = A4
base = getSampleStyleSheet()

def style(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

S = {
    "cover_title": style("cover_title", fontSize=28, textColor=WHITE,
        alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=8),
    "cover_sub": style("cover_sub", fontSize=14, textColor=LIGHT_BLUE,
        alignment=TA_CENTER, fontName="Helvetica", spaceAfter=6),
    "cover_meta": style("cover_meta", fontSize=10, textColor=ACCENT,
        alignment=TA_CENTER, fontName="Helvetica"),
    "section": style("section", fontSize=13, textColor=WHITE,
        fontName="Helvetica-Bold", spaceBefore=2, spaceAfter=2),
    "body": style("body", fontSize=9.5, textColor=DARK_TEXT,
        fontName="Helvetica", leading=15, spaceAfter=6, alignment=TA_JUSTIFY),
    "step": style("step", fontSize=9.5, textColor=DARK_TEXT,
        fontName="Helvetica", leading=15, spaceAfter=3, leftIndent=14),
    "code": style("code", fontSize=8.5, textColor=DARK_BLUE,
        fontName="Courier", leading=13),
    "caption": style("caption", fontSize=8, textColor=MUTED,
        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=4),
}


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, H - 1.1*cm, W, 1.1*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(WHITE)
    canvas.drawString(1.5*cm, H - 0.72*cm, "CHART DIGITIZER")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W - 1.5*cm, H - 0.72*cm,
        "How-To Guide  ·  University of Naples Federico II")
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, W, 0.9*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(W/2, 0.32*cm,
        f"Page {doc.page}  ·  Confidential — MSc Data Science Thesis")
    canvas.restoreState()

def on_first_page(canvas, doc):
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(MID_BLUE)
    canvas.rect(0, 0, W, 3.5*cm, fill=1, stroke=0)


def section_header(number, title):
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


def code_block(lines):
    rows = [[Paragraph(l.replace(" ", "&nbsp;"), S["code"])] for l in lines]
    t = Table(rows, colWidths=[W - 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), CODE_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("LINEBEFORE",    (0,0), (0,-1), 2, MID_BLUE),
    ]))
    return KeepTogether([t, Spacer(1, 0.25*cm)])


def styled_table(data, col_widths):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  DARK_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, colors.HexColor("#f8fafc")]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


story = []

# ── Cover ────────────────────────────────────────────────────────────────────
story += [
    Spacer(1, 7.5*cm),
    Paragraph("Chart Digitizer", S["cover_title"]),
    Paragraph("How to Run &amp; Test — Step-by-Step Guide", S["cover_sub"]),
    Spacer(1, 1.2*cm),
    Paragraph("University of Naples Federico II<br/>MSc Data Science", S["cover_meta"]),
    Spacer(1, 0.4*cm),
    Paragraph("Supervisor: Prof. Schiano Lo Moriello", S["cover_meta"]),
    Spacer(1, 0.4*cm),
    Paragraph("August 2026", S["cover_meta"]),
    PageBreak(),
]

# ── 1. What this is ──────────────────────────────────────────────────────────
story += [
    section_header(1, "What This Package Contains"),
    Paragraph(
        "Chart Digitizer is an offline web application that extracts the two curves "
        "(milk flow and vacuum pressure) from AMS milking-report PDFs and produces one "
        "CSV file per animal session. Everything runs locally — no internet connection "
        "is used at any point.", S["body"]),
    styled_table([
        ["Item", "Purpose"],
        ["app.py  ·  start.sh  ·  frontend/", "The web application"],
        ["pipeline/pipeline.py", "The computer-vision extraction pipeline"],
        ["sample_input/sample_report.pdf", "A real 2-page AMS report to test with (16 sessions)"],
        ["synthetic/pdf_output/", "3 synthetic test PDFs + exact ground truth (48 charts)"],
        ["tests/evaluate_accuracy.py", "Accuracy benchmark against the ground truth"],
        ["pipeline/csv_synthetic_*/", "Pre-generated pipeline output for the benchmark"],
        ["Chart_Digitizer_Explainer.pdf", "Technical explainer (architecture & accuracy)"],
        ["requirements.txt  ·  Dockerfile", "Dependencies / optional container setup"],
    ], [7*cm, 9*cm]),
    Spacer(1, 0.4*cm),
]

# ── 2. Requirements ──────────────────────────────────────────────────────────
story += [
    section_header(2, "Requirements"),
    Paragraph(
        "Only <b>Python 3.10 or newer</b> is required (check with "
        "<font name='Courier'>python3 --version</font>). "
        "Tesseract OCR is <b>optional</b> — it is used only when processing PNG/JPG "
        "images instead of PDFs. All PDFs, including the included samples, work without it.",
        S["body"]),
    Spacer(1, 0.2*cm),
]

# ── 3. Setup ─────────────────────────────────────────────────────────────────
story += [
    section_header(3, "Setup (one time, ~2 minutes)"),
    Paragraph("Open a terminal inside the <font name='Courier'>chart_digitizer</font> "
              "folder and run:", S["body"]),
    Paragraph("<b>macOS / Linux</b>", S["step"]),
    code_block([
        "python3 -m venv venv",
        "source venv/bin/activate",
        "pip install -r requirements.txt",
    ]),
    Paragraph("<b>Windows (Command Prompt)</b>", S["step"]),
    code_block([
        "python -m venv venv",
        "venv\\Scripts\\activate.bat",
        "pip install -r requirements.txt",
    ]),
    Paragraph(
        "The install downloads OpenCV, NumPy, PyMuPDF, Pandas and Flask. "
        "It may take a minute or two on first run.", S["body"]),
]

# ── 4. Run the web app ───────────────────────────────────────────────────────
story += [
    section_header(4, "Run the Web App"),
    Paragraph("<b>macOS / Linux</b>", S["step"]),
    code_block(["./start.sh"]),
    Paragraph("<b>Windows</b>", S["step"]),
    code_block(["python app.py"]),
    Paragraph(
        "Then open <b><font name='Courier'>http://localhost:5001</font></b> in any browser and:",
        S["body"]),
    Paragraph("1.  Drag <font name='Courier'>sample_input/sample_report.pdf</font> onto the "
              "upload area (or click it to browse).", S["step"]),
    Paragraph("2.  Click <b>Run Extraction</b> — a progress bar shows charts being extracted.", S["step"]),
    Paragraph("3.  <b>Expected result:</b> 16 sessions from 15 animals, dated 2024-03-07, "
              "with zero warnings.", S["step"]),
    Paragraph("4.  Click any session row to preview the extracted curves and per-session "
              "statistics (peak flow, duration, estimated yield, average pressure).", S["step"]),
    Paragraph("5.  Download individual CSVs, or all of them with "
              "<b>Download all as ZIP</b>.", S["step"]),
    Spacer(1, 0.2*cm),
    Paragraph(
        "Each CSV contains three columns — curve name, time in minutes (0–10), and value. "
        "Both curves start at (0, 0), and the flow curve runs to the end of the 10-minute "
        "session window.", S["body"]),
    code_block([
        "curve,time_min,value",
        "Flusso_kg_min,0.0,0.0",
        "Flusso_kg_min,0.0202,0.1923",
        "Pressione_assoluta_0.1bar,0.0,0.0",
    ]),
]

# ── 5. Command line ──────────────────────────────────────────────────────────
story += [
    section_header(5, "Command-Line Usage (optional)"),
    Paragraph("The pipeline can also run without the web app:", S["body"]),
    code_block([
        "python pipeline/pipeline.py --input sample_input/sample_report.pdf \\",
        "                            --out ./my_csv_output",
    ]),
    Paragraph("Add <font name='Courier'>--report</font> to also write a JSON summary "
              "of every chart processed.", S["body"]),
]

# ── 6. Verify accuracy ───────────────────────────────────────────────────────
story += [
    section_header(6, "Verify the Accuracy Claims"),
    Paragraph(
        "The package includes three synthetic PDFs whose exact curve coordinates are known "
        "(<font name='Courier'>synthetic/pdf_output/ground_truth.json</font>), plus the "
        "pipeline's output for them. To reproduce the accuracy numbers reported in the "
        "technical explainer:", S["body"]),
    code_block([
        "cd tests",
        "python evaluate_accuracy.py",
    ]),
    Paragraph("<b>Expected output</b> (48/48 charts matched):", S["body"]),
    styled_table([
        ["Metric", "Flusso (flow)", "Pressione (pressure)"],
        ["MAE — mean",   "0.12 kg/min", "0.19 × 0.1 bar"],
        ["MAE — median", "0.11 kg/min", "0.20 × 0.1 bar"],
        ["Curve coverage", "100.0 %", "98.4 %"],
    ], [5.3*cm, 5.3*cm, 5.3*cm]),
    Spacer(1, 0.25*cm),
    Paragraph(
        "To regenerate the pipeline output from scratch before benchmarking "
        "(instead of using the pre-generated CSVs), run:", S["body"]),
    code_block([
        "python pipeline/pipeline.py --input synthetic/pdf_output/synthetic_1_baseline.pdf \\",
        "                            --out pipeline/csv_synthetic_baseline",
        "python pipeline/pipeline.py --input synthetic/pdf_output/synthetic_2_multipage.pdf \\",
        "                            --out pipeline/csv_synthetic_multipage",
        "python pipeline/pipeline.py --input synthetic/pdf_output/synthetic_3_edge.pdf \\",
        "                            --out pipeline/csv_synthetic_edge",
    ]),
]

# ── 7. Docker ────────────────────────────────────────────────────────────────
story += [
    section_header(7, "Docker (optional alternative)"),
    Paragraph("If Docker is installed, Sections 2–3 can be skipped entirely:", S["body"]),
    code_block([
        "docker build -t chart-digitizer .",
        "docker run -p 5001:5000 chart-digitizer",
    ]),
    Paragraph("Then open <font name='Courier'>http://localhost:5001</font>.", S["body"]),
]

# ── 8. Troubleshooting ───────────────────────────────────────────────────────
story += [
    section_header(8, "Troubleshooting"),
    styled_table([
        ["Symptom", "Fix"],
        ["Port 5001 already in use",
         "Run on another port:  ./start.sh 5002   (then open localhost:5002)"],
        ["ModuleNotFoundError",
         "The virtual environment is not active — rerun the activate command from Section 3"],
        ["Permission denied: ./start.sh",
         "chmod +x start.sh"],
        ["'tesseract not found' warning",
         "Only affects PNG/JPG inputs. PDFs work without Tesseract — no action needed"],
    ], [6*cm, 10*cm]),
    Spacer(1, 0.4*cm),
    Paragraph("For anything else, contact the author.", S["body"]),
]

doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    topMargin=1.7*cm, bottomMargin=1.5*cm,
    leftMargin=1.5*cm, rightMargin=1.5*cm,
)
doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
print(f"PDF saved → {OUT}")
