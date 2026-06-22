# AKS FastAPI Dev, Operations and Authentication Design

## 1. Purpose

This document defines the simplest operational shape for fast development and
agile delivery of Retail Search V2 on AKS.

The platform remains:

- Python-first
- FastAPI-first
- container-first
- fully in-memory for serving
- completely ephemeral at the container layer
- cold-blob-only for durable state
- modular enough to split later

The bias is to minimize platform ceremony until scale forces a split.

## 2. Simplicity principles

Use the fewest moving parts that preserve correctness:

1. One Python codebase.
2. One base container image.
3. Multiple FastAPI apps/process roles from the same image.
4. One AKS namespace per environment.
5. One storage account per environment.
6. One Azure Storage container per tenant.
7. One indexing write path for durable records.
8. One STS/auth service for internal and tenant tokens.
9. Blob snapshots and append blobs as the only durable state.
10. GitOps or simple `kubectl apply` manifests before introducing heavier tooling.

## 3. Service shape on AKS

Start with one image and multiple deployments:

```text
retail-v2-api image
  -> search-recommendation deployment
  -> indexing deployment
  -> model-integration deployment
  -> admin-api deployment
  -> auth-sts deployment
  -> builder/compactor job or cronjob
```

All deployments use the same source tree and container image. The role is
selected by command or environment variable:

```text
SERVICE_ROLE=search
SERVICE_ROLE=indexing
SERVICE_ROLE=model
SERVICE_ROLE=admin
SERVICE_ROLE=sts
SERVICE_ROLE=builder
```

This keeps build/release simple while preserving module boundaries.

Pods must not store durable data. They may cache runtime partitions in memory
and use local disk only as temporary scratch during a build or load.

## 4. Minimal container image

Use a simple Python image:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock* requirements.txt* /app/
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY retail_v2 /app/retail_v2
CMD ["python", "-m", "uvicorn", "retail_v2.api_host:create_app", "--host", "0.0.0.0", "--port", "8080"]
```

If `uv` is used, keep it as a build-time convenience, not a runtime dependency.

Recommended first runtime dependencies:

```text
fastapi
uvicorn
pydantic
orjson
azure-storage-blob
azure-identity
polars
pyarrow
duckdb
sortedcontainers
rapidfuzz
hnswlib or usearch
fastembed
prometheus-client
```

## 5. Environments

Use three environments:

| Environment | Purpose | AKS namespace |
| --- | --- | --- |
| `dev` | fast iteration, disposable data | `retail-v2-dev` |
| `staging` | E2E validation, production-like topology | `retail-v2-staging` |
| `prod` | tenant serving | `retail-v2-prod` |

Each environment has:

- one namespace
- one storage account
- one container registry path/tag stream
- one config map
- one Key Vault or secret source
- one ingress hostname

## 6. CI/CD pipeline

Keep the pipeline linear:

```text
commit
  -> unit tests
  -> build image
  -> push image
  -> deploy dev
  -> smoke test
  -> promote same image to staging
  -> E2E/load test
  -> promote same image to prod
```

Do not rebuild between environments. Promote the same immutable image digest.

Minimum checks:

- Python unit tests
- schema validation tests
- sample catalog runtime build
- FastAPI route smoke test
- blob append/replay test
- auth token validation test

## 7. Deployment management

Start with plain Kubernetes YAML:

```text
k8s/
  base/
    deployment-search.yaml
    deployment-indexing.yaml
    deployment-model.yaml
    deployment-admin.yaml
    deployment-sts.yaml
    cronjob-builder.yaml
    service.yaml
    ingress.yaml
  overlays/
    dev/
    staging/
    prod/
