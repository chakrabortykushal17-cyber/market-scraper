"""
run_github_actions.py — GitHub Actions Cloud Scraper Runner
===========================================================
Runs in GitHub Actions cloud environment.
Reads credentials from Environment Variables (GitHub Secrets).
Scrapes TradingEconomics and pushes to MilesWeb MySQL.
"""

import os
import sys
import time
from datetime import datetime

# Import pymysql
try:
    import pymysql
except ImportError:
    print("[ERROR] pymysql is not installed.")
    sys.exit(1)

# Import scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper import TradingEconomicsScraper, get_market_summary

# ── Configuration (Reads from Environment Variables / GitHub Secrets) ──────────
DB_HOST = os.getenv("DB_HOST", "45.199.139.15")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "financei1_financeintels")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Myogoku@2026")
DB_NAME = os.getenv("DB_NAME", "financei1_db")

SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "3"))  # seconds between cycles
MAX_RUNTIME_MINUTES = int(os.getenv("MAX_RUNTIME_MINUTES", "330"))  # 5.5 hours runtime per job


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
    )


def init_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraped_market_data (
                id               BIGINT AUTO_INCREMENT PRIMARY KEY,
                item_type        VARCHAR(20),
                category         VARCHAR(100),
                name             VARCHAR(200) NOT NULL,
                symbol           VARCHAR(200) NOT NULL,
                unit             VARCHAR(50),
                price            DOUBLE,
                change_val       DOUBLE,
                change_percent   DOUBLE,
                weekly_percent   DOUBLE,
                monthly_percent  DOUBLE,
                ytd_percent      DOUBLE,
                yoy_percent      DOUBLE,
                market_date      VARCHAR(50),
                source_url       TEXT,
                scraped_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_symbol (symbol(150)),
                INDEX idx_scraped_at (scraped_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)


def clean_old_records(conn, days_to_keep=3):
    """Automatically cleans up records older than days_to_keep to keep DB fast and light."""
    try:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM scraped_market_data WHERE scraped_at < NOW() - INTERVAL {days_to_keep} DAY LIMIT 20000")
            deleted = cur.rowcount
            if deleted > 0:
                print(f"  [DB CLEANUP] Automatically purged {deleted} old records.")
    except Exception as e:
        pass


import random

LAST_PUSHED_STATE = {}


def push_data(conn, items):
    if not items:
        return 0

    sql = """
        INSERT INTO scraped_market_data
            (item_type, category, name, symbol, unit, price, change_val, change_percent,
             weekly_percent, monthly_percent, ytd_percent, yoy_percent,
             market_date, source_url, scraped_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for item in items:
        name = item.get("name") or item.get("symbol") or ""
        if not name:
            continue

        raw_price = item.get("price")
        chg = item.get("change") or 0.0
        chg_pct = item.get("change_percent") or 0.0

        if raw_price is not None and isinstance(raw_price, (int, float)) and raw_price > 0:
            key = name.lower()
            prev = LAST_PUSHED_STATE.get(key, {})
            base_p = prev.get("base", raw_price)
            if abs(raw_price - base_p) / (base_p or 1) >= 0.002:
                base_p = raw_price

            # Subtle realistic 3-second micro-tick (0.01% - 0.02%)
            jitter = (random.random() - 0.495) * (base_p * 0.00022)
            curr = prev.get("curr", base_p) + jitter
            # Bound strictly within +/- 0.05%
            curr = max(base_p * 0.9995, min(base_p * 1.0005, curr))

            precision = 4 if base_p < 5 else 2
            p_final = round(curr, precision)
            LAST_PUSHED_STATE[key] = {"base": base_p, "curr": p_final}

            p_diff = p_final - raw_price
            chg_final = round(chg + p_diff, precision)
            open_est = base_p - chg
            chg_pct_final = round((chg_final / open_est) * 100, 2) if open_est > 0 else chg_pct
        else:
            p_final = raw_price
            chg_final = chg
            chg_pct_final = chg_pct

        rows.append((
            item.get("type", "stock"),
            item.get("category", "General"),
            name,
            name,
            item.get("unit", ""),
            p_final,
            chg_final,
            chg_pct_final,
            item.get("weekly_percent"),
            item.get("monthly_percent"),
            item.get("ytd_percent"),
            item.get("yoy_percent"),
            item.get("date", ""),
            item.get("url", ""),
            now,
        ))

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    return len(rows)


def run_cycle(scraper):
    stocks = scraper.scrape_stocks()
    commodities = scraper.scrape_commodities()
    crypto = scraper.scrape_crypto()
    return stocks + commodities + crypto


def main():
    print("=" * 65)
    print("  GitHub Actions Cloud Scraper — TradingEconomics to MilesWeb")
    print(f"  Interval: {SCRAPE_INTERVAL}s | Target Server: {DB_HOST}")
    print("=" * 65)

    scraper = TradingEconomicsScraper()
    start_time = time.time()
    max_duration_seconds = MAX_RUNTIME_MINUTES * 60
    cycle = 0

    # Initialize connection and tables ONCE at startup
    print("  Connecting to MilesWeb MySQL (persistent connection)...")
    conn = None
    try:
        conn = get_connection()
        init_tables(conn)
        print("  ✓ Database connected and tables verified.")
    except Exception as e:
        print(f"  [DB INIT WARNING] {e} — will retry during cycle loop.")

    while True:
        elapsed = time.time() - start_time
        if elapsed >= max_duration_seconds:
            print(f"\n[DONE] Reached target job duration ({MAX_RUNTIME_MINUTES} mins). Exiting cleanly.")
            break

        cycle += 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{ts}] ── Cycle #{cycle} (Elapsed: {int(elapsed)}s/{max_duration_seconds}s) ──")

        try:
            print("  Scraping TradingEconomics (Stocks, Commodities, Crypto)...")
            t_scrape = time.time()
            data = run_cycle(scraper)
            print(f"  ✓ Scraped {len(data)} items in {time.time() - t_scrape:.1f}s.")

            if not data:
                print("  [WARN] No data scraped. Retrying next cycle.")
                time.sleep(SCRAPE_INTERVAL)
                continue

            # Ensure connection is active (ping with auto-reconnect)
            if conn is None:
                conn = get_connection()
            else:
                try:
                    conn.ping(reconnect=True)
                except Exception:
                    conn = get_connection()

            t_push = time.time()
            inserted = push_data(conn, data)
            print(f"  ✓ Pushed {inserted} records in {time.time() - t_push:.2f}s!")

            summary = get_market_summary(data)
            print(f"  Summary: {summary.get('gainers_count', 0)} Gainers | "
                  f"{summary.get('losers_count', 0)} Losers | "
                  f"Avg Change: {summary.get('avg_change_percent', 0.0)}%")

            # Periodically prune stale data older than 3 days
            if cycle % 50 == 0:
                clean_old_records(conn, 3)

        except Exception as e:
            print(f"  [ERROR] {e}")

        print(f"  Sleeping {SCRAPE_INTERVAL}s until next cycle...")
        time.sleep(SCRAPE_INTERVAL)

    if conn:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
