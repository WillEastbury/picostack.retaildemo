# Retail Search V2 Modular Python API Host Design

## 1. Purpose

This document maps each external commerce API area and each V2
commerce feature into composable Python modules that plug into a provider-neutral
API host.

The target implementation is a Python API host, preferably FastAPI-compatible,
with explicit module boundaries so storage, models, ranking, vector search,
event processing and merchandising can be replaced independently.

## 2. Design goals

The Python host must:

- expose commerce-compatible REST routes where practical
- expose simpler native V2 routes where useful
- load modules through explicit dependency injection
- keep API routing separate from business logic
- keep materialized runtime state immutable per snapshot/version
- support atomic runtime swaps
- support bulk and real-time ingestion
- support pluggable model providers
- support pluggable storage/index backends
- support staging diagnostics without leaking them into production responses

## 3. API host shape

Recommended package layout:

```text
retail_v2/
  api_host.py
  config.py
  dependencies.py
  modules/
    catalog/
    products/
    inventory/
    events/
    search/
    recommendations/
    autocomplete/
    serving_configs/
    controls/
    attributes/
    models/
    operations/
    enrichment/
    personalization/
    safety/
    runtime/
  adapters/
    vertex_rest/
    native_v2/
  schemas/
    catalog.py
    product.py
    event.py
    search.py
    predict.py
    controls.py
    operations.py
```

Host bootstrap:

```python
def create_app(config: RetailConfig) -> FastAPI:
    container = build_container(config)
    app = FastAPI(title="Retail Search V2")

    register_vertex_routes(app, container)
    register_native_routes(app, container)
    register_health_routes(app, container)

    return app
```

## 4. Module contract

Every module should have:

- Pydantic request/response schemas
- a service class containing business logic
- a router registration function
- explicit dependencies
- tests independent of the API host

Pattern:

```python
class ModuleProtocol(Protocol):
    name: str

    def register_routes(self, app: FastAPI, deps: AppDependencies) -> None:
        ...

    def health(self) -> ModuleHealth:
        ...
```

## 5. Shared runtime module

### Commerce API areas covered

- catalog serving state
- branch/default branch
- search runtime
- recommendation runtime

### Responsibilities

The runtime module owns immutable materialized serving state.

```python
@dataclass(frozen=True)
class CatalogRuntime:
    version: str
    products_by_id: Mapping[str, Product]
    variants_by_primary_id: Mapping[str, tuple[str, ...]]
    text_index: TextIndex
    facet_index: FacetIndex
    vector_index: VectorIndex
    rule_plan: RulePlan
    serving_config_plan: ServingConfigPlan
    recommendation_views: RecommendationViews
    personalization_features: PersonalizationViews
```

Build:

- `RuntimeBuilder`
- `RuntimeRegistry`
- `RuntimeSwapService`
- `RuntimeRollbackService`

Interface:

```python
class RuntimeRegistry:
    def current(self, catalog: CatalogRef, branch: str | None = None) -> CatalogRuntime: ...
    def stage(self, runtime: CatalogRuntime) -> OperationRef: ...
    def promote(self, catalog: CatalogRef, branch: str, version: str) -> None: ...
    def rollback(self, catalog: CatalogRef, branch: str) -> None: ...
```

## 6. Catalog module

### Commerce API area mapped

```text
projects.locations.catalogs
```

### API mapping

| Compatible API | Python module method |
| --- | --- |
| `catalogs.get` | `CatalogService.get_catalog()` |
| `catalogs.list` | `CatalogService.list_catalogs()` |
| `catalogs.patch` | `CatalogService.patch_catalog()` |
| `catalogs.setDefaultBranch` | `CatalogService.set_default_branch()` |

### Responsibilities

- catalog metadata
- catalog settings
- branch/snapshot selection
- tenant/catalog isolation boundary
- default branch atomic switch

Build:

```python
class CatalogService:
    def get_catalog(self, name: str) -> Catalog: ...
    def list_catalogs(self, parent: str) -> Page[Catalog]: ...
    def patch_catalog(self, catalog: Catalog, update_mask: FieldMask) -> Catalog: ...
    def set_default_branch(self, catalog: str, branch_id: str) -> Operation: ...
```

