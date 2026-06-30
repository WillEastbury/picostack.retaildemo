from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header

from wave_shared.auth import context_from_auth, require_scope


@dataclass
class ERPState:
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    stock: dict[str, dict[str, Any]] = field(default_factory=dict)
    pricing: dict[str, dict[str, Any]] = field(default_factory=dict)
    offers: dict[str, dict[str, Any]] = field(default_factory=dict)
    customers: dict[str, dict[str, Any]] = field(default_factory=dict)
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    invoices: dict[str, dict[str, Any]] = field(default_factory=dict)


class ERPStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = ERPState()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.state = ERPState(**{k: payload.get(k, {}) for k in ERPState.__dataclass_fields__.keys()})

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.state.__dict__, indent=2), encoding="utf-8")


def create_app() -> FastAPI:
    app = FastAPI(title="WaveStore ERP API")
    store = ERPStore(Path(os.environ.get("WAVESTORE_ERP_DATA") or (Path(os.getenv("TEMP") or ".") / "wavestore-erp-state.json")))

    def erp_context(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ):
        return context_from_auth("wavestore-erp-api", authorization=authorization, x_tenant_id=x_tenant_id, require_tenant_header=True)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavestore-erp-api"}

    @app.get("/erp/products")
    async def list_products(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"products": sorted(store.state.products.values(), key=lambda p: p.get("id", ""))}

    @app.post("/erp/products")
    async def upsert_product(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        product_id = str(payload.get("id") or payload.get("sku") or "").strip()
        if not product_id:
            return {"error": "id is required"}
        merged = {"id": product_id, **payload}
        store.state.products[product_id] = merged
        if product_id not in store.state.stock:
            store.state.stock[product_id] = {"productId": product_id, "availableQuantity": int(payload.get("availableQuantity") or 0), "availability": str(payload.get("availability") or "IN_STOCK")}
        if product_id not in store.state.pricing:
            price = payload.get("price")
            if price is None and isinstance(payload.get("priceInfo"), dict):
                price = payload["priceInfo"].get("price")
            store.state.pricing[product_id] = {"productId": product_id, "price": float(price or 0.0), "currencyCode": str(payload.get("currencyCode") or "GBP")}
        store._save()
        return {"accepted": True, "product": merged}

    @app.get("/erp/stock")
    async def list_stock(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"stock": sorted(store.state.stock.values(), key=lambda s: s.get("productId", ""))}

    @app.post("/erp/stock:set")
    async def set_stock(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        product_id = str(payload.get("productId") or "").strip()
        if not product_id:
            return {"error": "productId is required"}
        row = {
            "productId": product_id,
            "availableQuantity": int(payload.get("availableQuantity") or 0),
            "availability": str(payload.get("availability") or ("OUT_OF_STOCK" if int(payload.get("availableQuantity") or 0) <= 0 else "IN_STOCK")),
        }
        store.state.stock[product_id] = row
        store._save()
        return {"accepted": True, "stock": row}

    @app.get("/erp/pricing")
    async def list_pricing(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"pricing": sorted(store.state.pricing.values(), key=lambda s: s.get("productId", ""))}

    @app.post("/erp/pricing")
    async def upsert_pricing(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        product_id = str(payload.get("productId") or "").strip()
        if not product_id:
            return {"error": "productId is required"}
        row = {"productId": product_id, "price": float(payload.get("price") or 0.0), "currencyCode": str(payload.get("currencyCode") or "GBP")}
        store.state.pricing[product_id] = row
        store._save()
        return {"accepted": True, "pricing": row}

    @app.get("/erp/offers")
    async def list_offers(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"offers": sorted(store.state.offers.values(), key=lambda s: s.get("id", ""))}

    @app.post("/erp/offers")
    async def upsert_offer(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        offer_id = str(payload.get("id") or f"offer-{uuid4().hex[:8]}")
        row = {"id": offer_id, **payload}
        store.state.offers[offer_id] = row
        store._save()
        return {"accepted": True, "offer": row}

    @app.get("/erp/customers")
    async def list_customers(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"customers": sorted(store.state.customers.values(), key=lambda c: c.get("id", ""))}

    @app.post("/erp/customers")
    async def upsert_customer(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        customer_id = str(payload.get("id") or f"cust-{uuid4().hex[:8]}")
        row = {"id": customer_id, **payload}
        store.state.customers[customer_id] = row
        store._save()
        return {"accepted": True, "customer": row}

    @app.get("/erp/orders")
    async def list_orders(customerId: str | None = None, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        rows = list(store.state.orders.values())
        if customerId:
            rows = [row for row in rows if str(row.get("customerId") or "") == customerId]
        rows.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return {"orders": rows}

    @app.post("/erp/orders")
    async def place_order(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.order")
        customer_id = str(payload.get("customerId") or "guest")
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        if not items:
            return {"error": "items are required"}
        order_id = f"ord-{uuid4().hex[:10]}"
        total = 0.0
        normalized_items = []
        for item in items:
            product_id = str(item.get("productId") or "")
            qty = max(1, int(item.get("quantity") or 1))
            price = float(store.state.pricing.get(product_id, {}).get("price") or 0.0)
            total += qty * price
            normalized_items.append({"productId": product_id, "quantity": qty, "price": price})
            stock_row = store.state.stock.get(product_id)
            if stock_row:
                stock_row["availableQuantity"] = max(0, int(stock_row.get("availableQuantity") or 0) - qty)
                stock_row["availability"] = "IN_STOCK" if stock_row["availableQuantity"] > 0 else "OUT_OF_STOCK"
        order = {"id": order_id, "customerId": customer_id, "items": normalized_items, "status": "PLACED", "total": round(total, 2), "currencyCode": "GBP", "createdAt": __import__("datetime").datetime.utcnow().isoformat() + "Z"}
        invoice_id = f"inv-{uuid4().hex[:10]}"
        invoice = {"id": invoice_id, "orderId": order_id, "customerId": customer_id, "status": "OPEN", "amount": order["total"], "currencyCode": "GBP", "createdAt": order["createdAt"]}
        store.state.orders[order_id] = order
        store.state.invoices[invoice_id] = invoice
        store._save()
        return {"accepted": True, "order": order, "invoice": invoice}

    @app.get("/erp/invoices")
    async def list_invoices(customerId: str | None = None, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        rows = list(store.state.invoices.values())
        if customerId:
            rows = [row for row in rows if str(row.get("customerId") or "") == customerId]
        rows.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return {"invoices": rows}

    @app.get("/erp/export/catalog")
    async def export_catalog(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.export")
        products = []
        for product_id, product in store.state.products.items():
            stock = store.state.stock.get(product_id, {})
            pricing = store.state.pricing.get(product_id, {})
            products.append({
                "id": product_id,
                "title": str(product.get("title") or product_id),
                "description": str(product.get("description") or ""),
                "categories": list(product.get("categories") or []),
                "brands": list(product.get("brands") or []),
                "tags": list(product.get("tags") or []),
                "availability": str(stock.get("availability") or product.get("availability") or "IN_STOCK"),
                "availableQuantity": int(stock.get("availableQuantity") or product.get("availableQuantity") or 0),
                "priceInfo": {
                    "price": float(pricing.get("price") or product.get("price") or 0.0),
                    "currencyCode": str(pricing.get("currencyCode") or product.get("currencyCode") or "GBP"),
                },
                "images": list(product.get("images") or []),
            })
        return {"products": products}

    return app
