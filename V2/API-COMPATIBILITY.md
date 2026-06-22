# External Commerce API Compatibility Map

## Purpose

This document maps the external commerce API REST surface to
V2-compatible API concepts.

The goal is not to proxy a managed cloud provider. The goal is to make our own retail search
engine migration-friendly by using compatible resource names, request concepts,
operation names and response shapes where practical.

## Compatibility principles

V2 should:

- keep commerce-style resource names as an optional compatibility layer
- expose first-party, provider-neutral APIs underneath
- ingest catalog, inventory and user events once for both search and
  recommendations
- support bulk and real-time ingestion paths
- support long-running operation responses for imports, purges and rebuilds
- preserve field-mask semantics for patch/update APIs
- preserve placement/serving-config concepts for search and recommendations
- support controls/rules as data attached to serving configs

V2 does not need to implement every provider-specific authentication, IAM,
regional or long-running-operation detail in the first implementation.

## Resource name convention

Compatibility resource names should follow the commerce-style shape:

```text
projects/{project}/locations/{location}/catalogs/{catalog}
projects/{project}/locations/{location}/catalogs/{catalog}/branches/{branch}
projects/{project}/locations/{location}/catalogs/{catalog}/branches/{branch}/products/{product}
projects/{project}/locations/{location}/catalogs/{catalog}/servingConfigs/{servingConfig}
projects/{project}/locations/{location}/catalogs/{catalog}/controls/{control}
projects/{project}/locations/{location}/catalogs/{catalog}/models/{model}
```

For local/single-tenant deployments, V2 can map these to:

```text
project = default_project
location = global
catalog = default_catalog
branch = default_branch
```

## Product resource

Compatible resource:

```text
projects.locations.catalogs.branches.products
```

V2 equivalent:

