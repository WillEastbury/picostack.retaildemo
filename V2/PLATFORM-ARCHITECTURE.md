# Retail Search V2 Platform Architecture

## 1. Purpose

This document maps the required retail search/recommendation capabilities to
Python libraries, runtime components and deployable service modules.

The target platform is a composable Python service that runs entirely in memory.
Durable state lives only in storage blobs:

- immutable snapshot blobs loaded at startup/rebuild
- append blobs for catalog deltas, inventory, events, operations and audit
- explicit tail markers that identify committed append segments

It can run as:

- a single embedded container for demos and small/medium catalogs
- a vertically scaled API service loading snapshots from blob storage
- a horizontally scaled read-serving tier backed by shared blob snapshots
- a future distributed platform where specific modules are replaced by managed
  services without changing API contracts

The first Azure deployment target uses one Azure Storage container per tenant in
one storage account configured for read-access geo-zone-redundant storage
(RA-GZRS). See `AZURE-TENANT-SERVICE-TOPOLOGY.md`.

Tenants may optionally configure multiple storage accounts. In that mode, the
indexing endpoint dual-writes or multi-writes append records to all required
storage replicas and only returns committed success once the configured commit
policy is satisfied.

## 2. Architecture summary

```text
                 ┌──────────────────────────┐
                 │        API Host           │
                 │ FastAPI / Starlette       │
                 └────────────┬─────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  ┌─────▼─────┐        ┌──────▼──────┐       ┌──────▼──────┐
  │ Catalog   │        │ Search      │       │ Recommend   │
  │ Products  │        │ Browse      │       │ Predict     │
  │ Inventory │        │ Complete    │       │ Cross/Upsell│
  └─────┬─────┘        └──────┬──────┘       └──────┬──────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                 ┌────────────▼────────────┐
                 │   CatalogRuntime         │
                 │ immutable in-memory views│
                 └────────────┬────────────┘
                              │
   ┌──────────────────────────┼──────────────────────────┐
   │                          │                          │
┌──▼─────────┐        ┌───────▼────────┐        ┌────────▼───────┐
│ Snapshot   │        │ Append Blobs    │        │ Feature Blobs    │
│ Blobs      │        │ + Tail Markers  │        │ Parquet/JSON     │
└────────────┘        └────────────────┘        └────────────────┘
```

The core rule: **catalog, inventory and events are loaded/replayed from cold
blobs into memory, materialized into runtime views, then reused by search,
autocomplete and recommendations**.

Production serving uses an immutable base runtime plus live overlays:

```text
CatalogRuntime(base snapshot) + LiveOverlay(high-churn updates) -> served view
```

The base runtime is atomically swapped. The overlay is bounded, mutable and
folded into later rebuilds.

## 3. Capability-to-library map

The library map is part of the development-cost guardrail: reuse proven
components wherever they are not core product differentiation.

| Capability | First-choice Python libraries | Role in platform |
| --- | --- | --- |
| API host | `FastAPI`, `Starlette`, `uvicorn` | REST routes, dependency injection, health/readiness endpoints. |
| Request/schema validation | `pydantic v2`, `msgspec`, `jsonschema` | commerce-compatible request/response models and catalog validation. |
| Fast JSON | `orjson` | Catalog loading, event append, API serialization. |
| Product lookup | built-in `dict`, `immutables` optional | `productsById`, GTIN lookup, primary/variant maps. |
| Packed runtime data | `array`, `memoryview`, `numpy`, Arrow buffers | Minimize hot-path object overhead and GC pressure. |
| Text search | custom BM25/BM25F, `rank-bm25` optional | Keyword and browse retrieval. |
| Tokenization | `regex`, custom analyzer | Product/query tokenization, normalization. |
| Fuzzy matching | `rapidfuzz` | Spelling fixes, fuzzy autocomplete, query repair. |
| Vector search | `hnswlib` or `usearch`; `faiss-cpu` optional | ANN candidate retrieval for semantic search and similar items. |
| Embeddings | `fastembed`, `sentence-transformers`, `onnxruntime` | Product/query vectors, semantic intent, reranking. |
| Range indexes | `sortedcontainers`, `BTrees` optional | Price, rating, publish time, inventory and numeric filters. |
| Facet set math | `pyroaring`, Python `set`, `numpy` masks | Dynamic facets, filters, rule targeting. |
| Autocomplete | custom prefix map, `marisa-trie` optional | Search/brand/category/product suggestions. |
| Event aggregation | `polars`, `duckdb`, `pyarrow` | warehouse-style event analytics and feature snapshots. |
| Recommendation graphs | custom adjacency maps, `networkx` for prototyping | Co-purchase, similar item, cross-sell and upsell graphs. |
| Scheduling | `apscheduler`, `asyncio` | Runtime rebuilds, compaction, daily feature refresh. |
| Cold blob persistence | blob SDK adapter, Parquet, JSONL | Snapshots, append logs, operations and audit with tail markers. |
| Metrics | `prometheus-client`, OpenTelemetry | Latency, ingestion lag, freshness, errors and ranking diagnostics. |
| Testing/load | `pytest`, `httpx`, `locust`, `pytest-benchmark` | Functional, API and performance validation. |

