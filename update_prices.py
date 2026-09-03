import json
from pathlib import Path


# ============================================================
# WISECART DATABASE UPDATE
# ============================================================
#
# Only use REAL collected supermarket data.
# Never insert fake/test prices.
#
# Currently:
#   Carrefour = active collector
#
# Future:
#   Naivas
#   Quickmart
#   FoodPlus
#
# will be added when their collectors are working.
# ============================================================


DATA_DIR = Path("data")

CARREFOUR_FILE = DATA_DIR / "carrefour.json"

OUTPUT_FILE = DATA_DIR / "products.json"


# ============================================================
# LOAD CARREFOUR DATA
# ============================================================

if not CARREFOUR_FILE.exists():

    raise SystemExit(
        "ERROR: data/carrefour.json does not exist."
    )


with open(
    CARREFOUR_FILE,
    "r",
    encoding="utf-8"
) as f:

    carrefour_products = json.load(f)


# ============================================================
# VALIDATE DATA
# ============================================================

if not isinstance(carrefour_products, list):

    raise SystemExit(
        "ERROR: Carrefour data is not a list."
    )


if len(carrefour_products) == 0:

    raise SystemExit(
        "ERROR: Carrefour returned 0 products."
    )


# ============================================================
# CLEAN PRODUCTS
# ============================================================

products = []

for product in carrefour_products:

    if not isinstance(product, dict):
        continue

    if not product.get("product"):
        continue

    if product.get("price") is None:
        continue

    # Make sure store is present.
    product["store"] = "Carrefour"

    products.append(product)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

unique = {}

for product in products:

    key = (
        str(product.get("product", "")).strip().lower(),
        str(product.get("size", "")).strip().lower(),
        str(product.get("link", "")).strip()
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
        str(
            product.get("product", "")
        ).lower(),

        str(
            product.get("size", "")
        ).lower()
    )
)


# ============================================================
# SAVE
# ============================================================

DATA_DIR.mkdir(
    exist_ok=True
)


with open(
    OUTPUT_FILE,
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
print("WISECART DATABASE UPDATED")
print("=" * 60)
print()

print(
    f"Real Carrefour products: {len(products)}"
)

print(
    f"Saved to: {OUTPUT_FILE}"
)

print()

print(
    "No fake supermarket prices were added."
)

print()
