import json
from pathlib import Path

# Load Carrefour data collected by collect_carrefour.py
carrefour_file = Path("data/carrefour.json")

carrefour_products = []

if carrefour_file.exists():
    with open(carrefour_file, "r", encoding="utf-8") as f:
        carrefour_products = json.load(f)

# Temporary data for the other supermarkets
other_stores = [
    {
        "store": "Naivas",
        "product": "Guru Long Grain White Rice",
        "size": "1Kg",
        "price": 175,
        "stock": "In Stock",
        "location": "Mombasa",
        "link": "https://naivas.online/"
    },
    {
        "store": "Quickmart",
        "product": "Guru Long Grain White Rice",
        "size": "1Kg",
        "price": 190,
        "stock": "In Stock",
        "location": "Mombasa",
        "link": "https://quickmart.co.ke/"
    },
    {
        "store": "FoodPlus",
        "product": "Guru Long Grain White Rice",
        "size": "1Kg",
        "price": 264,
        "stock": "In Stock",
        "location": "Mombasa",
        "link": "https://foodplus.co.ke/"
    }
]

# Combine the data
products = carrefour_products + other_stores

# Save WiseCart database
Path("data").mkdir(exist_ok=True)

with open("data/products.json", "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2)

print(f"WiseCart updated with {len(products)} products.")
