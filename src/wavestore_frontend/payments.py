"""Modular checkout payment provider abstraction for WaveStore.

Adding/removing a payment provider is a config change (env vars), not a rewrite: every provider
implements the same PaymentProvider interface (create_intent / capture / provider metadata), and
the checkout endpoints in wavestore_frontend/app.py only ever talk to that interface, never a
specific provider's SDK directly.

Providers:
  - NativeProvider:  the original (and default) behavior -- no external payment gateway at all,
                     checkout goes straight to wavestore-erp-api's /erp/orders. Always available,
                     requires no configuration, and is what every existing checkout call already
                     did before this module existed (kept 100% backward compatible).
  - StripeProvider:  real Stripe integration (Payment Intents API) -- creates a real
                     PaymentIntent server-side and returns its client_secret for Stripe.js/
                     Stripe Elements to confirm in the browser, then the confirm step verifies
                     the PaymentIntent's status before the ERP order is placed.
  - PayPalProvider:  real PayPal integration (Orders v2 API) -- creates a real PayPal Order and
                     returns its approval link for PayPal's JS SDK/redirect flow, then the
                     confirm step captures the order before the ERP order is placed.

Both StripeProvider and PayPalProvider require real API credentials (env vars below) to do
anything -- without them, is_configured() returns False and the provider registry silently
excludes them from GET /v2/checkout/providers, so a deployment with no payment gateway
credentials configured behaves exactly like it did before this module existed (native-only).
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlencode


@dataclass
class PaymentIntentResult:
    """What create_intent() hands back to the browser to complete payment."""

    provider: str
    intentId: str
    status: str  # "requires_action" | "requires_capture" | "succeeded" | "created"
    clientSecret: str | None = None  # Stripe: pass to Stripe.js confirmCardPayment
    approvalUrl: str | None = None  # PayPal: redirect/open in a popup for buyer approval
    amount: float = 0.0
    currency: str = "GBP"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "intentId": self.intentId,
            "status": self.status,
            "clientSecret": self.clientSecret,
            "approvalUrl": self.approvalUrl,
            "amount": self.amount,
            "currency": self.currency,
            **self.extra,
        }


@dataclass
class CaptureResult:
    """What capture()/confirm() hands back once payment has actually been taken."""

    provider: str
    intentId: str
    status: str  # "succeeded" | "failed"
    amountCaptured: float = 0.0
    currency: str = "GBP"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "intentId": self.intentId,
            "status": self.status,
            "amountCaptured": self.amountCaptured,
            "currency": self.currency,
            **self.extra,
        }


class PaymentProvider(ABC):
    """The one interface every payment provider (present or future) must implement. Checkout
    code in wavestore_frontend/app.py only ever calls these three methods -- never a provider-
    specific SDK/API directly -- so adding a new provider (e.g. a future "AmazonPay" or
    "GooglePay") means writing one new class here and registering it in PROVIDERS, nothing else
    in the checkout flow changes."""

    name: str = "unknown"

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this provider has the credentials/config it needs to actually run. Providers
        that return False are excluded from GET /v2/checkout/providers -- a deployment with no
        Stripe/PayPal keys set simply never offers them as an option."""

    @abstractmethod
    def create_intent(self, order_ref: str, amount: float, currency: str, metadata: dict[str, Any]) -> PaymentIntentResult:
        """Start a payment for `amount`/`currency` against an as-yet-unplaced order reference.
        Returns whatever the browser needs to complete payment (a client secret, an approval
        URL, or for the native provider, an immediately-succeeded result)."""

    @abstractmethod
    def capture(self, intent_id: str, metadata: dict[str, Any]) -> CaptureResult:
        """Confirm/capture a previously created intent once the buyer has completed the
        provider-side payment step in the browser. Must be idempotent -- calling it twice for an
        already-captured intent should return the same success result, not error."""


