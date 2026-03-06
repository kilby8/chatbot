"""
db_manager.py
Core SQLite database engine and query helpers for the solar scraper project.
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "solar_data")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
DB_PATH = os.path.join(BASE_DIR, "solar_data", "solar.db")
LOG_PATH = os.path.join(DATA_DIR, "scraper.log")


@dataclass
class ScrapeResult:
    manufacturer_name: str
    scrape_mode: str
    started_at: datetime
    status: str
    records_inserted: int
    error_message: str | None = None


class SolarDB:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_paths()
        self.engine: Engine = create_engine(f"sqlite:///{self.db_path}", future=True)
        self._initialize_database()

    def _ensure_paths(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, "w", encoding="utf-8") as log_file:
                log_file.write(f"{self._now_iso()} | SolarDB initialized\n")

    def _initialize_database(self) -> None:
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS manufacturers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                country TEXT,
                tier INTEGER,
                annual_capacity_gw REAL,
                base_url TEXT,
                website_active INTEGER DEFAULT 1,
                last_scraped TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manufacturer_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                technology TEXT,
                cell_type TEXT,
                wattage_min REAL,
                wattage_max REAL,
                efficiency_pct REAL,
                warranty_years INTEGER,
                availability TEXT,
                datasheet_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(manufacturer_id, product_name),
                FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS certifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                standard TEXT NOT NULL,
                certificate_code TEXT,
                issued_by TEXT,
                valid_until TEXT,
                UNIQUE(product_id, standard, certificate_code),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manufacturer_id INTEGER,
                scrape_mode TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                records_inserted INTEGER DEFAULT 0,
                duration_seconds REAL,
                error_message TEXT,
                FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
            );
            """,
        ]

        with self.engine.begin() as conn:
            for ddl in ddl_statements:
                conn.execute(text(ddl))

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_standard(raw_standard: str) -> str:
        return raw_standard.strip().upper()

    def _query_df(self, sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql_query(text(sql), conn, params=params or {})

    def get_or_create_manufacturer(self, manufacturer: dict[str, Any]) -> int:
        row = self._query_df(
            "SELECT id FROM manufacturers WHERE name = :name",
            {"name": manufacturer["name"]},
        )
        if not row.empty:
            return int(row.iloc[0]["id"])

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO manufacturers (name, last_scraped)
                    VALUES (:name, :last_scraped)
                    """
                ),
                {"name": manufacturer["name"], "last_scraped": self._now_iso()},
            )
        row = self._query_df(
            "SELECT id FROM manufacturers WHERE name = :name",
            {"name": manufacturer["name"]},
        )
        return int(row.iloc[0]["id"])

    def upsert_manufacturers(self, manufacturers: list[dict[str, Any]]) -> int:
        if not manufacturers:
            return 0

        sql = text(
            """
            INSERT INTO manufacturers (
                name, country, tier, annual_capacity_gw, base_url,
                website_active, last_scraped
            ) VALUES (
                :name, :country, :tier, :annual_capacity_gw, :base_url,
                :website_active, :last_scraped
            )
            ON CONFLICT(name) DO UPDATE SET
                country = COALESCE(excluded.country, manufacturers.country),
                tier = COALESCE(excluded.tier, manufacturers.tier),
                annual_capacity_gw = COALESCE(excluded.annual_capacity_gw, manufacturers.annual_capacity_gw),
                base_url = COALESCE(excluded.base_url, manufacturers.base_url),
                website_active = COALESCE(excluded.website_active, manufacturers.website_active),
                last_scraped = COALESCE(excluded.last_scraped, manufacturers.last_scraped)
            """
        )

        now = self._now_iso()
        rows = []
        for item in manufacturers:
            rows.append(
                {
                    "name": item["name"],
                    "country": item.get("country"),
                    "tier": item.get("tier"),
                    "annual_capacity_gw": item.get("annual_capacity_gw"),
                    "base_url": item.get("base_url"),
                    "website_active": int(bool(item.get("website_active", True))),
                    "last_scraped": item.get("last_scraped", now),
                }
            )

        with self.engine.begin() as conn:
            conn.execute(sql, rows)
        return len(rows)

    def upsert_products(self, manufacturer_name: str, products: list[dict[str, Any]]) -> int:
        if not products:
            return 0

        manufacturer_id = self.get_or_create_manufacturer({"name": manufacturer_name})
        product_sql = text(
            """
            INSERT INTO products (
                manufacturer_id, product_name, technology, cell_type,
                wattage_min, wattage_max, efficiency_pct, warranty_years,
                availability, datasheet_url
            ) VALUES (
                :manufacturer_id, :product_name, :technology, :cell_type,
                :wattage_min, :wattage_max, :efficiency_pct, :warranty_years,
                :availability, :datasheet_url
            )
            ON CONFLICT(manufacturer_id, product_name) DO UPDATE SET
                technology = excluded.technology,
                cell_type = excluded.cell_type,
                wattage_min = excluded.wattage_min,
                wattage_max = excluded.wattage_max,
                efficiency_pct = excluded.efficiency_pct,
                warranty_years = excluded.warranty_years,
                availability = excluded.availability,
                datasheet_url = excluded.datasheet_url
            """
        )

        rows = []
        for product in products:
            rows.append(
                {
                    "manufacturer_id": manufacturer_id,
                    "product_name": product["product_name"],
                    "technology": product.get("technology"),
                    "cell_type": product.get("cell_type"),
                    "wattage_min": product.get("wattage_min"),
                    "wattage_max": product.get("wattage_max"),
                    "efficiency_pct": product.get("efficiency_pct"),
                    "warranty_years": product.get("warranty_years"),
                    "availability": product.get("availability", "unknown"),
                    "datasheet_url": product.get("datasheet_url"),
                }
            )

        with self.engine.begin() as conn:
            conn.execute(product_sql, rows)

            for product in products:
                certs = product.get("certifications", [])
                if not certs:
                    continue

                product_id_query = text(
                    """
                    SELECT id FROM products
                    WHERE manufacturer_id = :manufacturer_id
                      AND product_name = :product_name
                    """
                )
                product_row = conn.execute(
                    product_id_query,
                    {
                        "manufacturer_id": manufacturer_id,
                        "product_name": product["product_name"],
                    },
                ).fetchone()
                if not product_row:
                    continue

                product_id = int(product_row[0])
                for cert in certs:
                    if isinstance(cert, dict):
                        standard = self._normalize_standard(str(cert.get("standard", "")))
                        certificate_code = cert.get("certificate_code") or ""
                        issued_by = cert.get("issued_by")
                        valid_until = cert.get("valid_until")
                    else:
                        standard = self._normalize_standard(str(cert))
                        certificate_code = ""
                        issued_by = None
                        valid_until = None

                    if not standard:
                        continue

                    conn.execute(
                        text(
                            """
                            INSERT INTO certifications (
                                product_id, standard, certificate_code, issued_by, valid_until
                            ) VALUES (
                                :product_id, :standard, :certificate_code, :issued_by, :valid_until
                            )
                            ON CONFLICT(product_id, standard, certificate_code) DO NOTHING
                            """
                        ),
                        {
                            "product_id": product_id,
                            "standard": standard,
                            "certificate_code": certificate_code,
                            "issued_by": issued_by,
                            "valid_until": valid_until,
                        },
                    )

        return len(rows)

    def record_scrape_run(self, result: ScrapeResult) -> None:
        manufacturer_row = self._query_df(
            "SELECT id FROM manufacturers WHERE name = :name",
            {"name": result.manufacturer_name},
        )
        manufacturer_id = int(manufacturer_row.iloc[0]["id"]) if not manufacturer_row.empty else None

        finished_at = datetime.now(timezone.utc)
        duration_seconds = (finished_at - result.started_at).total_seconds()

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO scrape_runs (
                        manufacturer_id, scrape_mode, started_at, finished_at, status,
                        records_inserted, duration_seconds, error_message
                    ) VALUES (
                        :manufacturer_id, :scrape_mode, :started_at, :finished_at, :status,
                        :records_inserted, :duration_seconds, :error_message
                    )
                    """
                ),
                {
                    "manufacturer_id": manufacturer_id,
                    "scrape_mode": result.scrape_mode,
                    "started_at": result.started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "status": result.status,
                    "records_inserted": result.records_inserted,
                    "duration_seconds": duration_seconds,
                    "error_message": result.error_message,
                },
            )

    def get_database_stats(self) -> dict[str, Any]:
        stats = {}
        with self.engine.connect() as conn:
            stats["manufacturers_total"] = conn.execute(text("SELECT COUNT(*) FROM manufacturers")).scalar_one()
            stats["tier1_manufacturers"] = conn.execute(
                text("SELECT COUNT(*) FROM manufacturers WHERE tier = 1")
            ).scalar_one()
            stats["products_total"] = conn.execute(text("SELECT COUNT(*) FROM products")).scalar_one()
            stats["products_with_efficiency"] = conn.execute(
                text("SELECT COUNT(*) FROM products WHERE efficiency_pct IS NOT NULL")
            ).scalar_one()
            stats["certifications_total"] = conn.execute(text("SELECT COUNT(*) FROM certifications")).scalar_one()
            stats["last_scrape_at"] = conn.execute(text("SELECT MAX(finished_at) FROM scrape_runs")).scalar_one()

        stats["db_size_mb"] = round(os.path.getsize(self.db_path) / (1024 * 1024), 4) if os.path.exists(self.db_path) else 0
        return stats

    def get_all_manufacturers(self, tier: int | None = None) -> pd.DataFrame:
        sql = """
            SELECT
                id,
                name,
                country,
                tier,
                annual_capacity_gw,
                base_url,
                website_active,
                last_scraped
            FROM manufacturers
        """
        params: dict[str, Any] = {}
        if tier is not None:
            sql += " WHERE tier = :tier"
            params["tier"] = tier
        sql += " ORDER BY name"
        return self._query_df(sql, params)

    def get_products(
        self,
        technology: str | None = None,
        min_watts: float | None = None,
        min_efficiency: float | None = None,
        manufacturer: str | None = None,
    ) -> pd.DataFrame:
        sql = """
            SELECT
                p.id,
                m.name AS manufacturer,
                m.country,
                p.product_name,
                p.technology,
                p.cell_type,
                p.wattage_min,
                p.wattage_max,
                p.efficiency_pct,
                p.warranty_years,
                p.availability,
                p.datasheet_url
            FROM products p
            JOIN manufacturers m ON m.id = p.manufacturer_id
            WHERE 1 = 1
        """
        params: dict[str, Any] = {}
        if technology:
            sql += " AND LOWER(p.technology) = LOWER(:technology)"
            params["technology"] = technology
        if min_watts is not None:
            sql += " AND COALESCE(p.wattage_max, p.wattage_min, 0) >= :min_watts"
            params["min_watts"] = min_watts
        if min_efficiency is not None:
            sql += " AND COALESCE(p.efficiency_pct, 0) >= :min_efficiency"
            params["min_efficiency"] = min_efficiency
        if manufacturer:
            sql += " AND LOWER(m.name) LIKE LOWER(:manufacturer)"
            params["manufacturer"] = f"%{manufacturer}%"

        sql += " ORDER BY m.name, p.product_name"
        return self._query_df(sql, params)

    def get_top_efficiency_products(self, limit: int = 10) -> pd.DataFrame:
        return self._query_df(
            """
            SELECT
                m.name AS manufacturer,
                p.product_name,
                p.technology,
                p.efficiency_pct,
                p.wattage_max,
                p.warranty_years
            FROM products p
            JOIN manufacturers m ON m.id = p.manufacturer_id
            WHERE p.efficiency_pct IS NOT NULL
            ORDER BY p.efficiency_pct DESC, p.wattage_max DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )

    def get_technology_breakdown(self) -> pd.DataFrame:
        return self._query_df(
            """
            SELECT
                COALESCE(technology, 'Unknown') AS technology,
                COUNT(*) AS products,
                ROUND(AVG(efficiency_pct), 2) AS avg_efficiency_pct,
                ROUND(AVG(wattage_max), 1) AS avg_wattage_max
            FROM products
            GROUP BY COALESCE(technology, 'Unknown')
            ORDER BY products DESC, technology
            """
        )

    def get_country_stats(self) -> pd.DataFrame:
        return self._query_df(
            """
            SELECT
                COALESCE(m.country, 'Unknown') AS country,
                COUNT(DISTINCT m.id) AS manufacturers,
                COUNT(p.id) AS products,
                ROUND(AVG(m.annual_capacity_gw), 2) AS avg_annual_capacity_gw
            FROM manufacturers m
            LEFT JOIN products p ON p.manufacturer_id = m.id
            GROUP BY COALESCE(m.country, 'Unknown')
            ORDER BY manufacturers DESC, products DESC, country
            """
        )

    def get_certifications(self, standard: str | None = None) -> pd.DataFrame:
        sql = """
            SELECT
                m.name AS manufacturer,
                p.product_name,
                c.standard,
                c.certificate_code,
                c.issued_by,
                c.valid_until
            FROM certifications c
            JOIN products p ON p.id = c.product_id
            JOIN manufacturers m ON m.id = p.manufacturer_id
            WHERE 1 = 1
        """
        params: dict[str, Any] = {}
        if standard:
            sql += " AND UPPER(c.standard) LIKE :standard"
            params["standard"] = f"%{standard.upper()}%"
        sql += " ORDER BY c.standard, m.name, p.product_name"
        return self._query_df(sql, params)

    def search(self, keyword: str) -> pd.DataFrame:
        wildcard = f"%{keyword.lower()}%"
        return self._query_df(
            """
            SELECT
                m.name AS manufacturer,
                p.product_name,
                p.technology,
                p.cell_type,
                p.wattage_max,
                p.efficiency_pct,
                p.availability
            FROM products p
            JOIN manufacturers m ON m.id = p.manufacturer_id
            WHERE LOWER(m.name) LIKE :q
               OR LOWER(p.product_name) LIKE :q
               OR LOWER(COALESCE(p.technology, '')) LIKE :q
               OR LOWER(COALESCE(p.cell_type, '')) LIKE :q
               OR LOWER(COALESCE(p.availability, '')) LIKE :q
            ORDER BY m.name, p.product_name
            """,
            {"q": wildcard},
        )

    def get_scrape_history(self, limit: int = 10) -> pd.DataFrame:
        return self._query_df(
            """
            SELECT
                COALESCE(m.name, 'Unknown') AS manufacturer,
                s.scrape_mode,
                s.started_at,
                s.finished_at,
                s.status,
                s.records_inserted,
                s.duration_seconds,
                s.error_message
            FROM scrape_runs s
            LEFT JOIN manufacturers m ON m.id = s.manufacturer_id
            ORDER BY s.id DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )

    def export_to_csv(self, df: pd.DataFrame, filename: str) -> str:
        os.makedirs(DATA_DIR, exist_ok=True)
        path = os.path.join(DATA_DIR, filename)
        df.to_csv(path, index=False)
        return path

    def export_html_report(self) -> str:
        os.makedirs(REPORTS_DIR, exist_ok=True)

        stats = self.get_database_stats()
        top_eff = self.get_top_efficiency_products(20)
        tech_breakdown = self.get_technology_breakdown()
        country_stats = self.get_country_stats()

        html = f"""
        <html>
          <head>
            <meta charset="utf-8" />
            <title>Solar Catalogue Report</title>
            <style>
              body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
              h1, h2 {{ margin-bottom: 0.4rem; }}
              table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
              th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
              th {{ background: #f4f6f8; }}
              .meta {{ margin-bottom: 20px; color: #666; }}
            </style>
          </head>
          <body>
            <h1>Solar Catalogue Report</h1>
            <div class="meta">Generated: {self._now_iso()}</div>
            <h2>Database Statistics</h2>
            <ul>
              <li>Manufacturers: {stats.get('manufacturers_total', 0)}</li>
              <li>Tier-1 Manufacturers: {stats.get('tier1_manufacturers', 0)}</li>
              <li>Products: {stats.get('products_total', 0)}</li>
              <li>Certifications: {stats.get('certifications_total', 0)}</li>
              <li>Database Size (MB): {stats.get('db_size_mb', 0)}</li>
            </ul>
            <h2>Top Efficiency Products</h2>
            {top_eff.to_html(index=False)}
            <h2>Technology Breakdown</h2>
            {tech_breakdown.to_html(index=False)}
            <h2>Country Statistics</h2>
            {country_stats.to_html(index=False)}
          </body>
        </html>
        """

        report_path = os.path.join(REPORTS_DIR, "solar_catalogue_report.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
        return report_path


if __name__ == "__main__":
    db = SolarDB()
    print("Database initialized at:", db.db_path)
    print("Stats:", db.get_database_stats())
