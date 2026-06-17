from __future__ import annotations

import argparse
import ctypes
import json
import mimetypes
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PICOWEB_SRC = ROOT.parent / "picoweb" / "src"
BAREMETAL_SRC = ROOT.parent / "BareMetalJsTools" / "src"
if str(PICOWEB_SRC) not in sys.path:
    sys.path.insert(0, str(PICOWEB_SRC))

from picoweb_core import Request, Response, Route  # noqa: E402
from picoweb_server import run_server  # noqa: E402


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

    def home(_request: Request, response: Response) -> Response:
        return html_response(response, storefront)

    def baremetal(request: Request, response: Response) -> Response:
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
        return response.with_json(bridge.ingest())

    def products(_request: Request, response: Response) -> Response:
        return response.with_json(bridge.products())

    def product(request: Request, response: Response) -> Response:
        payload = bridge.product(request.params["id"])
        if "error" in payload:
            response.status = 404
        return response.with_json(payload)

    def search(request: Request, response: Response) -> Response:
        payload = json_body(request)
        return response.with_json(bridge.search(str(payload.get("query", ""))))

    def recommend(request: Request, response: Response) -> Response:
        payload = json_body(request)
        return response.with_json(bridge.recommend(str(payload.get("id", ""))))

    def event(request: Request, response: Response) -> Response:
        payload = json_body(request)
        return response.with_json(
            bridge.event(
                str(payload.get("visitorId", "demo")),
                str(payload.get("eventType", "detail-page-view")),
                str(payload.get("productId", "")),
            )
        )

    return [
        Route("GET", "/", home),
        Route("GET", "/retail", home),
        Route("GET", "/baremetal/{name}", baremetal),
        Route("POST", "/api/retail/products:ingestDemo", ingest),
        Route("GET", "/api/retail/products", products),
        Route("GET", "/api/retail/products/{id}", product),
        Route("POST", "/api/retail/search", search),
        Route("POST", "/api/retail/recommend", recommend),
        Route("POST", "/api/retail/events", event),
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
