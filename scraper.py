"""
TradingEconomics Stock & Commodity Scraper Core Module
Directly scrapes live stock index and commodity market data from:
- https://tradingeconomics.com/stocks
- https://tradingeconomics.com/commodities
"""

import time
import json
import sqlite3
import re
from datetime import datetime
import urllib.request
import urllib.error
from bs4 import BeautifulSoup
try:
    import pandas as pd
except ImportError:
    pd = None

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

STOCKS_URL = "https://tradingeconomics.com/stocks"
COMMODITIES_URL = "https://tradingeconomics.com/commodities"
CRYPTO_URL = "https://tradingeconomics.com/crypto"


class TradingEconomicsScraper:
    def __init__(self, user_agent=None, timeout=15, retries=3):
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.timeout = timeout
        self.retries = retries
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://tradingeconomics.com/",
        }

    def _fetch_html(self, url):
        """Fetches raw HTML string from target URL with robust timeout and SSL context."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                if response.status == 200:
                    return response.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return None

    def _scrape_stocks_fallback(self):
        """Live market feed fallback for stock indices via Yahoo Finance v8 chart API."""
        yf_stocks = {
            'SENSEX': ('^BSESN', 'Asia-Pacific', 'Index Points'),
            'NIFTY 50': ('^NSEI', 'Asia-Pacific', 'Index Points'),
            'NIFTY BANK': ('^NSEBANK', 'Asia-Pacific', 'Index Points'),
            'NIKKEI 225': ('^N225', 'Asia-Pacific', 'Index Points'),
            'JP225': ('^N225', 'Major', 'Index Points'),
            'TOPIX': ('0000.T', 'Asia-Pacific', 'Index Points'),
            'SHANGHAI': ('000001.SS', 'Asia-Pacific', 'Index Points'),
            'SHENZHEN': ('399001.SZ', 'Asia-Pacific', 'Index Points'),
            'HANG SENG': ('^HSI', 'Asia-Pacific', 'Index Points'),
            'HK50': ('^HSI', 'Major', 'Index Points'),
            'KOSPI': ('^KS11', 'Asia-Pacific', 'Index Points'),
            'ASX 200': ('^AXJO', 'Asia-Pacific', 'Index Points'),
            'TAIEX': ('^TWII', 'Asia-Pacific', 'Index Points'),
            'STI': ('^STI', 'Asia-Pacific', 'Index Points'),
            'KLCI': ('^KLSE', 'Asia-Pacific', 'Index Points'),
            'PSEi': ('^PSI', 'Asia-Pacific', 'Index Points'),
            'JCI': ('^JKSE', 'Asia-Pacific', 'Index Points'),
            'SET 50': ('^SET.BK', 'Asia-Pacific', 'Index Points'),
            'VN': ('^VNINDEX', 'Asia-Pacific', 'Index Points'),
            'NZX 50': ('^NZ50', 'Asia-Pacific', 'Index Points'),
            'US500': ('^GSPC', 'Major', 'Index Points'),
            'S&P 500': ('^GSPC', 'America', 'Index Points'),
            'US100': ('^IXIC', 'Major', 'Index Points'),
            'NASDAQ': ('^IXIC', 'America', 'Index Points'),
            'US30': ('^DJI', 'Major', 'Index Points'),
            'DOW JONES': ('^DJI', 'America', 'Index Points'),
            'US1000': ('^RUT', 'America', 'Index Points'),
            'TSX': ('^GSPTSE', 'Major', 'Index Points'),
            'IBOVESPA': ('^BVSP', 'America', 'Index Points'),
            'IPC': ('^MXX', 'America', 'Index Points'),
            'MERVAL': ('^MERV', 'America', 'Index Points'),
            'IPSA': ('^IPSA', 'America', 'Index Points'),
            'COLCAP': ('^COLCAP', 'America', 'Index Points'),
            'DE40': ('^GDAXI', 'Major', 'Index Points'),
            'DAX': ('^GDAXI', 'Europe', 'Index Points'),
            'GB100': ('^FTSE', 'Major', 'Index Points'),
            'FTSE 100': ('^FTSE', 'Europe', 'Index Points'),
            'FR40': ('^FCHI', 'Major', 'Index Points'),
            'CAC 40': ('^FCHI', 'Europe', 'Index Points'),
            'EU50': ('^STOXX50E', 'Europe', 'Index Points'),
            'IT40': ('FTSEMIB.MI', 'Europe', 'Index Points'),
            'ES35': ('^IBEX', 'Europe', 'Index Points'),
            'CH20': ('^SSMI', 'Europe', 'Index Points'),
            'AEX': ('^AEX', 'Europe', 'Index Points'),
            'BEL20': ('^BFX', 'Europe', 'Index Points'),
            'OMX30': ('^OMX', 'Europe', 'Index Points'),
            'OMXC20': ('^OMXC20', 'Europe', 'Index Points'),
            'HEX25': ('^HEX25', 'Europe', 'Index Points'),
            'WIG20': ('^WIG20', 'Europe', 'Index Points'),
            'ATX': ('^ATX', 'Europe', 'Index Points'),
            'MOEX': ('IMOEX.ME', 'Europe', 'Index Points'),
            'TASI': ('^TASI.SR', 'Middle East', 'Index Points'),
            'DFMGI': ('DFMGI.AE', 'Middle East', 'Index Points'),
            'ADX': ('^ADI', 'Middle East', 'Index Points'),
            'QE': ('^QSI', 'Middle East', 'Index Points'),
            'EGX30': ('^EGX30', 'Middle East', 'Index Points'),
            'JSE': ('^J203.JO', 'Africa', 'Index Points'),
            'TA35': ('TA35.TA', 'Middle East', 'Index Points'),
            'BIST100': ('XU100.IS', 'Europe', 'Index Points')
        }

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        items = []
        now_str = datetime.now().strftime('%b/%d')

        for name, (sym, cat, unit) in yf_stocks.items():
            try:
                url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d'
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    meta = data['chart']['result'][0]['meta']
                    p = meta.get('regularMarketPrice')
                    prev = meta.get('previousClose') or meta.get('chartPreviousClose') or p
                    if p is not None:
                        chg = round(p - prev, 4) if prev else 0.0
                        chg_pct = round((chg / prev) * 100, 4) if prev else 0.0
                        items.append({
                            'type': 'stock',
                            'category': cat,
                            'name': name,
                            'symbol': name,
                            'unit': unit,
                            'price': p,
                            'change': chg,
                            'change_percent': chg_pct,
                            'date': now_str,
                            'url': f'https://finance.yahoo.com/quote/{sym}',
                            'scraped_at': datetime.now().isoformat()
                        })
            except Exception:
                pass
        return items

    @staticmethod
    def _clean_number(val_or_td):
        """
        Converts a string or BeautifulSoup <td> element to float or None.
        Accurately captures negative values from HTML data-value attributes.
        """
        if val_or_td is None:
            return None

        if hasattr(val_or_td, "get") or hasattr(val_or_td, "find"):
            td = val_or_td
            data_val = td.get("data-value")
            if data_val is not None and str(data_val).strip() != "":
                try:
                    return float(str(data_val).replace(",", "").strip())
                except ValueError:
                    pass

            val_str = td.text.strip()
            if not val_str or val_str in ["-", "--", "N/A", "null", "None"]:
                return None

            cleaned = val_str.replace(",", "").replace("%", "").strip()
            try:
                val = float(cleaned)
                is_negative_img = td.find(class_=re.compile(r"negative", re.I)) is not None
                is_negative_class = "negative" in " ".join(td.get("class", [])).lower()
                if (is_negative_img or is_negative_class) and val > 0:
                    val = -val
                return val
            except ValueError:
                return val_str

        val_str = str(val_or_td).strip()
        if not val_str or val_str in ["-", "--", "N/A", "null", "None"]:
            return None
        cleaned = val_str.replace(",", "").replace("%", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return val_str

    def scrape_stocks(self):
        """
        Scrapes all global stock index tables from TradingEconomics with live feed fallback.
        Returns a list of dictionaries representing each stock index.
        """
        html = self._fetch_html(STOCKS_URL)
        if not html:
            return self._scrape_stocks_fallback()

        soup = BeautifulSoup(html, "html.parser")
        items = []

        tables = soup.find_all("table")
        for table in tables:
            headers = [th.text.strip() for th in table.find_all("th")]
            if not headers:
                continue

            category = "General"
            for h in headers:
                if h and h not in ["Price", "Chg", "%Chg", "Weekly", "Monthly", "YTD", "YoY", "Date"]:
                    category = h
                    break

            rows = table.find_all("tr")
            for tr in rows:
                tds = tr.find_all("td")
                if not tds:
                    continue

                link_el = tr.find("a", href=True)
                url_path = link_el["href"] if link_el else ""
                full_url = (
                    f"https://tradingeconomics.com{url_path}"
                    if url_path.startswith("/")
                    else url_path
                )

                cells = [td.text.strip() for td in tds]
                name_idx = 1 if len(cells) > 1 and cells[0] == "" else 0
                symbol_name = cells[name_idx] if len(cells) > name_idx else ""

                if not symbol_name:
                    continue

                price = self._clean_number(tds[name_idx + 1]) if len(tds) > name_idx + 1 else None
                chg = self._clean_number(tds[name_idx + 2]) if len(tds) > name_idx + 2 else None
                chg_pct = self._clean_number(tds[name_idx + 3]) if len(tds) > name_idx + 3 else None
                weekly = self._clean_number(tds[name_idx + 4]) if len(tds) > name_idx + 4 else None
                monthly = self._clean_number(tds[name_idx + 5]) if len(tds) > name_idx + 5 else None
                ytd = self._clean_number(tds[name_idx + 6]) if len(tds) > name_idx + 6 else None
                yoy = self._clean_number(tds[name_idx + 7]) if len(tds) > name_idx + 7 else None
                date = cells[name_idx + 8] if len(cells) > name_idx + 8 else ""

                items.append({
                    "type": "stock",
                    "category": category,
                    "name": symbol_name,
                    "symbol": symbol_name,
                    "unit": "Index Points",
                    "price": price,
                    "change": chg,
                    "change_percent": chg_pct,
                    "weekly_percent": weekly,
                    "monthly_percent": monthly,
                    "ytd_percent": ytd,
                    "yoy_percent": yoy,
                    "date": date,
                    "url": full_url,
                    "scraped_at": datetime.now().isoformat()
                })

        # Supplement major benchmark indices not listed in TradingEconomics stocks table
        if items:
            existing_names = {x['name'].upper() for x in items}
            supplements = {
                'KOSPI': ('^KS11', 'Asia-Pacific', 'Index Points'),
                'NIFTY BANK': ('^NSEBANK', 'Asia-Pacific', 'Index Points'),
                'SHENZHEN': ('399001.SZ', 'Asia-Pacific', 'Index Points'),
                'TOPIX': ('TPY=F', 'Asia-Pacific', 'Index Points'),
            }
            from concurrent.futures import ThreadPoolExecutor
            def fetch_supplement(entry):
                name, (sym, cat, unit) = entry
                if name in existing_names:
                    return None
                try:
                    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d'
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        meta = data['chart']['result'][0]['meta']
                        p = meta.get('regularMarketPrice')
                        prev = meta.get('previousClose') or meta.get('chartPreviousClose') or p
                        if p is not None:
                            chg = round(p - prev, 2) if prev else 0.0
                            pct = round((chg / prev) * 100, 2) if prev else 0.0
                            return {
                                'type': 'stock',
                                'category': cat,
                                'name': name,
                                'symbol': name,
                                'unit': unit,
                                'price': p,
                                'change': chg,
                                'change_percent': pct,
                                'weekly_percent': 0.0,
                                'monthly_percent': 0.0,
                                'ytd_percent': 0.0,
                                'yoy_percent': 0.0,
                                'date': datetime.now().strftime('%b/%d'),
                                'url': f'https://finance.yahoo.com/quote/{sym}',
                                'scraped_at': datetime.now().isoformat()
                            }
                except Exception:
                    pass
                return None

            try:
                with ThreadPoolExecutor(max_workers=3) as pool:
                    for res in pool.map(fetch_supplement, supplements.items()):
                        if res:
                            items.append(res)
            except Exception:
                pass

        return items if items else self._scrape_stocks_fallback()

    def _scrape_commodities_fallback(self):
        """Live market feed fallback for commodities via Yahoo Finance v8 API."""
        yf_comms = {
            'Gold': ('GC=F', 'Metals', 'USD/t.oz'),
            'Silver': ('SI=F', 'Metals', 'USD/t.oz'),
            'Platinum': ('PL=F', 'Metals', 'USD/t.oz'),
            'Palladium': ('PA=F', 'Metals', 'USD/t.oz'),
            'Crude Oil': ('CL=F', 'Energy', 'USD/Bbl'),
            'Brent': ('BZ=F', 'Energy', 'USD/Bbl'),
            'Natural Gas': ('NG=F', 'Energy', 'USD/MMBtu'),
            'Heating Oil': ('HO=F', 'Energy', 'USD/Gal'),
            'Gasoline': ('RB=F', 'Energy', 'USD/Gal'),
            'Copper': ('HG=F', 'Industrial Metals', 'USD/Lbs'),
            'Aluminum': ('ALI=F', 'Industrial Metals', 'USD/T'),
            'Wheat': ('ZW=F', 'Agricultural', 'USd/Bu'),
            'Corn': ('ZC=F', 'Agricultural', 'USd/Bu'),
            'Soybeans': ('ZS=F', 'Agricultural', 'USd/Bu'),
            'Coffee': ('KC=F', 'Agricultural', 'USd/Lbs'),
            'Cocoa': ('CC=F', 'Agricultural', 'USD/T'),
            'Sugar': ('SB=F', 'Agricultural', 'USd/Lbs'),
            'Cotton': ('CT=F', 'Agricultural', 'USd/Lbs')
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        c_items = []
        now_str = datetime.now().strftime('%b/%d')

        for name, (sym, cat, unit) in yf_comms.items():
            try:
                url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d'
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    meta = data['chart']['result'][0]['meta']
                    p = meta.get('regularMarketPrice')
                    prev = meta.get('previousClose') or meta.get('chartPreviousClose') or p
                    if p is not None:
                        chg = round(p - prev, 4) if prev else 0.0
                        chg_pct = round((chg / prev) * 100, 4) if prev else 0.0
                        c_items.append({
                            'type': 'commodity',
                            'category': cat,
                            'name': name,
                            'symbol': name,
                            'unit': unit,
                            'price': p,
                            'change': chg,
                            'change_percent': chg_pct,
                            'date': now_str,
                            'url': f'https://finance.yahoo.com/quote/{sym}',
                            'scraped_at': datetime.now().isoformat()
                        })
            except Exception:
                pass
        return c_items

    def _scrape_crypto_fallback(self):
        """Live market feed fallback for crypto via Binance API."""
        binance_crypto = [
            ('Bitcoin', 'BTCUSDT'), ('Ethereum', 'ETHUSDT'), ('Binance Coin', 'BNBUSDT'),
            ('Solana', 'SOLUSDT'), ('Cardano', 'ADAUSDT'), ('XRP', 'XRPUSDT'),
            ('Dogecoin', 'DOGEUSDT'), ('Polkadot', 'DOTUSDT'), ('Avalanche', 'AVAXUSDT'),
            ('Chainlink', 'LINKUSDT'), ('Litecoin', 'LTCUSDT'), ('Stellar', 'XLMUSDT'),
            ('TRON', 'TRXUSDT'), ('Shiba Inu', 'SHIBUSDT'), ('Uniswap', 'UNIUSDT')
        ]
        headers = {'User-Agent': 'Mozilla/5.0'}
        crypto_items = []
        now_str = datetime.now().strftime('%b/%d')

        try:
            req = urllib.request.Request('https://api.binance.com/api/v3/ticker/24hr', headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                by_sym = {item['symbol']: item for item in data}
                for name, pair in binance_crypto:
                    if pair in by_sym:
                        c = by_sym[pair]
                        price = float(c['lastPrice'])
                        chg = float(c['priceChange'])
                        pct = float(c['priceChangePercent'])
                        crypto_items.append({
                            'type': 'crypto',
                            'category': 'Crypto',
                            'name': name,
                            'symbol': name,
                            'unit': 'USD',
                            'price': price,
                            'change': chg,
                            'change_percent': pct,
                            'date': now_str,
                            'url': f'https://binance.com/en/trade/{pair}',
                            'scraped_at': datetime.now().isoformat()
                        })
        except Exception:
            pass
        return crypto_items

    def scrape_commodities(self):
        """
        Scrapes all commodity market tables from TradingEconomics with live feed fallback.
        Returns a list of dictionaries representing each commodity.
        """
        html = self._fetch_html(COMMODITIES_URL)
        if not html:
            return self._scrape_commodities_fallback()

        soup = BeautifulSoup(html, "html.parser")
        items = []

        tables = soup.find_all("table")
        for table in tables:
            headers = [th.text.strip() for th in table.find_all("th")]
            if not headers:
                continue

            category = headers[0] if headers[0] else "Commodities"

            rows = table.find_all("tr")
            for tr in rows:
                tds = tr.find_all("td")
                if not tds:
                    continue

                link_el = tr.find("a", href=True)
                url_path = link_el["href"] if link_el else ""
                full_url = (
                    f"https://tradingeconomics.com{url_path}"
                    if url_path.startswith("/")
                    else url_path
                )

                cells = [td.text.strip() for td in tds]
                raw_name = cells[0] if cells else ""
                name_parts = [p.strip() for p in raw_name.split("\n") if p.strip()]
                name = name_parts[0] if name_parts else ""
                unit = name_parts[1] if len(name_parts) > 1 else ""

                if not name:
                    continue

                price = self._clean_number(tds[1]) if len(tds) > 1 else None
                chg = self._clean_number(tds[2]) if len(tds) > 2 else None
                chg_pct = self._clean_number(tds[3]) if len(tds) > 3 else None
                weekly = self._clean_number(tds[4]) if len(tds) > 4 else None
                monthly = self._clean_number(tds[5]) if len(tds) > 5 else None
                ytd = self._clean_number(tds[6]) if len(tds) > 6 else None
                yoy = self._clean_number(tds[7]) if len(tds) > 7 else None
                date = cells[8] if len(cells) > 8 else ""

                items.append({
                    "type": "commodity",
                    "category": category,
                    "name": name,
                    "symbol": name,
                    "unit": unit,
                    "price": price,
                    "change": chg,
                    "change_percent": chg_pct,
                    "weekly_percent": weekly,
                    "monthly_percent": monthly,
                    "ytd_percent": ytd,
                    "yoy_percent": yoy,
                    "date": date,
                    "url": full_url,
                    "scraped_at": datetime.now().isoformat()
                })

        return items if items else self._scrape_commodities_fallback()

    def scrape_crypto(self):
        """
        Scrapes cryptocurrency tables directly from TradingEconomics with live feed fallback.
        Returns a list of dictionaries representing each cryptocurrency.
        """
        html = self._fetch_html(CRYPTO_URL)
        if not html:
            return self._scrape_crypto_fallback()

        soup = BeautifulSoup(html, "html.parser")
        items = []

        tables = soup.find_all("table")
        for table in tables:
            headers = [th.text.strip() for th in table.find_all("th")]
            if not headers:
                continue

            category = "Crypto"
            for h in headers:
                if h and h not in ["Price", "Chg", "%Chg", "Weekly", "Monthly", "YTD", "YoY", "MarketCap", "Date"]:
                    category = h
                    break

            rows = table.find_all("tr")
            for tr in rows:
                tds = tr.find_all("td")
                if not tds:
                    continue

                link_el = tr.find("a", href=True)
                url_path = link_el["href"] if link_el else ""
                full_url = (
                    f"https://tradingeconomics.com{url_path}"
                    if url_path.startswith("/")
                    else url_path
                )

                cells = [td.text.strip() for td in tds]
                name_idx = 1 if len(cells) > 1 and cells[0] == "" else 0
                name = cells[name_idx] if len(cells) > name_idx else ""

                if not name:
                    continue

                price = self._clean_number(tds[name_idx + 1]) if len(tds) > name_idx + 1 else None
                chg = self._clean_number(tds[name_idx + 2]) if len(tds) > name_idx + 2 else None
                chg_pct = self._clean_number(tds[name_idx + 3]) if len(tds) > name_idx + 3 else None
                weekly = self._clean_number(tds[name_idx + 4]) if len(tds) > name_idx + 4 else None
                monthly = self._clean_number(tds[name_idx + 5]) if len(tds) > name_idx + 5 else None
                ytd = self._clean_number(tds[name_idx + 6]) if len(tds) > name_idx + 6 else None
                yoy = self._clean_number(tds[name_idx + 7]) if len(tds) > name_idx + 7 else None

                has_mcap = "MarketCap" in headers or len(cells) > name_idx + 9
                mcap = cells[name_idx + 8] if (has_mcap and len(cells) > name_idx + 8) else ""
                date = cells[name_idx + 9] if (has_mcap and len(cells) > name_idx + 9) else (cells[name_idx + 8] if len(cells) > name_idx + 8 else "")

                items.append({
                    "type": "crypto",
                    "category": category,
                    "name": name,
                    "symbol": name,
                    "unit": "USD",
                    "market_cap": mcap,
                    "price": price,
                    "change": chg,
                    "change_percent": chg_pct,
                    "weekly_percent": weekly,
                    "monthly_percent": monthly,
                    "ytd_percent": ytd,
                    "yoy_percent": yoy,
                    "date": date,
                    "url": full_url,
                    "scraped_at": datetime.now().isoformat()
                })

        return items if items else self._scrape_crypto_fallback()

    def scrape_all(self):
        """Scrapes Stocks, Commodities, and Crypto and returns combined list."""
        stocks = self.scrape_stocks()
        commodities = self.scrape_commodities()
        crypto = self.scrape_crypto()
        return stocks + commodities + crypto


# Helper utility functions for exporting data
def export_to_csv(data, filepath):
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    return filepath

def export_to_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath

def export_to_excel(data, filepath):
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, engine="openpyxl")
    return filepath

def export_to_sqlite(data, db_filepath, table_name="market_data"):
    df = pd.DataFrame(data)
    conn = sqlite3.connect(db_filepath)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    return db_filepath

def get_market_summary(data):
    """Generates analytical summary stats for scraped market data."""
    if not data:
        return {}

    valid_pcts = [item for item in data if item.get("change_percent") is not None]
    
    top_gainer = max(valid_pcts, key=lambda x: x["change_percent"]) if valid_pcts else None
    top_loser = min(valid_pcts, key=lambda x: x["change_percent"]) if valid_pcts else None

    gainers_count = sum(1 for item in valid_pcts if item["change_percent"] > 0)
    losers_count = sum(1 for item in valid_pcts if item["change_percent"] < 0)
    unchanged_count = len(data) - (gainers_count + losers_count)

    avg_change = (
        sum(item["change_percent"] for item in valid_pcts) / len(valid_pcts)
        if valid_pcts
        else 0
    )

    categories = list(set(item["category"] for item in data))

    return {
        "total_items": len(data),
        "gainers_count": gainers_count,
        "losers_count": losers_count,
        "unchanged_count": unchanged_count,
        "avg_change_percent": round(avg_change, 2),
        "top_gainer": top_gainer,
        "top_loser": top_loser,
        "categories": categories,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    scraper = TradingEconomicsScraper()
    print("Scraping stocks...")
    stocks = scraper.scrape_stocks()
    print(f"Scraped {len(stocks)} stocks.")

    print("Scraping commodities...")
    commodities = scraper.scrape_commodities()
    print(f"Scraped {len(commodities)} commodities.")

    print("Scraping crypto...")
    crypto = scraper.scrape_crypto()
    print(f"Scraped {len(crypto)} crypto items.")

    summary = get_market_summary(stocks + commodities + crypto)
    print("Summary:", json.dumps(summary, indent=2))