```text
catalog snapshot products[] + product service + inventory service
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `create` | Create one product in a staging snapshot or update journal. |
| `get` | Fetch one product by resource name or product ID. |
| `list` | Page products under a branch/catalog. |
| `patch` | Apply partial product update with field-mask semantics. |
| `delete` | Tombstone/remove one product. |
| `import` | Bulk product import for initial load/rebuild. |
| `purge` | Delete products matching a filter under a branch/catalog. |
| `setInventory` | Replace inventory fields with timestamp-aware conflict handling. |
| `addLocalInventories` | Add/update local inventory records for one product. |
| `removeLocalInventories` | Remove local inventory records for one product. |
| `addFulfillmentPlaces` | Compatibility alias; implement through local inventory updates. |
| `removeFulfillmentPlaces` | Compatibility alias; implement through local inventory updates. |

Suggested compatibility routes:

```text
POST   /v2/{parent=projects/*/locations/*/catalogs/*/branches/*}/products
GET    /v2/{name=projects/*/locations/*/catalogs/*/branches/*/products/*}
GET    /v2/{parent=projects/*/locations/*/catalogs/*/branches/*}/products
PATCH  /v2/{product.name=projects/*/locations/*/catalogs/*/branches/*/products/*}
DELETE /v2/{name=projects/*/locations/*/catalogs/*/branches/*/products/*}
POST   /v2/{parent=projects/*/locations/*/catalogs/*/branches/*}/products:import
POST   /v2/{parent=projects/*/locations/*/catalogs/*/branches/*}/products:purge
POST   /v2/{name=projects/*/locations/*/catalogs/*/branches/*/products/*}:setInventory
POST   /v2/{product=projects/*/locations/*/catalogs/*/branches/*/products/*}:addLocalInventories
POST   /v2/{product=projects/*/locations/*/catalogs/*/branches/*/products/*}:removeLocalInventories
```

Implementation notes:

- `import`, `purge` and large inventory operations should return an operation.
- `patch` should accept an update mask.
- imports should support full snapshot build plus atomic runtime swap.
- inventory writes should be idempotent and timestamp-aware.

## User events resource

Compatible resource:

```text
projects.locations.catalogs.userEvents
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `collect` | Browser/mobile/client-side event collection endpoint. |
| `write` | Server-side single event write. |
| `import` | Bulk user event import/backfill. |
| `purge` | Delete events matching filter for compliance/rebuild. |
| `rejoin` | Rejoin historical events with current catalog data. |

Suggested compatibility routes:

```text
POST /v2/{parent=projects/*/locations/*/catalogs/*}/userEvents:collect
POST /v2/{parent=projects/*/locations/*/catalogs/*}/userEvents:write
POST /v2/{parent=projects/*/locations/*/catalogs/*}/userEvents:import
POST /v2/{parent=projects/*/locations/*/catalogs/*}/userEvents:purge
POST /v2/{parent=projects/*/locations/*/catalogs/*}/userEvents:rejoin
```

Implementation notes:

- `collect` should be safe for browser/mobile use and support CORS.
- `write` should be the server-to-server path.
- `import` and `purge` should return operations.
- `rejoin` should rebuild event-to-product joins when catalog identifiers,
  variants or product metadata change.
- event ingestion must be idempotent or deduplicate by event ID where present.

## Placements resource

Compatible resource:

```text
projects.locations.catalogs.placements
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `search` | Search a placement. |
| `predict` | Return recommendations for a placement. |

Suggested compatibility routes:

```text
POST /v2/{placement=projects/*/locations/*/catalogs/*/placements/*}:search
POST /v2/{placement=projects/*/locations/*/catalogs/*/placements/*}:predict
```

V2 should treat placements as compatibility aliases for serving configs. New
implementations should prefer `servingConfigs.search` and
`servingConfigs.predict`.

## Serving configs resource

Compatible resource:

```text
projects.locations.catalogs.servingConfigs
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `create` | Create a serving config. |
| `list` | List serving configs under a catalog. |
| `get` | Get one serving config. |
| `patch` | Update serving config with field-mask semantics. |
| `delete` | Delete a serving config. |
| `addControl` | Attach a control/rule to the serving config. |
| `removeControl` | Detach a control/rule from the serving config. |
| `search` | Search using the serving config. |
| `predict` | Recommend/predict using the serving config. |

Suggested compatibility routes:

```text
POST   /v2/{parent=projects/*/locations/*/catalogs/*}/servingConfigs
GET    /v2/{parent=projects/*/locations/*/catalogs/*}/servingConfigs
GET    /v2/{name=projects/*/locations/*/catalogs/*/servingConfigs/*}
PATCH  /v2/{servingConfig.name=projects/*/locations/*/catalogs/*/servingConfigs/*}
DELETE /v2/{name=projects/*/locations/*/catalogs/*/servingConfigs/*}
POST   /v2/{servingConfig=projects/*/locations/*/catalogs/*/servingConfigs/*}:addControl
POST   /v2/{servingConfig=projects/*/locations/*/catalogs/*/servingConfigs/*}:removeControl
POST   /v2/{placement=projects/*/locations/*/catalogs/*/servingConfigs/*}:search
POST   /v2/{placement=projects/*/locations/*/catalogs/*/servingConfigs/*}:predict
```

V2 serving configs map directly to `servingConfigs[]` in the snapshot.

## Controls resource

Compatible resource:

```text
projects.locations.catalogs.controls
```

V2 equivalent:

```text
rules[] + controls compatibility resource
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `create` | Create a control/rule. |
| `list` | List controls under a catalog. |
| `get` | Get one control. |
| `patch` | Update a control/rule. |
| `delete` | Delete a control/rule. |

Suggested compatibility routes:

```text
POST   /v2/{parent=projects/*/locations/*/catalogs/*}/controls
GET    /v2/{parent=projects/*/locations/*/catalogs/*}/controls
GET    /v2/{name=projects/*/locations/*/catalogs/*/controls/*}
PATCH  /v2/{control.name=projects/*/locations/*/catalogs/*/controls/*}
DELETE /v2/{name=projects/*/locations/*/catalogs/*/controls/*}
```

V2 control types should cover:

- boost
- bury/demote
- pin
- filter
- facet control
- redirect/reroute
- synonym expansion
- replacement/rewrite
- do-not-associate/no-op controls where useful for compatibility

## Attributes config resource

Compatible resource:

```text
projects.locations.catalogs.attributesConfig
```

V2 equivalent:

```text
central attribute configuration + schema/enrichment metadata
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `addCatalogAttribute` | Add a searchable/facetable/filterable/boostable attribute definition. |
| `removeCatalogAttribute` | Remove an attribute definition. |
| `replaceCatalogAttribute` | Replace an attribute definition. |
| `updateCatalogAttribute` | Update an attribute definition. |

Suggested compatibility routes:

```text
POST /v2/{attributesConfig=projects/*/locations/*/catalogs/*/attributesConfig}:addCatalogAttribute
POST /v2/{attributesConfig=projects/*/locations/*/catalogs/*/attributesConfig}:removeCatalogAttribute
POST /v2/{attributesConfig=projects/*/locations/*/catalogs/*/attributesConfig}:replaceCatalogAttribute
POST /v2/{attributesConfig=projects/*/locations/*/catalogs/*/attributesConfig}:updateCatalogAttribute
```

Initial V2 can derive this from product-level `attributes.*.searchable` and
`attributes.*.indexable`, but production should prefer a central config.

## Completion data resource

Compatible resource:

```text
projects.locations.catalogs.completionData
```

V2 equivalent:

```text
suggestion/autocomplete data + suggestPrefixIndex
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `import` | Bulk import completion data/suggestions. |
| `purge` | Delete completion data matching a filter or source. |

Suggested compatibility routes:

```text
POST /v2/{parent=projects/*/locations/*/catalogs/*}/completionData:import
POST /v2/{parent=projects/*/locations/*/catalogs/*}/completionData:purge
```

Completion data should feed predictive autocomplete alongside generated
suggestions from catalog, events and synonyms.

## Models resource

Compatible resource:

```text
projects.locations.catalogs.models
```

V2 equivalent:

```text
recommendation/search model registry + offline training jobs
```

Methods to mirror:

| Compatible method | V2 requirement |
| --- | --- |
| `create` | Register/create a model config. |
| `list` | List model configs. |
| `get` | Get one model config. |
| `delete` | Delete one model config. |
| `pause` | Pause scheduled training/materialization. |
| `resume` | Resume scheduled training/materialization. |
| `tune` | Start tuning/retraining for a model. |

Suggested compatibility routes:

```text
POST   /v2/{parent=projects/*/locations/*/catalogs/*}/models
GET    /v2/{parent=projects/*/locations/*/catalogs/*}/models
GET    /v2/{name=projects/*/locations/*/catalogs/*/models/*}
DELETE /v2/{name=projects/*/locations/*/catalogs/*/models/*}
POST   /v2/{name=projects/*/locations/*/catalogs/*/models/*}:pause
POST   /v2/{name=projects/*/locations/*/catalogs/*/models/*}:resume
POST   /v2/{name=projects/*/locations/*/catalogs/*/models/*}:tune
```

Model types should include search relevance, semantic query understanding,
autocomplete, recommended-for-you, frequently-bought-together, cross-sell,
upsell, cold-start and trending/bestseller feeds.

## Catalog resource

Compatible resource:

```text
projects.locations.catalogs
```

V2 equivalent:

```text
tenant/catalog metadata + branch/snapshot selection
```

Compatibility operations should include:

| Operation | V2 requirement |
| --- | --- |
| `get` | Get catalog metadata/config. |
| `list` | List catalogs where multi-catalog tenancy is enabled. |
| `patch` | Patch catalog metadata/config. |
| `setDefaultBranch` | Switch active branch/snapshot for serving. |

Suggested compatibility routes:

```text
GET   /v2/{name=projects/*/locations/*/catalogs/*}
GET   /v2/{parent=projects/*/locations/*}/catalogs
PATCH /v2/{catalog.name=projects/*/locations/*/catalogs/*}
POST  /v2/{catalog=projects/*/locations/*/catalogs/*}:setDefaultBranch
```

`setDefaultBranch` should map to V2 atomic runtime swap.

## Operations resource

Long-running operations are needed for:

- product import
- product purge
- user event import
- user event purge
- completion data import
- completion data purge
- model tuning
- full runtime rebuild

Suggested shape:

```json
{
  "name": "projects/default/locations/global/operations/op-123",
  "done": false,
  "metadata": {},
  "response": null,
  "error": null
}
```

Minimum operations API:

```text
GET    /v2/{name=projects/*/locations/*/operations/*}
GET    /v2/{name=projects/*/locations/*}/operations
DELETE /v2/{name=projects/*/locations/*/operations/*}
POST   /v2/{name=projects/*/locations/*/operations/*}:cancel
```

## Search request compatibility

V2 search requests should support commerce-compatible concepts:

- `placement` or serving config resource name
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

V2 can implement these progressively. The first implementation should prioritize
`query`, `visitorId`, `pageSize`, `pageToken`, `filter`, `facetSpecs`,
`boostSpec`, `pageCategories`, `personalizationSpec` and `labels`.

## Predict request compatibility

V2 predict/recommend requests should support commerce-compatible concepts:

- `placement` or serving config resource name
- `userEvent`
- `pageSize`
- `pageToken`
- `filter`
- `validateOnly`
- `params`
- `labels`

The `userEvent` payload is important: it carries the active product, cart,
visitor/session and context that recommendation models use for real-time
predictions.

## Response compatibility

V2 responses should preserve these concepts:

Search response:

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
- `diagnostics` for V2 staging/debug use

Predict response:

- `results[]`
- `attributionToken`
- `nextPageToken`
- `missingIds[]`
- `validateOnly`
- `appliedControls[]`
- `diagnostics` for V2 staging/debug use

Product result entries should include product identity, hydrated product data,
variant/default-variant information and ranking/explanation metadata in staging.

## Implementation priority

Phase 1 compatibility:

1. Product get/list/create/patch/import.
2. Product setInventory/addLocalInventories/removeLocalInventories.
3. UserEvents write/collect/import.
4. ServingConfigs search/predict.
5. Controls create/list/get/patch/delete.
6. Operations get/list for imports/rebuilds.

Phase 2 compatibility:

1. Product purge/delete.
2. UserEvents purge/rejoin.
3. CompletionData import/purge.
4. AttributesConfig methods.
5. Models create/list/get/pause/resume/tune.
6. Catalog setDefaultBranch.

Phase 3 compatibility:

1. Full commerce-compatible search request coverage.
2. Full commerce-compatible predict request coverage.
3. Long-running operation cancel/delete.
4. Placement compatibility aliases.
5. Export adapters for external commerce API/warehouse-shaped schemas.
