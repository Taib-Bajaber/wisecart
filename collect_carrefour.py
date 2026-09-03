from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
import json
import re

import requests
from bs4 import BeautifulSoup


URL = "https://www.carrefour.ke/mafken/en/c/FKEN1701240"
STORE = "Carrefour"
LOCATION = "Mombasa"


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def extract_prices(text):
    prices = []

    patterns = [
        r"(?:KES|KSh)\s*([\d,]+(?:\.\d+)?)",
        r"([\d,]+(?:\.\d+)?)\s*(?:KES|KSh)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for value in matches:
            try:
                number = float(value.replace(",", ""))

                if number > 0:
                    prices.append(number)

            except ValueError:
                continue

        if prices:
            break

    return prices


def extract_size(text):
    match = re.search(
        r"\b\d+(?:\.\d+)?\s*"
        r"(?:kg|g|mg|ml|cl|l)\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return clean_text(match.group(0))

    return ""


def extract_stock(text):
    lower = text.lower()

    if "out of stock" in lower:
        return "Out of Stock"

    if "in stock" in lower:
        return "In Stock"

    if "available" in lower:
        return "Available"

    return "Unknown"


def find_product_container(anchor):
    current = anchor

    for _ in range(10):
        current = current.parent

        if current is None:
            break

        text = clean_text(
            current.get_text(" ", strip=True)
        )

        if re.search(
            r"(?:KES|KSh)\s*[\d,]+",
            text,
            re.IGNORECASE,
        ):
            return current

    return anchor.parent


def extract_product_name(anchor):
    return clean_text(
        anchor.get_text(" ", strip=True)
    )


def collect():
    print()
    print("=" * 60)
    print("WISECART CARREFOUR COLLECTOR")
    print("=" * 60)
    print()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,"
            "*/*;q=0.8"
        ),
        "Accept-Language": "en-KE,en;q=0.9",
    }

    print("Opening Carrefour Kenya...")
    print(URL)
    print()

    response = requests.get(
        URL,
        headers=headers,
        timeout=60,
    )

    print(
        "Carrefour HTTP status:",
        response.status_code
    )

    print(
        "Response length:",
        len(response.content)
    )

    print(
        "Server:",
        response.headers.get("server", "")
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Carrefour returned HTTP {response.status_code}"
        )

    html = response.text

    if not html:
        raise RuntimeError(
            "Carrefour returned an empty page."
        )

    print("Carrefour HTML received successfully.")
    print()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    anchors = soup.find_all(
        "a",
        href=re.compile(
            r"/p/",
            re.IGNORECASE
        ),
    )

    print(
        "Product links found:",
        len(anchors)
    )

    print()

    products = []
    seen = set()

    updated_at = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    for anchor in anchors:
        try:
            href = anchor.get(
                "href",
                ""
            ).strip()

            if not href:
                continue

            link = urljoin(
                URL,
                href
            )

            card = find_product_container(
                anchor
            )

            card_text = clean_text(
                card.get_text(
                    " ",
                    strip=True
                )
            )

            name = extract_product_name(
                anchor
            )

            if not name:
                continue

            # Current WiseCart collection target.
            if "rice" not in card_text.lower():
                continue

            prices = extract_prices(
                card_text
            )

            if not prices:
                continue

            price = min(prices)

            old_price = None

            higher_prices = [
                value
                for value in prices
                if value > price
            ]

            if higher_prices:
                old_price = max(
                    higher_prices
                )

            discount_percent = None
            discount_savings = None

            if (
                old_price is not None
                and old_price > price
            ):
                discount_savings = round(
                    old_price - price,
                    2
                )

                discount_percent = round(
                    (
                        (
                            old_price
                            - price
                        )
                        / old_price
                    )
                    * 100,
                    2,
                )

            size = extract_size(
                card_text
            )

            stock = extract_stock(
                card_text
            )

            key = (
                name.lower(),
                size.lower(),
                link,
            )

            if key in seen:
                continue

            seen.add(key)

            products.append(
                {
                    "store": STORE,
                    "product": name,
                    "size": size,
                    "price": price,
                    "old_price": old_price,
                    "discount_percent": discount_percent,
                    "discount_savings": discount_savings,
                    "stock": stock,
                    "location": LOCATION,
                    "link": link,
                    "updated_at": updated_at,
                }
            )

        except Exception as error:
            print(
                "Skipped product:",
                error
            )

    products.sort(
        key=lambda item: (
            item["product"].lower(),
            item["size"].lower(),
        )
    )

    output = Path(
        "data/carrefour.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            products,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print(
        f"FOUND {len(products)} "
        "CARREFOUR RICE PRODUCTS"
    )
    print("=" * 60)
    print()

    for product in products[:10]:
        print(
            product["product"],
            "|",
            product["size"],
            "|",
            product["price"],
            "KES",
            "|",
            product["stock"],
        )

    print()

    if not products:
        raise RuntimeError(
            "Carrefour loaded, but no rice products "
            "could be extracted."
        )

    print(
        f"SUCCESS: Saved {len(products)} "
        f"products to {output}"
    )


if __name__ == "__main__":
    collect()
