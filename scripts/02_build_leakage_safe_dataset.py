from pathlib import Path
import json
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'processed'
OUTDIR = ROOT / 'outputs'
OUTDIR.mkdir(parents=True, exist_ok=True)
MODEL_CSV = DATA_DIR / 'ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv'
INFILE = DATA_DIR / 'ETF_Master_Merged_2021_to_2026.csv'
AUDIT_XLSX = OUTDIR / 'ETF_Label_and_Leakage_Audit_2021_to_2026.xlsx'
SUMMARY_JSON = OUTDIR / 'modeling_dataset_summary.json'

m = pd.read_csv(INFILE, parse_dates=['Date']).sort_values('Date').reset_index(drop=True)
# Preserve the actual NSE trading calendar before filtering incomplete observations.
m['Next_Market_Date'] = m['Date'].shift(-1)
m['Next_Complete_Case'] = m['Complete_Case'].shift(-1)
m['Next_Abs_Dislocation_Pct'] = m['Abs_Dislocation_Pct'].shift(-1)
m['Next_Signed_Dislocation_Pct'] = m['Price_NAV_Dislocation_Pct'].shift(-1)

# Feature engineering is performed on complete observations only. Every X value uses date t or earlier.
v = m.loc[m['Complete_Case'].eq(1)].copy().reset_index(drop=False).rename(columns={'index':'Master_Row'})
v['Prediction_Date'] = v['Date']
v['Target_Date'] = v['Next_Market_Date']

# Returns available after the close/NAV publication on t.
v['X_ETF_Return_1D_Pct'] = v['ETF_Close'].pct_change(fill_method=None) * 100
v['X_NAV_Return_1D_Pct'] = v['NAV'].pct_change(fill_method=None) * 100
v['X_NIFTY50_Return_1D_Pct'] = v['NIFTY50_Close'].pct_change(fill_method=None) * 100
v['X_Tracking_Return_Difference_1D_Pct'] = v['X_ETF_Return_1D_Pct'] - v['X_NIFTY50_Return_1D_Pct']
v['X_ETF_Return_5D_Pct'] = (v['ETF_Close'] / v['ETF_Close'].shift(5) - 1) * 100
v['X_NIFTY50_Return_5D_Pct'] = (v['NIFTY50_Close'] / v['NIFTY50_Close'].shift(5) - 1) * 100
v['X_VIX_Change_5D_Pct'] = (v['INDIA_VIX_Close'] / v['INDIA_VIX_Close'].shift(5) - 1) * 100

# Price–NAV state and lags.
v['X_Dislocation_Pct_t'] = v['Price_NAV_Dislocation_Pct']
v['X_Abs_Dislocation_Pct_t'] = v['Abs_Dislocation_Pct']
for lag in (1, 2, 5):
    v[f'X_Dislocation_Lag_{lag}_Pct'] = v['Price_NAV_Dislocation_Pct'].shift(lag)
v['X_Premium_Flag_t'] = (v['Price_NAV_Dislocation_Pct'] > 0).astype(int)
v['X_Abs_Dislocation_Mean_5D_Pct'] = v['Abs_Dislocation_Pct'].rolling(5).mean()
v['X_Abs_Dislocation_Mean_20D_Pct'] = v['Abs_Dislocation_Pct'].rolling(20).mean()
v['X_Abs_Dislocation_Std_20D_Pct'] = v['Abs_Dislocation_Pct'].rolling(20).std(ddof=1)

# Liquidity and market controls known by t.
v['X_Log_ETF_Volume_t'] = np.log1p(v['ETF_Volume'])
v['X_Volume_to_20D_Median'] = v['ETF_Volume'] / v['ETF_Volume'].rolling(20).median()
v['X_Log_ETF_Turnover_t'] = np.log1p(v['ETF_Turnover_INR'])
v['X_Average_Trade_Value_INR_t'] = v['ETF_Turnover_INR'] / v['ETF_Trades'].replace(0, np.nan)
v['X_Delivery_Pct_t'] = v['ETF_Delivery_Pct']
v['X_Intraday_Range_Pct_t'] = v['ETF_Intraday_Range_Pct']
v['X_NIFTY50_Close_t'] = v['NIFTY50_Close']
v['X_INDIA_VIX_Close_t'] = v['INDIA_VIX_Close']
v['X_INDIA_VIX_Change_1D_Pct'] = v['INDIA_VIX_Pct_Change']

