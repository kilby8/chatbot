"""
app.py
Dedicated Streamlit application for the Solar Scraper project.

Run:
    cd solar_scraper
    streamlit run app.py --server.headless true
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st

from db_manager import ScrapeResult, SolarDB
from solar_scraper import SolarScraper

# ─── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Solar Scraper",
    page_icon="\u2600\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* tighten metric cards */
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px 10px;
    }
    [data-testid="stMetric"] label { font-size: 0.82rem; }
    /* subtle dividers between tabs content */
    .block-container { padding-top: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Shared state helpers ────────────────────────────────────
@st.cache_resource
def _get_db() -> SolarDB:
    return SolarDB()


def _refresh():
    """Clear all data caches so the next render fetches fresh DB rows."""
    for key in list(st.session_state.keys()):
        if key.startswith("_cache_"):
            del st.session_state[key]
    st.cache_data.clear()


@st.cache_data(ttl=30)
def _all_products() -> pd.DataFrame:
    return _get_db().get_products()


@st.cache_data(ttl=30)
def _all_manufacturers() -> pd.DataFrame:
    return _get_db().get_all_manufacturers()


@st.cache_data(ttl=30)
def _stats() -> dict:
    return _get_db().get_database_stats()


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## \u2600\ufe0f Solar Scraper")
    st.caption("Web scraper + database explorer\nfor solar panel catalogues")
    st.divider()

    stats = _stats()
    st.metric("Manufacturers", stats["manufacturers_total"])
    st.metric("Products", stats["products_total"])
    st.metric("Certifications", stats["certifications_total"])
    db_mb = stats.get("db_size_mb", 0)
    st.metric("DB size", f"{db_mb:.3f} MB")

    st.divider()
    last = stats.get("last_scrape_at")
    if last:
        st.caption(f"Last scrape: {last[:19]}")
    else:
        st.caption("No scrapes yet")


# ─── Tabs ────────────────────────────────────────────────────
tab_dashboard, tab_products, tab_manufacturers, tab_search, tab_scraper, tab_history = st.tabs(
    [
        "\U0001f4ca Dashboard",
        "\U0001f4e6 Products",
        "\U0001f3ed Manufacturers",
        "\U0001f50d Search",
        "\U0001f680 Run Scraper",
        "\U0001f4cb History",
    ]
)


# ════════════════════════════════════════════════════════════
#  TAB 1 — Dashboard
# ════════════════════════════════════════════════════════════
with tab_dashboard:
    st.header("Dashboard")

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Manufacturers", stats["manufacturers_total"])
    k2.metric("Tier-1", stats["tier1_manufacturers"])
    k3.metric("Products", stats["products_total"])
    k4.metric("With efficiency data", stats["products_with_efficiency"])
    k5.metric("Certifications", stats["certifications_total"])

    st.divider()

    # Charts row
    chart_l, chart_r = st.columns(2)

    tech_df = _get_db().get_technology_breakdown()
    with chart_l:
        st.subheader("Products by technology")
        if not tech_df.empty:
            st.bar_chart(tech_df.set_index("technology")["products"], color="#f97316")
        else:
            st.info("No product data yet.")

    with chart_r:
        st.subheader("Avg efficiency by technology (%)")
        if not tech_df.empty:
            st.bar_chart(tech_df.set_index("technology")["avg_efficiency_pct"], color="#0ea5e9")
        else:
            st.info("No product data yet.")

    st.divider()

    # Country + Top efficiency side-by-side
    col_country, col_top = st.columns(2)

    with col_country:
        st.subheader("Country overview")
        country_df = _get_db().get_country_stats()
        if not country_df.empty:
            st.dataframe(country_df, use_container_width=True, hide_index=True)
        else:
            st.info("No data.")

    with col_top:
        st.subheader("Top 5 most efficient panels")
        top5 = _get_db().get_top_efficiency_products(5)
        if not top5.empty:
            st.dataframe(top5, use_container_width=True, hide_index=True)
        else:
            st.info("No data.")


# ════════════════════════════════════════════════════════════
#  TAB 2 — Products
# ════════════════════════════════════════════════════════════
with tab_products:
    st.header("Product catalogue")

    products = _all_products()

    if products.empty:
        st.warning("No products in database. Run the scraper first.")
    else:
        # Filter controls in columns
        f1, f2, f3, f4 = st.columns(4)

        tech_opts = sorted(products["technology"].dropna().unique().tolist())
        mfr_opts = sorted(products["manufacturer"].dropna().unique().tolist())
        avail_opts = sorted(products["availability"].dropna().unique().tolist())

        with f1:
            sel_tech = st.multiselect("Technology", tech_opts, default=tech_opts, key="prod_tech")
        with f2:
            sel_mfr = st.multiselect("Manufacturer", mfr_opts, default=mfr_opts, key="prod_mfr")
        with f3:
            sel_avail = st.multiselect("Availability", avail_opts, default=avail_opts, key="prod_avail")
        with f4:
            min_w = st.number_input("Min wattage (W)", min_value=0, value=0, step=50, key="prod_w")

        sl1, sl2 = st.columns(2)
        with sl1:
            min_eff = st.slider(
                "Min efficiency (%)",
                min_value=0.0,
                max_value=float(products["efficiency_pct"].max() or 25.0),
                value=0.0,
                step=0.5,
                key="prod_eff",
            )
        with sl2:
            sort_by = st.selectbox(
                "Sort by",
                ["manufacturer", "efficiency_pct", "wattage_max", "warranty_years", "product_name"],
                key="prod_sort",
            )

        # Apply filters
        view = products.copy()
        if sel_tech:
            view = view[view["technology"].isin(sel_tech)]
        if sel_mfr:
            view = view[view["manufacturer"].isin(sel_mfr)]
        if sel_avail:
            view = view[view["availability"].isin(sel_avail)]
        if min_w > 0:
            view = view[view["wattage_max"].fillna(0) >= min_w]
        if min_eff > 0:
            view = view[view["efficiency_pct"].fillna(0) >= min_eff]

        ascending = sort_by in ("manufacturer", "product_name")
        view = view.sort_values(sort_by, ascending=ascending, na_position="last")

        display_cols = [
            "manufacturer",
            "product_name",
            "technology",
            "cell_type",
            "wattage_min",
            "wattage_max",
            "efficiency_pct",
            "warranty_years",
            "availability",
        ]

        st.dataframe(view[display_cols], use_container_width=True, hide_index=True, height=460)
        st.caption(f"Showing {len(view)} of {len(products)} products")

        # Download
        st.download_button(
            "\u2b07\ufe0f Download filtered CSV",
            data=_to_csv_bytes(view[display_cols]),
            file_name="solar_products_filtered.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════
#  TAB 3 — Manufacturers
# ════════════════════════════════════════════════════════════
with tab_manufacturers:
    st.header("Manufacturer directory")

    mfr_all = _all_manufacturers()
    if mfr_all.empty:
        st.warning("No manufacturers in database. Run the scraper first.")
    else:
        tier_filter = st.radio(
            "Tier filter",
            ["All", "Tier 1 only"],
            horizontal=True,
            key="mfr_tier",
        )
        if tier_filter == "Tier 1 only":
            mfr_view = mfr_all[mfr_all["tier"] == 1]
        else:
            mfr_view = mfr_all

        show_cols = ["name", "country", "tier", "annual_capacity_gw", "base_url", "website_active", "last_scraped"]
        st.dataframe(mfr_view[show_cols], use_container_width=True, hide_index=True)
        st.caption(f"{len(mfr_view)} manufacturers")

        st.divider()

        # Per-manufacturer product counts
        st.subheader("Products per manufacturer")
        products = _all_products()
        if not products.empty:
            counts = (
                products.groupby("manufacturer")
                .agg(
                    products=("product_name", "count"),
                    avg_efficiency=("efficiency_pct", "mean"),
                    max_wattage=("wattage_max", "max"),
                )
                .reset_index()
            )
            counts["avg_efficiency"] = counts["avg_efficiency"].round(2)
            st.dataframe(counts, use_container_width=True, hide_index=True)
            st.bar_chart(counts.set_index("manufacturer")["products"], color="#10b981")

        st.divider()

        # Certifications
        st.subheader("Certifications")
        certs = _get_db().get_certifications()
        if not certs.empty:
            st.dataframe(certs, use_container_width=True, hide_index=True)
        else:
            st.info("No certification data yet.")


# ════════════════════════════════════════════════════════════
#  TAB 4 — Search
# ════════════════════════════════════════════════════════════
with tab_search:
    st.header("Keyword search")
    st.caption("Search across product names, manufacturers, technologies, cell types, and availability.")

    query = st.text_input("Enter keyword", placeholder="e.g. bifacial, TOPCon, LONGi", key="search_q")

    if query:
        results = _get_db().search(query)
        if results.empty:
            st.warning(f'No results for "{query}"')
        else:
            st.success(f'{len(results)} result(s) for "{query}"')
            st.dataframe(results, use_container_width=True, hide_index=True)
            st.download_button(
                "\u2b07\ufe0f Download results CSV",
                data=_to_csv_bytes(results),
                file_name=f"search_{query}.csv",
                mime="text/csv",
            )
    else:
        st.info("Type a keyword above to search the product catalogue.")


# ════════════════════════════════════════════════════════════
#  TAB 5 — Run Scraper
# ════════════════════════════════════════════════════════════
with tab_scraper:
    st.header("Run scraper")
    st.caption(
        "Scrape manufacturer websites, verify connectivity, and load product data into the database."
    )

    col_btn, col_info = st.columns([1, 2])

    with col_info:
        st.markdown(
            """
            **What happens when you click Start:**
            1. The scraper checks each manufacturer's website for connectivity.
            2. Product data is collected for every reachable manufacturer.
            3. All data is upserted into the local SQLite database.
            4. A scrape-run record is saved for auditing.
            """
        )

    with col_btn:
        run = st.button("\u25b6\ufe0f  Start scrape", type="primary", use_container_width=True)

    if run:
        db = _get_db()
        scraper = SolarScraper()

        progress = st.progress(0, text="Initialising scraper...")
        log_area = st.empty()
        logs: list[str] = []

        def _log(msg: str):
            logs.append(msg)
            log_area.code("\n".join(logs), language="text")

        _log("Starting scrape...")

        # Step 1 — manufacturers
        progress.progress(10, text="Checking manufacturer websites...")
        _log("Checking manufacturer websites...")
        manufacturers = scraper.scrape_manufacturers()
        _log(f"  Found {len(manufacturers)} manufacturers")
        db.upsert_manufacturers(manufacturers)

        # Step 2 — products per manufacturer
        total = len(manufacturers)
        total_products = 0
        for i, mfr in enumerate(manufacturers):
            name = mfr["name"]
            pct = int(30 + 60 * (i / max(total, 1)))
            progress.progress(pct, text=f"Scraping products for {name}...")

            started_at = datetime.now(timezone.utc)
            products = scraper.scrape_products_for_manufacturer(name)

            try:
                inserted = db.upsert_products(name, products)
                total_products += inserted
                db.record_scrape_run(
                    ScrapeResult(
                        manufacturer_name=name,
                        scrape_mode="streamlit_scrape",
                        started_at=started_at,
                        status="success",
                        records_inserted=inserted,
                    )
                )
                _log(f"  {name}: {inserted} products saved")
            except Exception as exc:
                db.record_scrape_run(
                    ScrapeResult(
                        manufacturer_name=name,
                        scrape_mode="streamlit_scrape",
                        started_at=started_at,
                        status="failed",
                        records_inserted=0,
                        error_message=str(exc),
                    )
                )
                _log(f"  {name}: FAILED ({exc})")

        progress.progress(100, text="Done!")
        _log(f"\nScrape complete. {len(manufacturers)} manufacturers, {total_products} products saved.")

        _refresh()
        st.success(
            f"Scrape finished successfully.  "
            f"{len(manufacturers)} manufacturers \u00b7 {total_products} products.",
            icon="\u2705",
        )
        st.caption("Switch to another tab to see the updated data.")


# ════════════════════════════════════════════════════════════
#  TAB 6 — Scrape History
# ════════════════════════════════════════════════════════════
with tab_history:
    st.header("Scrape run history")

    limit = st.selectbox("Show last", [10, 25, 50, 100], key="hist_limit")
    history = _get_db().get_scrape_history(limit)

    if history.empty:
        st.info("No scrape runs recorded yet. Go to the **Run Scraper** tab to start one.")
    else:
        # Summary metrics
        h1, h2, h3 = st.columns(3)
        h1.metric("Total runs shown", len(history))
        success_ct = int((history["status"] == "success").sum())
        fail_ct = int((history["status"] == "failed").sum())
        h2.metric("Successful", success_ct)
        h3.metric("Failed", fail_ct)

        st.dataframe(
            history[["manufacturer", "scrape_mode", "started_at", "status", "records_inserted", "duration_seconds", "error_message"]],
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "\u2b07\ufe0f Download history CSV",
            data=_to_csv_bytes(history),
            file_name="scrape_history.csv",
            mime="text/csv",
        )

        # Scraper log file
        from db_manager import LOG_PATH

        if os.path.exists(LOG_PATH):
            with st.expander("Raw scraper log"):
                with open(LOG_PATH, "r", encoding="utf-8") as f:
                    log_text = f.read()
                st.code(log_text[-5000:] if len(log_text) > 5000 else log_text, language="text")
