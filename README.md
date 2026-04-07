# Pennsylvania Child Care Access Analysis
**Where can Pennsylvania families find licensed child care, and what quality can they expect?**

This project analyzes 7,469 licensed child care providers across all 67 Pennsylvania counties using public licensing data and Census population estimates to map where access is strong, where it falls short, and where quality lags behind availability.

---

## The map

![PA Child Care Access, Providers per 1,000 Children Under 5](<img width="1240" height="1208" alt="yTPLn-pennsylvania-child-care-access-providers-per-1-000-children-under-5-" src="https://github.com/user-attachments/assets/88e14aaf-b9d9-48c0-80fa-3df7e3b48966" />
)

> Licensed providers per 1,000 children under 5 by county. Red = lowest access, green = highest.  
> Built with PA DHS licensing data + Census ACS 2022. [View interactive map →](https://datawrapper.dwcdn.net/yTPLn/1/)

---

## What I found

- **7,469 licensed providers** operate across all 67 PA counties, but coverage is uneven
- **Philadelphia and Allegheny** account for 34% of all providers statewide, despite being 2 of 67 counties
- **83.7% of providers hold a STAR rating** (Keystone STARS, PA's quality system), but STAR 1, the entry level, is the single largest group at 40% of all rated providers
- **Median access statewide: 9.6 providers per 1,000 children under 5**, with wide county-level variation
- **Rural north-central counties** (Sullivan, Forest, Cameron, Potter) have 2–4 providers total. Small populations keep their per-1k ratios artificially high, in practice, families have almost no choice

---

## What I built

A Python pipeline that pulls from two public sources, merges them at the county level, and feeds a Streamlit dashboard:

**Data sources:**
- PA DHS Child Care Provider Listing (April 2026), 7,469 rows, 53 columns
- U.S. Census Bureau ACS 2022 5-Year Estimates, children under 5, total population by county

**Analysis:**
- Classified all providers by type (Center, Group Home, Family Home) and STAR quality tier
- Handled encoding issues in raw data (`STAR 4– ACC` with em-dash + non-breaking space) that caused ~300 providers to be misclassified in initial passes, caught through Excel spot-checks
- Computed providers per 1,000 children under 5 as the core access metric
- Flagged counties with <10 providers as statistically unreliable on the per-1k metric

**Outputs:**
- Interactive Streamlit dashboard (filterable by county, provider type, STAR rating)
- Datawrapper choropleth map
- Export-ready CSVs for Datawrapper / Tableau

---

## What I'd do next

- **Add subsidy acceptance data**, a county can have many providers but if none accept Child Care Works (PA's subsidy program), low-income families can't use them. That's the access story that actually matters for equity
- **Add historical data**, the PA DHS file is a monthly snapshot. Pulling 3–5 years would show whether rural counties are gaining or losing providers over time
- **Legislative district cut**, the data includes PA House and Senate district for every provider. A district-level view would make this directly actionable for policymakers
- **Infant/toddler gap**, child care for under-2s is significantly harder to find than preschool-age care. The subsidy columns in the raw data could surface exactly where that gap is worst

---

## Run it yourself

```bash
git clone https://github.com/MedhaDev/pa-childcare-analysis.git
cd pa-childcare-analysis

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Download PA DHS data from data.pa.gov and update DHS_CSV path in pipeline.py
python pipeline.py
streamlit run dashboard.py
```

Dashboard runs at `http://localhost:8501`

---

## Data sources

| Source | Description | Link |
|---|---|---|
| PA DHS | Child Care Provider Listing, April 2026 | [data.pa.gov](https://data.pa.gov) |
| U.S. Census Bureau | ACS 2022 5-Year Estimates, B01001 | [census.gov](https://census.gov) |
| Keystone STARS | PA quality rating system for child care providers | [pakeys.org](https://www.pakeys.org) |

---

## Stack

Python · Pandas · GeoPandas · Streamlit · Plotly · Census API · Datawrapper

---
