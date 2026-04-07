"""
PA Child Care Access — Data Pipeline
Combines PA DHS licensing data with Census ACS 2022 children-under-5 counts.

Run: python pipeline.py
"""

from __future__ import annotations
import json, sys, requests
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUT_DIR  = BASE_DIR / "outputs"
DATA_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

DHS_CSV = Path(
   "/Users/medhasharma/Downloads/Child_Care_Providers_including_Early_Learning_Programs_Listing_Current_Monthly_Facility_County_Human_Services_20260405.csv"
).expanduser()

PROVIDER_TYPE_MAP = {
    "child care center":      "Center",
    "center":                 "Center",
    "group child care home":  "Group Home",
    "group":                  "Group Home",
    "family child care home": "Family Home",
    "family":                 "Family Home",
    "other":                  "Other / Resource",
}
STAR_ORDER = ["STAR 4", "STAR 3", "STAR 2", "STAR 1", "Unrated"]
TYPE_ORDER  = ["Center", "Group Home", "Family Home", "Other / Resource"]


# ── 1. Load DHS ───────────────────────────────────────────────────────────────

def load_dhs(path):
    if not path.exists():
        sys.exit(f"\nFile not found:\n    {path}\n")
    with open(path) as f:
        first_line = f.readline().strip()
    skip = 1 if first_line and "," not in first_line else 0
    df = pd.read_csv(path, low_memory=False, skiprows=skip)
    df.columns = df.columns.str.strip()
    print(f"  Loaded {len(df):,} rows | {len(df.columns)} columns")
    return df


# ── 2. Clean ──────────────────────────────────────────────────────────────────

def classify_star(val):
    import re as _re
    v = str(val).strip()
    if "No STAR" in v or v.replace("\xa0", "").strip() in ("nan", "", "None"):
        return "Unrated"
    match = _re.search(r"STAR (\d)", v)
    if match:
        return f"STAR {match.group(1)}"
    return "Unrated"
    # Match STAR level by digit — handles "STAR 4", "STAR 4, ACC", encoding variants
    # Check longest match first (4 before checking if 1 is in "41" etc)
    import re
    match = re.search(r'star\s*(\d)', v)
    if match:
        return f"STAR {match.group(1)}"
    return "Unrated"


def clean(df):
    df["county"]        = df["Facility County"].str.strip().str.title()
    df["county_fips"]   = pd.to_numeric(df["Facility County FIPS Code"], errors="coerce")
    raw_type            = df["Provider Type"].str.strip().str.lower().fillna("other")
    df["provider_type"] = raw_type.map(PROVIDER_TYPE_MAP).fillna("Other / Resource")
    df["star_tier"]     = df["STAR Level"].apply(classify_star)
    df["capacity"]      = pd.to_numeric(df["Child Capacity"], errors="coerce")
    coords = df["Facility Latitude & Longitude"].str.extract(r"POINT \(([^\s]+)\s+([^\)]+)\)")
    df["lon"] = pd.to_numeric(coords[0], errors="coerce")
    df["lat"] = pd.to_numeric(coords[1], errors="coerce")
    before = len(df)
    df = df[df["county"].notna() & (df["county"] != "")].copy()
    print(f"  Rows after county filter: {len(df):,} (dropped {before - len(df):,})")
    return df


# ── 3. Fetch Census ACS — children under 5 by county ─────────────────────────

