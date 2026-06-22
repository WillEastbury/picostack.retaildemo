# Blob Storage and Tail-Marker Log Design

## 1. Purpose

V2 is a completely in-memory serving platform. It does not use a local database,
local durable event store, Redis, external search index, external vector
database or hot operational store in the core design.

The only durable persistence is blob storage:

- load immutable snapshots from storage blobs
- append new records to blob storage append blobs
- use tail markers to identify committed append segments
- rebuild or recover all in-memory state from blobs

In Azure, the default topology is one storage container per tenant in a shared
storage account configured for RA-GZRS/read-access geo-zone-redundant storage.

## 2. Storage principle

```text
blob snapshots + committed append blob segments
  -> load/replay
  -> in-memory base runtime + live overlay
  -> serve APIs
```

The API host must be disposable. If the container is restarted, it recovers by:

1. reading the current manifest blob
2. loading the referenced snapshot blobs
3. replaying committed append blobs up to their tail markers
4. rebuilding the base runtime and live overlay in memory

No durable data is stored in containers. Container memory is cache/projection
only, and local filesystem use is temporary scratch only.

## 3. Blob layout

Recommended blob storage layout:

```text
/catalogs/{catalog}/branches/{branch}/manifests/current.json
/catalogs/{catalog}/branches/{branch}/partition-map/current.json
/catalogs/{catalog}/branches/{branch}/snapshots/{version}/catalog.json
/catalogs/{catalog}/branches/{branch}/snapshots/{version}/features/*.parquet
/catalogs/{catalog}/branches/{branch}/snapshots/{version}/runtime-manifest.json

/catalogs/{catalog}/branches/{branch}/append/catalog-deltas/{partitionId}/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
/catalogs/{catalog}/branches/{branch}/append/inventory/{partitionId}/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
/catalogs/{catalog}/branches/{branch}/append/events/{partitionId}/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
/catalogs/{catalog}/branches/{branch}/append/audit/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
/catalogs/{catalog}/branches/{branch}/append/operations/{yyyy}/{mm}/{dd}/segment-{id}.jsonl
```

## 4. Tail marker format

Each append segment ends with an explicit tail marker record.

```json
{
  "recordType": "tail",
  "segmentId": "events-20260622-000001",
  "sequence": 98231,
  "recordCount": 98231,
  "contentHash": "sha256:...",
  "minEventTime": "2026-06-22T00:00:00Z",
  "maxEventTime": "2026-06-22T00:05:00Z",
  "closedTime": "2026-06-22T00:05:01Z"
}
```

A segment is committed only if:

- the tail marker exists
- the sequence and record count match the records read
- the content hash matches
- the segment ID matches the manifest or listing entry

Segments without a valid tail marker are treated as uncommitted and ignored or
repaired by the writer.

## 5. Append record envelope

All append blobs should use a shared envelope:

```json
{
  "recordType": "event",
  "segmentId": "events-20260622-000001",
  "sequence": 123,
  "recordId": "evt-001",
  "recordTime": "2026-06-22T11:01:00Z",
  "payload": {}
}
```

Record types:

| Record type | Purpose |
| --- | --- |
| `catalog_delta` | Product create/patch/delete/tombstone. |
| `inventory_update` | Inventory and local inventory updates. |
| `event` | User event. |
| `control_update` | Control/rule changes. |
| `serving_config_update` | Serving config changes. |
| `operation_update` | Long-running operation state. |
| `audit` | Audit entry. |
| `tail` | Segment commit marker. |

## 6. Writer behavior

Writers must:

- append records in sequence order
- buffer records into bounded segments
- write one tail marker when the segment closes
- never mutate a closed segment
- open a new segment after tail marker write
- use idempotent `recordId` values where possible
- expose the current open segment in memory only

Writers may be configured for one or more storage account replicas. In that
mode, the indexing endpoint writes the same ordered record envelope to every
configured account/container replica.

Dual/multi-writer rule:

```text
record accepted
  -> append to replica A
  -> append to replica B
  -> verify required replica commit policy
  -> then return success
```

This is not a banking-grade distributed transaction. It is an idempotent,
ordered, replayable multi-append contract. If a write partially succeeds, the
indexing endpoint records the failed replica and retries with the same
`recordId`, `segmentId` and `sequence` until replicas converge or the record is
dead-lettered.

The platform can acknowledge writes at two levels:

| Ack mode | Meaning |
| --- | --- |
| `accepted` | accepted into in-memory overlay and pending append flush |
| `durable` | written to append blob and covered by a tail marker |
| `multi_durable` | written to all required storage replicas and covered by tail markers |

Production-critical event ingestion should use `durable` or document the loss
window for `accepted`.

For tenant configurations with multiple required storage replicas, write APIs
should default to `multi_durable` for catalog, inventory, rules, audit and
operation streams. High-volume user events may use queued `accepted` mode when
loss/lag windows are acceptable.

