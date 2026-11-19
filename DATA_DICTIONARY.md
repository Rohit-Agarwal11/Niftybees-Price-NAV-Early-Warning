# Data dictionary and provenance

| File | Source | Purpose |
|---|---|---|
| `NIFTYBEES_EQ_Market_Data_2021_to_2026_Clean.csv` | NSE historical security data | ETF market price, volume and trading activity |
| `NIFTYBEES_NAV_AMFI_official_2021_to_2026_Updated.csv` | AMFI official NAV history | Official daily NAV benchmark |
| `NIFTY50_Historical_2021_to_2026_Clean.csv` | NSE index historical data | Broad-market control |
| `INDIA_VIX_Historical_2021_to_2026_Clean.csv` | NSE India VIX history | Market-volatility control |
| `ETF_Master_Merged_2021_to_2026.csv` | Rebuilt by script 01 | Date-aligned audit panel |
| `ETF_Analysis_Ready_2021_to_2026.csv` | Rebuilt by script 01 | Complete-case descriptive panel |
| `ETF_Modeling_Dataset_Leakage_Safe_2021_to_2026.csv` | Rebuilt by script 02 | Features at date t and next-market-day outcome |

The cleaned official inputs are retained so a reviewer can reproduce the analysis without downloading files from dynamic websites. Source URLs, access notes and field mappings appear in `docs/SOURCES_AND_REFERENCES.md`, `docs/source_register.csv`, and `data/raw/README.md`.
