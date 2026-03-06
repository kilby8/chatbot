"""
cli.py
Interactive command-line interface for exploring solar.db.
"""

from __future__ import annotations

from db_manager import SolarDB
from solar_scraper_with_db import run_scraper_with_db


def print_menu() -> None:
    print("\n" + "=" * 62)
    print(" Solar DB CLI")
    print("=" * 62)
    print("1) Database stats")
    print("2) List manufacturers")
    print("3) List products")
    print("4) Filter products by technology")
    print("5) Keyword search")
    print("6) Run scraper and save to DB")
    print("7) Export HTML report")
    print("0) Exit")


def run_cli() -> None:
    db = SolarDB()
    while True:
        print_menu()
        choice = input("Select option: ").strip()

        if choice == "1":
            stats = db.get_database_stats()
            print("\nDatabase statistics")
            for k, v in stats.items():
                print(f"  - {k}: {v}")

        elif choice == "2":
            df = db.get_all_manufacturers()
            if df.empty:
                print("No manufacturers found. Run scraper first.")
            else:
                print(df.to_string(index=False))

        elif choice == "3":
            df = db.get_products()
            if df.empty:
                print("No products found. Run scraper first.")
            else:
                print(df.to_string(index=False))

        elif choice == "4":
            tech = input("Technology (e.g., TOPCon): ").strip()
            df = db.get_products(technology=tech)
            if df.empty:
                print(f"No products found for technology: {tech}")
            else:
                print(df.to_string(index=False))

        elif choice == "5":
            keyword = input("Keyword: ").strip()
            df = db.search(keyword)
            if df.empty:
                print(f"No results for keyword: {keyword}")
            else:
                print(df.to_string(index=False))

        elif choice == "6":
            run_scraper_with_db()

        elif choice == "7":
            path = db.export_html_report()
            print(f"Report generated at: {path}")

        elif choice == "0":
            print("Goodbye.")
            break

        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    run_cli()
