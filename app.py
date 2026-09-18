"""
Flask Backend Application for TradingEconomics Web Dashboard & REST API.
Includes MySQL, PostgreSQL, and SQLite Database persistence & history endpoints.
"""

import os
import time
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from scraper import (
    TradingEconomicsScraper,
    export_to_csv,
    export_to_json,
    export_to_excel,
    get_market_summary,
)
from db_helper import DatabaseManager
from autostart import is_autostart_enabled, enable_autostart, disable_autostart, get_status_summary


app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

scraper = TradingEconomicsScraper()
db = DatabaseManager()

# Cache TTL set to 15 seconds for auto-updating
CACHE_TTL_SECONDS = 15
cache = {
    "stocks": {"data": None, "timestamp": 0},
    "commodities": {"data": None, "timestamp": 0},
    "crypto": {"data": None, "timestamp": 0},
}


def get_cached_data(target="all", force_refresh=False):
    now = time.time()
    result = []
    newly_scraped = []

    if target in ["stocks", "all"]:
        if (
            force_refresh
            or cache["stocks"]["data"] is None
            or (now - cache["stocks"]["timestamp"]) > CACHE_TTL_SECONDS
        ):
            try:
                scraped = scraper.scrape_stocks()
                cache["stocks"]["data"] = scraped
                cache["stocks"]["timestamp"] = now
                newly_scraped.extend(scraped)
            except Exception as e:
                print(f"Error scraping stocks: {e}")
                if cache["stocks"]["data"] is None:
                    cache["stocks"]["data"] = []
        result.extend(cache["stocks"]["data"])

    if target in ["commodities", "all"]:
        if (
            force_refresh
            or cache["commodities"]["data"] is None
            or (now - cache["commodities"]["timestamp"]) > CACHE_TTL_SECONDS
        ):
            try:
                scraped = scraper.scrape_commodities()
                cache["commodities"]["data"] = scraped
                cache["commodities"]["timestamp"] = now
                newly_scraped.extend(scraped)
            except Exception as e:
                print(f"Error scraping commodities: {e}")
                if cache["commodities"]["data"] is None:
                    cache["commodities"]["data"] = []
        result.extend(cache["commodities"]["data"])

    if target in ["crypto", "all"]:
        if (
            force_refresh
            or cache["crypto"]["data"] is None
            or (now - cache["crypto"]["timestamp"]) > CACHE_TTL_SECONDS
        ):
            try:
                scraped = scraper.scrape_crypto()
                cache["crypto"]["data"] = scraped
                cache["crypto"]["timestamp"] = now
                newly_scraped.extend(scraped)
            except Exception as e:
                print(f"Error scraping crypto: {e}")
                if cache["crypto"]["data"] is None:
                    cache["crypto"]["data"] = []
        result.extend(cache["crypto"]["data"])

    # Auto-save fresh scraped snapshots to Database
    if newly_scraped:
        try:
            db.save_scraped_data(newly_scraped)
            summary = get_market_summary(newly_scraped)
            db.log_scrape_run(summary, target=target)
        except Exception as e:
            print(f"[App] Database auto-save warning: {e}")

    return result


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/data", methods=["GET"])
def api_data():
    target = request.args.get("type", "all").lower()
    category = request.args.get("category", "").strip().lower()
    search = request.args.get("search", "").strip().lower()
    sort_by = request.args.get("sort_by", "").strip().lower()
    order = request.args.get("order", "asc").strip().lower()
    force = request.args.get("force_refresh", "false").lower() == "true"

    data = get_cached_data(target=target, force_refresh=force)

    # Filter category
    if category and category != "all":
        data = [d for d in data if d.get("category", "").lower() == category]

    # Filter search
    if search:
        data = [
            d
            for d in data
            if search in d.get("name", "").lower() or search in d.get("symbol", "").lower()
        ]

    # Sorting
    if sort_by in ["price", "change", "change_percent", "weekly_percent", "monthly_percent", "ytd_percent", "yoy_percent"]:
        is_reverse = order == "desc"
        data.sort(
            key=lambda x: (x.get(sort_by) is None, x.get(sort_by) if x.get(sort_by) is not None else -999999),
            reverse=is_reverse,
        )
    elif sort_by == "name":
        data.sort(key=lambda x: x.get("name", "").lower(), reverse=(order == "desc"))

    return jsonify({
        "success": True,
        "count": len(data),
        "target": target,
        "scraped_at": datetime.now().isoformat(),
        "db_engine": db.active_engine,
        "data": data,
    })


