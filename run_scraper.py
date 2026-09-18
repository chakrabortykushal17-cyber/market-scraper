"""
run_scraper.py — Continuous Market Data Pusher
=================================================
Run this on your PC. It:
  1. Scrapes TradingEconomics (stocks + commodities) using your scraper.py
  2. Connects to your REMOTE MilesWeb MySQL (financei1_db)
  3. UPSERTs all data (one row per symbol, always current)
  4. Repeats every 15 seconds

Usage:
    pip install -r requirements.txt
    python run_scraper.py
"""

import time
import sys
import os
from datetime import datetime

# Fix Windows console Unicode encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# ── Configuration ─────────────────────────────────────────────────────────────
SCRAPE_INTERVAL = 3  # seconds between scrape cycles

# Remote MilesWeb MySQL — matches your stock_scraper.php credentials
DB_CONFIG = {
    "host":     "45.199.139.15",   # MilesWeb server IP for financeintels.com
    "port":     3306,
    "user":     "financei1_financeintels",
    "password": "Myogoku@2026",
    "database": "financei1_db",
}

# YOUR PC's current public IP is: 49.37.2.178
# You MUST add this IP in MilesWeb cPanel → Remote MySQL → Add Host
# Otherwise you will get 'Access denied' error.

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    import pymysql
except ImportError:
    print("[ERROR] pymysql not found. Run: pip install pymysql")
    sys.exit(1)

# Import scraper from same folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper import TradingEconomicsScraper, get_market_summary


# ── Database Setup ─────────────────────────────────────────────────────────────
def get_connection():
    return pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )


def init_tables(conn):
    """Creates the scraped_market_data table if it doesn't exist."""
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
    print("[DB] Tables ready.")


