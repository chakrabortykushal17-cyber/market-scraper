# 📈 TradingEconomics Stock, Commodity & Crypto Scraper

A high-performance Python web scraping tool and interactive web dashboard designed to scrape live financial market data directly from:
- **Stocks**: `https://tradingeconomics.com/stocks`
- **Commodities**: `https://tradingeconomics.com/commodities`
- **Crypto**: `https://tradingeconomics.com/crypto`

---

## ✨ Features

- **Direct Scraper Library (`scraper.py`)**:
  - Scrapes 130+ global stock market indices (Major, Europe, America, Asia, Oceania, Africa).
  - Scrapes 100+ commodity markets (Energy, Metals, Agricultural, Industrial, Livestock, Electricity).
  - Scrapes 75+ cryptocurrency assets (Bitcoin, Ethereum, Solana, Cardano, XRP, BNB, etc.).
  - Extracts Symbol/Name, Unit, Price, Day Change, % Change, Weekly %, Monthly %, YTD %, YoY %, Market Cap, Date, and Direct Url.
  - Automatic HTTP retry logic, custom headers, and clean floating point formatting.
  - Generates market sentiment summaries (Top Gainers, Top Losers, Bullish/Bearish ratio).

- **Powerful CLI Interface (`cli.py`)**:
  - Scrape Stocks, Commodities, Crypto, or all.
  - Filter by Category, Search Keyword, Top Gainers, or Top Losers.
  - Export data to **CSV**, **JSON**, **Excel (.xlsx)**, **SQLite Database (.db)**, or **HTML Reports**.
  - Terminal table formatting with colorized gain/loss indicators.
  - Continuous **Watch Daemon Mode** (`--watch 30`).

- **Automatic PC Startup Mode (`autostart.py`)**:
  - Automatically runs the continuous scraper (`run_scraper.py`) silently in the background when your PC boots up or user logs in.
  - Interactive toggle on Web Dashboard UI.
  - 1-click batch files (`enable_autostart.bat`, `disable_autostart.bat`) and CLI commands.

---

## ⚡ PC Auto-Start Feature (Run on Startup)

You can set the scraper to automatically launch silently whenever your PC turns on:

### Option A: Web Dashboard (1-Click)
Open the Web Dashboard at `http://localhost:5000` and click the **`⚡ PC Auto-Start: OFF`** button in the top navigation bar to turn it ON or OFF.

### Option B: Batch Files
Double-click `enable_autostart.bat` to enable PC auto-start, or `disable_autostart.bat` to disable it.

### Option C: Terminal CLI
```bash
# Enable PC Auto-Start (runs silently in background on boot)
python autostart.py --enable

# Disable PC Auto-Start
python autostart.py --disable

# Check current status
python autostart.py --status
```

---

## 🚀 Quick Start


### 1. Requirements & Installation

Python 3.8+ is required. Install dependencies via:

```bash
pip install -r requirements.txt
```

---

## 💻 Command Line Interface (CLI) Usage

Run `cli.py` directly from your terminal:

### Basic Commands:
```bash
# Scrape all stocks and commodities and display in terminal
python cli.py

# Scrape only commodities
python cli.py -t commodities

# Scrape only stocks and limit display to 10 items
python cli.py -t stocks -n 10
```

### Filtering Data:
```bash
# Filter by category (e.g. Energy, Metals, Europe, Major)
python cli.py -c Energy

# Search for specific market symbol or commodity
python cli.py -s Gold

# Show top gainers only
python cli.py --gainers

# Show top losers only
python cli.py --losers
```

### Exporting Data:
```bash
# Export all market data to CSV
python cli.py -f csv -o exports/market_data.csv

# Export commodities to JSON
python cli.py -t commodities -f json -o exports/commodities.json

# Export to Excel spreadsheet (.xlsx)
python cli.py -f excel -o exports/market_report.xlsx

# Export to SQLite database table
python cli.py -f sqlite -o exports/market_database.db

# Export to standalone HTML report
python cli.py -f html -o exports/report.html
```

### Continuous Watch Mode:
```bash
# Scrape and print updated market data every 30 seconds
python cli.py -w 30
```

---

## 🌐 Web Dashboard UI

Launch the interactive web dashboard server:

```bash
python app.py
# OR
python cli.py --web
```

Then open your browser and navigate to:
👉 **`http://localhost:5000`**

---

## 🐍 Using as a Python Library

You can import `scraper.py` into your own Python projects:

```python
from scraper import TradingEconomicsScraper, get_market_summary

scraper = TradingEconomicsScraper()

# Scrape stock index markets
stocks = scraper.scrape_stocks()
print(f"Scraped {len(stocks)} stock indices")

# Scrape commodity markets
commodities = scraper.scrape_commodities()
print(f"Scraped {len(commodities)} commodities")

# Get analytics summary
summary = get_market_summary(stocks + commodities)
print("Top Gainer:", summary['top_gainer']['name'], summary['top_gainer']['change_percent'])
```

---

## 📁 Project Structure

```
stock scrapper/
├── scraper.py         # Core scraping engine & export functions
├── cli.py             # Feature-rich Command Line Interface
├── app.py             # Flask Web Server & API backend
├── static/            # Web Dashboard Frontend
│   ├── index.html     # Glassmorphic UI Dashboard HTML
│   ├── css/style.css  # Modern CSS styling system
│   └── js/app.js      # Interactive JavaScript & Chart.js logic
├── exports/           # Output directory for exported files
├── requirements.txt   # Python package dependencies
└── README.md          # Documentation & user guide
```

---

## 📜 License
MIT License - Free for personal & commercial use.
