from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException

from retail_v2.models import TenantContext
from wave_shared.auth import context_from_auth, issuer_for_audience, require_scope


def _is_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _scope_policy() -> dict[str, frozenset[str]]:
    return {
        "wave-sts": frozenset({"sts.issue", "sts.validate"}),
        "wavesearch-api": frozenset({"search.query", "search.admin", "search.ingest", "events.write"}),
        "wavestore-erp-api": frozenset({"erp.read", "erp.write", "erp.order", "erp.export"}),
        "wavestore-frontend": frozenset({"search.query", "events.write", "erp.read", "erp.order"}),
        "wavestore-erp-frontend": frozenset({"erp.read", "erp.write", "erp.order"}),
        "wavesearch-frontend": frozenset({"search.query", "search.admin", "search.ingest", "events.write", "erp.export"}),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Wave STS")
    scope_policy = _scope_policy()
    allow_anonymous_admin = _is_enabled(os.environ.get("WAVE_STS_ALLOW_ANONYMOUS_ADMIN"))

    allowed = {
        item.strip()
        for item in (os.environ.get("WAVE_STS_ALLOWED_AUDIENCES") or "wave-sts,wavesearch-api,wavestore-erp-api,wavestore-frontend,wavestore-erp-frontend,wavesearch-frontend").split(",")
        if item.strip()
    }

    def sts_admin_context(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> TenantContext:
        if allow_anonymous_admin and not authorization:
            return TenantContext(tenant_id=x_tenant_id or "system", scopes=frozenset({"sts.issue", "sts.validate"}))
        return context_from_auth("wave-sts", authorization=authorization, x_tenant_id=x_tenant_id, require_tenant_header=True)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wave-sts"}

    @app.get("/sts/jwks")
    async def jwks() -> dict[str, Any]:
        return {
            "issuer": os.environ.get("WAVE_STS_ISSUER", "wave-sts"),
            "alg": "HS256",
            "kid": os.environ.get("WAVE_STS_KID", "wave-sts-hs256-v1"),
            "audiences": sorted(allowed),
        }

    @app.post("/sts/token")
    async def issue_token(payload: dict[str, Any], context: TenantContext = Depends(sts_admin_context)) -> dict[str, Any]:
        require_scope(context, "sts.issue")
        audience = str(payload.get("audience") or "wavesearch-api")
        if audience not in allowed:
            raise HTTPException(status_code=400, detail=f"audience not allowed: {audience}")
        tenant = str(payload.get("tenant") or "demo-tenant")
        subject = str(payload.get("subject") or "demo-user")
        requested_scopes = [str(scope) for scope in (payload.get("scopes") or [])]
        if not requested_scopes:
            raise HTTPException(status_code=400, detail="scopes[] is required")
        allowed_scopes = scope_policy.get(audience, frozenset())
        invalid_scopes = sorted({scope for scope in requested_scopes if scope not in allowed_scopes})
        if invalid_scopes:
            raise HTTPException(status_code=400, detail=f"scopes not allowed for audience {audience}: {', '.join(invalid_scopes)}")
        ttl_seconds = int(payload.get("ttlSeconds") or 900)
        ttl_seconds = max(60, min(3600, ttl_seconds))
        token = issuer_for_audience(audience).issue(subject, tenant, requested_scopes, ttl_seconds=ttl_seconds)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "issuer": os.environ.get("WAVE_STS_ISSUER", "wave-sts"),
            "audience": audience,
            "tenant": tenant,
            "scope": " ".join(requested_scopes),
            "expires_in": ttl_seconds,
        }

    @app.post("/sts/validate")
    async def validate_token(payload: dict[str, Any], context: TenantContext = Depends(sts_admin_context)) -> dict[str, Any]:
        require_scope(context, "sts.validate")
        token = str(payload.get("token") or "")
        audience = str(payload.get("audience") or "")
        if not token or not audience:
            raise HTTPException(status_code=400, detail="token and audience are required")
        try:
            context = issuer_for_audience(audience).verify(token)
            return {"active": True, "tenant": context.tenant_id, "scopes": sorted(context.scopes)}
        except ValueError as exc:
            return {"active": False, "error": str(exc)}

    return app