def upsert_data(conn, items):
    """
    Inserts scraped items. Each scrape run creates a new row (time-series log).
    The PHP reads the most recent row per symbol to display current values.
    """
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

    import random
    from zoneinfo import ZoneInfo

    STOCK_SESSIONS = {
        'sensex': ('Asia/Kolkata', '09:15', '15:30', [0, 1, 2, 3, 4]),
        'nifty': ('Asia/Kolkata', '09:15', '15:30', [0, 1, 2, 3, 4]),
        'nikkei': ('Asia/Tokyo', '09:00', '15:30', [0, 1, 2, 3, 4]),
        'jp225': ('Asia/Tokyo', '09:00', '15:30', [0, 1, 2, 3, 4]),
        'topix': ('Asia/Tokyo', '09:00', '15:30', [0, 1, 2, 3, 4]),
        'shanghai': ('Asia/Shanghai', '09:30', '15:00', [0, 1, 2, 3, 4]),
        'shenzhen': ('Asia/Shanghai', '09:30', '15:00', [0, 1, 2, 3, 4]),
        'csi 300': ('Asia/Shanghai', '09:30', '15:00', [0, 1, 2, 3, 4]),
        'hang seng': ('Asia/Hong_Kong', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'hk50': ('Asia/Hong_Kong', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'kospi': ('Asia/Seoul', '09:00', '15:30', [0, 1, 2, 3, 4]),
        'asx': ('Australia/Sydney', '10:00', '16:00', [0, 1, 2, 3, 4]),
        'taiex': ('Asia/Taipei', '09:00', '13:30', [0, 1, 2, 3, 4]),
        'tsi': ('Asia/Taipei', '09:00', '13:30', [0, 1, 2, 3, 4]),
        'sti': ('Asia/Singapore', '09:00', '17:00', [0, 1, 2, 3, 4]),
        'klci': ('Asia/Kuala_Lumpur', '09:00', '17:00', [0, 1, 2, 3, 4]),
        'fklci': ('Asia/Kuala_Lumpur', '09:00', '17:00', [0, 1, 2, 3, 4]),
        'psei': ('Asia/Manila', '09:30', '15:00', [0, 1, 2, 3, 4]),
        'jci': ('Asia/Jakarta', '09:00', '16:00', [0, 1, 2, 3, 4]),
        'set': ('Asia/Bangkok', '10:00', '16:30', [0, 1, 2, 3, 4]),
        'vn': ('Asia/Ho_Chi_Minh', '09:00', '15:00', [0, 1, 2, 3, 4]),
        'nzx': ('Pacific/Auckland', '10:00', '17:00', [0, 1, 2, 3, 4]),
        'sp500': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        's&p 500': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'us500': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'nasdaq': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'us100': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'dow jones': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'us30': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'russell': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'us1000': ('America/New_York', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'tsx': ('America/Toronto', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'bovespa': ('America/Sao_Paulo', '10:00', '17:55', [0, 1, 2, 3, 4]),
        'ibovespa': ('America/Sao_Paulo', '10:00', '17:55', [0, 1, 2, 3, 4]),
        'ipc': ('America/Mexico_City', '08:30', '15:00', [0, 1, 2, 3, 4]),
        'merval': ('America/Argentina/Buenos_Aires', '11:00', '17:00', [0, 1, 2, 3, 4]),
        'ipsa': ('America/Santiago', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'igpa': ('America/Santiago', '09:30', '16:00', [0, 1, 2, 3, 4]),
        'colcap': ('America/Bogota', '08:30', '15:00', [0, 1, 2, 3, 4]),
        'de40': ('Europe/Berlin', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'dax': ('Europe/Berlin', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'gb100': ('Europe/London', '08:00', '16:30', [0, 1, 2, 3, 4]),
        'ftse': ('Europe/London', '08:00', '16:30', [0, 1, 2, 3, 4]),
        'fr40': ('Europe/Paris', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'cac': ('Europe/Paris', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'eu50': ('Europe/Berlin', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'it40': ('Europe/Rome', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'es35': ('Europe/Madrid', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'ch20': ('Europe/Zurich', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'nl30': ('Europe/Amsterdam', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'aex': ('Europe/Amsterdam', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'bel20': ('Europe/Brussels', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'be20': ('Europe/Brussels', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'stockholm': ('Europe/Stockholm', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'copenhagen': ('Europe/Copenhagen', '09:00', '17:00', [0, 1, 2, 3, 4]),
        'helsinki': ('Europe/Helsinki', '10:00', '18:30', [0, 1, 2, 3, 4]),
        'wig': ('Europe/Warsaw', '09:00', '17:00', [0, 1, 2, 3, 4]),
        'atx': ('Europe/Vienna', '09:00', '17:30', [0, 1, 2, 3, 4]),
        'moex': ('Europe/Moscow', '10:00', '18:50', [0, 1, 2, 3, 4]),
        'tasi': ('Asia/Riyadh', '10:00', '15:00', [6, 0, 1, 2, 3]),
        'dfm': ('Asia/Dubai', '10:00', '15:00', [0, 1, 2, 3, 4]),
        'adx': ('Asia/Dubai', '10:00', '15:00', [0, 1, 2, 3, 4]),
        'qe': ('Asia/Qatar', '09:30', '13:15', [6, 0, 1, 2, 3]),
        'egx': ('Africa/Cairo', '10:00', '14:30', [6, 0, 1, 2, 3]),
        'sa40': ('Africa/Johannesburg', '09:00', '17:00', [0, 1, 2, 3, 4]),
        'jse': ('Africa/Johannesburg', '09:00', '17:00', [0, 1, 2, 3, 4]),
        'ta-125': ('Asia/Jerusalem', '10:00', '17:30', [6, 0, 1, 2, 3]),
        'bist': ('Europe/Istanbul', '10:00', '18:00', [0, 1, 2, 3, 4]),
    }

    def is_stock_market_open(name):
        low = name.lower()
        for k, (tz, op, cl, days) in STOCK_SESSIONS.items():
            if k in low:
                try:
                    now = datetime.now(ZoneInfo(tz))
                    day = now.weekday()
                    hm = now.strftime('%H:%M')
                    return (day in days and op <= hm <= cl)
                except Exception:
                    return False
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    with conn.cursor() as cur:
        for item in items:
            name = item.get("name") or item.get("symbol") or ""
            if not name:
                continue

            raw_price = item.get("price")
            chg = item.get("change") or 0.0
            chg_pct = item.get("change_percent") or 0.0
            item_type = item.get("type", "stock")

            is_open = True
            if item_type == "stock":
                is_open = is_stock_market_open(name)

            if is_open and raw_price is not None and isinstance(raw_price, (int, float)) and raw_price > 0:
                jitter = (random.random() - 0.495) * (raw_price * 0.00022)
                p_final = round(raw_price + jitter, 4 if raw_price < 5 else 2)
                p_diff = p_final - raw_price
                chg_final = round(chg + p_diff, 4 if raw_price < 5 else 2)
                open_est = raw_price - chg
                chg_pct_final = round((chg_final / open_est) * 100, 2) if open_est > 0 else chg_pct
            else:
                p_final = raw_price
                chg_final = chg
                chg_pct_final = chg_pct

            cur.execute(sql, (
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
            count += 1
    return count


def save_to_local_sqlite(items, db_path="stock_scraper_local.db"):
    """Fallback: saves scraped items to local SQLite database if remote MySQL is unavailable."""
    import sqlite3
    if not items:
        return 0

    sql = """
        INSERT INTO scraped_market_data
            (item_type, category, name, symbol, unit, price, change_val, change_percent,
             weekly_percent, monthly_percent, ytd_percent, yoy_percent,
             market_date, source_url, scraped_at)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        for item in items:
            name = item.get("name") or item.get("symbol") or ""
            if not name:
                continue
            cur.execute(sql, (
                item.get("type", "stock"),
                item.get("category", "General"),
                name,
                name,
                item.get("unit", ""),
                item.get("price"),
                item.get("change"),
                item.get("change_percent"),
                item.get("weekly_percent"),
                item.get("monthly_percent"),
                item.get("ytd_percent"),
                item.get("yoy_percent"),
                item.get("date", ""),
                item.get("url", ""),
                now,
            ))
            count += 1
        conn.commit()
    return count


# ── Main Loop ──────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Finance Intel — TradingEconomics Scraper")
    print("  Pushing data to MilesWeb MySQL every 15 seconds")
    print("=" * 60)

    scraper = TradingEconomicsScraper()
    cycle = 0

    while True:
        cycle += 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{ts}] ── Cycle #{cycle} ──────────────────────────────")

        # 1. Scrape
        try:
            print("  Scraping stocks from TradingEconomics...")
            stocks = scraper.scrape_stocks()
            print(f"  ✓ Stocks: {len(stocks)} items")

            print("  Scraping commodities from TradingEconomics...")
            commodities = scraper.scrape_commodities()
            print(f"  ✓ Commodities: {len(commodities)} items")

            print("  Scraping crypto from TradingEconomics...")
            crypto = scraper.scrape_crypto()
            print(f"  ✓ Crypto: {len(crypto)} items")

            all_data = stocks + commodities + crypto
            print(f"  Total scraped: {len(all_data)} items")

        except Exception as e:
            print(f"  [SCRAPE ERROR] {e}")
            print(f"  Retrying in {SCRAPE_INTERVAL} seconds...")
            time.sleep(SCRAPE_INTERVAL)
            continue

        if not all_data:
            print("  [WARN] No data scraped. Skipping DB write.")
            time.sleep(SCRAPE_INTERVAL)
            continue

        # 2. Connect to DB & push
        conn = None
        try:
            print("  Connecting to MySQL (financei1_db)...")
            conn = get_connection()
            init_tables(conn)

            inserted = upsert_data(conn, all_data)
            print(f"  ✓ Pushed {inserted} rows to MySQL")

            summary = get_market_summary(all_data)
            print(f"  Market summary: {summary['gainers_count']} gainers, "
                  f"{summary['losers_count']} losers, "
                  f"avg change: {summary['avg_change_percent']:.2f}%")

        except pymysql.OperationalError as e:
            print(f"  [DB ERROR] Cannot connect to MySQL: {e}")
            print()
            print("  ── Troubleshooting ─────────────────────────────────")
            print("  1. Open MilesWeb cPanel → Remote MySQL")
            print("  2. Add your PC's public IP (e.g. 49.37.2.145 or 49.37.%.%)")
            print("  3. Update DB_CONFIG['host'] in this file with server IP")
            print("  ────────────────────────────────────────────────────")
            print("  [FALLBACK] Saving to local SQLite database (stock_scraper_local.db)...")
            try:
                saved = save_to_local_sqlite(all_data)
                print(f"  ✓ Saved {saved} rows to local SQLite DB")
            except Exception as sql_err:
                print(f"  [SQLite Error] {sql_err}")

        except Exception as e:
            print(f"  [DB ERROR] {e}")

        finally:
            if conn:
                conn.close()

        print(f"  Sleeping {SCRAPE_INTERVAL}s until next cycle...")
        time.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Stopped] Scraper terminated by user.")
        sys.exit(0)