## 4. Service module architecture

The module architecture can be deployed as one API host or split into endpoint
families:

- indexing endpoint
- model integration endpoint
- search and recommendation endpoint
- admin console/API
- catalog endpoint
- user events endpoint
- inventory endpoint
- rules endpoint

All durable writes flow through the indexing endpoint into tenant append blobs.
When dual-write is enabled, the indexing endpoint owns replica commit,
watermarks and repair.

### 4.1 API host

Owns HTTP routing and dependency wiring only.

Libraries:

- `FastAPI`
- `Starlette`
- `Pydantic`
- `uvicorn`

Responsibilities:

- register commerce-compatible routes
- register native V2 routes
- inject service modules
- apply auth/safety hooks
- expose health/readiness/status

Does not own:

- ranking logic
- model logic
- event aggregation
- storage internals

### 4.2 Catalog/product service

Owns product and catalog resources.

Libraries:

- `pydantic` / `msgspec`
- `orjson`
- built-in `dict`

Runtime views:

- `productsById`
- `variantsByPrimaryId`
- `primaryByVariantId`
- `collectionsById`
- `gtinIndex`

API areas:

- `products.create`
- `products.get`
- `products.list`
- `products.patch`
- `products.delete`
- `products.import`
- `products.purge`

### 4.3 Inventory service

Owns availability, fulfillment and local inventory updates.

Libraries:

- `orjson`
- `sortedcontainers`
- `pyroaring` or `set`

Runtime views:

- `localInventoriesByProductId`
- `localInventoryByPlaceId`
- `availabilityIndex`
- `fulfillmentTypeIndex`

API areas:

- `products.setInventory`
- `products.addLocalInventories`
- `products.removeLocalInventories`

### 4.4 Event service

Owns live and bulk user-event ingestion.

Libraries:

- `orjson`
- `pyarrow`
- `polars`
- `duckdb`

Storage:

```text
blob://.../append/events/YYYY/MM/DD/*.jsonl
blob://.../snapshots/{version}/events/date=YYYY-MM-DD/*.parquet
blob://.../snapshots/{version}/features/*.parquet
```

API areas:

- `userEvents.collect`
- `userEvents.write`
- `userEvents.import`
- `userEvents.purge`
- `userEvents.rejoin`

### 4.5 Runtime builder

Owns immutable serving runtime construction.

Libraries:

- `orjson`
- `polars`
- `sortedcontainers`
- `pyroaring`
- `hnswlib` / `usearch`
- `fastembed` / `sentence-transformers`

Build stages:

```text
load catalog
validate schema
normalize product graph
load feature snapshots
build lookup maps
build text index
build facets/ranges
build vector index
build autocomplete index
build recommendation views
compile rules/serving configs
publish CatalogRuntime
```

### 4.6 Search service

Owns search and browse execution.

Libraries:

- custom BM25/BM25F
- `rapidfuzz`
- `hnswlib` / `usearch`
- `pyroaring`
- `sortedcontainers`

Pipeline:

```text
query
  -> query understanding
  -> lexical candidates
  -> semantic candidates
  -> filter/facet
  -> personalization
  -> controls/rules
  -> final rank
  -> hydrated response
```

API areas:

- `placements.search`
- `servingConfigs.search`

### 4.7 Recommendation service

Owns prediction and recommendation placements.

Libraries:

- custom adjacency maps
- `numpy`
- `polars`
- `hnswlib` / `usearch`

Candidate views:

- recommended for you
- frequently bought together
- others you might like
- recently viewed
- buy it again
- on sale
- bestsellers
- new arrivals
- trending products
- top-rated products
- cross-sell
- upsell
- no-results alternatives
- cold-start

API areas:

- `placements.predict`
- `servingConfigs.predict`

