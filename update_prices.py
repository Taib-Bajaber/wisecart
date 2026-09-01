import json
from pathlib import Path

products = [
    {
        "store": "Carrefour",
        "product": "Guru Long Grain White Rice",
        "size": "1Kg",
        "price": 160,
        "stock": "In Stock",
        "location": "Mombasa",
        "link": "https://www.carrefour.ke/mafken/en/indian-basmati-rice/guru-long-grain-rice-1kg/p/61721"
    },
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

Path("data").mkdir(exist_ok=True)

with open("data/products.json", "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2)

print("WiseCart data updated.")
