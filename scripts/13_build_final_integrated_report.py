"""Build the integrated final research report from verified project outputs."""
from __future__ import annotations

from pathlib import Path
from copy import deepcopy

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIG = ROOT / "figures"
REPORT = ROOT / "report"
REPORT.mkdir(exist_ok=True)
TMP = ROOT / "outputs" / "final_report_assets"
TMP.mkdir(exist_ok=True)
DEST = REPORT / "ETF_Project_Final_Integrated_Draft.docx"


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd"); tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=90, bottom=80, end=90):
    tc = cell._tc; tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar"); tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}"); tc_mar.append(node)
        node.set(qn("w:w"), str(v)); node.set(qn("w:type"), "dxa")


def set_cell_width(cell, width_inches):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW"); tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_inches * 1440))); tc_w.set(qn("w:type"), "dxa")


def set_table_borders(table, color="D9D9D9", size="5"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders"); tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}"); borders.append(node)
        node.set(qn("w:val"), "single"); node.set(qn("w:sz"), size)
        node.set(qn("w:space"), "0"); node.set(qn("w:color"), color)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar"); fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
    fld_end = OxmlElement("w:fldChar"); fld_end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_begin, instr, fld_end])


def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink"); hyperlink.set(qn("r:id"), r_id)
    run = OxmlElement("w:r"); r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color"); color.set(qn("w:val"), "000000")
    underline = OxmlElement("w:u"); underline.set(qn("w:val"), "single")
    r_pr.extend([color, underline]); run.append(r_pr)
    t = OxmlElement("w:t"); t.text = text; run.append(t); hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_body(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="Body Text")
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True; p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    return p


def add_bullet(doc, text):
    return doc.add_paragraph(text, style="List Bullet")


def add_caption(doc, text):
    p = doc.add_paragraph(text, style="Caption")
    p.paragraph_format.keep_with_next = True
    return p


def add_table(doc, headers, rows, widths, font_size=8.5, aligns=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER; table.autofit = False
    set_table_borders(table); set_repeat_table_header(table.rows[0])
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]; set_cell_width(cell, widths[i]); set_cell_shading(cell, "1F4E78")
        set_cell_margins(cell); cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(str(h)); r.bold = True; r.font.color.rgb = RGBColor(255,255,255); r.font.size = Pt(font_size)
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            set_cell_width(cells[i], widths[i]); set_cell_margins(cells[i]); cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if ridx % 2 == 1: set_cell_shading(cells[i], "F3F6FA")
            p = cells[i].paragraphs[0]
            p.alignment = aligns[i] if aligns else (WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER)
            r = p.add_run(str(value)); r.font.size = Pt(font_size)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_figure(doc, path, caption, width=6.45, note=None):
    add_caption(doc, caption)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    p.paragraph_format.space_after = Pt(2)
    if note:
        n = doc.add_paragraph(note, style="Source Note"); n.paragraph_format.space_after = Pt(8)


def add_reference(doc, number, text, url=None):
    p = doc.add_paragraph(style="Reference")
    p.add_run(f"[{number}] {text}")
    if url:
        p.add_run(" "); add_hyperlink(p, url, url)


def equation_png(text, output, width=10):
    fig, ax = plt.subplots(figsize=(width, .75)); ax.axis("off")
    ax.text(.5, .5, text, ha="center", va="center", fontsize=17)
    fig.savefig(output, dpi=240, transparent=True, bbox_inches="tight", pad_inches=.05); plt.close(fig)


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.top_margin = sec.bottom_margin = Inches(.68)
sec.left_margin = sec.right_margin = Inches(.78)
add_page_number(sec.footer.paragraphs[0])

styles = doc.styles
normal = styles["Normal"]; normal.font.name = "Times New Roman"; normal.font.size = Pt(10.5); normal.font.color.rgb = RGBColor(0,0,0)
normal.paragraph_format.space_after = Pt(5); normal.paragraph_format.line_spacing = 1.13
for name, size, before, after in [("Title",21,0,12),("Heading 1",15,12,6),("Heading 2",12.5,9,4),("Heading 3",11,7,3)]:
    st=styles[name];st.font.name="Arial";st.font.size=Pt(size);st.font.bold=True;st.font.color.rgb=RGBColor(0,0,0)
    st.paragraph_format.space_before=Pt(before);st.paragraph_format.space_after=Pt(after);st.paragraph_format.keep_with_next=True
styles["Body Text"].font.name="Times New Roman";styles["Body Text"].font.size=Pt(10.5)
styles["Body Text"].paragraph_format.first_line_indent=Inches(.25);styles["Body Text"].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
styles["Body Text"].paragraph_format.line_spacing=1.13;styles["Body Text"].paragraph_format.space_after=Pt(5)
styles["List Bullet"].font.name="Times New Roman";styles["List Bullet"].font.size=Pt(10.5);styles["List Bullet"].paragraph_format.space_after=Pt(3)
styles["Caption"].font.name="Arial";styles["Caption"].font.size=Pt(9);styles["Caption"].font.bold=True;styles["Caption"].font.color.rgb=RGBColor(0,0,0)
styles["Caption"].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER;styles["Caption"].paragraph_format.space_before=Pt(7);styles["Caption"].paragraph_format.space_after=Pt(3)
for custom in ["Source Note","Reference"]:
    if custom not in styles: styles.add_style(custom, 1)
styles["Source Note"].font.name="Times New Roman";styles["Source Note"].font.size=Pt(8.5);styles["Source Note"].font.italic=True
styles["Source Note"].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER;styles["Source Note"].paragraph_format.space_after=Pt(7)
styles["Reference"].font.name="Times New Roman";styles["Reference"].font.size=Pt(9.2);styles["Reference"].paragraph_format.left_indent=Inches(.25)
styles["Reference"].paragraph_format.first_line_indent=Inches(-.25);styles["Reference"].paragraph_format.space_after=Pt(3)

