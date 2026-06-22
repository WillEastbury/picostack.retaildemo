# PicoStack Retail Search API Demo

End-to-end retail search demo built from Pico stack components:

- **PicoWAL**: product, index, journal, and event storage.
- **PicoWAL Search**: full-text, vector candidate, facet, range, and ranking primitives.
- **PicoWAL Retail Primitives**: retail catalog/search/recommend/event behavior.
- **PicoWeb**: route dispatch and HTTP server.
- **BareMetalJsTools**: browser-side API calls and search helper module.
- **SimpleCMS-style JSON**: site metadata, pages, menu items, store metadata and sample storage endpoints.
- **PicoScript**: checkout policy and CMS template rendering run through PicoScript's C frontend and PicoVM.
- **PicoScript route policy**: every demo route executes `scripts/route_policy.pc` before serving content or invoking backend actions.
- **Azure Voice Live compatible shop assistant**: optional browser voice bridge with retail tools for find/order/shipping/stock.

## Run

From WSL/Linux:

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
bash scripts/build_demo_lib.sh
python3 src/retail_asgi_server.py --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787/
```

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | storefront |
| `GET` | `/checkout` | storefront with checkout panel |
| `GET` | `/api/cms/config` | SimpleCMS-style site config JSON |
| `GET` | `/api/cms/pages` | visible CMS pages/menu data |
| `GET` | `/api/cms/pages/{slug}` | one CMS page |
| `GET` | `/api/demo/catalog` | complete sample-data API set |
| `GET` | `/api/demo/customers` | sample customers |
| `GET` | `/api/demo/promotions` | sample promotions |
| `GET` | `/api/demo/shipping` | sample shipping methods |
| `GET` | `/api/demo/paymentMethods` | sample payment methods |
| `GET` | `/api/storage/{objectType}/sample` | SimpleCMS-style storage sample endpoint |
| `POST` | `/api/retail/products:ingestDemo` | seed demo catalog |
| `GET` | `/api/retail/products` | list products |
| `GET` | `/api/retail/products/{id}` | product detail |
| `POST` | `/api/retail/search` | search products |
| `POST` | `/api/retail/recommend` | similar items |
| `POST` | `/api/retail/events` | record user event |
| `GET` | `/api/retail/cart/{id}` | get cart |
| `POST` | `/api/retail/cart` | add item to cart |
| `PUT` | `/api/retail/cart/{id}` | update/remove cart item |
| `POST` | `/api/retail/checkout` | place demo order |
| `GET` | `/api/retail/orders/{id}` | get demo order |
| `POST` | `/api/retail/call-me` | request a demo store callback |
| `GET` | `/api/retail/callbacks` | list demo callback requests |
| `GET` | `/api/retail/voice/config` | browser voice configuration and retail tool schema |
| `WS` | `/ws/browser-voice` | browser microphone to Azure Voice Live bridge |
| `GET` | `/api/product-service/products?offset=0&limit=50` | paged SKU-keyed product list |
| `GET` | `/api/product-service/products/{sku}` | product by SKU |
| `POST` | `/api/product-service/products` | create/update one product or `{products:[...]}` |
| `POST` | `/api/product-service/products:sync` | bulk sync products by SKU |
| `POST` | `/api/product-service/products:upload` | upload JSON/CSV product file |
| `POST` | `/api/product-service/products:generate` | generate deterministic load-test products |

Example:

```bash
curl -X POST http://127.0.0.1:8787/api/retail/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"waterproof jacket"}'
```

CMS example:

```bash
curl http://127.0.0.1:8787/api/cms/config
curl http://127.0.0.1:8787/api/storage/Product/sample
```

PicoScript-backed behavior:

- `scripts/checkout_policy.pc` calculates discount, tax and total in integer pence.
- `src/picoscript_runner.py` compiles that policy through PicoScript and runs it on PicoVM during checkout.
- CMS page responses render a small template via PicoScript `Template.Compile` / `Template.Render`.
- `scripts/route_policy.pc` is executed for every route handler as the PicoScript serving/action gate.

Checkout example:

```bash
curl -X POST http://127.0.0.1:8787/api/retail/cart \
  -H 'Content-Type: application/json' \
  -d '{"cartId":"demo-cart","productId":"aurora-shell","quantity":1}'

curl -X POST http://127.0.0.1:8787/api/retail/checkout \
  -H 'Content-Type: application/json' \
  -d '{"cartId":"demo-cart","customerId":"cust-demo-hiker","shippingMethodId":"standard","paymentMethodId":"demo-card","promoCode":"SUMMIT10"}'
```

Callback example:

```bash
curl -X POST http://127.0.0.1:8787/api/retail/call-me \
  -H 'Content-Type: application/json' \
  -d '{"name":"Avery Hill","phone":"+447700900123","topic":"stock","reason":"Please check stock on Aurora Storm Shell Jacket"}'
```

Product service examples:

```bash
curl -X POST http://127.0.0.1:8787/api/product-service/products \
  -H 'Content-Type: application/json' \
  -d '{"sku":"SKU-DEMO-001","title":"Demo product","description":"Created through the product service","category":"hardware","brand":"Pico","tags":["demo","hardware"],"price":19.99,"inventory":42}'

curl -X POST http://127.0.0.1:8787/api/product-service/products:generate \
  -H 'Content-Type: application/json' \
  -d '{"count":5000,"seed":42}'

curl -F "file=@products.csv" http://127.0.0.1:8787/api/product-service/products:upload
```

Load test:

```bash
python3 scripts/load_test_products.py \
  --base-url http://127.0.0.1:8787 \
  --count 5000 \
  --requests 2000 \
  --concurrency 20
```

Voice setup:

```bash
export VOICE_LIVE_ENDPOINT="https://<your-ai-resource>.services.ai.azure.com"
export VOICE_LIVE_API_KEY="<optional-api-key>"
export VOICE_LIVE_MODEL="gpt-realtime-mini"
bash scripts/build_demo_lib.sh
python3 src/retail_asgi_server.py --host 127.0.0.1 --port 8787
```

The storefront **Talk with me** panel can then use Voice Live tools:

- `find_items`
- `check_stock`
- `order_items`
- `check_shipping_status`

## Validate

```bash
bash scripts/build_demo_lib.sh
PYTHONPATH=../picoweb/src python3 tests/smoke.py
```

Expected:

```text
picostack retail demo smoke ok
```

Run a live HTTP smoke test:

```bash
bash scripts/live_smoke.sh
```

Expected:

```text
picostack retail demo live smoke ok
```

## Repository boundary

This repo is a demo assembly layer. Reusable primitives stay in their own repos:

- generic storage/search changes go to `picowal`
- generic routing changes go to `picoweb`
- generic browser utilities go to `BareMetalJsTools`
- retail-specific reusable behavior goes to `picowal.retailprimitives`
