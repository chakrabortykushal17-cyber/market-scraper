"""
Database Helper Module for TradingEconomics Stock Scraper.
Supports MySQL, PostgreSQL, and SQLite with automatic schema initialization,
batch snapshot recording, execution logging, and historical query support.
"""

import os
import sqlite3
from datetime import datetime

# Optional drivers
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class DatabaseManager:
    def __init__(
        self,
        db_type=None,
        host=None,
        port=None,
        user=None,
        password=None,
        db_name=None,
    ):
        self.db_type = (db_type or os.getenv("DB_TYPE", "mysql")).lower()
        self.host = host or os.getenv("DB_HOST", "45.199.139.15")
        self.port = int(port or os.getenv("DB_PORT", 3306 if self.db_type == "mysql" else 5432))
        self.user = user or os.getenv("DB_USER", "financei1_financeintels")
        self.password = password or os.getenv("DB_PASSWORD", "Myogoku@2026")
        self.db_name = db_name or os.getenv("DB_NAME", "financei1_db")
        self.sqlite_path = os.getenv("SQLITE_PATH", "stock_scraper_local.db")
        
        self.active_engine = "none"
        self.is_connected = False
        self.last_error = None

        # Test connection & initialize schema
        self.init_db()

    def get_connection(self):
        """Attempts connection to MySQL, PostgreSQL, or falls back gracefully to SQLite."""
        # 1. MySQL
        if self.db_type == "mysql" and HAS_PYMYSQL:
            try:
                conn = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.db_name,
                    autocommit=True,
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=3,
                )
                self.active_engine = "MySQL"
                self.is_connected = True
                return conn, "mysql"
            except Exception as e:
                self.last_error = f"MySQL connection failed ({e})"

        # 2. PostgreSQL
        if self.db_type in ["postgres", "postgresql"] and HAS_PSYCOPG2:
            try:
                conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    dbname=self.db_name,
                    connect_timeout=3,
                )
                conn.autocommit = True
                self.active_engine = "PostgreSQL"
                self.is_connected = True
                return conn, "postgres"
            except Exception as e:
                self.last_error = f"PostgreSQL connection failed ({e})"

        # 3. SQLite Fallback (Zero setup local DB file)
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            self.active_engine = "SQLite (Local DB)"
            self.is_connected = True
            return conn, "sqlite"
        except Exception as e:
            self.last_error = f"SQLite connection failed ({e})"
            self.is_connected = False
            return None, "none"

    def init_db(self):
        """Creates required tables if they don't already exist."""
        conn, engine = self.get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            if engine == "mysql":
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}`;")
                cursor.execute(f"USE `{self.db_name}`;")
                
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_market_data (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    item_type VARCHAR(20),
                    category VARCHAR(100),
                    name VARCHAR(150),
                    symbol VARCHAR(150),
                    unit VARCHAR(50),
                    price DECIMAL(18, 4),
                    change_val DECIMAL(18, 4),
                    change_percent DECIMAL(10, 4),
                    weekly_percent DECIMAL(10, 4),
                    monthly_percent DECIMAL(10, 4),
                    ytd_percent DECIMAL(10, 4),
                    yoy_percent DECIMAL(10, 4),
                    market_date VARCHAR(50),
                    source_url TEXT,
                    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_symbol (symbol),
                    INDEX idx_scraped_at (scraped_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraper_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    target VARCHAR(50),
                    total_items INT,
                    gainers_count INT,
                    losers_count INT,
                    avg_change_percent DECIMAL(10, 4),
                    status VARCHAR(50),
                    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)

            elif engine == "postgres":
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_market_data (
                    id BIGSERIAL PRIMARY KEY,
                    item_type VARCHAR(20),
                    category VARCHAR(100),
                    name VARCHAR(150),
                    symbol VARCHAR(150),
                    unit VARCHAR(50),
                    price NUMERIC(18, 4),
                    change_val NUMERIC(18, 4),
                    change_percent NUMERIC(10, 4),
                    weekly_percent NUMERIC(10, 4),
                    monthly_percent NUMERIC(10, 4),
                    ytd_percent NUMERIC(10, 4),
                    yoy_percent NUMERIC(10, 4),
                    market_date VARCHAR(50),
                    source_url TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sym ON scraped_market_data(symbol);
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraper_logs (
                    id BIGSERIAL PRIMARY KEY,
                    target VARCHAR(50),
                    total_items INT,
                    gainers_count INT,
                    losers_count INT,
                    avg_change_percent NUMERIC(10, 4),
                    status VARCHAR(50),
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)

            else:  # sqlite
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT,
                    category TEXT,
                    name TEXT,
                    symbol TEXT,
                    unit TEXT,
                    price REAL,
                    change_val REAL,
                    change_percent REAL,
                    weekly_percent REAL,
                    monthly_percent REAL,
                    ytd_percent REAL,
                    yoy_percent REAL,
                    market_date TEXT,
                    source_url TEXT,
                    scraped_at TEXT
                );
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraper_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT,
                    total_items INTEGER,
                    gainers_count INTEGER,
                    losers_count INTEGER,
                    avg_change_percent REAL,
                    status TEXT,
                    scraped_at TEXT
                );
                """)

            cursor.close()
            conn.close()
            return True
        except Exception as e:
            self.last_error = f"Table init error ({e})"
            if conn:
                conn.close()
            return False

    def save_scraped_data(self, items):
        """Batch inserts scraped market data snapshots into the database."""
        if not items:
            return 0

        conn, engine = self.get_connection()
        if not conn:
            return 0

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inserted = 0

        try:
            cursor = conn.cursor()
            for item in items:
                name = item.get("name") or item.get("symbol") or ""
                if not name:
                    continue

                val_type = item.get("type", "stock")
                cat = item.get("category", "General")
                unit = item.get("unit", "")
                price = item.get("price")
                chg = item.get("change")
                chg_pct = item.get("change_percent")
                weekly = item.get("weekly_percent")
                monthly = item.get("monthly_percent")
                ytd = item.get("ytd_percent")
                yoy = item.get("yoy_percent")
                dt = item.get("date", "")
                url = item.get("url", "")

                if engine == "mysql":
                    cursor.execute("""
                        INSERT INTO scraped_market_data 
                        (item_type, category, name, symbol, unit, price, change_val, change_percent, weekly_percent, monthly_percent, ytd_percent, yoy_percent, market_date, source_url, scraped_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (val_type, cat, name, name, unit, price, chg, chg_pct, weekly, monthly, ytd, yoy, dt, url, now_str))
                elif engine == "postgres":
                    cursor.execute("""
                        INSERT INTO scraped_market_data 
                        (item_type, category, name, symbol, unit, price, change_val, change_percent, weekly_percent, monthly_percent, ytd_percent, yoy_percent, market_date, source_url, scraped_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (val_type, cat, name, name, unit, price, chg, chg_pct, weekly, monthly, ytd, yoy, dt, url, now_str))
                else:  # sqlite
                    cursor.execute("""
                        INSERT INTO scraped_market_data 
                        (item_type, category, name, symbol, unit, price, change_val, change_percent, weekly_percent, monthly_percent, ytd_percent, yoy_percent, market_date, source_url, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (val_type, cat, name, name, unit, price, chg, chg_pct, weekly, monthly, ytd, yoy, dt, url, now_str))

                inserted += 1

            if engine == "sqlite":
                conn.commit()

            cursor.close()
            conn.close()
            return inserted
        except Exception as e:
            print(f"[DBManager Error] save_scraped_data failed: {e}")
            if conn:
                conn.close()
            return inserted

    def log_scrape_run(self, summary, target="all"):
        """Logs scraper execution summary stats into database."""
        conn, engine = self.get_connection()
        if not conn:
            return False

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = summary.get("total_items", 0)
        gainers = summary.get("gainers_count", 0)
        losers = summary.get("losers_count", 0)
        avg_chg = summary.get("avg_change_percent", 0)

        try:
            cursor = conn.cursor()
            if engine in ["mysql", "postgres"]:
                cursor.execute("""
                    INSERT INTO scraper_logs (target, total_items, gainers_count, losers_count, avg_change_percent, status, scraped_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (target, total, gainers, losers, avg_chg, "SUCCESS", now_str))
            else:
                cursor.execute("""
                    INSERT INTO scraper_logs (target, total_items, gainers_count, losers_count, avg_change_percent, status, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (target, total, gainers, losers, avg_chg, "SUCCESS", now_str))
                conn.commit()

            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[DBManager Error] log_scrape_run failed: {e}")
            if conn:
                conn.close()
            return False

    def get_symbol_history(self, symbol, limit=50):
        """Queries historical price time-series data for a given symbol."""
        conn, engine = self.get_connection()
        if not conn:
            return []

        clean_sym = str(symbol).strip().lower()
        results = []

        try:
            cursor = conn.cursor()
            if engine in ["mysql", "postgres"]:
                cursor.execute("""
                    SELECT price, change_val, change_percent, scraped_at, market_date
                    FROM scraped_market_data
                    WHERE LOWER(name) LIKE %s OR LOWER(symbol) LIKE %s
                    ORDER BY scraped_at DESC
                    LIMIT %s
                """, (f"%{clean_sym}%", f"%{clean_sym}%", limit))
                rows = cursor.fetchall()
            else:
                cursor.execute("""
                    SELECT price, change_val, change_percent, scraped_at, market_date
                    FROM scraped_market_data
                    WHERE LOWER(name) LIKE ? OR LOWER(symbol) LIKE ?
                    ORDER BY scraped_at DESC
                    LIMIT ?
                """, (f"%{clean_sym}%", f"%{clean_sym}%", limit))
                rows = cursor.fetchall()

            for r in rows:
                if isinstance(r, dict):
                    results.append({
                        "price": float(r["price"]) if r.get("price") is not None else None,
                        "change": float(r["change_val"]) if r.get("change_val") is not None else 0,
                        "change_percent": float(r["change_percent"]) if r.get("change_percent") is not None else 0,
                        "scraped_at": str(r["scraped_at"]),
                        "market_date": str(r.get("market_date") or ""),
                    })
                else:  # tuple / sqlite Row
                    results.append({
                        "price": float(r[0]) if r[0] is not None else None,
                        "change": float(r[1]) if r[1] is not None else 0,
                        "change_percent": float(r[2]) if r[2] is not None else 0,
                        "scraped_at": str(r[3]),
                        "market_date": str(r[4] or ""),
                    })

            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"[DBManager Error] get_symbol_history failed: {e}")
            if conn:
                conn.close()
            return []

    def get_db_stats(self):
        """Returns database connectivity health, total records, and active engine."""
        conn, engine = self.get_connection()
        if not conn:
            return {
                "connected": False,
                "engine": self.active_engine,
                "db_name": self.db_name,
                "total_records": 0,
                "total_logs": 0,
                "error": self.last_error or "Unable to connect to database",
            }

        total_records = 0
        total_logs = 0

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scraped_market_data")
            row1 = cursor.fetchone()
            total_records = row1[0] if isinstance(row1, (tuple, list)) else (row1.get("COUNT(*)") or list(row1.values())[0])

            cursor.execute("SELECT COUNT(*) FROM scraper_logs")
            row2 = cursor.fetchone()
            total_logs = row2[0] if isinstance(row2, (tuple, list)) else (row2.get("COUNT(*)") or list(row2.values())[0])

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[DBManager Error] get_db_stats count failed: {e}")
            if conn:
                conn.close()

        return {
            "connected": True,
            "engine": self.active_engine,
            "host": self.host,
            "port": self.port,
            "db_name": self.db_name,
            "total_records": total_records,
            "total_logs": total_logs,
        }
