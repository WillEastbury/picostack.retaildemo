"""Generic OpenID Connect (OIDC) federation for wave-sts: Google, Microsoft (Entra ID / "Live
ID"), and Apple ("Sign in with Apple"), all funnelled through the exact same Authorization Code
flow + ID token verification path, so adding a fourth provider later is "add one ProviderConfig",
not "write a new auth system".

Design:
  - Every provider is configured purely via environment variables. is_configured() gates whether
    a provider is offered at all -- a deployment with no Google/Microsoft/Apple credentials set
    behaves exactly like it did before this module existed (native-only login).
  - The Authorization Code flow is the same for all three: redirect the browser to the
    provider's authorization endpoint, receive a `code` on the callback, exchange it at the
    provider's token endpoint for an id_token (a signed JWT asserting who the user is), then
    verify that JWT for real: signature (against the provider's published JWKS, RS256), issuer,
    audience, and expiry -- not just decode-and-trust.
  - Apple is the one genuinely different case: it doesn't use a static client_secret like Google/
    Microsoft. Instead, Apple requires the client_secret ITSELF to be a short-lived ES256-signed
    JWT, signed with your Apple Developer "Sign in with Apple" private key (.p8). See
    apple_client_secret() below -- built with real ECDSA signing (cryptography package), not a
    stub.
"""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _http_json(url: str, method: str = "GET", body: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    req_headers = dict(headers or {})
    data = None
    if body is not None:
        data = urlencode(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = Request(url=url, method=method, data=data, headers=req_headers)
    try:
        with urlopen(req, timeout=20) as response:  # nosec B310 - well-known, configured OIDC provider endpoints
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OIDC HTTP error ({exc.code}) calling {url}: {detail}") from exc


# --- JWKS-backed RS256 ID token verification (Google, Microsoft, and Apple all issue RS256 ID
# tokens signed with a key from their own published JWKS) ---
_jwks_cache: dict[str, tuple[dict[str, Any], float]] = {}
_JWKS_CACHE_TTL_SECONDS = 3600


def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    cached = _jwks_cache.get(jwks_uri)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]
    jwks = _http_json(jwks_uri)
    _jwks_cache[jwks_uri] = (jwks, now + _JWKS_CACHE_TTL_SECONDS)
    return jwks


def _rsa_public_key_from_jwk(jwk: dict[str, Any]) -> rsa.RSAPublicKey:
    n = int.from_bytes(_unb64url(jwk["n"]), "big")
    e = int.from_bytes(_unb64url(jwk["e"]), "big")
    return rsa.RSAPublicNumbers(e, n).public_key()


def verify_id_token(id_token: str, jwks_uri: str, expected_issuers: set[str], expected_audience: str) -> dict[str, Any]:
    """Real ID token verification: checks the RS256 signature against the provider's published
    JWKS (matched by `kid`), then the issuer, audience, and expiry claims. Raises ValueError on
    any failure -- callers must not treat a raised exception as "logged in"."""
    try:
        header_b64, payload_b64, sig_b64 = id_token.split(".")
    except ValueError as exc:
        raise ValueError("malformed id_token") from exc
    header = json.loads(_unb64url(header_b64))
    if header.get("alg") != "RS256":
        raise ValueError(f"unsupported id_token alg: {header.get('alg')} (only RS256 is supported)")
    jwks = _fetch_jwks(jwks_uri)
    matching_key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if not matching_key:
        raise ValueError("no matching JWKS key for id_token kid -- provider may have rotated keys, retry")
    public_key = _rsa_public_key_from_jwk(matching_key)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = _unb64url(sig_b64)
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes

    try:
        public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature as exc:
        raise ValueError("id_token signature verification failed") from exc
    payload = json.loads(_unb64url(payload_b64))
    if payload.get("iss") not in expected_issuers:
        # Support a single wildcard segment for multi-tenant issuers (Microsoft's "common"
        # endpoint signs tokens with the ACTUAL signed-in tenant's GUID embedded in the issuer
        # URL, which cannot be known in advance -- e.g. "https://login.microsoftonline.com/*/v2.0"
        # matches any tenant under that path). This is the standard, documented approach for
        # multi-tenant apps validating Microsoft identity platform tokens.
        issuer = str(payload.get("iss") or "")
        wildcard_match = any(
            "*" in pattern and issuer.startswith(pattern.split("*")[0]) and issuer.endswith(pattern.split("*")[1])
            for pattern in expected_issuers
        )
        if not wildcard_match:
            raise ValueError(f"unexpected id_token issuer: {payload.get('iss')}")
    audience = payload.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if expected_audience not in audiences:
        raise ValueError(f"id_token audience mismatch: expected {expected_audience!r}, got {audiences}")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("id_token has expired")
    return payload


def apple_client_secret(team_id: str, client_id: str, key_id: str, private_key_pem: str, ttl_seconds: int = 15_777_000) -> str:
    """Apple's OAuth client_secret is itself a short-lived ES256-signed JWT (max validity ~6
    months), signed with your Sign in with Apple private key -- NOT a static secret like every
    other OIDC provider. Real ECDSA (P-256/ES256) signing via the `cryptography` package."""
    now = int(time.time())
    header = {"alg": "ES256", "kid": key_id}
    payload = {
        "iss": team_id,
        "iat": now,
        "exp": now + ttl_seconds,
        "aud": "https://appleid.apple.com",
        "sub": client_id,
    }
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}.{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    private_key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("Apple private key must be an EC (P-256) key for ES256 signing")
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

    der_signature = private_key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_signature)
    # JOSE ES256 signatures are raw fixed-width r||s (32 bytes each for P-256), NOT the DER
    # encoding `sign()` returns by default -- this conversion is required or every verifier will
    # reject the signature.
    raw_signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{signing_input}.{_b64url(raw_signature)}"


