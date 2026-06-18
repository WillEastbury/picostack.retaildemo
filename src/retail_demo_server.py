from __future__ import annotations

import argparse
import ctypes
import json
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PICOWEB_SRC = ROOT.parent / "picoweb" / "src"
BAREMETAL_SRC = ROOT.parent / "BareMetalJsTools" / "src"
CMS_PATH = ROOT / "content" / "site.json"
if str(PICOWEB_SRC) not in sys.path:
    sys.path.insert(0, str(PICOWEB_SRC))

from picoweb_core import Request, Response, Route  # noqa: E402
from picoweb_server import run_server  # noqa: E402
from src.picoscript_runner import checkout_totals_pence, render_template, route_action  # noqa: E402


DEMO_CUSTOMERS = [
    {
        "id": "cust-demo-hiker",
        "name": "Avery Hill",
        "email": "avery.hill@example.test",
        "loyaltyTier": "Summit",
        "defaultAddress": {
            "line1": "14 Ridge Lane",
            "city": "Keswick",
            "postcode": "CA12 5AA",
            "country": "GB",
        },
    },
    {
        "id": "cust-demo-skier",
        "name": "Morgan Vale",
        "email": "morgan.vale@example.test",
        "loyaltyTier": "Basecamp",
        "defaultAddress": {
            "line1": "22 Alpine Close",
            "city": "Aviemore",
            "postcode": "PH22 1QB",
            "country": "GB",
        },
    },
]

DEMO_PROMOTIONS = [
    {"code": "SUMMIT10", "description": "10% off demo order", "type": "percent", "value": 10.0},
    {"code": "FREESHIP", "description": "Free standard delivery", "type": "shipping", "value": 0.0},
]

DEMO_SHIPPING = [
    {"id": "standard", "name": "Standard delivery", "price": 3.95, "eta": "3-5 working days"},
    {"id": "express", "name": "Express delivery", "price": 8.95, "eta": "1-2 working days"},
    {"id": "pickup", "name": "Store pickup", "price": 0.0, "eta": "Ready tomorrow"},
]

DEMO_PAYMENT_METHODS = [
    {"id": "demo-card", "label": "Demo Visa ending 4242", "type": "card"},
    {"id": "demo-wallet", "label": "Demo wallet", "type": "wallet"},
]


def load_cms() -> dict[str, Any]:
    return json.loads(CMS_PATH.read_text(encoding="utf-8"))


class RetailBridge:
    def __init__(self, library: Path, store_root: Path) -> None:
        self._lib = ctypes.CDLL(str(library))
        self._configure()
        store_root.mkdir(parents=True, exist_ok=True)
        if self._lib.demo_init(str(store_root).encode("utf-8")) != 1:
            raise RuntimeError(f"failed to initialize PicoWAL store at {store_root}")

    def _configure(self) -> None:
        self._lib.demo_init.argtypes = [ctypes.c_char_p]
        self._lib.demo_init.restype = ctypes.c_int
        for name in ["demo_ingest", "demo_products"]:
            fn = getattr(self._lib, name)
            fn.argtypes = []
            fn.restype = ctypes.c_char_p
        for name in ["demo_product", "demo_search", "demo_recommend"]:
            fn = getattr(self._lib, name)
            fn.argtypes = [ctypes.c_char_p]
            fn.restype = ctypes.c_char_p
        self._lib.demo_event.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self._lib.demo_event.restype = ctypes.c_char_p

    def _decode(self, value: bytes) -> Any:
        return json.loads(value.decode("utf-8"))

    def ingest(self) -> Any:
        return self._decode(self._lib.demo_ingest())

    def products(self) -> Any:
        return self._decode(self._lib.demo_products())

    def product(self, product_id: str) -> Any:
        return self._decode(self._lib.demo_product(product_id.encode("utf-8")))

    def search(self, query: str) -> Any:
        return self._decode(self._lib.demo_search(query.encode("utf-8")))

    def recommend(self, product_id: str) -> Any:
        return self._decode(self._lib.demo_recommend(product_id.encode("utf-8")))

    def event(self, visitor_id: str, event_type: str, product_id: str) -> Any:
        return self._decode(
            self._lib.demo_event(
                visitor_id.encode("utf-8"),
                event_type.encode("utf-8"),
                product_id.encode("utf-8"),
            )
        )


def json_body(request: Request) -> dict[str, Any]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def html_response(response: Response, body: str) -> Response:
    response.content_type = "text/html; charset=utf-8"
    response.body = body.encode("utf-8")
    response.headers["Content-Length"] = str(len(response.body))
    return response


