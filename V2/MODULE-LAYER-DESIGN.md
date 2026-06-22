# Module and Layer Design

## 1. Layer stack

```text
Presentation layer
  -> API layer
  -> Auth and tenant layer
  -> Routing and partition layer
  -> Domain service layer
  -> Runtime/query layer
  -> Storage/indexing layer
  -> Blob persistence layer
```

Each layer has narrow responsibilities and should be testable independently.

## 2. Presentation layer

Modules:

- Admin Console UI
- API documentation
- status dashboards

Responsibilities:

- tenant configuration UI
- rule management UI
- runtime/partition/watermark visibility
- feature toggles

Does not:

- write storage directly
- bypass auth/STS
- bypass indexing

## 3. API layer

Modules:

- FastAPI app factory
- native API routers
- commerce-compatible routers
- request/response schemas

Responsibilities:

- parse requests
- validate payloads
- map routes to services
- emit responses
- expose health/readiness/status

Key files/modules:

```text
retail_v2/api_host.py
retail_v2/routers/catalog.py
retail_v2/routers/events.py
retail_v2/routers/search.py
retail_v2/routers/recommend.py
retail_v2/routers/admin.py
```

## 4. Auth and tenant layer

Modules:

- STS
- token validator
- tenant resolver
- scope/role authorizer

Responsibilities:

- issue tenant-scoped JWTs
- validate JWTs
- resolve tenant container
- enforce endpoint scopes
- reject cross-tenant access

Interfaces:

```python
class TenantContext:
    tenant_id: str
    branch_id: str
    scopes: set[str]
```

## 5. Routing and partition layer

Modules:

- partition key resolver
- partition map reader
- partition owner resolver
- ingress routing metadata
- failover coordinator

Responsibilities:

- derive partition key
- compute partition ID
- resolve region/cluster/owner
- enforce sticky routing
- expose partition headers
- manage partition map version

Interfaces:

```python
class PartitionRouter:
    def resolve(self, tenant: TenantContext, key: str) -> PartitionRoute: ...
```

## 6. Domain service layer

Modules:

- CatalogService
- UserEventService
- InventoryService
- RulesService
- SearchService
- RecommendationService
- AutocompleteService
- ModelIntegrationService
- AdminService
- OperationService

Responsibilities:

- implement business behavior
- call indexing for durable writes
- call runtime for reads
- never write blobs directly except through owned storage/indexing services

## 7. Runtime/query layer

Modules:

- RuntimeRegistry
- CatalogRuntime
- LiveOverlay
- QueryUnderstanding
- SearchRanker
- RecommendationRanker
- FacetEngine
- FilterEngine
- AutocompleteEngine

Responsibilities:

- hold in-memory runtime shards
- serve low-latency queries
- merge base runtime with overlay
- apply ranking/rules/personalization
- produce attribution tokens

Data structures:

- packed postings
- vector buffers
- bitmaps
- sorted arrays
- compact product records
- columnar feature views

## 8. Storage/indexing layer

Modules:

- IndexingService
- AppendWriter
- TailMarkerWriter
- TailMarkerValidator
- LeaseManager
- ReplicaCommitCoordinator
- PartitionAppendPlanner
- ReplayService

Responsibilities:

- validate append records
- own ordered partition writes
- acquire/renew blob leases
- append to primary and required replicas
- write tail markers
- track watermarks
- repair partial writes
- notify consumers

Write interface:

```python
class IndexingService:
    def append(self, request: AppendRequest) -> AppendResult: ...
```

## 9. Blob persistence layer

Modules:

- BlobStore
- AzureBlobStore
- ManifestStore
- ProductBlobStore
- FeatureBlobStore
- AppendBlobStore

Responsibilities:

- read/write JSON blobs
- append records
- manage blob leases
- list partition paths
- read manifests
- publish manifests atomically

Interfaces:

```python
class BlobStore:
    def read_json(self, path: str) -> dict: ...
    def write_json(self, path: str, value: dict) -> None: ...
    def append(self, path: str, data: bytes) -> None: ...
    def acquire_lease(self, path: str, owner: str) -> Lease: ...
```

## 10. Cross-cutting modules

### Observability

- metrics
- structured logs
- traces
- status endpoints

### Cost accounting

- request count by endpoint
- CPU time approximation
- model job cost
- storage operation count
- cost per 1,000 requests

### Safety

- tenant isolation
- PII checks
- event retention
- audit records
- admin action approval

## 11. Module dependency rule

Allowed dependency direction:

```text
API -> auth/tenant -> routing -> domain -> runtime/storage
```

Forbidden:

- runtime importing API routers
- admin UI writing blob storage directly
- search service appending durable records directly
- model integration bypassing indexing for durable writes
- storage layer depending on domain services

## 12. Suggested package layout

```text
retail_v2/
  api/
  auth/
  tenancy/
  partitioning/
  domain/
    catalog/
    events/
    inventory/
    rules/
    search/
    recommend/
    autocomplete/
    model_integration/
    admin/
  runtime/
  indexing/
  storage/
  observability/
  schemas/
```

## 13. First module build order

1. `storage.BlobStore`
2. `partitioning.PartitionMap`
3. `indexing.AppendWriter`
4. `indexing.LeaseManager`
5. `auth.STS`
6. `domain.catalog`
7. `runtime.RuntimeBuilder`
8. `domain.search`
9. `domain.events`
10. `domain.inventory`
11. `domain.rules`
12. `domain.recommend`
13. `domain.admin`

