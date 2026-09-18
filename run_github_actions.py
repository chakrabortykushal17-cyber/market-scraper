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
from zoneinfo import ZoneInfo

STOCK_SESSIONS = {
    # Asia-Pacific
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
    # Americas
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
    # Europe
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
    # Middle East & Africa
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
        item_type = item.get("type", "stock")

        # Closed stock markets must NEVER be jittered or fluctuated
        is_open = True
        if item_type == "stock":
            is_open = is_stock_market_open(name)

        if is_open and raw_price is not None and isinstance(raw_price, (int, float)) and raw_price > 0:
            key = name.lower()
            prev = LAST_PUSHED_STATE.get(key, {})
            base_p = prev.get("base", raw_price)
            if abs(raw_price - base_p) / (base_p or 1) >= 0.002:
                base_p = raw_price

            # Subtle realistic 3-second micro-tick (0.01% - 0.02%) only when market is actively OPEN
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
            # Strictly frozen at the official scraped closing price without any artificial noise
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
