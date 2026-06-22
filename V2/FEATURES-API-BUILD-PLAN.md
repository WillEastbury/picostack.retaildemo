# Retail Search V2 Features, API Surface Mapping and Build Plan

## 1. Purpose

This document consolidates the Retail Search V2 product requirements into one
implementation-oriented plan:

- feature catalogue
- external commerce API compatibility mapping
- runtime architecture required to replicate the features
- ETL, indexing, model, serving and operations work to build

The target is a provider-neutral retail search and recommendations engine that
can be compatible with commerce-style product/event/serving concepts without
depending on a managed cloud provider, a managed provider or any single managed provider.

## 2. Product capabilities to replicate

| Capability | Required V2 behavior | Major components to build |
| --- | --- | --- |
| Product search | Keyword, browse and hybrid semantic search over primary products, variants and collections. | Product API, catalog schema, lexical index, semantic/vector index, ranking engine. |
| Semantic search / intent understanding | NLP query understanding, synonym detection, intent/entity/category/attribute extraction. | Query understanding model hook, synonym expansion, intent cache, semantic query vectors. |
| Dynamic facets | Facet counts over filtered result sets, category/brand/price/availability/rating/custom attributes. | Facet index, filter parser, facet count engine, attribute config. |
| Boost / bury / pin / filter | Merchandising controls alter result ordering without replacing relevance entirely. | Controls API, rule compiler, ranking rule stage, applied-control diagnostics. |
| Personalized search | Session/visitor/persona features affect ranking in real time. | Event ingestion, persona feature store/materialized views, personalization scorer. |
| Recommendations | Recommended-for-you, similar items, frequently bought together, cart complements and more. | Recommendation API, candidate graphs, objective-specific ranking, real-time overlay. |
| Curated recommendation models | Model types for CTR, conversion, revenue/order, margin, cross-sell, upsell, cold-start. | Model registry, offline training/materialization jobs, serving config objectives. |
| Search-based recommendations | Bestsellers, new arrivals, trending, top-rated, popular-for-query/category. | Event aggregations, freshness/rating/trending indexes, placement configs. |
| Predictive autocomplete | Search, brand, category and product-preview suggestions as users type. | Completion data import, prefix index, suggestion scorer, product preview hydration. |
| Conversational refinement | Broad/ambiguous queries return ordered clarification questions. | Question flow schema/API, trigger compiler, session preference writes. |
| Cold-start users/products | Useful results with sparse history using content, taxonomy, priors and session context. | Enrichment pipeline, content features, global/category priors, cold-start candidate views. |
| Catalog enrichment | Infer taxonomy, attributes, quality signals, image tags and searchable/facetable metadata. | Offline enrichment jobs, quality diagnostics, derived attributes. |
| Inventory-aware serving | Availability, local inventory, fulfillment and price changes affect ranking/results. | Inventory APIs, timestamp-aware update handling, availability indexes. |
| No-results alternatives | Failed searches return alternatives, adjacent categories, recommendations or questions. | No-results placement, fallback hierarchy, spelling/synonym expansion, recommendation fallback. |
| Cross-sell / upsell | Product, cart and checkout placements suggest complements, upgrades and add-ons. | Cross-sell/upsell candidate graphs, price ladder, compatibility and margin scoring. |
| Merchandising console support | Business users manage promotions, controls, serving configs and fallback logic. | Controls/serving config APIs, audit log, preview/test/publish flow. |
| KPI optimization | Ranking and recommendation strategies optimize explicit metrics. | KPI schema, experiment tracking, offline replay, online A/B hooks. |
| Safety/privacy | Tenant isolation, access control, GDPR delete/export, PII minimization, audit. | AuthZ layer, retention policy, event deletion/export, audit trail. |
| Composable commerce | Headless API-first services that fit existing stacks/channels. | Provider-neutral APIs, adapters, portable JSON snapshot, replaceable backends. |

## 3. Data domains

### 3.1 Catalog

The product catalog is the source for products, variants, collections, categories,
brands, attributes, prices, media, ratings, promotions and local inventory.

Build:

