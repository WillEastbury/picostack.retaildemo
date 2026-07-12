"""Real email sending for WaveStore ERP order/payment/shipping notifications.

Transport: stdlib smtplib/email (no new dependency) -- an SmtpEmailProvider that actually
connects to a configured SMTP server (STARTTLS) and sends real HTML email. Gated behind
is_configured() exactly like the payment providers and SSO providers elsewhere in this
platform: a deployment with no SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD configured simply doesn't
send real email, but every send attempt is still recorded in the in-memory/persisted outbox
(status "sent" / "skipped_not_configured" / "failed") so the whole notification pipeline --
which event fired, what the rendered email looked like, whether it would have gone out -- is
fully verifiable and demoable without needing real SMTP credentials.

Templates are branded using the same whitelabel branding config (store name / logo / accent
color) the storefront itself uses (see wavestore_erp_api's BRANDING_DEFAULTS/branding field) --
plain Python string templates, no new templating dependency, consistent with the rest of this
codebase's dependency-free style.
"""

from __future__ import annotations

import html
import os
import smtplib
import time
from email.message import EmailMessage
from typing import Any


class EmailProvider:
    def is_configured(self) -> bool:
        raise NotImplementedError

    def send(self, to_address: str, subject: str, html_body: str, from_address: str) -> None:
        raise NotImplementedError


