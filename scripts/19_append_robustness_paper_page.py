"""Append reproducible robustness evidence to the four-page core paper."""
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper" / "core_main_4page.pdf"
PAPER = ROOT / "paper" / "main.pdf"
TIMELINE = ROOT / "figures" / "ETF_Operational_Timeline.png"
doc = fitz.open(SOURCE)
if len(doc) < 4:
    raise RuntimeError("Expected the four-page core paper")
if len(doc) > 4:
    doc.select(range(4))

css = """
* { font-family:'Times New Roman',serif; color:#000; }
p { font-size:9.5pt; line-height:1.08; text-align:justify; margin:0 0 5pt 0; }
h1 { font-size:12pt; font-weight:normal; text-align:center; margin:0 0 7pt 0; }
h2 { font-size:10.5pt; font-weight:normal; text-align:left; margin:5pt 0 4pt 0; }
table { width:100%; border-collapse:collapse; font-size:8.2pt; margin:4pt 0 7pt 0; }
th { border-top:1pt solid #000; border-bottom:.55pt solid #000; font-weight:normal; }
td,th { padding:2pt; text-align:right; vertical-align:top; }
td:first-child,th:first-child { text-align:left; }
tr:last-child td { border-bottom:1pt solid #000; }
.caption { font-size:8.8pt; line-height:1.05; text-align:center; margin:2pt 0 6pt 0; }
.note { font-size:8.5pt; line-height:1.04; font-style:italic; }
"""

def replace(page, rect, html, scale=.90):
    page.draw_rect(rect, color=None, fill=(1,1,1), overlay=True)
    spare, used = page.insert_htmlbox(rect, html, css=css, scale_low=scale, overlay=True)
    if spare < -.1:
        raise RuntimeError(f"Text overflow in {rect}: {spare}")

conclusion = """<p>In a leakage-controlled NIFTYBEES pilot with 1,185 eligible forecasts, the current gap-to-rolling-threshold ratio is a stronger observed next-day warning signal than the tested complex classifiers under repeated future-year evaluation. Its mean PR-AUC is 0.233, although paired superiority is established only over the decision tree. Alerted dates have a 6.00-bps larger mean next-session gap (95% bootstrap interval: 2.84–9.45 bps). A one-day official-NAV delay materially reduces performance and leaves the gap ratio effectively tied with random forest; timely NAV availability and a documented fallback are therefore required. Histogram gradient boosting also fails to improve the original ranking. The screen is defensible as a transparent, capacity-constrained monitoring aid with calibration and drift controls, not as an automatic trading engine. Generalization to additional verified ETFs remains open.</p>"""
repro = """<h1>VII. REPRODUCIBILITY AND RESPONSIBLE AI USE</h1><p>The repository contains cleaned inputs, provenance, leakage audits, configuration, scripts, predictions and sensitivity outputs. Exact numerical reproduction requires Python 3.11/3.12 and versions pinned in <i>requirements.txt</i>; the full retuning workflow can take tens of minutes. Table I maps to <i>modeling_dataset_summary.json</i>; Tables II–III to <i>walk_forward_results.json</i> and <i>ETF_Walk_Forward_Metrics.csv</i>; Table IV to <i>ETF_Alert_Budget_Summary.csv</i>; Table V to <i>ETF_Logistic_Standardized_Coefficients.csv</i>; Table VI to <i>ETF_Dislocation_Size_by_Alert.csv</i>; and Table VII to <i>ETF_NAV_Timing_Stress_Summary.csv</i>. The gradient-boosting row reproduces from <i>ETF_Gradient_Boosting_Metrics.csv</i>. Seeds are fixed (main seed 42). Repository: github.com/Rohit-Agarwal11/Niftybees-Price-NAV-Early-Warning.</p>"""
replace(doc[3], fitz.Rect(46,48,305,195), repro, .70)
replace(doc[3], fitz.Rect(46,287,305,421), conclusion, .82)

