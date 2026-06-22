# Azure Tenant Service Topology

## 1. Purpose

This document maps the fully in-memory V2 platform onto an Azure deployment
topology where durable state is held only in Azure Storage blobs and append
blobs.

The platform is still provider-neutral at the API and module level, but the
first cloud deployment target is:

```text
one Azure Storage account
  -> one storage container per tenant
  -> RA-GZRS / read-access geo-zone-redundant storage
  -> in-memory API services loading/replaying tenant blobs
```

The user-facing spelling "RA-ZGRS" maps to Azure's RA-GZRS concept:
read-access geo-zone-redundant storage.

The topology is also dual/multi-writer aware. A tenant may be configured with
multiple storage accounts. The indexing endpoint writes each accepted record to
all required storage replicas before returning success, or queues the write and
returns an operation when async commit is configured.

The topology is multi-region/multi-cluster aware. Global load balancers route to
healthy regions, and cluster ingress routes tenant/partition traffic to the
owning service instance.

## 2. Tenant storage model

Each tenant gets one container under the same storage account:

```text
storage account: retailsearchprod
container: tenant-{tenantId}
```

Dual-account tenant example:

```text
primary storage account:   retailsearchprod-a
secondary storage account: retailsearchprod-b
container on both:         tenant-{tenantId}
commit policy:             all_required
```

Container layout:

```text
/manifests/current.json
/branches/{branch}/partition-map/current.json
/branches/{branch}/snapshots/{version}/catalog.json
/branches/{branch}/snapshots/{version}/features/*.parquet
/branches/{branch}/snapshots/{version}/runtime-manifest.json

/branches/{branch}/append/catalog-deltas/{partitionId}/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/inventory/{partitionId}/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/events/{partitionId}/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/user-audit/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/product-interactions/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/rules/YYYY/MM/DD/segment-{id}.jsonl
/branches/{branch}/append/operations/YYYY/MM/DD/segment-{id}.jsonl
```

Tenant isolation rules:

- every API request resolves to exactly one tenant container
- tenant storage config may resolve that container across multiple storage
  accounts
- services never mix tenant containers in memory
- runtime cache keys include tenant ID and branch
- model/enrichment jobs read and write only within the tenant container
- admin configuration is stored as tenant-scoped append records and snapshots

## 3. Service topology

```text
                  ┌──────────────────────┐
                  │ Admin Console UI      │
                  └──────────┬───────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                    API Host / Gateway                    │
└───────┬────────────┬─────────────┬─────────────┬────────┘
        │            │             │             │
┌───────▼──────┐ ┌───▼───────┐ ┌──▼────────┐ ┌──▼─────────┐
│ Indexing     │ │ Model     │ │ Search &  │ │ Tenant/Admin│
│ Endpoint     │ │ Integration│ │ Recommend │ │ Config      │
└───────┬──────┘ └───┬───────┘ └──┬────────┘ └──┬─────────┘
        │            │             │             │
        └────────────┴─────────────┴─────────────┘
                             │
                 ┌───────────▼───────────┐
                 │ Tenant Azure Container │
                 │ snapshots + appends    │
                 └───────────────────────┘
```

## 4. Endpoint responsibilities

### 4.1 Indexing endpoint

The indexing endpoint is the only write-ingress path for ordered durable data.

Responsibilities:

- validate incoming records
- assign or verify sequence numbers
- append ordered records to tenant append blobs on every required storage
  account replica
- return success only after required replicas satisfy the tenant commit policy
- write user audit trails
- write product interaction logs
- write catalog/inventory/rules ingress records
- write tail markers when segments close
- publish change notifications to consumers
- update the tenant live overlay where applicable
- repair partial replica writes using deterministic record IDs and watermarks

Owned streams:

```text
catalog-deltas
inventory
events
user-audit
product-interactions
rules
operations
```

The indexing endpoint does not perform heavy semantic enrichment. It validates
and persists the raw accepted record first.

Dual-write modes:

| Mode | Behavior |
| --- | --- |
| `sync_all_required` | API call returns after all required replicas commit. |
| `queued_all_required` | API call returns operation/accepted; operation completes after all required replicas commit. |
| `primary_then_repair` | API call returns after primary commit; repair worker catches up optional replicas. |

Catalog, inventory, rules, audit and operations should use
`sync_all_required` or `queued_all_required`. User events may use
`queued_all_required` when throughput matters more than immediate durability.

### 4.2 Model integration endpoint

The model integration endpoint consumes committed data from the indexing
endpoint and produces enriched artifacts.

Responsibilities:

- read committed append segments and snapshots
- pass selected data through one or many model providers
- apply custom prompts where LLMs are used
- reshape model outputs into V2 schema-compatible fields
- enrich products with retail-specific intelligence
- enrich query/event data into features
- produce semantic classifications, embeddings and rerank features
- write enriched outputs back as blob snapshots or append records
- notify runtime builders that enrichment outputs changed

Retail intelligence outputs:

