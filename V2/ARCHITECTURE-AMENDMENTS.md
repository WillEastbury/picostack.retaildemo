# Architecture Amendments from Rubber-Duck Review

## 1. Summary

The first V2 design was directionally sound, but it had one critical unresolved
tension: it described an immutable, atomically swapped `CatalogRuntime` while
also promising real-time inventory, event, personalization and session updates.

The amended design resolves this with a two-tier runtime backed only by cold
blob snapshots and append blobs:

```text
Cold blob snapshots + committed append segments
  -> immutable base runtime + mutable live overlay
  -> served view
```

This keeps the snapshot/rollback benefits of immutable runtime builds while
allowing high-churn updates without rebuilding every index on every event.

## 2. Two-tier runtime model

### Immutable base runtime

The base runtime is rebuilt from catalog snapshots and feature snapshots loaded
from storage blobs.

It owns low-churn structures:

- product documents
- primary/variant/collection graph
- text index
- base facet index
- base range index
- product vectors
- autocomplete prefix index
- recommendation candidate graphs
- compiled serving configs
- compiled controls
- historical feature snapshots

Base runtime update cadence:

| Data type | Default cadence |
| --- | --- |
| Full catalog snapshot | manual/import-driven |
| Product text/vector changes | batch rebuild or delta rebuild |
| Recommendation graphs | daily or scheduled |
| Feature snapshots | scheduled/event-compaction driven |
| Controls/serving config publish | compile + atomic swap |

### Mutable live overlay

The overlay is a bounded mutable layer merged at read time. It is a projection
of append blobs, not a durable source of truth.

It owns high-churn data:

- inventory and availability updates
- local inventory updates
- current session events
- real-time visitor/session features
- short-window trending counters
- active offer/price overrides
- product tombstones pending base rebuild
- small catalog deltas pending base rebuild

Overlay update cadence:

| Data type | Cadence |
| --- | --- |
| Inventory | append blob + immediate overlay |
| Local inventory | append blob + immediate overlay |
| Session features | event append blob + immediate overlay |
| Short-window counters | event append blob + immediate / rolling overlay |
| Price/offer override | append blob + immediate overlay |
| Catalog delta | append blob + immediate overlay, folded into next base rebuild |

Read-path merge:

```text
served_result = base_runtime result
  + live inventory/price/offer overlay
  + live session/persona overlay
  + live tombstone/delta overlay
```

## 3. Runtime interfaces

```python
@dataclass(frozen=True)
class CatalogRuntime:
    version: str
    products_by_id: Mapping[str, Product]
    text_index: TextIndex
    facet_index: FacetIndex
    range_index: RangeIndex
    vector_index: VectorIndex
    recommendation_views: RecommendationViews
    serving_config_plan: ServingConfigPlan
    rule_plan: RulePlan

class LiveOverlay:
    inventory: InventoryOverlay
    sessions: SessionFeatureOverlay
    counters: RealtimeCounterOverlay
    product_deltas: ProductDeltaOverlay
    tombstones: TombstoneOverlay

class RuntimeRegistry:
    def current(self, catalog: str, branch: str) -> CatalogRuntime: ...
    def overlay(self, catalog: str, branch: str) -> LiveOverlay: ...
```

Serving services receive both:

```python
runtime = runtime_registry.current(catalog, branch)
overlay = runtime_registry.overlay(catalog, branch)
response = search_service.search(request, runtime, overlay)
```

## 4. Inventory source-of-truth and precedence

V2 has three inventory-compatible surfaces:

1. product-level `availability` / `availableQuantity`
2. product-level `localInventories[]`
3. top-level or API-driven inventory updates

The precedence is:

```text
live inventory overlay
  > top-level inventory[] update stream
  > product.localInventories[]
  > product availability/availableQuantity
```

Variant-level inventory is authoritative for purchasable products.

Primary product availability is derived lazily at read time:

```text
primary is effectively in stock if any purchasable variant is in stock
```

This prevents stale primary availability after variant inventory changes.

## 5. Multi-process and horizontal scaling model

The single-container version may keep overlays in process.

For multi-worker or multi-replica deployments, in-process overlays are not
sufficient unless traffic is sticky to the same process.

Supported deployment modes:

