# In-Memory Python Runtime Design

## 1. Purpose

This document explains how V2 can meet the retail search specification using:

- raw JSON product catalog snapshots loaded from blobs
- append-only append blobs for events, inventory and deltas
- Parquet feature snapshots loaded from blobs
- embedded Python indexes and models
- a Python API host as glue

The goal is to replicate the core commerce-style retail search and recommendation
capabilities without requiring warehouse analytics, Azure AI Search, Redis, a vector
database or any external serving dependency for the first serious version.

## 2. Source data model

V2 should treat product data and event data differently.

Product/catalog data is state:

```text
products.json
  -> validate
  -> normalize
  -> enrich
  -> build CatalogRuntime
```

User events are history persisted as append blobs:

```text
append/events/*.jsonl with tail markers
  -> append
  -> replay committed tail-marked segments
  -> aggregate
  -> materialize feature snapshots
  -> update EventRuntime / PersonaRuntime
```

This mirrors the warehouse pattern without needing warehouse analytics in the serving path:

| Warehouse concept | Embedded Python equivalent |
| --- | --- |
| Product table | `products.json` / `catalog.schema.json` |
| User event table | append-only append blobs |
| Date partition | `append/events/YYYY/MM/DD/*.jsonl` and feature Parquet snapshots |
| Streaming insert | API append to append blob segment |
| Batch query | `polars` or `duckdb` aggregation job |
| Feature table | materialized Parquet/JSON feature snapshot |
| Serving export | immutable in-memory runtime |

## 3. Runtime architecture

```text
Catalog snapshot blobs
Committed append blobs
Feature snapshot blobs
Rules/configs
  -> RuntimeBuilder
  -> immutable CatalogRuntime
  -> FastAPI modules
```

The API host serves from immutable runtime objects:

```python
@dataclass(frozen=True)
class CatalogRuntime:
    products_by_id: dict[str, Product]
    text_index: TextIndex
    facet_index: FacetIndex
    range_index: RangeIndex
    vector_index: VectorIndex
    autocomplete_index: AutocompleteIndex
    recommendation_views: RecommendationViews
    event_features: EventFeatures
    persona_features: PersonaFeatures
```

Real-time data is applied through a mutable overlay:

```python
@dataclass
class LiveOverlay:
    inventory: InventoryOverlay
    sessions: SessionFeatureOverlay
    counters: RealtimeCounterOverlay
    product_deltas: ProductDeltaOverlay
    tombstones: TombstoneOverlay
```

Updates are staged and swapped atomically:

```text
new blob snapshot -> build new runtime -> validate -> swap current runtime pointer
high-churn update -> append to append blob -> update overlay -> fold into later rebuild
```

No local database or durable local disk is part of the serving design. Local disk
is scratch only.

## 3.1 Minimal memory overhead and arena-style ownership

V2 should minimize memory overhead on the hot serving path.

Python should not try to manually arena-allocate ordinary Python objects.
CPython already has its own allocator and garbage collector. Instead, V2 should
use an arena-style ownership model at the runtime level:

```text
RuntimeBuilder allocates packed structures
  -> CatalogRuntime owns those structures
  -> serving reads them without mutation
  -> new CatalogRuntime is built beside the old one
  -> atomic swap
  -> old runtime is released as one unreachable object graph
```

Use Python objects at the edges:

- API request/response models
- validation
- admin/config surfaces
- build-time normalization

Use packed structures inside `CatalogRuntime`:

| Runtime data | Preferred representation |
| --- | --- |
| postings | `array.array`, `numpy.ndarray`, compact tuples or memoryviews |
| vectors | `numpy.ndarray`, ANN index buffers |
| facet memberships | bitmaps or compact integer arrays |
| range indexes | sorted numeric arrays |
| autocomplete prefixes | compact trie/prefix maps |
| feature tables | Arrow/Parquet-derived columnar arrays |
| product hydration | compact product records plus string/value dictionaries |

