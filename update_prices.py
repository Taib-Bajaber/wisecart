import json

CARREFOUR_FILE = "data/carrefour.json"
OUTPUT_FILE = "data/products.json"

with open(CARREFOUR_FILE, "r", encoding="utf-8") as f:
    carrefour_data = json.load(f)

if isinstance(carrefour_data, dict):
    products = carrefour_data.get("products", [])
else:
    products = carrefour_data

if not isinstance(products, list):
    raise SystemExit("ERROR: Carrefour products data is not a list.")

if not products:
    raise SystemExit("ERROR: Carrefour product list is empty.")

products = sorted(
    products,
    key=lambda x: x.get("product", "").lower()
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print("WiseCart data updated successfully.")
print("Carrefour products:", len(products))
print("Saved:", OUTPUT_FILE)
