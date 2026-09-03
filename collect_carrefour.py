from playwright.sync_api import sync_playwright
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import os
import re
import time


URL = "https://www.carrefour.ke/mafken/en/c/FKEN1701240"


# ============================================================
# PROXY
# ============================================================

def get_proxy():
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


# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# OPEN CARREFOUR
# ============================================================

def open_carrefour(page):

    print()
    print("Opening Carrefour Kenya...")
    print(URL)
    print()

    errors = []

    # Try several navigation methods.
    attempts = [
        {
            "wait_until": "commit",
            "timeout": 60000
        },
        {
            "wait_until": "domcontentloaded",
            "timeout": 90000
        },
        {
            "wait_until": "load",
            "timeout": 90000
        }
    ]

    for attempt_number, options in enumerate(
        attempts,
        start=1
    ):

        print(
            f"Navigation attempt "
            f"{attempt_number}/{len(attempts)}..."
        )

        try:

            response = page.goto(
                URL,
                wait_until=options["wait_until"],
                timeout=options["timeout"]
            )

            print(
                "Navigation response:",
                response.status
                if response
                else "none"
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

            # If Chrome has not gone to its error page,
            # consider navigation successful.
            if "chrome-error" not in page.url.lower():

                print()
                print(
                    "Carrefour page reached successfully."
                )
                print()

                return True

        except Exception as e:

            error_text = str(e)

            errors.append(
                error_text
            )

            print(
                "Navigation warning:",
                error_text
            )

            time.sleep(3)

    print()
    print(
        "All Carrefour navigation attempts failed."
    )

    for error in errors:
        print(
            "ERROR:",
            error
        )

    return False


# ============================================================
# MAIN
# ============================================================

products = []


with sync_playwright() as p:

    proxy = get_proxy()

    browser_options = {
        "headless": True,

        # Important for the HTTP/2 problem seen in GitHub Actions.
        "args": [
            "--disable-http2",
            "--disable-quic",
            "--disable-features=UseDnsHttpsSvcbAlpn",
            "--disable-blink-features=AutomationControlled"
        ]
    }

    if proxy:
        browser_options["proxy"] = proxy

    print()
    print("=" * 60)
    print("WISECART CARREFOUR COLLECTOR")
    print("=" * 60)
    print()

    print("Launching Chromium...")

    browser = p.chromium.launch(
        **browser_options
    )

    context = browser.new_context(

        viewport={
            "width": 1440,
            "height": 900
        },

        ignore_https_errors=True,

        user_agent=(
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0.0.0 "
            "Safari/537.36"
        ),

        locale="en-KE",

        timezone_id="Africa/Nairobi"
    )

    page = context.new_page()

    # Hide obvious automation signal.
    page.add_init_script("""
        Object.defineProperty(
            navigator,
            'webdriver',
            {
                get: () => undefined
            }
        );
    """)

    success = open_carrefour(page)

    if not success:

        browser.close()

        raise RuntimeError(
            "Browser could not reach Carrefour."
        )

    # ========================================================
    # CHECK PAGE
    # ========================================================

    try:

        body_text = page.locator(
            "body"
        ).inner_text(
            timeout=10000
        ).lower()

    except Exception:

        body_text = ""

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

    # ========================================================
    # LOAD PRODUCTS
    # ========================================================

    print()
    print("Loading Carrefour products...")
    print()

    previous_count = 0
    stable_rounds = 0

    for i in range(40):

        links = page.locator(
            "a[href*='/p/']"
        )

        current_count = links.count()

        print(
            f"Scroll {i + 1}/40 | "
            f"product links: {current_count}"
        )

        if current_count == previous_count:

            stable_rounds += 1

        else:

            stable_rounds = 0

        if stable_rounds >= 5:

            print(
                "Product count is stable."
            )

            break

        previous_count = current_count

        page.mouse.wheel(
            0,
            5000
        )

        time.sleep(2)

    # ========================================================
    # COLLECT LINKS
    # ========================================================

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

    if total_links == 0:

        browser.close()

        raise RuntimeError(
            "Carrefour loaded, but no product "
            "links were found."
        )

    # ========================================================
    # EXTRACT PRODUCTS
    # ========================================================

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
                card.inner_text(
                    timeout=3000
                )
            )

            # First test = rice only.
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

                "discount_percent": discount,

                "discount_savings": savings,

                "stock": stock,

                "location": "Mombasa",

                "link": href,

                "updated_at": updated_at
            })

        except Exception as e:

            print(
                f"Skipped product {i}: {e}"
            )

    browser.close()


# ============================================================
# REMOVE DUPLICATES
# ============================================================

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


# ============================================================
# SORT
# ============================================================

products.sort(
    key=lambda product: (
        product["product"].lower(),
        product["size"].lower()
    )
)


# ============================================================
# SAVE
# ============================================================

Path("data").mkdir(
    exist_ok=True
)

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


# ============================================================
# RESULT
# ============================================================

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
        product["stock"]
    )

print()

if len(products) == 0:

    print(
        "ERROR: 0 products were collected."
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