## 7. Product module

### Commerce API area mapped

```text
projects.locations.catalogs.branches.products
```

### API mapping

| Compatible API | Python module method |
| --- | --- |
| `products.create` | `ProductService.create_product()` |
| `products.get` | `ProductService.get_product()` |
| `products.list` | `ProductService.list_products()` |
| `products.patch` | `ProductService.patch_product()` |
| `products.delete` | `ProductService.delete_product()` |
| `products.import` | `ProductImportService.import_products()` |
| `products.purge` | `ProductImportService.purge_products()` |

### Responsibilities

- commerce-compatible product schema
- primary/variant/collection validation
- product create/update/delete
- bulk import
- purge/tombstone
- product hydration for search/recommendation responses

Build:

```python
class ProductService:
    def create_product(self, parent: str, product: Product) -> Product: ...
    def get_product(self, name: str) -> Product: ...
    def list_products(self, parent: str, page_size: int, page_token: str | None) -> Page[Product]: ...
    def patch_product(self, product: Product, update_mask: FieldMask) -> Product: ...
    def delete_product(self, name: str) -> None: ...

class ProductImportService:
    def import_products(self, parent: str, source: ImportSource) -> Operation: ...
    def purge_products(self, parent: str, filter: str, force: bool) -> Operation: ...
```

## 8. Inventory module

### Commerce API area mapped

```text
products.setInventory
products.addLocalInventories
products.removeLocalInventories
```

### API mapping

| Compatible API | Python module method |
| --- | --- |
| `setInventory` | `InventoryService.set_inventory()` |
| `addLocalInventories` | `InventoryService.add_local_inventories()` |
| `removeLocalInventories` | `InventoryService.remove_local_inventories()` |
| `addFulfillmentPlaces` | compatibility alias to local inventory |
| `removeFulfillmentPlaces` | compatibility alias to local inventory |

### Responsibilities

- real-time inventory updates
- local inventory records
- timestamp-aware conflict handling
- fulfillment indexes
- availability features for search/recommendations

Build:

```python
class InventoryService:
    def set_inventory(self, name: str, inventory: InventoryUpdate) -> Operation: ...
    def add_local_inventories(self, product: str, inventories: list[LocalInventory]) -> Operation: ...
    def remove_local_inventories(self, product: str, place_ids: list[str]) -> Operation: ...
```

## 9. User events module

### Commerce API area mapped

```text
projects.locations.catalogs.userEvents
```

### API mapping

| Compatible API | Python module method |
| --- | --- |
| `userEvents.collect` | `UserEventService.collect_event()` |
| `userEvents.write` | `UserEventService.write_event()` |
| `userEvents.import` | `UserEventImportService.import_events()` |
| `userEvents.purge` | `UserEventImportService.purge_events()` |
| `userEvents.rejoin` | `UserEventImportService.rejoin_events()` |

### Responsibilities

- browser/mobile event collection
- server-side event writes
- bulk event import
- event purge for compliance/rebuild
- event rejoin after catalog changes
- event dedupe
- real-time session feature updates

Build:

```python
class UserEventService:
    def collect_event(self, parent: str, event: UserEvent) -> UserEventAck: ...
    def write_event(self, parent: str, event: UserEvent) -> UserEvent: ...

class UserEventImportService:
    def import_events(self, parent: str, source: ImportSource) -> Operation: ...
    def purge_events(self, parent: str, filter: str, force: bool) -> Operation: ...
    def rejoin_events(self, parent: str, mode: str) -> Operation: ...
```

## 10. Search module

### Commerce API areas mapped

```text
placements.search
servingConfigs.search
```

### API mapping

| Compatible API | Python module method |
| --- | --- |
| `placements.search` | `SearchService.search_by_placement()` |
| `servingConfigs.search` | `SearchService.search_by_serving_config()` |

### Responsibilities

- search request parsing
- query understanding
- lexical candidate retrieval
- semantic/vector candidate retrieval
- filtering
- dynamic facets
- boost/bury/pin/filter controls
- personalization
- variant rollup
- result hydration
- attribution token generation