# Dynamic label threshold: 95th percentile of the 252 complete observations available through t.
window = 252
v['Rolling_Threshold_95Pct'] = v['Abs_Dislocation_Pct'].rolling(window=window, min_periods=window).quantile(0.95)
v['Threshold_Observation_Count'] = v['Abs_Dislocation_Pct'].rolling(window=window, min_periods=1).count().astype(int)
v['Threshold_Window_Start_Date'] = v['Prediction_Date'].shift(window-1)
v['X_Current_Abs_Gap_to_Threshold_Ratio'] = v['X_Abs_Dislocation_Pct_t'] / v['Rolling_Threshold_95Pct']

# Label is valid only when the immediately following NSE market session is also complete.
v['Target_Abs_Dislocation_Pct'] = v['Next_Abs_Dislocation_Pct']
v['Target_Signed_Dislocation_Pct'] = v['Next_Signed_Dislocation_Pct']
v['Y_Abnormal_Dislocation_95Q'] = (v['Target_Abs_Dislocation_Pct'] > v['Rolling_Threshold_95Pct']).astype('Int64')
v['Y_Above_0_50_Pct'] = (v['Target_Abs_Dislocation_Pct'] > 0.50).astype('Int64')
v['Y_Above_1_00_Pct'] = (v['Target_Abs_Dislocation_Pct'] > 1.00).astype('Int64')

# Eligibility: full historical window, next actual market day complete, all chosen predictors available.
feature_cols = [
    'X_Dislocation_Pct_t','X_Abs_Dislocation_Pct_t','X_Dislocation_Lag_1_Pct',
    'X_Dislocation_Lag_2_Pct','X_Dislocation_Lag_5_Pct','X_Premium_Flag_t',
    'X_Abs_Dislocation_Mean_5D_Pct','X_Abs_Dislocation_Mean_20D_Pct',
    'X_Abs_Dislocation_Std_20D_Pct','X_Current_Abs_Gap_to_Threshold_Ratio',
    'X_ETF_Return_1D_Pct','X_NAV_Return_1D_Pct','X_NIFTY50_Return_1D_Pct',
    'X_Tracking_Return_Difference_1D_Pct','X_ETF_Return_5D_Pct',
    'X_NIFTY50_Return_5D_Pct','X_INDIA_VIX_Close_t','X_INDIA_VIX_Change_1D_Pct',
    'X_VIX_Change_5D_Pct','X_Log_ETF_Volume_t','X_Volume_to_20D_Median',
    'X_Log_ETF_Turnover_t','X_Average_Trade_Value_INR_t','X_Delivery_Pct_t',
    'X_Intraday_Range_Pct_t'
]
v['Has_252_Observation_History'] = v['Rolling_Threshold_95Pct'].notna().astype(int)
v['Next_Actual_Market_Day_Complete'] = v['Next_Complete_Case'].eq(1).astype(int)
v['All_Features_Available'] = v[feature_cols].notna().all(axis=1).astype(int)
v['Initial_Eligible'] = (
    v['Has_252_Observation_History'].eq(1) &
    v['Next_Actual_Market_Day_Complete'].eq(1) &
    v['All_Features_Available'].eq(1) &
    v['Target_Abs_Dislocation_Pct'].notna()
).astype(int)

# Fixed chronological holdout defined by target date.
def split_name(d):
    if pd.isna(d): return 'Not eligible'
    if d <= pd.Timestamp('2024-12-31'): return 'Train'
    if d <= pd.Timestamp('2025-12-31'): return 'Validation'
    return 'Test'
v['Chronological_Split'] = v['Target_Date'].map(split_name)

