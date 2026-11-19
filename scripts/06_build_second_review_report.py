from pathlib import Path
import json
import math

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'report'
OUT.mkdir(parents=True, exist_ok=True)
FIGURES = ROOT / 'figures'
FIGURES.mkdir(parents=True, exist_ok=True)
RESULTS = json.loads((ROOT / 'outputs' / 'model_results.json').read_text(encoding='utf-8'))
DOCX = OUT / 'ETF_Project_Revised_Second_Review_Draft.docx'
FIG1 = FIGURES / 'ETF_Test_PR_AUC.png'
FIG2 = FIGURES / 'ETF_Alert_Budget.png'

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
test_metrics = pd.DataFrame([r for r in RESULTS['metrics'] if r['Split']=='Test'])
budget = pd.DataFrame([r for r in RESULTS['budget_metrics'] if r['Split']=='Test'])

fig, ax = plt.subplots(figsize=(7.2, 3.5))
colors = ['#A5A5A5','#1F77B4','#4472C4','#70AD47','#ED7D31']
ax.bar(test_metrics['Model'], test_metrics['PR_AUC'], color=colors)
ax.axhline(test_metrics.loc[test_metrics.Model.eq('Historical Prevalence'),'PR_AUC'].iloc[0], color='#7F7F7F', linestyle='--', linewidth=1, label='No-skill PR-AUC')
ax.set_ylabel('PR-AUC')
ax.set_title('Out-of-time test PR-AUC')
ax.set_ylim(0, 0.34)
ax.grid(axis='y', alpha=.25)
ax.tick_params(axis='x', rotation=18)
ax.legend(frameon=False, loc='upper right')
fig.tight_layout()
fig.savefig(FIG1, dpi=220, bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(7.2, 3.5))
ax.bar(budget['Model'], budget['Precision_at_Budget']*100, color=['#1F77B4','#4472C4','#70AD47','#ED7D31'])
ax.set_ylabel('Precision among alerts (%)')
ax.set_title('Test performance under a 10% alert budget')
ax.set_ylim(0, 42)
ax.grid(axis='y', alpha=.25)
for i, (p, tp) in enumerate(zip(budget['Precision_at_Budget']*100, budget['True_Positives'])):
    ax.text(i, p+1, f'{p:.1f}%\n{int(tp)} events', ha='center', va='bottom', fontsize=9)
ax.tick_params(axis='x', rotation=12)
fig.tight_layout()
fig.savefig(FIG2, dpi=220, bbox_inches='tight')
plt.close(fig)

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.5)
sec.page_height = Inches(11)
sec.top_margin = Inches(0.72)
sec.bottom_margin = Inches(0.72)
sec.left_margin = Inches(0.78)
sec.right_margin = Inches(0.78)

styles = doc.styles
normal = styles['Normal']
normal.font.name = 'Aptos'
normal.font.size = Pt(10.5)
normal.font.color.rgb = RGBColor(0,0,0)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.08

styles['Title'].font.name = 'Aptos Display'
styles['Title'].font.size = Pt(19)
styles['Title'].font.bold = True
styles['Title'].font.color.rgb = RGBColor(0,0,0)
styles['Title'].paragraph_format.space_after = Pt(10)

for name, size in [('Heading 1',14),('Heading 2',12),('Heading 3',11)]:
    st=styles[name]
    st.font.name='Aptos Display'
    st.font.size=Pt(size)
    st.font.bold=True
    st.font.color.rgb=RGBColor(0,0,0)
    st.paragraph_format.space_before=Pt(10)
    st.paragraph_format.space_after=Pt(5)
    st.paragraph_format.keep_with_next=True

def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd')
        tcPr.append(shd)
    shd.set(qn('w:fill'), fill)

def set_cell_margins(cell, top=90, start=90, bottom=90, end=90):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar')
        tcPr.append(tcMar)
    for m, v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        node = tcMar.find(qn(f'w:{m}'))
        if node is None:
            node=OxmlElement(f'w:{m}')
            tcMar.append(node)
        node.set(qn('w:w'), str(v)); node.set(qn('w:type'),'dxa')

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement('w:tblHeader')
    tblHeader.set(qn('w:val'),'true')
    trPr.append(tblHeader)

