"""Adds a second wave of demo products to the WaveSearch catalog, this time populating
subcategories that don't yet exist under the existing top-level departments (rather than adding
more items to already-represented subcategories) -- and runs the real LLM enrichment pass on
just these new products (existing products are unaffected: same delta-ingestion cache-hit
behavior as scripts/add_demo_products.py).

New subcategories added (6 products each, 36 total):
    Electronics > Wearables      (smartwatches, fitness trackers)
    Clothing > Bottoms           (jeans, chinos)
    Footwear > Sandals           (sandals, flip-flops)
    Home > Furniture             (small furniture: stools, side tables)
    Grocery > Snacks             (crisps, chocolate, nuts)
    Outdoor > Camping            (tents, sleeping bags, camping stoves)

Enrichment: the ai_toggles["enrich"] LLM enrichment pass is normally left OFF in this deployment
(cost control -- see wavesearch_api/app.py ai_toggles defaults), so this script temporarily
enables it for the single ingest call that adds these products, then restores whatever the
enrich toggle's previous state was. Because /search/ingest/catalog's enrichment cache matches
existing products by content hash, only the 36 new products actually get an LLM call -- the rest
of the (unchanged) catalog is skipped exactly like the non-enrichment delta-ingestion path.

Usage:
    python scripts/add_more_demo_products.py --base-url https://search-api.retail.demos.wavefunctionlabs.com
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

    wearables = [
        ("Fitness Tracker Band", "Slim wrist-worn fitness tracker with heart rate monitoring", "black", 39.99, 60),
        ("Smartwatch Series Basic", "Everyday smartwatch with notifications and step tracking", "silver", 89.99, 45),
        ("GPS Running Watch", "GPS-enabled sports watch for runners and cyclists", "blue", 129.99, 30),
        ("Sleep Tracking Ring", "Compact sleep and recovery tracking ring", "black", 199.99, 20),
        ("Kids Activity Tracker", "Durable activity tracker designed for children", "pink", 24.99, 35),
        ("Hybrid Smartwatch", "Analog-style smartwatch with 2-week battery life", "brown", 149.99, 25),
    ]
    for i, (title, desc, color, price, qty) in enumerate(wearables, start=1):
        new_products.append(_product(f"SKU-WEAR-{i:03d}", title, desc, "Electronics > Wearables", "Pulseline", price, color, "Wearable", qty))

    jeans = [
        ("Slim Fit Jeans", "Classic slim fit denim jeans", "indigo", 39.99, 80),
        ("Straight Leg Jeans", "Timeless straight leg denim jeans", "dark blue", 42.99, 75),
        ("Relaxed Fit Chinos", "Comfortable relaxed fit chino trousers", "khaki", 34.99, 65),
        ("Skinny Jeans", "Stretch skinny fit denim jeans", "black", 37.99, 70),
        ("Bootcut Jeans", "Classic bootcut denim jeans", "mid blue", 41.99, 55),
        ("Cargo Trousers", "Utility cargo trousers with multiple pockets", "olive", 44.99, 50),
    ]
    for i, (title, desc, color, price, qty) in enumerate(jeans, start=1):
        new_products.append(_product(f"SKU-JEAN-{i:03d}", title, desc, "Clothing > Bottoms", "Denimworks", price, color, "Apparel", qty))

    sandals = [
        ("Classic Flip-Flops", "Lightweight everyday flip-flop sandals", "black", 9.99, 100),
        ("Sport Sandals", "Adjustable strap sport sandals for outdoor wear", "grey", 24.99, 70),
        ("Leather Slide Sandals", "Comfortable leather slide sandals", "brown", 29.99, 55),
        ("Beach Sandals", "Quick-dry beach sandals", "blue", 14.99, 85),
        ("Orthotic Comfort Sandals", "Supportive sandals with cushioned footbed", "tan", 34.99, 45),
        ("Kids Sandals", "Durable adjustable sandals for children", "red", 12.99, 60),
    ]
    for i, (title, desc, color, price, qty) in enumerate(sandals, start=1):
        new_products.append(_product(f"SKU-SAND-{i:03d}", title, desc, "Footwear > Sandals", "Stridewell", price, color, "Footwear", qty))

    furniture = [
        ("Wooden Side Table", "Compact wooden side table for living rooms", "oak", 49.99, 25),
        ("Folding Stool", "Portable folding stool for extra seating", "black", 19.99, 40),
        ("Storage Ottoman", "Upholstered storage ottoman with hidden compartment", "grey", 59.99, 20),
        ("Bookshelf 3-Tier", "Compact 3-tier bookshelf for small spaces", "white", 69.99, 18),
        ("Accent Armchair", "Compact accent armchair for reading nooks", "mustard", 149.99, 12),
        ("Coat Rack Stand", "Freestanding coat and hat rack stand", "black", 34.99, 30),
    ]
    for i, (title, desc, color, price, qty) in enumerate(furniture, start=1):
        new_products.append(_product(f"SKU-FURN-{i:03d}", title, desc, "Home > Furniture", "Homestead", price, color, "Furniture", qty))

    snacks = [
        ("Sea Salt Crisps 150g", "Crunchy sea salt flavoured potato crisps", "yellow", 1.49, 150),
        ("Milk Chocolate Bar 100g", "Classic smooth milk chocolate bar", "brown", 1.99, 200),
        ("Mixed Nuts 200g", "Roasted and salted mixed nuts", "brown", 3.49, 90),
        ("Popcorn Sharing Bag", "Lightly salted popcorn sharing bag", "yellow", 2.29, 110),
        ("Dried Fruit Mix 150g", "Assorted dried fruit snack mix", "orange", 2.99, 80),
        ("Pretzel Sticks 200g", "Crunchy salted pretzel sticks", "brown", 1.79, 100),
    ]
    for i, (title, desc, color, price, qty) in enumerate(snacks, start=1):
        new_products.append(_product(f"SKU-SNACK-{i:03d}", title, desc, "Grocery > Snacks", "Fizzwell", price, color, "Snack", qty))

    camping = [
        ("2-Person Dome Tent", "Lightweight waterproof dome tent for two", "green", 79.99, 20),
        ("Sleeping Bag 3-Season", "Insulated sleeping bag rated for three seasons", "navy", 44.99, 30),
        ("Portable Camping Stove", "Compact single-burner camping stove", "silver", 34.99, 25),
        ("Camping Lantern LED", "Rechargeable LED camping lantern", "black", 19.99, 40),
        ("Insulated Camping Mat", "Lightweight insulated sleeping mat", "grey", 24.99, 35),
        ("Collapsible Camping Chair", "Portable folding camping chair with cup holder", "orange", 29.99, 28),
    ]
    for i, (title, desc, color, price, qty) in enumerate(camping, start=1):
        new_products.append(_product(f"SKU-CAMP-{i:03d}", title, desc, "Outdoor > Camping", "TrailForge", price, color, "Outdoor", qty))

    return new_products


async def run(args: argparse.Namespace) -> int:
    base = args.base_url.rstrip("/")
    public_headers = {"X-Tenant-Id": args.tenant}
    async with aiohttp.ClientSession() as session:
        admin_token = await fetch_admin_token(session, args.sts_url, args.admin_user, args.admin_password, args.tenant)
        admin_headers = {"X-Tenant-Id": args.tenant, "Authorization": f"Bearer {admin_token}"}
        print(f"authenticated as {args.admin_user!r} against {args.sts_url}")

        config_before = await get_json(session, f"{base}/search/admin/config", admin_headers)
        enrich_was_enabled = bool((config_before.get("ai") or {}).get("enrichEnabled"))
        print(f"current enrichEnabled={enrich_was_enabled} (will temporarily enable for this ingest, then restore)")

        baseline = await post_json(session, f"{base}/search/query", public_headers, {"query": "", "pageSize": 500})
        existing_products = [row["product"] for row in (baseline.get("results") or []) if isinstance(row.get("product"), dict)]
        print(f"fetched {len(existing_products)} existing products (reported totalSize={baseline.get('totalSize')})")

        new_products = build_new_products()
        print(f"generated {len(new_products)} new products across NEW subcategories: wearables, bottoms, sandals, furniture, snacks, camping")

        if not enrich_was_enabled:
            await post_json(session, f"{base}/search/admin/ai-toggle", admin_headers, {"enrichEnabled": True})
            print("enrichEnabled temporarily set to True for this ingest")

        try:
            merged = existing_products + new_products
            print(f"\n== ingesting merged catalog ({len(merged)} products), running LLM enrichment on the new 36 ==")
            result = await post_json(session, f"{base}/search/ingest/catalog", admin_headers, {"products": merged})
            enrichment = result.get("enrichment") or {}
            print(f"accepted={result.get('accepted')}  ingestedCount={result.get('ingestedCount')}")
            print(f"enrichment: applied={enrichment.get('applied')}  reusedFromCache={enrichment.get('reusedFromCache')}  reason={enrichment.get('reason')}")
            if "vectorIndexed" in result:
                print(f"vector index: {result['vectorIndexed']}")
        finally:
            if not enrich_was_enabled:
                await post_json(session, f"{base}/search/admin/ai-toggle", admin_headers, {"enrichEnabled": False})
                print("enrichEnabled restored to False")

        verify = await post_json(session, f"{base}/search/query", public_headers, {"query": "", "pageSize": 500})
        expected_total = len(existing_products) + len(new_products)
        ok = verify.get("totalSize") == expected_total
        reused_ok = enrichment.get("reusedFromCache") == len(existing_products)
        enriched_ok = enrichment.get("applied") is True
        print(f"\ncatalog size check: {'PASS' if ok else 'FAIL'} (expected {expected_total}, got {verify.get('totalSize')})")
        print(f"delta-ingestion cache check: {'PASS' if reused_ok else 'FAIL'} (expected {len(existing_products)} reused)")
        print(f"enrichment-applied check: {'PASS' if enriched_ok else 'FAIL'}")

        # Spot-check a couple of the new subcategories, and confirm LLM enrichment actually
        # generated tags for a new product (raw seed data starts with tags: []).
        spot = await post_json(session, f"{base}/search/query", public_headers, {"query": "camping tent", "pageSize": 5})
        spot_ids = [row.get("id") for row in (spot.get("results") or [])]
        spot_ok = any(pid and str(pid).startswith("SKU-CAMP-") for pid in spot_ids)
        print(f"spot-check 'camping tent' search: {'PASS' if spot_ok else 'FAIL'} (found: {spot_ids})")

        sample_row = next((row for row in (verify.get("results") or []) if str(row.get("id")) == "SKU-WEAR-001"), None)
        sample_tags = ((sample_row or {}).get("product") or {}).get("tags") or []
        tags_ok = len(sample_tags) > 0
        print(f"enrichment tags check on SKU-WEAR-001: {'PASS' if tags_ok else 'FAIL'} ({len(sample_tags)} tags: {sample_tags[:5]})")

        return 0 if (ok and reused_ok and enriched_ok and spot_ok and tags_ok) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="https://search-api.retail.demos.wavefunctionlabs.com", help="wavesearch-api base URL")
    parser.add_argument("--sts-url", default="https://sts.retail.demos.wavefunctionlabs.com", help="wave-sts base URL")
    parser.add_argument("--admin-user", default="search.admin", help="wave-sts username with search.ingest/search.admin scope")
    parser.add_argument("--admin-password", default="demo123!", help="wave-sts password for --admin-user")
    parser.add_argument("--tenant", default="demo-tenant", help="X-Tenant-Id header value")
    args = parser.parse_args()
    exit_code = asyncio.run(run(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
