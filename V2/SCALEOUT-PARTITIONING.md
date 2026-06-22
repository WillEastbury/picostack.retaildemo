# Scale-Out Partitioning and Sticky Routing

## 1. Purpose

V2 must support maximal scale-out by design while preserving the in-memory,
cold-blob-backed architecture.

The scale-out model is:

```text
tenant
  -> partition key
  -> extensible hash ring
  -> region / cluster / owning service instance
  -> partitioned blob paths
  -> partition-local runtime/overlay
```

A request for the same product, user/session or query partition should route to
the same serving/indexing instance whenever possible.

Hard rule:

```text
data is always partitioned in blob storage
containers store no durable data
in-memory state is cache/projection only
global LB + cluster ingress own dynamic partition routing
```

Adding partitions should not require restructuring existing blob data.
Instead, the partition map and ingress routing change which new partitions own
new writes and which instances load/replay which partition paths.

## 2. Why sticky partitioning matters

Sticky partitioning improves:

- cache locality
- in-memory overlay correctness
- session personalization
- append ordering
- per-partition replay
- hot-key isolation
- horizontal scale-out

Without sticky routing, every replica needs either all overlays or an external
hot shared state layer. V2 avoids that by routing related requests to the same
partition owner.

## 3. Partition key strategy

Different endpoints use different partition keys:

| Request type | Partition key |
| --- | --- |
| Product create/patch/delete | `productId` or `primaryProductId` |
| Inventory update | variant `productId`, falling back to `primaryProductId` |
| User event write | `visitorId` or `sessionId` |
| Search query | normalized query hash, optionally blended with visitor/session hash |
| Recommendation request | visitor/session ID, active product ID or cart hash |
| Rules/admin write | tenant-level control partition |
| Catalog import | tenant/catalog build partition |
| Model enrichment | product ID or batch partition |

The chosen partition key must be included in the append record envelope:

```json
{
  "partitionKey": "SKU-001",
  "partitionId": "p0037",
  "recordId": "evt-001",
  "payload": {}
}
```

## 4. Extensible hash ring

Each tenant has a partition map:

```json
{
  "tenantId": "tenant-123",
  "version": "partition-map-2026-06-22T12:00:00Z",
  "hash": "rendezvous",
  "partitions": 256,
  "owners": {
    "p0000": "indexing-0",
    "p0001": "indexing-1"
  }
}
```

Preferred algorithms:

- rendezvous hashing for owner selection
- consistent hashing for ring-style ownership
- fixed virtual partitions for simple rebalancing

Recommended first implementation:

```text
256 virtual partitions per tenant
partitionId = hash(tenantId + partitionKey) % 256
owner = partitionMap[partitionId]
```

## 5. Storage partitioning

Cold blob data is always partitioned on disk/blob. Append blob paths include
partition IDs from the first implementation:

```text
/branches/{branch}/append/events/p0037/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/inventory/p0042/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/catalog-deltas/p0011/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/rules/control/YYYY/MM/DD/segment-{id}.jsonl
```

Snapshot paths can also be partitioned:
Snapshot paths are also partitioned:

```text
/branches/{branch}/snapshots/{version}/partitions/p0037/catalog.json
/branches/{branch}/snapshots/{version}/partitions/p0037/features.parquet
/branches/{branch}/snapshots/{version}/partitions/p0037/runtime-manifest.json
```

Global metadata remains tenant/branch scoped:

```text
/manifests/current.json
/branches/{branch}/partition-map/current.json
```

Partition IDs are stable storage keys. Runtime owners are not. A partition can
move between instances without rewriting the partition's stored data.

## 6. Runtime partitioning

Each serving instance owns one or more partitions.

```text
Search instance A:
  p0000, p0004, p0091

Search instance B:
  p0001, p0005, p0092
```

Each owner loads only its assigned partition runtime where possible:

```text
CatalogRuntimePartition
  products
  text index shard
  facet shard
  vector shard
  recommendation shard
  overlay shard
```

Global queries may fan out to multiple partitions, but sticky routing should be
used whenever the request has a natural product/user/query key.