# Cover page
p=doc.add_paragraph(style="Title");p.alignment=WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Does Model Complexity Improve Next Day Price NAV Dislocation Warnings")
sub=doc.add_paragraph();sub.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=sub.add_run("A Leakage Controlled Walk Forward Study of NIFTYBEES");r.bold=True;r.font.name="Arial";r.font.size=Pt(16)
doc.add_paragraph()
for line in ["Ansh Kotwal  B2026006","Anish Mayya  B2026005","Rohit Agarwal  B2026037"]:
    p=doc.add_paragraph(line);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.runs[0].font.size=Pt(12)
doc.add_paragraph()
for line in ["Goa Institute of Management","PGDM Big Data Analytics","Advanced Machine Learning for Business Transformation"]:
    p=doc.add_paragraph(line);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.runs[0].font.size=Pt(11.5)
doc.add_paragraph()
p=doc.add_paragraph("Final Integrated Draft  18 November 2026");p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.runs[0].bold=True
doc.add_paragraph()
p=doc.add_paragraph("Study period  1 January 2021 to 16 November 2026");p.alignment=WD_ALIGN_PARAGRAPH.CENTER
page_break(doc)

doc.add_heading("Abstract", level=1)
add_body(doc,"This study evaluates whether complex machine learning models provide more reliable next trading day warnings of abnormal NIFTYBEES price NAV dislocations than transparent benchmark rules. Official NSE market data, AMFI net asset values, NIFTY 50 observations and India VIX data are reconciled for 1 January 2021 through 16 November 2026. The final merged panel contains 1,446 complete observations. A prospective abnormal event occurs when the next trading day's absolute dislocation exceeds the rolling 95th percentile estimated from the 252 complete observations available on the prediction date. The leakage controlled modelling sample contains 1,185 forecasts and 80 events. Three purged expanding window evaluations compare historical prevalence, current gap rules, previous event persistence, logistic regression, a decision tree and a random forest. The current gap to threshold ratio achieves the highest mean walk forward PR AUC of 0.233, compared with 0.169 for logistic regression, 0.156 for the decision tree and 0.184 for random forest. A paired moving block bootstrap establishes a 0.078 advantage over the decision tree, while intervals against logistic regression and random forest include zero. Market stress variables improve logistic regression from 0.153 to 0.195, but liquidity variables do not generate consistent gains. The gap ratio has the highest pooled precision at 5, 10 and 20 percent alert budgets. Event prevalence changes from 10.7 percent in 2024 to 2.0 percent in 2025 and 15.9 percent in 2026, producing substantial calibration and alert volume instability. The evidence supports a transparent capacity constrained monitoring system with continuing drift checks. It does not support automatic trading or universal superiority of one model.")
p=doc.add_paragraph();p.add_run("Keywords  ").bold=True;p.add_run("exchange traded funds, price NAV dislocation, NIFTYBEES, early warning, walk forward validation, interpretable machine learning, calibration, distribution shift")

doc.add_heading("Executive Summary", level=1)
add_body(doc,"The project began as an ETF pricing analysis and has been reframed as a prospective risk screening problem. After the NAV for trading date t becomes available, the system ranks the risk that the next actual NSE trading session will exhibit an unusually large price NAV dislocation. The design prevents the next day outcome from entering the event threshold, feature construction, model tuning or alert cutoff selection.")
add_bullet(doc,"The transparent current gap ratio records the highest average walk forward PR AUC, 0.233, and wins two of three test years.")
add_bullet(doc,"The uncertainty analysis supports superiority over the decision tree, but does not establish superiority over logistic regression or random forest at the 95 percent level.")
add_bullet(doc,"Market stress information improves logistic regression in every test fold; adding liquidity information or all available predictors does not reliably improve results.")
add_bullet(doc,"At a 10 percent review capacity, the gap ratio finds 19 of 65 pooled test events with 26.4 percent precision and 29.2 percent recall.")
add_bullet(doc,"Fixed score cutoffs fail under changing conditions. A validation cutoff intended for 10 percent alerts produces 0.0 to 5.3 percent alerts in 2025 and 22.9 to 39.3 percent in 2026.")
add_body(doc,"The recommended implementation is therefore a transparent ranking system that reviews a fixed percentage of dates, displays probability calibration when a classifier is used and monitors event prevalence, predictor shift, score shift and alert volume.")
page_break(doc)

doc.add_heading("1 Introduction and Business Problem", level=1)
add_body(doc,"An exchange traded fund is priced in two connected settings. Units trade continuously on an exchange, while net asset value is calculated from the value of the underlying portfolio. Creation and redemption by authorized participants should constrain large price differences, but trading costs, inventory limits, liquidity conditions, asynchronous prices and order imbalances can prevent immediate correction [8-13]. A premium can cause a buyer to pay more than the portfolio value represented by the unit; a discount can expose a seller to an unusually low execution price.")
add_body(doc,"This study asks a decision focused question: after the current day's official NAV becomes available, which dates deserve review for the risk of an abnormal price NAV dislocation on the next actual trading session? The objective is risk monitoring. It does not forecast general equity returns, prove an executable arbitrage strategy or recommend a trade.")
add_body(doc,"NIFTYBEES is used as a carefully audited pilot. It is a broad market Indian equity ETF with sufficient history to construct rolling thresholds and multiple chronological tests. All empirical claims therefore apply directly to NIFTYBEES. Expansion to other ETFs requires separate reconciliation of scheme identity, listing history, benchmark, corporate actions and NAV publication timing.")

