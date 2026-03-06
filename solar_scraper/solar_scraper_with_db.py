"""
solar_scraper_with_db.py
Scraper + database integration entrypoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

from db_manager import ScrapeResult, SolarDB
from solar_scraper import SolarScraper


def run_scraper_with_db() -> None:
    db = SolarDB()
    scraper = SolarScraper()

    print("Starting scrape...")
    payload = scraper.scrape_all()
    manufacturers = payload["manufacturers"]
    products_by_mfr = payload["products"]

    db.upsert_manufacturers(manufacturers)

    total_inserted = 0
    for manufacturer in manufacturers:
        name = manufacturer["name"]
        started_at = datetime.now(timezone.utc)
        products = products_by_mfr.get(name, [])
        try:
            inserted = db.upsert_products(name, products)
            total_inserted += inserted
            db.record_scrape_run(
                ScrapeResult(
                    manufacturer_name=name,
                    scrape_mode="seed_web_scrape",
                    started_at=started_at,
                    status="success",
                    records_inserted=inserted,
                )
            )
            print(f"  - {name}: {inserted} products saved")
        except Exception as exc:
            db.record_scrape_run(
                ScrapeResult(
                    manufacturer_name=name,
                    scrape_mode="seed_web_scrape",
                    started_at=started_at,
                    status="failed",
                    records_inserted=0,
                    error_message=str(exc),
                )
            )
            print(f"  - {name}: failed ({exc})")

    print("\nScrape + DB load completed.")
    print(f"Manufacturers processed: {len(manufacturers)}")
    print(f"Products saved:          {total_inserted}")
    print(f"Database path:           {db.db_path}")


if __name__ == "__main__":
    run_scraper_with_db()
