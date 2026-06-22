from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException

from .auth import TokenIssuer, require_scope
from .blob_store import LocalBlobStore
from .models import TenantContext
from .services import RetailV2Service


ROOT = Path(__file__).resolve().parents[2]


def create_service() -> RetailV2Service:
    data_root = Path(os.environ.get("RETAIL_V2_DEMO_BLOB_ROOT") or Path(tempfile.gettempdir()) / "retail-v2-demo-blobs")
    catalog_path = Path(os.environ.get("RETAIL_V2_CATALOG") or ROOT / "V2" / "sample-catalog.json")
    return RetailV2Service(LocalBlobStore(data_root), catalog_path)


def create_app(service: RetailV2Service | None = None) -> FastAPI:
    app = FastAPI(title="Retail Search V2 Demo")
    service = service or create_service()
    issuer = TokenIssuer(issuer="retail-v2-demo", secret=os.environ.get("RETAIL_V2_STS_SECRET", "dev-secret"))

    def current_tenant(authorization: Annotated[str | None, Header()] = None, x_tenant_id: Annotated[str | None, Header()] = None) -> TenantContext:
        if authorization and authorization.lower().startswith("bearer "):
            try:
                return issuer.verify(authorization.split(" ", 1)[1])
            except ValueError as exc:
                raise HTTPException(status_code=401, detail=str(exc)) from exc
        return TenantContext(tenant_id=x_tenant_id or "demo-tenant", scopes=frozenset({"admin", "search.query", "events.write", "inventory.write"}))

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.post("/v2/auth/token")
    async def token(payload: dict) -> dict:
        tenant = str(payload.get("tenant") or "demo-tenant")
        subject = str(payload.get("subject") or "demo-user")
        scopes = payload.get("scopes") or ["search.query", "events.write"]
        return {"access_token": issuer.issue(subject, tenant, list(scopes)), "token_type": "Bearer"}

    @app.get("/v2/status")
    async def status(context: TenantContext = Depends(current_tenant)) -> dict:
        return {"tenant": context.tenant_id} | service.status()

    @app.get("/v2/partition/{key}")
    async def partition(key: str, context: TenantContext = Depends(current_tenant)) -> dict:
        route = service.route(context, key)
        return route.__dict__

    @app.get("/v2/catalog/products")
    async def products(offset: int = 0, limit: int = 50, context: TenantContext = Depends(current_tenant)) -> dict:
        require_scope(context, "search.query")
        return service.products(offset, limit)

    @app.get("/v2/catalog/products/{product_id}")
    async def product(product_id: str, context: TenantContext = Depends(current_tenant)) -> dict:
        require_scope(context, "search.query")
        result = service.product(product_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result)
        return result

    @app.post("/v2/search")
    async def search(payload: dict, context: TenantContext = Depends(current_tenant)) -> dict:
        require_scope(context, "search.query")
        return service.search(str(payload.get("query") or ""), int(payload.get("pageSize") or 10))

    @app.post("/v2/recommend")
    async def recommend(payload: dict, context: TenantContext = Depends(current_tenant)) -> dict:
        require_scope(context, "search.query")
        return service.recommend(payload.get("productId"), int(payload.get("pageSize") or 10))

    @app.post("/v2/userEvents:write")
    async def event_write(payload: dict, context: TenantContext = Depends(current_tenant)) -> dict:
        require_scope(context, "events.write")
        return service.append_event(context, payload)

    @app.post("/v2/inventory:set")
    async def inventory_set(payload: dict, context: TenantContext = Depends(current_tenant)) -> dict:
        require_scope(context, "inventory.write")
        return service.update_inventory(context, payload)

    @app.post("/v2/rules")
    async def rules(payload: dict, context: TenantContext = Depends(current_tenant)) -> dict:
        require_scope(context, "admin")
        return service.append_rule(context, payload)

    return app