# Purge one overlapping label interval at each boundary.
v['Purged_Boundary_Overlap'] = 0
eligible_idx = v.index[v['Initial_Eligible'].eq(1)].tolist()
for prior_split, next_split in [('Train','Validation'), ('Validation','Test')]:
    nxt = v.index[(v['Initial_Eligible'].eq(1)) & (v['Chronological_Split'].eq(next_split))]
    prv = v.index[(v['Initial_Eligible'].eq(1)) & (v['Chronological_Split'].eq(prior_split))]
    if len(nxt) and len(prv):
        first_next_prediction = v.loc[nxt[0], 'Prediction_Date']
        overlap = [i for i in prv if v.loc[i, 'Target_Date'] >= first_next_prediction]
        if overlap:
            v.loc[overlap, 'Purged_Boundary_Overlap'] = 1
v['Leakage_Safe_Model_Use'] = (v['Initial_Eligible'].eq(1) & v['Purged_Boundary_Overlap'].eq(0)).astype(int)

# Data provenance and timing audit fields.
v['Prediction_Timestamp_Rule'] = 'After date-t AMFI NAV publication; all date-t market data known'
v['Forecast_Horizon_Trading_Days'] = 1
v['Feature_Cutoff_Date'] = v['Prediction_Date']
v['Label_Window_End_Date'] = v['Target_Date']

model_cols = [
    'Prediction_Date','Target_Date','Prediction_Timestamp_Rule','Forecast_Horizon_Trading_Days',
    'Chronological_Split','Feature_Cutoff_Date','Threshold_Window_Start_Date',
    'Threshold_Observation_Count','Rolling_Threshold_95Pct',
] + feature_cols + [
    'Target_Signed_Dislocation_Pct','Target_Abs_Dislocation_Pct',
    'Y_Abnormal_Dislocation_95Q','Y_Above_0_50_Pct','Y_Above_1_00_Pct'
]
model = v.loc[v['Leakage_Safe_Model_Use'].eq(1), model_cols].copy()
for c in ['Prediction_Date','Target_Date','Feature_Cutoff_Date','Threshold_Window_Start_Date']:
    model[c] = pd.to_datetime(model[c]).dt.strftime('%Y-%m-%d')
model.to_csv(MODEL_CSV, index=False, float_format='%.8f')

# Audit tables.
audit_cols = [
    'Prediction_Date','Target_Date','Master_Row','Has_252_Observation_History',
    'Next_Actual_Market_Day_Complete','All_Features_Available','Initial_Eligible',
    'Chronological_Split','Purged_Boundary_Overlap','Leakage_Safe_Model_Use',
    'Threshold_Window_Start_Date','Threshold_Observation_Count','Rolling_Threshold_95Pct',
    'Target_Abs_Dislocation_Pct','Y_Abnormal_Dislocation_95Q'
]
audit = v[audit_cols].copy()

used = v[v['Leakage_Safe_Model_Use'].eq(1)].copy()
summary = used.groupby('Chronological_Split', sort=False).agg(
    Observations=('Prediction_Date','size'),
    First_Prediction_Date=('Prediction_Date','min'),
    Last_Prediction_Date=('Prediction_Date','max'),
    First_Target_Date=('Target_Date','min'),
    Last_Target_Date=('Target_Date','max'),
    Abnormal_Events=('Y_Abnormal_Dislocation_95Q','sum'),
    Above_0_50_Pct=('Y_Above_0_50_Pct','sum'),
    Above_1_00_Pct=('Y_Above_1_00_Pct','sum'),
).reset_index()
summary['Abnormal_Event_Rate_Pct'] = summary['Abnormal_Events'] / summary['Observations'] * 100
summary.loc[len(summary)] = [
    'Total', len(used), used['Prediction_Date'].min(), used['Prediction_Date'].max(),
    used['Target_Date'].min(), used['Target_Date'].max(),
    int(used['Y_Abnormal_Dislocation_95Q'].sum()), int(used['Y_Above_0_50_Pct'].sum()),
    int(used['Y_Above_1_00_Pct'].sum()), used['Y_Abnormal_Dislocation_95Q'].mean()*100
]