## 7. Request routing

The API gateway/host resolves:

```text
tenant -> partition key -> partition id -> region -> cluster -> owner endpoint
```

Routing headers:

```text
X-Tenant-Id: tenant-123
X-Partition-Key: visitor-123
X-Partition-Id: p0037
X-Partition-Map-Version: partition-map-2026-06-22T12:00:00Z
```

If the request lands on a non-owner instance, it may:

1. proxy to the owner
2. redirect internally
3. return retry metadata to the gateway

Preferred first implementation: API gateway computes the owner and routes
directly to the correct Kubernetes service/pod group.

Dynamic partition addition belongs at the global LB / cluster ingress routing
layer:

```text
new partition map published
  -> new owners warm/load partition caches
  -> global LB / ingress starts routing matching keys to new owners
  -> old owners drain
```

No container-local data migration is required because containers are ephemeral
and blobs remain the source of truth.

## 8. Sticky sessions

Sticky sessions are required for real-time session personalization unless a
shared overlay is introduced.

Sticky key:

```text
tenantId + visitorId/sessionId
```

Session events, search requests and recommendations for the same visitor should
hit the same partition owner.

If the owner changes during rebalance:

- old owner drains partition
- new owner loads snapshot + replay append watermarks
- gateway switches routing after new owner is ready

## 9. Partitioned indexing

The indexing endpoint is partitioned by write key.

```text
write request
  -> validate
  -> compute partition
  -> route to partition owner
  -> append to partition stream on all required storage replicas
  -> update partition overlay
  -> return according to commit policy
```

This preserves ordering per partition without requiring one global writer.

Ordering guarantee:

```text
strict order within tenant + stream + partition
not strict global order across all tenant data
```

This is sufficient for product/user/query-local updates and greatly improves
scale-out.

## 10. Query partitioning

Search has two modes:

### Keyed search

If request has visitor/session/query key:

```text
query partition = hash(normalizedQuery or sessionId)
```

The owner can use partition-local:

- query stats
- personalization overlay
- cached query interpretation
- hot result cache

### Global search

For broad catalog search, V2 may:

1. fan out to all product partitions
2. fan out to top-N likely partitions
3. route to a replicated global search runtime

First implementation can keep a replicated global search runtime for simplicity,
then partition product indexes when memory or traffic requires it.

## 11. Rebalancing

Rebalancing must be explicit and safe.

Steps:

1. publish new partition map as staged
2. signal affected owners/followers that partition ownership changed
3. old followers dump/release in-memory caches for partitions they no longer own
4. new followers load product/feature blobs and replay committed append segments
5. new followers report ready with runtime version and append watermark
6. gateway/ingress switches partition routing
7. old owners drain in-flight requests
8. old owners release partition leases/runtimes
9. staged map becomes current

Partition map updates are control-plane operations and should be written through
the indexing/control path.

Rebalancing changes ownership, not storage layout. Existing partition blob paths
remain valid; new owners load and replay from blobs.

No durable data moves between containers during rebalance. Only in-memory
partition caches are dumped and reloaded by the affected followers/owners.

## 12. Hot partition handling

Hot keys can be split:

| Hot key | Mitigation |
| --- | --- |
| popular query | query-result cache, subpartition by result page or replica read-only query partition |
| celebrity product | split product interactions by event type or time bucket |
| heavy tenant | increase virtual partitions and owner count |
| high-volume events | queued append mode and larger segment batches |

The partitioning scheme must support increasing virtual partition count over
time.

## 13. Acceptance criteria

Scale-out is ready when:

- every write request has a deterministic partition key
- append paths include partition IDs
- snapshot paths include partition IDs where data is partitionable
- partition owners can be resolved from a versioned map
- containers can be deleted and recreated without data loss
- LB/ingress can route a partition to a new owner without rewriting blobs
- sticky session routing works for user/session traffic
- indexing preserves order within tenant/stream/partition
- search/recommendation can route keyed requests to partition owners
- rebalancing can move partitions without data loss
- dual-write replica watermarks are tracked per partition