class ProviderConfig:
    """Plain class, deliberately NOT a dataclass -- MicrosoftProvider needs several of these
    "fields" to be computed @property methods (its endpoints depend on a runtime-configurable
    tenant ID), which dataclass field/property mixing handles very badly (subclasses redeclaring
    an inherited field with a default while other inherited fields still lack one raises
    "non-default argument follows default argument" at class-definition time). Plain attributes
    set in __init__/class body avoid that footgun entirely."""

    name: str = "unknown"
    display_name: str = "Unknown"
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    jwks_uri: str = ""
    issuers: set[str] = frozenset()
    scope: str = "openid email profile"
    response_mode: str | None = None  # Apple requires "form_post"

    def is_configured(self) -> bool:
        raise NotImplementedError

    def client_id(self) -> str:
        raise NotImplementedError

    def client_secret_for_token_exchange(self) -> str:
        raise NotImplementedError


class GoogleProvider(ProviderConfig):
    name = "google"
    display_name = "Google"
    authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    jwks_uri = "https://www.googleapis.com/oauth2/v3/certs"
    issuers = {"https://accounts.google.com", "accounts.google.com"}

    def is_configured(self) -> bool:
        return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))

    def client_id(self) -> str:
        return os.environ.get("GOOGLE_CLIENT_ID", "")

    def client_secret_for_token_exchange(self) -> str:
        return os.environ.get("GOOGLE_CLIENT_SECRET", "")


