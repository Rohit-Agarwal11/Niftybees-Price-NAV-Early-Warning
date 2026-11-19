from pathlib import Path
import json
import math
import warnings

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, brier_score_loss, log_loss, precision_score,
    recall_score, roc_auc_score
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)
INPUT = ROOT / 'data' / 'processed' / 'ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv'
PREDICTIONS = OUT / 'ETF_Model_Comparison_Predictions_2022_to_2026.csv'
RESULTS_JSON = OUT / 'model_results.json'

df = pd.read_csv(INPUT, parse_dates=['Prediction_Date', 'Target_Date'])
feature_cols = [c for c in df.columns if c.startswith('X_')]
target = 'Y_Abnormal_Dislocation_95Q'

train = df[df['Chronological_Split'].eq('Train')].copy()
valid = df[df['Chronological_Split'].eq('Validation')].copy()
test = df[df['Chronological_Split'].eq('Test')].copy()

X_train, y_train = train[feature_cols], train[target].astype(int)
X_valid, y_valid = valid[feature_cols], valid[target].astype(int)
X_test, y_test = test[feature_cols], test[target].astype(int)

def safe_auc(y, score):
    return float(roc_auc_score(y, score)) if len(np.unique(y)) > 1 else None

def top_budget_metrics(y, score, budget=0.10):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    k = max(1, int(math.ceil(len(y) * budget)))
    order = np.argsort(-score, kind='stable')
    alert = np.zeros(len(y), dtype=int)
    alert[order[:k]] = 1
    tp = int(((alert == 1) & (y == 1)).sum())
    return {
        'Budget_Pct': budget * 100,
        'Alerts': int(k),
        'True_Positives': tp,
        'Precision_at_Budget': float(tp / k),
        'Recall_at_Budget': float(tp / max(1, y.sum())),
        'Alert_Flag': alert,
    }

def fixed_threshold_metrics(y, score, threshold):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    alert = (score >= threshold).astype(int)
    tp = int(((alert == 1) & (y == 1)).sum())
    alerts = int(alert.sum())
    return {
        'Locked_Threshold': float(threshold),
        'Alerts': alerts,
        'Alert_Rate_Pct': float(alert.mean() * 100),
        'True_Positives': tp,
        'Precision': float(tp / alerts) if alerts else 0.0,
        'Recall': float(tp / max(1, y.sum())),
        'Alert_Flag': alert,
    }

def validation_budget_threshold(score, budget=0.10):
    score = np.asarray(score, dtype=float)
    k = max(1, int(math.ceil(len(score) * budget)))
    return float(np.sort(score)[::-1][k - 1])

def calibration_stats(y, prob):
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(prob, dtype=float), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    slope_model = LogisticRegression(penalty=None, solver='lbfgs', max_iter=5000)
    slope_model.fit(logit, y)
    # Equal-frequency expected calibration error.
    q = min(5, len(np.unique(p)))
    if q < 2:
        ece = float(abs(y.mean() - p.mean()))
    else:
        bins = pd.qcut(p, q=q, duplicates='drop')
        tmp = pd.DataFrame({'y': y, 'p': p, 'bin': bins})
        agg = tmp.groupby('bin', observed=True).agg(n=('y','size'), actual=('y','mean'), predicted=('p','mean'))
        ece = float(((agg['n']/len(tmp)) * (agg['actual']-agg['predicted']).abs()).sum())
    return {
        'Brier_Score': float(brier_score_loss(y, p)),
        'Log_Loss': float(log_loss(y, p, labels=[0,1])),
        'Mean_Predicted_Probability': float(p.mean()),
        'Actual_Event_Rate': float(y.mean()),
        'Calibration_Intercept': float(slope_model.intercept_[0]),
        'Calibration_Slope': float(slope_model.coef_[0][0]),
        'ECE_5_Bins': ece,
    }