def add_table(headers, rows, widths=None, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    set_repeat_table_header(table.rows[0])
    for j,h in enumerate(headers):
        cell=table.rows[0].cells[j]
        cell.text=str(h)
        set_cell_shading(cell,'1F4E78')
        cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        for p in cell.paragraphs:
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name='Aptos'; r.font.size=Pt(font_size); r.font.bold=True; r.font.color.rgb=RGBColor(255,255,255)
    for i,row in enumerate(rows):
        cells=table.add_row().cells
        for j,val in enumerate(row):
            cells[j].text='' if val is None else str(val)
            set_cell_shading(cells[j], 'F3F6FA' if i%2 else 'FFFFFF')
            cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cells[j])
            for p in cells[j].paragraphs:
                p.paragraph_format.space_after=Pt(0)
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    r.font.name='Aptos'; r.font.size=Pt(font_size); r.font.color.rgb=RGBColor(0,0,0)
        if widths:
            for j,w in enumerate(widths):
                cells[j].width=Inches(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return table

def add_body(text, bold_lead=None):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold=True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    return p

def add_bullet(text):
    p=doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after=Pt(3)
    p.add_run(text)
    return p

def add_caption(text):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next=True
    r=p.add_run(text); r.bold=True; r.font.size=Pt(9.5)

def add_page_number(paragraph):
    paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=paragraph.add_run()
    fldChar1=OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'),'begin')
    instr=OxmlElement('w:instrText'); instr.set(qn('xml:space'),'preserve'); instr.text=' PAGE '
    fldChar2=OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'),'end')
    run._r.extend([fldChar1,instr,fldChar2])

# Title page and abstract
p=doc.add_paragraph(style='Title')
p.alignment=WD_ALIGN_PARAGRAPH.CENTER
p.add_run('An Explainable Machine Learning Early Warning System for Price NAV Dislocations in Indian Equity ETFs')
p2=doc.add_paragraph()
p2.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p2.add_run('Evidence from NIFTYBEES')
r.font.size=Pt(14); r.bold=True

for line in [
    'Ansh Kotwal B2026006  Email insert official address',
    'Anish Mayya B2026005  Email insert official address',
    'Rohit Agarwal B2026037  Email insert official address',
    'Goa Institute of Management  Big Data Analytics',
    'Advanced Machine Learning for Business Transformation',
    'Second Review Draft  17 November 2026'
]:
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=p.add_run(line); run.font.size=Pt(10.5)

doc.add_paragraph()
doc.add_heading('Abstract', level=1)
add_body('This study develops and evaluates an explainable next trading day early warning system for abnormal differences between the market closing price and net asset value of Nippon India ETF Nifty 50 BeES. The analysis combines official NSE trading data, AMFI net asset values, NIFTY 50 market controls and India VIX observations from 1 January 2021 through 16 November 2026. After data reconciliation, 1,446 complete daily observations remain. An abnormal event is defined prospectively: the next day absolute price NAV dislocation must exceed the rolling 95th percentile estimated from the 252 complete observations available on the prediction date. The leakage safe modelling sample contains 1,185 forecasts, including 80 abnormal events. Transparent rules, logistic regression, a decision tree and a random forest are compared using chronological validation and an untouched 2026 test period. The current gap rule records the strongest test PR AUC of 0.290, compared with a no skill value of 0.159. Logistic regression is the best probability classifier, with a test PR AUC of 0.267 and Brier score of 0.134. Under a 10 percent alert budget, the current gap rule identifies 8 of 34 test events with 36.4 percent precision. The results show that a simple, auditable signal can outperform more complex classifiers when market conditions change. The system should therefore be interpreted as a risk monitoring aid rather than a trading recommendation.')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
r=p.add_run('Keywords  '); r.bold=True
p.add_run('exchange traded funds, price NAV dislocation, NIFTYBEES, early warning, interpretable machine learning, PR AUC, calibration')

doc.add_page_break()

doc.add_heading('1 Introduction and Business Problem', level=1)
add_body('An exchange traded fund is priced in two connected markets. Its units trade continuously on an exchange, while its net asset value is calculated from the value of the underlying portfolio. Creation and redemption by authorized participants should limit large differences between these two values, but the mechanism is not frictionless. Trading costs, inventory constraints, thin secondary market liquidity, stale component prices and sudden order imbalances can allow the exchange price to trade temporarily above or below NAV.')
add_body('For an investor, a large premium or discount is an execution risk. A buyer may pay substantially more than the value represented by the underlying portfolio, while a seller may accept an unusually low price. For an ETF sponsor, trading desk or market maker, a widening price NAV gap may also signal liquidity stress or delayed arbitrage. The business problem is therefore to identify an elevated risk of abnormal dislocation before the next trading session. The objective is not to forecast general equity returns or promise an arbitrage profit.')
add_body('This project studies NIFTYBEES as a carefully audited pilot. The broader title refers to the intended ETF risk monitoring framework, but the empirical claims in this report apply only to NIFTYBEES. Restricting the first implementation to one scheme avoids combining funds before scheme identity, listing history, benchmark and NAV publication timing are reconciled.')

doc.add_heading('2 Literature Review', level=1)
doc.add_heading('2.1 ETF pricing and the arbitrage mechanism', level=2)
add_body('ETF market prices can deviate from reported NAV even though authorized participants can create or redeem units. Hilliard [8] models premiums and discounts as a mean reverting process with jumps and finds that pricing efficiency differs across asset classes. Petajisto [7] documents economically meaningful pricing bands and shows that larger deviations are associated with international and less liquid holdings. These studies establish that the arbitrage mechanism narrows price differences but does not eliminate them at every point in time.')
add_body('Liquidity is central to the speed and cost of correction. Bae and Kim [9] find that illiquid ETFs have larger tracking errors and that the effect is stronger when underlying assets are also illiquid. Rappoport and Tuzun [10] likewise show that market liquidity affects the efficacy of ETF arbitrage. Pan and Zeng [12] demonstrate how authorized participants balance their arbitrage role against dealer inventory and balance sheet constraints. Although some of this evidence comes from fixed income ETFs, the underlying implication is relevant to equity ETFs: observed premiums and discounts may reflect limits to immediate arbitrage as well as information differences.')

doc.add_heading('2.2 Evidence from India', level=2)
add_body('Indian studies provide direct evidence that price NAV deviations deserve separate analysis. Reddy and Dhabolkar [5] examine pricing efficiency using autoregressive and vector error correction methods and report persistent deviations and lead lag relationships between NAV and market prices. Goel and Ahluwalia [6] study 24 Indian equity ETFs and find that premiums, discounts and tracking errors remain material despite apparently low arbitrage constraints. They identify bid ask spreads, NAV momentum, market capitalization and operational constraints as relevant to pricing efficiency. This literature supports the use of liquidity, trading activity, underlying market movement and volatility as predictors.')
add_body('The existing Indian literature is mainly explanatory or contemporaneous. It measures tracking error, tests long run relationships, estimates the speed of correction or studies fund characteristics. These are important questions, but they do not directly answer whether information available after the current day NAV publication can warn of an abnormal dislocation on the next actual trading day.')

doc.add_heading('2.3 Volatility, stress and interpretability', level=2)
add_body('ETF arbitrage can transmit shocks between the fund and its underlying securities. Ben David, Franzoni and Moussawi [11] find that greater ETF ownership is associated with higher volatility and short horizon price reversals in underlying stocks. This motivates the inclusion of India VIX and NIFTY 50 movements as market stress controls rather than treating the ETF in isolation.')
add_body('The prediction task is imbalanced because abnormal dislocations are intentionally rare. Saito and Rehmsmeier [13] show why precision recall analysis is more informative than ROC analysis when positive observations are scarce. Probability quality also matters because an early warning system communicates risk rather than only a class label. Guo et al. [14] emphasize that predictive accuracy and probability calibration are different properties. The project therefore reports PR AUC, Brier score, calibration diagnostics and performance under a fixed alert budget. It also retains simple rules and logistic regression because transparent models are easier to audit when predictions influence financial decisions [15].')

doc.add_heading('2.4 Research gap and contribution', level=2)
add_body('Among the studies reviewed, we did not identify an Indian equity ETF study that combines a post NAV prediction timestamp, an ETF specific rolling event definition, purged chronological evaluation, probability calibration and a constrained alert budget. This project addresses that methodological gap through a single ETF pilot. Its contribution is a leakage controlled early warning design and an empirical comparison of transparent rules with classifiers. It does not claim that NIFTYBEES results generalize automatically to all Indian ETFs.')

add_caption('Table 1  Position of the study relative to selected literature')
add_table(
    ['Study','Market and method','Main relevance','Difference from this project'],
    [
        ['Reddy and Dhabolkar 2020','Indian ETFs; autoregression and VECM','Price NAV persistence and lead lag behaviour','Explains pricing efficiency; does not predict next day abnormal events'],
        ['Goel and Ahluwalia 2021','24 Indian equity ETFs; efficiency and fund characteristics','Indian discounts, tracking error and operational constraints','Cross fund explanatory analysis rather than post NAV warning'],
        ['Petajisto 2017','Multiple ETF asset classes; pricing bands','Mispricing persists despite arbitrage','Focuses pricing inefficiency and mean reversion'],
        ['Bae and Kim 2020','US ETFs; liquidity and tracking error','Illiquidity increases deviations and risk','Does not construct an event classifier'],
        ['Rappoport and Tuzun 2020','Equity and bond ETF panel; arbitrage and liquidity','Liquidity affects arbitrage efficacy','Studies mechanism rather than operational warning'],
        ['Current study','NIFTYBEES; rolling label and chronological classifiers','Next day warning, calibration and alert budget','Single fund pilot with leakage safe implementation'],
    ],
    widths=[1.4,1.8,2.0,2.1], font_size=8.3
)

doc.add_heading('3 Research Question and Objectives', level=1)
add_body('Research question: Can information available after the current trading day NAV publication predict whether NIFTYBEES will experience an abnormally large price NAV dislocation on the next actual NSE trading day?')
for item in [
    'Construct a reproducible daily panel using official market price, NAV, benchmark and volatility data.',
    'Define abnormal dislocations relative to the ETF own trailing history without using future information.',
    'Compare a simple alert rule with logistic regression, decision tree and random forest classifiers.',
    'Evaluate ranking, probability calibration and operational usefulness under a limited alert budget.',
    'Explain the main signals and document limitations that affect interpretation and deployment.'
]: add_bullet(item)

doc.add_heading('4 Data and Data Quality', level=1)
add_body('The observation unit is one NIFTYBEES trading date. Market price and liquidity fields come from official NSE security level reports. NAV observations use the AMFI historical NAV service for scheme code 140084, verified against the scheme name and ISIN. NIFTY 50 historical index data provide underlying market controls, and official NSE India VIX data provide the market volatility control. The study period runs from 1 January 2021 through 16 November 2026.')
add_caption('Table 2  Final data coverage')
add_table(
    ['Dataset','Rows','Coverage','Use'],
    [
        ['NIFTYBEES market data','1,456','1 Jan 2021 to 16 Nov 2026','Prices and liquidity'],
        ['Official AMFI NAV','1,451','1 Jan 2021 to 16 Nov 2026','Price NAV dislocation'],
        ['NIFTY 50','1,456','1 Jan 2021 to 16 Nov 2026','Underlying market control'],
        ['India VIX','1,455','1 Jan 2021 to 16 Nov 2026','Volatility control'],
        ['Complete case panel','1,446','1 Jan 2021 to 16 Nov 2026','Feature and label construction'],
    ], widths=[1.9,0.8,2.0,2.1], font_size=8.8
)
add_body('Eight special or Muhurat market sessions have exchange trading records but no corresponding AMFI NAV and are excluded when the next actual market session lacks a complete target. Three AMFI NAV reporting dates occur without an NSE market session. Two India VIX source zero anomalies, dated 12 February 2021 and 30 March 2021, are excluded. Extreme ETF price NAV differences were retained only after checking their source values; the largest absolute dislocation is 3.010 percent on 4 June 2024.')

doc.add_heading('5 Methodology', level=1)
doc.add_heading('5.1 Prediction timestamp and dislocation', level=2)
add_body('The forecast is made after AMFI publishes the NAV for trading date t. SEBI disclosure requirements specify that NAV is normally made available on AMFI and mutual fund websites by 11 p.m. on the business day [4]. At that point the ETF closing price, trading activity, NIFTY 50 close, India VIX and the date t NAV are available. The prediction concerns the next actual NSE trading date.')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run('d_t = 100 x (ETF closing price_t - NAV_t) / NAV_t'); r.font.name='Cambria Math'; r.font.size=Pt(11); r.bold=True
add_body('The signed value identifies a premium or discount, while the absolute value measures the size of the dislocation regardless of direction.')

doc.add_heading('5.2 Forward label and leakage controls', level=2)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run('y_(t+1) = 1 when |d_(t+1)| > rolling 95th percentile of the 252 complete observations ending on t'); r.font.name='Cambria Math'; r.font.size=Pt(10.5); r.bold=True
add_body('The target date cannot influence its own threshold. A row enters the modelling dataset only when date t is complete, the immediately following market session is complete, all selected predictors are available and 252 complete historical observations exist. Samples are assigned by target date. One overlapping label interval is purged at each train validation and validation test boundary. The final dataset contains 1,185 leakage safe observations.')

doc.add_heading('5.3 Predictors and models', level=2)
add_body('The predictor set contains 25 variables available by date t: current and lagged signed dislocations, current absolute dislocation, rolling five and 20 day dislocation summaries, ETF and NAV returns, NIFTY 50 returns, ETF minus index return differences, India VIX level and changes, volume, turnover, average trade value, delivery percentage and intraday range. Log transformations are applied to volume and turnover. The current gap rule uses the ratio of the current absolute dislocation to the rolling 95th percentile threshold as a transparent continuous risk score.')
add_body('Three classifiers are estimated: L2 regularized logistic regression, a bounded decision tree and a random forest. Hyperparameters are selected using validation PR AUC only. The models are trained on the training sample and remain locked for the test evaluation. The test labels are not used for feature selection, model selection or alert threshold selection.')

add_caption('Table 3  Chronological design')
add_table(
    ['Partition','Target period','Observations','Abnormal events','Event rate'],
    [
        ['Training','12 Jan 2022 to 30 Dec 2024','725','41','5.66%'],
        ['Validation','1 Jan 2025 to 30 Dec 2025','246','5','2.03%'],
        ['Testing','1 Jan 2026 to 16 Nov 2026','214','34','15.89%'],
        ['Total','12 Jan 2022 to 16 Nov 2026','1,185','80','6.75%'],
    ], widths=[1.2,2.2,1.0,1.1,1.0], font_size=8.8
)

doc.add_heading('5.4 Evaluation', level=2)
add_body('PR AUC is the primary ranking metric because the positive class is uncommon and the practical question is whether high risk scores concentrate genuine events. ROC AUC is reported as a secondary discrimination measure. Brier score, log loss, calibration intercept, calibration slope and five bin expected calibration error assess probability quality. Operational usefulness is evaluated by allowing alerts on only the highest scored 10 percent of dates. A second check freezes the validation score threshold and applies it unchanged to testing, revealing whether score distributions and alert volumes drift.')

doc.add_heading('6 Results', level=1)
doc.add_heading('6.1 Out of time model comparison', level=2)
add_caption('Table 4  Test performance')
add_table(
    ['Model','PR AUC','ROC AUC','Lift over no skill','Brier score','ECE'],
    [
        ['Historical prevalence','0.159','0.500','0.0%','0.144','0.102'],
        ['Current gap rule','0.290','0.642','82.8%','Not applicable','Not applicable'],
        ['Logistic regression','0.267','0.543','68.4%','0.134','0.079'],
        ['Decision tree','0.206','0.605','29.8%','0.152','0.094'],
        ['Random forest','0.202','0.599','27.1%','0.162','0.118'],
    ], widths=[1.6,0.8,0.8,1.1,1.0,0.8], font_size=8.7
)
add_body('Random forest achieved the highest validation PR AUC of 0.276 and was therefore the model selected under the predeclared rule. It did not retain that advantage in the untouched test period. The current gap rule achieved the highest test PR AUC of 0.290, followed by logistic regression at 0.267. Both substantially exceed the test event prevalence of 0.159, which is the no skill PR AUC. The finding does not justify replacing the validation selection rule after observing test outcomes. It instead shows that a simple signal generalized better under the 2026 conditions.')
add_caption('Figure 1  Model ranking in the untouched test period')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
p.add_run().add_picture(str(FIG1), width=Inches(6.7))

doc.add_heading('6.2 Alert budget performance', level=2)
add_caption('Table 5  Test alerts under a 10 percent budget')
add_table(
    ['Model','Alerts','True events identified','Precision','Recall'],
    [
        ['Current gap rule','22','8','36.4%','23.5%'],
        ['Logistic regression','22','7','31.8%','20.6%'],
        ['Decision tree','22','5','22.7%','14.7%'],
        ['Random forest','22','4','18.2%','11.8%'],
    ], widths=[1.9,0.8,1.5,1.0,1.0], font_size=8.8
)
add_body('The current gap rule identifies eight of the 34 abnormal test events while issuing 22 alerts. Its alert precision of 36.4 percent is more than twice the unconditional test event rate. Logistic regression identifies seven events with 31.8 percent precision. The result supports an operational design that ranks dates and limits review capacity instead of using a universal probability cutoff.')
add_caption('Figure 2  Precision when only 10 percent of test dates can be flagged')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
p.add_run().add_picture(str(FIG2), width=Inches(6.7))

doc.add_heading('6.3 Calibration and model explanations', level=2)
add_body('Logistic regression is the strongest probability classifier in testing. Its Brier score of 0.134 improves on the historical prevalence benchmark of 0.144, and its mean predicted probability of 15.12 percent is close to the actual test event rate of 15.89 percent. Its calibration slope of 0.355 nevertheless indicates that cross sectional probability differences are too extreme or unstable. Random forest predicts an average probability of 24.78 percent and has a worse Brier score of 0.162, showing overprediction during the shifted test regime.')
add_body('For logistic regression, the largest standardized coefficients are associated with ETF turnover, India VIX level and change, delivery percentage and recent dislocation values. Random forest gives its highest importance to the current gap to threshold ratio and the previous day signed dislocation. These patterns are consistent with persistence and liquidity channels discussed in the literature, but they are predictive associations rather than causal estimates. Correlated predictors also mean that individual coefficients and feature importances should not be interpreted in isolation.')

doc.add_heading('7 Discussion', level=1)
add_body('The most important empirical result is that added model complexity did not produce the best out of time warning performance. Random forest fit the sparse 2025 validation events well enough to win the selection stage, but the transparent current gap rule ranked 2026 outcomes more effectively. This result supports the project emphasis on interpretable baselines. A model comparison is informative only when the simple rule is treated as a genuine competitor rather than a weak formality.')
add_body('The shift in event frequency is equally important. Abnormal events represent 2.03 percent of validation dates and 15.89 percent of test dates. A score threshold calibrated to issue about 10 percent alerts in validation flags 39.3 percent of test dates for the current gap rule, 22.9 percent for logistic regression and 33.6 percent for random forest. The score distributions therefore changed materially. A live system should monitor event prevalence, probability calibration and alert volume and should recalibrate or retrain only under a documented schedule.')
add_body('The results also clarify how the system should be presented to a business user. It is a screening mechanism that prioritizes dates for review. A high score does not establish that an arbitrage is executable, because transaction costs, bid ask spreads, market impact, creation unit requirements and the timing of NAV publication are outside the current target. The warning can help an investor pause, compare current price with NAV or iNAV, inspect liquidity and use a limit order. It should not automatically trigger a trade.')

doc.add_heading('8 Managerial and Analytical Implications', level=1)
for item in [
    'Use the current gap ratio as the first line ranking signal because it is transparent and performed best in the test period.',
    'Use logistic regression when a probability estimate is required, but display calibration and drift warnings beside the probability.',
    'Cap alerts by review capacity, such as the highest risk 10 percent of dates, rather than relying only on a fixed score threshold.',
    'Recheck source timing and extreme values before escalating an alert, especially on special trading sessions and volatile market days.',
    'Treat feature importance as an explanation of model behaviour, not evidence that turnover, volatility or delivery activity causes dislocation.'
]: add_bullet(item)

doc.add_heading('9 Limitations and Future Work', level=1)
add_body('The study uses one highly traded broad market ETF. The result may not extend to sectoral, thematic, international, gold, debt or lower liquidity ETFs. A multi ETF panel should be added only after scheme codes, ISINs, benchmark mappings, listing histories, corporate actions and NAV publication schedules are reconciled for every fund.')
add_body('Daily closing price and end of day NAV may not capture intraday arbitrage dynamics. Future work could incorporate bid ask spreads, order book measures, iNAV, authorized participant flows and creation redemption activity where reliable data are available. The event definition is relative to the ETF recent history and is therefore suitable for monitoring, but sensitivity checks should compare the 95th percentile label with fixed economic thresholds such as 0.50 percent and 1.00 percent.')
add_body('Only five validation events are available, making hyperparameter choice and calibration estimates uncertain. Future evaluation should use walk forward folds across additional ETFs and market regimes. Statistical uncertainty should be reported through confidence intervals or bootstrap procedures that respect time dependence. Transaction costs and executable trading returns are outside this study and must be analysed separately before any investment interpretation.')

doc.add_heading('10 Conclusion', level=1)
add_body('This project converts an ETF pricing efficiency question into a leakage safe next trading day warning task. Official market, NAV, benchmark and volatility data support 1,446 complete NIFTYBEES observations and 1,185 eligible forecasts after the historical lookback and boundary purging rules are applied. The current gap rule produces the strongest test ranking performance, and logistic regression provides the most useful probability estimates among the classifiers. Decision tree and random forest add comparison evidence but do not improve the final out of time result.')
add_body('The central conclusion is practical: an explainable monitoring system is feasible, but stable alert capacity matters more than choosing the most complex model. The system should rank risk, limit alerts, expose its drivers and monitor calibration as market conditions change. The evidence supports a NIFTYBEES pilot and a carefully controlled expansion to other Indian ETFs; it does not support automated trading or general claims about the entire ETF market.')

doc.add_heading('11 Reproducibility', level=1)
add_body('Repository URL: insert public or institution accessible GitHub repository URL before submission.')
add_body('The repository should contain a README with the exact execution order, Python environment and file provenance. Raw downloaded files should remain unchanged in a source directory. Processing scripts should generate the cleaned market, NAV, NIFTY 50 and India VIX files, followed by the merged master panel, analysis ready panel, leakage safe modelling dataset and model comparison outputs.')
for item in [
    'data raw: original NSE, AMFI, NIFTY 50 and India VIX downloads.',
    'data processed: cleaned source files, merged panel and modelling dataset.',
    'scripts: data audit, feature and label construction, model comparison and report figure generation.',
    'outputs: audit workbooks, model metrics, row level predictions and figures.',
    'environment file: pinned versions of Python, pandas, NumPy, scikit learn and plotting packages.',
    'README: commands, expected row counts, split dates, random seed 42 and descriptions of every output.'
]: add_bullet(item)
add_body('Reproduction checks should confirm 1,456 market rows, 1,451 AMFI NAV rows, 1,446 complete cases, 1,185 modelling observations and 80 abnormal events. Model training uses random seed 42. The test set must remain isolated until all model and threshold choices are frozen.')

doc.add_heading('12 Artificial Intelligence Use Disclosure', level=1)
add_body('Generative artificial intelligence tools were used to assist literature discovery, code drafting, language editing and document formatting. The student authors selected the research design, reviewed the cited sources, verified the official data, executed and checked the analysis, and remain responsible for all interpretations and errors. AI generated text and code were not accepted without human review. No confidential personal data were provided to the tools.')

doc.add_heading('References', level=1)
refs = [
    '[1] National Stock Exchange of India, Security wise price, volume and deliverable position data, https://www.nseindia.com/report-detail/eq_security.',
    '[2] Association of Mutual Funds in India, Historical NAV download, https://www.amfiindia.com/net-asset-value/nav-download.',
    '[3] NSE Indices, Historical index data, https://www.niftyindices.com/reports.',
    '[4] Securities and Exchange Board of India, Master Circular for Mutual Funds, NAV disclosure requirements, 2026.',
    '[5] Y. V. Reddy and P. Dhabolkar, Pricing Efficiency of Exchange Traded Funds in India, Organizations and Markets in Emerging Economies, vol. 11, no. 1, pp. 244 to 268, 2020, doi:10.15388/omee.2020.11.33.',
    '[6] G. Goel and E. Ahluwalia, Do pricing efficiencies in Indian equity ETF market impact its performance, Global Finance Journal, vol. 49, art. 100654, 2021, doi:10.1016/j.gfj.2021.100654.',
    '[7] A. Petajisto, Inefficiencies in the Pricing of Exchange Traded Funds, Financial Analysts Journal, vol. 73, no. 1, pp. 24 to 54, 2017, doi:10.2469/faj.v73.n1.7.',
    '[8] J. Hilliard, Premiums and discounts in ETFs: An analysis of the arbitrage mechanism in domestic and international funds, Global Finance Journal, vol. 25, no. 2, pp. 90 to 107, 2014.',
    '[9] K. Bae and D. Kim, Liquidity risk and exchange traded fund returns, variances, and tracking errors, Journal of Financial Economics, vol. 138, no. 1, pp. 222 to 253, 2020, doi:10.1016/j.jfineco.2019.02.012.',
    '[10] D. E. Rappoport W. and T. Tuzun, Arbitrage and Liquidity: Evidence from a Panel of Exchange Traded Funds, Finance and Economics Discussion Series 2020 097, Federal Reserve Board, 2020, doi:10.17016/FEDS.2020.097.',
    '[11] I. Ben David, F. Franzoni, and R. Moussawi, Do ETFs Increase Volatility, Journal of Finance, vol. 73, no. 6, pp. 2471 to 2535, 2018, doi:10.1111/jofi.12727.',
    '[12] K. Pan and Y. Zeng, ETF Arbitrage Under Liquidity Mismatch, SSRN Working Paper 2895478, 2019, doi:10.2139/ssrn.2895478.',
    '[13] T. Saito and M. Rehmsmeier, The Precision Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets, PLOS ONE, vol. 10, no. 3, e0118432, 2015, doi:10.1371/journal.pone.0118432.',
    '[14] C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, On Calibration of Modern Neural Networks, Proceedings of the 34th International Conference on Machine Learning, vol. 70, pp. 1321 to 1330, 2017.',
    '[15] C. Rudin, Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead, Nature Machine Intelligence, vol. 1, pp. 206 to 215, 2019, doi:10.1038/s42256-019-0048-x.'
]
for ref in refs:
    p=doc.add_paragraph()
    p.paragraph_format.left_indent=Inches(0.2)
    p.paragraph_format.first_line_indent=Inches(-0.2)
    p.paragraph_format.space_after=Pt(3)
    r=p.add_run(ref); r.font.size=Pt(9)

for section in doc.sections:
    add_page_number(section.footer.paragraphs[0])

doc.core_properties.title = 'ETF Project Revised Second Review Draft'
doc.core_properties.subject = 'NIFTYBEES price NAV dislocation early warning system'
doc.core_properties.author = 'Ansh Kotwal, Anish Mayya, Rohit Agarwal'

OUT.mkdir(parents=True, exist_ok=True)
doc.save(DOCX)
print(DOCX)