- `catalog.schema.json` validation
- import adapters from source systems
- commerce-compatible product shape
- product identity normalization
- primary/variant/collection relationship validation
- catalog quality diagnostics
- snapshot versioning and rollback

### 3.2 Inventory

Inventory controls availability, fulfillment, local price overrides and
rerouting.

Build:

- real-time inventory update endpoint
- `setInventory` compatibility endpoint
- `addLocalInventories` / `removeLocalInventories`
- timestamp-aware conflict handling
- location/fulfillment indexes
- availability-derived ranking features

### 3.3 User events

Events train and update personalization, ranking and recommendations.

Build:

- browser/mobile `collect`
- server-side `write`
- bulk `import`
- `purge` for compliance/rebuild
- `rejoin` to reconnect events to current product metadata
- event deduplication and checkpoints
- event materialization into query/product/session/persona stats

## 4. Commerce-compatible API surface

### 4.1 Products

Compatible resource:

```text
projects.locations.catalogs.branches.products
```

| API | V2 implementation |
| --- | --- |
| `create` | Create one product in update journal/staging snapshot. |
| `get` | Read product by resource name or product ID. |
| `list` | Page products in catalog branch. |
| `patch` | Partial update using update mask. |
| `delete` | Tombstone/delete product. |
| `import` | Bulk product import and runtime rebuild. |
| `purge` | Delete selected products by filter. |
| `setInventory` | Timestamp-aware inventory replacement. |
| `addLocalInventories` | Add/update place-level inventory. |
| `removeLocalInventories` | Remove place-level inventory. |

Build:

- product service
- product import pipeline
- product update journal
- field-mask patcher
- product purge/tombstone engine
- long-running operation tracking
- atomic runtime rebuild/swap

### 4.2 User events

Compatible resource:

```text
projects.locations.catalogs.userEvents
```

| API | V2 implementation |
| --- | --- |
| `collect` | Browser/mobile CORS-safe event endpoint. |
| `write` | Server-side single event endpoint. |
| `import` | Bulk historical event import. |
| `purge` | Delete events by filter. |
| `rejoin` | Rebind historical events to current catalog. |

Build:

- event schema
- event ingestion API
- durable event log
- event dedupe key
- browser-safe collection endpoint
- event import operation
- purge/rejoin jobs
- event-to-feature materializer

### 4.3 Placements

Compatible resource:

```text
projects.locations.catalogs.placements
```

| API | V2 implementation |
| --- | --- |
| `search` | Search a placement. |
| `predict` | Recommend for a placement. |

Build:

- placement aliases to serving configs
- search request parser
- predict request parser
- placement context resolver

### 4.4 Serving configs

Compatible resource:

```text
projects.locations.catalogs.servingConfigs
```

| API | V2 implementation |
| --- | --- |
| `create` | Create serving config. |
| `list` | List serving configs. |
| `get` | Read one serving config. |
| `patch` | Update serving config. |
| `delete` | Delete serving config. |
| `addControl` | Attach control/rule. |
| `removeControl` | Detach control/rule. |
| `search` | Search using serving config. |
| `predict` | Recommend using serving config. |

Build:

- serving config store
- placement/objective/ranking-weight schema
- control attachment index
- serving config compiler
- search/predict execution by config

### 4.5 Controls

Compatible resource:

```text
projects.locations.catalogs.controls
```

| API | V2 implementation |
| --- | --- |
| `create` | Create boost/bury/pin/filter/facet/rewrite control. |
| `list` | List controls. |
| `get` | Read one control. |
| `patch` | Update control. |
| `delete` | Delete control. |

Build:

- control schema
- control CRUD
- rule compiler
- applied-control diagnostics
- preview/test/publish lifecycle
- rollback/audit trail

### 4.6 Attributes config

Compatible resource:

```text
projects.locations.catalogs.attributesConfig
```

| API | V2 implementation |
| --- | --- |
| `addCatalogAttribute` | Add searchable/indexable/facetable/boostable attribute definition. |
| `removeCatalogAttribute` | Remove definition. |
| `replaceCatalogAttribute` | Replace definition. |
| `updateCatalogAttribute` | Update definition. |

Build:

