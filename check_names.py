import sys, io, pymysql
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(
    host='45.199.139.15', port=3306,
    user='financei1_financeintels', password='Myogoku@2026',
    database='financei1_db', cursorclass=pymysql.cursors.DictCursor, connect_timeout=10
)
with conn.cursor() as cur:
    cur.execute("SELECT DISTINCT name, symbol, category, price, change_percent FROM scraped_market_data WHERE item_type='stock'")
    rows = cur.fetchall()
    print(f"Total distinct stocks: {len(rows)}")
    for r in rows:
        print(f"{r['category']} | {r['name']} | price: {r['price']} | chg%: {r['change_percent']}")
conn.close()