doc.add_heading("2 Literature Review and Research Gap", level=1)
doc.add_heading("2.1 ETF pricing and limits to arbitrage", level=2)
add_body(doc,"Hilliard [9] models ETF premiums and discounts as a mean reverting process with jumps, while Petajisto [8] documents economically meaningful pricing bands that are wider for international and illiquid assets. Bae and Kim [10] show that ETF liquidity affects tracking error and volatility. Rappoport and Tuzun [11] find that market liquidity changes the efficacy of ETF arbitrage, and Pan and Zeng [13] explain how liquidity mismatch and dealer inventory can restrict arbitrage capacity. Together, these studies imply that current dislocation, recent dislocation history, market stress and trading activity are plausible predictive signals.")
doc.add_heading("2.2 Evidence from Indian ETFs", level=2)
add_body(doc,"Reddy and Dhabolkar [6] use autoregression and vector error correction methods to study Indian ETF price NAV deviations and lead lag relationships. Goel and Ahluwalia [7] examine 24 Indian equity ETFs and report meaningful discounts and tracking errors despite apparently low arbitrage constraints. Their evidence motivates direct analysis of Indian pricing efficiency, but it is primarily explanatory or contemporaneous. It does not evaluate a post NAV, next trading day warning system with leakage controls and a fixed review budget.")
doc.add_heading("2.3 Prediction, calibration and temporal evaluation", level=2)
add_body(doc,"The abnormal outcome is rare by construction, so PR AUC is more informative than ROC AUC for the primary comparison [14]. Probability quality is evaluated separately because discrimination does not guarantee calibration [15,20]. The Brier score is a proper scoring rule for probabilistic forecasts [19]. Cerqueira, Torgo and Mozetic [17] show that repeated out of sample evaluation is particularly appropriate when time series are nonstationary. Moving block resampling follows the dependent data logic established by Künsch [18]. These methodological findings support purged chronological folds, calibration reporting and block bootstrap uncertainty rather than random cross validation.")
doc.add_heading("2.4 Interpretability and research gap", level=2)
add_body(doc,"Rudin [16] argues that interpretable models should be treated as serious alternatives in consequential settings rather than explained only after fitting a black box. This principle is relevant to an ETF warning system because analysts must understand what triggers review. Among the studies examined, we did not identify an Indian equity ETF study that combines a post NAV prediction timestamp, a rolling ETF specific event definition, purged walk forward evaluation, paired dependent data uncertainty, calibration, feature ablation, label sensitivity and operational alert budgets. The contribution is this integrated design and its evidence, not a claim that price NAV deviations or machine learning are individually new.")
add_caption(doc,"Table 1  Position of the study relative to selected literature")
add_table(doc,["Study","Market and method","Relevant finding","Difference from this study"],[
    ["Reddy and Dhabolkar [6]","Indian ETFs; AR and VECM","Persistent deviations and lead lag behaviour","Explains pricing efficiency; no prospective event warning"],
    ["Goel and Ahluwalia [7]","24 Indian equity ETFs","Discounts, tracking error and operating constraints","Cross fund explanatory design"],
    ["Petajisto [8]","Multiple ETF asset classes","Pricing bands and short horizon mean reversion","No operational classifier or alert budget"],
    ["Bae and Kim [10]","US ETFs; liquidity and tracking error","Illiquidity increases deviation risk","Different market and dependent variable"],
    ["Rappoport and Tuzun [11]","ETF panel; arbitrage and liquidity","Liquidity affects arbitrage efficacy","Studies mechanism rather than next day warnings"],
    ["Current study","NIFTYBEES; purged walk forward models","Ranking, calibration, uncertainty and drift","Single fund pilot with prospective label"]
],[1.25,1.75,1.8,2.2],font_size=7.8,aligns=[WD_ALIGN_PARAGRAPH.LEFT]*4)

doc.add_heading("3 Research Questions and Hypotheses", level=1)
add_body(doc,"The primary research question is whether complex machine learning models provide more reliable next trading day warnings of abnormal NIFTYBEES price NAV dislocations than transparent benchmark rules when market conditions change over time.")
add_caption(doc,"Table 2  Prespecified hypotheses and decision evidence")
add_table(doc,["Hypothesis","Statement","Primary evidence"],[
    ["H1 Persistence","A larger current dislocation is associated with higher next day abnormal risk.","Gap rules, persistence benchmark and 10 percent alert lift"],
    ["H2 Incremental information","Market stress and liquidity add value beyond gap history.","Feature group ablation"],
    ["H3 Complexity","Nonlinear classifiers do not consistently beat transparent rules.","Walk forward PR AUC and paired bootstrap"],
    ["H4 Temporal shift","Prevalence and distribution shifts affect calibration and alert volume.","Yearly calibration, PSI and locked cutoffs"],
    ["H5 Operational utility","Limited capacity ranking identifies events above random review.","5, 10 and 20 percent alert budgets"]
],[1.05,3.15,2.8],font_size=8.2,aligns=[WD_ALIGN_PARAGRAPH.CENTER,WD_ALIGN_PARAGRAPH.LEFT,WD_ALIGN_PARAGRAPH.LEFT])

