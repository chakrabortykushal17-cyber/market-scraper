from run_scraper import get_connection

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT name, symbol, price, unit FROM scraped_market_data WHERE item_type='crypto' AND unit='USD' AND price IS NOT NULL")
    rows = cur.fetchall()
    print(f"Total USD crypto items in DB: {len(rows)}")
    for r in rows:
        print(f"Name: '{r['name']}' | Symbol: '{r['symbol']}' | Price: {r['price']} | Unit: '{r['unit']}'")
conn.close()
