# Original download instructions

The repository contains the cleaned official extracts in `data/processed/` so the analysis can be reproduced without repeatedly querying public websites. If the raw source files are downloaded again, retain them unchanged in this directory and record the download date.

## 1. NIFTYBEES market data

Publisher: National Stock Exchange of India.

Page: https://www.nseindia.com/report-detail/eq_security

Select security **Nippon India ETF Nifty 50 BeES / NIFTYBEES**, series **EQ**, and download annual ranges because the website normally limits one request to approximately one year. Required period: 01-Jan-2021 through 16-Nov-2026.

Required fields: symbol, series, date, previous close, open, high, low, last, close, average price, traded quantity, turnover, trades, deliverable quantity and delivery percentage.

## 2. NIFTYBEES NAV

Publisher: Association of Mutual Funds in India.

Page: https://www.amfiindia.com/net-asset-value/nav-download

Fund house: Nippon India Mutual Fund. Scheme: Nippon India ETF Nifty 50 BeES. Scheme code: **140084**. ISIN: **INF204KB14I2**. Download the history in smaller date blocks if the site restricts the maximum range.

## 3. NIFTY 50

Publisher: NSE Indices.

Page: https://www.niftyindices.com/reports

Download historical price-return index data for **NIFTY 50** for each calendar year from 2021 through 2026. Required fields: date, open, high, low and close.

## 4. India VIX

Publisher: National Stock Exchange of India.

Page: https://www.nseindia.com/reports-indices-historical-index-data

Choose **India VIX** and download annual ranges from 2021 through 2026. Required fields: date, open, high, low, close, previous close, change and percentage change.

## Integrity checks after downloading

- Never manually replace a missing observation with zero.
- Preserve original filenames and original downloaded copies.
- Confirm dates are unique within each source.
- Confirm scheme code, ISIN, symbol and series before merging.
- Keep source-zero VIX values flagged; do not silently impute them.
