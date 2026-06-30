from __future__ import annotations

import os
from typing import Annotated

from fastapi import Header, HTTPException

from retail_v2.auth import TokenIssuer
from retail_v2.models import TenantContext


def issuer_for_audience(audience: str) -> TokenIssuer:
    return TokenIssuer(
        issuer=os.environ.get("WAVE_STS_ISSUER", "wave-sts"),
        secret=os.environ.get("WAVE_STS_SECRET", "dev-secret"),
        audience=audience,
    )


def context_from_auth(
    audience: str,
    authorization: Annotated[str | None, Header()] = None,
    x_tenant_id: Annotated[str | None, Header()] = None,
    require_tenant_header: bool = False,
) -> TenantContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization.split(" ", 1)[1]
    try:
        context = issuer_for_audience(audience).verify(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if require_tenant_header and not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-Id header required")
    if x_tenant_id and x_tenant_id != context.tenant_id:
        raise HTTPException(status_code=403, detail="tenant header/token mismatch")
    return context


def require_scope(context: TenantContext, scope: str) -> None:
    if scope not in context.scopes:
        raise HTTPException(status_code=403, detail=f"missing required scope: {scope}")