def calibration_table(y, prob, model, split):
    temp = pd.DataFrame({'Actual': np.asarray(y, dtype=int), 'Probability': np.asarray(prob, dtype=float)})
    temp['Bin'] = pd.qcut(temp['Probability'].rank(method='first'), q=5, labels=['1 Lowest','2','3','4','5 Highest'])
    out = temp.groupby('Bin', observed=False).agg(
        Observations=('Actual','size'), Actual_Events=('Actual','sum'),
        Actual_Event_Rate=('Actual','mean'), Mean_Predicted_Probability=('Probability','mean'),
        Min_Probability=('Probability','min'), Max_Probability=('Probability','max')
    ).reset_index()
    out.insert(0, 'Split', split)
    out.insert(0, 'Model', model)
    return out

models = {}
tuning_rows = []

# Logistic regression: tune C using validation PR-AUC only.
for C in [0.01, 0.1, 1.0, 10.0]:
    model = Pipeline([
        ('scale', StandardScaler()),
        ('model', LogisticRegression(C=C, penalty='l2', solver='liblinear', max_iter=5000, random_state=42))
    ])
    model.fit(X_train, y_train)
    pv = model.predict_proba(X_valid)[:, 1]
    tuning_rows.append({'Model':'Logistic Regression','Parameters':f'C={C}','Validation_PR_AUC':average_precision_score(y_valid,pv),'Validation_Brier':brier_score_loss(y_valid,pv)})
best_log = max([r for r in tuning_rows if r['Model']=='Logistic Regression'], key=lambda r:(r['Validation_PR_AUC'],-r['Validation_Brier']))
best_C = float(best_log['Parameters'].split('=')[1])
log_model = Pipeline([
    ('scale', StandardScaler()),
    ('model', LogisticRegression(C=best_C, penalty='l2', solver='liblinear', max_iter=5000, random_state=42))
])
log_model.fit(X_train, y_train)
models['Logistic Regression'] = log_model

# Small decision tree: transparent classifier with tuning limited to depth and leaf size.
for depth in [2, 3, 4, 5]:
    for leaf in [10, 25, 50]:
        for weight in [None, 'balanced']:
            model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, class_weight=weight, random_state=42)
            model.fit(X_train, y_train)
            pv = model.predict_proba(X_valid)[:, 1]
            tuning_rows.append({'Model':'Decision Tree','Parameters':f'depth={depth}; leaf={leaf}; weight={weight}','Validation_PR_AUC':average_precision_score(y_valid,pv),'Validation_Brier':brier_score_loss(y_valid,pv)})
best_tree = max([r for r in tuning_rows if r['Model']=='Decision Tree'], key=lambda r:(r['Validation_PR_AUC'],-r['Validation_Brier']))
parts = dict(p.split('=') for p in best_tree['Parameters'].split('; '))
tree_model = DecisionTreeClassifier(
    max_depth=int(parts['depth']), min_samples_leaf=int(parts['leaf']),
    class_weight=None if parts['weight']=='None' else parts['weight'], random_state=42
)
tree_model.fit(X_train, y_train)
models['Decision Tree'] = tree_model

# Random forest: modest grid suitable for a college project.
for depth in [3, 5, None]:
    for leaf in [5, 10, 20]:
        for max_features in ['sqrt', 0.5]:
            for weight in [None, 'balanced_subsample']:
                model = RandomForestClassifier(
                    n_estimators=400, max_depth=depth, min_samples_leaf=leaf,
                    max_features=max_features, class_weight=weight,
                    random_state=42, n_jobs=-1
                )
                model.fit(X_train, y_train)
                pv = model.predict_proba(X_valid)[:, 1]
                tuning_rows.append({
                    'Model':'Random Forest',
                    'Parameters':f'depth={depth}; leaf={leaf}; max_features={max_features}; weight={weight}',
                    'Validation_PR_AUC':average_precision_score(y_valid,pv),
                    'Validation_Brier':brier_score_loss(y_valid,pv)
                })
best_rf = max([r for r in tuning_rows if r['Model']=='Random Forest'], key=lambda r:(r['Validation_PR_AUC'],-r['Validation_Brier']))
parts = dict(p.split('=') for p in best_rf['Parameters'].split('; '))
rf_model = RandomForestClassifier(
    n_estimators=400,
    max_depth=None if parts['depth']=='None' else int(parts['depth']),
    min_samples_leaf=int(parts['leaf']),
    max_features='sqrt' if parts['max_features']=='sqrt' else float(parts['max_features']),
    class_weight=None if parts['weight']=='None' else parts['weight'],
    random_state=42, n_jobs=-1
)
rf_model.fit(X_train, y_train)
models['Random Forest'] = rf_model

