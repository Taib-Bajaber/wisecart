from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import urljoin
import json
import re
import time

URL = "https://www.carrefour.ke/mafken/en/c/FKEN1701240"

products = []

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page(
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        )
    )

    print("Opening Carrefour Kenya...")
    
    try:
        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=90000
        )
    except Exception as e:
        print(f"Page load warning: {e}")

    time.sleep(8)

    print("Page title:", page.title())
    print("Current URL:", page.url)

    # Detect access blocking
    body_text = page.locator("body").inner_text().lower()

    if "access denied" in body_text:
        print("ERROR: Carrefour returned ACCESS DENIED.")
        browser.close()
        raise SystemExit(1)

    # Scroll to load more products
    print("Loading products...")

    previous_count = 0
    stable_rounds = 0

    for i in range(20):
        links = page.locator("a[href*='/p/']")
        current_count = links.count()

        print(f"Scroll {i + 1}/20 - products found: {current_count}")

        if current_count == previous_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= 3:
            break

        previous_count = current_count

        page.mouse.wheel(0, 4000)
        time.sleep(2)

    links = page.locator("a[href*='/p/']")

    print(f"Final product links found: {links.count()}")

    for i in range(links.count()):

        try:
            link = links.nth(i)

            href = link.get_attribute("href")

            if not href:
                continue

            href = urljoin(URL, href)

            # Get the surrounding product-card text
            card = link

            for _ in range(10):
                parent = card.locator("..")

                try:
                    text = parent.inner_text(timeout=2000)
                except Exception:
                    break

                if "KES" in text.upper():
                    card = parent
                    break

                card = parent

            text = card.inner_text()

            if "rice" not in text.lower():
                continue

            # Product name
            name = link.inner_text().strip()

            if not name:
                continue

            # Price
            price_matches = re.findall(
                r"(?:KES|KSh)\s*([\d,]+(?:\.\d+)?)",
                text,
                re.IGNORECASE
            )

            if not price_matches:
                price_matches = re.findall(
                    r"([\d,]+(?:\.\d+)?)\s*KES",
                    text,
                    re.IGNORECASE
                )

            if not price_matches:
                continue

            prices = []

            for value in price_matches:
                try:
                    prices.append(
                        float(value.replace(",", ""))
                    )
                except:
                    pass

            if not prices:
                continue

            price = min(prices)

            # Size
            size_match = re.search(
                r"\b\d+(?:\.\d+)?\s*(?:kg|g|ml|l)\b",
                text,
                re.IGNORECASE
            )

            size = (
                size_match.group(0)
                if size_match
                else ""
            )

            # Old price / discount
            old_price = None

            if len(prices) > 1:
                higher_prices = [
                    p for p in prices
                    if p > price
                ]

                if higher_prices:
                    old_price = max(higher_prices)

            discount = None
            savings = None

            if old_price and old_price > price:
                savings = round(
                    old_price - price,
                    2
                )

                discount = round(
                    ((old_price - price) / old_price) * 100,
                    2
                )

            # Stock
            lower_text = text.lower()

            if "out of stock" in lower_text:
                stock = "Out of Stock"
            elif "in stock" in lower_text:
                stock = "In Stock"
            else:
                stock = "Unknown"

            products.append({
                "store": "Carrefour",
                "product": name,
                "size": size,
                "price": price,
                "old_price": old_price,
                "discount_percent": discount,
                "discount_savings": savings,
                "stock": stock,
                "location": "Kenya",
                "link": href
            })

        except Exception as e:
            print(f"Skipped product {i}: {e}")

    browser.close()


# Remove duplicates
unique = {}

for product in products:
    key = (
        product["product"].lower(),
        product["size"].lower(),
        product["link"]
    )

    unique[key] = product

products = list(unique.values())


# Save results
Path("data").mkdir(exist_ok=True)

with open(
    "data/carrefour.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        products,
        f,
        indent=2,
        ensure_ascii=False
    )


print()
print("=" * 50)
print(f"FOUND {len(products)} CARREFOUR RICE PRODUCTS")
print("=" * 50)

for product in products[:10]:
    print(
        product["product"],
        "|",
        product["size"],
        "|",
        product["price"],
        "KES"
    )

if len(products) == 0:
    print()
    print("WARNING: 0 products were collected.")
    print("Do NOT treat this run as successful.")
