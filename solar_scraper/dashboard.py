"""
dashboard.py
Streamlit GUI for exploring the solar scraper SQLite database.

Run from the solar_scraper directory:
    streamlit run dashboard.py --server.headless true
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from db_manager import SolarDB

st.set_page_config(page_title="Solar Catalogue", page_icon="\u2600\ufe0f", layout="wide")

@st.cache_resource
def get_db() -> SolarDB:
    return SolarDB()

db = get_db()


# ── Header ───────────────────────────────────────────────────
st.title("\u2600\ufe0f Solar Panel Catalogue")
st.caption("Interactive explorer for the solar scraper database")


# ── KPI row ──────────────────────────────────────────────────
stats = db.get_database_stats()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Manufacturers", stats["manufacturers_total"])
c2.metric("Tier-1", stats["tier1_manufacturers"])
c3.metric("Products", stats["products_total"])
c4.metric("Certifications", stats["certifications_total"])


# ── Sidebar filters ──────────────────────────────────────────
st.sidebar.header("Filters")

all_products = db.get_products()
tech_options = sorted(all_products["technology"].dropna().unique().tolist())
mfr_options = sorted(all_products["manufacturer"].dropna().unique().tolist())

selected_tech = st.sidebar.multiselect("Technology", tech_options, default=tech_options)
selected_mfr = st.sidebar.multiselect("Manufacturer", mfr_options, default=mfr_options)

watt_range = st.sidebar.slider(
    "Min wattage (W)",
    min_value=0,
    max_value=int(all_products["wattage_max"].max() or 800),
    value=0,
    step=10,
)
eff_range = st.sidebar.slider(
    "Min efficiency (%)",
    min_value=0.0,
    max_value=float(all_products["efficiency_pct"].max() or 25),
    value=0.0,
    step=0.5,
)

keyword = st.sidebar.text_input("Keyword search")


# ── Filtered product table ───────────────────────────────────
st.header("Products")

filtered = all_products.copy()
if selected_tech:
    filtered = filtered[filtered["technology"].isin(selected_tech)]
if selected_mfr:
    filtered = filtered[filtered["manufacturer"].isin(selected_mfr)]
if watt_range > 0:
    filtered = filtered[filtered["wattage_max"].fillna(0) >= watt_range]
if eff_range > 0:
    filtered = filtered[filtered["efficiency_pct"].fillna(0) >= eff_range]
if keyword:
    kw = keyword.lower()
    mask = filtered.apply(lambda row: any(kw in str(v).lower() for v in row), axis=1)
    filtered = filtered[mask]

display_cols = [
    "manufacturer", "product_name", "technology", "cell_type",
    "wattage_min", "wattage_max", "efficiency_pct",
    "warranty_years", "availability",
]
st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)
st.caption(f"{len(filtered)} of {len(all_products)} products shown")


# ── Charts ───────────────────────────────────────────────────
chart_left, chart_right = st.columns(2)

with chart_left:
    st.subheader("Technology breakdown")
    tech_df = db.get_technology_breakdown()
    if not tech_df.empty:
        st.bar_chart(tech_df.set_index("technology")["products"])

with chart_right:
    st.subheader("Avg efficiency by technology")
    if not tech_df.empty:
        st.bar_chart(tech_df.set_index("technology")["avg_efficiency_pct"])


# ── Country stats ────────────────────────────────────────────
st.header("Country statistics")
country_df = db.get_country_stats()
if not country_df.empty:
    st.dataframe(country_df, use_container_width=True, hide_index=True)


# ── Top efficiency ───────────────────────────────────────────
st.header("Top efficiency products")
top_eff = db.get_top_efficiency_products(10)
if not top_eff.empty:
    st.dataframe(top_eff, use_container_width=True, hide_index=True)


# ── Manufacturers ────────────────────────────────────────────
st.header("Manufacturers")
mfr_df = db.get_all_manufacturers()
if not mfr_df.empty:
    st.dataframe(
        mfr_df[["name", "country", "tier", "annual_capacity_gw", "base_url", "website_active"]],
        use_container_width=True,
        hide_index=True,
    )


# ── Certifications ───────────────────────────────────────────
st.header("Certifications")
certs = db.get_certifications()
if not certs.empty:
    st.dataframe(certs, use_container_width=True, hide_index=True)
else:
    st.info("No certification data yet.")


# ── Scrape history ───────────────────────────────────────────
st.header("Scrape history")
history = db.get_scrape_history(20)
if not history.empty:
    st.dataframe(history, use_container_width=True, hide_index=True)
else:
    st.info("No scrape runs recorded yet.")
