import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

URL = "https://www.carrefour.ke/mafken/en/c/FKEN1701240"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

products = []

for item in soup.select("div.product-card"):
    name = item.get_text(" ", strip=True)

    if "rice" not in name.lower():
        continue

    products.append({
        "store": "Carrefour",
        "product": name,
        "size": "",
        "price": 0,
        "stock": "Unknown",
        "location": "Mombasa",
        "link": URL
    })

Path("data").mkdir(exist_ok=True)

with open("data/carrefour.json", "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2)

print(f"Found {len(products)} Carrefour products.")
