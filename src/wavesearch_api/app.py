from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, Header, HTTPException

from retail_v2.blob_store import LocalBlobStore
from retail_v2.models import TenantContext
from retail_v2.services import RetailV2Service
from wave_shared.auth import context_from_auth, require_scope


ROOT = Path(__file__).resolve().parents[2]


def create_service() -> RetailV2Service:
    data_root = Path(os.environ.get("WAVESEARCH_BLOB_ROOT") or Path(tempfile.gettempdir()) / "wavesearch-api-blobs")
    catalog_path = Path(os.environ.get("WAVESEARCH_CATALOG") or ROOT / "V2" / "sample-catalog.json")
    store = LocalBlobStore(data_root)
    return RetailV2Service(store, catalog_path)


def _write_catalog_snapshot(products: list[dict[str, Any]]) -> Path:
    tmp = Path(tempfile.gettempdir()) / f"wavesearch-ingest-{os.getpid()}.json"
    tmp.write_text(json.dumps({"products": products}, ensure_ascii=True, indent=2), encoding="utf-8")
    return tmp


def _fetch_erp_catalog(url: str, tenant_id: str, token: str | None = None) -> list[dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    headers["X-Tenant-Id"] = tenant_id
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as response:  # nosec B310 - trusted demo configuration endpoint
        payload = json.loads(response.read().decode("utf-8"))
    products = payload.get("products") if isinstance(payload, dict) else None
    if not isinstance(products, list):
        raise ValueError("ERP catalog response missing products[]")
    return products


def create_app(service: RetailV2Service | None = None) -> FastAPI:
    app = FastAPI(title="WaveSearch Labs Retail Search API")
    service = service or create_service()

    def search_context(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> TenantContext:
        return context_from_auth("wavesearch-api", authorization=authorization, x_tenant_id=x_tenant_id, require_tenant_header=True)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavesearch-api"}

    @app.post("/search/query")
    async def search_query(payload: dict[str, Any], context: TenantContext = Depends(search_context)) -> dict[str, Any]:
        require_scope(context, "search.query")
        return service.search(str(payload.get("query") or ""), int(payload.get("pageSize") or 10))

    @app.post("/search/recommend")
    async def search_recommend(payload: dict[str, Any], context: TenantContext = Depends(search_context)) -> dict[str, Any]:
        require_scope(context, "search.query")
        return service.recommend(payload.get("productId"), int(payload.get("pageSize") or 10))

    @app.post("/search/events")
    async def search_events(
        payload: dict[str, Any],
        context: TenantContext = Depends(search_context),
        x_retail_partition_key: Annotated[str | None, Header(alias="X-Retail-Partition-Key")] = None,
    ) -> dict[str, Any]:
        require_scope(context, "events.write")
        return service.append_event(context, payload, x_retail_partition_key)

    @app.get("/search/admin/analytics")
    async def admin_analytics(context: TenantContext = Depends(search_context)) -> dict[str, Any]:
        require_scope(context, "search.admin")
        return service.analytics_summary(context)

    @app.get("/search/admin/config")
    async def admin_config(context: TenantContext = Depends(search_context)) -> dict[str, Any]:
        require_scope(context, "search.admin")
        return service.get_admin_config(context)

    @app.post("/search/admin/rules")
    async def admin_rules(
        payload: dict[str, Any],
        context: TenantContext = Depends(search_context),
        x_retail_partition_key: Annotated[str | None, Header(alias="X-Retail-Partition-Key")] = None,
    ) -> dict[str, Any]:
        require_scope(context, "search.admin")
        return service.append_rule(context, payload, x_retail_partition_key)

    @app.post("/search/ingest/catalog")
    async def ingest_catalog(payload: dict[str, Any], context: TenantContext = Depends(search_context)) -> dict[str, Any]:
        require_scope(context, "search.ingest")
        products = payload.get("products") if isinstance(payload.get("products"), list) else []
        if not products:
            raise HTTPException(status_code=400, detail="products[] is required")
        snapshot = _write_catalog_snapshot(products)
        result = service.rebuild_runtime({"catalogPath": str(snapshot)})
        return {"accepted": "error" not in result, **result}

    @app.post("/search/ingest/from-erp")
    async def ingest_from_erp(payload: dict[str, Any], context: TenantContext = Depends(search_context)) -> dict[str, Any]:
        require_scope(context, "search.ingest")
        erp_catalog_url = str(payload.get("erpCatalogUrl") or "").strip()
        erp_token = str(payload.get("erpToken") or "").strip() or None
        if not erp_catalog_url:
            raise HTTPException(status_code=400, detail="erpCatalogUrl is required")
        if not erp_token:
            raise HTTPException(status_code=400, detail="erpToken is required")
        try:
            products = _fetch_erp_catalog(erp_catalog_url, context.tenant_id, erp_token)
        except Exception as exc:  # surfaced as explicit API error
            raise HTTPException(status_code=400, detail=f"ERP fetch failed: {exc}") from exc
        snapshot = _write_catalog_snapshot(products)
        result = service.rebuild_runtime({"catalogPath": str(snapshot)})
        return {"accepted": "error" not in result, "ingestedCount": len(products), **result}

    return app
