from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from retail_v2.auth import TokenIssuer

from wavestore_frontend.voice import TOOL_DEFINITIONS, WaveBrowserVoiceBridge, WaveVoiceToolContext, wave_voice_settings_from_env
from wavestore_frontend.payments import CaptureResult, PaymentIntentResult, available_providers, get_provider


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

    # Pending checkouts awaiting payment confirmation (two-phase checkout: /v2/checkout/init
    # creates a payment intent with the chosen provider and stashes what order to place once
    # payment succeeds; /v2/checkout/confirm captures the payment and only THEN places the real
    # ERP order). Process-local and short-lived by nature (a shopper completes payment within
    # the same session), so an in-memory dict is fine here -- unlike the ERP's own durable state.
    _pending_checkouts: dict[str, dict[str, Any]] = {}

    def tenant_value(x_tenant_id: str | None) -> str:
        return (x_tenant_id or "demo-tenant").strip() or "demo-tenant"

    # Process-local token cache: search (and recommend/offers) are publicly reachable pages with
    # no shopper login required, but wavesearch-api still enforces a signed, scoped JWT per the
    # platform's zero-trust design. Previously every single /v2/search call minted a brand-new
    # token via a full STS /sts/login round-trip (~120ms of PBKDF2 password verification alone,
    # plus network hops), even though the resulting token/scopes are identical call to call.
    # Cache by (audience, tenant, subject, scopes) and only re-issue once the cached token is
    # close to expiry, requesting the maximum STS-allowed TTL (1 hour) to minimize refreshes.
    _token_cache: dict[tuple[str, str, str, tuple[str, ...]], tuple[str, float]] = {}
    TOKEN_TTL_SECONDS = 3600
    TOKEN_REFRESH_MARGIN_SECONDS = 60

    def issue_token(audience: str, tenant: str, subject: str, scopes: list[str]) -> str:
        cache_key = (audience, tenant, subject, tuple(sorted(scopes)))
        cached = _token_cache.get(cache_key)
        now = time.monotonic()
        if cached and cached[1] > now:
            return cached[0]

        local_secret = os.environ.get("WAVE_STS_SECRET")
        if local_secret:
            issuer = TokenIssuer(
                issuer=os.environ.get("WAVE_STS_ISSUER", "wave-sts"),
                secret=local_secret,
                audience=audience,
            )
            token = issuer.issue(subject, tenant, scopes, ttl_seconds=TOKEN_TTL_SECONDS)
            _token_cache[cache_key] = (token, now + TOKEN_TTL_SECONDS - TOKEN_REFRESH_MARGIN_SECONDS)
            return token

        payload = {"audience": audience, "tenant": tenant, "subject": subject, "scopes": scopes, "ttlSeconds": TOKEN_TTL_SECONDS}
        try:
            result = _json_request(f"{sts}/sts/token", method="POST", body=payload, headers={"X-Tenant-Id": tenant})
        except Exception:
            service_username = os.environ.get("WAVESTORE_SERVICE_USER", "wave.user")
            service_password = os.environ.get("WAVESTORE_SERVICE_PASSWORD", "demo123!")
            try:
                result = _json_request(
                    f"{sts}/sts/login",
                    method="POST",
                    body={
                        "tenant": tenant,
                        "username": service_username,
                        "password": service_password,
                        "audience": audience,
                        "scopes": scopes,
                        "ttlSeconds": TOKEN_TTL_SECONDS,
                    },
                    headers={"X-Tenant-Id": tenant},
                )
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"STS token issue failed: {exc}") from exc
        token = str(result.get("access_token") or "")
        if not token:
            raise HTTPException(status_code=502, detail="STS token issue returned no access_token")
        expires_in = int(result.get("expires_in") or TOKEN_TTL_SECONDS)
        _token_cache[cache_key] = (token, now + expires_in - TOKEN_REFRESH_MARGIN_SECONDS)
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
        audience = str(payload.get("audience") or "wavesearch-api").strip() or "wavesearch-api"
        allowed_scopes_by_audience = {
            "wave-sts": {"sts.issue", "sts.validate", "sts.admin"},
            "wavesearch-api": {"search.query", "search.admin", "search.ingest", "events.write"},
            "wavestore-erp-api": {"erp.read", "erp.write", "erp.order", "erp.export"},
            "wavestore-frontend": {"search.query", "events.write", "erp.read", "erp.order"},
            "wavestore-erp-frontend": {"erp.read", "erp.write", "erp.order"},
            "wavesearch-frontend": {"search.query", "search.admin", "search.ingest", "events.write", "erp.export"},
        }
        default_scopes_by_audience = {
            "wavesearch-api": ["search.query", "events.write"],
            "wavestore-frontend": ["search.query", "events.write", "erp.read", "erp.order"],
            "wavestore-erp-api": ["erp.read", "erp.write", "erp.order", "erp.export"],
            "wave-sts": ["sts.issue", "sts.validate", "sts.admin"],
        }
        allowed_scope_set = allowed_scopes_by_audience.get(audience, set())
        scopes_raw = payload.get("scopes")
        requested_scopes = [str(s).strip() for s in scopes_raw] if isinstance(scopes_raw, list) else []
        if requested_scopes and allowed_scope_set:
            scopes = [scope for scope in requested_scopes if scope in allowed_scope_set]
        else:
            scopes = []
        if not scopes:
            scopes = default_scopes_by_audience.get(audience, ["search.query", "events.write"])
        try:
            login = _json_request(
                f"{sts}/sts/login",
                method="POST",
                body={
                    "tenant": tenant,
                    "username": username,
                    "password": password,
                    "audience": audience,
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

    def do_search(query: Any, page_size: Any, filters: dict[str, Any], tenant: str, visitor_id: Any = None) -> dict[str, Any]:
        # /search/query is a public, read-only endpoint on wavesearch-api (no auth required) —
        # skip token issuance entirely rather than minting a token nobody checks.
        try:
            body: dict[str, Any] = {"query": query, "pageSize": page_size, "filters": filters if isinstance(filters, dict) else {}}
            if visitor_id:
                body["visitorId"] = visitor_id
            return _json_request(
                f"{search_api}/search/query",
                method="POST",
                body=body,
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"search backend failed: {exc}") from exc

    def do_visual_search(
        description: Any,
        page_size: Any,
        tenant: str,
        visitor_id: Any = None,
        image_base64: Any = None,
        image_mime_type: Any = None,
    ) -> dict[str, Any]:
        try:
            body: dict[str, Any] = {"pageSize": page_size}
            if description:
                body["description"] = description
            if visitor_id:
                body["visitorId"] = visitor_id
            if image_base64:
                body["imageBase64"] = image_base64
                body["imageMimeType"] = image_mime_type or "image/jpeg"
            return _json_request(
                f"{search_api}/search/visual",
                method="POST",
                body=body,
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"visual search backend failed: {exc}") from exc

    def do_browse(filters: dict[str, Any], page_size: Any, offset: Any, sort: Any, tenant: str, visitor_id: Any = None) -> dict[str, Any]:
        try:
            body: dict[str, Any] = {"filters": filters if isinstance(filters, dict) else {}, "pageSize": page_size, "offset": offset or 0}
            if sort:
                body["sort"] = sort
            if visitor_id:
                body["visitorId"] = visitor_id
            return _json_request(
                f"{search_api}/search/browse",
                method="POST",
                body=body,
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"browse backend failed: {exc}") from exc

    def do_track_event(payload: dict[str, Any], tenant: str) -> dict[str, Any]:
        try:
            return _json_request(
                f"{search_api}/search/events",
                method="POST",
                body=payload,
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"event tracking failed: {exc}") from exc

    def do_autocomplete(query: Any, limit: Any, tenant: str) -> dict[str, Any]:
        try:
            return _json_request(
                f"{search_api}/search/autocomplete?query={quote(str(query or ''))}&limit={int(limit or 8)}",
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"autocomplete backend failed: {exc}") from exc

    def do_recommend(product_id: Any, visitor_id: Any, page_size: Any, tenant: str) -> dict[str, Any]:
        try:
            return _json_request(
                f"{search_api}/search/recommend",
                method="POST",
                body={"productId": product_id, "visitorId": visitor_id, "pageSize": page_size},
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"recommend backend failed: {exc}") from exc

    def do_offers(tenant: str) -> dict[str, Any]:
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.read'])}"
        try:
            return _json_request(f"{erp_api}/erp/offers", headers={"Authorization": bearer, "X-Tenant-Id": tenant})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"offers backend failed: {exc}") from exc

    def do_search_offers(query: Any, page_size: Any, tenant: str) -> dict[str, Any]:
        try:
            return _json_request(
                f"{search_api}/search/offers",
                method="POST",
                body={"query": query, "pageSize": page_size},
                headers={"X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"offer search backend failed: {exc}") from exc

    def do_checkout(customer_id: str, items: list[dict[str, Any]], tenant: str) -> dict[str, Any]:
        if not items:
            raise HTTPException(status_code=400, detail="checkout requires items[]")
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.order', 'erp.read', 'erp.write'])}"
        try:
            return _json_request(
                f"{erp_api}/erp/orders",
                method="POST",
                body={"customerId": customer_id or "guest", "items": items},
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"checkout failed: {exc}") from exc

    def _resolve_checkout_total(customer_id: str, items: list[dict[str, Any]], tenant: str) -> tuple[float, list[dict[str, Any]]]:
        # Resolves each line item through the ERP's personalized pricing engine (condition
        # records -- see wavestore_erp_api's /erp/pricing/resolve-batch) so the amount a payment
        # provider is asked to charge always matches what the ERP order will actually total,
        # including any customer/product-hierarchy-based discount the shopper is entitled to.
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.read'])}"
        product_ids = [str(item.get("productId") or "") for item in items if item.get("productId")]
        try:
            resolved = _json_request(
                f"{erp_api}/erp/pricing/resolve-batch",
                method="POST",
                body={"productIds": product_ids, "customerId": customer_id or None},
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"pricing resolution failed: {exc}") from exc
        price_by_product = {row["productId"]: row["price"] for row in resolved.get("prices", [])}
        total = 0.0
        priced_items: list[dict[str, Any]] = []
        for item in items:
            product_id = str(item.get("productId") or "")
            qty = max(1, int(item.get("quantity") or 1))
            price = price_by_product.get(product_id, 0.0)
            total += qty * price
            priced_items.append({"productId": product_id, "quantity": qty, "price": price})
        return round(total, 2), priced_items

    def do_checkout_providers() -> dict[str, Any]:
        return {"providers": [{"name": p.name} for p in available_providers()]}

    def do_checkout_init(customer_id: str, items: list[dict[str, Any]], provider_name: str, tenant: str) -> dict[str, Any]:
        if not items:
            raise HTTPException(status_code=400, detail="checkout requires items[]")
        total, priced_items = _resolve_checkout_total(customer_id, items, tenant)
        provider = get_provider(provider_name)
        checkout_ref = f"chk-{os.urandom(6).hex()}"
        try:
            intent = provider.create_intent(checkout_ref, total, "GBP", {"customerId": customer_id or "guest"})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"{provider.name} payment intent creation failed: {exc}") from exc
        _pending_checkouts[checkout_ref] = {
            "customerId": customer_id or "guest",
            "items": priced_items,
            "tenant": tenant,
            "provider": provider.name,
            "intentId": intent.intentId,
            "total": total,
        }
        return {"checkoutRef": checkout_ref, "total": total, "currency": "GBP", "intent": intent.to_dict()}

    def do_checkout_confirm(checkout_ref: str) -> dict[str, Any]:
        pending = _pending_checkouts.get(checkout_ref)
        if not pending:
            raise HTTPException(status_code=404, detail="unknown or already-completed checkoutRef")
        provider = get_provider(pending["provider"])
        try:
            capture: CaptureResult = provider.capture(pending["intentId"], {"customerId": pending["customerId"]})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"{provider.name} payment capture failed: {exc}") from exc
        if capture.status != "succeeded":
            return {"accepted": False, "payment": capture.to_dict(), "reason": "payment not completed"}
        # Payment is confirmed -- NOW place the real ERP order (with the already-resolved,
        # personalized-pricing item list, as explicit prices so the ERP doesn't re-resolve and
        # potentially race a pricing-condition change between init and confirm).
        order_result = do_checkout(pending["customerId"], pending["items"], pending["tenant"])
        del _pending_checkouts[checkout_ref]
        return {"accepted": True, "payment": capture.to_dict(), **order_result}

    def do_account_orders(customer_id: str, tenant: str) -> dict[str, Any]:
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.read', 'erp.order'])}"
        try:
            return _json_request(
                f"{erp_api}/erp/orders?customerId={quote(customer_id, safe='')}",
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"account orders failed: {exc}") from exc

    def do_account_invoices(customer_id: str, tenant: str) -> dict[str, Any]:
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, customer_id or 'wave.shopper', ['erp.read'])}"
        try:
            return _json_request(
                f"{erp_api}/erp/invoices?customerId={quote(customer_id, safe='')}",
                headers={"Authorization": bearer, "X-Tenant-Id": tenant},
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"account invoices failed: {exc}") from exc

    @app.post("/v2/search")
    async def v2_search(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_search(payload.get("query"), payload.get("pageSize"), payload.get("filters"), tenant, payload.get("visitorId"))

    @app.post("/v2/search/visual")
    async def v2_search_visual(
        payload: dict[str, Any],
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_visual_search(
            payload.get("description"),
            payload.get("pageSize"),
            tenant,
            payload.get("visitorId"),
            payload.get("imageBase64"),
            payload.get("imageMimeType"),
        )

    @app.post("/v2/browse")
    async def v2_browse(
        payload: dict[str, Any],
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_browse(payload.get("filters"), payload.get("pageSize"), payload.get("offset"), payload.get("sort"), tenant, payload.get("visitorId"))

    @app.post("/v2/events")
    async def v2_events(
        payload: dict[str, Any],
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_track_event(payload, tenant)

    @app.get("/v2/search/autocomplete")
    async def v2_search_autocomplete(
        q: str = "",
        limit: int = 8,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_autocomplete(q, limit, tenant)

    @app.post("/v2/recommend")
    async def v2_recommend(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_recommend(payload.get("productId"), payload.get("visitorId"), payload.get("pageSize"), tenant)

    @app.get("/v2/offers")
    async def v2_offers(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_offers(tenant)

    @app.post("/v2/offers/search")
    async def v2_offers_search(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_search_offers(payload.get("query"), payload.get("pageSize"), tenant)

    @app.post("/v2/checkout")
    async def v2_checkout(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        # Single-call checkout -- kept for backward compatibility, always uses the "native"
        # provider (no external payment gateway), exactly as before this module existed. New
        # integrations should use the two-phase /v2/checkout/init + /v2/checkout/confirm flow
        # below, which supports Stripe/PayPal/any future provider.
        tenant = tenant_value(x_tenant_id)
        customer_id = str(payload.get("customerId") or "guest")
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        return do_checkout(customer_id, items, tenant)

    @app.get("/v2/checkout/providers")
    async def v2_checkout_providers() -> dict[str, Any]:
        return do_checkout_providers()

    @app.post("/v2/checkout/init")
    async def v2_checkout_init(
        payload: dict[str, Any],
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        customer_id = str(payload.get("customerId") or "guest")
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        provider_name = str(payload.get("provider") or "native")
        return do_checkout_init(customer_id, items, provider_name, tenant)

    @app.post("/v2/checkout/confirm")
    async def v2_checkout_confirm(payload: dict[str, Any]) -> dict[str, Any]:
        checkout_ref = str(payload.get("checkoutRef") or "")
        if not checkout_ref:
            raise HTTPException(status_code=400, detail="checkoutRef is required")
        return do_checkout_confirm(checkout_ref)

    @app.get("/v2/account/orders")
    async def v2_account_orders(
        customerId: str,
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_account_orders(customerId, tenant)

    @app.get("/v2/account/invoices")
    async def v2_account_invoices(
        customerId: str,
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        return do_account_invoices(customerId, tenant)

    @app.get("/v2/catalog/products")
    async def v2_catalog_products(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        tenant = tenant_value(x_tenant_id)
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.export', 'erp.read'])}"
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
        bearer = f"Bearer {issue_token('wavestore-erp-api', tenant, 'wave.shopper', ['erp.export', 'erp.read'])}"
        try:
            export = _json_request(f"{erp_api}/erp/export/catalog", headers={"Authorization": bearer, "X-Tenant-Id": tenant})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"catalog export failed: {exc}") from exc
        products = export.get("products") if isinstance(export, dict) else None
        if not isinstance(products, list):
            raise HTTPException(status_code=502, detail="catalog export returned invalid products payload")
        if not products:
            products = _fallback_products()
        requested = product_id.strip().lower()
        for p in products:
            if str(p.get("id") or "").strip().lower() == requested:
                return p
        raise HTTPException(status_code=404, detail=f"product not found: {product_id}")

    @app.get("/v2/voice/config")
    async def v2_voice_config() -> dict[str, Any]:
        return {
            "enabled": wave_voice_settings_from_env() is not None,
            "websocket": "/ws/voice",
            "tools": TOOL_DEFINITIONS,
        }

    @app.websocket("/ws/voice")
    async def ws_voice(websocket: WebSocket) -> None:
        settings = wave_voice_settings_from_env()
        await websocket.accept()
        if settings is None:
            await websocket.send_text(json.dumps({"type": "error", "error": "Voice is not configured on this server yet."}))
            await websocket.close(code=1011)
            return
        tools = WaveVoiceToolContext(
            do_search=do_search,
            do_recommend=do_recommend,
            do_offers=do_offers,
            do_checkout=do_checkout,
            do_account_orders=do_account_orders,
            do_account_invoices=do_account_invoices,
        )
        bridge = WaveBrowserVoiceBridge(websocket, settings, tools)
        try:
            await bridge.run()
        except WebSocketDisconnect:
            return
        except Exception as exc:
            try:
                await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
                await websocket.close(code=1011)
            except Exception:
                pass

    return app
