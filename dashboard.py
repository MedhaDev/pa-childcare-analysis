"""
PA Child Care Access Dashboard — dark mode compatible
Run: streamlit run dashboard.py
"""

import json
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path
from urllib.request import urlopen

OUT_DIR = Path(__file__).parent / "outputs"

st.set_page_config(page_title="PA Child Care Access", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', Helvetica, sans-serif; }
.block-container { padding-top: 2rem; max-width: 1180px; }
h1 { font-size: 1.75rem !important; font-weight: 700 !important;
     border-bottom: 2.5px solid currentColor; padding-bottom: 0.4rem;
     margin-bottom: 0.4rem !important; }
h2 { font-size: 0.78rem !important; font-weight: 600 !important;
     letter-spacing: 0.09em; text-transform: uppercase;
     margin-top: 2.2rem !important; margin-bottom: 0.6rem !important; }
.stat { border: 1.5px solid rgba(128,128,128,0.4); padding: 1rem 1.2rem; border-radius: 2px; }
.stat-label { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em;
              text-transform: uppercase; opacity: 0.7; margin-bottom: 0.2rem; }
.stat-value { font-size: 2rem; font-weight: 700; line-height: 1.1; }
.stat-sub   { font-size: 0.74rem; opacity: 0.6; margin-top: 0.15rem; }
.stDownloadButton > button {
    background: transparent !important;
    border: 1.5px solid rgba(128,128,128,0.5) !important;
    border-radius: 2px !important; font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important; font-weight: 500 !important;
    letter-spacing: 0.05em !important; padding: 0.45rem 1.1rem !important;
}
.stDownloadButton > button:hover { border-color: currentColor !important; }
[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,0.2); }
#MainMenu { visibility: hidden; } footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

TYPE_COLORS = {
    "Center":           "#4C9BE8",
    "Group Home":       "#7EC8A4",
    "Family Home":      "#F4A261",
    "Other / Resource": "#A8A8A8",
}
STAR_COLORS = {
    "STAR 4": "#2ecc71", "STAR 3": "#85e89d",
    "STAR 2": "#f1c40f", "STAR 1": "#e07c00", "Unrated": "#e74c3c",
}
ACCESS_COLORS = {
    "Very Low (<5)":    "#e74c3c",
    "Low (5–10)":       "#e07c00",
    "Moderate (10–20)": "#f1c40f",
    "High (>20)":       "#2ecc71",
}
STAR_ORDER   = ["STAR 4", "STAR 3", "STAR 2", "STAR 1", "Unrated"]
TYPE_ORDER   = ["Center", "Group Home", "Family Home", "Other / Resource"]
ACCESS_ORDER = ["Very Low (<5)", "Low (5–10)", "Moderate (10–20)", "High (>20)"]


@st.cache_data
def load():
    cp = OUT_DIR / "pa_childcare_counties.csv"
    pp = OUT_DIR / "pa_childcare_points.csv"
    sp = OUT_DIR / "summary.json"
    if not cp.exists():
        return None, None, None
    return pd.read_csv(cp), pd.read_csv(pp), json.loads(sp.read_text())

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    with urlopen(url) as r:
        geo = json.load(r)
    geo["features"] = [f for f in geo["features"] if f["id"].startswith("42")]
    return geo

counties, pts, summary = load()

if counties is None:
    st.title("PA Child Care Access")
    st.error("Run `python pipeline.py` first, then refresh.")
    st.stop()

has_census = summary.get("has_census_data", False)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Filter")
    sel_counties = st.multiselect("County", sorted(pts["county"].dropna().unique()), placeholder="All counties")
    sel_types    = st.multiselect("Provider type", TYPE_ORDER, placeholder="All types")
    sel_stars    = st.multiselect("STAR rating", STAR_ORDER, placeholder="All ratings")

    st.markdown("---")
    if has_census:
        st.markdown("### Map metric")
        map_metric = st.radio(
            "Color counties by",
            ["Total providers", "Providers per 1k children under 5"],
            index=1,
        )
    else:
        map_metric = "Total providers"

    st.markdown("---")
    st.markdown(
        "<small>**Source:** PA DHS Child Care Provider Listing, April 2026.<br>"
        "Population: Census ACS 2022.<br>"
        "STAR 1–4 = Keystone STARS quality rating.</small>",
        unsafe_allow_html=True,
    )

fpts = pts.copy()
if sel_counties: fpts = fpts[fpts["county"].isin(sel_counties)]
if sel_types:    fpts = fpts[fpts["provider_type"].isin(sel_types)]
if sel_stars:    fpts = fpts[fpts["star_tier"].isin(sel_stars)]

