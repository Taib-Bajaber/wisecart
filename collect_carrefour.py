import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import re
from urllib.parse import urljoin

URL = "https://www.carrefour.ke/mafken/en/c/FKEN1701240"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/138 Safari/537.36"
}

response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

products = []

# Look through links on the Carrefour page and identify product information
for link in soup.find_all("a", href=True):

    text = link.get_text(" ", strip=True)

    if not text:
        continue

    # We only want rice products for this first version
    if "rice" not in text.lower():
        continue

    # Find prices inside the product text
    prices = re.findall(r"(\d[\d,]*)\s*\.?\s*00\s*KES", text)

    if not prices:
        continue

    price = float(prices[0].replace(",", ""))

    href = urljoin(URL, link["href"])

    # Try to identify a size
    size_match = re.search(
        r"\b(\d+(?:\.\d+)?\s*(?:kg|g|ml|l))\b",
        text,
        re.IGNORECASE
    )

    size = size_match.group(1) if size_match else ""

    products.append({
        "store": "Carrefour",
        "product": text,
        "size": size,
        "price": price,
        "stock": "Unknown",
        "location": "Mombasa",
        "link": href
    })

# Remove duplicates
unique = {}

for product in products:
    key = (product["product"], product["price"], product["link"])
    unique[key] = product

products = list(unique.values())

Path("data").mkdir(exist_ok=True)

with open("data/carrefour.json", "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2, ensure_ascii=False)

print(f"Found {len(products)} Carrefour rice products.")
