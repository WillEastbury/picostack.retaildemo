from __future__ import annotations

from pathlib import Path

from .append_log import AppendWriter
from .blob_store import BlobStore
from .models import TenantContext
from .partitioning import PartitionRouter
from .paths import TenantPaths
from .runtime import CatalogRuntime, LiveOverlay, RuntimeBuilder, SearchEngine, load_catalog_file


class RetailV2Service:
    def __init__(self, store: BlobStore, catalog_path: Path, owner_id: str = "local-owner"):
        self.store = store
        self.router = PartitionRouter(owners=(owner_id,))
        self.append_writer = AppendWriter(store, owner_id=owner_id)
        self.runtime: CatalogRuntime = RuntimeBuilder().build(load_catalog_file(catalog_path))
        self.overlay = LiveOverlay()
        self.search_engine = SearchEngine()

    def tenant_paths(self, context: TenantContext) -> TenantPaths:
        return TenantPaths(context.tenant_id, context.branch_id)

    def route(self, context: TenantContext, key: str):
        return self.router.resolve(context, key)

    def products(self, offset: int = 0, limit: int = 50) -> dict:
        items = list(self.runtime.products_by_id.values())
        page = items[offset : offset + limit]
        return {"totalSize": len(items), "offset": offset, "limit": limit, "products": [p.raw for p in page]}

    def product(self, product_id: str) -> dict:
        product = self.runtime.product(product_id)
        if product is None:
            return {"error": "not_found", "id": product_id}
        return product.raw

    def append_event(self, context: TenantContext, payload: dict) -> dict:
        key = str(payload.get("visitorId") or payload.get("sessionId") or payload.get("eventId") or "anonymous")
        route = self.route(context, key)
        result = self.append_writer.append_one(self.tenant_paths(context), "events", route, "event", payload)
        self.overlay.events_seen += 1
        return result

    def update_inventory(self, context: TenantContext, payload: dict) -> dict:
        key = str(payload.get("productId") or payload.get("primaryProductId") or "unknown")
        route = self.route(context, key)
        result = self.append_writer.append_one(self.tenant_paths(context), "inventory", route, "inventory_update", payload)
        self.overlay.inventory[key] = payload
        return result

    def append_rule(self, context: TenantContext, payload: dict) -> dict:
        key = str(payload.get("id") or "control")
        route = self.route(context, key)
        return self.append_writer.append_one(self.tenant_paths(context), "rules", route, "control_update", payload)

    def search(self, query: str, limit: int = 10, filters: dict | None = None) -> dict:
        return self.search_engine.search(self.runtime, query, limit, filters)

    def recommend(self, product_id: str | None = None, limit: int = 10) -> dict:
        return self.search_engine.recommend(self.runtime, product_id, limit)

    def status(self) -> dict:
        return {
            "runtimeVersion": self.runtime.version,
            "productCount": len(self.runtime.products_by_id),
            "eventOverlayCount": self.overlay.events_seen,
            "inventoryOverlayCount": len(self.overlay.inventory),
        }