width, height = doc[0].rect.width, doc[0].rect.height
page = doc.new_page(width=width, height=height)
page.insert_htmlbox(fitz.Rect(40,25,width-40,50), "<h1>APPENDIX A. ADDITIONAL ROBUSTNESS AND OPERATIONAL VALUE</h1>", css=css)
page.insert_image(fitz.Rect(48,54,width-48,194), filename=str(TIMELINE), keep_proportion=True)
page.insert_htmlbox(fitz.Rect(45,195,width-45,232), "<p class='caption'>Fig. 3. Information timing and operational workflow. The 11 p.m. NAV cutoff is stipulated; actual release timestamps were unavailable. Reviewer-requested analyses retain the frozen label and folds and are reported regardless of result.</p>", css=css)

left = """
<h2>A. Magnitude of the flagged dislocation</h2>
<p>The primary 10% gap-ratio rule flags 72 of 702 held-out dates. Those dates have materially larger next-session absolute price–NAV gaps:</p>
<table><tr><th>Group</th><th>N</th><th>Events</th><th>Mean</th><th>Median</th><th>P90</th></tr>
<tr><td>Not alerted</td><td>630</td><td>46</td><td>12.49</td><td>11.33</td><td>21.18</td></tr>
<tr><td>Alerted</td><td>72</td><td>19</td><td>18.49</td><td>17.20</td><td>36.56</td></tr></table>
<p class='note'>Table VI. Absolute dislocation in basis points.</p>
<p>The mean difference is 6.00 bps. A 5,000-resample stratified bootstrap gives a 95% interval of 2.84–9.45 bps; the median difference is 5.87 bps (1.83–8.06). Thus the alert identifies larger outcomes, not merely more binary threshold exceedances.</p>
<h2>B. Workload interpretation</h2>
<p>The 10% rule produces 72 reviews across the three held-out years, about 24 annually, and detects 19 of 65 events. This is an observed workload description rather than an estimate of trading profitability.</p>
"""
right = """
<h2>C. One-day delayed-NAV stress test</h2>
<p>The stress scenario keeps date-<i>t</i> ETF market information but replaces the official NAV with date <i>t−1</i>. All NAV-dependent features are rebuilt and each classifier is retuned within the frozen folds.</p>
<table><tr><th>Model</th><th>Mean<br>PR-AUC</th><th>10%<br>precision</th><th>10%<br>recall</th></tr>
<tr><td>Gap ratio</td><td>0.160</td><td>17.1%</td><td>19.0%</td></tr>
<tr><td>Logistic</td><td>0.148</td><td>14.4%</td><td>21.8%</td></tr>
<tr><td>Tree</td><td>0.110</td><td>14.4%</td><td>21.8%</td></tr>
<tr><td>Random forest</td><td>0.161</td><td>18.1%</td><td>20.8%</td></tr></table>
<p class='note'>Table VII. Performance when the current official NAV is delayed.</p>
<p>Performance falls and the gap ratio and random forest become effectively tied. Timely official NAV availability is therefore a material operating assumption.</p>
<h2>D. Gradient-boosting comparator</h2>
<p>A validation-tuned histogram gradient-boosting model records PR-AUC of 0.185, 0.037 and 0.212 in 2024–2026, for a mean of 0.145. Its mean 10% precision is 13.1%. It does not close the gap to the transparent rule's original 0.233 mean PR-AUC.</p>
<p class='note'>Reproduce from ETF_Dislocation_Size_by_Alert.csv, ETF_NAV_Timing_Stress_Summary.csv and ETF_Gradient_Boosting_Metrics.csv.</p>
"""
page.insert_htmlbox(fitz.Rect(42,236,296,height-38), left, css=css, scale_low=.88)
page.insert_htmlbox(fitz.Rect(316,236,width-42,height-38), right, css=css, scale_low=.88)

tmp = PAPER.with_suffix('.tmp.pdf')
doc.save(tmp, garbage=4, deflate=True)
doc.close()
tmp.replace(PAPER)
print(PAPER)
