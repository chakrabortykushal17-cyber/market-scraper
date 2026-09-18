"""
Command Line Interface (CLI) for TradingEconomics Scraper.
Provides rich terminal output, filtering, exporting (CSV, JSON, Excel, SQLite, HTML),
watching daemon mode, and web dashboard server initiation.
"""

import argparse
import sys
import os
import time
from datetime import datetime
from scraper import (
    TradingEconomicsScraper,
    export_to_csv,
    export_to_json,
    export_to_excel,
    export_to_sqlite,
    get_market_summary,
)

# Terminal colors using ANSI escapes
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_YELLOW = "\033[93m"
COLOR_GRAY = "\033[90m"


# Force UTF-8 output on Windows standard console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def print_banner():
    banner = f"""
{COLOR_CYAN}{COLOR_BOLD}===============================================================
  [+] TRADINGECONOMICS STOCKS & COMMODITIES SCRAPER
==============================================================={COLOR_RESET}
"""
    print(banner)


def format_change(val):
    if val is None:
        return f"{COLOR_GRAY}N/A{COLOR_RESET}"
    if val > 0:
        return f"{COLOR_GREEN}+{val:.2f}%{COLOR_RESET}"
    elif val < 0:
        return f"{COLOR_RED}{val:.2f}%{COLOR_RESET}"
    return f"{COLOR_GRAY}0.00%{COLOR_RESET}"


def print_table(data, title="Market Data"):
    print(f"\n{COLOR_BOLD}{COLOR_YELLOW}--- {title} (Total: {len(data)}) ---{COLOR_RESET}")
    header_fmt = f"{COLOR_BOLD}{'Type':<11} | {'Category':<14} | {'Name / Symbol':<22} | {'Price':<12} | {'Change':<10} | {'% Change':<10} | {'YTD %':<10} | {'Date':<8}{COLOR_RESET}"
    divider = "-" * 110
    print(header_fmt)
    print(divider)

    for item in data:
        t_type = item.get("type", "").capitalize()
        cat = item.get("category", "")[:14]
        name = item.get("name", "")[:22]
        price = f"{item['price']:.2f}" if isinstance(item.get("price"), (int, float)) else "N/A"
        chg = f"{item['change']:+.2f}" if isinstance(item.get("change"), (int, float)) else "N/A"
        chg_pct = format_change(item.get("change_percent"))
        ytd_pct = format_change(item.get("ytd_percent"))
        date = item.get("date", "")

        row_str = f"{t_type:<11} | {cat:<14} | {name:<22} | {price:<12} | {chg:<10} | {chg_pct:<19} | {ytd_pct:<19} | {date:<8}"
        print(row_str)
    print(divider)