doc.add_heading("4 Data and Data Quality", level=1)
add_body(doc,"The observation unit is one NIFTYBEES trading date. Security level price, volume, turnover, trade count, delivery and intraday range fields come from NSE [1]. Official NAV observations come from AMFI scheme code 140084 and ISIN INF204KB14I2 [2]. NIFTY 50 data provide the underlying market control [3], and official India VIX observations provide market stress information [4]. SEBI's March 2026 Master Circular states that the NAV for domestic schemes is normally disclosed by 11 p.m. on the same business day [5]. The forecast timestamp is therefore after the date t NAV becomes available.")
add_caption(doc,"Table 3  Final data coverage")
add_table(doc,["Dataset","Rows","Coverage","Use"],[
    ["NIFTYBEES market data","1,456","1 Jan 2021 to 16 Nov 2026","Price and liquidity"],
    ["Official AMFI NAV","1,451","1 Jan 2021 to 16 Nov 2026","Price NAV dislocation"],
    ["NIFTY 50","1,456","1 Jan 2021 to 16 Nov 2026","Underlying market"],
    ["India VIX","1,455","1 Jan 2021 to 16 Nov 2026","Market stress"],
    ["Complete merged panel","1,446","1 Jan 2021 to 16 Nov 2026","Feature and label construction"],
    ["Leakage safe forecasts","1,185","12 Jan 2022 to 16 Nov 2026","Model evaluation"]
],[2.0,.75,2.05,2.2],font_size=8.5)
add_body(doc,"Eight special or Muhurat trading sessions have an NSE record but no matching AMFI NAV. Three AMFI NAV dates have no NSE market session. India VIX values of zero on 12 February 2021 and 30 March 2021 are treated as source anomalies and excluded from complete cases. Extreme dislocations are retained after source verification; the largest is 3.010 percent on 4 June 2024. These decisions are recorded at row level in the audit workbook and processing scripts.")

doc.add_heading("5 Methodology", level=1)
doc.add_heading("5.1 Prediction timestamp and prospective label", level=2)
add_body(doc,"For prediction date t, signed dislocation measures the percentage difference between the ETF closing price and official NAV. Positive values indicate a premium and negative values a discount.")
eq1=TMP/"equation_dislocation.png"; equation_png(r"$d_t = 100 \times \frac{P_t - NAV_t}{NAV_t}$",eq1)
p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(eq1),width=Inches(3.2))
add_body(doc,"The abnormal event is relative to the ETF's own recent history. The threshold uses only information available through t.")
eq2=TMP/"equation_label.png"; equation_png(r"$Y_{t+1}=1\;\;\mathrm{if}\;\;|d_{t+1}|>Q_{0.95}(|d_{t-251}|,\ldots,|d_t|)$",eq2)
p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(eq2),width=Inches(5.5))
add_body(doc,"A row enters modelling only when 252 complete historical observations are available, the following actual NSE session has a complete target and all predictors are available on t. The future target cannot influence its own threshold. One overlapping label interval is purged at each train validation and validation test boundary.")
doc.add_heading("5.2 Predictors, benchmarks and classifiers", level=2)
add_body(doc,"The 25 predictors cover current and lagged dislocations, five and 20 day dislocation summaries, ETF and NAV returns, NIFTY 50 returns, ETF minus index return differences, India VIX level and changes, volume, turnover, trade value, delivery percentage and intraday range. Volume and turnover are log transformed. Logistic scaling is fitted on training data only.")
add_body(doc,"Benchmarks include historical prevalence, current absolute gap, current gap divided by its rolling threshold and previous event persistence. Classifiers are L2 regularized logistic regression, a bounded decision tree and a 400 tree random forest. Validation PR AUC selects hyperparameters, with Brier score as a tie breaker. Random seed 42 is fixed.")
doc.add_heading("5.3 Purged walk forward evaluation", level=2)
add_caption(doc,"Table 4  Expanding window design")
add_table(doc,["Fold","Training targets","Validation targets","Test targets","Test rows and events"],[
    ["1","Through 2022","2023","2024","242 and 26"],
    ["2","Through 2023","2024","2025","246 and 5"],
    ["3","Through 2024","2025","2026 to 16 Nov","214 and 34"]
],[.55,1.55,1.45,1.55,1.9],font_size=8.5)
add_body(doc,"Each classifier is retuned in every fold using the validation period. The subsequent test period is evaluated once. This repeated subsequent year design is appropriate for assessing nonstationary temporal data [17].")
doc.add_heading("5.4 Evaluation and robustness analyses", level=2)
add_body(doc,"PR AUC is the primary ranking metric. ROC AUC is secondary. Brier score, log loss, calibration intercept, calibration slope and five equal frequency bin expected calibration error assess probability quality. Operational performance is measured by precision, recall, lift and number needed to review at 5, 10 and 20 percent capacities. Cutoff ties use expected selection within the tied group.")
add_body(doc,"Uncertainty is estimated with 2,000 paired moving block resamples using five observation blocks and a ten observation sensitivity check [18]. Robustness analyses cover rolling 90th, 95th and 97.5th percentile labels; fixed 0.50 and 1.00 percent labels; five feature groups; and validation locked cutoffs applied to the subsequent test year. Population Stability Index is used as a descriptive monitoring statistic, with values below 0.10 labelled low, 0.10 to below 0.25 moderate and at least 0.25 large.")

page_break(doc)
doc.add_heading("6 Results", level=1)
doc.add_heading("6.1 Walk forward model comparison", level=2)
add_caption(doc,"Table 5  Mean untouched test performance across three walk forward folds")
add_table(doc,["Model","Mean PR AUC","Minimum","Maximum","10 percent precision","10 percent recall"],[
    ["Historical prevalence","0.096","0.020","0.159","9.6%","10.3%"],
    ["Current absolute gap","0.218","0.125","0.277","22.4%","29.5%"],
    ["Current gap ratio","0.233","0.116","0.293","26.8%","32.7%"],
    ["Previous event persistence","0.154","0.056","0.214","27.9%","39.7%"],
    ["Logistic regression","0.169","0.035","0.267","18.6%","14.6%"],
    ["Decision tree","0.156","0.100","0.206","20.9%","39.3%"],
    ["Random forest","0.184","0.077","0.274","18.1%","26.2%"]
],[1.8,1.0,.8,.8,1.3,1.3],font_size=8.2)
add_body(doc,"The current gap ratio has the highest mean PR AUC and wins the 2024 and 2026 test folds. The current absolute gap wins the sparse 2025 fold. Random forest is validation selected in every fold but wins no subsequent test fold. H1 is supported because current gap information consistently ranks future events above prevalence. H3 is also supported at the consistency level: model complexity does not reliably dominate transparent rules.")
add_figure(doc,FIG/"ETF_Walk_Forward_PR_AUC.png","Figure 1  Purged walk forward test PR AUC by fold",6.4,"Source  Authors' calculations from the leakage safe modelling dataset.")