fcounties = counties.copy()
if sel_counties: fcounties = fcounties[fcounties["county"].isin(sel_counties)]


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("# Pennsylvania Child Care Access")
total_in_view = int(fcounties["total_providers"].sum()) if "total_providers" in fcounties.columns else len(fpts)
total_all = summary.get("total_providers", 7469)
st.caption(
    f"**{total_all:,}** licensed providers across 67 counties · PA DHS, April 2026"
)

# Stat cards
cols = st.columns(5 if has_census else 4)
def card(col, label, value, sub=""):
    col.markdown(
        f'<div class="stat"><div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'<div class="stat-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )

# Use county summary for counts (all 7,469) not points (7,364 with coords)
total_all    = int(fcounties["total_providers"].sum())
star_cols    = [c for c in fcounties.columns if c.startswith("star_star_")]
total_rated  = int(fcounties[star_cols].sum().sum()) if star_cols else 0
pct_rated    = round(total_rated / max(total_all, 1) * 100, 1)

card(cols[0], "Licensed Providers",  f"{total_all:,}",                  "PA DHS, April 2026")
card(cols[1], "Counties",             f"{fcounties['county'].nunique()}", "represented")
card(cols[2], "STAR Rated",           f"{pct_rated}%",                  "hold STAR 1–4")
card(cols[3], "Provider Types",       "4",                              "Center, Group, Family, Other")
if has_census:
    median_access = fcounties["providers_per_1k"].median()
    card(cols[4], "Median Access",
         f"{median_access:.1f}" if pd.notna(median_access) else "—",
         "providers per 1k children")


# ── Map ───────────────────────────────────────────────────────────────────────

st.markdown("## Where are providers?")

use_access = has_census and map_metric == "Providers per 1k children under 5"

if use_access:
    color_col   = "providers_per_1k"
    color_scale = [[0,"#e74c3c"],[0.25,"#e07c00"],[0.5,"#f1c40f"],[1.0,"#2ecc71"]]
    range_color = [0, fcounties["providers_per_1k"].quantile(0.95)]
    color_label = "Providers / 1k children"
    caption     = "Color = licensed providers per 1,000 children under 5 (Census ACS 2022). Red = lowest access, green = highest. Note: counties with fewer than 10 providers should be interpreted with caution — small absolute numbers can produce misleadingly high ratios."
else:
    color_col   = "total_providers"
    color_scale = [[0,"#0d3b6e"],[0.05,"#1a6bb5"],[0.2,"#4C9BE8"],[0.5,"#85c4f0"],[1.0,"#ffffff"]]
    range_color = [0, 300]
    color_label = "Providers"
    caption     = "Color = total licensed providers per county. Scale capped at 300 so rural counties are visible."

try:
    geo = load_geojson()
    hover = {"fips": False, "total_providers": True, "providers_per_1k": True, "children_under5": True}
    fig_map = px.choropleth_mapbox(
        fcounties,
        geojson=geo,
        locations="fips",
        color=color_col,
        color_continuous_scale=color_scale,
        range_color=range_color,
        mapbox_style="carto-darkmatter",
        center={"lat": 41.0, "lon": -77.5},
        zoom=5.8,
        opacity=0.85,
        hover_name="county",
        hover_data=hover,
        labels={
            color_col: color_label,
            "total_providers": "Total providers",
            "providers_per_1k": "Per 1k children",
            "children_under5": "Children under 5",
        },
    )
    fig_map.update_coloraxes(colorbar_title=color_label)
    fig_map.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0}, height=440,
        font=dict(family="Inter", color="#ffffff"),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(caption)
except Exception as e:
    st.info(f"Map requires internet connection to load county boundaries. ({e})")


# ── Charts ────────────────────────────────────────────────────────────────────

def base_layout(height=260):
    return dict(
        showlegend=False, height=height,
        margin=dict(l=0, r=60, t=10, b=10),
        font=dict(family="Inter", size=11),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", title="", color="#aaa"),
        yaxis=dict(title="", color="#aaa"),
    )

col_l, col_r = st.columns(2)

