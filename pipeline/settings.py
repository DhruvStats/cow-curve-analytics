"""
settings.py — every tunable value for the Chart Digitizer, in one place.

These are fixed to the values verified against the real AMS report: 16/16
charts extracted, each calibrated to its own printed milk weight, axis fit
within 0.004 units. Nothing here is auto-detected or guessed at run time, so
two runs of the same PDF always produce identical output.

What is NOT here, deliberately: the animal id, date, session time, milk weight
and axis ranges. Those are read from each chart's own printed text on every
run, which is what lets the same settings handle a different report every day.

Change a value here only if the report format itself changes.
"""

# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

# The AMS report prints charts in a fixed 2-column, 4-row grid. Rows are
# located from the header positions rather than assumed, but the column split
# is taken from this.
GRID_ROWS = 4
GRID_COLS = 2
CHARTS_PER_PAGE = GRID_ROWS * GRID_COLS

# Charts in one visual row share a header Y within a point or two; 20pt buckets
# group them without merging rows, which sit ~199pt apart.
ROW_BUCKET_PT = 20.0

# The header sits a few points above the chart's top edge; back up by this so
# the crop and the text search include it.
HEADER_PAD_PT = 6.0

# The left chart's plot area overruns the page midpoint (gridlines reach
# x=305.9 on a 595.3pt page, midpoint 297.7), so column windows are widened by
# this much for geometry while text selection stays on the strict half.
COLUMN_OVERLAP_PT = 14.0


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

# Rasterisation DPI for the CV fallback path (scans, PNG/JPG uploads).
RASTER_DPI = 150

# DPI for the per-chart crops shown beside the extracted curve in the UI.
CROP_DPI = 150

# DPI for the optional pixel self-check (tests/verify_against_pdf.py).
FIDELITY_DPI = 300


# ---------------------------------------------------------------------------
# Curve colours in the PDF vector layer (DeviceRGB, 0..1)
# ---------------------------------------------------------------------------

# The report draws flow in pure blue and vacuum in a dark green. Margins are
# generous enough for a slightly different firmware palette while staying well
# clear of the greys (0.75) and black used for grid and frame.
BLUE_MIN_B, BLUE_MAX_R, BLUE_MAX_G = 0.55, 0.45, 0.45
GREEN_MIN_G, GREEN_MAX_R, GREEN_MAX_B = 0.35, 0.45, 0.45

# A channel must also dominate its rivals by this margin, not merely clear the
# thresholds above. Some herds' reports carry a third trace in purple
# (0.392, 0.027, 0.647), which passes the blue test on its own terms - blue
# 0.647 is over the minimum and red 0.392 under the maximum - and was being
# merged into the flow curve, inflating one chart's milk to 896% of its
# printed weight. Pure blue leads red by 1.000 and that purple by only 0.255,
# so a margin of half the range separates them with room on both sides.
CHANNEL_DOMINANCE = 0.50


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

# Row spacing in the CSV, in minutes. 0.02 min = 1.2 s. The AMS samples flow
# about every 2.7 s, so this is finer than the source and loses no detail.
CSV_TIME_STEP_MIN = 0.02

# Chart crops live in this subdirectory of the job output, so listing a job's
# CSVs stays a simple "*.csv in out_dir" scan.
CHART_IMAGE_SUBDIR = "charts"

# Decimal places for values written to the CSV. At 150 DPI one pixel is about
# 0.016 data units, so four places is already past the source resolution.
CSV_DECIMALS = 4


# ---------------------------------------------------------------------------
# Measurement rules
# ---------------------------------------------------------------------------

# Every flow curve is scaled so its area equals the milk weight printed on the
# same chart. That weight is the AMS flow meter's own measurement and the
# number the farm works from. Only the vertical scale changes; peak timing,
# dips and session length stay exactly as drawn.
CALIBRATE_TO_PRINTED_MILK = True

# The curve is drawn with a pen of real width, so the true value lies somewhere
# inside the ink rather than on one exact height. Half that width is the most
# the reading can honestly be out by, and therefore the most the calibration
# above is allowed to move it.
#
# A correction larger than this is not resolving ink ambiguity - it is covering
# milk the chart never drew, which happens when the session ran past the right
# edge of the time axis. Scaling the visible part to cover it would invent flow
# that is not in the source, so those curves are left exactly as measured and
# reported as truncated instead.
PEN_WIDTH_PT = 1.44
PEN_HALF_WIDTH_KG_MIN = 0.0389

# A little headroom above the ink bound before refusing, so a curve sitting
# right at the limit is not rejected over rounding in the area integral.
CALIBRATION_TOLERANCE = 1.15

# The AMS prints its own end-of-milking threshold on every chart as a dashed
# line labelled "0,20". Session length is measured against that line, so it
# matches what the machine itself counts as milking.
FLOW_THRESHOLD_KG_MIN = 0.20

# Vacuum level that means the cluster is still attached. The pressure trace
# sits near 4.5 during milking and falls away on detach, so a mid-scale cut
# separates the two cleanly.
ATTACHED_PRESSURE = 2.0

# Minimum fraction of chart width a curve must span on the CV fallback path,
# to reject coloured axis labels being mistaken for a curve.
MIN_CURVE_COVERAGE = 0.10


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

# Required curve-match accuracy, checked per chart whenever the fidelity check
# runs. Any chart below this is named rather than averaged away.
ACCURACY_THRESHOLD_PCT = 98.0

# The fidelity self-check re-renders every chart and re-measures the printed
# line, then reports how far the extracted curve sits from the drawn one.
#
# This is the figure that describes the digitiser, so it is on. It asks the
# only question the extraction can be held to - did it read the line that is
# there - and it answers it for every chart, including the sessions that run
# to the end of the time axis. Comparing instead against the weight printed in
# the header measures something else: whether the AMS's flow meter agrees with
# the AMS's own drawing, which is a property of the report, not of this code.
#
# Measured cost on the sample report is 1.2 s for sixteen charts, against an
# earlier note of about two seconds each; that estimate came from a run that
# also took the raster fallback path.
RUN_FIDELITY_CHECK = True


# ---------------------------------------------------------------------------
# Report text (Italian AMS format)
# ---------------------------------------------------------------------------

# Labels the header parser looks for. A report in another language would need
# these changed, and nothing else.
LABEL_ANIMAL = "Animale"
LABEL_DATE = "Data"
LABEL_TIME = "Ora"
LABEL_MILK = "latte"
LABEL_FARM = "Numero Azienda"

# Axis titles as printed, for reference when adapting to another format.
AXIS_X_TITLE = "Durata mungitura"
AXIS_Y_LEFT = "Flusso[kg/min]"
AXIS_Y_RIGHT = "pressione assoluta [0.1bar]"

# Curve names written into the CSV's `curve` column.
CURVE_FLOW = "Flusso_kg_min"
CURVE_PRESSURE = "Pressione_assoluta_0.1bar"
