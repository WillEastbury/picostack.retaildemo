# Retail Search V2 System Specification

## 1. System intent

Retail Search V2 is a state-of-the-art retail search and recommendation
platform designed to run as a Python/FastAPI service fleet on AKS.

The platform serves:

- product search
- category browse
- autocomplete
- personalized recommendations
- cross-sell and upsell
- merchandising controls
- catalog enrichment
- event-driven learning
- admin and tenant configuration

The serving path is fully in memory. Durable state is held in Azure Blob Storage
using tier-neutral blob storage: JSON blobs for product/catalog/features and
append blobs for audit trails, interaction streams, catalog deltas, inventory,
rules and operations.

## 2. Non-negotiable constraints

| Constraint | Requirement |
| --- | --- |
| Retail quality | Must provide state-of-the-art retail search and recommendation features. |
| Unit economics | Must cost less than `$0.10 / 1,000` served requests. |
| Development cost | Must reuse proven libraries/components and avoid rebuilding commodity infrastructure. |
| Durability | Durable data lives in blob storage only. Containers are ephemeral. |
| Partitioning | Data is always partitioned in blob paths. Runtime ownership is routed by partition maps. |
| Scale-out | Must support multi-instance, multi-cluster and multi-region scale-out. |
| Write ownership | Every record has a single global owning partition at a time. |
| Consistency | Partition owner writes ordered records; blob leases prevent concurrent writers. |
| Failover | Partition ownership changes through explicit/manual failover and partition-map update. |
| Extensibility | External services are allowed only with explicit cost/latency/failure/exit justification. |

## 3. Logical architecture

```text
Clients / channels
  -> global load balancer
  -> regional AKS ingress
  -> tenant + partition routing
  -> FastAPI service role
  -> in-memory runtime / overlay
  -> blob storage snapshots and append streams
```

Core service roles:

- Auth / STS
- API gateway / host
- indexing
- catalog
- user events
- inventory
- rules
- search and recommendation
- model integration
- builder / compactor
- admin API / UI

## 4. Storage model

Storage is tier-neutral. The platform does not require a specific hot/cool/cold
storage tier.

Per tenant:

```text
storage account(s)
  -> container: tenant-{tenantId}
     -> manifests
     -> partition maps
     -> product JSON blobs
     -> feature JSON/Parquet blobs
     -> append blob streams
```

Durable object classes:

| Object | Shape |
| --- | --- |
| Product | one JSON blob per product or partitioned product batch |
| Feature | JSON/Parquet blob per feature family and partition |
| Event/audit trail | append blob segment with tail marker |
| Inventory update | append blob segment with tail marker |
| Rule/control update | append blob segment with tail marker |
| Operation update | append blob segment with tail marker |
| Manifest | JSON blob pointing to active versions and watermarks |
| Partition map | JSON blob assigning partition ranges to owners |

## 5. Partition ownership

All data is partitioned on storage paths. In memory, services may cache loaded
partitions, but they never own durable state locally.

Partition routing:

```text
tenantId + partitionKey
  -> partitionId
  -> region / cluster
  -> owning service instance
```

Partition keys:

| Data/request | Partition key |
| --- | --- |
| Product | `productId` or `primaryProductId` |
| Inventory | variant `productId` |
| User event | `visitorId` or `sessionId` |
| Search | normalized query or session key |
| Recommendation | session/user/product/cart key |
| Rules/admin | tenant control partition |
| Features | product/user/query key depending on feature type |

Only the current partition owner writes the append stream for a partition.
Ownership is protected by blob leases in the primary location.

## 6. Blob lease model

Each writable partition stream has a lease record or lease blob.

Lease lifecycle:

```text
owner starts
  -> acquire blob lease for tenant/stream/partition
  -> write ordered append records
  -> write tail markers
  -> renew lease while healthy
  -> release lease on drain/shutdown
```

Manual failover:

```text
operator marks owner unhealthy
  -> stop routing new writes to old owner
  -> wait for lease expiry or break lease
  -> assign partition to new owner
  -> new owner replays committed tail-marked segments
  -> new owner acquires lease
  -> ingress routes partition to new owner
```

