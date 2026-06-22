from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp


QUERIES = [
    "coffee drinks",
    "hardware drill",
    "sportswear trainers",
    "food snack",
    "outerwear jacket",
    "garden smart",
    "generated loadtest",
    "premium compact",
    "Pico Goods",
    "Contoso trail",
]


@dataclass
class Timings:
    values: list[float] = field(default_factory=list)

    def add(self, seconds: float) -> None:
        self.values.append(seconds * 1000.0)

    def summary(self) -> dict[str, float]:
        if not self.values:
            return {"count": 0}
        ordered = sorted(self.values)
        return {
            "count": len(ordered),
            "min_ms": round(ordered[0], 2),
            "mean_ms": round(statistics.mean(ordered), 2),
            "p50_ms": round(ordered[int(len(ordered) * 0.50)], 2),
            "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1], 2),
            "p99_ms": round(ordered[int(len(ordered) * 0.99) - 1], 2),
            "max_ms": round(ordered[-1], 2),
        }


async def timed(timings: Timings, coro):
    start = time.perf_counter()
    result = await coro
    timings.add(time.perf_counter() - start)
    return result


async def post_json(session: aiohttp.ClientSession, url: str, payload: Any) -> Any:
    async with session.post(url, json=payload) as response:
        response.raise_for_status()
        return await response.json()


async def get_json(session: aiohttp.ClientSession, url: str) -> Any:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()


async def upload_csv(session: aiohttp.ClientSession, url: str, count: int) -> Any:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["sku", "title", "description", "category", "brand", "tags", "price", "inventory"])
    writer.writeheader()
    for i in range(count):
        writer.writerow(
            {
                "sku": f"CSV{i:05d}",
                "title": f"CSV Generated Product {i}",
                "description": f"CSV generated product {i} for upload and sync benchmark",
                "category": ["food", "sportswear", "drinks", "hardware"][i % 4],
                "brand": ["Contoso", "Northwind", "Fabrikam", "Litware"][i % 4],
                "tags": "csv generated loadtest",
                "price": f"{1.99 + (i % 250):.2f}",
                "inventory": str((i * 17) % 5000),
            }
        )
    form = aiohttp.FormData()
    form.add_field("file", buf.getvalue().encode("utf-8"), filename="products.csv", content_type="text/csv")
    async with session.post(url, data=form) as response:
        response.raise_for_status()
        return await response.json()


async def worker(name: str, session: aiohttp.ClientSession, base: str, requests: int, sku_count: int, timings: dict[str, Timings]) -> None:
    rng = random.Random(name)
    sku_limit = max(1, sku_count)
    for _ in range(requests):
        choice = rng.random()
        if choice < 0.70:
            query = rng.choice(QUERIES)
            await timed(timings["search"], post_json(session, f"{base}/api/retail/search", {"query": query}))
        elif choice < 0.86:
            sku = f"SKU{rng.randrange(0, sku_limit):05d}"
            await timed(timings["product"], get_json(session, f"{base}/api/product-service/products/{sku}"))
        elif choice < 0.94:
            await timed(timings["list"], get_json(session, f"{base}/api/product-service/products?offset={rng.randrange(0, max(1, sku_limit - 25))}&limit=25"))
        else:
            sku = f"SKU{rng.randrange(0, sku_limit):05d}"
            await timed(timings["cart"], post_json(session, f"{base}/api/retail/cart", {"cartId": f"bench-{name}", "productId": sku, "quantity": 1}))


async def main() -> None:
    parser = argparse.ArgumentParser(description="PicoStack retail product/search load test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--requests", type=int, default=2000)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--csv-upload-count", type=int, default=0)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    timings = {name: Timings() for name in ["generate", "upload", "search", "product", "list", "cart"]}
    connector = aiohttp.TCPConnector(limit=args.concurrency * 2)
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print(f"Generating and syncing {args.count} products...")
        gen = await timed(timings["generate"], post_json(session, f"{base}/api/product-service/products:generate", {"count": args.count, "seed": 42}))
        print(json.dumps(gen, indent=2)[:1000])
        if args.csv_upload_count:
            print(f"Uploading {args.csv_upload_count} CSV products...")
            up = await timed(timings["upload"], upload_csv(session, f"{base}/api/product-service/products:upload", args.csv_upload_count))
            print(json.dumps(up, indent=2)[:1000])

        per_worker = max(1, args.requests // args.concurrency)
        started = time.perf_counter()
        await asyncio.gather(
            *(worker(str(i), session, base, per_worker, args.count, timings) for i in range(args.concurrency))
        )
        elapsed = time.perf_counter() - started

    total_requests = per_worker * args.concurrency
    print("\nBenchmark summary")
    print(json.dumps({name: timing.summary() for name, timing in timings.items()}, indent=2))
    print(json.dumps({"total_requests": total_requests, "elapsed_s": round(elapsed, 2), "rps": round(total_requests / elapsed, 2)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
