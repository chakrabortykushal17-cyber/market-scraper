import sys, io, pymysql
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(
    host='45.199.139.15', port=3306,
    user='financei1_financeintels', password='Myogoku@2026',
    database='financei1_db', cursorclass=pymysql.cursors.DictCursor, connect_timeout=10
)
with conn.cursor() as cur:
    cur.execute("SELECT DISTINCT name, item_type, category FROM scraped_market_data ORDER BY item_type, category, name")
    rows = cur.fetchall()
    print(f"Total unique scraped names: {len(rows)}")
    for r in rows:
        print(f"{r['item_type']} | {r['category']} | {r['name']}")
conn.close()