### 4.8 Autocomplete service

Owns predictive typeahead.

Libraries:

- custom prefix maps
- `marisa-trie` optional
- `rapidfuzz`

Suggestion sources:

- product titles
- categories
- brands
- popular queries
- synonyms
- curated completion data
- product previews

API areas:

- native `/api/complete`
- `completionData.import`
- `completionData.purge`

### 4.9 Controls and serving-config service

Owns merchandising rules and placement behavior.

Libraries:

- `pydantic`
- custom rule compiler
- append-only audit JSONL

Control types:

- boost
- bury/demote
- pin
- filter
- facet control
- redirect/reroute
- synonym/rewrite
- fallback logic

API areas:

- `controls.*`
- `servingConfigs.*`
- `servingConfigs.addControl`
- `servingConfigs.removeControl`

### 4.10 Model service

Owns model registry, model providers and scheduled training/materialization.

Libraries:

- `fastembed`
- `sentence-transformers`
- `onnxruntime`
- `apscheduler`
- `polars`

Model families:

- query understanding
- semantic embeddings
- reranking
- autocomplete scoring
- recommendation candidates
- cold-start similarity

API areas:

- `models.create`
- `models.get`
- `models.list`
- `models.pause`
- `models.resume`
- `models.tune`

## 5. Data plane vs control plane

### Data plane

Latency-sensitive request path:

```text
FastAPI route
  -> current CatalogRuntime
  -> search/recommend/autocomplete service
  -> hydrated response
```

Components:

- search
- recommendations
- autocomplete
- product hydration
- real-time session personalization

Data plane should avoid:

- large file reads
- full dataframe scans
- rebuild work
- blocking model training

### Control plane

Mutation and rebuild path:

```text
import/update/event/rule/model request
  -> validate
  -> append/update source data
  -> create operation
  -> background job
  -> build new runtime/features
  -> atomic swap
```

Components:

- imports
- event compaction
- model tuning
- runtime rebuild
- rule publish
- branch switch
- purge/rejoin

## 6. Storage layout

Recommended blob layout:

```text
/catalogs/{catalog}/branches/{branch}/manifests/current.json
/catalogs/{catalog}/branches/{branch}/snapshots/{version}/catalog.json
/catalogs/{catalog}/branches/{branch}/snapshots/{version}/features/*.parquet
/catalogs/{catalog}/branches/{branch}/append/events/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
/catalogs/{catalog}/branches/{branch}/append/inventory/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
/catalogs/{catalog}/branches/{branch}/append/catalog-deltas/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
/catalogs/{catalog}/branches/{branch}/append/audit/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
```

This gives the first platform:

- readable source-of-truth blobs
- replayable append history
- compact feature storage
- restartable runtime
- operation/audit durability

## 7. Scaling model

Scale-out is partition-first. Requests should route by tenant plus product,
user/session or query key through a versioned extensible hash map. Each
partition owner loads the relevant runtime shard and live overlay, and append
paths include the partition ID.

```text
tenant + partitionKey
  -> partitionId
  -> global LB chooses region/cluster
  -> cluster ingress routes to owner instance
  -> partitioned append blobs
  -> partition-local runtime/overlay
```

Data is always partitioned in blob storage. In-memory runtime shards are
ephemeral caches/projections. Dynamic partition addition is handled by updating
the partition map and LB/ingress routing, not by restructuring stored data.

Multi-region and multi-cluster routing use the same partition map extended with
region and cluster ownership. Global load balancers route to healthy regions and
can behave CDN-like for safe read-only traffic.

### Stage 1: single container

```text
API + runtime + append blob writer + background jobs + blob snapshots
```

Best for:

- prototype
- demos
- small catalogs
- deterministic development

### Stage 2: split builder and serving

```text
builder container -> writes runtime snapshots
serving containers -> load current runtime snapshot
```

Best for:

- safer rebuilds
- larger catalogs
- multiple read replicas

### Stage 3: distributed adapters

Replace selected embedded components:

| Embedded component | Replaceable adapter |
| --- | --- |
| JSON/Parquet blobs | object storage provider adapter |
| append blobs with tail markers | Event Hubs/Kafka/PubSub |
| embedded vector index | vector DB / AI Search |
| cold operation append blobs | Postgres/Cosmos |
| local feature Parquet | feature store/warehouse |

The API and module contracts stay stable.

## 8. Capability coverage