doc.add_heading("6.2 Dependent data uncertainty", level=2)
add_caption(doc,"Table 6  Paired five observation block bootstrap comparison")
add_table(doc,["Comparison","Observed PR AUC difference","95 percent interval","Interpretation"],[
    ["Gap ratio minus logistic regression","0.064","-0.012 to 0.164","Interval includes zero"],
    ["Gap ratio minus decision tree","0.078","0.019 to 0.168","Positive at 95 percent"],
    ["Gap ratio minus random forest","0.049","-0.024 to 0.128","Interval includes zero"]
],[2.1,1.3,1.35,2.25],font_size=8.3,aligns=[WD_ALIGN_PARAGRAPH.LEFT,WD_ALIGN_PARAGRAPH.CENTER,WD_ALIGN_PARAGRAPH.CENTER,WD_ALIGN_PARAGRAPH.LEFT])
add_body(doc,"The gap ratio mean PR AUC interval is 0.160 to 0.349. Its advantage over the decision tree remains positive with both five and ten observation blocks. Intervals against logistic regression and random forest include zero. The appropriate conclusion is therefore that the gap ratio has the best point estimate and a demonstrated advantage over the tree, while superiority over the other two classifiers remains uncertain.")
add_figure(doc,FIG/"ETF_Bootstrap_Paired_Differences.png","Figure 2  Paired block bootstrap differences in mean PR AUC",6.2,"Bars show percentile 95 percent intervals from 2,000 valid five observation block resamples.")

doc.add_heading("6.3 Label sensitivity", level=2)
add_caption(doc,"Table 7  Winner under alternative rolling event definitions")
add_table(doc,["Label","Events in modelling data","Highest mean PR AUC","Gap ratio 10 percent precision","Interpretation"],[
    ["Rolling 90th percentile","182","Random forest 0.299","35.2%","Forest leads by 0.010"],
    ["Rolling 95th percentile","80","Gap ratio 0.233","26.8%","Primary result"],
    ["Rolling 97.5th percentile","37","Random forest 0.286","21.1%","Forest leads by 0.002"],
    ["Fixed 0.50 percent","12","Infeasible","Not estimated","Too few events"],
    ["Fixed 1.00 percent","2","Infeasible","Not estimated","Too few events"]
],[1.5,1.25,1.35,1.45,1.45],font_size=8.0)
add_body(doc,"The exact PR AUC winner changes with the rolling percentile. However, the current gap ratio has the highest mean precision, recall and lift at the 10 percent alert budget for all three feasible rolling definitions. This separates ranking sensitivity from operational usefulness. The fixed thresholds are reported as infeasible rather than discarded, because their event counts cannot support the planned fold structure.")
add_figure(doc,FIG/"ETF_Label_Sensitivity_PR_AUC.png","Figure 3  Mean walk forward PR AUC under alternative labels",6.4,"Fixed thresholds are excluded from model comparison because their positive counts are insufficient.")

doc.add_heading("6.4 Alert budget and workload trade off", level=2)
add_caption(doc,"Table 8  Pooled current gap ratio performance by review capacity")
add_table(doc,["Budget","Alerts","Events found","Precision","Recall","Lift","Marginal precision"],[
    ["5%","37","11","29.7%","16.9%","3.21x","Not applicable"],
    ["10%","72","19","26.4%","29.2%","2.85x","22.9%"],
    ["20%","142","27","19.0%","41.5%","2.05x","11.4%"]
],[.7,.75,.95,.9,.9,.75,1.25],font_size=8.4)
add_body(doc,"The current gap ratio has the highest pooled precision at every prespecified capacity. Moving from 5 to 10 percent adds 35 reviews and eight events, while moving from 10 to 20 percent adds 70 reviews and only eight additional events. H5 is supported because precision remains about two to three times prevalence. A 10 percent capacity provides a defensible balance between workload and coverage, although the decision maker can choose another capacity based on resources.")
add_figure(doc,FIG/"ETF_Gap_Ratio_Budget_Tradeoff.png","Figure 4  Current gap ratio workload and coverage trade off",6.15,"Cutoff ties are handled through expected selection rather than row order.")

doc.add_heading("6.5 Feature group ablation", level=2)
add_caption(doc,"Table 9  Mean PR AUC by feature group")
add_table(doc,["Feature group","Predictors","Logistic","Tree","Forest"],[
    ["Gap only","6","0.160","0.171","0.169"],
    ["Gap history","10","0.153","0.153","0.178"],
    ["Gap plus market stress","15","0.195","0.160","0.173"],
    ["Gap plus liquidity","16","0.150","0.163","0.176"],
    ["Full model","25","0.169","0.156","0.184"],
    ["Gap ratio reference","1","0.233","0.233","0.233"]
],[2.25,.9,1.15,1.15,1.15],font_size=8.5)
add_body(doc,"H2 receives partial support. Adding NIFTY 50 and India VIX variables to gap history raises logistic regression mean PR AUC from 0.153 to 0.195 and improves it in all three folds. The mean 10 percent precision increases from 15.4 to 23.9 percent. The effect does not generalize to random forest, and liquidity variables do not produce consistent PR AUC or Brier improvements. More predictors therefore do not automatically improve out of time performance.")
add_figure(doc,FIG/"ETF_Feature_Ablation_PR_AUC.png","Figure 5  Classifier PR AUC by feature group",6.25,"Every classifier is retuned within each feature group and fold.")