Avoid serving directly from large graphs of Pydantic models or deeply nested
dict/list objects once the runtime is built.

Memory rules:

- validate rich objects at ingress/build time
- compile into compact runtime views
- cap per-request scratch allocations
- keep overlays bounded
- measure runtime size per tenant
- track peak memory during rebuild as `old runtime + new runtime + build scratch`

Do not implement custom pooling until profiling shows allocation pressure.

## 4. Product catalog implementation

### Specification coverage

Covers:

- Product resource
- Primary / variant / collection products
- Catalog import
- Product get/list/search hydration
- Dynamic facets
- Cold-start product features
- Catalog enrichment

### Python implementation

| Need | Python component |
| --- | --- |
| JSON parse | `orjson` |
| Schema validation | `pydantic`, `msgspec` or `jsonschema` |
| Product lookup | `dict[str, Product]` |
| Primary/variant grouping | `dict[primary_id, list[variant_id]]` |
| Collection grouping | `dict[collection_id, list[product_id]]` |
| GTIN lookup | `dict[gtin, product_id]` |
| Snapshot persistence | JSON, `orjson`, Parquet or `msgpack` |

The first implementation loads:

```text
blob://catalogs/{catalog}/branches/{branch}/snapshots/{version}/catalog.json
```

Live updates append to:

```text
blob://catalogs/{catalog}/branches/{branch}/append/catalog-deltas/YYYY/MM/DD/segment-N.jsonl
blob://catalogs/{catalog}/branches/{branch}/append/inventory/YYYY/MM/DD/segment-N.jsonl
blob://catalogs/{catalog}/branches/{branch}/append/events/YYYY/MM/DD/segment-N.jsonl
```

## 5. Text search implementation

### Specification coverage

Covers:

- Keyword search
- Browse/category search
- Semantic search candidate fusion
- Facets and filters
- Search result ordering

### Python implementation

| Need | Python component |
| --- | --- |
| Tokenization | custom tokenizer, `regex` |
| BM25/BM25F | custom scorer or `rank-bm25` |
| Inverted index | `dict[str, list[Posting]]` |
| Field weighting | custom BM25F weights |
| Fuzzy matching | `rapidfuzz` |
| Synonym expansion | custom synonym dictionary |

Runtime view:

```text
term -> posting[]
posting = product_id + field_mask + term_frequency
```

## 6. Vector and semantic search implementation

### Specification coverage

Covers:

- Semantic search
- Query understanding
- Similar products
- Cold-start recommendations
- Reranking

### Python implementation

| Need | Python component |
| --- | --- |
| Embeddings | `fastembed`, `sentence-transformers`, `onnxruntime` |
| ANN vector search | `hnswlib`, `usearch`, `faiss-cpu` |
| Exact small-vector search | `numpy`, `scikit-learn` |
| Reranking | cross-encoder via `sentence-transformers` or ONNX |

Recommended first choice:

```text
fastembed or sentence-transformers -> product/query vectors
hnswlib or usearch -> vector candidate retrieval
```

Runtime view:

```text
product_id -> vector
vector_index.search(query_vector, k)
```

## 7. Facet, filter and range implementation

### Specification coverage

Covers:

- Dynamic facets
- Attribute filters
- Price/rating/inventory ranges
- Boost/bury/filter controls
- Browse refinement

### Python implementation

| Need | Python component |
| --- | --- |
| Facet membership | `dict[field][value] -> bitset/product_ids` |
| Fast set math | `pyroaring` or Python `set` |
| Range indexes | `sortedcontainers`, `BTrees` |
| Filter parsing | custom parser or `lark` |

Runtime views:

```text
facet_name -> facet_value -> product_ids
field -> sorted(value, product_id)[]
```

For a small/medium catalog, Python `set` is enough. For larger catalogs,
`pyroaring` gives compact and fast intersections.

