"""
prune_database.py — Safely delete older records from scraped_market_data in chunks
Keeps the latest 3 days of data (plenty for all real-time prices & history charts).
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_scraper

def prune_old_data(days_to_keep=3, chunk_size=50000):
    conn = run_scraper.get_connection()
    cur = conn.cursor()

    print(f"[PRUNE] Finding cutoff ID for records older than {days_to_keep} days...")
    cur.execute(f"SELECT MAX(id) as cutoff FROM scraped_market_data WHERE scraped_at < NOW() - INTERVAL {days_to_keep} DAY")
    row = cur.fetchone()
    cutoff_id = row['cutoff'] if row else None

    if not cutoff_id:
        print("[PRUNE] No old records found to delete.")
        conn.close()
        return

    print(f"[PRUNE] Cutoff ID is {cutoff_id}. Deleting records in chunks of {chunk_size}...")

    total_deleted = 0
    t_start = time.time()

    while True:
        t0 = time.time()
        cur.execute(f"DELETE FROM scraped_market_data WHERE id <= %s LIMIT %s", (cutoff_id, chunk_size))
        deleted = cur.rowcount
        total_deleted += deleted

        if deleted == 0:
            break

        elapsed = time.time() - t_start
        print(f"  ✓ Deleted {deleted} rows (Total: {total_deleted:,} | Chunk time: {time.time() - t0:.2f}s | Elapsed: {elapsed:.1f}s)")
        # Brief pause to let any pending web queries execute freely
        time.sleep(0.05)

    print(f"\n[COMPLETE] Successfully purged {total_deleted:,} old records in {time.time() - t_start:.1f}s!")

    # Check remaining count
    cur.execute("SELECT COUNT(*) as remaining, MIN(scraped_at) as earliest, MAX(scraped_at) as latest FROM scraped_market_data")
    stats = cur.fetchone()
    print(f"[STATS] Remaining records: {stats['remaining']:,}")
    print(f"[STATS] Earliest record: {stats['earliest']}")
    print(f"[STATS] Latest record:   {stats['latest']}")

    conn.close()

if __name__ == "__main__":
    prune_old_data()