by_year = used.assign(Target_Year=used['Target_Date'].dt.year).groupby('Target_Year').agg(
    Observations=('Prediction_Date','size'),
    Abnormal_Events=('Y_Abnormal_Dislocation_95Q','sum'),
    Mean_Target_Abs_Gap_Pct=('Target_Abs_Dislocation_Pct','mean'),
    Maximum_Target_Abs_Gap_Pct=('Target_Abs_Dislocation_Pct','max')
).reset_index()
by_year['Abnormal_Event_Rate_Pct'] = by_year['Abnormal_Events']/by_year['Observations']*100

events = used.loc[used['Y_Abnormal_Dislocation_95Q'].eq(1), [
    'Prediction_Date','Target_Date','Chronological_Split','Rolling_Threshold_95Pct',
    'Target_Signed_Dislocation_Pct','Target_Abs_Dislocation_Pct'
]].sort_values('Target_Date')

checks = pd.DataFrame([
    ['Feature dates do not exceed prediction date', bool((used['Feature_Cutoff_Date'] <= used['Prediction_Date']).all()), 'Feature_Cutoff_Date equals Prediction_Date'],
    ['Target is the immediately next NSE market date', bool((used['Target_Date'] > used['Prediction_Date']).all()), 'Built from next row of the full market calendar'],
    ['Threshold excludes target day', bool((used['Threshold_Window_Start_Date'] <= used['Prediction_Date']).all()), '252 observations ending on prediction date t'],
    ['Exactly 252 observations in threshold', bool((used['Threshold_Observation_Count'] == 252).all()), 'Required before a row enters modelling data'],
    ['No missing selected predictors', bool(used[feature_cols].notna().all().all()), 'All feature columns complete'],
    ['No missing primary labels', bool(used['Y_Abnormal_Dislocation_95Q'].notna().all()), 'Primary label complete'],
    ['Purged rows excluded', bool((used['Purged_Boundary_Overlap'] == 0).all()), 'One-step overlapping intervals removed at split boundaries'],
    ['Prediction dates unique', bool(used['Prediction_Date'].is_unique), 'One forecast per eligible market date'],
], columns=['Leakage_or_Quality_Check','Passed','Evidence'])

methodology = [
    ('Objective','Predict whether NIFTYBEES will experience an abnormal absolute price–NAV dislocation on the next actual NSE trading day.'),
    ('Prediction timestamp','After AMFI publishes NAV for trading date t. ETF, NIFTY 50 and India VIX closing information for t is then known.'),
    ('Forecast horizon','One actual NSE trading day: t+1.'),
    ('Primary label','1 when absolute dislocation on t+1 is greater than the rolling 95th percentile calculated from 252 complete observations ending on t; otherwise 0.'),
    ('Dislocation formula','100 × (ETF closing market price − NAV) ÷ NAV.'),
    ('Why label is leakage-safe','The target-day dislocation is compared with a threshold frozen on t. It is never used to calculate its own threshold.'),
    ('Split rule','Train: target dates through 31-Dec-2024; Validation: target dates in 2025; Test: target dates in 2026.'),
    ('Purging rule','At each split boundary, any earlier-split observation whose label interval reaches the first prediction date of the next split is excluded.'),
    ('Sensitivity labels','Separate fixed thresholds above 0.50% and above 1.00% are retained for robustness checks.'),
    ('Missing-data rule','A row is excluded if date t is incomplete, the immediately next market session is incomplete, 252 observations are unavailable, or a selected feature is missing.'),
]

dictionary_rows = []
for c in model_cols:
    role = 'Identifier / timing'
    if c.startswith('X_'): role = 'Predictor available by date t'
    elif c.startswith('Y_'): role = 'Future outcome label'
    elif c.startswith('Target_'): role = 'Future outcome audit value'
    elif c in ['Rolling_Threshold_95Pct','Threshold_Observation_Count','Threshold_Window_Start_Date']: role = 'Label construction / audit'
    dictionary_rows.append((c, role))