with col_l:
    st.markdown("## What type of provider?")
    # Use county summary totals (all 7,469 providers) not points (7,364 with coordinates)
    type_col_map = {
        "Center":           "type_center",
        "Group Home":       "type_group_home",
        "Family Home":      "type_family_home",
        "Other / Resource": "type_other_resource",
    }
    tc = pd.DataFrame({
        "Type":  list(type_col_map.keys()),
        "Count": [
            int(fcounties[col].sum()) if col in fcounties.columns else 0
            for col in type_col_map.values()
        ]
    })
    fig = px.bar(tc, x="Count", y="Type", orientation="h",
                 color="Type", color_discrete_map=TYPE_COLORS, text="Count")
    fig.update_traces(textposition="outside", textfont=dict(family="Inter", size=11, color="#ccc"))
    fig.update_layout(**base_layout())
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.markdown("## What quality rating?")
    sc = fpts["star_tier"].value_counts().reindex(STAR_ORDER).dropna().reset_index()
    sc.columns = ["Rating", "Count"]
    fig = px.bar(sc, x="Count", y="Rating", orientation="h",
                 color="Rating", color_discrete_map=STAR_COLORS, text="Count")
    fig.update_traces(textposition="outside", textfont=dict(family="Inter", size=11, color="#ccc"))
    lay = base_layout()
    lay["yaxis"]["categoryorder"] = "array"
    lay["yaxis"]["categoryarray"] = STAR_ORDER
    fig.update_layout(**lay)
    st.plotly_chart(fig, use_container_width=True)

# Access tier chart — only if Census data available
if has_census and "access_tier" in fcounties.columns:
    st.markdown("## Access by county — providers per 1,000 children under 5")
    st.caption(
        "Thresholds: Very Low <5 · Low 5–10 · Moderate 10–20 · High >20 providers per 1,000 children"
    )
    tier_counts = (
        fcounties["access_tier"].astype(str)
        .value_counts().reindex(ACCESS_ORDER).dropna().reset_index()
    )
    tier_counts.columns = ["Tier", "Counties"]
    fig_access = px.bar(
        tier_counts, x="Counties", y="Tier", orientation="h",
        color="Tier", color_discrete_map=ACCESS_COLORS, text="Counties",
    )
    fig_access.update_traces(textposition="outside", textfont=dict(family="Inter", size=11, color="#ccc"))
    lay = base_layout(200)
    lay["yaxis"]["categoryorder"] = "array"
    lay["yaxis"]["categoryarray"] = ACCESS_ORDER
    fig_access.update_layout(**lay)
    st.plotly_chart(fig_access, use_container_width=True)


# ── County table ──────────────────────────────────────────────────────────────

st.markdown("## County breakdown")

show = ["county", "total_providers"]
for c in ["type_center","type_group_home","type_family_home"]:
    if c in fcounties.columns: show.append(c)
if has_census:
    for c in ["children_under5","providers_per_1k","access_tier"]:
        if c in fcounties.columns: show.append(c)
for c in ["pct_rated","quality_tier"]:
    if c in fcounties.columns: show.append(c)

rename = {
    "county":"County", "total_providers":"Total", "type_center":"Centers",
    "type_group_home":"Group Homes", "type_family_home":"Family Homes",
    "children_under5":"Children U5", "providers_per_1k":"Per 1k",
    "access_tier":"Access Tier", "pct_rated":"% Rated", "quality_tier":"Quality Tier",
}
table_df = (
    fcounties[show]
    .sort_values("total_providers", ascending=False)
    .rename(columns=rename)
    .reset_index(drop=True)
)
col_config = {
    "% Rated": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
}
if has_census and "Per 1k" in table_df.columns:
    col_config["Per 1k"] = st.column_config.NumberColumn(format="%.1f")

st.dataframe(table_df, use_container_width=True, height=360, column_config=col_config)


# ── Downloads ─────────────────────────────────────────────────────────────────

st.markdown("## Download")
dl1, dl2, dl3 = st.columns(3)

with dl1:
    cp = OUT_DIR / "pa_childcare_counties.csv"
    st.download_button("↓ County summary (CSV)",
                       data=cp.read_bytes(),
                       file_name="pa_childcare_counties.csv", mime="text/csv")
with dl2:
    st.download_button("↓ Provider points (CSV)",
                       data=fpts.to_csv(index=False).encode(),
                       file_name="pa_childcare_providers.csv", mime="text/csv")
with dl3:
    dw = OUT_DIR / "datawrapper_counties.csv"
    if dw.exists():
        st.download_button("↓ Datawrapper-ready (CSV)",
                           data=dw.read_bytes(),
                           file_name="datawrapper_counties.csv", mime="text/csv")

st.markdown("---")
st.markdown(
    "<small style='opacity:0.5'>PA DHS Child Care Provider Listing · April 2026 · "
    "Census ACS 2022 · Keystone STARS ratings as recorded at time of export</small>",
    unsafe_allow_html=True,
)