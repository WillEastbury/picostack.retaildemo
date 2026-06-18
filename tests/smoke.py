from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.retail_demo_server import RetailBridge, make_routes
from src.picoscript_runner import route_action
from src.retail_voice_tools import RetailVoiceToolContext
from picoweb_core import Response, parse_request, dispatch


ROOT = Path(__file__).resolve().parents[1]


def call(routes, method: str, path: str, body: dict | None = None):
    raw = json.dumps(body or {}).encode("utf-8") if body is not None else b""
    request = parse_request(method, path, {}, raw)
    response = dispatch(routes, request)
    assert response.status < 500, response.body
    if response.content_type.startswith("application/json"):
        return json.loads(response.body.decode("utf-8"))
    return response.body.decode("utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bridge = RetailBridge(ROOT / "build" / "libpicostack_retail_demo.so", Path(tmp))
        routes = make_routes(bridge)
        assert route_action(1, 1, 1) == (1, 2)
        assert route_action(20, 2, 20) == (20, 2)
        assert route_action(21, 2, 21) == (21, 2)
        assert route_action(22, 1, 22) == (22, 2)
        assert route_action(20, 1, 1) == (0, 4)
        home = call(routes, "GET", "/")
        assert "siteName" in home
        assert "loadCMS" in home
        assert "BareMetal.Communications" in home
        assert call(routes, "POST", "/api/retail/products:ingestDemo", {})["ingested"] is True
        cms = call(routes, "GET", "/api/cms/config")
        assert cms["Metadata"]["SiteName"] == "Pico Outfitters"
        pages = call(routes, "GET", "/api/cms/pages")
        assert any(page["RelativeUrl"] == "checkout" for page in pages["pages"])
        page = call(routes, "GET", "/api/cms/pages/home")
        assert page["page"]["Hero"]["Title"]
        assert page["Rendered"].startswith("Pico Outfitters ::")
        store_sample = call(routes, "GET", "/api/storage/Store/sample")
        assert store_sample["Title"] == "Pico Outfitters"
        products = call(routes, "GET", "/api/retail/products")
        assert products["totalSize"] >= 1
        sample = call(routes, "GET", "/api/demo/catalog")
        assert sample["site"]["SiteName"] == "Pico Outfitters"
        assert sample["customers"]
        assert sample["promotions"]
        assert sample["shippingMethods"]
        assert sample["paymentMethods"]
        search = call(routes, "POST", "/api/retail/search", {"query": "waterproof jacket"})
        assert search["results"]
        detail = call(routes, "GET", "/api/retail/products/aurora-shell")
        assert detail["brand"] == "Contoso Trail"
        recs = call(routes, "POST", "/api/retail/recommend", {"id": "aurora-shell"})
        assert "results" in recs
        event = call(routes, "POST", "/api/retail/events", {"visitorId": "demo", "eventType": "detail-page-view", "productId": "aurora-shell"})
        assert event["accepted"] is True
        cart = call(routes, "POST", "/api/retail/cart", {"cartId": "demo-cart", "productId": "aurora-shell", "quantity": 2})
        assert cart["subtotal"] > 0
        assert cart["lines"][0]["quantity"] == 2
        cart = call(routes, "PUT", "/api/retail/cart/demo-cart", {"productId": "aurora-shell", "quantity": 1})
        assert cart["lines"][0]["quantity"] == 1
        checkout = call(
            routes,
            "POST",
            "/api/retail/checkout",
            {
                "cartId": "demo-cart",
                "customerId": "cust-demo-hiker",
                "shippingMethodId": "standard",
                "paymentMethodId": "demo-card",
                "promoCode": "SUMMIT10",
            },
        )
        assert checkout["order"]["status"] == "CONFIRMED"
        assert checkout["order"]["summary"]["total"] > 0
        assert checkout["order"]["summary"]["policy"] == "picoscript:checkout_policy.pc"
        order = call(routes, "GET", f"/api/retail/orders/{checkout['order']['id']}")
        assert order["order"]["id"] == checkout["order"]["id"]
        callback = call(
            routes,
            "POST",
            "/api/retail/call-me",
            {
                "name": "Avery Hill",
                "phone": "+447700900123",
                "reason": "Help finding waterproof jackets and checking stock",
                "topic": "find",
                "productId": "aurora-shell",
            },
        )
        assert callback["callback"]["status"] == "REQUESTED"
        callbacks = call(routes, "GET", "/api/retail/callbacks")
        assert callbacks["callbacks"][0]["phone"] == "+447700900123"
        voice_tools = RetailVoiceToolContext(bridge)
        found = voice_tools.call_tool("find_items", {"query": "coffee drinks"})
        assert "results" in found
        stock = voice_tools.call_tool("check_stock", {"query": "drill hardware"})
        assert stock["found"] is True
        order = voice_tools.call_tool("order_items", {"product_id": "aurora-shell", "quantity": 1, "customer_name": "Avery"})
        assert order["ordered"] is True
        shipping = voice_tools.call_tool("check_shipping_status", {"order_id": order["order"]["id"]})
        assert shipping["found"] is True
    print("picostack retail demo smoke ok")


if __name__ == "__main__":
    main()