Build:

```python
class SearchService:
    def search(self, request: SearchRequest) -> SearchResponse:
        interpretation = self.query_understanding.interpret(request)
        candidates = self.retriever.retrieve(interpretation, request)
        ranked = self.ranker.rank(candidates, request, interpretation)
        return self.response_builder.build(ranked, request, interpretation)
```

Submodules:

- `QueryUnderstandingService`
- `CandidateRetriever`
- `FilterEngine`
- `FacetEngine`
- `SearchRanker`
- `SearchResponseBuilder`

## 11. Recommendations module

### Commerce API areas mapped

```text
placements.predict
servingConfigs.predict
models
```

### API mapping

| Compatible API | Python module method |
| --- | --- |
| `placements.predict` | `RecommendationService.predict_by_placement()` |
| `servingConfigs.predict` | `RecommendationService.predict_by_serving_config()` |

### Responsibilities

- recommendation request parsing
- model/strategy selection
- real-time session overlay
- candidate generation
- cross-sell/upsell
- no-results alternatives
- ranking by objective
- product hydration
- attribution token generation

Build:

```python
class RecommendationService:
    def predict(self, request: PredictRequest) -> PredictResponse:
        strategy = self.strategy_selector.select(request)
        candidates = strategy.generate(request)
        ranked = self.ranker.rank(candidates, request)
        return self.response_builder.build(ranked, request)
```

Strategy modules:

- `RecommendedForYouStrategy`
- `FrequentlyBoughtTogetherStrategy`
- `OthersYouMightLikeStrategy`
- `RecentlyViewedStrategy`
- `BuyItAgainStrategy`
- `OnSaleStrategy`
- `BestSellersStrategy`
- `NewArrivalsStrategy`
- `TrendingProductsStrategy`
- `TopRatedProductsStrategy`
- `CrossSellStrategy`
- `UpsellStrategy`
- `ColdStartStrategy`
- `NoResultsAlternativesStrategy`

## 12. Autocomplete module

### Commerce API area mapped

```text
projects.locations.catalogs.completionData
```

### API mapping

| Compatible API | Python module method |
| --- | --- |
| `completionData.import` | `CompletionDataService.import_completion_data()` |
| `completionData.purge` | `CompletionDataService.purge_completion_data()` |
| native suggest endpoint | `AutocompleteService.complete()` |

### Responsibilities

- prefix index
- search suggestions
- brand suggestions
- category suggestions
- product previews
- objective-aware suggestion ranking
- personalization-aware suggestions

Build:

```python
class AutocompleteService:
    def complete(self, request: CompleteRequest) -> CompleteResponse: ...

class CompletionDataService:
    def import_completion_data(self, parent: str, source: ImportSource) -> Operation: ...
    def purge_completion_data(self, parent: str, filter: str) -> Operation: ...
```

## 13. Serving config module

### Commerce API area mapped

```text
projects.locations.catalogs.servingConfigs
```

### Responsibilities

- placement definitions
- objective selection
- ranking weights
- attached control IDs
- question flow association
- KPI and guardrail settings

Build:

```python
class ServingConfigService:
    def create(self, parent: str, config: ServingConfig) -> ServingConfig: ...
    def list(self, parent: str) -> Page[ServingConfig]: ...
    def get(self, name: str) -> ServingConfig: ...
    def patch(self, config: ServingConfig, update_mask: FieldMask) -> ServingConfig: ...
    def delete(self, name: str) -> None: ...
    def add_control(self, name: str, control_id: str) -> ServingConfig: ...
    def remove_control(self, name: str, control_id: str) -> ServingConfig: ...
```

## 14. Controls and merchandising module

### Commerce API area mapped

```text
projects.locations.catalogs.controls
```

### Responsibilities

- boost
- bury/demote
- pin
- filter
- facet controls
- redirects/reroutes
- synonyms/replacements
- fallback logic
- merchandising preview/test/publish
- audit and rollback

Build:

