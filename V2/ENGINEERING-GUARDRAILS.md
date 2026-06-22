# Engineering Guardrails

## 1. Product quality guardrail

V2 must provide state-of-the-art retail search and recommendation capabilities.

This means the platform must support:

- semantic search and query understanding
- keyword + vector candidate retrieval
- dynamic facets
- autocomplete with product previews
- personalized search
- personalized recommendations
- cross-sell and upsell
- cold-start recommendations
- no-results alternatives
- merchandising controls
- enrichment and catalog quality diagnostics
- KPI-driven ranking

If a design decision makes these capabilities impossible or materially weaker,
it should be rejected or explicitly escalated.

## 1.1 Memory overhead guardrail

V2 must minimize memory overhead because each AKS serving replica loads tenant
runtime state into memory.

Rules:

- use rich Python/Pydantic objects at API and validation boundaries
- compile hot serving data into packed runtime structures
- prefer arrays, bitmaps, memoryviews, vector index buffers and columnar feature
  tables over nested Python object graphs
- treat `CatalogRuntime` as the owner of these packed structures
- release old runtimes by atomic swap rather than mutating in place
- keep live overlays bounded and measurable
- track memory per tenant and peak rebuild memory

Classic manual arena allocation for Python objects is not a goal. The goal is
arena-style runtime ownership and compact data representation.


## 2. Unit economics guardrail

The serving target is:

```text
< $0.10 per 1,000 requests
= < $0.0001 per request
```

This target applies to search, recommendation and autocomplete serving. It does
not mean every offline enrichment/model job must fit that request cost, but
offline costs must be amortized and visible.

Cost design implications:

- serve from memory, not remote query engines
- avoid per-request LLM calls on the hot path
- precompute embeddings and enrichment
- use lightweight rerankers only behind candidate limits
- keep expensive model calls in offline/model-integration jobs
- measure p50/p95 latency and CPU per request
- track cost per 1,000 requests per endpoint

## 3. Development cost guardrail

Do not reinvent commodity infrastructure.

Default to proven Python libraries and small adapters:

- FastAPI / Starlette for HTTP
- Pydantic or msgspec for schemas
- orjson for JSON
- Polars / DuckDB / PyArrow for analytics and Parquet
- hnswlib / usearch / FAISS for vector indexes
- sortedcontainers / sets / bitmaps for in-memory indexes
- rapidfuzz for fuzzy matching
- fastembed / sentence-transformers / ONNX Runtime for embeddings and rerankers

Build custom code only where it is core product differentiation:

- retail ranking composition
- serving config/rule semantics
- tenant runtime loading/replay
- append blob tail-marker protocol
- attribution/KPI joining
- product/variant/collection materialization

## 4. External service justification guardrail

AKS and Azure Storage are part of the baseline platform. Any additional external
service is allowed only when its use is explicitly justified.

For every proposed external service beyond AKS and Azure Storage, document:

| Question | Required answer |
| --- | --- |
| What capability does it provide? | The concrete feature or operational gap it closes. |
| Why not embedded/in-memory Python? | Why local libraries or the existing cold-blob model are insufficient. |
| Cost impact | Expected effect on the `< $0.10 / 1,000 requests` target. |
| Latency impact | Whether it is on the hot path or offline/control-plane only. |
| Failure mode | What happens if the service is unavailable. |
| Data boundary | What tenant/catalog/event data leaves the core platform. |
| Exit path | How the service can be replaced later. |

Preferred use of external services:

- offline enrichment
- batch/model jobs
- observability
- identity federation
- optional scale adapters

Avoid external services on the hot request path unless they are essential and
the cost/latency tradeoff is explicitly accepted.

## 5. Decision checklist

Before adding a new component, ask:

1. Does it improve retail search/recommendation quality?
2. Does it preserve the $0.10 / 1,000 request serving target?
3. Can an existing library do this reliably?
4. Is it off the hot path if expensive?
5. Can it recover from blobs only?
6. Does it keep tenant isolation clear?
7. Does it preserve the indexing endpoint as the durable write ingress?
8. If it is an external service beyond AKS/Azure Storage, is its use justified
   with cost, latency, failure-mode and exit-path analysis?

If the answer is no, redesign before implementation.
