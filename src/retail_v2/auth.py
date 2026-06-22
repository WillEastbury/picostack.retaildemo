from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from .models import TenantContext


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


@dataclass(frozen=True)
class TokenIssuer:
    issuer: str
    secret: str
    audience: str = "retail-v2"

    def issue(self, subject: str, tenant_id: str, scopes: list[str], ttl_seconds: int = 3600) -> str:
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload: dict[str, Any] = {
            "iss": self.issuer,
            "sub": subject,
            "aud": self.audience,
            "tenant": tenant_id,
            "scope": " ".join(scopes),
            "iat": now,
            "exp": now + ttl_seconds,
        }
        signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}.{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
        sig = hmac.new(self.secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        return f"{signing_input}.{_b64url(sig)}"

    def verify(self, token: str) -> TenantContext:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError as exc:
            raise ValueError("invalid token format") from exc
        signing_input = f"{header_b64}.{payload_b64}"
        expected = hmac.new(self.secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        actual = _unb64url(sig_b64)
        if not hmac.compare_digest(expected, actual):
            raise ValueError("invalid token signature")
        payload = json.loads(_unb64url(payload_b64))
        if payload.get("aud") != self.audience:
            raise ValueError("invalid token audience")
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("token expired")
        tenant = payload.get("tenant")
        if not tenant:
            raise ValueError("missing tenant claim")
        scopes = frozenset(str(payload.get("scope") or "").split())
        return TenantContext(tenant_id=str(tenant), scopes=scopes)


def require_scope(context: TenantContext, scope: str) -> None:
    if scope not in context.scopes and "admin" not in context.scopes:
        raise PermissionError(f"missing required scope: {scope}")