scores = {}
prevalence = float(y_train.mean())
for split_name, split_df in [('Train', train), ('Validation', valid), ('Test', test)]:
    scores[('Historical Prevalence', split_name)] = np.repeat(prevalence, len(split_df))
    scores[('Current Gap Rule', split_name)] = split_df['X_Current_Abs_Gap_to_Threshold_Ratio'].to_numpy(float)
    for name, model in models.items():
        scores[(name, split_name)] = model.predict_proba(split_df[feature_cols])[:, 1]

metric_rows = []
budget_rows = []
locked_rows = []
calibration_rows = []
probability_models = ['Historical Prevalence', 'Logistic Regression', 'Decision Tree', 'Random Forest']
all_models = ['Historical Prevalence', 'Current Gap Rule', 'Logistic Regression', 'Decision Tree', 'Random Forest']
operational_models = ['Current Gap Rule', 'Logistic Regression', 'Decision Tree', 'Random Forest']
split_map = {'Train':train, 'Validation':valid, 'Test':test}

for name in all_models:
    valid_score = scores[(name, 'Validation')]
    locked_threshold = validation_budget_threshold(valid_score, 0.10)
    for split_name in ['Validation', 'Test']:
        split_df = split_map[split_name]
        y = split_df[target].astype(int).to_numpy()
        score = scores[(name, split_name)]
        row = {
            'Model': name, 'Split': split_name, 'Observations':len(y), 'Events':int(y.sum()),
            'Event_Rate_Pct':float(y.mean()*100),
            'PR_AUC':float(average_precision_score(y, score)),
            'ROC_AUC':safe_auc(y, score),
        }
        if name in probability_models:
            row.update(calibration_stats(y, score))
            calibration_rows.append(calibration_table(y, score, name, split_name))
        else:
            row.update({k:None for k in ['Brier_Score','Log_Loss','Mean_Predicted_Probability','Actual_Event_Rate','Calibration_Intercept','Calibration_Slope','ECE_5_Bins']})
        metric_rows.append(row)

        if name in operational_models:
            bm = top_budget_metrics(y, score, 0.10)
            budget_rows.append({k:v for k,v in {'Model':name,'Split':split_name,**bm}.items() if k!='Alert_Flag'})
            lm = fixed_threshold_metrics(y, score, locked_threshold)
            locked_rows.append({k:v for k,v in {'Model':name,'Split':split_name,**lm}.items() if k!='Alert_Flag'})

metrics = pd.DataFrame(metric_rows)
budgets = pd.DataFrame(budget_rows)
locked = pd.DataFrame(locked_rows)
calibration = pd.concat(calibration_rows, ignore_index=True)
tuning = pd.DataFrame(tuning_rows).sort_values(['Model','Validation_PR_AUC','Validation_Brier'], ascending=[True,False,True])

# Select the classifier on validation PR-AUC only. The test period remains untouched.
classifier_names = list(models.keys())
validation_classifier_metrics = metrics[(metrics['Split']=='Validation') & metrics['Model'].isin(classifier_names)]
selected_model = validation_classifier_metrics.sort_values(['PR_AUC','Brier_Score'], ascending=[False,True]).iloc[0]['Model']

# Feature explanations from the fitted training-only models.
log_coef = pd.DataFrame({
    'Feature': feature_cols,
    'Standardized_Coefficient': log_model.named_steps['model'].coef_[0]
})
log_coef['Absolute_Coefficient'] = log_coef['Standardized_Coefficient'].abs()
log_coef['Direction'] = np.where(log_coef['Standardized_Coefficient'] >= 0, 'Higher predicted risk', 'Lower predicted risk')
log_coef = log_coef.sort_values('Absolute_Coefficient', ascending=False)

