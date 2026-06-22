from __future__ import annotations

import argparse
import csv
import io
import json
import random
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response as FastResponse

from picoweb_core import dispatch, parse_request
from src.retail_demo_server import ROOT, RetailBridge, make_routes
from src.retail_voice_bridge import RetailBrowserVoiceBridge, retail_voice_settings_from_env
from src.retail_voice_tools import RetailVoiceToolContext, TOOL_DEFINITIONS


def create_app(library: Path | None = None, store: Path | None = None, seed: bool = True) -> FastAPI:
    bridge = RetailBridge(library or ROOT / "build" / "libpicostack_retail_demo.so", store or Path(tempfile.gettempdir()) / "picostack-retail-demo")
    if seed:
        bridge.ingest()
    routes = make_routes(bridge)
    tools = RetailVoiceToolContext(bridge)
    app = FastAPI(title="PicoStack Retail Voice Demo")

    def sync_products(products: list[dict[str, Any]]) -> dict[str, Any]:
        synced = 0
        errors: list[dict[str, Any]] = []
        for index, product in enumerate(products):
            result = bridge.upsert_product(product, persist=False)
            if "error" in result:
                errors.append({"index": index, "error": result["error"]})
                continue
            synced += 1
        persist = bridge.persist_index()
        if "error" in persist:
            errors.append({"index": -1, "error": persist["error"]})
        return {"synced": synced, "errors": errors, "persisted": "error" not in persist}

    def generated_products(count: int, seed_value: int) -> list[dict[str, Any]]:
        rng = random.Random(seed_value)
        categories = ["food", "sportswear", "drinks", "hardware", "outerwear", "home", "garden", "electronics"]
        brands = ["Contoso", "Northwind", "Fabrikam", "Litware", "Adventure Works", "Pico Goods"]
        nouns = ["jacket", "trainer", "coffee", "drill", "snack", "bottle", "lamp", "glove", "saw", "pack"]
        adjectives = ["urban", "summit", "premium", "compact", "trail", "fresh", "spark", "pro", "daily", "smart"]
        products = []
        for i in range(count):
            category = categories[i % len(categories)]
            brand = brands[i % len(brands)]
            noun = nouns[i % len(nouns)]
            adjective = adjectives[(i * 7) % len(adjectives)]
            sku = f"SKU{i:05d}"
            products.append(
                {
                    "sku": sku,
                    "title": f"{brand} {adjective.title()} {noun.title()} {i}",
                    "description": f"Generated {category} product {sku} for PicoWAL load testing with {adjective} {noun} search terms.",
                    "category": category,
                    "brand": brand,
                    "tags": [category, adjective, noun, "generated", "loadtest"],
                    "price": round(rng.uniform(1.5, 499.0), 2),
                    "inventory": rng.randint(0, 5000),
                }
            )
        return products

    @app.get("/api/retail/voice/config")
    async def voice_config() -> dict[str, Any]:
        return {
            "enabled": retail_voice_settings_from_env() is not None,
            "websocket": "/ws/browser-voice",
            "tools": TOOL_DEFINITIONS,
        }

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/product-service/products")
    async def product_service_products(offset: int = 0, limit: int = 50) -> dict[str, Any]:
        return bridge.products_page(offset, limit)

    @app.get("/api/product-service/products/{sku}")
    async def product_service_product(sku: str) -> dict[str, Any]:
        return bridge.product(sku)

    @app.post("/api/product-service/products")
    async def product_service_post(payload: dict[str, Any]) -> dict[str, Any]:
        products = payload.get("products") if isinstance(payload, dict) else None
        if isinstance(products, list):
            return sync_products(products)
        return sync_products([payload])

    @app.post("/api/product-service/products:sync")
    async def product_service_sync(payload: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
        products = payload if isinstance(payload, list) else payload.get("products", [])
        if not isinstance(products, list):
            return {"synced": 0, "errors": [{"index": -1, "error": "products must be a list"}], "persisted": False}
        return sync_products(products)

    @app.post("/api/product-service/products:generate")
    async def product_service_generate(payload: dict[str, Any]) -> dict[str, Any]:
        count = max(1, min(8000, int(payload.get("count") or 5000)))
        seed_value = int(payload.get("seed") or 42)
        return sync_products(generated_products(count, seed_value)) | {"generated": count, "seed": seed_value}

    @app.post("/api/product-service/products:upload")
    async def product_service_upload(file: UploadFile = File(...)) -> dict[str, Any]:
        data = await file.read()
        name = (file.filename or "").lower()
        if name.endswith(".csv"):
            text = data.decode("utf-8-sig")
            products = list(csv.DictReader(io.StringIO(text)))
        else:
            payload = json.loads(data.decode("utf-8"))
            products = payload if isinstance(payload, list) else payload.get("products", [])
        return sync_products(products)

    @app.websocket("/ws/browser-voice")
    async def browser_voice(websocket: WebSocket) -> None:
        settings = retail_voice_settings_from_env()
        await websocket.accept()
        if settings is None:
            await websocket.send_text(json.dumps({"type": "error", "error": "Set VOICE_LIVE_ENDPOINT and credentials to enable retail voice."}))
            await websocket.close(code=1011)
            return
        bridge_runner = RetailBrowserVoiceBridge(websocket, settings, tools)
        try:
            await bridge_runner.run()
        except WebSocketDisconnect:
            return
        except Exception as exc:
            await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
            await websocket.close(code=1011)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD"])
    async def pico_dispatch(path: str, request: Request) -> FastResponse:
        body = await request.body()
        raw_path = "/" + path
        if request.url.query:
            raw_path += "?" + request.url.query
        pico_request = parse_request(request.method, raw_path, dict(request.headers), body)
        pico_response = dispatch(routes, pico_request)
        return FastResponse(
            content=pico_response.body,
            status_code=pico_response.status,
            media_type=pico_response.content_type,
            headers={k: v for k, v in pico_response.headers.items() if k.lower() != "content-type"},
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="PicoStack retail ASGI + Voice Live demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--library", type=Path, default=ROOT / "build" / "libpicostack_retail_demo.so")
    parser.add_argument("--store", type=Path, default=Path(tempfile.gettempdir()) / "picostack-retail-demo")
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(create_app(args.library, args.store, seed=not args.no_seed), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