doc.add_heading("6.6 Temporal shift and calibration", level=2)
add_caption(doc,"Table 10  Outcome and operational regime changes")
add_table(doc,["Test year","Events","Prevalence","PR AUC winner","Median predictor PSI","Locked alert range"],[
    ["2024","26","10.7%","Gap ratio 0.293","0.141","15.7 to 28.1%"],
    ["2025","5","2.0%","Absolute gap 0.125","0.191","0.0 to 5.3%"],
    ["2026","34","15.9%","Gap ratio 0.290","0.222","22.9 to 39.3%"]
],[.75,.65,.9,1.55,1.35,1.5],font_size=8.3)
add_body(doc,"H4 is supported. Event prevalence changes by a factor of 7.8 between the lowest and highest years. Predictor and score distributions shift, rankings change and no classifier remains well calibrated in every period. Logistic regression predicts 32.3 percent mean risk against 10.7 percent observed in 2024, 2.8 percent against 2.0 percent in 2025 and 15.1 percent against 15.9 percent in 2026. Its calibration slope remains below one in every year.")
add_body(doc,"A validation score cutoff intended for 10 percent alerts issues no logistic alerts in 2025 but 22.9 percent in 2026. The gap ratio cutoff issues 1.6 percent in 2025 and 39.3 percent in 2026. The operational system should therefore rank a fixed capacity rather than rely on a permanent score threshold.")
add_figure(doc,FIG/"ETF_Temporal_Shift_Outcomes.png","Figure 6  Outcome regime changes across test years",6.4,"The 2026 period ends on 16 November 2026.")
add_figure(doc,FIG/"ETF_Temporal_Shift_Locked_Alerts.png","Figure 7  Alert volume after applying validation locked cutoffs",6.4,"Constant and binary score benchmarks are omitted because complete ties make percentile cutoffs operationally uninformative.")

page_break(doc)
doc.add_heading("7 Discussion and Scholarly Comparison", level=1)
doc.add_heading("7.1 Persistence and pricing efficiency", level=2)
add_body(doc,"The strong current gap result is consistent with Reddy and Dhabolkar's evidence of persistent Indian ETF deviations [6] and with the short horizon pricing bands and mean reversion described by Petajisto [8] and Hilliard [9]. The present study adds a prospective interpretation: the current gap contains information about whether the next session will exceed an ETF specific abnormality threshold. This remains an association and does not show that a profitable trade is executable.")
doc.add_heading("7.2 Market stress and liquidity", level=2)
add_body(doc,"The market stress improvement in logistic regression is directionally consistent with evidence that ETF activity and volatility interact [12]. The absence of a broad liquidity gain differs from the stronger cross sectional liquidity relationships reported by Bae and Kim [10], Goel and Ahluwalia [7] and Rappoport and Tuzun [11]. The difference is credible rather than contradictory: this study examines one liquid broad market ETF, daily public proxies and a next day event, whereas those studies use broader panels, different liquidity measures and explanatory outcomes. The result suggests that daily volume, turnover, delivery and range do not add stable incremental warning information after gap history for this fund.")
doc.add_heading("7.3 Complexity, calibration and uncertainty", level=2)
add_body(doc,"The random forest's repeated validation selection but absence of test wins shows why model complexity must be judged out of time. The result supports Rudin's argument that transparent alternatives should be evaluated directly in consequential applications [16]. It also aligns with the wider forecasting evidence that no model is universally best and that evaluation design matters when data shift [17]. Probability calibration varies independently of PR AUC, as calibration research predicts [15,20].")
add_body(doc,"The uncertainty analysis prevents an inflated conclusion. The gap ratio has the best observed mean, but only its advantage over the decision tree excludes zero at the 95 percent level. Reporting this limitation increases the credibility of the main result. The evidence supports the gap ratio as the preferred operational benchmark, while logistic regression and random forest remain statistically plausible alternatives.")
doc.add_heading("7.4 What is original in this project", level=2)
add_body(doc,"The project's originality lies in the combination of decisions and controls. It defines an actionable post NAV timestamp, constructs a leakage safe next session label, treats transparent rules as genuine competitors, evaluates repeated subsequent years, quantifies dependent data uncertainty, tests label and feature sensitivity, measures calibration and connects model rankings to a fixed review capacity. The contribution is demonstrated on NIFTYBEES and should be described as a rigorous pilot rather than a universal ETF model.")

doc.add_heading("8 Contribution and Managerial Implications", level=1)
doc.add_heading("8.1 Methodological contribution", level=2)
add_body(doc,"The study provides a reproducible template for prospective financial warning tasks in which labels depend on rolling history. Its boundary purging, validation only tuning, repeated test periods and dependent data intervals reduce several common sources of optimistic bias.")
doc.add_heading("8.2 Empirical contribution", level=2)
add_body(doc,"The evidence shows that current price NAV dislocation is a stronger and more stable warning signal than unrestricted feature expansion. Market stress adds value to a parsimonious logistic model, but public daily liquidity measures do not contribute consistently. The results also quantify how rapidly probability and workload interpretations can fail when event prevalence changes.")
doc.add_heading("8.3 Operational recommendation", level=2)
add_bullet(doc,"Use the current gap to rolling threshold ratio as the first line ranking signal.")
add_bullet(doc,"Review a fixed capacity, with 10 percent as the study's primary balance between precision and recall.")
add_bullet(doc,"Use logistic regression when a probability is required, accompanied by calibration and drift indicators.")
add_bullet(doc,"Monitor event prevalence, feature PSI, score PSI, Brier score and realised alert volume by period.")
add_bullet(doc,"Investigate source timing and extreme values before escalating a warning, particularly on special sessions.")
add_body(doc,"A high score should prompt price NAV comparison, liquidity review and cautious execution. It should not automatically initiate a trade because bid ask spread, market impact, creation unit constraints, intraday iNAV and transaction costs are outside the current target.")