No elections are required in the baseline design. Ownership is explicit in the
partition map and protected by storage leases.

## 6.1 Partition change signal and rebalance

Partition changes are signalled through the partition map/control path.

```text
partition map update
  -> signal affected owners/followers
  -> followers dump in-memory data for partitions they no longer own
  -> new followers load product/feature blobs and replay append trails
  -> followers report ready
  -> ingress switches routing
```

Durable blob data is not moved or rewritten for a rebalance. Only ownership,
routing and in-memory caches change.

## 7. Write path

All durable writes go through the indexing endpoint or a service path that calls
indexing.

```text
write request
  -> auth / tenant check
  -> derive partition key
  -> route to owning partition
  -> validate schema
  -> acquire/verify lease
  -> append ordered record
  -> update in-memory overlay
  -> close segment with tail marker according to policy
  -> notify consumers
```

Dual/multi-write mode:

```text
append primary account
append required replica accounts
verify required commit policy
return success or operation
```

Supported commit policies:

- `primary_only`
- `all_required`
- `queued_all_required`

## 8. Read path

Search/recommendation services read from in-memory runtime:

```text
request
  -> auth / tenant check
  -> route to partition owner or read replica
  -> base runtime lookup
  -> live overlay merge
  -> ranking / filtering / personalization
  -> response with attribution token
```

Read replicas may serve if:

- runtime version is acceptable
- append watermarks are within staleness policy
- request does not require strict session overlay locality

## 9. Runtime model

Runtime is split:

```text
immutable base runtime + mutable bounded overlay = served view
```

Base runtime:

- product lookup
- text index
- vector index
- facet/range indexes
- autocomplete index
- recommendation candidate views
- feature snapshots
- compiled rules/configs

Live overlay:

- recent inventory
- price/offer overrides
- session features
- short-window counters
- tombstones
- small catalog deltas

The overlay is replayable from append blobs and is not durable state.

## 10. Memory model

Hot-path memory must be compact.

Use:

- arrays
- memoryviews
- bitmaps
- vector buffers
- columnar feature tables
- compact product hydration records

Avoid serving from:

- large nested Python dict/list graphs
- Pydantic object graphs
- per-request model calls
- unbounded session maps

`CatalogRuntime` acts as the arena-like owner of packed runtime structures.

## 11. API surface

Native API groups:

- `/auth/*`
- `/catalog/*`
- `/events/*`
- `/inventory/*`
- `/rules/*`
- `/search`
- `/recommend`
- `/autocomplete`
- `/admin/*`
- `/operations/*`
- `/status/*`

Commerce-compatible API groups:

- products
- user events
- placements
- serving configs
- controls
- attributes config
- completion data
- models
- catalogs
- operations

## 12. Model integration

Model integration is off the hot path by default.

Responsibilities:

- semantic enrichment
- taxonomy classification
- attribute extraction
- embeddings
- reranking features
- product quality diagnostics
- cold-start features
- query understanding features

Outputs are stored as V2 schema-compatible artifacts in blobs and loaded into
runtime during build/replay.

## 13. Admin and management

Admin surfaces manage:

- tenants
- feature flags
- serving configs
- rules/controls
- model/enrichment configuration
- partition maps
- runtime versions
- watermarks
- failover operations
- rebuild/compaction

Admin writes go through the same append/indexing path.

## 14. Observability

Must expose:

- request latency and volume by endpoint
- cost per 1,000 requests
- runtime version by tenant/partition
- partition owner health
- blob lease status
- append watermarks
- replica lag
- tail marker failures
- validation failures
- model job failures
- memory per tenant/partition

## 15. First implementation slice

Build in this order:

1. STS with tenant-scoped tokens.
2. Blob store abstraction and Azure Blob implementation.
3. Partition map loader.
4. Blob lease manager.
5. Append writer with tail markers.
6. Indexing endpoint.
7. Catalog import via indexing.
8. Runtime loader from product JSON blobs.
9. Basic search endpoint.
10. User event endpoint with attribution token.
11. Inventory endpoint with live overlay.
12. Rules endpoint with simple boost/bury/pin.
13. Admin status page for runtime, partitions, leases and watermarks.