class SmtpEmailProvider(EmailProvider):
    def __init__(self) -> None:
        self.host = os.environ.get("SMTP_HOST", "").strip()
        self.port = int(os.environ.get("SMTP_PORT") or "587")
        self.username = os.environ.get("SMTP_USERNAME", "").strip()
        self.password = os.environ.get("SMTP_PASSWORD", "").strip()
        self.use_tls = str(os.environ.get("SMTP_USE_TLS", "true")).strip().lower() not in {"0", "false", "no"}

    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)

    def send(self, to_address: str, subject: str, html_body: str, from_address: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_address
        message["To"] = to_address
        message.set_content("This email requires an HTML-capable mail client to view.")
        message.add_alternative(html_body, subtype="html")
        with smtplib.SMTP(self.host, self.port, timeout=20) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(message)


_PROVIDER = SmtpEmailProvider()


def email_is_configured() -> bool:
    return _PROVIDER.is_configured()


def _branded_wrapper(branding: dict[str, Any], title: str, body_html: str) -> str:
    store_name = html.escape(str(branding.get("storeName") or "WaveStore"))
    logo_url = html.escape(str(branding.get("logoUrl") or ""))
    primary_color = html.escape(str(branding.get("primaryColor") or "#0d6efd"))
    logo_img = f'<img src="{logo_url}" alt="{store_name}" width="32" height="32" style="border-radius:6px;vertical-align:middle;margin-right:8px;">' if logo_url else ""
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f4f7;font-family:Segoe UI,Arial,sans-serif;color:#1b1230;">
  <div style="max-width:560px;margin:0 auto;padding:24px;">
    <div style="background:{primary_color};border-radius:10px 10px 0 0;padding:18px 22px;color:#ffffff;">
      {logo_img}<span style="font-size:20px;font-weight:700;vertical-align:middle;">{store_name}</span>
    </div>
    <div style="background:#ffffff;border:1px solid #e2e2ea;border-top:0;border-radius:0 0 10px 10px;padding:22px;">
      <h2 style="margin-top:0;color:#1b1230;">{html.escape(title)}</h2>
      {body_html}
    </div>
    <p style="text-align:center;color:#8a8a99;font-size:12px;margin-top:16px;">&copy; {time.strftime('%Y')} {store_name}. All rights reserved.</p>
  </div>
</body></html>"""


def _line_items_html(items: list[dict[str, Any]], product_titles: dict[str, str]) -> str:
    rows = []
    for item in items:
        product_id = str(item.get("productId") or "")
        title = html.escape(product_titles.get(product_id, product_id))
        qty = item.get("quantity", 1)
        price = item.get("price", 0.0)
        rows.append(
            f'<tr><td style="padding:6px 0;border-bottom:1px solid #eee;">{title}</td>'
            f'<td style="padding:6px 0;border-bottom:1px solid #eee;text-align:center;">x{qty}</td>'
            f'<td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;">£{price:.2f}</td></tr>'
        )
    return f'<table style="width:100%;border-collapse:collapse;margin:12px 0;">{"".join(rows)}</table>'


def render_order_confirmation(branding: dict[str, Any], order: dict[str, Any], product_titles: dict[str, str]) -> tuple[str, str]:
    subject = f"Your order {order.get('id')} is confirmed"
    body = (
        f'<p>Thanks for your order! Here\'s a summary:</p>'
        f'{_line_items_html(order.get("items") or [], product_titles)}'
        f'<p style="text-align:right;font-weight:700;font-size:16px;">Total: £{float(order.get("total") or 0):.2f}</p>'
        f'<p style="color:#666;font-size:13px;">Order ID: {html.escape(str(order.get("id")))}</p>'
    )
    return subject, _branded_wrapper(branding, "Order confirmed", body)


def render_payment_received(branding: dict[str, Any], invoice: dict[str, Any]) -> tuple[str, str]:
    subject = f"Payment received for invoice {invoice.get('id')}"
    body = (
        f'<p>We\'ve received your payment of <strong>£{float(invoice.get("amount") or 0):.2f}</strong>. '
        f"Thank you for shopping with us!</p>"
        f'<p style="color:#666;font-size:13px;">Invoice ID: {html.escape(str(invoice.get("id")))} &middot; Order ID: {html.escape(str(invoice.get("orderId")))}</p>'
    )
    return subject, _branded_wrapper(branding, "Payment received", body)


def render_order_shipped(branding: dict[str, Any], order: dict[str, Any]) -> tuple[str, str]:
    subject = f"Your order {order.get('id')} has shipped"
    tracking = order.get("trackingNumber")
    carrier = order.get("carrier")
    tracking_html = f'<p>Carrier: {html.escape(str(carrier))}<br>Tracking number: <strong>{html.escape(str(tracking))}</strong></p>' if tracking else ""
    body = f"<p>Good news -- your order is on its way!</p>{tracking_html}" f'<p style="color:#666;font-size:13px;">Order ID: {html.escape(str(order.get("id")))}</p>'
    return subject, _branded_wrapper(branding, "Order shipped", body)


def render_order_delivered(branding: dict[str, Any], order: dict[str, Any]) -> tuple[str, str]:
    subject = f"Your order {order.get('id')} was delivered"
    body = f"<p>Your order has been delivered. We hope you enjoy it!</p>" f'<p style="color:#666;font-size:13px;">Order ID: {html.escape(str(order.get("id")))}</p>'
    return subject, _branded_wrapper(branding, "Order delivered", body)


RENDERERS = {
    "order_confirmation": render_order_confirmation,
    "payment_received": render_payment_received,
    "order_shipped": render_order_shipped,
    "order_delivered": render_order_delivered,
}


def send_event_email(
    outbox: list[dict[str, Any]],
    event_type: str,
    to_address: str | None,
    branding: dict[str, Any],
    from_address: str,
    max_outbox_entries: int = 200,
    **template_args: Any,
) -> dict[str, Any]:
    """Renders and (attempts to) send a templated notification email for one event, always
    appending a record to `outbox` regardless of whether SMTP is actually configured -- this is
    what makes the whole pipeline verifiable/demoable without real credentials. `outbox` is
    mutated in place (append + trim) so callers just need to persist it afterward."""
    renderer = RENDERERS.get(event_type)
    entry: dict[str, Any] = {
        "eventType": event_type,
        "to": to_address,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if renderer is None:
        entry["status"] = "failed"
        entry["error"] = f"unknown email event type: {event_type}"
        outbox.append(entry)
        return entry
    if not to_address:
        entry["status"] = "skipped_no_recipient"
        outbox.append(entry)
        return entry
    subject, html_body = renderer(branding, **template_args)
    entry["subject"] = subject
    entry["htmlPreview"] = html_body
    if not email_is_configured():
        entry["status"] = "skipped_not_configured"
        outbox.append(entry)
    else:
        try:
            _PROVIDER.send(to_address, subject, html_body, from_address)
            entry["status"] = "sent"
        except Exception as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
        outbox.append(entry)
    del outbox[: max(0, len(outbox) - max_outbox_entries)]
    return entry
