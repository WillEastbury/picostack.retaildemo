from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.retail_demo_server import RetailBridge, make_routes
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
        home = call(routes, "GET", "/")
        assert "PicoStack Retail Search" in home
        assert "BareMetal.Communications" in home
        assert call(routes, "POST", "/api/retail/products:ingestDemo", {})["ingested"] is True
        products = call(routes, "GET", "/api/retail/products")
        assert products["totalSize"] >= 1
        search = call(routes, "POST", "/api/retail/search", {"query": "waterproof jacket"})
        assert search["results"]
        detail = call(routes, "GET", "/api/retail/products/aurora-shell")
        assert detail["brand"] == "Contoso Trail"
        recs = call(routes, "POST", "/api/retail/recommend", {"id": "aurora-shell"})
        assert "results" in recs
        event = call(routes, "POST", "/api/retail/events", {"visitorId": "demo", "eventType": "detail-page-view", "productId": "aurora-shell"})
        assert event["accepted"] is True
    print("picostack retail demo smoke ok")


if __name__ == "__main__":
    main()