```python
class ControlService:
    def create(self, parent: str, control: Control) -> Control: ...
    def list(self, parent: str) -> Page[Control]: ...
    def get(self, name: str) -> Control: ...
    def patch(self, control: Control, update_mask: FieldMask) -> Control: ...
    def delete(self, name: str) -> None: ...

class RuleCompiler:
    def compile(self, controls: Iterable[Control]) -> RulePlan: ...
```

## 15. Attributes configuration module

### Commerce API area mapped

```text
projects.locations.catalogs.attributesConfig
```

### Responsibilities

- searchable attributes
- indexable/filterable attributes
- facetable attributes
- boostable attributes
- attribute validation
- migration from product-level flags

Build:

```python
class AttributesConfigService:
    def add_catalog_attribute(self, name: str, attribute: CatalogAttribute) -> AttributesConfig: ...
    def remove_catalog_attribute(self, name: str, key: str) -> AttributesConfig: ...
    def replace_catalog_attribute(self, name: str, attribute: CatalogAttribute) -> AttributesConfig: ...
    def update_catalog_attribute(self, name: str, attribute: CatalogAttribute, update_mask: FieldMask) -> AttributesConfig: ...
```

## 16. Models module

### Commerce API area mapped

```text
projects.locations.catalogs.models
```

### Responsibilities

- model registry
- recommendation model configs
- search relevance model configs
- query understanding model configs
- daily training/materialization schedule
- pause/resume/tune lifecycle
- model metrics

Build:

```python
class ModelService:
    def create(self, parent: str, model: ModelConfig) -> ModelConfig: ...
    def list(self, parent: str) -> Page[ModelConfig]: ...
    def get(self, name: str) -> ModelConfig: ...
    def delete(self, name: str) -> None: ...
    def pause(self, name: str) -> ModelConfig: ...
    def resume(self, name: str) -> ModelConfig: ...
    def tune(self, name: str, request: TuneRequest) -> Operation: ...
```

Provider interface:

```python
class ModelProvider(Protocol):
    def embed_products(self, products: Sequence[Product]) -> Mapping[str, Vector]: ...
    def embed_query(self, query: str) -> Vector: ...
    def rerank(self, query: str, products: Sequence[Product]) -> Sequence[RankedProduct]: ...
```

## 17. Personalization module

### Commerce features mapped

- personalized search
- recommended for you
- real-time predictions
- personas
- cold-start fallback

### Responsibilities

- visitor/session profile
- brand affinity
- category affinity
- color affinity
- size affinity
- price-band affinity
- fulfillment preference
- real-time session overlay
- GDPR delete/export support for profile features

Build:

```python
class PersonalizationService:
    def get_features(self, context: UserContext) -> PersonaFeatures: ...
    def update_session(self, event: UserEvent) -> None: ...
    def delete_user_features(self, user_ref: str) -> Operation: ...
    def export_user_features(self, user_ref: str) -> PersonaExport: ...
```

## 18. Enrichment module

### Commerce feature areas mapped

- catalog improvements
- cold-start product handling
- semantic search quality
- catalog quality diagnostics

### Responsibilities

- taxonomy normalization
- inferred attributes
- image-derived tags
- title cleanup
- duplicate detection
- quality score
- missing-field diagnostics

Build:

```python
class EnrichmentService:
    def enrich_product(self, product: Product) -> EnrichedProduct: ...
    def enrich_catalog(self, snapshot: CatalogSnapshot) -> Operation: ...
```

## 19. Operations module

### Commerce API area mapped

```text
operations
```

### Responsibilities

- long-running operation records
- progress metadata
- errors
- cancellation
- operation result references

Build:

```python
class OperationService:
    def create(self, kind: str, metadata: dict) -> Operation: ...
    def get(self, name: str) -> Operation: ...
    def list(self, parent: str) -> Page[Operation]: ...
    def cancel(self, name: str) -> Operation: ...
    def delete(self, name: str) -> None: ...
    def complete(self, name: str, response: object) -> Operation: ...
    def fail(self, name: str, error: OperationError) -> Operation: ...
```

## 20. Safety and audit module

### Feature areas mapped