## 8. Predictive autocomplete implementation

### Specification coverage

Covers:

- Search suggestions
- Brand suggestions
- Category suggestions
- Product previews
- Objective-aware autocomplete

### Python implementation

| Need | Python component |
| --- | --- |
| Prefix index | custom prefix map, `marisa-trie`, `datrie` |
| Fuzzy prefix matching | `rapidfuzz` |
| Suggestion scoring | event stats + business objective weights |
| Product previews | product hydrator from `products_by_id` |

Runtime view:

```text
prefix -> suggestions[]
prefix -> product_preview_ids[]
```

Suggestions are generated from:

- product titles
- categories
- brands
- popular queries
- synonyms
- curated completion data

## 9. Event data implementation

### Specification coverage

Covers:

- UserEvents collect/write/import/purge/rejoin
- Personalized search
- Recommendations
- Real-time predictions
- KPI aggregation
- warehouse-style event-driven learning

### Python implementation

| Need | Python component |
| --- | --- |
| Live writes | append-only JSONL via `orjson` |
| Batch storage | Parquet via `pyarrow` / `polars` |
| Aggregations | `polars` or `duckdb` |
| Real-time counters | `collections.Counter`, `dict`, `defaultdict` |
| Replay | read JSONL/Parquet by checkpoint |
| Deduplication | event ID set or rolling hash index |

Recommended blob layout:

```text
blob://.../append/events/2026/06/22/segment-000001.jsonl
blob://.../snapshots/2026-06-22/features/product_stats.parquet
blob://.../snapshots/2026-06-22/features/query_stats.parquet
blob://.../snapshots/2026-06-22/features/persona_features.parquet
```

Live event flow:

```text
POST userEvents:collect/write
  -> validate event
  -> append JSONL segment
  -> close with tail marker according to durability policy
  -> update in-memory session counters
  -> enqueue batch compaction
```

Batch feature flow:

```text
JSONL/Parquet events
  -> Polars/DuckDB aggregation
  -> feature Parquet snapshots
  -> reload EventRuntime
```

## 10. Recommendation implementation

### Specification coverage

Covers:

- Recommended for you
- Others you might like
- Frequently bought together
- Recently viewed
- Buy it again
- On sale
- Bestsellers
- New arrivals
- Trending products
- Top-rated products
- Cross-sell / upsell
- No-results alternatives
- Cold-start recommendations

### Python implementation

| Need | Python component |
| --- | --- |
| Co-occurrence graph | `dict[product_id, Counter[product_id]]` |
| Similar items | vector index + category/attribute similarity |
| Personalized rows | persona features + product affinity scorer |
| Trending | time-window event counters |
| Bestsellers | purchase counters |
| Top rated | rating index |
| New arrivals | publish/available time range index |
| Cross-sell | cart/product complement graph |
| Upsell | price ladder + category compatibility |

Runtime views:

```text
frequently_bought_together: product_id -> product_ids
similar_items: product_id -> product_ids
recommended_for_you: visitor/session -> product_ids
bestsellers: category/window -> product_ids
trending: category/window -> product_ids
upsell: product/cart -> product_ids
cross_sell: product/cart -> product_ids
```

## 11. Personalization implementation

### Specification coverage

Covers:

- Real-time personalized search
- Real-time recommendations
- Shopper personas
- Anonymous/session fallback
- GDPR delete/export workflows

### Python implementation

| Need | Python component |
| --- | --- |
| Session features | in-memory dict keyed by session/visitor |
| Historical persona | Parquet feature snapshot |
| Affinity scoring | custom weighted scorer |
| Feature refresh | event materializer job |
| Delete/export | feature store filter/export job |

Persona features:

```text
brand affinity
category affinity
color affinity
size affinity
price-band affinity
fulfillment preference
recent query intent
```

Real-time overlay:

```text
historical persona + current session events -> request-time ranking features
```

