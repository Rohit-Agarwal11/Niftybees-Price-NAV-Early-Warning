"""Merge the four official cleaned sources and create the analysis panel.

The script is deterministic and uses Date as the only merge key. It also
records missing NAV/VIX observations and the two source-zero VIX anomalies.
"""
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def unique_dates(frame: pd.DataFrame, name: str) -> None:
    if frame["Date"].duplicated().any():
        bad = frame.loc[frame["Date"].duplicated(False), "Date"].dt.strftime("%Y-%m-%d").tolist()
        raise ValueError(f"{name} has duplicate dates: {bad[:10]}")


market = pd.read_csv(DATA / "NIFTYBEES_EQ_Market_Data_2021_to_2026_Clean.csv", parse_dates=["Date"])
nav = pd.read_csv(DATA / "NIFTYBEES_NAV_AMFI_official_2021_to_2026_Updated.csv")
nifty = pd.read_csv(DATA / "NIFTY50_Historical_2021_to_2026_Clean.csv", parse_dates=["Date"])
vix = pd.read_csv(DATA / "INDIA_VIX_Historical_2021_to_2026_Clean.csv", parse_dates=["Date"])

assert len(market) == 1456
assert set(market["Symbol"]) == {"NIFTYBEES"}
assert set(market["Series"]) == {"EQ"}
assert set(nav["Scheme Code"].astype(str)) == {"140084"}

nav["Date"] = pd.to_datetime(nav["AUDIT_DATE"])
for frame, name in [(market, "market"), (nav, "NAV"), (nifty, "NIFTY 50"), (vix, "India VIX")]:
    unique_dates(frame, name)

market = market.rename(columns={
    "Symbol": "ETF_Symbol", "Series": "ETF_Series", "Prev Close": "ETF_Prev_Close",
    "Open Price": "ETF_Open", "High Price": "ETF_High", "Low Price": "ETF_Low",
    "Last Price": "ETF_Last", "Close Price": "ETF_Close", "Average Price": "ETF_Average_Price",
    "Total Traded Quantity": "ETF_Volume", "Turnover ₹": "ETF_Turnover_INR",
    "No. of Trades": "ETF_Trades", "Deliverable Qty": "ETF_Deliverable_Qty",
    "% Dly Qt to Traded Qty": "ETF_Delivery_Pct",
})
market["ETF_Intraday_Range_Pct"] = ((market["ETF_High"] - market["ETF_Low"]) / market["ETF_Close"] * 100).round(4)
market["ETF_Extreme_Range_Flag"] = (market["ETF_Intraday_Range_Pct"] > 5).astype(int)
delivery_check = market["ETF_Deliverable_Qty"] / market["ETF_Volume"] * 100
market["ETF_Delivery_Audit_Flag"] = np.where(
    (delivery_check - market["ETF_Delivery_Pct"]).abs() <= 0.10, "OK", "CHECK_SOURCE"
)

market_cols = [
    "Date", "ETF_Symbol", "ETF_Series", "ETF_Prev_Close", "ETF_Open", "ETF_High", "ETF_Low",
    "ETF_Last", "ETF_Close", "ETF_Average_Price", "ETF_Volume", "ETF_Turnover_INR",
    "ETF_Trades", "ETF_Deliverable_Qty", "ETF_Delivery_Pct", "ETF_Intraday_Range_Pct",
    "ETF_Extreme_Range_Flag", "ETF_Delivery_Audit_Flag",
]
master = market[market_cols].copy()
master = master.merge(nav[["Date", "NAV"]], on="Date", how="left", validate="one_to_one")
master["Price_NAV_Dislocation_Pct"] = ((master["ETF_Close"] - master["NAV"]) / master["NAV"] * 100).round(6)
master["Abs_Dislocation_Pct"] = master["Price_NAV_Dislocation_Pct"].abs().round(6)

nifty = nifty.rename(columns={"Open": "NIFTY50_Open", "High": "NIFTY50_High", "Low": "NIFTY50_Low", "Close": "NIFTY50_Close"})
master = master.merge(nifty[["Date", "NIFTY50_Open", "NIFTY50_High", "NIFTY50_Low", "NIFTY50_Close"]], on="Date", how="left", validate="one_to_one")

vix = vix.rename(columns={
    "Open": "INDIA_VIX_Open", "High": "INDIA_VIX_High", "Low": "INDIA_VIX_Low",
    "Close": "INDIA_VIX_Close", "% Change": "INDIA_VIX_Pct_Change",
    "Data Quality Flag": "VIX_Quality_Flag",
})
master = master.merge(vix[["Date", "INDIA_VIX_Open", "INDIA_VIX_High", "INDIA_VIX_Low", "INDIA_VIX_Close", "INDIA_VIX_Pct_Change", "VIX_Quality_Flag"]], on="Date", how="left", validate="one_to_one")
master["VIX_Quality_Flag"] = master["VIX_Quality_Flag"].fillna("MISSING")
master["NAV_Available"] = master["NAV"].notna().astype(int)
master["VIX_Available"] = master["INDIA_VIX_Close"].notna().astype(int)
master["Complete_Case"] = (
    master["NAV_Available"].eq(1)
    & master["NIFTY50_Close"].notna()
    & master["VIX_Available"].eq(1)
    & master["VIX_Quality_Flag"].eq("OK")
).astype(int)


def quality_note(row: pd.Series) -> str:
    notes = []
    if not row["NAV_Available"]:
        notes.append("NAV_MISSING")
    if not row["VIX_Available"]:
        notes.append("VIX_MISSING")
    elif row["VIX_Quality_Flag"] != "OK":
        notes.append(str(row["VIX_Quality_Flag"]))
    return "|".join(notes) if notes else "OK"


master["Data_Quality_Notes"] = master.apply(quality_note, axis=1)
master = master.sort_values("Date").reset_index(drop=True)
analysis = master.loc[master["Complete_Case"].eq(1)].copy()

master.to_csv(DATA / "ETF_Master_Merged_2021_to_2026.csv", index=False, date_format="%Y-%m-%d", float_format="%.6f")
analysis.to_csv(DATA / "ETF_Analysis_Ready_2021_to_2026.csv", index=False, date_format="%Y-%m-%d", float_format="%.6f")

assert len(master) == 1456
assert len(analysis) == 1446
assert master["NAV_Available"].sum() == 1448
assert (master["VIX_Quality_Flag"] == "SOURCE_ZERO_ANOMALY").sum() == 2
print({"master_rows": len(master), "complete_rows": len(analysis), "first": str(master.Date.min().date()), "last": str(master.Date.max().date())})
