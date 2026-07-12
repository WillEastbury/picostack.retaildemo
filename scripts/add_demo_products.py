"""Adds 35 new demo products to the WaveSearch catalog via a real delta ingestion call, and
verifies the existing catalog was left untouched (cache-hit, not re-enriched/re-embedded).

Categories added: Batteries, Soft Drinks, T-Shirts, Shoes, USB Sticks, Memory Cards (35 products
total). Products use minimal seed data (title/description/categories/brands/price/availability)
and rely on the existing ingestion-time LLM enrichment pass (_enrich_catalog_with_llm) to fill in
tags/expanded description, exactly like every other product in this catalog.

/search/ingest/catalog REPLACES the whole runtime with whatever product list is POSTed, so this
script first fetches the full current catalog (via a single large /search/query call, which
returns each product's full Retail-API-shaped payload under "product"), appends the 35 new
products unmodified for everything else, and re-posts the merged list. Because the existing
products are POSTed back byte-for-byte identical to what's already indexed, their content hash
matches the enrichment/vector caches and they are NOT re-enriched or re-embedded -- only the 35
new products pay that cost. This is the delta-ingestion behavior the catalog cache was built for.

Usage:
    python scripts/add_demo_products.py --base-url https://search-api.retail.demos.wavefunctionlabs.com
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

import aiohttp


async def get_json(session: aiohttp.ClientSession, url: str, headers: dict[str, str]) -> Any:
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        return await response.json()


async def post_json(session: aiohttp.ClientSession, url: str, headers: dict[str, str], payload: Any) -> Any:
    async with session.post(url, headers=headers, json=payload) as response:
        response.raise_for_status()
        return await response.json()


async def fetch_admin_token(session: aiohttp.ClientSession, sts_url: str, username: str, password: str, tenant: str) -> str:
    body = await post_json(
        session, f"{sts_url.rstrip('/')}/sts/login", {}, {"username": username, "password": password, "audience": "wavesearch-api", "tenant": tenant}
    )
    return str(body["access_token"])


def _product(
    product_id: str,
    title: str,
    description: str,
    category: str,
    brand: str,
    price: float,
    color: str,
    family: str,
    quantity: int,
) -> dict[str, Any]:
    # Matches the exact Retail-API-shaped payload the rest of the catalog already uses (see a
    # live /search/query result's "product" field) so ingestion/enrichment/embedding treats these
    # identically to every other product.
    return {
        "name": f"projects/demo/locations/global/catalogs/default_catalog/branches/default_branch/products/{product_id}",
        "id": product_id,
        "type": "PRIMARY",
        "primaryProductId": product_id,
        "gtin": f"0{abs(hash(product_id)) % 10**11:011d}",
        "searchGridEligible": True,
        "title": title,
        "description": description,
        "languageCode": "en-GB",
        "categories": [category],
        "brands": [brand],
        "uri": f"https://store.example/products/{product_id}",
        "priceInfo": {"currencyCode": "GBP", "price": price},
        "availability": "IN_STOCK",
        "availableQuantity": quantity,
        "attributes": {
            "color": {"text": [color], "searchable": True, "indexable": True},
            "family": {"text": [family], "searchable": True, "indexable": True},
        },
        "sizes": ["One Size"],
        "conditions": ["new"],
        "tags": [],
        "images": [{"width": 1024, "height": 1024, "uri": "/static/images/product-generic.jpg"}],
    }


def build_new_products() -> list[dict[str, Any]]:
    new_products: list[dict[str, Any]] = []

    batteries = [
        ("AA Alkaline Battery 4-Pack", "Long-lasting AA alkaline batteries", "silver", 3.99, 45),
        ("AAA Alkaline Battery 8-Pack", "Long-lasting AAA alkaline batteries", "silver", 4.49, 60),
        ("Rechargeable NiMH AA 4-Pack", "High-capacity rechargeable AA batteries", "green", 9.99, 30),
        ("9V Alkaline Battery 2-Pack", "Standard 9V batteries for smoke alarms and instruments", "black", 5.49, 25),
        ("Lithium Coin Cell CR2032 5-Pack", "Long-life lithium coin cell batteries for watches and remotes", "silver", 4.29, 50),
        ("USB Battery Charger 4-Slot", "Smart charger for AA/AAA rechargeable batteries", "black", 14.99, 20),
    ]
    for i, (title, desc, color, price, qty) in enumerate(batteries, start=1):
        new_products.append(_product(f"SKU-BATT-{i:03d}", title, desc, "Electronics > Power > Batteries", "Voltify", price, color, "Power", qty))

    drinks = [
        ("Cola Soft Drink 330ml Can", "Classic carbonated cola soft drink", "red", 0.89, 200),
        ("Lemon Lime Soda 330ml Can", "Refreshing citrus carbonated soft drink", "green", 0.89, 180),
        ("Sparkling Orange Soda 330ml Can", "Fizzy orange flavoured soft drink", "orange", 0.89, 160),
        ("Diet Cola 6-Pack Cans", "Zero sugar cola soft drink multipack", "black", 3.99, 90),
        ("Ginger Beer 330ml Bottle", "Spiced ginger carbonated soft drink", "brown", 1.29, 70),
        ("Tonic Water 1L Bottle", "Classic quinine tonic water mixer", "clear", 1.49, 60),
    ]
    for i, (title, desc, color, price, qty) in enumerate(drinks, start=1):
        new_products.append(_product(f"SKU-DRINK-{i:03d}", title, desc, "Grocery > Drinks > Soft Drinks", "Fizzwell", price, color, "Beverage", qty))

    tshirts = [
        ("Classic Crew Neck T-Shirt", "Soft cotton crew neck t-shirt for everyday wear", "white", 12.99, 120),
        ("Graphic Print T-Shirt", "Cotton t-shirt with printed graphic design", "black", 14.99, 100),
        ("V-Neck T-Shirt", "Lightweight cotton v-neck t-shirt", "navy", 13.49, 90),
        ("Long Sleeve T-Shirt", "Cotton long sleeve t-shirt for cooler days", "grey", 16.99, 80),
        ("Performance Sport T-Shirt", "Moisture-wicking t-shirt for workouts and running", "blue", 18.99, 70),
        ("Organic Cotton T-Shirt", "Sustainably sourced organic cotton t-shirt", "green", 17.99, 60),
    ]
    for i, (title, desc, color, price, qty) in enumerate(tshirts, start=1):
        new_products.append(_product(f"SKU-TSHIRT-{i:03d}", title, desc, "Clothing > Tops > T-Shirts", "Everwear", price, color, "Apparel", qty))

    shoes = [
        ("Running Shoe", "Lightweight cushioned running shoe for daily training", "black", 64.99, 55),
        ("Casual Sneaker", "Everyday casual sneaker with breathable upper", "white", 49.99, 65),
        ("Trail Running Shoe", "Grippy trail running shoe for off-road terrain", "grey", 74.99, 40),
        ("Slip-On Canvas Shoe", "Comfortable slip-on canvas shoe for casual wear", "navy", 34.99, 70),
        ("Walking Shoe", "Supportive walking shoe with cushioned insole", "brown", 54.99, 45),
        ("High-Top Sneaker", "Retro-styled high-top sneaker", "red", 59.99, 50),
    ]
    for i, (title, desc, color, price, qty) in enumerate(shoes, start=1):
        new_products.append(_product(f"SKU-SHOE-{i:03d}", title, desc, "Footwear > Shoes", "Stridewell", price, color, "Footwear", qty))

    usb_sticks = [
        ("USB 3.0 Flash Drive 32GB", "Compact high-speed USB 3.0 flash drive", "black", 7.99, 100),
        ("USB 3.0 Flash Drive 64GB", "Compact high-speed USB 3.0 flash drive", "black", 11.99, 90),
        ("USB 3.0 Flash Drive 128GB", "High-capacity USB 3.0 flash drive", "silver", 17.99, 70),
        ("USB-C Flash Drive 64GB", "Dual USB-C/USB-A flash drive for phones and laptops", "grey", 15.99, 60),
        ("Metal USB Flash Drive 32GB", "Durable metal-bodied USB flash drive with keyring loop", "silver", 9.99, 80),
        ("Encrypted USB Flash Drive 64GB", "Password-protected secure USB flash drive", "black", 24.99, 40),
    ]
    for i, (title, desc, color, price, qty) in enumerate(usb_sticks, start=1):
        new_products.append(_product(f"SKU-USB-{i:03d}", title, desc, "Electronics > Storage > USB Drives", "DataForge", price, color, "Storage", qty))

    memory_cards = [
        ("MicroSD Card 32GB", "High-speed microSD card for cameras and phones", "black", 6.99, 110),
        ("MicroSD Card 128GB", "High-capacity microSD card with adapter", "black", 14.99, 85),
        ("SD Card 64GB UHS-I", "Fast SD card for cameras and camcorders", "grey", 12.99, 75),
        ("SD Card 256GB UHS-II", "Professional high-speed SD card for 4K video", "grey", 39.99, 35),
        ("MicroSD Card 64GB with Adapter", "Reliable microSD card bundled with full-size adapter", "black", 9.99, 95),
    ]
    for i, (title, desc, color, price, qty) in enumerate(memory_cards, start=1):
        new_products.append(_product(f"SKU-MEM-{i:03d}", title, desc, "Electronics > Storage > Memory Cards", "DataForge", price, color, "Storage", qty))

    return new_products


async def run(args: argparse.Namespace) -> int:
    base = args.base_url.rstrip("/")
    public_headers = {"X-Tenant-Id": args.tenant}
    async with aiohttp.ClientSession() as session:
        admin_token = await fetch_admin_token(session, args.sts_url, args.admin_user, args.admin_password, args.tenant)
        admin_headers = {"X-Tenant-Id": args.tenant, "Authorization": f"Bearer {admin_token}"}
        print(f"authenticated as {args.admin_user!r} against {args.sts_url}")

        baseline = await post_json(session, f"{base}/search/query", public_headers, {"query": "", "pageSize": 500})
        existing_products = [row["product"] for row in (baseline.get("results") or []) if isinstance(row.get("product"), dict)]
        print(f"fetched {len(existing_products)} existing products (reported totalSize={baseline.get('totalSize')})")

        new_products = build_new_products()
        print(f"generated {len(new_products)} new products across categories: batteries, soft drinks, t-shirts, shoes, USB sticks, memory cards")

        merged = existing_products + new_products
        print(f"\n== ingesting merged catalog ({len(merged)} products) ==")
        result = await post_json(session, f"{base}/search/ingest/catalog", admin_headers, {"products": merged})
        enrichment = result.get("enrichment") or {}
        print(f"accepted={result.get('accepted')}  ingestedCount={result.get('ingestedCount')}  totalProducts={result.get('totalProducts')}")
        print(f"enrichment: applied={enrichment.get('applied')}  reusedFromCache={enrichment.get('reusedFromCache')}  reason={enrichment.get('reason')}")
        if "vectorIndexed" in result:
            print(f"vector index: {result['vectorIndexed']}")

        verify = await post_json(session, f"{base}/search/query", public_headers, {"query": "", "pageSize": 500})
        print(f"\n== verification: catalog now reports totalSize={verify.get('totalSize')} ==")

        expected_total = len(existing_products) + len(new_products)
        ok = verify.get("totalSize") == expected_total
        # Delta-ingestion evidence: prefer the enrichment cache's reusedFromCache count when the
        # (optional, off-by-default) LLM enrichment toggle is on; otherwise fall back to the
        # vector index's reused/embedded split, which is always computed regardless of the
        # enrichment toggle and is equally valid evidence that only the new products were
        # actually (re)processed.
        vector = result.get("vectorIndexed") or {}
        if enrichment.get("reusedFromCache") is not None:
            reused_ok = enrichment.get("reusedFromCache") == len(existing_products)
            reused_detail = f"enrichment reusedFromCache={enrichment.get('reusedFromCache')}"
        else:
            reused_ok = vector.get("reused") == len(existing_products) and vector.get("embedded") == len(new_products)
            reused_detail = f"vector index reused={vector.get('reused')} embedded={vector.get('embedded')} (enrichment disabled: {enrichment.get('reason') or 'ai_toggles.enrich is off'})"
        print(f"catalog size check: {'PASS' if ok else 'FAIL'} (expected {expected_total})")
        print(f"delta-ingestion cache check: {'PASS' if reused_ok else 'FAIL'} ({reused_detail}, expected {len(existing_products)} untouched)")

        # Spot-check one new category renders and searches correctly.
        spot = await post_json(session, f"{base}/search/query", public_headers, {"query": "memory card", "pageSize": 10})
        spot_ids = [row.get("id") for row in (spot.get("results") or [])]
        spot_ok = any(pid and str(pid).startswith("SKU-MEM-") for pid in spot_ids)
        print(f"spot-check 'memory card' search: {'PASS' if spot_ok else 'FAIL'} (found: {spot_ids})")

        return 0 if (ok and reused_ok and spot_ok) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="https://search-api.retail.demos.wavefunctionlabs.com", help="wavesearch-api base URL")
    parser.add_argument("--sts-url", default="https://sts.retail.demos.wavefunctionlabs.com", help="wave-sts base URL")
    parser.add_argument("--admin-user", default="search.admin", help="wave-sts username with search.ingest scope")
    parser.add_argument("--admin-password", default="demo123!", help="wave-sts password for --admin-user")
    parser.add_argument("--tenant", default="demo-tenant", help="X-Tenant-Id header value")
    args = parser.parse_args()
    exit_code = asyncio.run(run(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
