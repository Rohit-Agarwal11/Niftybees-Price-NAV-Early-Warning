from copy import deepcopy
from pathlib import Path
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'report' / 'ETF_Project_Final_Integrated_Draft.docx'
OUT = ROOT / 'report' / 'ETF_Project_Final_Overleaf_Style.docx'
doc=Document(SRC)

# Helpers
def set_cell_margins(cell, top=35, start=45, bottom=35, end=45):
    tc=cell._tc; tcPr=tc.get_or_add_tcPr(); tcMar=tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar=OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m,v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        e=tcMar.find(qn('w:'+m))
        if e is None: e=OxmlElement('w:'+m); tcMar.append(e)
        e.set(qn('w:w'),str(v)); e.set(qn('w:type'),'dxa')

def set_columns(sectPr, num, space=360):
    cols=sectPr.find(qn('w:cols'))
    if cols is None:
        cols=OxmlElement('w:cols'); sectPr.append(cols)
    cols.set(qn('w:num'),str(num)); cols.set(qn('w:space'),str(space))

def continuous_sectpr(num):
    sp=OxmlElement('w:sectPr')
    typ=OxmlElement('w:type'); typ.set(qn('w:val'),'continuous'); sp.append(typ)
    pg=OxmlElement('w:pgSz'); pg.set(qn('w:w'),'12240'); pg.set(qn('w:h'),'15840'); sp.append(pg)
    mar=OxmlElement('w:pgMar')
    for k,v in [('top','720'),('right','720'),('bottom','720'),('left','720'),('header','360'),('footer','360'),('gutter','0')]: mar.set(qn('w:'+k),v)
    sp.append(mar); set_columns(sp,num); return sp

def add_break_before(el, current_cols):
    p=OxmlElement('w:p'); pPr=OxmlElement('w:pPr'); pPr.append(continuous_sectpr(current_cols)); p.append(pPr); el.addprevious(p)

def add_break_after(el, current_cols):
    p=OxmlElement('w:p'); pPr=OxmlElement('w:pPr'); pPr.append(continuous_sectpr(current_cols)); p.append(pPr); el.addnext(p)

def remove_page_breaks(p):
    for br in list(p._p.iter(qn('w:br'))):
        if br.get(qn('w:type')) in (None,'page'):
            br.getparent().remove(br)

# Page setup. Title section is one column; body will become two columns.
sec=doc.sections[0]
sec.page_width=Inches(8.5); sec.page_height=Inches(11)
sec.top_margin=Inches(.5); sec.bottom_margin=Inches(.5); sec.left_margin=Inches(.5); sec.right_margin=Inches(.5)
sec.header_distance=Inches(.25); sec.footer_distance=Inches(.25)
for footer in [sec.footer, sec.first_page_footer, sec.even_page_footer]:
    for p in footer.paragraphs: p._element.getparent().remove(p._element)

# Base typography.
styles=doc.styles
for sname in ['Normal','Body Text','List Bullet','Source Note','Caption']:
    if sname in styles:
        st=styles[sname]; st.font.name='Times New Roman'; st._element.rPr.rFonts.set(qn('w:eastAsia'),'Times New Roman')