def bytes_response(response: Response, body: bytes, content_type: str) -> Response:
    response.content_type = content_type
    response.body = body
    response.headers["Content-Length"] = str(len(body))
    return response


def make_routes(bridge: RetailBridge) -> list[Route]:
    storefront = (ROOT / "www" / "index.html").read_text(encoding="utf-8")
    cms = load_cms()
    carts: dict[str, dict[str, Any]] = {}
    orders: dict[str, dict[str, Any]] = {}
    callbacks: list[dict[str, Any]] = []

    def require_action(action: int, method: int, path: int) -> None:
        actual, status_class = route_action(action, method, path)
        if actual != action or status_class != 2:
            raise RuntimeError(f"PicoScript route policy rejected action {action}")

    def home(_request: Request, response: Response) -> Response:
        require_action(1, 1, 1)
        site = cms.get("Metadata", {})
        page = next((item for item in cms.get("Pages", []) if item.get("RelativeUrl") == "home"), {})
        rendered = render_template(
            storefront,
            {
                "SiteName": str(site.get("SiteName", "")),
                "SiteTitle": str(site.get("SiteTitle", "")),
                "SiteDescription": str(site.get("SiteDescription", "")),
                "HomePageTitle": str(page.get("PageTitle", "")),
            },
        )
        return html_response(response, rendered)

    def baremetal(request: Request, response: Response) -> Response:
        require_action(2, 1, 2)
        name = request.params["name"]
        allowed = {"BareMetal.Communications.js", "BareMetal.Search.js"}
        if name not in allowed:
            response.status = 404
            response.body = b"not found"
            response.content_type = "text/plain"
            return response
        path = BAREMETAL_SRC / name
        return bytes_response(response, path.read_bytes(), "application/javascript")

    def ingest(_request: Request, response: Response) -> Response:
        require_action(3, 2, 3)
        return response.with_json(bridge.ingest())

    def products(_request: Request, response: Response) -> Response:
        require_action(4, 1, 4)
        return response.with_json(bridge.products())

    def cms_config(_request: Request, response: Response) -> Response:
        require_action(5, 1, 5)
        return response.with_json(cms)

    def cms_pages(_request: Request, response: Response) -> Response:
        require_action(6, 1, 6)
        pages = [page for page in cms.get("Pages", []) if not page.get("IsHidden")]
        return response.with_json({"pages": pages})

    def cms_page(request: Request, response: Response) -> Response:
        require_action(7, 1, 7)
        slug = request.params["slug"]
        page = next((item for item in cms.get("Pages", []) if item.get("RelativeUrl") == slug), None)
        if page is None:
            response.status = 404
            return response.with_json({"error": "page not found"})
        site = cms.get("Metadata", {})
        rendered = render_template(
            "{{SiteName}} :: {{PageTitle}} :: {{MarkdownContent}}",
            {
                "SiteName": str(site.get("SiteName", "")),
                "PageTitle": str(page.get("PageTitle", "")),
                "MarkdownContent": str(page.get("MarkdownContent", "")),
            },
        )
        return response.with_json({"page": page, "Site": site, "Store": cms.get("Store", {}), "Rendered": rendered})

    def sample_catalog(_request: Request, response: Response) -> Response:
        require_action(8, 1, 8)
        return response.with_json(
            {
                "site": cms.get("Metadata", {}),
                "pages": cms.get("Pages", []),
                "store": cms.get("Store", {}),
                "catalog": bridge.products(),
                "customers": DEMO_CUSTOMERS,
                "promotions": DEMO_PROMOTIONS,
                "shippingMethods": DEMO_SHIPPING,
                "paymentMethods": DEMO_PAYMENT_METHODS,
            }
        )

    def sample_customers(_request: Request, response: Response) -> Response:
        require_action(9, 1, 9)
        return response.with_json({"customers": DEMO_CUSTOMERS})

    def sample_promotions(_request: Request, response: Response) -> Response:
        require_action(10, 1, 10)
        return response.with_json({"promotions": DEMO_PROMOTIONS})

    def sample_shipping(_request: Request, response: Response) -> Response:
        require_action(11, 1, 11)
        return response.with_json({"shippingMethods": DEMO_SHIPPING})

    def sample_payments(_request: Request, response: Response) -> Response:
        require_action(12, 1, 12)
        return response.with_json({"paymentMethods": DEMO_PAYMENT_METHODS})

    def storage_sample(request: Request, response: Response) -> Response:
        require_action(13, 1, 13)
        object_type = request.params["objectType"]
        if object_type == "Product":
            return response.with_json(bridge.products())
        if object_type == "Store":
            return response.with_json(cms.get("Store", {}))
        if object_type == "Page":
            return response.with_json({"pages": cms.get("Pages", [])})
        if object_type == "Basket":
            return response.with_json(build_cart("demo-cart"))
        response.status = 404
        return response.with_json({"error": "sample type not found"})

    def product(request: Request, response: Response) -> Response:
        require_action(14, 1, 14)
        payload = bridge.product(request.params["id"])
        if "error" in payload:
            response.status = 404
        return response.with_json(payload)

    def search(request: Request, response: Response) -> Response:
        require_action(15, 2, 15)
        payload = json_body(request)
        return response.with_json(bridge.search(str(payload.get("query", ""))))

    def recommend(request: Request, response: Response) -> Response:
        require_action(16, 2, 16)
        payload = json_body(request)
        return response.with_json(bridge.recommend(str(payload.get("id", ""))))

    def event(request: Request, response: Response) -> Response:
        require_action(17, 2, 17)
        payload = json_body(request)
        return response.with_json(
            bridge.event(
                str(payload.get("visitorId", "demo")),
                str(payload.get("eventType", "detail-page-view")),
                str(payload.get("productId", "")),
            )
        )

    def get_product_map() -> dict[str, dict[str, Any]]:
        products_payload = bridge.products()
        return {str(item["id"]): item for item in products_payload.get("products", [])}

    def build_cart(cart_id: str) -> dict[str, Any]:
        cart = carts.setdefault(cart_id, {"id": cart_id, "items": []})
        product_map = get_product_map()
        lines = []
        subtotal = 0.0
        for item in cart["items"]:
            product = product_map.get(item["productId"])
            if not product:
                continue
            quantity = max(1, int(item.get("quantity", 1)))
            price = float(product.get("price", 0.0))
            total = round(price * quantity, 2)
            subtotal += total
            lines.append({"product": product, "quantity": quantity, "lineTotal": total})
        cart["lines"] = lines
        cart["subtotal"] = round(subtotal, 2)
        return cart

    def cart_get(request: Request, response: Response) -> Response:
        require_action(18, 1, 18)
        return response.with_json(build_cart(request.params["id"]))

    def cart_add(request: Request, response: Response) -> Response:
        require_action(19, 2, 19)
        payload = json_body(request)
        cart_id = str(payload.get("cartId") or "demo-cart")
        product_id = str(payload.get("productId") or "")
        quantity = max(1, int(payload.get("quantity") or 1))
        product_map = get_product_map()
        if product_id not in product_map:
            response.status = 404
            return response.with_json({"error": "product not found"})
        cart = carts.setdefault(cart_id, {"id": cart_id, "items": []})
        for item in cart["items"]:
            if item["productId"] == product_id:
                item["quantity"] = max(1, int(item.get("quantity", 1))) + quantity
                break
        else:
            cart["items"].append({"productId": product_id, "quantity": quantity})
        return response.with_json(build_cart(cart_id))

    def cart_update(request: Request, response: Response) -> Response:
        require_action(20, 3, 20)
        payload = json_body(request)
        cart_id = request.params["id"]
        product_id = str(payload.get("productId") or "")
        quantity = max(0, int(payload.get("quantity") or 0))
        cart = carts.setdefault(cart_id, {"id": cart_id, "items": []})
        updated = []
        for item in cart["items"]:
            if item["productId"] == product_id:
                if quantity:
                    item["quantity"] = quantity
                    updated.append(item)
                continue
            updated.append(item)
        cart["items"] = updated
        return response.with_json(build_cart(cart_id))

    def checkout(request: Request, response: Response) -> Response:
        require_action(20, 2, 20)
        payload = json_body(request)
        cart_id = str(payload.get("cartId") or "demo-cart")
        customer_id = str(payload.get("customerId") or DEMO_CUSTOMERS[0]["id"])
        shipping_id = str(payload.get("shippingMethodId") or "standard")
        payment_id = str(payload.get("paymentMethodId") or "demo-card")
        promo_code = str(payload.get("promoCode") or "").upper()

        customer = next((item for item in DEMO_CUSTOMERS if item["id"] == customer_id), DEMO_CUSTOMERS[0])
        shipping = next((item for item in DEMO_SHIPPING if item["id"] == shipping_id), DEMO_SHIPPING[0])
        payment = next((item for item in DEMO_PAYMENT_METHODS if item["id"] == payment_id), DEMO_PAYMENT_METHODS[0])
        promotion = next((item for item in DEMO_PROMOTIONS if item["code"] == promo_code), None)
        cart = build_cart(cart_id)
        subtotal = float(cart["subtotal"])
        shipping_price = float(shipping["price"])
        discount_percent = 0
        if promotion and promotion["type"] == "percent":
            discount_percent = int(float(promotion["value"]))
        if promotion and promotion["type"] == "shipping":
            shipping_price = 0.0
        totals = checkout_totals_pence(
            int(round(subtotal * 100)),
            int(round(shipping_price * 100)),
            discount_percent,
        )
        discount = round(totals["discount"] / 100.0, 2)
        tax = round(totals["tax"] / 100.0, 2)
        total = round(totals["total"] / 100.0, 2)
        order_id = "ord-" + uuid.uuid4().hex[:10]
        order = {
            "id": order_id,
            "status": "CONFIRMED",
            "cart": cart,
            "customer": customer,
            "shippingMethod": shipping,
            "paymentMethod": payment,
            "promotion": promotion,
            "summary": {
                "subtotal": subtotal,
                "discount": discount,
                "shipping": round(shipping_price, 2),
                "tax": tax,
                "total": total,
                "policy": "picoscript:checkout_policy.pc",
            },
        }
        orders[order_id] = order
        carts[cart_id] = {"id": cart_id, "items": []}
        return response.with_json({"order": order})

    def order_get(request: Request, response: Response) -> Response:
        require_action(20, 1, 20)
        order = orders.get(request.params["id"])
        if not order:
            response.status = 404
            return response.with_json({"error": "order not found"})
        return response.with_json({"order": order})

    def call_me(request: Request, response: Response) -> Response:
        require_action(21, 2, 21)
        payload = json_body(request)
        callback = {
            "id": "cb-" + uuid.uuid4().hex[:10],
            "status": "REQUESTED",
            "name": str(payload.get("name") or "Store visitor"),
            "phone": str(payload.get("phone") or ""),
            "reason": str(payload.get("reason") or "Shopping help"),
            "topic": str(payload.get("topic") or "find/order/shipping/stock"),
            "productId": str(payload.get("productId") or ""),
            "preferredWindow": str(payload.get("preferredWindow") or "ASAP"),
        }
        callbacks.append(callback)
        return response.with_json({"callback": callback, "callbacks": callbacks})

    def callback_list(_request: Request, response: Response) -> Response:
        require_action(22, 1, 22)
        return response.with_json({"callbacks": callbacks})

    return [
        Route("GET", "/", home),
        Route("GET", "/retail", home),
        Route("GET", "/checkout", home),
        Route("GET", "/sample-data", home),
        Route("GET", "/baremetal/{name}", baremetal),
        Route("GET", "/api/cms/config", cms_config),
        Route("GET", "/api/cms/pages", cms_pages),
        Route("GET", "/api/cms/pages/{slug}", cms_page),
        Route("GET", "/api/demo/catalog", sample_catalog),
        Route("GET", "/api/demo/customers", sample_customers),
        Route("GET", "/api/demo/promotions", sample_promotions),
        Route("GET", "/api/demo/shipping", sample_shipping),
        Route("GET", "/api/demo/paymentMethods", sample_payments),
        Route("GET", "/api/storage/{objectType}/sample", storage_sample),
        Route("POST", "/api/retail/products:ingestDemo", ingest),
        Route("GET", "/api/retail/products", products),
        Route("GET", "/api/retail/products/{id}", product),
        Route("POST", "/api/retail/search", search),
        Route("POST", "/api/retail/recommend", recommend),
        Route("POST", "/api/retail/events", event),
        Route("GET", "/api/retail/cart/{id}", cart_get),
        Route("POST", "/api/retail/cart", cart_add),
        Route("PUT", "/api/retail/cart/{id}", cart_update),
        Route("POST", "/api/retail/checkout", checkout),
        Route("GET", "/api/retail/orders/{id}", order_get),
        Route("POST", "/api/retail/call-me", call_me),
        Route("GET", "/api/retail/callbacks", callback_list),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="PicoStack retail search API demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--library", type=Path, default=ROOT / "build" / "libpicostack_retail_demo.so")
    parser.add_argument("--store", type=Path, default=Path(tempfile.gettempdir()) / "picostack-retail-demo")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()

    bridge = RetailBridge(args.library, args.store)
    if args.seed:
        bridge.ingest()
    run_server(make_routes(bridge), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