- semantic enrichment
- taxonomy classification
- attribute extraction
- compatibility facts
- query understanding hints
- product embeddings
- query embeddings
- reranking features
- quality scores
- cold-start features

Model provider rule:

```text
models are adapters; enriched outputs are V2 schema artifacts
```

This prevents the platform from depending on any one LLM vendor.

### 4.3 Search and recommendation endpoint

The search/recommendation endpoint is the low-latency read-serving path.

Responsibilities:

- load tenant runtime from blob snapshots
- replay committed append segments up to watermarks
- maintain tenant in-memory base runtime and live overlay
- serve search
- serve browse/category requests
- serve recommendations
- serve autocomplete
- apply rules, personalization and live inventory overlays
- emit attribution tokens for event/KPI joins

It should not write durable data directly. Any event generated from serving
responses is sent to the indexing endpoint.

### 4.4 Admin console UI

The admin console is a simple tenant configuration and merchandising interface.

Responsibilities:

- configure tenant settings
- enable/disable features
- manage serving configs
- manage rules and controls
- manage enrichment/model configuration
- inspect catalog quality issues
- inspect event ingestion health
- inspect runtime versions and watermarks
- trigger rebuild/compaction jobs
- preview/test rules before publishing

Admin mutations go through API endpoints and are persisted as append records.

### 4.5 Catalog endpoint

Responsibilities:

- product create/patch/delete/import/purge API surface
- product get/list
- catalog snapshot import
- branch/version selection
- product schema validation
- primary/variant/collection validation

Durable writes go through the indexing endpoint as catalog delta records.

### 4.6 User events endpoint

Responsibilities:

- browser/mobile event collection
- server-side event writes
- bulk user event import
- event purge requests
- event rejoin requests
- event validation
- event attribution token checks

Accepted writes are forwarded to the indexing endpoint for ordered append.

### 4.7 Inventory endpoint

Responsibilities:

- set inventory
- add local inventories
- remove local inventories
- validate timestamp/update precedence
- maintain live inventory overlay
- feed availability-aware ranking

Accepted writes are forwarded to the indexing endpoint as inventory append
records.

### 4.8 Rules endpoint

Responsibilities:

- create/list/get/patch/delete controls
- manage boost/bury/pin/filter/facet/reroute rules
- validate rule DSL
- preview/test rules
- attach/detach controls to serving configs
- publish rule changes

Published rule changes are forwarded to the indexing endpoint and later compiled
into the runtime rule plan.

## 5. Change notification model

The indexing endpoint notifies consumers after committed append writes.

Notification payload:

```json
{
  "tenantId": "tenant-123",
  "branchId": "default_branch",
  "stream": "events",
  "segmentId": "segment-000123",
  "tailMarker": {
    "sequence": 98231,
    "recordCount": 98231,
    "contentHash": "sha256:..."
  },
  "watermark": "segment-000123"
  "replicaWatermarks": {
    "primary": "segment-000123",
    "secondary": "segment-000123"
  }
}
```

Consumers:

- search/recommendation endpoint updates overlays or schedules replay
- model integration endpoint schedules enrichment
- compaction/runtime builder schedules snapshot rebuild
- admin console updates ingestion status

Notifications are hints. The source of truth is still the committed append blob
with a valid tail marker.

## 6. Endpoint-to-storage mapping

| Endpoint | Reads | Appends/writes |
| --- | --- | --- |
| Indexing | manifests, open segment metadata | all append streams |
| Model integration | snapshots, committed append streams | enrichment snapshots/appends |
| Search/recommendation | manifests, snapshots, committed append streams | none directly |
| Admin console/API | manifests, config snapshots | config/rule append records via indexing |
| Catalog | catalog snapshots | catalog deltas via indexing |
| User events | none/minimal validation lookups | events via indexing |
| Inventory | runtime/overlay for validation | inventory via indexing |
| Rules | rule snapshots | rules via indexing |

## 7. In-memory runtime per endpoint

| Endpoint | Runtime state |
| --- | --- |
| Indexing | small tenant stream state, open segment buffers, validation schemas |
| Model integration | batch working sets, model clients, enrichment outputs |
| Search/recommendation | full tenant `CatalogRuntime` + `LiveOverlay` |
| Admin console | tenant metadata cache, status views |
| Catalog | validation/runtime metadata cache |
| User events | validation schemas, optional small dedupe window |
| Inventory | live inventory overlay cache |
| Rules | rule validation/compiler cache |

Only search/recommendation requires the full serving runtime.

## 8. Build order

1. Tenant container resolver.
2. Cold blob manifest reader/writer.
3. Append blob writer with tail markers.
4. Indexing endpoint.
5. Catalog endpoint through indexing.
6. User events endpoint through indexing.
7. Inventory endpoint through indexing.
8. Runtime loader/replay.
9. Search/recommendation endpoint.
10. Rules endpoint and rule compiler.
11. Model integration endpoint.
12. Admin console UI.