| Specification capability | Platform module | Libraries |
| --- | --- | --- |
| Product API | Product service | FastAPI, Pydantic, orjson |
| Inventory API | Inventory service | FastAPI, sortedcontainers, pyarrow |
| User events | Event service | orjson, JSONL, Polars, DuckDB |
| Search | Search service | BM25, hnswlib/usearch, pyroaring |
| Semantic search | Query/model services | fastembed, sentence-transformers, onnxruntime |
| Dynamic facets | Runtime/search services | pyroaring, dict/set |
| Range filters | Runtime/search services | sortedcontainers, BTrees optional |
| Autocomplete | Autocomplete service | prefix map, rapidfuzz, marisa-trie optional |
| Recommendations | Recommendation service | adjacency maps, numpy, polars |
| Personalization | Personalization service | event counters, Parquet feature snapshots |
| Controls | Controls service | Pydantic, rule compiler, audit JSONL |
| Serving configs | Serving-config service | Pydantic, runtime compiler |
| Model lifecycle | Model service | apscheduler, model provider adapters |
| Operations | Operations service | append blobs, background jobs |
| Safety/audit | Safety service | auth hooks, audit JSONL |

## 9. Platform interfaces

Runtime objects should be treated as region-owned/arena-owned structures:

```text
CatalogRuntime owns packed indexes and buffers
LiveOverlay owns bounded mutable deltas
RuntimeRegistry atomically swaps the active runtime
```

This gives arena-like lifetime control without fighting CPython's allocator.

### Search provider interface

```python
class SearchProvider(Protocol):
    def search(self, request: SearchRequest, runtime: CatalogRuntime) -> SearchResponse:
        ...
```

### Recommendation provider interface

```python
class RecommendationProvider(Protocol):
    def predict(self, request: PredictRequest, runtime: CatalogRuntime) -> PredictResponse:
        ...
```

### Vector index interface

```python
class VectorIndex(Protocol):
    def add(self, product_id: str, vector: list[float]) -> None:
        ...

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        ...
```

### Feature store interface

```python
class FeatureStore(Protocol):
    def product_stats(self) -> ProductStatsView:
        ...

    def query_stats(self) -> QueryStatsView:
        ...

    def persona(self, visitor_id: str | None, session_id: str | None) -> PersonaFeatures:
        ...
```

### Runtime registry interface

```python
class RuntimeRegistry(Protocol):
    def current(self, catalog: str, branch: str) -> CatalogRuntime:
        ...

    def publish(self, runtime: CatalogRuntime) -> None:
        ...

    def rollback(self, catalog: str, branch: str) -> None:
        ...
```

## 10. Recommended first implementation stack

Install only the minimum stack first:

```text
fastapi
uvicorn
pydantic
orjson
polars
pyarrow
duckdb
sortedcontainers
rapidfuzz
hnswlib or usearch
fastembed
apscheduler
prometheus-client
pytest
httpx
```

Add later if needed:

```text
pyroaring
sentence-transformers
onnxruntime
marisa-trie
opentelemetry
locust
```

## 11. Platform build phases

### Phase 1: embedded serving kernel

Build:

- FastAPI host
- product schema/load
- product lookup
- text index
- facet/range indexes
- search endpoint
- catalog browser/debug endpoint

### Phase 2: event-driven learning

Build:

- event collect/write/import
- JSONL event log
- Polars/DuckDB aggregations
- product/query stats
- recommendation views
- autocomplete suggestions

### Phase 3: semantic and personalized serving

Build:

- embeddings
- vector index
- semantic search
- persona features
- real-time session overlay
- cross-sell/upsell
- no-results alternatives

### Phase 4: control plane and operations

Build:

- serving config CRUD
- controls CRUD
- rule compiler
- operations store
- runtime rebuild/swap
- audit/rollback
- model registry/tune hooks

### Phase 5: production hardening

Build:

- auth/authz
- GDPR delete/export
- pipeline lag metrics
- SLO dashboards
- load tests
- split builder/serving deployment
- adapter interfaces for distributed services

## 12. Resulting platform shape

The final platform is:

```text
Python API Host
  + CatalogRuntime
  + Product/Inventory/Event modules
  + Search/Recommend/Autocomplete modules
  + Controls/ServingConfig/Model modules
  + Cold blob snapshot/append feature pipeline
  + Embedded vector/text/facet/range indexes
```

It satisfies the V2 specification while staying:

- provider-neutral
- single-container capable
- API-compatible with commerce API concepts
- replaceable module by module
- cheap to run
- easy to debug from files
- ready to scale later through adapters