class MicrosoftProvider(ProviderConfig):
    # "Microsoft LiveId" in the modern Microsoft identity platform is Entra ID (formerly Azure
    # AD) v2.0 endpoints, which also accept personal Microsoft/Live accounts when using the
    # "common" tenant -- this is the actual, current implementation of what used to be branded
    # "Windows Live ID" sign-in.
    name = "microsoft"
    display_name = "Microsoft"
    scope = "openid email profile"

    def _tenant(self) -> str:
        return os.environ.get("MICROSOFT_TENANT_ID", "common")

    @property
    def authorization_endpoint(self) -> str:  # type: ignore[override]
        return f"https://login.microsoftonline.com/{self._tenant()}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:  # type: ignore[override]
        return f"https://login.microsoftonline.com/{self._tenant()}/oauth2/v2.0/token"

    @property
    def jwks_uri(self) -> str:  # type: ignore[override]
        return f"https://login.microsoftonline.com/{self._tenant()}/discovery/v2.0/keys"

    @property
    def issuers(self) -> set[str]:  # type: ignore[override]
        # The v2.0 token issuer embeds the actual signed-in tenant GUID (not literally "common"),
        # so when using the multi-tenant "common" endpoint we cannot pin one exact issuer string
        # in advance -- a single wildcard segment (see verify_id_token) matches any tenant under
        # login.microsoftonline.com. When a specific MICROSOFT_TENANT_ID is configured, pin to
        # that exact tenant's issuer for tighter validation.
        tenant = self._tenant()
        if tenant == "common":
            return {"https://login.microsoftonline.com/*/v2.0"}
        return {f"https://login.microsoftonline.com/{tenant}/v2.0"}

    def is_configured(self) -> bool:
        return bool(os.environ.get("MICROSOFT_CLIENT_ID") and os.environ.get("MICROSOFT_CLIENT_SECRET"))

    def client_id(self) -> str:
        return os.environ.get("MICROSOFT_CLIENT_ID", "")

    def client_secret_for_token_exchange(self) -> str:
        return os.environ.get("MICROSOFT_CLIENT_SECRET", "")


class AppleProvider(ProviderConfig):
    name = "apple"
    display_name = "Apple"
    authorization_endpoint = "https://appleid.apple.com/auth/authorize"
    token_endpoint = "https://appleid.apple.com/auth/token"
    jwks_uri = "https://appleid.apple.com/auth/keys"
    issuers = {"https://appleid.apple.com"}
    scope = "name email"
    response_mode = "form_post"  # Apple POSTs the callback instead of a GET redirect

    def is_configured(self) -> bool:
        return bool(
            os.environ.get("APPLE_CLIENT_ID")
            and os.environ.get("APPLE_TEAM_ID")
            and os.environ.get("APPLE_KEY_ID")
            and os.environ.get("APPLE_PRIVATE_KEY")
        )

    def client_id(self) -> str:
        return os.environ.get("APPLE_CLIENT_ID", "")

    def client_secret_for_token_exchange(self) -> str:
        return apple_client_secret(
            team_id=os.environ.get("APPLE_TEAM_ID", ""),
            client_id=os.environ.get("APPLE_CLIENT_ID", ""),
            key_id=os.environ.get("APPLE_KEY_ID", ""),
            private_key_pem=os.environ.get("APPLE_PRIVATE_KEY", "").replace("\\n", "\n"),
        )


PROVIDERS: dict[str, ProviderConfig] = {
    "google": GoogleProvider(),
    "microsoft": MicrosoftProvider(),
    "apple": AppleProvider(),
}


def available_providers() -> list[ProviderConfig]:
    return [p for p in PROVIDERS.values() if p.is_configured()]


def build_authorize_url(provider: ProviderConfig, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": provider.client_id(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": provider.scope,
        "state": state,
    }
    if provider.response_mode:
        params["response_mode"] = provider.response_mode
    return f"{provider.authorization_endpoint}?{urlencode(params)}"


def exchange_code(provider: ProviderConfig, code: str, redirect_uri: str) -> dict[str, Any]:
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": provider.client_id(),
        "client_secret": provider.client_secret_for_token_exchange(),
    }
    return _http_json(provider.token_endpoint, method="POST", body=body)


def verify_provider_id_token(provider: ProviderConfig, id_token: str) -> dict[str, Any]:
    return verify_id_token(id_token, provider.jwks_uri, provider.issuers, provider.client_id())
