# PicoStack Retail Search API Demo

End-to-end retail search demo built from Pico stack components:

- **PicoWAL**: product, index, journal, and event storage.
- **PicoWAL Search**: full-text, vector candidate, facet, range, and ranking primitives.
- **PicoWAL Retail Primitives**: retail catalog/search/recommend/event behavior.
- **PicoWeb**: route dispatch and HTTP server.
- **BareMetalJsTools**: browser-side API calls and search helper module.

## Run

From WSL/Linux:

```bash
bash scripts/build_demo_lib.sh
python3 src/retail_demo_server.py --seed --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787/
```

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | storefront |
| `POST` | `/api/retail/products:ingestDemo` | seed demo catalog |
| `GET` | `/api/retail/products` | list products |
| `GET` | `/api/retail/products/{id}` | product detail |
| `POST` | `/api/retail/search` | search products |
| `POST` | `/api/retail/recommend` | similar items |
| `POST` | `/api/retail/events` | record user event |

Example:

```bash
curl -X POST http://127.0.0.1:8787/api/retail/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"waterproof jacket"}'
```

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