## 6.1 Multi-account commit policy

Tenant storage config defines replica policy:

```json
{
  "storageReplicas": [
    { "name": "primary", "account": "retailsearchprod-a", "required": true },
    { "name": "secondary", "account": "retailsearchprod-b", "required": true },
    { "name": "analytics-copy", "account": "retailsearchanalytics", "required": false }
  ],
  "commitPolicy": "all_required"
}
```

Supported commit policies:

| Policy | Meaning |
| --- | --- |
| `primary_only` | Return after primary account commit. Other replicas are async best-effort. |
| `all_required` | Return only after all required replicas commit. |
| `queued_all_required` | Queue accepted work and complete operation only after all required replicas commit. |

`queued_all_required` is useful for slow paths where the caller can accept an
operation ID instead of waiting synchronously.

## 6.2 Partial write recovery

Partial writes are expected and recoverable.

Recovery uses:

- deterministic `recordId`
- deterministic `segmentId`
- deterministic `sequence`
- idempotent append/replay handling
- per-replica watermarks
- tail marker validation

If one replica has a record and another does not, the repair worker appends the
missing record to the lagging replica. If tail markers differ, the segment is
marked inconsistent and repaired or superseded by a later compaction snapshot.

## 7. Reader/recovery behavior

Recovery reads:

```text
current manifest
  -> snapshot blobs
  -> committed append segments
  -> in-memory runtime
```

Replay order:

1. catalog snapshot
2. feature snapshots
3. catalog deltas
4. inventory updates
5. controls and serving config updates
6. user events
7. operations/audit metadata

Within each stream, records are ordered by:

```text
segment path/time -> sequence
```

Deduplication uses:

```text
recordType + recordId
```

## 8. Compaction model

Append blobs are the write path. Snapshot blobs are the compaction output.

```text
append segments
  -> compaction job
  -> new catalog/features/runtime snapshot
  -> manifest update
  -> old segments retained until retention expiry
```

Compaction produces:

- catalog snapshot
- feature Parquet snapshots
- runtime manifest
- operation summary
- compaction audit record

## 9. Manifest model

`current.json` identifies the committed serving version:

```json
{
  "catalogId": "default_catalog",
  "branchId": "default_branch",
  "runtimeVersion": "2026-06-22T12:00:00Z",
  "catalogSnapshot": "snapshots/2026-06-22T12:00:00Z/catalog.json",
  "featureSnapshots": [
    "snapshots/2026-06-22T12:00:00Z/features/product_stats.parquet"
  ],
  "appendWatermarks": {
    "catalog-deltas": "segment-000010",
    "inventory": "segment-000119",
    "events": "segment-009832"
  },
  "replicaWatermarks": {
    "primary": {
      "events": "segment-009832"
    },
    "secondary": {
      "events": "segment-009832"
    }
  }
}
```

Manifest updates must be atomic from the reader's perspective. The writer should
write a new manifest blob/version and then update the `current` pointer.

## 10. In-memory overlays with append persistence

High-churn writes update the live overlay first:

```text
API write
  -> validate
  -> append to append blob
  -> apply to LiveOverlay
  -> return
```

If `durable` ack is required:

```text
API write
  -> validate
  -> append
  -> close/tail or ensure covered by committed segment policy
  -> apply overlay
  -> return
```

The overlay is never the source of truth. It is a replayable projection of cold
append blobs.

## 11. Operational implications

Because all durable state is in blobs:

- API containers can be replaced at any time
- read replicas can load the same manifest
- builder jobs can publish new snapshots independently
- no local disk is required except temporary build scratch
- no Redis/database is required for the base architecture

Tradeoffs:

- recovery time depends on snapshot size and append replay volume
- tail-marker commit policy determines event loss window
- highly real-time multi-replica overlays require either sticky routing or fast
  append visibility/replay
- compaction cadence is critical to bound replay time

## 12. Build requirements

Build modules:

- `ColdBlobReader`
- `ColdBlobAppendWriter`
- `TailMarkerValidator`
- `ManifestReader`
- `ManifestPublisher`
- `AppendReplayService`
- `CompactionService`
- `OverlayProjector`

Python interfaces:

```python
class ColdBlobStore(Protocol):
    def read_json(self, path: str) -> dict: ...
    def read_bytes(self, path: str) -> bytes: ...
    def list(self, prefix: str) -> Iterable[BlobInfo]: ...

class AppendBlobWriter(Protocol):
    def append(self, stream: str, record: AppendRecord) -> None: ...
    def close_segment(self, stream: str) -> TailMarker: ...

class AppendReplayService(Protocol):
    def replay(self, manifest: RuntimeManifest) -> ReplayResult: ...
```

## 13. Architecture statement

V2 persistence is:

```text
blob snapshots + append blobs with tail markers
```

V2 serving is:

```text
entirely in memory
```

V2 recovery is:

```text
load snapshots + replay committed append blobs
```