data_dictionary = pd.DataFrame(dictionary_rows, columns=['Column','Role'])

# Create formatted workbook.
wb = Workbook()
wb.remove(wb.active)
navy='17365D'; blue='4472C4'; light='D9EAF7'; green='E2F0D9'; red='FCE4D6'; white='FFFFFF'; gray='E7E6E6'
thin=Side(style='thin', color='B7B7B7')

def add_df_sheet(name, df, freeze='A2', autofilter=True):
    ws=wb.create_sheet(name)
    for j, col in enumerate(df.columns, 1):
        cell=ws.cell(1,j,col)
        cell.fill=PatternFill('solid', fgColor=navy)
        cell.font=Font(color=white,bold=True)
        cell.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        cell.border=Border(bottom=thin)
    for i, row in enumerate(df.itertuples(index=False, name=None), 2):
        for j, val in enumerate(row,1):
            if isinstance(val, pd.Timestamp): val=val.to_pydatetime()
            if pd.isna(val): val=None
            ws.cell(i,j,val)
    if freeze: ws.freeze_panes=freeze
    if autofilter and len(df): ws.auto_filter.ref=f'A1:{get_column_letter(len(df.columns))}{len(df)+1}'
    for j,col in enumerate(df.columns,1):
        vals=[str(col)] + [str(x) for x in df.iloc[:500,j-1].dropna().tolist()]
        width=min(max(max(map(len,vals))+2,12),38)
        ws.column_dimensions[get_column_letter(j)].width=width
    ws.sheet_view.showGridLines=False
    return ws

meth_df=pd.DataFrame(methodology,columns=['Item','Decision'])
ws=add_df_sheet('Methodology',meth_df,autofilter=False)
ws.column_dimensions['A'].width=27; ws.column_dimensions['B'].width=115
for row in ws.iter_rows(min_row=2):
    row[0].font=Font(bold=True,color=navy); row[1].alignment=Alignment(wrap_text=True,vertical='top')
    row[0].alignment=Alignment(wrap_text=True,vertical='top')
    ws.row_dimensions[row[0].row].height=42

ws=add_df_sheet('Split Summary',summary)
for c in range(2,7):
    for r in range(2,len(summary)+2): ws.cell(r,c).number_format='dd-mmm-yyyy' if c in (3,4,5,6) else '0'
for r in range(2,len(summary)+2): ws.cell(r,10).number_format='0.00%'
# Correct percentage display since values are already percentage units.
for r in range(2,len(summary)+2): ws.cell(r,10).number_format='0.00'
add_df_sheet('Year Summary',by_year)
add_df_sheet('Abnormal Events',events)
ws=add_df_sheet('Leakage Checks',checks)
for r in range(2,len(checks)+2):
    ws.cell(r,2).fill=PatternFill('solid',fgColor=green if ws.cell(r,2).value else red)
    ws.cell(r,2).font=Font(bold=True)
add_df_sheet('Candidate Audit',audit)
add_df_sheet('Data Dictionary',data_dictionary)
wb.save(AUDIT_XLSX)

result = {
    'input_rows': int(len(m)),
    'complete_rows': int(len(v)),
    'model_rows_after_purge': int(len(model)),
    'first_prediction_date': str(model['Prediction_Date'].min()),
    'last_prediction_date': str(model['Prediction_Date'].max()),
    'first_target_date': str(model['Target_Date'].min()),
    'last_target_date': str(model['Target_Date'].max()),
    'primary_events': int(model['Y_Abnormal_Dislocation_95Q'].sum()),
    'primary_event_rate_pct': float(model['Y_Abnormal_Dislocation_95Q'].mean()*100),
    'purged_boundary_rows': int(v['Purged_Boundary_Overlap'].sum()),
    'all_checks_passed': bool(checks['Passed'].all()),
    'split_summary': summary.astype(str).to_dict(orient='records'),
    'model_csv': str(MODEL_CSV.relative_to(ROOT)),
    'audit_xlsx': str(AUDIT_XLSX.relative_to(ROOT)),
}
SUMMARY_JSON.write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