## 12. Controls and merchandising implementation

### Specification coverage

Covers:

- Controls API
- Serving configs
- Boost / bury / pin / filter
- Fallback logic
- No-zero recommendations
- Merchandising audit

### Python implementation

| Need | Python component |
| --- | --- |
| Rule storage | JSON snapshot / module store |
| Rule compilation | custom `RuleCompiler` |
| Rule matching | predicate functions over query/context/product |
| Ranking impact | custom scorer stage |
| Audit | append-only audit JSONL |

Runtime views:

```text
serving_config_id -> objective/weights/rule_ids
placement -> serving_config_id
rule_id -> compiled predicates/actions
```

## 13. API host implementation

### Specification coverage

Covers:

- commerce-compatible API surface
- Native V2 API surface
- Composable modules
- Operations
- Health/readiness

### Python implementation

| Need | Python component |
| --- | --- |
| API framework | `FastAPI` / `Starlette` |
| Models | `pydantic` or `msgspec` |
| Server | `uvicorn` |
| Background jobs | `asyncio`, `apscheduler` |
| Metrics | `prometheus-client`, OpenTelemetry |

Modules:

```text
catalog
products
inventory
events
search
recommendations
autocomplete
serving_configs
controls
attributes
models
operations
runtime
safety
```

## 14. Persistence through blobs only

The system is durable without local databases. All durable state is blob
state.

| Need | Component |
| --- | --- |
| Catalog snapshot | JSON blob |
| Event log | append blob JSONL with tail marker |
| Feature snapshots | Parquet blobs |
| Runtime snapshot | cold manifest + optional binary artifact blobs |
| Operation store | append blob operation records |
| Audit log | append blob audit records |

This keeps the service deployable as disposable containers that recover by
loading snapshots and replaying committed append segments.

## 15. How this meets the specification

| Specification area | In-memory Python implementation |
| --- | --- |
| Commerce product compatibility | Pydantic/msgspec product schema + product service routes. |
| Shared ingestion | Products JSON + event logs feed one `CatalogRuntime`. |
| Search | BM25 index + vector index + facets + ranker. |
| Semantic intent | embedding/reranker provider + query parser. |
| Recommendations | materialized candidate graphs + objective ranker. |
| Personalization | event-derived persona features + real-time session overlay. |
| Predictive autocomplete | prefix index + suggestion scorer + product previews. |
| Cold-start | content/enrichment features + category/brand/popularity priors. |
| warehouse-style learning | Parquet + Polars/DuckDB aggregation jobs. |
| Merchandising | JSON controls + rule compiler + applied-control diagnostics. |
| Inventory-aware serving | top-level inventory stream + local inventory indexes. |
| Safety/audit | pseudonymous events + audit JSONL + delete/export jobs. |
| Composable API host | FastAPI modules with dependency injection. |

## 16. Recommended first build stack

Use:

```text
FastAPI
Pydantic v2 or msgspec
orjson
polars
pyarrow
duckdb
sortedcontainers
pyroaring
hnswlib or usearch
rapidfuzz
fastembed or sentence-transformers
apscheduler
prometheus-client
```

Start without:

- external vector database
- Redis
- Elasticsearch/OpenSearch
- warehouse analytics
- Azure AI Search
- managed feature store

Those can be added later as replaceable adapters if scale or operations require
them.

## 17. Build order

1. Load `products.json` and validate with the schema.
2. Build product lookup, primary/variant grouping and facet/range indexes.
3. Build BM25 text search.
4. Add event append API and JSONL log.
5. Add Polars/DuckDB aggregation into product/query stats.
6. Add autocomplete prefix index.
7. Add vector embeddings and ANN index.
8. Add recommendation candidate graphs.
9. Add controls and serving configs.
10. Add personalization/session overlays.
11. Add no-results, cross-sell, upsell and cold-start strategies.
12. Add operation tracking, audit and metrics.

