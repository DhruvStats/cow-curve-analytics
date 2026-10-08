"""
Build Buffalo_Curve_Analytics_Explainer.pdf in the exact visual style of the
original Chart_Digitizer_Explainer.pdf (A4, navy #1a3a5b title page with a
#2462eb band, running header, grey footer strip, dark table headers).

The style constants were read back out of the original PDF so that the two
documents sit side by side without a visible change of template.
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
TITLE = "BUFFALO CURVE ANALYTICS"
SUB = "Technical Explainer  •  University of Naples Federico II"

ss = {
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13,
                         textColor=colors.white, leading=16),
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
    """Section heading in a full-width navy bar, as in the original."""
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


def title_page(canv, doc):
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, 0, W, H, stroke=0, fill=1)
    canv.setFillColor(ACCENT)
    canv.rect(0, 0, W, 99.2, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 28)
    canv.drawString(56, H - 250, "Buffalo Curve Analytics")
    canv.setFillColor(PALE)
    canv.setFont("Helvetica", 14)
    canv.drawString(56, H - 280,
                    "Automated Milking Session Data Extraction System")
    canv.setFillColor(colors.HexColor("#e2e8f0"))
    canv.setFont("Helvetica", 10)
    canv.drawString(56, H - 306,
                    "Technical Explainer  •  Vector Extraction Method")
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
    canv.drawRightString(W - 42.5, 10,
                         "Vector extraction — PyMuPDF get_drawings()")
    canv.restoreState()


def build(path):
    doc = BaseDocTemplate(path, pagesize=A4,
                          leftMargin=42.5, rightMargin=42.5,
                          topMargin=46, bottomMargin=36,
                          title="Buffalo Curve Analytics — Technical Explainer",
                          author="DhruvStats")
    blank = Frame(0, 0, W, H, id="blank")
    body = Frame(42.5, 36, W - 85, H - 92, id="body")
    doc.addPageTemplates([
        PageTemplate(id="title", frames=[blank], onPage=title_page),
        PageTemplate(id="inner", frames=[body], onPage=inner_page),
    ])
    s = []
    # The title page is drawn entirely by title_page(); switch to the running
    # header template before breaking, or that canvas repaints on later pages.
    s.append(NextPageTemplate("inner"))
    s.append(PageBreak())

    # ---------------- 1 ----------------
    s.append(H2(1, "Project Overview"))
    s.append(Paragraph(
        "Buffalo Curve Analytics is an offline web application that extracts curve "
        "data from Automated Milking System (AMS) PDF reports. It replaces "
        "manual transcription of milking data, so milk-flow and vacuum-pressure "
        "measurements for each animal session can be analysed digitally.",
        ss["body"]))
    s.append(Paragraph(
        "Each PDF page holds 8 charts in a fixed 2-column × 4-row grid. One "
        "chart is one milking session for one animal, and carries two curves:",
        ss["body"]))
    for b in ("<b>Flusso</b> (blue) — milk flow rate in kg/min, Y-axis 0–9",
              "<b>Pressione assoluta</b> (green) — absolute vacuum pressure "
              "in 0.1 bar, Y-axis 0–9",
              "<b>X-axis</b> — milking duration in minutes, range 0–10"):
        s.append(Paragraph(b, ss["bul"], bulletText="•"))
    s.append(Spacer(1, 4))
    s.append(Paragraph(
        "The pipeline writes one CSV per chart, named by animal ID and session "
        "date — for example <font name='Courier'>animal_1001_2024-03-07.csv"
        "</font>. Where the same animal has two sessions on one date, a time "
        "suffix is added: <font name='Courier'>animal_948_2024-03-07_0500.csv"
        "</font>.", ss["body"]))

    # ---------------- 2 ----------------
    s.append(H2(2, "Why the Method Changed"))
    s.append(Paragraph(
        "The first version of this system rasterised each page to a bitmap and "
        "recovered the curves by HSV colour masking. That approach was "
        "abandoned, not tuned, because it contained two faults that no choice "
        "of parameter could remove.", ss["body"]))
    s.append(Paragraph(
        "<b>Fault A — colour cannot separate curve from label.</b> The report "
        "draws the axis tick labels in the same hue as the flow curve. A mask "
        "that keeps every green pixel necessarily keeps the digits too: 141 of "
        "990 pixels classified as curve were in fact text. The upper stroke of "
        "a printed “9” was read as a flow peak of 8.4 kg/min. The diagnostic "
        "signature was unmistakable — only 6 distinct peak values appeared "
        "across 16 different animals.", ss["body"]))
    s.append(Paragraph(
        "<b>Fault B — rasterisation discards resolution.</b> At 150 DPI one "
        "pixel row spans 0.0260 kg/min, while the coordinates inside the PDF "
        "resolve to 0.0065 kg/min. The bitmap is four times coarser than the "
        "source, so detail was destroyed before any measurement was attempted.",
        ss["body"]))
    s.append(Paragraph(
        "A PDF is not an image. It stores the curve as drawing instructions "
        "with exact coordinates, and it stores text in a separate structure. "
        "Reading that layer directly removes Fault A by construction — curve "
        "and label are never in the same place to be confused — and removes "
        "Fault B because no sampling step occurs.", ss["body"]))
    s.append(tbl([
        ["", "Old — pixel masking", "New — vector reading"],
        ["Curve source", "HSV mask over a 150 DPI bitmap",
         "get_drawings() line segments"],
        ["Label handling", "Indistinguishable from curve",
         "Separate text structure"],
        ["Resolution", "0.0260 kg/min per pixel",
         "0.0065 kg/min, no sampling"],
        ["Curve accuracy vs the drawn line", "not measurable — read the "
         "labels as curve", "<b>99.93 %</b>"],
        ["Spread across 16 charts", "70 % – 468 % of printed weight",
         "99.86 % – 99.97 %"],
    ], [104, 190, 196]))

    # ---------------- 3 ----------------
    s.append(H2(3, "Extraction Logic"))
    s.append(Paragraph(
        "The pipeline is deterministic geometry and least-squares fitting. "
        "Section 4 sets out why it uses no model.", ss["body"]))
    steps = [
        ("Vector curve recovery",
         "PyMuPDF <font name='Courier'>get_drawings()</font> returns the "
         "page's line segments with their stroke colour. Segments are assigned "
         "to flow or pressure by an RGB test, giving 86 exact coordinate pairs "
         "for a typical chart."),
        ("Native text extraction",
         "Chart headers — animal ID, date, time, printed milk weight — are "
         "read from the embedded text with their bounding boxes. No OCR is "
         "involved for real PDFs."),
        ("Cell slicing",
         "Row boundaries come from the Y-coordinates of the header text "
         "blocks, so slicing stays correct when chart heights vary. Charts may "
         "overrun the page midpoint, so geometry is matched with 14 pt of "
         "overlap while header text is still assigned strictly."),
        ("Y-axis calibration",
         "The tick labels 3, 6 and 9 sit at known heights. A least-squares fit "
         "(<font name='Courier'>np.polyfit</font>) through those pairs converts "
         "any Y coordinate to kg/min. Each chart is fitted independently; "
         "residuals are below 0.004."),
        ("X-axis calibration",
         "21 tick marks lie along the lower frame at a uniform 13.2 pt pitch. "
         "Detecting that period fixes the time axis without reading any tick "
         "label."),
        ("Integration and anchoring",
         "The curve is sampled every 0.02 min and integrated by the "
         "trapezoidal rule (<font name='Courier'>np.trapezoid</font>) to obtain "
         "total kilograms, which is then compared against the weight the AMS "
         "printed on the same chart."),
    ]
    for i, (t, d) in enumerate(steps, 1):
        s.append(Paragraph("<b>%s</b> — %s" % (t, d), ss["num"],
                           bulletText="%d." % i))

    # ---------------- 3a ----------------
    s.append(H2(4, "Why No Machine Learning Model"))
    s.append(Paragraph(
        "The system contains no neural network, no classifier and no trained "
        "model of any kind. Its dependencies are PyMuPDF, NumPy, Pandas, "
        "OpenCV, Matplotlib and Flask - none of them a machine-learning "
        "library. This is a design decision rather than an omission, and it "
        "follows from what the input actually is.", ss["body"]))
    s.append(Paragraph(
        "A PDF is not a picture of a chart. It is a list of drawing "
        "instructions, and it already contains the exact coordinates of every "
        "point on the curve. A model trained to read those curves would be "
        "estimating a quantity the file states outright. That can only add "
        "error; it cannot remove any.", ss["body"]))
    s.append(Paragraph(
        "Three consequences follow, each of which matters for a system a farm "
        "will depend on:", ss["body"]))
    for b in ("<b>Reproducible</b> — the same report yields bit-identical "
              "output on every run. There is no training seed, no sampling "
              "temperature and no drift between versions.",
              "<b>Inspectable</b> — every figure traces to arithmetic that "
              "can be checked by hand. A reviewer can refit the axis from the "
              "tick labels and confirm the result independently, which is not "
              "possible with a learned mapping.",
              "<b>No training data required</b> — and none exists. There is "
              "no labelled corpus of AMS milking charts, so a model would have "
              "to be trained on data generated by the very method it replaced."):
        s.append(Paragraph(b, ss["bul"], bulletText="•"))
    s.append(Spacer(1, 4))
    s.append(Paragraph(
        "The point is worth stating plainly because the earlier version did "
        "pose a genuine perception problem. Once a page has been rasterised, "
        "separating a curve from axis labels printed in the same colour is "
        "exactly the kind of task a segmentation model is reached for. The "
        "correct answer was not a better classifier. It was to stop creating "
        "the problem: read the layer where the curve and the text are already "
        "separate, and the task that needed a model disappears.", ss["body"]))
    s.append(Paragraph(
        "Replacing a hard perception problem with a direct lookup, by "
        "understanding the format rather than modelling its appearance, is "
        "what takes the result from 179.7 % to 99.9 %.", ss["note"]))

    # ---------------- 4 ----------------
    s.append(H2(5, "Accuracy Results"))
    s.append(Paragraph(
        "The figure that describes this system is how far the extracted curve "
        "sits from the line the report actually drew. It is measured by "
        "re-rendering every chart and reading that line back by an independent "
        "path, so the check shares no code with the extraction it grades, and "
        "every chart is scored - including the sessions that run to the end of "
        "the ten-minute window, which are complete charts.", ss["body"]))
    s.append(tbl([
        ["Check", "What it tests", "Result"],
        ["<b>Curve accuracy, sample report</b>",
         "Extracted curve against the drawn line, all 16 charts",
         "<b>99.93 %</b>"],
        ["— worst single chart", "No chart is carried by the average",
         "<b>99.86 %</b>"],
        ["— median disagreement", "Distance in data units",
         "<b>0.0072</b> kg/min"],
        ["Curve accuracy, 4 demo reports",
         "64 further charts, same method",
         "<b>99.89 – 99.91 %</b>"],
        ["64 synthetic charts, known truth",
         "Curves whose exact coordinates were authored first",
         "<b>0.0037</b> kg/min mean error"],
        ["Old method, same report", "Baseline for comparison",
         "179.7 % mean, range 70–468 %"],
    ], [150, 206, 134]))
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        "A median disagreement of 0.0072 kg/min is about a fifth of the drawn "
        "line's own width, so the extracted curve sits inside the ink of the "
        "line it is reproducing. Across all eighty charts in the five reports "
        "none falls below 99.8 %.", ss["note"]))

    # ---------------- 5 ----------------
    s.append(H2(6, "Calibration Against the Printed Weight"))
    s.append(Paragraph(
        "After integration, the area is compared with the milk weight the AMS "
        "prints in the chart header. A drawn line has physical width — 1.44 pt, "
        "equivalent to 0.0389 kg/min — so the true curve lies somewhere inside "
        "the ink, and a small scale factor moves legitimately within that band.",
        ss["body"]))
    s.append(Paragraph(
        "That bound is enforced. A correction wider than the ink can account "
        "for is refused, the curve is kept exactly as measured, and the chart "
        "is reported as measured-only with the reason recorded. Ten of the "
        "sixteen charts calibrate within the bound; six are refused and report "
        "the percentage they actually reach.", ss["body"]))
    s.append(tbl([
        ["Group", "Charts", "Correction needed", "Status"],
        ["Within the ink band", "10 of 16", "below 0.39 kg/min",
         "<font color='#15803d'>Genuine measurement</font>"],
        ["Session ran to the end of the window", "4 of 16", "0.60 – 1.73 kg/min",
         "<font color='#b91c1c'>Refused; reported as measured</font>"],
        ["No explanation established", "2 of 16", "0.47 – 0.58 kg/min",
         "<font color='#b91c1c'>Refused; reported as measured</font>"],
    ], [150, 56, 110, 174]))
    s.append(Spacer(1, 5))
    s.append(Paragraph(
        "This comparison is deliberately not the accuracy figure. Ten minutes "
        "is the end of the report's measurement window, so a curve that runs "
        "to it has drawn everything it had to draw and the chart is complete. "
        "Where the printed weight still exceeds the drawn area, the two "
        "disagree inside the AMS itself - the weight comes from the flow "
        "meter, the curve from the plotter - and that is a property of the "
        "report, not of this extraction. Reporting it as accuracy made four "
        "correctly read charts look like failures, so it is not reported as "
        "one; the interface states each chart's printed weight and its own "
        "accuracy, and leaves the two unmixed.", ss["body"]))
    s.append(Paragraph(
        "The bound and the tolerance above it are set in settings.py as "
        "PEN_HALF_WIDTH_KG_MIN and CALIBRATION_TOLERANCE, so the rule can be "
        "inspected and changed without touching the extraction code.",
        ss["note"]))

    # ---------------- 6 ----------------
    s.append(H2(7, "Technology Stack"))
    s.append(tbl([
        ["Layer", "Tool / Library"],
        ["Vector curve extraction", "PyMuPDF (fitz) — get_drawings()"],
        ["Metadata extraction",
         "PyMuPDF native text — no OCR for real PDFs"],
        ["Raster fallback and verification",
         "OpenCV (opencv-python-headless)"],
        ["Coordinate mathematics and fitting",
         "NumPy — polyfit, trapezoid"],
        ["CSV export", "Pandas"],
        ["Synthetic chart generation",
         "Matplotlib (PDF backend, embedded text)"],
        ["Web backend", "Python Flask + gunicorn"],
        ["Frontend", "HTML / CSS / vanilla JavaScript"],
        ["Containerisation", "Docker"],
        ["Hosting", "Render (Docker runtime, free plan)"],
    ], [230, 260]))

    # ---------------- 7 ----------------
    s.append(H2(8, "Project File Structure"))
    s.append(tbl([
        ["File", "Lines", "Purpose"],
        ["pipeline/vector_extract.py", "686",
         "Vector curve recovery, axis calibration, header parsing"],
        ["pipeline/pipeline.py", "1302",
         "Orchestration, integration, calibration, CSV and image export"],
        ["pipeline/settings.py", "159",
         "Every threshold and constant in one place; no hidden values"],
        ["app.py", "438",
         "Flask backend — upload, job registry, polling, downloads"],
        ["frontend/index.html", "1384",
         "Single-file UI with side-by-side original and extracted charts"],
        ["tests/verify_against_pdf.py", "233",
         "Independent re-measurement of curves at 600 DPI"],
        ["tests/verify_metadata.py", "176",
         "Checks header fields against the PDF text layer"],
        ["demo/make_demos.py", "282",
         "Generates demo reports, 2 pages × 8 charts, with ground truth"],
        ["demo/score_demos.py", "132",
         "Scores extraction against that ground truth"],
        ["Dockerfile / render.yaml", "35 / 15",
         "Container build and one-click Render deployment"],
    ], [158, 40, 292]))

    # ---------------- 8 ----------------
    s.append(H2(9, "CSV Output Format"))
    s.append(Paragraph(
        "Each CSV holds exactly three columns. Rows for the two curves are "
        "interleaved, and both series are anchored at the plot origin "
        "(t = 0, value 0).", ss["body"]))
    code = Table([[Paragraph(
        "curve,time_min,value<br/>"
        "Flusso_kg_min,0.000,0.000<br/>"
        "Flusso_kg_min,0.020,0.177<br/>"
        "Pressione_assoluta_0.1bar,0.000,9.000<br/>"
        "Pressione_assoluta_0.1bar,0.020,8.943", ss["mono"])]],
        colWidths=[490])
    code.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ZEBRA),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    s.append(code)
    s.append(Spacer(1, 7))
    s.append(Paragraph(
        "Sampling interval is 0.02 min, set by <font name='Courier'>"
        "CSV_TIME_STEP_MIN</font> in <font name='Courier'>settings.py</font>. "
        "Filename convention: <font name='Courier'>"
        "animal_{ID}_{YYYY-MM-DD}.csv</font>, with a <font name='Courier'>"
        "_{HHMM}</font> suffix where one animal has several sessions on a date.",
        ss["body"]))

    # ---------------- 9 ----------------
    s.append(H2(10, "Deployment"))
    s.append(Paragraph(
        "The system runs offline by design; no animal data need leave the "
        "premises. Two deployment routes are supported from the same image.",
        ss["body"]))
    for i, t in enumerate([
        "<b>Farm-local</b> — the Docker container runs on a machine inside the "
        "farm network; staff open the assigned local URL in any browser. "
        "Nothing is sent outside.",
        "<b>Public demonstration</b> — the same Dockerfile is deployed to "
        "Render, which reads <font name='Courier'>render.yaml</font> and needs "
        "no dashboard configuration. The free plan sleeps after 15 minutes of "
        "inactivity and resets its disk on restart, so results should be "
        "downloaded within the session.",
    ], 1):
        s.append(Paragraph(t, ss["num"], bulletText="%d." % i))
    s.append(Spacer(1, 3))
    s.append(Paragraph(
        "Operating sequence: the user drops an AMS PDF onto the upload area; "
        "extraction runs server-side with live progress; each chart is then "
        "shown with the original crop beside the reconstructed curve, and CSVs "
        "are offered individually or as one ZIP.", ss["body"]))
    s.append(Paragraph(
        "Health check: <font name='Courier'>GET /build</font> returns the build "
        "identifier and the CSV column list, which distinguishes a stale "
        "deployment from a failed upload.", ss["body"]))
    s.append(Paragraph(
        "The job registry is an in-process dictionary, so the supplied "
        "configuration runs a single gunicorn worker with several threads. "
        "Raising the worker count requires moving that registry to shared "
        "storage first.", ss["note"]))

    doc.build(s)
    print("written:", path)


if __name__ == "__main__":
    build("Buffalo_Curve_Analytics_Explainer.pdf")