styles['Normal'].font.size=Pt(10)
styles['Normal'].paragraph_format.space_after=Pt(0)
styles['Normal'].paragraph_format.line_spacing=1.0
styles['Body Text'].font.size=Pt(10)
styles['Body Text'].paragraph_format.first_line_indent=Inches(.16)
styles['Body Text'].paragraph_format.space_after=Pt(2)
styles['Body Text'].paragraph_format.line_spacing=1.0
styles['List Bullet'].font.size=Pt(9.5)
styles['List Bullet'].paragraph_format.left_indent=Inches(.16)
styles['List Bullet'].paragraph_format.first_line_indent=Inches(-.12)
styles['List Bullet'].paragraph_format.space_after=Pt(1)
styles['Caption'].font.size=Pt(8)
styles['Caption'].font.bold=False
styles['Caption'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
styles['Caption'].paragraph_format.space_before=Pt(3)
styles['Caption'].paragraph_format.space_after=Pt(2)
styles['Source Note'].font.size=Pt(7.5)
styles['Source Note'].font.italic=True
styles['Source Note'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
styles['Source Note'].paragraph_format.space_after=Pt(3)

# Title block.
title=doc.paragraphs[0]
title.alignment=WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before=Pt(10); title.paragraph_format.space_after=Pt(2)
for r in title.runs: r.font.name='Times New Roman'; r.font.size=Pt(23); r.font.bold=False
# Remove the blue divider used by the earlier one-column report cover.
pBdr=title._p.get_or_add_pPr().find(qn('w:pBdr'))
if pBdr is not None: title._p.get_or_add_pPr().remove(pBdr)
title_style_bdr=styles['Title']._element.pPr.find(qn('w:pBdr')) if styles['Title']._element.pPr is not None else None
if title_style_bdr is not None: styles['Title']._element.pPr.remove(title_style_bdr)
subtitle=doc.paragraphs[1]; subtitle.alignment=WD_ALIGN_PARAGRAPH.CENTER
subtitle.paragraph_format.space_after=Pt(15)
for r in subtitle.runs: r.font.name='Times New Roman'; r.font.size=Pt(12); r.font.italic=False
for idx in [3,4,5]:
    p=doc.paragraphs[idx]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(0)
    for r in p.runs: r.font.name='Times New Roman'; r.font.size=Pt(10.5)
for idx in [7,8,9,11,13]:
    p=doc.paragraphs[idx]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(0)
    for r in p.runs: r.font.name='Times New Roman'; r.font.size=Pt(9.5); r.font.bold=False
# Compact/remove blank title spacer paragraphs.
for idx in [2,6,10,12,14]:
    p=doc.paragraphs[idx]; remove_page_breaks(p); p.paragraph_format.space_after=Pt(0); p.paragraph_format.space_before=Pt(0)
    for r in p.runs: r.font.size=Pt(1)
# End the full-width title block and start two columns before Abstract.
p14=doc.paragraphs[14]
pPr=p14._p.get_or_add_pPr(); pPr.append(continuous_sectpr(1))
set_columns(doc._element.body.sectPr,2)
# Letter setup on final section properties.
body_sp=doc._element.body.sectPr
pg=body_sp.find(qn('w:pgSz')); pg.set(qn('w:w'),'12240'); pg.set(qn('w:h'),'15840')
mar=body_sp.find(qn('w:pgMar'))
for k,v in [('top','720'),('right','720'),('bottom','720'),('left','720'),('header','360'),('footer','360'),('gutter','0')]: mar.set(qn('w:'+k),v)

# Remove forced page breaks from the former cover and before the Introduction.
for p in doc.paragraphs:
    remove_page_breaks(p)

# Merge Abstract label into its text, matching the Overleaf run-in style.
p_abs_h=next(p for p in doc.paragraphs if p.text=='Abstract')
abs_idx=next(i for i,p in enumerate(doc.paragraphs) if p.text=='Abstract')
p_abs=doc.paragraphs[abs_idx+1]
for r in list(p_abs.runs): r._element.getparent().remove(r._element)
r=p_abs.add_run('Abstract—'); r.bold=True; r.italic=True
r=p_abs.add_run('This study evaluates whether complex machine learning models provide more reliable next trading day warnings of abnormal NIFTYBEES price NAV dislocations than transparent benchmark rules. Official NSE market data, AMFI net asset values, NIFTY 50 observations and India VIX data are reconciled for 1 January 2021 through 16 November 2026. The final merged panel contains 1,446 complete observations. A prospective abnormal event occurs when the next trading day’s absolute dislocation exceeds the rolling 95th percentile estimated from the 252 complete observations available on the prediction date. The leakage controlled modelling sample contains 1,185 forecasts and 80 events. Three purged expanding window evaluations compare historical prevalence, current gap rules, previous event persistence, logistic regression, a decision tree and a random forest. The current gap to threshold ratio achieves the highest mean walk forward PR AUC of 0.233, compared with 0.169 for logistic regression, 0.156 for the decision tree and 0.184 for random forest. A paired moving block bootstrap establishes a 0.078 advantage over the decision tree, while intervals against logistic regression and random forest include zero. Market stress variables improve logistic regression from 0.153 to 0.195, but liquidity variables do not generate consistent gains. The gap ratio has the highest pooled precision at 5, 10 and 20 percent alert budgets. Event prevalence changes from 10.7 percent in 2024 to 2.0 percent in 2025 and 15.9 percent in 2026, producing substantial calibration and alert volume instability. The evidence supports a transparent capacity constrained monitoring system with continuing drift checks. It does not support automatic trading or universal superiority of one model.')
p_abs.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; p_abs.paragraph_format.first_line_indent=Inches(.16); p_abs.paragraph_format.space_after=Pt(2)
p_abs_h._element.getparent().remove(p_abs_h._element)
# Index terms styling.
kw=next(p for p in doc.paragraphs if p.text.startswith('Keywords'))
text=kw.text.replace('Keywords  ','')
for r in list(kw.runs): r._element.getparent().remove(r._element)
r=kw.add_run('Index Terms—'); r.bold=True; r.italic=True
kw.add_run(text)
kw.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; kw.paragraph_format.space_after=Pt(6)

# IEEE-like section and subsection headings.
roman={1:'I',2:'II',3:'III',4:'IV',5:'V',6:'VI',7:'VII',8:'VIII',9:'IX',10:'X',11:'XI'}
current_main=None; sub_no=0
for p in doc.paragraphs:
    if p.style.name=='Heading 1':
        m=re.match(r'^(\d+)\s+(.*)$',p.text)
        if m:
            current_main=int(m.group(1)); sub_no=0
            p.text=f"{roman[current_main]}.  {m.group(2).upper()}"
        elif p.text=='Executive Summary': p.text='EXECUTIVE SUMMARY'
        elif p.text=='References': p.text='REFERENCES'
        elif p.text.startswith('Appendix A'): p.text='APPENDIX A.  REPRODUCTION OUTPUTS'
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before=Pt(7); p.paragraph_format.space_after=Pt(3); p.paragraph_format.keep_with_next=True
        for r in p.runs:
            r.font.name='Times New Roman'; r.font.size=Pt(10); r.font.bold=False; r.font.small_caps=True
    elif p.style.name=='Heading 2':
        sub_no+=1
        txt=re.sub(r'^\d+\.\d+\s+','',p.text)
        p.text=f"{chr(64+sub_no)}.  {txt}"
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before=Pt(5); p.paragraph_format.space_after=Pt(1); p.paragraph_format.keep_with_next=True
        for r in p.runs:
            r.font.name='Times New Roman'; r.font.size=Pt(10); r.font.bold=True; r.font.italic=True

# General body paragraph formatting and remove large spacing.
for pi,p in enumerate(doc.paragraphs):
    if p.style.name in ('Body Text','Normal') and pi >= 15:
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing=1.0
        if p.style.name=='Normal' and p.text and not p.text.startswith(('Index Terms','Repository URL')):
            p.paragraph_format.first_line_indent=Inches(.16)
        p.paragraph_format.space_after=Pt(2)
        for r in p.runs:
            r.font.name='Times New Roman'; r.font.size=Pt(10); r.font.color.rgb=RGBColor(0,0,0)
    if p.style.name=='List Bullet':
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        for r in p.runs: r.font.name='Times New Roman'; r.font.size=Pt(9.5); r.font.color.rgb=RGBColor(0,0,0)

# Caption conversion: TABLE I / Fig. 1.
for p in doc.paragraphs:
    if p.style.name=='Caption':
        m=re.match(r'Table\s+(\d+)\s+(.*)',p.text)
        if m:
            n=int(m.group(1)); rn=['','I','II','III','IV','V','VI','VII','VIII','IX','X','XI'][n]
            p.text=f"TABLE {rn}\n{m.group(2).upper()}"
        else:
            m=re.match(r'Figure\s+(\d+)\s+(.*)',p.text)
            if m: p.text=f"Fig. {m.group(1)}.  {m.group(2)}"
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next=True
        for r in p.runs: r.font.name='Times New Roman'; r.font.size=Pt(8); r.font.bold=False

# Tables. Wide tables span both columns; smaller tables remain column-width.
wide_indices=set(range(len(doc.tables)))
for ti,table in enumerate(doc.tables):
    table.alignment=WD_TABLE_ALIGNMENT.CENTER; table.autofit=True
    table._tbl.tblPr.tblStyle.set(qn('w:val'),'TableGrid') if table._tbl.tblPr.tblStyle is not None else None
    fs=Pt(7.2 if ti in wide_indices else 6.5)
    for ri,row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; set_cell_margins(cell)
            for p in cell.paragraphs:
                p.paragraph_format.space_before=Pt(0); p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=.9
                for r in p.runs:
                    r.font.name='Times New Roman'; r.font.size=fs; r.font.color.rgb=RGBColor(0,0,0)
                    if ri==0: r.font.bold=True
    # Remove blue shading; retain simple black rules.
    for cell in table.rows[0].cells:
        shd=cell._tc.get_or_add_tcPr().find(qn('w:shd'))
        if shd is not None: shd.set(qn('w:fill'),'FFFFFF')
    if ti in wide_indices:
        # Find the caption paragraph directly preceding the table (ignoring blank/break paragraphs).
        prev=table._tbl.getprevious()
        while prev is not None and prev.tag!=qn('w:p'): prev=prev.getprevious()
        if prev is not None: add_break_before(prev,2)
        # The final appendix table can remain in the full-width section; returning
        # to columns after it would strand the closing sentence on a blank page.
        if ti != len(doc.tables)-1:
            add_break_after(table._tbl,1)

# Figures and equations. Charts fit one column; formulas remain compact.
for i,s in enumerate(doc.inline_shapes):
    if i==0:
        if s.width>Inches(3.15):
            ratio=s.height/s.width; s.width=Inches(3.15); s.height=int(s.width*ratio)
    elif i==1:
        ratio=s.height/s.width; s.width=Inches(3.15); s.height=int(s.width*ratio)
    else:
        ratio=s.height/s.width; s.width=Inches(3.15); s.height=int(s.width*ratio)

# References: compact numbered list with hanging indentation.
start=next(i for i,p in enumerate(doc.paragraphs) if p.text=='REFERENCES')+1
for p in doc.paragraphs[start:]:
    if p.text.startswith('APPENDIX A.'): break
    if re.match(r'^\[\d+\]',p.text):
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent=Inches(.16); p.paragraph_format.first_line_indent=Inches(-.16)
        p.paragraph_format.space_after=Pt(1); p.paragraph_format.line_spacing=.9
        for r in p.runs: r.font.name='Times New Roman'; r.font.size=Pt(7.5); r.font.color.rgb=RGBColor(0,0,0)

# Keep title/captions/headings together; remove page numbers and header artifacts.
for p in doc.paragraphs:
    if p.style.name.startswith('Heading') or p.style.name=='Caption': p.paragraph_format.keep_with_next=True
for section in doc.sections:
    for hf in [section.header,section.footer,section.first_page_header,section.first_page_footer,section.even_page_header,section.even_page_footer]:
        for p in hf.paragraphs: p.clear()

# Metadata and save.
doc.core_properties.title='Does Model Complexity Improve Next Day Price NAV Dislocation Warnings'
doc.core_properties.subject='Overleaf-style two-column final integrated report'
doc.save(OUT)
print(OUT)
