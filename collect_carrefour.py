from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import os
import re
import time

URL = "https://www.carrefour.ke/mafken/en/c/FKEN1701240"


def get_proxy():
    proxy_string = os.environ.get("CARREFOUR_PROXY", "").strip()

    if not proxy_string:
        raise RuntimeError("CARREFOUR_PROXY secret is missing.")

    # Add scheme if Turnoxy does not provide one
    if "://" not in proxy_string:
        proxy_string = "http://" + proxy_string

    parsed = urlparse(proxy_string)

    if not parsed.hostname or not parsed.port:
        raise RuntimeError("CARREFOUR_PROXY format is invalid.")

    proxy = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    }

    if parsed.username:
        proxy["username"] = parsed.username

    if parsed.password:
        proxy["password"] = parsed.password

    return proxy


proxy = get_proxy()

print("Using Kenya proxy...")
print("Proxy server:", proxy["server"])


products = []


with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True,
        proxy=proxy
    )

    page = browser.new_page(
        viewport={
            "width": 1440,
            "height": 900
        },
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

    # Stop if Carrefour could not be reached
    if "chrome-error" in page.url.lower():
        print("ERROR: Browser could not reach Carrefour.")
        browser.close()
        raise SystemExit(1)

    body_text = page.locator("body").inner_text().lower()

    # Stop if Carrefour blocks the request
    if "access denied" in body_text:
        print("ERROR: Carrefour returned ACCESS DENIED.")
        browser.close()
        raise SystemExit(1)

    print("Loading products...")

    previous_count = 0
    stable_rounds = 0

    for i in range(20):

        links = page.locator("a[href*='/p/']")
        current_count = links.count()

        print(
            f"Scroll {i + 1}/20 - "
            f"products found: {current_count}"
        )

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

    print(
        f"Final product links found: {links.count()}"
    )


    for i in range(links.count()):

        try:

            link = links.nth(i)

            href = link.get_attribute("href")

            if not href:
                continue

            href = urljoin(URL, href)

            # Find the product card
            card = link

            for _ in range(10):

                parent = card.locator("..")

                try:
                    text = parent.inner_text(
                        timeout=2000
                    )

                except Exception:
                    break

                if (
                    "KES" in text.upper()
                    or "KSH" in text.upper()
                ):
                    card = parent
                    break

                card = parent

            text = card.inner_text()

            # Only collect rice products
            if "rice" not in text.lower():
                continue

            name = link.inner_text().strip()

            if not name:
                continue

            # Find prices
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
                        float(
                            value.replace(",", "")
                        )
                    )

                except ValueError:
                    pass

            if not prices:
                continue

            # Lowest price = current price
            price = min(prices)

            # Product size
            size_match = re.search(
                r"\b\d+(?:\.\d+)?\s*"
                r"(?:kg|g|ml|l)\b",
                text,
                re.IGNORECASE
            )

            size = (
                size_match.group(0)
                if size_match
                else ""
            )

            # Old price
            old_price = None

            if len(prices) > 1:

                higher_prices = [
                    p for p in prices
                    if p > price
                ]

                if higher_prices:
                    old_price = max(
                        higher_prices
                    )

            # Discount
            discount = None
            savings = None

            if old_price and old_price > price:

                savings = round(
                    old_price - price,
                    2
                )

                discount = round(
                    (
                        (old_price - price)
                        / old_price
                    ) * 100,
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

                "location": "Mombasa",

                "link": href

            })

        except Exception as e:

            print(
                f"Skipped product {i}: {e}"
            )


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


products = list(
    unique.values()
)


# Create data folder
Path("data").mkdir(
    exist_ok=True
)


# Save Carrefour data
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

print(
    f"FOUND {len(products)} "
    "CARREFOUR RICE PRODUCTS"
)

print("=" * 50)


# Show first 10 products
for product in products[:10]:

    print(
        product["product"],
        "|",
        product["size"],
        "|",
        product["price"],
        "KES"
    )


# Do not allow a fake successful run
if len(products) == 0:

    print()

    print(
        "ERROR: 0 products were collected."
    )

    print(
        "The run will be marked as FAILED."
    )

    raise SystemExit(1)