- central attribute config
- attribute validation
- facet/filter/searchability compiler
- migration from product-level `searchable` / `indexable`

### 4.7 Completion data

Compatible resource:

```text
projects.locations.catalogs.completionData
```

| API | V2 implementation |
| --- | --- |
| `import` | Bulk import curated autocomplete data. |
| `purge` | Delete completion data by source/filter. |

Build:

- completion data schema
- completion import job
- completion purge job
- prefix index
- suggestion scorer

### 4.8 Models

Compatible resource:

```text
projects.locations.catalogs.models
```

| API | V2 implementation |
| --- | --- |
| `create` | Register/create model config. |
| `list` | List model configs. |
| `get` | Read one model config. |
| `delete` | Delete model config. |
| `pause` | Pause scheduled training/materialization. |
| `resume` | Resume training/materialization. |
| `tune` | Start tune/retrain job. |

Build:

- model registry
- model objective schema
- training/materialization scheduler
- daily retraining job
- tune operation
- model status/metrics

### 4.9 Catalogs

Compatible resource:

```text
projects.locations.catalogs
```

| API | V2 implementation |
| --- | --- |
| `get` | Get catalog metadata/config. |
| `list` | List catalogs for multi-catalog tenancy. |
| `patch` | Update catalog metadata/config. |
| `setDefaultBranch` | Switch active branch/snapshot. |

Build:

- catalog metadata store
- branch/snapshot registry
- atomic branch switch
- branch rollback

### 4.10 Operations

Long-running operations are required for:

- product import
- product purge
- event import
- event purge
- completion data import/purge
- model tuning
- runtime rebuild

Build:

- operation store
- operation progress metadata
- operation result/error schema
- get/list/cancel/delete APIs

## 5. Search request/response compatibility

### 5.1 Search request fields to support

Priority fields:

- `placement`
- `branch`
- `query`
- `visitorId`
- `userInfo`
- `pageSize`
- `pageToken`
- `offset`
- `filter`
- `orderBy`
- `facetSpecs`
- `boostSpec`
- `queryExpansionSpec`
- `spellCorrectionSpec`
- `canonicalFilter`
- `variantRollupKeys`
- `pageCategories`
- `searchMode`
- `personalizationSpec`
- `labels`

Build:

- request parser
- filter grammar
- facet spec parser
- boost spec parser
- pagination tokens
- variant rollup
- personalization context resolver
- query expansion/spell correction hooks

### 5.2 Search response fields to support

Priority fields:

- `results[]`
- `facets[]`
- `totalSize`
- `attributionToken`
- `nextPageToken`
- `correctedQuery`
- `guidedSearchResult`
- `redirectUri`
- `appliedControls[]`
- `queryExpansionInfo`
- `diagnostics` for V2 staging/debug mode

Build:

- response hydrator
- facet response builder
- attribution token generator
- applied-control tracking
- guided/refinement response builder
- diagnostics/explanations

## 6. Predict/recommend request/response compatibility

### 6.1 Predict request fields to support

Priority fields:

- `placement`
- `userEvent`
- `pageSize`
- `pageToken`
- `filter`
- `validateOnly`
- `params`
- `labels`

Build:

- predict request parser
- embedded user-event resolver
- placement/model selector
- filter support
- pagination
- validation-only path

### 6.2 Predict response fields to support

Priority fields:

- `results[]`
- `attributionToken`
- `nextPageToken`
- `missingIds[]`
- `validateOnly`
- `appliedControls[]`
- `diagnostics`

Build:

- recommendation result hydrator
- missing ID tracker
- attribution token generator
- applied-control tracker
- model/strategy diagnostics

## 7. Materialized runtime to build

The runtime should be built from validated catalog/event snapshots and update
streams.

Required materialized views:

- `productsById`
- `variantsByPrimaryId`
- `primaryByVariantId`
- `effectiveProductByVariantId`
- `collectionsById`
- `collectionMembersById`
- `gtinIndex`
- `localInventoriesByProductId`
- `localInventoryByPlaceId`
- `categoryTree`
- `brandIndex`
- `textInvertedIndex`
- `facetIndex`
- `numericRangeIndex`
- `availabilityIndex`
- `suggestPrefixIndex`
- `productVectors`
- `vectorBuckets`
- `eventStats`
- `queryStats`
- `skuStats`
- `rulePlan`
- `servingConfigPlan`
- `questionFlowPlan`
- `personalizationFeatures`
- `recommendationCandidateViews`
- `coldStartFeatures`
- `pipelineAudit`

