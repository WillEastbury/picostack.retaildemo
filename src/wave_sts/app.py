from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from retail_v2.models import TenantContext
from wave_shared.auth import context_from_auth, issuer_for_audience, require_scope

STS_UI_HTML = Path(__file__).with_name("wave_sts_ui.html")


def _is_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _scope_policy() -> dict[str, frozenset[str]]:
    return {
        "wave-sts": frozenset({"sts.issue", "sts.validate", "sts.admin"}),
        "wavesearch-api": frozenset({"search.query", "search.admin", "search.ingest", "events.write"}),
        "wavestore-erp-api": frozenset({"erp.read", "erp.write", "erp.order", "erp.export"}),
        "wavestore-frontend": frozenset({"search.query", "events.write", "erp.read", "erp.order"}),
        "wavestore-erp-frontend": frozenset({"erp.read", "erp.write", "erp.order"}),
        "wavesearch-frontend": frozenset({"search.query", "search.admin", "search.ingest", "events.write", "erp.export"}),
    }


def _cors_origins() -> list[str]:
    configured = os.environ.get("WAVE_CORS_ORIGINS")
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    return [
        "http://127.0.0.1:8805",
        "http://localhost:8805",
        "http://127.0.0.1:8804",
        "http://localhost:8804",
        "http://127.0.0.1:8787",
        "http://localhost:8787",
    ]


class UserStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.users: dict[str, dict[str, Any]] = {}
        self._load()
        self._bootstrap_defaults()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.users = payload.get("users", {}) if isinstance(payload.get("users"), dict) else {}

    def _save(self) -> None:
        self.path.write_text(json.dumps({"users": self.users}, indent=2), encoding="utf-8")

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return base64.b64encode(derived).decode("ascii")

    def _bootstrap_defaults(self) -> None:
        default_password = os.environ.get("WAVE_STS_DEMO_PASSWORD", "demo123!")
        admin_user = os.environ.get("WAVE_STS_ADMIN_USER", "admin")
        admin_password = os.environ.get("WAVE_STS_ADMIN_PASSWORD", default_password)
        audience_defaults = ["wave-sts", "wavesearch-api", "wavestore-erp-api", "wavestore-frontend", "wavestore-erp-frontend", "wavesearch-frontend"]
        self.ensure_user(admin_user, admin_password, audience_defaults, ["sts.issue", "sts.validate", "sts.admin"], is_admin=True)
        self.ensure_user("sts.admin", default_password, ["wave-sts"], ["sts.issue", "sts.validate", "sts.admin"], is_admin=True)
        self.ensure_user("wave.user", default_password, ["wavesearch-api", "wavestore-erp-api", "wavestore-frontend"], ["search.query", "events.write", "erp.read", "erp.order"])
        self.ensure_user("erp.admin", default_password, ["wavestore-erp-api", "wavestore-erp-frontend"], ["erp.read", "erp.write", "erp.order", "erp.export"], is_admin=True)
        self.ensure_user("search.admin", default_password, ["wavesearch-api", "wavesearch-frontend", "wavestore-erp-api"], ["search.query", "search.admin", "search.ingest", "events.write", "erp.export", "erp.read"], is_admin=True)
        self.ensure_user("wavestore.admin", default_password, ["wavestore-frontend", "wavestore-erp-api", "wavestore-erp-frontend"], ["search.query", "events.write", "erp.read", "erp.write", "erp.order", "erp.export"], is_admin=True)
        self.ensure_user("wavesearch.admin", default_password, ["wavesearch-api", "wavesearch-frontend"], ["search.query", "search.admin", "search.ingest", "events.write"], is_admin=True)
        self.ensure_user("avery.hill", "avery.hill", ["wavestore-frontend", "wavesearch-api"], ["search.query", "events.write", "erp.read", "erp.order"])
        self.ensure_user("morgan.vale", "morgan.vale", ["wavestore-frontend", "wavesearch-api"], ["search.query", "events.write", "erp.read", "erp.order"])

    def create_user(
        self,
        username: str,
        password: str,
        allowed_audiences: list[str],
        allowed_scopes: list[str],
        *,
        is_admin: bool = False,
        disabled: bool = False,
    ) -> dict[str, Any]:
        if not username.strip():
            raise ValueError("username is required")
        if len(password) < 6:
            raise ValueError("password must be at least 6 characters")
        salt = os.urandom(16)
        row = {
            "username": username.strip(),
            "salt": base64.b64encode(salt).decode("ascii"),
            "passwordHash": self._hash_password(password, salt),
            "allowedAudiences": sorted({item for item in allowed_audiences if item}),
            "allowedScopes": sorted({item for item in allowed_scopes if item}),
            "isAdmin": bool(is_admin),
            "disabled": bool(disabled),
        }
        self.users[row["username"]] = row
        self._save()
        return row

    def ensure_user(
        self,
        username: str,
        password: str,
        allowed_audiences: list[str],
        allowed_scopes: list[str],
        *,
        is_admin: bool = False,
        disabled: bool = False,
    ) -> dict[str, Any]:
        existing = self.users.get(username.strip())
        if not existing:
            return self.create_user(username, password, allowed_audiences, allowed_scopes, is_admin=is_admin, disabled=disabled)
        merged = False
        audience_set = set(existing.get("allowedAudiences") or [])
        scope_set = set(existing.get("allowedScopes") or [])
        next_audiences = sorted(audience_set.union({item for item in allowed_audiences if item}))
        next_scopes = sorted(scope_set.union({item for item in allowed_scopes if item}))
        if next_audiences != list(existing.get("allowedAudiences") or []):
            existing["allowedAudiences"] = next_audiences
            merged = True
        if next_scopes != list(existing.get("allowedScopes") or []):
            existing["allowedScopes"] = next_scopes
            merged = True
        if is_admin and not bool(existing.get("isAdmin")):
            existing["isAdmin"] = True
            merged = True
        if not disabled and bool(existing.get("disabled")):
            existing["disabled"] = False
            merged = True
        if merged:
            self.users[existing["username"]] = existing
            self._save()
        return existing

    def verify_password(self, username: str, password: str) -> dict[str, Any] | None:
        user = self.users.get(username)
        if not user or bool(user.get("disabled")):
            return None
        try:
            salt = base64.b64decode(str(user.get("salt") or ""))
        except Exception:
            return None
        expected = str(user.get("passwordHash") or "")
        candidate = self._hash_password(password, salt)
        if hmac.compare_digest(expected, candidate):
            return user
        return None

    def list_public(self) -> list[dict[str, Any]]:
        rows = []
        for user in sorted(self.users.values(), key=lambda item: item.get("username", "")):
            rows.append(
                {
                    "username": user.get("username"),
                    "allowedAudiences": list(user.get("allowedAudiences") or []),
                    "allowedScopes": list(user.get("allowedScopes") or []),
                    "isAdmin": bool(user.get("isAdmin")),
                    "disabled": bool(user.get("disabled")),
                }
            )
        return rows