def fetch_census():
    """
    ACS 2022 5-year estimates for PA counties.
    B01001_003E = male under 5
    B01001_027E = female under 5
    B01003_001E = total population
    """
    cache = DATA_DIR / "acs2022_pa_children.csv"
    if cache.exists():
        print(f"  Using cached Census data: {cache.name}")
        return pd.read_csv(cache)

    print("  Fetching Census ACS 2022 (children under 5 by county)…")
    url = (
        "https://api.census.gov/data/2022/acs/acs5"
        "?get=NAME,B01001_003E,B01001_027E,B01003_001E"
        "&for=county:*&in=state:42"
    )
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠  Census API failed: {e}")
        print("  Continuing without population data — run again with internet access to add it.")
        return None

    raw = resp.json()
    headers, rows = raw[0], raw[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Parse county name: "Adams County, Pennsylvania" → "Adams"
    df["county"] = (
        df["NAME"]
        .str.replace(" County, Pennsylvania", "", regex=False)
        .str.strip().str.title()
    )
    df["children_under5"] = (
        pd.to_numeric(df["B01001_003E"], errors="coerce").fillna(0) +
        pd.to_numeric(df["B01001_027E"], errors="coerce").fillna(0)
    ).astype(int)
    df["total_population"] = pd.to_numeric(df["B01003_001E"], errors="coerce").fillna(0).astype(int)

    df = df[["county", "children_under5", "total_population"]]
    df.to_csv(cache, index=False)
    print(f"  Fetched {len(df)} counties — cached to {cache.name}")
    return df


# ── 4. County summary ─────────────────────────────────────────────────────────

def county_summary(df, census):
    fips_map = df.dropna(subset=["county_fips"]).groupby("county")["county_fips"].first()

    base = df.groupby("county").agg(
        total_providers    = ("county", "count"),
        providers_with_cap = ("capacity", lambda x: x.notna().sum()),
        total_capacity     = ("capacity", "sum"),
    ).reset_index()
    base["county_fips"] = base["county"].map(fips_map)
    base["fips"] = "42" + base["county_fips"].fillna(0).astype(int).astype(str).str.zfill(3)

    # Provider type counts
    type_counts = (
        df.groupby(["county", "provider_type"]).size()
        .unstack(fill_value=0).reindex(columns=TYPE_ORDER, fill_value=0)
    )
    type_counts.columns = [
        f"type_{c.lower().replace(' ','_').replace('/','').replace('__','_')}"
        for c in type_counts.columns
    ]

    # STAR counts
    star_counts = (
        df.groupby(["county", "star_tier"]).size()
        .unstack(fill_value=0).reindex(columns=STAR_ORDER, fill_value=0)
    )
    star_counts.columns = [f"star_{c.lower().replace(' ','_')}" for c in star_counts.columns]
    star_counts["pct_rated"] = (
        (star_counts.drop(columns=["star_unrated"]).sum(axis=1) /
         star_counts.sum(axis=1) * 100).round(1)
    )

    summary = base.join(type_counts, on="county").join(star_counts, on="county")

    # Merge Census population data
    if census is not None:
        summary = summary.merge(census, on="county", how="left")

        # Core access metric: providers per 1,000 children under 5
        summary["providers_per_1k"] = np.where(
            summary["children_under5"] > 0,
            (summary["total_providers"] / summary["children_under5"] * 1000).round(1),
            np.nan,
        )

        # Access tier based on providers per 1,000 children
        summary["access_tier"] = pd.cut(
            summary["providers_per_1k"],
            bins=[-np.inf, 5, 10, 20, np.inf],
            labels=["Very Low (<5)", "Low (5–10)", "Moderate (10–20)", "High (>20)"],
        )
    else:
        summary["children_under5"]  = np.nan
        summary["total_population"] = np.nan
        summary["providers_per_1k"] = np.nan
        summary["access_tier"]      = np.nan

    summary["quality_tier"] = pd.cut(
        summary["pct_rated"],
        bins=[-1, 25, 50, 75, 101],
        labels=["Mostly Unrated (<25%)", "Low Rated (25-50%)",
                "Moderate (50-75%)", "Well Rated (>75%)"],
    )
    summary["total_capacity"] = summary["total_capacity"].fillna(0).astype(int)
    return summary.sort_values("total_providers", ascending=False)


# ── 5. Point data ─────────────────────────────────────────────────────────────

def point_data(df):
    rename = {
        "Facility Name": "name", "Facility City": "city",
        "STAR Level": "star_raw", "PA Pre-K Counts": "pre_k",
        "Head Start State Supplemental Assistance Program": "head_start_supp",
        "Federal Early Head Start": "early_head_start",
        "Federal Head Start": "head_start",
        "School Age Provider": "school_age",
        "School District": "school_district",
        "PA House District": "house_district",
        "PA Senate District": "senate_district",
    }
    keep = [
        "Facility Name","county","county_fips","provider_type","star_tier",
        "capacity","lat","lon","Facility City","STAR Level","PA Pre-K Counts",
        "Head Start State Supplemental Assistance Program",
        "Federal Early Head Start","Federal Head Start",
        "School Age Provider","School District","PA House District","PA Senate District",
    ]
    keep = [c for c in keep if c in df.columns]
    pts = df[keep].copy()  # keep all 7,469 — lat/lon is null for 105 providers but county is known
    pts = pts.rename(columns={k:v for k,v in rename.items() if k in pts.columns})
    pts["fips"] = "42" + pts["county_fips"].fillna(0).astype(int).astype(str).str.zfill(3)
    print(f"  Point records with coordinates: {len(pts):,}")
    return pts


# ── 6. Export ─────────────────────────────────────────────────────────────────

def export(summary, points):
    summary.to_csv(OUT_DIR / "pa_childcare_counties.csv", index=False)
    points.to_csv(OUT_DIR / "pa_childcare_points.csv", index=False)

    # Datawrapper CSV — county name matching, clean columns
    dw_cols = {
        "county": "County",
        "total_providers": "Total Providers",
        "type_center": "Centers",
        "type_group_home": "Group Homes",
        "type_family_home": "Family Homes",
        "pct_rated": "Pct STAR Rated",
        "quality_tier": "Quality Tier",
        "children_under5": "Children Under 5",
        "providers_per_1k": "Providers per 1k Children",
        "access_tier": "Access Tier",
    }
    dw = summary[[c for c in dw_cols if c in summary.columns]].copy()
    dw.columns = [dw_cols[c] for c in dw.columns]
    dw["Quality Tier"]  = dw["Quality Tier"].astype(str)
    if "Access Tier" in dw.columns:
        dw["Access Tier"] = dw["Access Tier"].astype(str)
    dw.to_csv(OUT_DIR / "datawrapper_counties.csv", index=False)

    # Summary JSON
    rated = points[points["star_tier"] != "Unrated"]
    has_census = summary["children_under5"].notna().any()
    stats = {
        "total_providers":   int(summary["total_providers"].sum()),  # all 7469, not just those with coords
        "total_counties":    int(summary["county"].nunique()),
        "pct_rated":         round(len(rated) / len(points) * 100, 1),
        "provider_types":    points["provider_type"].value_counts().to_dict(),
        "star_distribution": points["star_tier"].value_counts().to_dict(),
        "has_census_data":   bool(has_census),
    }
    if has_census:
        stats["total_children_under5"] = int(summary["children_under5"].sum())
        stats["median_providers_per_1k"] = float(summary["providers_per_1k"].median().round(1))

    (OUT_DIR / "summary.json").write_text(json.dumps(stats, indent=2))

    print(f"\n  Total providers:  {stats['total_providers']:,}")
    print(f"  Counties:         {stats['total_counties']}")
    print(f"  % STAR rated:     {stats['pct_rated']}%")
    if has_census:
        print(f"  Children under 5: {stats['total_children_under5']:,}")
        print(f"  Median providers per 1k children: {stats['median_providers_per_1k']}")
    print(f"\n  Outputs → {OUT_DIR}/")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n── Load DHS ──");  raw     = load_dhs(DHS_CSV)
    print("\n── Clean ──");     df      = clean(raw)
    print("\n── Census ──");    census  = fetch_census()
    print("\n── Summarise ──"); summary = county_summary(df, census)
    print("\n── Points ──");    pts     = point_data(df)
    print("\n── Export ──");    export(summary, pts)
    print("\nDone. Run:  streamlit run dashboard.py\n")