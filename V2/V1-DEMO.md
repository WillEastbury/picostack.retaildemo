# V1 Demo Implementation

## Purpose

The V1 demo turns the platform specification into a small runnable Python
implementation. It is intentionally modular so components can be extracted into
OSS packages later.

## Package

```text
src/retail_v2/
```

Reusable modules:

| Module | Responsibility |
| --- | --- |
| `auth.py` | Minimal STS/JWT issuer and verifier for tenant-scoped demo tokens. |
| `blob_store.py` | Blob storage protocol plus local development adapter. |
| `paths.py` | Tenant blob path conventions for products, features and append streams. |
| `partitioning.py` | Stable hash partitioning and owner resolution. |
| `append_log.py` | Ordered append record writer and tail marker generation. |
| `runtime.py` | In-memory catalog runtime, product graph materialization and BM25-style search. |
| `services.py` | Domain service glue for catalog, events, inventory, rules, search and recommendation. |
| `app.py` | FastAPI app exposing the V1 demo endpoints. |

## Run locally

```text
set PYTHONPATH=src
python -m retail_v2
```

Default URL:

```text
http://127.0.0.1:8797
```

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /healthz` | Health check. |
| `POST /v2/auth/token` | Issue a demo tenant-scoped token. |
| `GET /v2/status` | Runtime and overlay status. |
| `GET /v2/partition/{key}` | Resolve a partition route for a key. |
| `GET /v2/catalog/products` | List products from the in-memory runtime. |
| `GET /v2/catalog/products/{product_id}` | Fetch one product. |
| `POST /v2/search` | Search catalog using the in-memory text index. |
| `POST /v2/recommend` | Return simple related recommendations. |
| `POST /v2/userEvents:write` | Append a user event with tail marker. |
| `POST /v2/inventory:set` | Append inventory update and update live overlay. |
| `POST /v2/rules` | Append rule/control update. |

## What is implemented

- tenant-scoped token issuance/validation
- deterministic partition routing
- append records with tail markers
- blob-style path layout via a local development adapter
- in-memory runtime built from `V2/sample-catalog.json`
- simple BM25-style keyword search
- simple content/category recommendation
- live overlays for events and inventory
- smoke test coverage

## What remains for production

- Azure Blob adapter
- real blob lease integration
- dual/multi-write replica coordinator
- partition map persistence and ingress routing
- model integration/enrichment jobs
- packed runtime structures
- full rule compiler
- observability, hardening and admin UI

## Validate

```text
python tests\v2_smoke.py
```

