# PA Child Care Access Analysis

Clean geospatial pipeline: PA DHS licensing data × Census ACS 2022 × TIGER/Line boundaries.

---

## Setup

```bash
# 1. Navigate to project folder
cd ~/Desktop/pa-childcare-analysis/

# 2. Create virtual environment (recommended)
python3.9 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

## Configure

Open `pipeline.py` and update the `DHS_CSV` path at the top if needed:

```python
DHS_CSV = Path("~/Downloads/Child_Care_Providers_including_...csv").expanduser()
```

Optional — get a free Census API key for faster requests:
https://api.census.gov/data/key_signup.html

```bash
export CENSUS_API_KEY="your_key_here"
```

## Run

```bash
# Step 1: Run the data pipeline (takes ~60 seconds first run; caches Census + TIGER data)
python pipeline.py

# Step 2: Launch the dashboard
streamlit run dashboard.py
```

Dashboard opens at http://localhost:8501

---

## Outputs

| File | Description |
|---|---|
| `outputs/pa_childcare_analysis.geojson` | County-level map data (Datawrapper / QGIS) |
| `outputs/pa_childcare_analysis.csv` | Flat table (Datawrapper / Tableau) |
| `outputs/summary.json` | Statewide quick-stats |
| `data/acs2022_pa_counties.csv` | Cached Census ACS data |
| `data/pa_counties.geojson` | Cached TIGER/Line boundaries |

---

## Metrics

| Metric | Definition |
|---|---|
| **Slots per 100** | Licensed capacity ÷ children under 5 × 100 |
| **Severe Shortage** | < 20 slots per 100 children |
| **Limited Access** | 20–50 slots per 100 children |
| **Adequate** | 50–75 slots per 100 children |
| **Good Access** | > 75 slots per 100 children |
| **Vulnerability Index** | Weighted: poverty 30%, single-parent HH 20%, access gap 35%, rural 15% |
| **Priority Score** | Vulnerability × 0.6 + access tier weight × 0.4 |

---

## Project Structure

```
pa-childcare-analysis/
├── pipeline.py        ← data collection + analysis
├── dashboard.py       ← Streamlit app
├── requirements.txt
├── README.md
├── data/              ← cached Census + TIGER data (auto-created)
└── outputs/           ← analysis outputs (auto-created)
```
