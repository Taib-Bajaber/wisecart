from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import os
import re
import time


URL = "https://www.carrefour.ke/mafken/en/c/FKEN1701240"


def get_proxy():
    """
    Proxy is OPTIONAL.

    If CARREFOUR_PROXY exists, use it.
    If it does not exist, connect directly.
    """

    proxy_string = os.environ.get(
        "CARREFOUR_PROXY",
        ""
    ).strip()

    if not proxy_string:
        print("No CARREFOUR_PROXY configured.")
        print("Using direct Carrefour connection.")
        return None

    if "://" not in proxy_string:
        proxy_string = "http://" + proxy_string

    parsed = urlparse(proxy_string)

    if not parsed.hostname or not parsed.port:
        raise RuntimeError(
            "CARREFOUR_PROXY format is invalid."
        )

    proxy = {
        "server": (
            f"{parsed.scheme}://"
            f"{parsed.hostname}:"
            f"{parsed.port}"
        )
    }

    if parsed.username:
        proxy["username"] = parsed.username

    if parsed.password:
        proxy["password"] = parsed.password

    print("Using Carrefour proxy:")
    print(proxy["server"])

    return proxy


def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def extract_prices(text):

    matches = re.findall(
        r"(?:KES|KSh)\s*([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if not matches:
        matches = re.findall(
            r"([\d,]+(?:\.\d+)?)\s*(?:KES|KSh)",
            text,
            re.IGNORECASE
        )

    prices = []

    for value in matches:

        try:
            number = float(
                value.replace(",", "")
            )

            if number > 0:
                prices.append(number)

        except ValueError:
            continue

    return prices


def extract_size(text):

    match = re.search(
        r"\b\d+(?:\.\d+)?\s*"
        r"(?:kg|g|mg|ml|cl|l)\b",
        text,
        re.IGNORECASE
    )

    if not match:
        return ""

    return clean_text(
        match.group(0)
    )


def extract_stock(text):

    lower = text.lower()

    if "out of stock" in lower:
        return "Out of Stock"

    if "in stock" in lower:
        return "In Stock"

    if "available" in lower:
        return "Available"

    return "Unknown"


def find_product_card(link):

    card = link

    for _ in range(10):

        try:

            parent = card.locator("..")

            text = parent.inner_text(
                timeout=2000
            )

            text = clean_text(text)

            if (
                "KES" in text.upper()
                or "KSH" in text.upper()
            ):
                return parent

            card = parent

        except Exception:
            break

    return link


products = []


with sync_playwright() as p:

    proxy = get_proxy()

    browser_options = {
        "headless": True
    }

    if proxy:
        browser_options["proxy"] = proxy

    browser = p.chromium.launch(
        **browser_options
    )

    context = browser.new_context(
        viewport={
            "width": 1440,
            "height": 900
        },
        user_agent=(
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0.0.0 "
            "Safari/537.36"
        )
    )

    page = context.new_page()

    print()
    print("=" * 60)
    print("WISECART CARREFOUR COLLECTOR")
    print("=" * 60)
    print()

    print("Opening Carrefour Kenya...")
    print(URL)
    print()

    try:

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=90000
        )

    except Exception as e:

        print(
            "Page load warning:",
            e
        )

    time.sleep(8)

    print(
        "Page title:",
        page.title()
    )

    print(
        "Current URL:",
        page.url
    )

    # Browser-level failure

    if "chrome-error" in page.url.lower():

        browser.close()

        raise RuntimeError(
            "Browser could not reach Carrefour."
        )

    # Read page text

    try:

        body_text = page.locator(
            "body"
        ).inner_text().lower()

    except Exception:

        body_text = ""

    # Detect blocking

    blocked_phrases = [
        "access denied",
        "request blocked",
        "temporarily blocked",
        "forbidden"
    ]

    for phrase in blocked_phrases:

        if phrase in body_text:

            browser.close()

            raise RuntimeError(
                "Carrefour blocked the request: "
                + phrase
            )

    print()
    print("Loading products...")
    print()

    previous_count = 0
    stable_rounds = 0

    # Scroll through catalogue

    for i in range(30):

        links = page.locator(
            "a[href*='/p/']"
        )

        current_count = links.count()

        print(
            f"Scroll {i + 1}/30 | "
            f"products found: {current_count}"
        )

        if current_count == previous_count:

            stable_rounds += 1

        else:

            stable_rounds = 0

        if stable_rounds >= 4:

            print(
                "Product count is stable."
            )

            break

        previous_count = current_count

        page.mouse.wheel(
            0,
            4500
        )

        time.sleep(2)

    links = page.locator(
        "a[href*='/p/']"
    )

    total_links = links.count()

    print()
    print(
        f"Final product links found: "
        f"{total_links}"
    )
    print()

    # Collect products

    for i in range(total_links):

        try:

            link = links.nth(i)

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            href = urljoin(
                URL,
                href
            )

            card = find_product_card(
                link
            )

            text = clean_text(
                card.inner_text()
            )

            # Currently collecting rice only.
            # We will expand this after
            # the first successful run.

            if "rice" not in text.lower():
                continue

            name = clean_text(
                link.inner_text()
            )

            if not name:
                continue

            prices = extract_prices(
                text
            )

            if not prices:
                continue

            # Current price

            price = min(prices)

            # Old price

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

            # Discount

            discount = None
            savings = None

            if (
                old_price is not None
                and old_price > price
            ):

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

            size = extract_size(
                text
            )

            stock = extract_stock(
                text
            )

            updated_at = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime()
            )

            products.append({

                "store": "Carrefour",

                "product": name,

                "size": size,

                "price": price,

                "old_price": old_price,

                "discount_percent":
                    discount,

                "discount_savings":
                    savings,

                "stock": stock,

                "location": "Mombasa",

                "link": href,

                "updated_at":
                    updated_at
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


# Sort products

products.sort(
    key=lambda product: (
        product["product"].lower(),
        product["size"].lower()
    )
)


# Create data folder

Path("data").mkdir(
    exist_ok=True
)


# Save Carrefour data

output_file = (
    "data/carrefour.json"
)

with open(
    output_file,
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
print("=" * 60)
print(
    f"FOUND {len(products)} "
    "CARREFOUR RICE PRODUCTS"
)
print("=" * 60)
print()


# Show first 10

for product in products[:10]:

    print(
        product["product"],
        "|",
        product["size"],
        "|",
        product["price"],
        "KES",
        "|",
        product["stock"]
    )


print()


# Never allow an empty run

if len(products) == 0:

    print(
        "ERROR: 0 products were collected."
    )

    print(
        "The workflow will be marked FAILED."
    )

    raise SystemExit(1)


print(
    f"SUCCESS: Saved {len(products)} "
    f"products to {output_file}"
)

print()
print(
    "Carrefour collection complete."
)
