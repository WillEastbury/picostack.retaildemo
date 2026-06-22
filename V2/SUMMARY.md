# Retail Search V2 Summary

## What we are building

Retail Search V2 is a provider-neutral, commerce-compatible retail search and
recommendations platform.

It is:

- Python/FastAPI based
- deployed on AKS
- fully in-memory for serving
- durable only through blob snapshots and append blobs
- tenant-isolated by Azure Storage container
- compatible with commerce API-style product, event, search, predict,
  controls and serving-config concepts
- designed to support search, browse, autocomplete, recommendations,
  merchandising, enrichment, personalization and analytics

## Overarching guardrails

V2 has three non-negotiable product and engineering guardrails:

| Guardrail | Meaning |
| --- | --- |
| State-of-the-art retail capability | Search and recommendations must include semantic understanding, personalization, merchandising, dynamic facets, autocomplete, cold-start handling, cross-sell/upsell and enrichment. |
| Cost target | Serving must cost less than `$0.10` per 1,000 requests, or `$0.0001` per request. |
| Reuse first | Minimize development cost by using proven Python libraries and adapters instead of rebuilding commodity infrastructure. |
| Minimal memory overhead | Runtime data should be packed into compact arrays, bitmaps, vector buffers and columnar features; `CatalogRuntime` owns these like an arena. |
| Justify external services | AKS and Azure Storage are baseline; any additional external service must justify capability, cost, latency, failure mode, data boundary and exit path. |

The hot path should serve from memory and avoid per-request LLM/model calls.
Expensive model work belongs in offline enrichment, feature generation or bounded
reranking stages.

## Core platform principle

```text
blob snapshots + committed append blobs
  -> load / replay
  -> immutable base runtime + live overlay
  -> search, recommend, autocomplete and admin APIs
```

There is no hot database in the core design. The API containers are disposable:
they recover by loading the current tenant manifest, loading snapshot blobs and
replaying committed append segments with valid tail markers.

Data is always partitioned in blob storage. Containers hold only in-memory
caches/projections and temporary scratch. Dynamic partition changes are handled
by the partition map and ingress routing, not by moving durable data between
containers.

On partition change, affected followers dump the partition's in-memory cache and
new owners reload product/feature blobs plus append trails before ingress routes
traffic to them.

The same partition model extends across regions and clusters. Global load
balancers choose healthy regions, cluster ingress routes to partition owners, and
safe read-only traffic can use CDN-like nearest-region routing.

## Tenant and storage model

Each tenant maps to a storage container:

```text
storage account(s)
  -> tenant-{tenantId}
     -> manifests
     -> snapshots
     -> append streams
```

Default Azure deployment:

- AKS for containers
- Python/FastAPI image
- Azure Storage account in RA-GZRS mode
- one container per tenant
- optional dual/multi-write to additional storage accounts

Ingress writes can use:

| Commit policy | Meaning |
| --- | --- |
| `primary_only` | Return after primary storage commit; optional replicas repair async. |
| `all_required` | Return after all required storage replicas commit. |
| `queued_all_required` | Return accepted/operation ID; complete after all required replicas commit. |

## Endpoint topology

| Endpoint | Responsibility |
| --- | --- |
| Auth / STS | Issues tenant-scoped tokens and service-to-service tokens. |
| Indexing | Sole durable write ingress; validates and appends ordered records with tail markers. |
| Catalog | Product import, create, patch, delete, get and list. Writes go through indexing. |
| User Events | Collect/write/import events. Writes go through indexing. |
| Inventory | Inventory and local inventory updates. Writes go through indexing. |
| Rules | Controls, boost/bury/pin/filter, serving-config attachments. Writes go through indexing. |
| Model Integration | Enrichment, classification, embeddings, prompts, reranking features. |
| Search / Recommend | Low-latency read-serving from in-memory runtime and live overlay. |
| Admin Console/API | Tenant config, feature flags, rules, runtime status and rebuild controls. |
| Builder / Compactor | Replays append blobs, builds feature snapshots and publishes new manifests. |

## Runtime model

The runtime is split into two layers.

### Immutable base runtime

Built from blob snapshots:

- products
- primary/variant/collection graph
- text index
- facet index
- range index
- vector index
- autocomplete index
- recommendation candidate views
- compiled rules
- compiled serving configs
- historical feature snapshots

### Mutable live overlay

Projected from append streams:

- inventory changes
- price/offer overrides
- session features
- short-window counters
- product tombstones
- small catalog deltas

Read path:

```text
served view = base runtime + live overlay
```

## Commerce-compatible API areas

The API compatibility surface maps to:

- `products`
- `userEvents`
- `placements`
- `servingConfigs`
- `controls`
- `attributesConfig`
- `completionData`
- `models`
- `catalogs`
- `operations`

V2 mirrors commerce API concepts where they help migration, but remains
provider-neutral internally.

## Product and catalog model

The product model supports:

- primary products
- variant products
- collection products
- GTIN
- categories
- brands
- price info and price ranges
- ratings
- availability
- fulfillment
- images
- audience
- colors
- sizes/materials/patterns/conditions
- promotions
- local inventories
- enrichment output

Primary products are usually search-grid entries. Variants are purchasable or
selectable options. Collections are bundles or grouped products.

## Event model

Events are append-only and deduplicatable.

Important event fields:

- `eventId`
- `eventType`
- `eventTime`
- `visitorId`
- `sessionId`
- `attributionToken`
- `placement`
- `servingConfigId`
- `productDetails`
- `transactionInfo`

The KPI join is:

```text
search/predict response -> attributionToken
event -> attributionToken + placement + servingConfigId
aggregate -> CTR / conversion / revenue per search / revenue per session
```

## Enrichment model

Enrichment runs offline or asynchronously through the model integration endpoint.

Components:

- taxonomy classifier
- attribute extractor
- color/size/material/pattern normalizers
- title cleaner
- image tagger
- duplicate detector
- compatibility extractor
- quality scorer
- searchability scorer

Outputs are written back as V2 schema artifacts, not vendor-specific model
payloads.

## Search and recommendation capabilities

Search supports:

- keyword search
- semantic/vector retrieval
- dynamic facets
- filters
- boost/bury/pin
- personalization
- query understanding
- conversational refinement

Recommendations support:

- recommended for you
- frequently bought together
- others you might like
- recently viewed
- buy it again
- on sale
- bestsellers
- new arrivals
- trending
- top rated
- cross-sell
- upsell
- no-results alternatives
- cold-start recommendations

## AKS delivery model

Keep delivery simple:

```text
one Python codebase
one container image
multiple FastAPI roles
one AKS namespace per environment
one STS/auth service
plain Kubernetes manifests first
```

Roles can be selected by environment variable:

```text
SERVICE_ROLE=search
SERVICE_ROLE=indexing
SERVICE_ROLE=model
SERVICE_ROLE=admin
SERVICE_ROLE=sts
SERVICE_ROLE=builder
```

## First build slice

The smallest useful implementation is:

1. STS issues tenant-scoped tokens.
2. Indexing appends tenant-scoped records to append blobs.
3. Catalog imports a sample catalog through indexing.
4. Search loads a tenant snapshot into memory.
5. Search returns basic product results.
6. Events record attribution-linked clicks/add-to-cart/purchases.
7. Admin status shows runtime version, tenant config and append watermarks.

This validates the architecture before implementing the full model and
merchandising surface.