def create_app() -> FastAPI:
    app = FastAPI(title="Wave STS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    scope_policy = _scope_policy()
    allow_anonymous_admin = _is_enabled(os.environ.get("WAVE_STS_ALLOW_ANONYMOUS_ADMIN"))
    users_path = Path(os.environ.get("WAVE_STS_USERS_PATH") or (Path(tempfile.gettempdir()) / "wave-sts-users.json"))
    users = UserStore(users_path)

    allowed = {
        item.strip()
        for item in (
            os.environ.get("WAVE_STS_ALLOWED_AUDIENCES")
            or "wave-sts,wavesearch-api,wavestore-erp-api,wavestore-frontend,wavestore-erp-frontend,wavesearch-frontend"
        ).split(",")
        if item.strip()
    }

    def validate_scopes(audience: str, scopes: list[str]) -> list[str]:
        allowed_scopes = scope_policy.get(audience, frozenset())
        invalid_scopes = sorted({scope for scope in scopes if scope not in allowed_scopes})
        if invalid_scopes:
            raise HTTPException(status_code=400, detail=f"scopes not allowed for audience {audience}: {', '.join(invalid_scopes)}")
        return scopes

    def sts_admin_context(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ) -> TenantContext:
        if allow_anonymous_admin and not authorization:
            return TenantContext(tenant_id=x_tenant_id or "system", scopes=frozenset({"sts.issue", "sts.validate", "sts.admin"}))
        return context_from_auth("wave-sts", authorization=authorization, x_tenant_id=x_tenant_id, require_tenant_header=True)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wave-sts"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse(STS_UI_HTML.read_text(encoding="utf-8"))
        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wave STS</title>
  <style>
    :root {
      --bg:#f5f1ff;
      --panel:#ffffff;
      --line:#d9cfef;
      --text:#1b1230;
      --muted:#6a5f85;
      --accent:#593196;
      --accent-2:#e06c00;
      --nav:#2d0f5e;
      --soft:#f8f4ff;
    }
    body { margin:0; font-family: "Segoe UI", Aptos, Calibri, sans-serif; background:var(--bg); color:var(--text); }
    .wrap { max-width:1150px; margin:0 auto; padding:20px; }
    .hero { background:linear-gradient(135deg, var(--nav) 0%, var(--accent) 55%, var(--accent-2) 100%); color:#fff; border-radius:14px; padding:16px; margin-bottom:12px; }
    .hero .muted { color:rgba(255,255,255,.85); }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px; margin-bottom:12px; box-shadow:0 6px 24px rgba(45,15,94,0.08); }
    .grid { display:grid; gap:10px; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); }
    input, textarea { width:100%; background:var(--soft); color:var(--text); border:1px solid var(--line); border-radius:10px; padding:10px; }
    textarea { min-height:160px; font-family: Consolas, monospace; }
    button { border:0; border-radius:10px; padding:10px 12px; background:var(--accent); color:#fff; font-weight:700; cursor:pointer; }
    pre { background:#1a122b; border:1px solid #2d1e4d; border-radius:10px; padding:10px; max-height:340px; overflow:auto; color:#d9cfef; }
    .muted { color: var(--muted); }
  </style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h2>Wave STS - User/Password + Token Admin</h2>
    <p class="muted">Manage demo users and issue/validate scoped tokens for retail + API frontends.</p>
  </div>
  <div class="panel">
    <div class="grid">
      <input id="tenant" value="demo-tenant" placeholder="Tenant">
      <input id="adminToken" placeholder="Admin Bearer token for /sts/users (optional in anonymous admin mode)">
    </div>
  </div>
  <div class="panel">
    <h3>Login test</h3>
    <div class="grid">
      <input id="username" value="sts.admin" placeholder="Username">
      <input id="password" value="demo123!" placeholder="Password" type="password">
      <input id="audience" value="wave-sts" placeholder="Audience">
      <input id="scopes" value="sts.issue,sts.validate,sts.admin" placeholder="Scopes CSV">
    </div>
    <button id="loginBtn">Login + issue token</button>
  </div>
  <div class="panel">
    <h3>User management</h3>
    <textarea id="userPayload">{"username":"promo.manager","password":"demo123!","allowedAudiences":["wavestore-erp-api","wavestore-erp-frontend"],"allowedScopes":["erp.read","erp.write"],"isAdmin":false}</textarea>
    <div class="grid">
      <button id="listUsersBtn">List users</button>
      <button id="createUserBtn">Create/update user</button>
      <button id="validateBtn">Validate token</button>
    </div>
  </div>
  <div class="panel"><pre id="out"></pre></div>
</div>
<script>
const out = document.getElementById("out");
async function call(path, method="GET", body=null, useAdminAuth=false) {
  const headers = { "Content-Type": "application/json", "X-Tenant-Id": document.getElementById("tenant").value || "demo-tenant" };
  if (useAdminAuth && document.getElementById("adminToken").value) headers.Authorization = "Bearer " + document.getElementById("adminToken").value.trim();
  const resp = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : null });
  const text = await resp.text();
  out.textContent = text;
  if (!resp.ok) throw new Error(text || "request failed");
  return JSON.parse(text);
}
document.getElementById("loginBtn").addEventListener("click", async () => {
  try {
    const scopes = document.getElementById("scopes").value.split(",").map(s => s.trim()).filter(Boolean);
    const data = await call("/sts/login", "POST", {
      tenant: document.getElementById("tenant").value || "demo-tenant",
      username: document.getElementById("username").value.trim(),
      password: document.getElementById("password").value,
      audience: document.getElementById("audience").value.trim(),
      scopes
    });
    if ((document.getElementById("audience").value || "").trim() === "wave-sts" && data.access_token) {
      document.getElementById("adminToken").value = data.access_token;
    }
  } catch (e) {}
});
document.getElementById("listUsersBtn").addEventListener("click", () => call("/sts/users", "GET", null, true).catch(() => {}));
document.getElementById("createUserBtn").addEventListener("click", () => {
  try {
    const payload = JSON.parse(document.getElementById("userPayload").value || "{}");
    call("/sts/users", "POST", payload, true).catch(() => {});
  } catch (e) { out.textContent = e.message; }
});
document.getElementById("validateBtn").addEventListener("click", () => {
  const token = (document.getElementById("adminToken").value || "").trim();
  const audience = (document.getElementById("audience").value || "").trim();
  call("/sts/validate", "POST", { token, audience }, true).catch(() => {});
});
</script>
</body>
</html>"""
        return HTMLResponse(html)

    @app.get("/sts/jwks")
    async def jwks() -> dict[str, Any]:
        return {
            "issuer": os.environ.get("WAVE_STS_ISSUER", "wave-sts"),
            "alg": "HS256",
            "kid": os.environ.get("WAVE_STS_KID", "wave-sts-hs256-v1"),
            "audiences": sorted(allowed),
        }

    @app.post("/sts/login")
    async def login(payload: dict[str, Any], x_tenant_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
        audience = str(payload.get("audience") or "wavesearch-api")
        if audience not in allowed:
            raise HTTPException(status_code=400, detail=f"audience not allowed: {audience}")
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        tenant = str(payload.get("tenant") or x_tenant_id or "demo-tenant")
        if not username or not password:
            raise HTTPException(status_code=400, detail="username and password are required")
        user = users.verify_password(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="invalid username or password")
        if audience not in set(user.get("allowedAudiences") or []):
            raise HTTPException(status_code=403, detail=f"user not allowed for audience: {audience}")
        requested_scopes = [str(scope) for scope in (payload.get("scopes") or [])]
        if not requested_scopes:
            requested_scopes = sorted(set(scope_policy.get(audience, frozenset())).intersection(set(user.get("allowedScopes") or [])))
        if not requested_scopes:
            raise HTTPException(status_code=400, detail="no permitted scopes for this user/audience")
        requested_scopes = validate_scopes(audience, requested_scopes)
        forbidden = sorted(set(requested_scopes) - set(user.get("allowedScopes") or []))
        if forbidden:
            raise HTTPException(status_code=403, detail=f"user not allowed scopes: {', '.join(forbidden)}")
        ttl_seconds = int(payload.get("ttlSeconds") or 900)
        ttl_seconds = max(60, min(3600, ttl_seconds))
        token = issuer_for_audience(audience).issue(username, tenant, requested_scopes, ttl_seconds=ttl_seconds)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "issuer": os.environ.get("WAVE_STS_ISSUER", "wave-sts"),
            "audience": audience,
            "tenant": tenant,
            "subject": username,
            "scope": " ".join(requested_scopes),
            "expires_in": ttl_seconds,
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
        requested_scopes = validate_scopes(audience, requested_scopes)
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
            token_context = issuer_for_audience(audience).verify(token)
            return {"active": True, "tenant": token_context.tenant_id, "scopes": sorted(token_context.scopes)}
        except ValueError as exc:
            return {"active": False, "error": str(exc)}

    @app.get("/sts/users")
    async def list_users(context: TenantContext = Depends(sts_admin_context)) -> dict[str, Any]:
        require_scope(context, "sts.admin")
        return {"users": users.list_public()}

    @app.post("/sts/users")
    async def upsert_user(payload: dict[str, Any], context: TenantContext = Depends(sts_admin_context)) -> dict[str, Any]:
        require_scope(context, "sts.admin")
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if not username or not password:
            raise HTTPException(status_code=400, detail="username and password are required")
        allowed_audiences = [str(item) for item in (payload.get("allowedAudiences") or [])]
        if not allowed_audiences:
            raise HTTPException(status_code=400, detail="allowedAudiences[] is required")
        invalid_audiences = sorted(set(allowed_audiences) - allowed)
        if invalid_audiences:
            raise HTTPException(status_code=400, detail=f"invalid audiences: {', '.join(invalid_audiences)}")
        allowed_scopes = [str(item) for item in (payload.get("allowedScopes") or [])]
        valid_scope_universe = set().union(*scope_policy.values())
        invalid_scopes = sorted(set(allowed_scopes) - valid_scope_universe)
        if invalid_scopes:
            raise HTTPException(status_code=400, detail=f"invalid scopes: {', '.join(invalid_scopes)}")
        row = users.create_user(
            username=username,
            password=password,
            allowed_audiences=allowed_audiences,
            allowed_scopes=allowed_scopes,
            is_admin=bool(payload.get("isAdmin")),
            disabled=bool(payload.get("disabled")),
        )
        return {
            "accepted": True,
            "user": {
                "username": row.get("username"),
                "allowedAudiences": row.get("allowedAudiences"),
                "allowedScopes": row.get("allowedScopes"),
                "isAdmin": bool(row.get("isAdmin")),
                "disabled": bool(row.get("disabled")),
            },
        }

    return app