| Mode | Real-time overlay strategy |
| --- | --- |
| Single process | in-process overlay |
| Multi-worker single node | per-worker read overlay plus per-worker event segments; session personalization requires sticky routing or shared overlay |
| Multi-replica | shared overlay store or reduced real-time guarantee |
| Split builder/serving | builder owns rebuilds; serving replicas load published runtime snapshots |

Production horizontal scale must choose one:

1. sticky session routing for session overlays
2. shared low-latency overlay store
3. documented fallback to near-real-time personalization only

Background schedulers must run in one owner process/container. They must not run
once per API worker.

## 6. Event durability and KPI linkage

User events must include stable keys for deduplication and KPI joins.

Required or strongly recommended fields:

- `eventId`
- `eventType`
- `eventTime`
- `visitorId`
- `sessionId`
- `attributionToken`
- `placement`
- `servingConfigId`
- `query`
- `productIds`
- `productDetails` with product ID and result position where applicable

The KPI join is:

```text
search/predict response -> attributionToken
user event -> attributionToken + placement + productDetails
aggregate -> CTR, conversion, revenue/search, revenue/session
```

Event append rules:

- use per-process or per-segment JSONL files
- never let multiple workers write unsafely to the same segment
- acknowledge according to a documented durability policy
- compact JSONL to Parquet for batch analytics

## 7. Pagination and runtime versioning

Page tokens must bind to:

- runtime version
- serving config
- query/request hash
- ranking seed
- overlay consistency window where applicable

Token shape:

```json
{
  "runtimeVersion": "catalog-2026-06-22T12:00:00Z",
  "servingConfig": "default-search",
  "requestHash": "sha256...",
  "offset": 20,
  "rankingSeed": "..."
}
```

If the runtime version is no longer retained, V2 may:

1. return a stale page token error
2. restart from page one
3. best-effort continue with diagnostics

The default should be explicit stale-token error in production.

## 8. Embedding and vector index rebuilds

Vector rebuilds must use an embedding cache.

Cache key:

```text
product_id + content_hash(title, description, categories, brands, attributes)
```

Rebuild flow:

```text
product changed?
  yes -> re-embed
  no  -> reuse cached embedding
```

Deletes are handled by:

- tombstone overlay immediately
- base vector index rebuild later

Small product additions may be added to an overlay vector index and folded into
the next base rebuild.

## 9. Latency and memory budgets

Every serving config should define latency guardrails.

Recommended defaults:

| Placement | Target |
| --- | --- |
| autocomplete | p95 <= 50 ms |
| search | p95 <= 150 ms |
| recommendations | p95 <= 120 ms |
| product lookup | p95 <= 30 ms |

Memory planning:

```text
peak_memory =
  worker_count
  * (base_runtime_size + overlay_size)
  + rebuild_runtime_size
```

During atomic swap, the builder may temporarily hold:

```text
old_runtime + new_runtime + build_scratch
```

If runtime size exceeds node memory, V2 must either:

- reduce worker count
- split builder from serving
- shard by catalog/category
- replace embedded components with external adapters

## 10. Schema hardening requirements

The current permissive schema is acceptable for early exploration, but production
ingestion needs stricter validation.

Required changes:

- event type enum
- `eventId`
- `sessionId`
- attribution fields
- typed rule condition/action DSL
- explicit extension bag instead of arbitrary product fields
- field-count and value-count limits
- diagnostics for missing cost when margin objective is configured
- diagnostics for missing categories on primary products

## 11. Rule and filter safety

Filters and control predicates are a serving-path risk.

Required limits:

- max expression depth
- max clause count
- max execution cost
- no unindexed full scans in production mode unless explicitly allowed
- validation before publish
- preview/test before publish

## 12. Product update concurrency

Product patch APIs need optimistic concurrency.

Use:

- product `etag` or `version`
- update mask
- conflict response on stale writes

Inventory remains timestamp-aware because inventory systems often emit ordered
updates independently from catalog product patches.

## 13. Updated platform principle

V2 is not just:

```text
immutable in-memory runtime
```

It is:

```text
immutable base runtime
  + bounded live overlays
  + scheduled compaction/rebuild
  + atomic publication
```

This is the model to use for implementation.