doc.add_heading("9 Limitations and Future Work", level=1)
add_body(doc,"The study covers one broad market ETF and three test years. The 2025 test fold contains only five events, making its ranking and calibration estimates imprecise. Bootstrap intervals remain wide, and most paired classifier comparisons are inconclusive. These limitations are reported rather than hidden.")
add_body(doc,"Closing price and end of day NAV do not capture intraday arbitrage. Bid ask spreads, order book depth, iNAV, authorized participant flows, creation and redemption activity, market impact and transaction costs are unavailable. Consequently, the study cannot estimate executable trading profitability.")
add_body(doc,"The rolling label is useful for risk monitoring but is relative to recent history. Fixed 0.50 and 1.00 percent definitions are economically intuitive but too sparse in the current sample. Future work should extend the history and add carefully reconciled ETFs before revisiting those thresholds.")
add_body(doc,"A multi ETF panel is the most valuable extension. Each fund should be mapped by scheme code and ISIN, with listing history, benchmark, corporate actions, NAV timing and asset class checked before pooling. External validation should test whether the gap ratio remains strong in sectoral, thematic, international, gold and debt ETFs. More frequent data could then support transaction cost and intraday execution analysis.")

doc.add_heading("10 Conclusion", level=1)
add_body(doc,"This project converts ETF pricing efficiency into a leakage controlled next trading day warning problem. Official sources support 1,446 complete NIFTYBEES observations and 1,185 eligible forecasts after the rolling history and boundary rules are applied. Across three purged walk forward tests, the current gap ratio produces the highest mean PR AUC and the best pooled precision at every alert budget. Its advantage over the decision tree is supported by the paired block bootstrap, while advantages over logistic regression and random forest remain uncertain.")
add_body(doc,"The evidence answers the primary question: added model complexity does not provide a more reliable warning system in this sample. Market stress improves one parsimonious classifier, but liquidity and unrestricted feature expansion do not produce general gains. Rankings, calibration and alert volumes vary sharply across years, so a permanent probability threshold is unsuitable.")
add_body(doc,"A feasible implementation is a transparent capacity based monitor that ranks dates, limits the number reviewed, exposes the drivers of risk and tracks drift. This conclusion is useful precisely because it is bounded. It supports a NIFTYBEES pilot and controlled external validation; it does not support automatic trading or a universal claim about Indian ETFs.")

doc.add_heading("11 Reproducibility and Research Integrity", level=1)
add_body(doc,"The repository contains cleaned official inputs, the merged and leakage safe analytical datasets, numbered scripts, frozen configuration, row level predictions, machine readable results, audit workbooks and figures. Running the documented workflow recreates data reconciliation, model comparison, walk forward validation, block bootstrap intervals, label sensitivity, alert budgets, feature ablation and temporal shift diagnostics.")
add_bullet(doc,"Expected counts: 1,456 market rows, 1,451 NAV rows, 1,446 complete cases, 1,185 modelling observations and 80 primary events.")
add_bullet(doc,"Environment: Python 3.11 or 3.12 with pinned package versions in requirements.txt.")
add_bullet(doc,"Execution: python run_all.py from the repository root.")
add_bullet(doc,"Randomness: random seed 42 for model fitting and bootstrap sampling.")
add_bullet(doc,"Test isolation: no test outcome enters preprocessing, feature selection, hyperparameter selection or validation cutoffs.")
p=doc.add_paragraph(style="Body Text");p.add_run("Repository URL  ").bold=True;p.add_run("Insert the public or institution accessible GitHub URL after uploading the final repository package.")
doc.add_heading("11.1 Artificial intelligence use disclosure", level=2)
add_body(doc,"Generative artificial intelligence tools assisted literature discovery, code drafting, language editing and document formatting. The student authors selected the research design, reviewed the cited sources, verified official data, executed the analysis and remain responsible for all interpretations and errors. AI generated text and code were not accepted without human review. No confidential personal data were supplied to the tools.")