```

Move to Helm/Kustomize only when repetition becomes painful.

For fast development:

- use image tags based on commit SHA
- use `kubectl rollout restart` or image patch
- expose `/healthz`, `/readyz`, `/status`
- keep app config in environment variables
- keep tenant feature flags in blob config snapshots

## 8. Runtime roles

### Search/recommendation deployment

Purpose:

- read-serving path
- holds tenant `CatalogRuntime` in memory
- maintains bounded live overlay
- serves search/recommend/autocomplete/product read APIs

Scaling:

- horizontal read replicas
- replicas load runtime from blobs
- session personalization requires sticky routing or shared overlay strategy
- ingress/LB routes partition keys to owning replicas so partition ownership can
  change without moving data between pods

### Indexing deployment

Purpose:

- sole durable write ingress
- validates all write records
- appends to tenant append blobs
- writes tail markers
- sends change notifications

Scaling:

- start with one replica per environment for strict ordering
- later shard by tenant or stream

### Model integration deployment

Purpose:

- enrichment
- classification
- semantic embedding
- reranking feature generation
- prompt-based model adapters

Scaling:

- async/background jobs
- can be scaled independently from serving

### Builder/compactor job

Purpose:

- compact append blobs
- build feature snapshots
- build runtime artifacts
- publish manifests

Run as:

- Kubernetes CronJob
- manual Job
- event-triggered Job later

### Admin API/UI

Purpose:

- tenant configuration
- feature toggles
- rules/controls
- serving configs
- runtime status
- ingestion health

Admin writes go through indexing.

### Auth/STS deployment

Purpose:

- authenticate callers
- issue short-lived service/tenant tokens
- provide token exchange for internal services
- validate tenant/resource scope

## 9. Authentication and STS

The STS is a first-class service.

Responsibilities:

- validate external identity provider tokens
- mint short-lived V2 access tokens
- mint internal service-to-service tokens
- bind tokens to tenant/container scope
- bind tokens to roles/permissions
- expose JWKS for token validation
- support key rotation
- support token introspection for admin/debug

Token claims:

```json
{
  "iss": "https://auth.retail-v2.example",
  "sub": "user-or-service-id",
  "aud": "retail-v2",
  "tenant": "tenant-123",
  "roles": ["search.query", "events.write"],
  "scope": "catalog:read events:write search:query",
  "exp": 1760000000
}
```

Role examples:

| Role/scope | Allowed |
| --- | --- |
| `search.query` | Search/recommend/autocomplete read APIs. |
| `catalog.read` | Product get/list. |
| `catalog.write` | Catalog import/patch via indexing. |
| `events.write` | User event collect/write. |
| `inventory.write` | Inventory updates. |
| `rules.admin` | Rule/control management. |
| `tenant.admin` | Tenant configuration and feature flags. |
| `service.indexing` | Internal indexing writes. |
| `service.model` | Model enrichment jobs. |

## 10. Auth flow

External caller:

```text
client identity token
  -> STS token exchange
  -> V2 access token
  -> API call with Bearer token
  -> API validates JWT + tenant scope
```

Internal service:

```text
workload identity
  -> STS service token
  -> call indexing/model/search endpoint
```

Admin console:

```text
admin login
  -> STS token exchange
  -> tenant/admin-scoped token
  -> admin API calls
```

## 11. Tenant authorization

Every request resolves:

```text
token tenant claim -> Azure storage container -> runtime cache key
```

The API must reject:

- missing tenant claim
- tenant claim that does not match URL/path/resource
- scope insufficient for endpoint
- attempt to read/write another tenant container

## 12. Secret and identity management

Use AKS Workload Identity where possible.

Secrets needed:

- STS signing keys or Key Vault key references
- external identity provider configuration
- storage account endpoint
- optional model provider credentials

Avoid storing:

- storage account keys in app config
- long-lived service credentials
- tenant secrets in app pods

## 13. Management API

Minimal management endpoints:

```text
GET  /status
GET  /status/runtime
GET  /status/tenants/{tenant}
GET  /status/ingestion/{tenant}
POST /admin/tenants/{tenant}/features
POST /admin/tenants/{tenant}/rebuild
POST /admin/tenants/{tenant}/rules:preview
POST /admin/tenants/{tenant}/rules:publish
```

Keep this small. Admin console should call these endpoints rather than editing
storage directly.

## 14. Observability

Expose:

- request count/latency by endpoint
- runtime version loaded per tenant
- overlay size per tenant
- append blob lag/watermark
- tail marker failures
- indexing validation failures
- model job duration/failures
- search/recommendation p95
- token validation failures

Use:

- `prometheus-client`
- stdout JSON logs
- Kubernetes events
- optional OpenTelemetry later

## 15. Fast development workflow

Developer loop:

```text
run FastAPI locally
  -> use local emulator/fake blob adapter
  -> load sample catalog
  -> run unit tests
  -> build image
  -> deploy dev namespace
```

Use a blob-store abstraction:

```python
class BlobStore:
    def read_bytes(path: str) -> bytes: ...
    def write_blob(path: str, data: bytes) -> None: ...
    def append_record(stream: str, record: dict) -> None: ...
    def list(prefix: str) -> list[BlobInfo]: ...
```

Adapters:

- `LocalFileBlobStore` for developer tests only
- `AzureBlobStore` for AKS

The production architecture remains blob storage. The local adapter is a
development harness, not a production persistence mode.

## 16. Keep it agile

Avoid early complexity:

- no service mesh initially
- no Helm until plain manifests hurt
- no distributed cache initially
- no separate repo per service
- no external vector DB initially
- no database for core durable state
- no complex workflow engine initially

Add complexity only when a clear bottleneck appears.

## 17. First build slice

The smallest useful AKS slice:

1. STS issues tenant-scoped tokens.
2. Indexing endpoint appends event records to tenant append blob.
3. Catalog endpoint imports sample catalog through indexing.
4. Search endpoint loads tenant catalog snapshot into memory.
5. Search endpoint answers basic query.
6. User events endpoint records attribution-linked click/add-to-cart events.
7. Admin status page shows runtime version and append watermarks.

This validates the core platform without building every model feature first.