class NativeProvider(PaymentProvider):
    """The original checkout behavior: no payment gateway at all, the ERP order IS the payment
    record (this is a demo platform -- "payment" here just means placing the order). Always
    configured, requires no setup, and is the default so nothing breaks for existing callers."""

    name = "native"

    def is_configured(self) -> bool:
        return True

    def create_intent(self, order_ref: str, amount: float, currency: str, metadata: dict[str, Any]) -> PaymentIntentResult:
        return PaymentIntentResult(provider=self.name, intentId=f"native-{order_ref}", status="succeeded", amount=amount, currency=currency)

    def capture(self, intent_id: str, metadata: dict[str, Any]) -> CaptureResult:
        return CaptureResult(provider=self.name, intentId=intent_id, status="succeeded")


def _json_request(url: str, method: str, body: dict[str, Any] | None, headers: dict[str, str]) -> Any:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req_headers = dict(headers)
    if body is not None:
        req_headers.setdefault("Content-Type", "application/json")
    req = Request(url=url, method=method, data=payload, headers=req_headers)
    with urlopen(req, timeout=20) as response:  # nosec B310 - trusted, configured payment gateway endpoint
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


class StripeProvider(PaymentProvider):
    """Real Stripe integration via the Payment Intents API (no stripe-python SDK dependency --
    plain HTTPS calls to Stripe's REST API, keeping this module dependency-free like the rest of
    this platform's LLM/embedding integrations). Requires STRIPE_SECRET_KEY (a real test-mode or
    live secret key, e.g. sk_test_...) to be configured.

    Flow: create_intent() creates a Stripe PaymentIntent server-side and returns its
    client_secret for Stripe.js/Stripe Elements to confirm card details in the browser (Stripe
    handles all card data -- it never touches this server). capture() re-fetches the
    PaymentIntent and checks its status is "succeeded" before allowing the ERP order to be
    placed."""

    name = "stripe"
    API_BASE = "https://api.stripe.com/v1"

    def __init__(self) -> None:
        self.secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()

    def is_configured(self) -> bool:
        return bool(self.secret_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/x-www-form-urlencoded"}

    def _form_request(self, path: str, method: str, fields: dict[str, Any]) -> Any:
        body = urlencode(fields).encode("utf-8")
        req = Request(url=f"{self.API_BASE}{path}", method=method, data=body, headers=self._headers())
        try:
            with urlopen(req, timeout=20) as response:  # nosec B310 - Stripe's official REST API endpoint
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Stripe API error ({exc.code}): {detail}") from exc

    def create_intent(self, order_ref: str, amount: float, currency: str, metadata: dict[str, Any]) -> PaymentIntentResult:
        # Stripe amounts are in the currency's smallest unit (pence for GBP), never a float.
        amount_minor = int(round(amount * 100))
        fields = {
            "amount": amount_minor,
            "currency": currency.lower(),
            "metadata[orderRef]": order_ref,
            **{f"metadata[{k}]": str(v) for k, v in metadata.items()},
        }
        data = self._form_request("/payment_intents", "POST", fields)
        return PaymentIntentResult(
            provider=self.name,
            intentId=data["id"],
            status="requires_action" if data.get("status") != "succeeded" else "succeeded",
            clientSecret=data.get("client_secret"),
            amount=amount,
            currency=currency,
        )

    def capture(self, intent_id: str, metadata: dict[str, Any]) -> CaptureResult:
        data = self._form_request(f"/payment_intents/{intent_id}", "GET", {})
        status = "succeeded" if data.get("status") == "succeeded" else "failed"
        return CaptureResult(
            provider=self.name,
            intentId=intent_id,
            status=status,
            amountCaptured=(data.get("amount_received") or 0) / 100.0,
            currency=str(data.get("currency") or "gbp").upper(),
            extra={"stripeStatus": data.get("status")},
        )


class PayPalProvider(PaymentProvider):
    """Real PayPal integration via the Orders v2 REST API. Requires PAYPAL_CLIENT_ID and
    PAYPAL_CLIENT_SECRET (sandbox or live app credentials). Uses PAYPAL_API_BASE to select
    sandbox (default, https://api-m.sandbox.paypal.com) vs live (https://api-m.paypal.com).

    Flow: create_intent() creates a PayPal Order and returns its approval link for PayPal's JS
    SDK (or a redirect) to send the buyer to approve payment. capture() calls PayPal's
    /v2/checkout/orders/{id}/capture endpoint, which actually takes the payment once the buyer
    has approved it, and only then allows the ERP order to be placed."""

    name = "paypal"

    def __init__(self) -> None:
        self.client_id = os.environ.get("PAYPAL_CLIENT_ID", "").strip()
        self.client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "").strip()
        self.api_base = os.environ.get("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com").rstrip("/")
        self._cached_token: str | None = None

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _access_token(self) -> str:
        if self._cached_token:
            return self._cached_token
        body = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
        req = Request(
            url=f"{self.api_base}/v1/oauth2/token",
            method="POST",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # Basic auth with client_id:client_secret -- PayPal's OAuth token endpoint requires this
        # even though the rest of the API uses bearer tokens.
        import base64

        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {auth}")
        try:
            with urlopen(req, timeout=20) as response:  # nosec B310 - PayPal's official OAuth endpoint
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"PayPal OAuth error ({exc.code}): {detail}") from exc
        self._cached_token = data["access_token"]
        return self._cached_token

    def create_intent(self, order_ref: str, amount: float, currency: str, metadata: dict[str, Any]) -> PaymentIntentResult:
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        body = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": order_ref,
                    "amount": {"currency_code": currency.upper(), "value": f"{amount:.2f}"},
                    "custom_id": order_ref,
                }
            ],
        }
        data = _json_request(f"{self.api_base}/v2/checkout/orders", "POST", body, headers)
        approval_url = next((link["href"] for link in data.get("links", []) if link.get("rel") == "approve"), None)
        return PaymentIntentResult(
            provider=self.name,
            intentId=data["id"],
            status="requires_action",
            approvalUrl=approval_url,
            amount=amount,
            currency=currency,
        )

    def capture(self, intent_id: str, metadata: dict[str, Any]) -> CaptureResult:
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        data = _json_request(f"{self.api_base}/v2/checkout/orders/{intent_id}/capture", "POST", {}, headers)
        status = "succeeded" if data.get("status") == "COMPLETED" else "failed"
        captured_amount = 0.0
        currency = "GBP"
        try:
            capture_row = data["purchase_units"][0]["payments"]["captures"][0]
            captured_amount = float(capture_row["amount"]["value"])
            currency = capture_row["amount"]["currency_code"]
        except (KeyError, IndexError, TypeError, ValueError):
            pass
        return CaptureResult(provider=self.name, intentId=intent_id, status=status, amountCaptured=captured_amount, currency=currency, extra={"paypalStatus": data.get("status")})


# Registry: every known provider, in the preferred display order. Extending the platform with a
# new payment provider means adding one entry here (and its class above) -- nothing else in the
# checkout flow (wavestore_frontend/app.py) needs to change.
_ALL_PROVIDERS: dict[str, PaymentProvider] = {
    "native": NativeProvider(),
    "stripe": StripeProvider(),
    "paypal": PayPalProvider(),
}


def available_providers() -> list[PaymentProvider]:
    """Providers that are actually usable in this deployment (native is always included)."""
    return [p for p in _ALL_PROVIDERS.values() if p.is_configured()]


def get_provider(name: str) -> PaymentProvider:
    provider = _ALL_PROVIDERS.get(name)
    if provider is None or not provider.is_configured():
        # Fall back to native rather than erroring -- a checkout request naming an unconfigured
        # provider (e.g. a stale client that cached "stripe" from before keys were removed)
        # should still complete, not hard-fail a shopper's purchase.
        return _ALL_PROVIDERS["native"]
    return provider
