import json
from pathlib import Path

CARREFOUR_FILE = Path("data/carrefour.json")
OUTPUT_FILE = Path("data/products.json")

with open(CARREFOUR_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, dict):
    products = data.get("products", [])
elif isinstance(data, list):
    products = data
else:
    raise SystemExit("ERROR: Invalid Carrefour data format.")

if not products:
    raise SystemExit("ERROR: No Carrefour products found.")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print("WiseCart data updated successfully.")
print("Carrefour products:", len(products))
print("Saved:", OUTPUT_FILE)
