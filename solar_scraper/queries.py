"""
queries.py
══════════════════════════════════════════════════
Run any query directly from PyCharm.
Click the ▶ Green Run button to execute.
══════════════════════════════════════════════════
"""

from db_manager import SolarDB
import pandas as pd

pd.set_option("display.max_columns",  15)
pd.set_option("display.width",        200)
pd.set_option("display.max_colwidth", 50)
pd.set_option("display.max_rows",     50)

db = SolarDB()


# ══════════════════════════════════════════════
# ▶  TOGGLE WHICH QUERIES RUN — set True/False
# ══════════════════════════════════════════════

RUN_DB_STATS          = True
RUN_ALL_MANUFACTURERS = True
RUN_TIER1_ONLY        = True
RUN_PRODUCTS_ALL      = True
RUN_TOPCON_FILTER     = True
RUN_HIGH_WATTAGE      = True
RUN_HIGH_EFFICIENCY   = True
RUN_TECH_BREAKDOWN    = True
RUN_COUNTRY_STATS     = True
RUN_CERTIFICATIONS    = True
RUN_KEYWORD_SEARCH    = True
RUN_SCRAPE_HISTORY    = True
EXPORT_CSV            = True
EXPORT_HTML_REPORT    = True

SEARCH_KEYWORD        = "bifacial"    # ← change keyword here
MIN_WATTS             = 500.0         # ← watt filter
MIN_EFFICIENCY        = 21.0          # ← efficiency filter %


def divider(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


# ──────────────────────────────────────────────
# 1. DATABASE STATISTICS
# ──────────────────────────────────────────────
if RUN_DB_STATS:
    divider("📊 DATABASE STATISTICS")
    stats = db.get_database_stats()
    for key, val in stats.items():
        label = key.replace("_", " ").title()
        print(f"  {label:<30}: {val}")


# ──────────────────────────────────────────────
# 2. ALL MANUFACTURERS
# ──────────────────────────────────────────────
if RUN_ALL_MANUFACTURERS:
    divider("🏭 ALL MANUFACTURERS")
    df = db.get_all_manufacturers()
    print(df[["name", "country", "tier", "base_url",
              "website_active", "last_scraped"]].to_string(index=False))
    print(f"\n  Total: {len(df)} manufacturers")


# ──────────────────────────────────────────────
# 3. TIER 1 ONLY
# ──────────────────────────────────────────────
if RUN_TIER1_ONLY:
    divider("⭐ TIER 1 MANUFACTURERS")
    df = db.get_all_manufacturers(tier=1)
    print(df[["name", "country", "annual_capacity_gw",
              "base_url"]].to_string(index=False))


# ──────────────────────────────────────────────
# 4. ALL PRODUCTS
# ──────────────────────────────────────────────
if RUN_PRODUCTS_ALL:
    divider("📦 ALL PRODUCTS IN DATABASE")
    df = db.get_products()
    if df.empty:
        print("  No products found. Run the scraper first.")
    else:
        print(df[["manufacturer", "product_name", "technology",
                   "wattage_max", "efficiency_pct",
                   "warranty_years", "availability"]].to_string(index=False))
        print(f"\n  Total: {len(df)} products")


# ──────────────────────────────────────────────
# 5. FILTER — TOPCon Technology
# ──────────────────────────────────────────────
if RUN_TOPCON_FILTER:
    divider("🔬 TOPCon PRODUCTS")
    df = db.get_products(technology="TOPCon")
    if df.empty:
        print("  No TOPCon products found yet.")
    else:
        print(df[["manufacturer", "product_name", "wattage_max",
                   "efficiency_pct", "cell_type"]].to_string(index=False))


# ──────────────────────────────────────────────
# 6. FILTER — High Wattage Panels (≥ MIN_WATTS)
# ──────────────────────────────────────────────
if RUN_HIGH_WATTAGE:
    divider(f"⚡ HIGH WATTAGE PANELS (≥ {MIN_WATTS}W)")
    df = db.get_products(min_watts=MIN_WATTS)
    if df.empty:
        print(f"  No panels with ≥ {MIN_WATTS}W found.")
    else:
        print(df[["manufacturer", "product_name", "wattage_min",
                   "wattage_max", "efficiency_pct",
                   "technology"]].to_string(index=False))


# ──────────────────────────────────────────────
# 7. TOP EFFICIENCY PRODUCTS
# ──────────────────────────────────────────────
if RUN_HIGH_EFFICIENCY:
    divider(f"🏆 TOP 10 MOST EFFICIENT PRODUCTS")
    df = db.get_top_efficiency_products(10)
    print(df.to_string(index=False))


# ──────────────────────────────────────────────
# 8. TECHNOLOGY BREAKDOWN
# ──────────────────────────────────────────────
if RUN_TECH_BREAKDOWN:
    divider("🔭 TECHNOLOGY BREAKDOWN")
    df = db.get_technology_breakdown()
    print(df.to_string(index=False))


# ──────────────────────────────────────────────
# 9. COUNTRY STATISTICS
# ──────────────────────────────────────────────
if RUN_COUNTRY_STATS:
    divider("🌍 STATS BY COUNTRY")
    df = db.get_country_stats()
    print(df.to_string(index=False))


# ──────────────────────────────────────────────
# 10. CERTIFICATIONS
# ──────────────────────────────────────────────
if RUN_CERTIFICATIONS:
    divider("🏅 IEC CERTIFICATIONS")
    df = db.get_certifications(standard="IEC")
    if df.empty:
        print("  No certification data yet.")
    else:
        print(df.to_string(index=False))


# ──────────────────────────────────────────────
# 11. KEYWORD SEARCH
# ──────────────────────────────────────────────
if RUN_KEYWORD_SEARCH:
    divider(f"🔍 KEYWORD SEARCH: '{SEARCH_KEYWORD}'")
    df = db.search(SEARCH_KEYWORD)
    if df.empty:
        print(f"  No results for '{SEARCH_KEYWORD}'")
    else:
        print(df.to_string(index=False))


# ──────────────────────────────────────────────
# 12. SCRAPE RUN HISTORY
# ──────────────────────────────────────────────
if RUN_SCRAPE_HISTORY:
    divider("🕐 SCRAPE RUN HISTORY (last 10)")
    df = db.get_scrape_history(10)
    if df.empty:
        print("  No scrape history yet.")
    else:
        print(df[["manufacturer", "scrape_mode", "started_at",
                   "status", "records_inserted",
                   "duration_seconds"]].to_string(index=False))


# ──────────────────────────────────────────────
# 13. EXPORT CSV
# ──────────────────────────────────────────────
if EXPORT_CSV:
    divider("📄 EXPORTING TO CSV")
    df = db.get_products()
    path = db.export_to_csv(df, "full_product_catalogue.csv")
    print(f"  Saved → {path}")


# ──────────────────────────────────────────────
# 14. EXPORT HTML REPORT
# ──────────────────────────────────────────────
if EXPORT_HTML_REPORT:
    divider("🌐 GENERATING HTML REPORT")
    path = db.export_html_report()
    print(f"  Saved → {path}")
    print("  Open in browser: Right-click → Open In → Browser")

print("\n✅ All queries complete.\n")
