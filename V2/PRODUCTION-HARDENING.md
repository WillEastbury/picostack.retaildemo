# Production Hardening, Security, Logging and Performance

## 1. Purpose

This document captures the productionizing work required beyond the first useful
implementation.

The goal is to harden the platform while preserving the core constraints:

- state-of-the-art retail search and recommendations
- less than `$0.10 / 1,000` served requests
- reuse proven libraries before building custom infrastructure
- fully in-memory serving
- durable state only in blob storage
- ephemeral containers
- partitioned data and sticky routing
- explicit justification for external services beyond AKS and Azure Storage

## 2. Production modules to build

| Area | What to build | Est. LoC |
| --- | --- | ---: |
| Structured logging | JSON logs, correlation IDs, tenant/partition/request IDs, redaction | 300-600 |
| Metrics | Prometheus metrics, latency histograms, per-endpoint counters, watermarks | 400-700 |
| Tracing | OpenTelemetry spans across API, indexing, blob and runtime operations | 300-600 |
| Health/readiness | Runtime loaded, partition ownership, lease status, blob reachability | 300-500 |
| Security middleware | JWT validation, scopes, tenant isolation, request size limits | 500-900 |
| STS hardening | key rotation, JWKS, token exchange, service tokens, clock skew | 700-1,200 |
| Input validation | schema hardening, dead-letter records, field limits, payload limits | 500-900 |
| PII protection | event redaction, blocked fields, pseudonymous IDs, audit checks | 400-800 |
| Audit logging | admin/rule/catalog changes, who/what/when, append-only audit stream | 400-700 |
| Rate limiting | per-tenant/per-token quotas, ingress-friendly limiter | 300-700 |
| Backpressure | queue depth, write throttling, model job throttling, 429/503 behavior | 400-800 |
| Lease resilience | renew loop, lease-break handling, owner fencing, stale owner detection | 500-900 |
| Replica repair | partial dual-write repair, replica lag metrics, replay verification | 600-1,000 |
| Runtime safety | versioned page tokens, stale token handling, runtime rollback | 400-800 |
| Performance optimization | packed indexes, cache warming, candidate caps, scratch buffers | 800-1,500 |
| Load testing | mixed ingestion/search/recommend workloads | 300-600 |
| Chaos/failure tests | lease loss, blob failure, replica lag, partition failover | 400-800 |
| Admin operations | rebuild/failover controls, partition status, operation status | 700-1,200 |
| Deployment hardening | AKS probes, PDBs, resource limits, HPA/KEDA, rollout strategy | 300-600 |
| Runbooks | operational playbooks for failover, repair, rollback, tenant disable | 300-600 |

Production hardening subtotal:

```text
8,100-15,900 LoC
```

## 3. Revised implementation size

| Scope | Est. LoC |
| --- | ---: |
| First useful implementation | 4,800-7,700 |
| Core owned platform modules | 7,700-11,950 |
| Production hardening | 8,100-15,900 |
| Tests | +50-100% depending rigor |

Credible production MVP:

```text
20k-35k LoC including tests
```

Fuller production-grade platform:

```text
35k-55k LoC including tests, admin UI, runbooks and performance harnesses
```

## 4. Production design principles

```text
Fail closed for security.
Fail visible for data quality.
Fail retryable for blob/replica writes.
Fail stale-but-safe for reads where allowed.
Never silently drop events.
Never mutate durable state outside indexing.
Never trust tenant IDs from request paths without token validation.
Never store durable data in containers.
```

## 5. Logging design

Logs must be structured JSON.

Every log entry should include:

- timestamp
- level
- service role
- tenant ID
- request ID
- correlation ID
- partition ID where available
- partition map version where available
- runtime version where available
- operation ID where available
- error code where available

Sensitive fields must be redacted before logging.

Do not log:

- raw tokens
- raw PII
- full event payloads containing customer identifiers
- model prompts containing tenant-private data unless explicitly configured for
  secure audit

## 6. Metrics design

Expose metrics for:

- request count by endpoint/status
- p50/p95/p99 latency by endpoint
- cost approximation per 1,000 requests
- partition owner health
- blob lease renewals/failures
- append write latency
- replica commit latency
- replica lag
- tail marker validation failures
- runtime load time
- runtime memory by tenant/partition
- overlay size by tenant/partition
- model/enrichment job duration
- validation failures and dead-letter counts

Start with `prometheus-client`; add OpenTelemetry only when traces are needed.

## 7. Security hardening

Required:

- JWT validation on every API except health probes
- tenant claim validation
- endpoint scope validation
- tenant/container binding
- request size limits
- per-tenant quotas
- admin action audit
- STS signing key rotation
- JWKS endpoint
- service-to-service token flow
- token clock-skew tolerance
- blocked-field PII checks for events

Fail closed when identity, tenant or scope is ambiguous.

## 8. Data quality hardening

The indexing endpoint must:

- validate schema
- enforce event type enums
- enforce payload size limits
- enforce product/variant ID rules
- derive or require `eventId`
- validate attribution fields where needed
- write invalid records to a dead-letter append stream
- expose dead-letter metrics and admin views

No accepted write should disappear silently.

## 9. Runtime safety

Runtime responses must be version-aware.

Required:

- runtime version in diagnostics/status
- page tokens bound to runtime version and request hash
- stale page token behavior
- runtime rollback support
- partition map version in routing/debug output
- old runtime retention window for pagination where feasible

## 10. Blob/replica write resilience

The indexing path must support:

- retries with bounded backoff
- idempotent `recordId`
- deterministic `segmentId`
- deterministic `sequence`
- lease fencing
- partial replica repair
- per-replica watermarks
- tail marker verification
- operation status for queued commits

Partial writes are recoverable. They are not considered successful until the
configured commit policy is satisfied.

## 11. Performance optimization priorities

1. Keep hot path in memory.
2. Avoid per-request model calls.
3. Bound candidate counts before reranking.
4. Use packed arrays, bitmaps and vector buffers.
5. Keep overlays bounded.
6. Cache query plans and popular query results.
7. Pre-warm runtime partitions before routing traffic.
8. Track p95/p99 latency per endpoint and partition.
9. Track cost per 1,000 requests.
10. Use external services only when justified.

## 12. Load and chaos testing

Minimum load scenarios:

- search-only traffic
- recommendation-only traffic
- autocomplete-only traffic
- mixed search/recommend/events
- high-volume event ingestion
- inventory update burst
- catalog delta burst
- partition rebalance during traffic
- dual-write replica lag

Failure scenarios:

- blob append failure
- secondary replica lag
- lease renewal failure
- partition owner death
- region failover
- stale manifest
- corrupt tail marker
- runtime load failure

## 13. AKS hardening

Required:

- readiness probe checks runtime and partition ownership
- liveness probe checks process health only
- resource requests/limits
- PodDisruptionBudgets for serving/indexing
- graceful shutdown/drain for partition owners
- HPA for read-serving roles
- KEDA or Jobs for builder/model workloads where needed
- zero-downtime rollout for read-serving roles
- explicit singleton/partition ownership for indexing roles

## 14. Runbooks

Runbooks must cover:

- tenant disable
- partition failover
- lease break
- replica repair
- runtime rollback
- bad catalog import
- bad rules publish
- event replay
- model/enrichment rollback
- storage account failover
- regional failover