def run_cli():
    parser = argparse.ArgumentParser(
        description="Scrape stock indices and commodities directly from TradingEconomics.com"
    )

    parser.add_argument(
        "-t",
        "--target",
        choices=["stocks", "commodities", "crypto", "all"],
        default="all",
        help="Target to scrape (stocks, commodities, crypto, or all)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["terminal", "csv", "json", "excel", "sqlite", "html"],
        default="terminal",
        help="Export or output format",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file path (default: exports/<target>_<timestamp>.<ext>)",
    )
    parser.add_argument(
        "-c",
        "--category",
        type=str,
        help="Filter by category (e.g. Major, Europe, Energy, Metals, Crypto)",
    )
    parser.add_argument(
        "-s",
        "--search",
        type=str,
        help="Search filter by stock/commodity/crypto name",
    )
    parser.add_argument(
        "--gainers",
        action="store_true",
        help="Filter top gainers only (positive percentage change)",
    )
    parser.add_argument(
        "--losers",
        action="store_true",
        help="Filter top losers only (negative percentage change)",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        help="Limit number of items displayed",
    )
    parser.add_argument(
        "-w",
        "--watch",
        type=int,
        nargs="?",
        const=5,
        default=None,
        metavar="SECONDS",
        help="Run continuously in watch mode every N seconds (default: 5s)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start Web Dashboard server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Web server port (default: 5000)",
    )

    args = parser.parse_args()

    if args.web:
        print_banner()
        print(f"{COLOR_CYAN}Launching Web Server on http://localhost:{args.port}...{COLOR_RESET}")
        from app import app
        app.run(host="0.0.0.0", port=args.port, debug=False)
        return

    print_banner()
    scraper = TradingEconomicsScraper()

    os.makedirs("exports", exist_ok=True)

    def execute_scrape():
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"{COLOR_GRAY}[{datetime.now().strftime('%H:%M:%S')}] Scraping {args.target}...{COLOR_RESET}")

        if args.target == "stocks":
            data = scraper.scrape_stocks()
        elif args.target == "commodities":
            data = scraper.scrape_commodities()
        elif args.target == "crypto":
            data = scraper.scrape_crypto()
        else:
            data = scraper.scrape_all()

        # Apply filters
        if args.category:
            cat_query = args.category.lower()
            data = [d for d in data if cat_query in d.get("category", "").lower()]

        if args.search:
            s_query = args.search.lower()
            data = [d for d in data if s_query in d.get("name", "").lower() or s_query in d.get("symbol", "").lower()]

        if args.gainers:
            data = [d for d in data if d.get("change_percent") is not None and d.get("change_percent") > 0]
            data.sort(key=lambda x: x.get("change_percent", 0), reverse=True)

        if args.losers:
            data = [d for d in data if d.get("change_percent") is not None and d.get("change_percent") < 0]
            data.sort(key=lambda x: x.get("change_percent", 0))

        if args.limit and args.limit > 0:
            data = data[: args.limit]

        # Display summary
        summary = get_market_summary(data)
        print(f"{COLOR_GREEN}Successfully scraped {len(data)} items.{COLOR_RESET}")
        if summary.get("top_gainer"):
            g = summary["top_gainer"]
            print(f"  {COLOR_BOLD}Top Gainer:{COLOR_RESET} {g['name']} ({g['category']}) {format_change(g['change_percent'])}")
        if summary.get("top_loser"):
            l = summary["top_loser"]
            print(f"  {COLOR_BOLD}Top Loser:{COLOR_RESET}  {l['name']} ({l['category']}) {format_change(l['change_percent'])}")

        # Format / Export
        if args.format == "terminal":
            print_table(data, title=f"TradingEconomics {args.target.capitalize()}")

        else:
            ext_map = {
                "csv": "csv",
                "json": "json",
                "excel": "xlsx",
                "sqlite": "db",
                "html": "html",
            }
            ext = ext_map[args.format]
            filepath = args.output or os.path.join("exports", f"{args.target}_{timestamp_str}.{ext}")

            if args.format == "csv":
                export_to_csv(data, filepath)
            elif args.format == "json":
                export_to_json(data, filepath)
            elif args.format == "excel":
                export_to_excel(data, filepath)
            elif args.format == "sqlite":
                export_to_sqlite(data, filepath)
            elif args.format == "html":
                # Export clean HTML report
                df = pd.DataFrame(data)
                html_content = f"""<!DOCTYPE html>
<html>
<head>
<title>TradingEconomics Scraped Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; }}
h1 {{ color: #38bdf8; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 20px; background: #1e293b; border-radius: 8px; overflow: hidden; }}
th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; }}
th {{ background-color: #334155; color: #94a3b8; font-weight: 600; }}
tr:hover {{ background-color: #475569; }}
.positive {{ color: #4ade80; font-weight: bold; }}
.negative {{ color: #f87171; font-weight: bold; }}
</style>
</head>
<body>
<h1>TradingEconomics Market Report</h1>
<p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total items: {len(data)}</p>
{df.to_html(classes="market-table", index=False)}
</body>
</html>"""
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)

            print(f"{COLOR_GREEN}[+] Exported {len(data)} items to: {os.path.abspath(filepath)}{COLOR_RESET}")

    if args.watch and args.watch > 0:
        print(f"{COLOR_CYAN}Starting Watch Mode (Interval: {args.watch} seconds)... Press Ctrl+C to stop.{COLOR_RESET}")
        try:
            while True:
                execute_scrape()
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print(f"\n{COLOR_YELLOW}Watch mode stopped by user.{COLOR_RESET}")
    else:
        execute_scrape()


if __name__ == "__main__":
    run_cli()