Build:

- immutable `CatalogRuntime`
- background runtime builder
- atomic runtime swap
- previous-runtime rollback
- runtime checksum/version metadata

## 8. Model and ranking work to build

### 8.1 Query understanding

Build:

- query normalization
- synonym detection
- intent/entity extraction
- category/attribute inference
- semantic embeddings or signatures
- low-confidence detection
- clarification trigger detection

### 8.2 Search ranking

Build:

- lexical BM25/BM25F scorer
- semantic scorer/reranker
- personalization scorer
- business objective scorer
- rule/merchandising scorer
- availability scorer
- final rank combiner

### 8.3 Recommendation models

Build model strategies for:

- recommended for you
- others you might like
- frequently bought together
- recently viewed
- page-level optimization
- buy it again
- on sale
- bestsellers
- new arrivals
- trending products
- top-rated products
- cross-sell
- upsell
- cold-start recommendations
- no-results alternatives

### 8.4 Real-time overlays

Build real-time feature overlays for:

- current query
- current page/category
- current product
- recent views
- recent carts
- recent orders
- cart contents
- inventory changes
- price changes
- active offers/promotions

## 9. ETL and pipeline work to build

Build pipelines for:

- catalog bulk import
- catalog real-time updates
- inventory real-time updates
- user event bulk import
- user event real-time ingestion
- completion data import
- model feature refresh
- daily recommendation materialization

Each pipeline must support:

- schema validation
- idempotent writes
- checkpointing
- replay
- dead-letter records
- freshness/lag metrics
- load testing
- audit trail

## 10. Safety, privacy and operations work to build

Build:

- tenant/catalog isolation
- API authentication and authorization
- audit log for catalog/rule/config changes
- PII minimization for events
- GDPR delete/export workflow
- event retention policy
- bad feed rollback
- bad rule rollback
- model rollback
- operation tracking
- health/status endpoints
- SLO dashboards

## 11. Implementation phases

### Phase 1: Core compatibility and baseline runtime

Build:

- V2 product schema validation
- product import/get/list/create/patch
- inventory set/add/remove
- user event write/collect/import
- in-memory runtime builder
- search API
- predict API
- serving config search/predict
- controls CRUD
- operations get/list

### Phase 2: Quality, personalization and recommendations

Build:

- event materialization
- personalization features
- recommendation candidate views
- predictive autocomplete
- semantic query understanding
- dynamic facets
- no-results alternatives
- cross-sell/upsell placements
- rule compiler and applied-control diagnostics

### Phase 3: Migration and merchandising completeness

Build:

- attributes config APIs
- completion data import/purge
- models create/list/get/pause/resume/tune
- user event purge/rejoin
- product purge
- catalog setDefaultBranch
- merchandising preview/test/publish
- A/B and offline replay evaluation

### Phase 4: Production hardening

Build:

- robust ETL pipelines
- durable operation store
- access control
- audit/rollback
- privacy workflows
- load/stress testing
- monitoring/SLO dashboards
- multi-catalog/tenant support

## 12. Acceptance criteria

The system is ready when:

- catalog, inventory and user events ingest through bulk and real-time paths
- search and recommendations use the same ingested data
- commerce-compatible product, event, serving config, placement and control APIs
  are available
- search returns ordered, faceted, personalized and merchandised results
- recommendations support all configured model types and placements
- autocomplete returns objective-aware suggestions and product previews
- no-results and low-confidence queries return alternatives or questions
- cold-start products and users receive useful results
- merchandising teams can configure controls and fallback logic
- model/ranking behavior is tied to KPIs and guardrails
- staging E2E validates query-to-result, recommendation and event feedback loops
- pipelines are robust under load and expose freshness/failure metrics
- safety, privacy, audit and rollback controls are implemented