tree_importance = pd.DataFrame({'Feature':feature_cols, 'Importance':tree_model.feature_importances_}).sort_values('Importance',ascending=False)
rf_importance = pd.DataFrame({'Feature':feature_cols, 'Importance':rf_model.feature_importances_}).sort_values('Importance',ascending=False)
tree_rules = export_text(tree_model, feature_names=feature_cols, decimals=4)

# Row-level prediction output with exact 10% ranking alerts and locked-threshold alerts.
pred = df[['Prediction_Date','Target_Date','Chronological_Split','Target_Abs_Dislocation_Pct',target]].copy()
pred['Historical_Prevalence_Probability'] = prevalence
pred['Current_Gap_Rule_Score'] = df['X_Current_Abs_Gap_to_Threshold_Ratio']
for name, model in models.items():
    key = name.replace(' ', '_')
    pred[f'{key}_Probability'] = model.predict_proba(df[feature_cols])[:,1]

for name in operational_models:
    score_col = {
        'Historical Prevalence':'Historical_Prevalence_Probability',
        'Current Gap Rule':'Current_Gap_Rule_Score',
        'Logistic Regression':'Logistic_Regression_Probability',
        'Decision Tree':'Decision_Tree_Probability',
        'Random Forest':'Random_Forest_Probability',
    }[name]
    valid_threshold = validation_budget_threshold(pred.loc[pred['Chronological_Split']=='Validation',score_col], 0.10)
    pred[f'{name.replace(" ","_")}_Locked_Alert'] = (pred[score_col] >= valid_threshold).astype(int)
    pred[f'{name.replace(" ","_")}_Top10Pct_Alert'] = 0
    for split_name in ['Validation','Test']:
        idx = pred.index[pred['Chronological_Split'].eq(split_name)]
        k = max(1, math.ceil(len(idx)*0.10))
        top_idx = pred.loc[idx].sort_values(score_col, ascending=False, kind='stable').head(k).index
        pred.loc[top_idx, f'{name.replace(" ","_")}_Top10Pct_Alert'] = 1

for c in ['Prediction_Date','Target_Date']:
    pred[c] = pd.to_datetime(pred[c]).dt.strftime('%Y-%m-%d')
pred.to_csv(PREDICTIONS, index=False, float_format='%.8f')

summary = {
    'selected_model': selected_model,
    'selection_rule': 'Highest validation PR-AUC; Brier score breaks ties',
    'train_rows': len(train), 'validation_rows':len(valid), 'test_rows':len(test),
    'train_events':int(y_train.sum()), 'validation_events':int(y_valid.sum()), 'test_events':int(y_test.sum()),
    'train_prevalence':prevalence,
    'best_parameters': {
        'Logistic Regression': best_log['Parameters'],
        'Decision Tree': best_tree['Parameters'],
        'Random Forest': best_rf['Parameters'],
    },
    'metrics': metrics.where(pd.notna(metrics), None).to_dict(orient='records'),
    'budget_metrics': budgets.to_dict(orient='records'),
    'locked_threshold_metrics': locked.to_dict(orient='records'),
    'calibration_bins': calibration.to_dict(orient='records'),
    'tuning': tuning.to_dict(orient='records'),
    'logistic_coefficients': log_coef.to_dict(orient='records'),
    'decision_tree_importance': tree_importance.to_dict(orient='records'),
    'random_forest_importance': rf_importance.to_dict(orient='records'),
    'decision_tree_rules': tree_rules,
    'feature_columns': feature_cols,
    'predictions_csv': str(PREDICTIONS.relative_to(ROOT)),
}
RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
RESULTS_JSON.write_text(json.dumps(summary, indent=2, default=str))

print(json.dumps({
    'selected_model':selected_model,
    'best_parameters':summary['best_parameters'],
    'validation_metrics':metrics[metrics.Split.eq('Validation')][['Model','PR_AUC','Brier_Score','ECE_5_Bins']].where(pd.notna(metrics),None).to_dict(orient='records'),
    'test_metrics':metrics[metrics.Split.eq('Test')][['Model','PR_AUC','Brier_Score','ECE_5_Bins']].where(pd.notna(metrics),None).to_dict(orient='records'),
    'test_budget':budgets[budgets.Split.eq('Test')].to_dict(orient='records'),
}, indent=2))
