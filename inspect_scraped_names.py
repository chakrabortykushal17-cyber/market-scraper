from scraper import TradingEconomicsScraper

s = TradingEconomicsScraper()
stocks = s.scrape_stocks()
comms = s.scrape_commodities()
cryptos = s.scrape_crypto()

print("=== STOCKS ===")
for item in stocks:
    print(f"Name: '{item['name']}' | Price: {item['price']} | Chg: {item['change']}")

print("\n=== COMMODITIES ===")
for item in comms:
    print(f"Name: '{item['name']}' | Price: {item['price']} | Chg: {item['change']}")

print("\n=== CRYPTO ===")
for item in cryptos:
    print(f"Name: '{item['name']}' | Price: {item['price']} | Chg: {item['change']}")
