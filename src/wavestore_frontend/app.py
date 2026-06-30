from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from retail_v2.auth import TokenIssuer


ROOT = Path(__file__).resolve().parents[2]
TELEMETRY_DEMO = ROOT / "telemetry-demo.html"
FALLBACK_CATALOG = ROOT / "V2" / "sample-catalog.json"
STATIC_DIR = Path(__file__).parent / "static"


def _json_request(url: str, method: str = "GET", body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req_headers = dict(headers or {})
    if body is not None:
        req_headers.setdefault("Content-Type", "application/json")
    req = Request(url=url, method=method, data=payload, headers=req_headers)
    with urlopen(req, timeout=30) as response:  # nosec B310 - trusted demo environment
        return json.loads(response.read().decode("utf-8"))


def _page_mode(path: str) -> str:
    if path.startswith("/product/"):
        return "product"
    if path == "/basket":
        return "basket"
    if path == "/account":
        return "account"
    if path == "/admin-sim":
        return "admin-sim"
    return "home"


def _render_telemetry_page(path: str) -> str:
    html = TELEMETRY_DEMO.read_text(encoding="utf-8")
    return html.replace("{{PAGE_MODE}}", _page_mode(path))


def _fallback_products() -> list[dict[str, Any]]:
    if not FALLBACK_CATALOG.exists():
        return []
    payload = json.loads(FALLBACK_CATALOG.read_text(encoding="utf-8"))
    products = payload.get("products")
    return products if isinstance(products, list) else []


def create_app() -> FastAPI:
    app = FastAPI(title="WaveStore Frontend")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    sts = os.environ.get("WAVE_STS_URL", "http://127.0.0.1:8801")
    search_api = os.environ.get("WAVESEARCH_API_URL", "http://127.0.0.1:8803")
    erp_api = os.environ.get("WAVESTORE_ERP_API_URL", "http://127.0.0.1:8802")

    def tenant_value(x_tenant_id: str | None) -> str:
        return (x_tenant_id or "demo-tenant").strip() or "demo-tenant"

    def issue_token(audience: str, tenant: str, subject: str, scopes: list[str]) -> str:
        local_secret = os.environ.get("WAVE_STS_SECRET")
        if local_secret:
            issuer = TokenIssuer(
                issuer=os.environ.get("WAVE_STS_ISSUER", "wave-sts"),
                secret=local_secret,
                audience=audience,
            )
            return issuer.issue(subject, tenant, scopes, ttl_seconds=900)
        payload = {"audience": audience, "tenant": tenant, "subject": subject, "scopes": scopes}
        try:
            result = _json_request(f"{sts}/sts/token", method="POST", body=payload, headers={"X-Tenant-Id": tenant})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"STS token issue failed: {exc}") from exc
        token = str(result.get("access_token") or "")
        if not token:
            raise HTTPException(status_code=502, detail="STS token issue returned no access_token")
        return token

    def bearer_or_issue(authorization: str | None, audience: str, tenant: str, subject: str, scopes: list[str]) -> str:
        if authorization and authorization.lower().startswith("bearer "):
            return authorization
        return f"Bearer {issue_token(audience, tenant, subject, scopes)}"

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavestore-frontend"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse(_render_telemetry_page("/"))

    @app.get("/basket", response_class=HTMLResponse)
    async def basket_page() -> HTMLResponse:
        return HTMLResponse(_render_telemetry_page("/basket"))

    @app.get("/account", response_class=HTMLResponse)
    async def account_page() -> HTMLResponse:
        return HTMLResponse(_render_telemetry_page("/account"))

    @app.get("/admin-sim", response_class=HTMLResponse)
    async def admin_sim_page() -> HTMLResponse:
        return HTMLResponse(_render_telemetry_page("/admin-sim"))

    @app.get("/product/{product_id}", response_class=HTMLResponse)
    async def product_page(product_id: str) -> HTMLResponse:
        return HTMLResponse(_render_telemetry_page(f"/product/{product_id}"))

    @app.post("/v2/auth/token")
    async def v2_auth_token(payload: dict[str, Any]) -> dict[str, Any]:
        tenant = str(payload.get("tenant") or "demo-tenant")
        subject = str(payload.get("subject") or "wave.user")
        scopes_raw = payload.get("scopes")
        scopes = [str(s) for s in scopes_raw] if isinstance(scopes_raw, list) and scopes_raw else ["search.query", "events.write"]
        token = issue_token("wavesearch-api", tenant, subject, scopes)
        return {"access_token": token, "token_type": "Bearer"}

    @app.post("/v2/auth/login")
    async def v2_auth_login(payload: dict[str, Any]) -> dict[str, Any]:
        tenant = str(payload.get("tenant") or "demo-tenant")
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if not username or not password:
            raise HTTPException(status_code=400, detail="username and password are required")
        scopes_raw = payload.get("scopes")
        scopes = [str(s) for s in scopes_raw] if isinstance(scopes_raw, list) and scopes_raw else ["search.query", "events.write", "erp.read", "erp.order"]
        try:
            login = _json_request(
                f"{sts}/sts/login",
                method="POST",
                body={
                    "tenant": tenant,
                    "username": username,
                    "password": password,
                    "audience": "wavesearch-api",
                    "scopes": scopes,
                },
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"STS login failed: {exc}") from exc
        token = str(login.get("access_token") or "")
        if not token:
            raise HTTPException(status_code=502, detail="STS login returned no access_token")
        return {"access_token": token, "token_type": "Bearer", "username": username, "tenant": tenant}

    @app.post("/v2/search")
    async def v2_search(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        bearer = bearer_or_issue(authorization, "wavesearch-api", tenant, "wave.shopper", ["search.query", "events.write"])
        try:
            return _json_request(
                f"{search_api}/search/query",
                method="POST",
                body={
                    "query": payload.get("query"),
                    "pageSize": payload.get("pageSize"),
                    "filters": payload.get("filters") if isinstance(payload.get("filters"), dict) else {},
                },
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"search backend failed: {exc}") from exc

    @app.post("/v2/recommend")
    async def v2_recommend(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        bearer = bearer_or_issue(authorization, "wavesearch-api", tenant, "wave.shopper", ["search.query", "events.write"])
        try:
            return _json_request(
                f"{search_api}/search/recommend",
                method="POST",
                body={
                    "productId": payload.get("productId"),
                    "visitorId": payload.get("visitorId"),
                    "pageSize": payload.get("pageSize"),
                },
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"recommend backend failed: {exc}") from exc

    @app.get("/v2/offers")
    async def v2_offers(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.read'])}"
        try:
            return _json_request(
                f"{erp_api}/erp/offers",
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"offers backend failed: {exc}") from exc

    @app.post("/v2/checkout")
    async def v2_checkout(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        customer_id = str(payload.get("customerId") or "guest")
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        if not items:
            raise HTTPException(status_code=400, detail="checkout requires items[]")
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.order', 'erp.read', 'erp.write'])}"
        try:
            return _json_request(
                f"{erp_api}/erp/orders",
                method="POST",
                body={"customerId": customer_id, "items": items},
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"checkout failed: {exc}") from exc

    @app.get("/v2/account/orders")
    async def v2_account_orders(
        customerId: str,
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.read', 'erp.order'])}"
        try:
            return _json_request(
                f"{erp_api}/erp/orders?customerId={quote(customerId, safe='')}",
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"account orders failed: {exc}") from exc

    @app.get("/v2/catalog/products")
    async def v2_catalog_products(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        bearer = bearer_or_issue(authorization, "wavestore-erp-api", tenant, "wave.shopper", ["erp.export", "erp.read"])
        try:
            export = _json_request(f"{erp_api}/erp/export/catalog", headers={"Authorization": bearer, "X-Tenant-Id": tenant})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"catalog export failed: {exc}") from exc
        products = export.get("products") if isinstance(export, dict) else None
        if not isinstance(products, list):
            raise HTTPException(status_code=502, detail="catalog export returned invalid products payload")
        if not products:
            products = _fallback_products()
        end = offset + limit
        return {"products": products[offset:end], "nextPageToken": str(end) if end < len(products) else ""}

    @app.get("/v2/catalog/products/{product_id}")
    async def v2_catalog_product(
        product_id: str,
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        bearer = bearer_or_issue(authorization, "wavestore-erp-api", tenant, "wave.shopper", ["erp.export", "erp.read"])
        try:
            export = _json_request(f"{erp_api}/erp/export/catalog", headers={"Authorization": bearer, "X-Tenant-Id": tenant})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"catalog export failed: {exc}") from exc
        products = export.get("products") if isinstance(export, dict) else None
        if not isinstance(products, list):
            raise HTTPException(status_code=502, detail="catalog export returned invalid products payload")
        if not products:
            products = _fallback_products()
        for p in products:
            if str(p.get("id") or "") == product_id:
                return p
        raise HTTPException(status_code=404, detail=f"product not found: {product_id}")

    return app