@app.route("/api/summary", methods=["GET"])
def api_summary():
    target = request.args.get("type", "all").lower()
    force = request.args.get("force_refresh", "false").lower() == "true"
    data = get_cached_data(target=target, force_refresh=force)
    summary = get_market_summary(data)
    summary["db_engine"] = db.active_engine
    return jsonify({"success": True, "summary": summary})


@app.route("/api/categories", methods=["GET"])
def api_categories():
    data = get_cached_data(target="all")
    categories = sorted(list(set(d.get("category") for d in data if d.get("category"))))
    return jsonify({"success": True, "categories": categories})


@app.route("/api/db-status", methods=["GET"])
def api_db_status():
    """Returns database health status, engine type, host, and record counts."""
    stats = db.get_db_stats()
    return jsonify({"success": True, "db": stats})


@app.route("/api/history", methods=["GET"])
def api_history():
    """Returns historical price time-series data for a given symbol from the DB."""
    symbol = request.args.get("symbol", "").strip()
    limit = int(request.args.get("limit", 50))
    if not symbol:
        return jsonify({"success": False, "error": "Missing symbol parameter", "history": []})

    history = db.get_symbol_history(symbol, limit=limit)
    return jsonify({
        "success": True,
        "symbol": symbol,
        "count": len(history),
        "db_engine": db.active_engine,
        "history": history,
    })


@app.route("/api/db-config", methods=["POST"])
def api_db_config():
    """Updates database configuration parameters dynamically."""
    global db
    body = request.get_json() or {}
    db_type = body.get("db_type", "mysql")
    host = body.get("host", "127.0.0.1")
    port = body.get("port", 3306 if db_type == "mysql" else 5432)
    user = body.get("user", "root")
    password = body.get("password", "")
    db_name = body.get("db_name", "finance_intel_db")

    db = DatabaseManager(
        db_type=db_type,
        host=host,
        port=port,
        user=user,
        password=password,
        db_name=db_name,
    )

    stats = db.get_db_stats()
    return jsonify({"success": stats["connected"], "db": stats})


@app.route("/api/export", methods=["GET"])
def api_export():
    target = request.args.get("type", "all").lower()
    fmt = request.args.get("format", "csv").lower()
    data = get_cached_data(target=target)

    os.makedirs("exports", exist_ok=True)
    filename = f"tradingeconomics_{target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if fmt == "json":
        filepath = os.path.join("exports", f"{filename}.json")
        export_to_json(data, filepath)
        return send_from_directory("exports", f"{filename}.json", as_attachment=True)

    elif fmt == "excel":
        filepath = os.path.join("exports", f"{filename}.xlsx")
        export_to_excel(data, filepath)
        return send_from_directory("exports", f"{filename}.xlsx", as_attachment=True)

    else:  # csv
        filepath = os.path.join("exports", f"{filename}.csv")
        export_to_csv(data, filepath)
        return send_from_directory("exports", f"{filename}.csv", as_attachment=True)


@app.route("/api/autostart", methods=["GET", "POST"])
def api_autostart():
    """Gets or sets PC Auto-Start status for background scraping."""
    if request.method == "POST":
        body = request.get_json() or {}
        action = body.get("action", "enable").lower()
        target = body.get("target", "scraper").lower()

        if action == "enable":
            success, msg = enable_autostart(target=target)
        else:
            success, msg = disable_autostart()

        return jsonify({"success": success, "message": msg, "status": get_status_summary()})

    return jsonify({"success": True, "status": get_status_summary()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

