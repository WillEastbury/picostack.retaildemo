# Multi-Region and Multi-Cluster Architecture

## 1. Purpose

V2 is multi-region and multi-cluster by design.

The platform scales behind load balancers. Those load balancers can route like a
CDN when needed:

- closest healthy region
- tenant affinity
- partition affinity
- failover region
- read-mostly edge routing

The service remains fully in-memory. Every cluster can recover by loading cold
blob snapshots and replaying committed append blobs.

## 2. Global topology

```text
Global load balancer / edge routing
  -> region A AKS cluster
  -> region B AKS cluster
  -> region C AKS cluster

Each cluster:
  -> FastAPI roles
  -> partition owners
  -> in-memory runtime shards
  -> blob snapshots + append streams
```

## 3. Routing hierarchy

Routing happens in layers:

```text
client
  -> global load balancer
  -> region
  -> cluster ingress
  -> tenant
  -> partition key
  -> partition owner
```

The global load balancer chooses region/cluster. The cluster ingress chooses the
partition owner.

## 4. Region-aware partition ownership

Partition maps include region and cluster ownership:

```json
{
  "tenantId": "tenant-123",
  "version": "partition-map-2026-06-22T12:00:00Z",
  "partitions": 256,
  "owners": {
    "p0037": {
      "primaryRegion": "uksouth",
      "primaryCluster": "retail-v2-aks-uksouth",
      "primaryOwner": "search-7",
      "secondaryRegion": "ukwest",
      "secondaryCluster": "retail-v2-aks-ukwest",
      "secondaryOwner": "search-3"
    }
  }
}
```

This lets routing preserve:

- tenant affinity
- partition affinity
- region affinity
- failover targets

## 5. Request routing modes

| Mode | Behavior |
| --- | --- |
| `nearest_read` | Route read requests to closest healthy region with a warm runtime. |
| `primary_partition` | Route writes and sticky sessions to the partition primary region/owner. |
| `read_replica` | Route read-only requests to secondary region when runtime is current enough. |
| `failover` | Route to secondary owner when primary region/cluster is unhealthy. |
| `edge_cached` | Route static/admin/catalog read assets like CDN-style cached content. |

Writes should prefer `primary_partition` unless the tenant has explicitly
enabled multi-primary write policy.

## 6. Write path across regions

The indexing endpoint remains the durable write-ingress owner.

Regional write path:

```text
request
  -> global LB routes to primary partition region
  -> indexing owner validates
  -> append to required storage replicas
  -> update region-local overlay
  -> notify consumers
```

If the request enters the wrong region, ingress can:

1. proxy to the primary partition region
2. redirect internally
3. accept into a regional queue only if queued commit mode is configured

Default: proxy/route to primary partition owner.

## 7. Read path across regions

Search/recommendation reads can be served by any region that has:

- current or acceptable runtime snapshot
- committed append replay up to required watermark
- partition ownership or read-replica permission

For strict session personalization, route the user/session to the same
partition/region where possible.

For anonymous read-heavy search, the global load balancer may use CDN-like
nearest-region routing.

## 8. Cold blob recovery by region

Each cluster can recover independently:

```text
start pod
  -> resolve tenant + partition map
  -> load current manifest
  -> load partition snapshots
  -> replay committed append segments
  -> warm runtime shard
  -> report ready to ingress
```

No durable data moves between containers. Only routing ownership changes.

## 9. Storage replication and multi-region

Cold blob storage may be:

- RA-GZRS in one storage account
- dual/multi-written to multiple storage accounts
- region-local storage accounts with required replica commit policies

The storage choice is tenant-configurable.

Commit policies:

| Policy | Multi-region meaning |
| --- | --- |
| `primary_only` | Primary region commits; other regions catch up asynchronously. |
| `all_required` | Required regional storage replicas must commit before success. |
| `queued_all_required` | Return operation/accepted and complete after required replicas commit. |

## 10. CDN-like behavior

The load balancer can act CDN-like for:

- static admin UI assets
- public catalog reads
- autocomplete for anonymous users
- popular query result caches
- read-only recommendation rows with acceptable staleness

It should not CDN-cache:

- authenticated tenant admin mutations
- inventory writes
- user event writes
- personalized results unless keyed safely by tenant/session/user context

## 11. Failure behavior

| Failure | Behavior |
| --- | --- |
| pod failure | ingress routes partition to another warm owner or starts recovery. |
| cluster failure | global LB routes to failover region. |
| region failure | secondary region loads/replays partition and takes ownership. |
| storage replica lag | route reads according to staleness policy; writes follow commit policy. |
| partition owner lag | mark owner not ready; route to warm secondary or return retry. |

## 12. Operational requirements

Must expose:

- region/cluster health
- partition owner health
- runtime version per partition
- append watermark per region and partition
- replica commit lag
- failover events
- routing decision diagnostics

## 13. Acceptance criteria

Multi-region/multi-cluster is ready when:

- global load balancer can route by region health
- cluster ingress can route by tenant/partition key
- partition map contains region/cluster/owner data
- partitions can fail over without durable data movement
- read-only requests can use region-local warm runtimes
- writes route to primary partition owners or configured queued commit path
- per-region watermarks and staleness are visible