page_break(doc)
doc.add_heading("References", level=1)
refs=[
 (1,"National Stock Exchange of India. Security wise price, volume and deliverable position data.","https://www.nseindia.com/report-detail/eq_security"),
 (2,"Association of Mutual Funds in India. Historical NAV download.","https://www.amfiindia.com/net-asset-value/nav-download"),
 (3,"NSE Indices. Historical index reports.","https://www.niftyindices.com/reports"),
 (4,"National Stock Exchange of India. Historical index data including India VIX.","https://www.nseindia.com/reports-indices-historical-index-data"),
 (5,"Securities and Exchange Board of India. Master Circular for Mutual Funds as on 20 March 2026, Chapter 9.","https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf"),
 (6,"Reddy, Y. V., and Dhabolkar, P. 2020. Pricing Efficiency of Exchange Traded Funds in India. Organizations and Markets in Emerging Economies 11(1), 244-268. doi:10.15388/omee.2020.11.33.","https://doi.org/10.15388/omee.2020.11.33"),
 (7,"Goel, G., and Ahluwalia, E. 2021. Do pricing efficiencies in Indian equity ETF market impact its performance? Global Finance Journal 49, 100654. doi:10.1016/j.gfj.2021.100654.","https://doi.org/10.1016/j.gfj.2021.100654"),
 (8,"Petajisto, A. 2017. Inefficiencies in the Pricing of Exchange Traded Funds. Financial Analysts Journal 73(1), 24-54. doi:10.2469/faj.v73.n1.7.","https://doi.org/10.2469/faj.v73.n1.7"),
 (9,"Hilliard, J. 2014. Premiums and discounts in ETFs: An analysis of the arbitrage mechanism in domestic and international funds. Global Finance Journal 25(2), 90-107.",None),
 (10,"Bae, K., and Kim, D. 2020. Liquidity risk and exchange traded fund returns, variances, and tracking errors. Journal of Financial Economics 138(1), 222-253. doi:10.1016/j.jfineco.2019.02.012.","https://doi.org/10.1016/j.jfineco.2019.02.012"),
 (11,"Rappoport, D. E., and Tuzun, T. 2020. Arbitrage and Liquidity: Evidence from a Panel of Exchange Traded Funds. Finance and Economics Discussion Series 2020-097. doi:10.17016/FEDS.2020.097.","https://doi.org/10.17016/FEDS.2020.097"),
 (12,"Ben-David, I., Franzoni, F., and Moussawi, R. 2018. Do ETFs Increase Volatility? Journal of Finance 73(6), 2471-2535. doi:10.1111/jofi.12727.","https://doi.org/10.1111/jofi.12727"),
 (13,"Pan, K., and Zeng, Y. 2019. ETF Arbitrage Under Liquidity Mismatch. SSRN Working Paper 2895478. doi:10.2139/ssrn.2895478.","https://doi.org/10.2139/ssrn.2895478"),
 (14,"Saito, T., and Rehmsmeier, M. 2015. The Precision Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets. PLOS ONE 10(3), e0118432. doi:10.1371/journal.pone.0118432.","https://doi.org/10.1371/journal.pone.0118432"),
 (15,"Guo, C., Pleiss, G., Sun, Y., and Weinberger, K. Q. 2017. On Calibration of Modern Neural Networks. Proceedings of ICML 2017, 1321-1330.","https://proceedings.mlr.press/v70/guo17a.html"),
 (16,"Rudin, C. 2019. Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. Nature Machine Intelligence 1, 206-215. doi:10.1038/s42256-019-0048-x.","https://doi.org/10.1038/s42256-019-0048-x"),
 (17,"Cerqueira, V., Torgo, L., and Mozetic, I. 2020. Evaluating time series forecasting models: An empirical study on performance estimation methods. Machine Learning 109, 1997-2028. doi:10.1007/s10994-020-05910-7.","https://doi.org/10.1007/s10994-020-05910-7"),
 (18,"Kunsch, H. R. 1989. The jackknife and the bootstrap for general stationary observations. The Annals of Statistics 17(3), 1217-1241. doi:10.1214/aos/1176347265.","https://doi.org/10.1214/aos/1176347265"),
 (19,"Gneiting, T., and Raftery, A. E. 2007. Strictly Proper Scoring Rules, Prediction, and Estimation. Journal of the American Statistical Association 102(477), 359-378. doi:10.1198/016214506000001437.","https://doi.org/10.1198/016214506000001437"),
 (20,"Niculescu-Mizil, A., and Caruana, R. 2005. Predicting good probabilities with supervised learning. Proceedings of the 22nd International Conference on Machine Learning, 625-632. doi:10.1145/1102351.1102430.","https://doi.org/10.1145/1102351.1102430"),
]
for n,text,url in refs: add_reference(doc,n,text,url)

doc.add_heading("Appendix A Reproduction Outputs", level=1)
add_table(doc,["Analysis","Primary reproducible output"],[
    ["Data audit","ETF_Label_and_Leakage_Audit_2021_to_2026.xlsx"],
    ["Walk forward validation","ETF_Walk_Forward_Validation.xlsx and row level predictions"],
    ["Bootstrap uncertainty","ETF_Block_Bootstrap_Uncertainty.xlsx"],
    ["Label sensitivity","ETF_Label_Sensitivity.xlsx"],
    ["Alert budgets","ETF_Alert_Budget_Sensitivity.xlsx"],
    ["Feature ablation","ETF_Feature_Ablation.xlsx"],
    ["Temporal shift","ETF_Temporal_Shift_Diagnostics.xlsx"],
    ["Machine readable results","JSON and CSV files in outputs"],
],[2.2,4.8],font_size=8.7,aligns=[WD_ALIGN_PARAGRAPH.LEFT,WD_ALIGN_PARAGRAPH.LEFT])
add_body(doc,"All reported counts and headline metrics are checked by executable verification scripts. The final GitHub package should be uploaded without changing the relative directory structure.")

# Prevent rows from splitting across pages and normalize paragraph widows.
for table in doc.tables:
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr(); cant_split = OxmlElement("w:cantSplit"); tr_pr.append(cant_split)
for p in doc.paragraphs:
    p_pr = p._p.get_or_add_pPr(); widow = OxmlElement("w:widowControl"); p_pr.append(widow)

doc.core_properties.title = "Does Model Complexity Improve Next Day Price NAV Dislocation Warnings"
doc.core_properties.subject = "Leakage controlled walk forward study of NIFTYBEES"
doc.core_properties.author = "Ansh Kotwal, Anish Mayya, Rohit Agarwal"
doc.core_properties.keywords = "NIFTYBEES, ETF, price NAV dislocation, machine learning, walk forward validation"
doc.save(DEST)
print(DEST)
