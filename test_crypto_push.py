import sys, os
from scraper import TradingEconomicsScraper
from run_scraper import get_connection, init_tables, upsert_data

s = TradingEconomicsScraper()
crypto = s.scrape_crypto()
print(f"Scraped crypto count: {len(crypto)}")

conn = get_connection()
init_tables(conn)
cnt = upsert_data(conn, crypto)
print(f"Pushed {cnt} crypto rows to MySQL")

with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) as c FROM scraped_market_data WHERE item_type='crypto'")
    print("MySQL crypto row count:", cur.fetchone())
conn.close()