- privacy
- tenant isolation
- GDPR delete/export
- merchandising audit
- bad-feed rollback
- bad-rule rollback

### Responsibilities

- auth/authz hooks
- tenant/catalog permissions
- audit log
- retention policy
- PII minimization checks
- deletion/export workflows

Build:

```python
class SafetyService:
    def authorize(self, principal: Principal, action: str, resource: str) -> None: ...
    def audit(self, entry: AuditEntry) -> None: ...
    def enforce_retention(self) -> Operation: ...
```

## 21. Module dependency graph

```text
API Host
  -> CatalogService
  -> ProductService
  -> InventoryService
  -> UserEventService
  -> ServingConfigService
  -> ControlService
  -> SearchService
       -> RuntimeRegistry
       -> QueryUnderstandingService
       -> PersonalizationService
       -> RuleCompiler
  -> RecommendationService
       -> RuntimeRegistry
       -> PersonalizationService
       -> ModelService
       -> RuleCompiler
  -> AutocompleteService
       -> RuntimeRegistry
       -> PersonalizationService
  -> RuntimeBuilder
       -> EnrichmentService
       -> AttributesConfigService
       -> ModelProvider
  -> OperationService
  -> SafetyService
```

No module should directly instantiate another module. Dependencies should be
passed through the host container.

## 22. API router mapping

| Router | Prefix | Module |
| --- | --- | --- |
| compatible products | `/v2/{parent}/products` | Product module |
| compatible inventory | `/v2/{product}:setInventory` | Inventory module |
| compatible user events | `/v2/{parent}/userEvents:*` | User events module |
| compatible placements | `/v2/{placement}:search`, `/v2/{placement}:predict` | Search / Recommendations |
| compatible serving configs | `/v2/{parent}/servingConfigs` | Serving config module |
| compatible controls | `/v2/{parent}/controls` | Controls module |
| compatible attributes config | `/v2/{attributesConfig}:*CatalogAttribute` | Attributes module |
| compatible completion data | `/v2/{parent}/completionData:*` | Autocomplete module |
| compatible models | `/v2/{parent}/models` | Models module |
| compatible catalogs | `/v2/{parent}/catalogs` | Catalog module |
| Operations | `/v2/{name}/operations` | Operations module |
| Native V2 search | `/api/search` | Search module |
| Native V2 recommend | `/api/recommend` | Recommendations module |
| Native V2 autocomplete | `/api/complete` | Autocomplete module |
| Health | `/healthz`, `/readyz`, `/status` | API host/runtime |

## 23. Build order

### Phase 1: API host and data foundation

Build:

1. Python package skeleton.
2. Pydantic schemas for product, event, search, predict and operations.
3. FastAPI host and dependency container.
4. Product module.
5. Inventory module.
6. Operation module.
7. Runtime builder with simple in-memory indexes.

### Phase 2: Search and recommendations

Build:

1. Search module with lexical retrieval, facets and filters.
2. Serving config module.
3. Controls module and rule compiler.
4. Recommendation module with baseline strategies.
5. Autocomplete module.
6. User event ingestion and event stats.

### Phase 3: ML and personalization

Build:

1. Query understanding module.
2. Model provider interface.
3. Vector/semantic retrieval.
4. Personalization module.
5. Cold-start features.
6. Cross-sell/upsell and no-results strategies.

### Phase 4: Production hardening

Build:

1. Durable storage adapters.
2. Durable operation store.
3. ETL pipeline jobs.
4. Safety/audit module.
5. GDPR delete/export.
6. Load tests.
7. Observability dashboards.

## 24. Acceptance criteria

The modular Python API host is ready when:

- every commerce-compatible route maps to exactly one owning module
- native V2 routes reuse the same services as compatibility routes
- catalog, inventory and events are ingested once and reused by search and
  recommendations
- search and recommendation responses are produced from `CatalogRuntime`
- controls and serving configs are compiled into runtime plans
- event updates affect personalization/session features
- long-running imports/rebuilds return operation records
- modules can be tested without starting the full API host
- model, storage and vector providers can be replaced without changing route code
- safety/audit hooks wrap mutating APIs
