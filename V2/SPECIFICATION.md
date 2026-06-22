# Retail Search V2 Specification

## 1. Purpose

Retail Search V2 is a vendor-neutral commerce search and recommendations engine
designed to load catalog, inventory and user-event data from storage blobs,
materialize an in-memory serving runtime, append durable writes to append
blobs with tail markers, and expose search, browse, suggestion, recommendation
and product APIs.

The design deliberately mirrors the widely used commerce product models where useful, while keeping the runtime simple enough to
run entirely in memory from JSON/Parquet snapshots and open-source models.

## 2. Goals

V2 must:

- provide state-of-the-art retail search and recommendation capabilities
- serve search/recommend/autocomplete traffic for less than `$0.10` per 1,000
  requests (`$0.0001` per request)
- minimize development cost by reusing proven libraries and adapters rather than
  rebuilding commodity infrastructure
- justify any external service beyond AKS and Azure Storage with cost, latency,
  failure-mode, data-boundary and exit-path analysis
- ingest catalog, inventory and user events once and reuse them for both search
  and recommendations
- keep serving completely in memory, with blob snapshots and append blobs as
  the only durable persistence
- support one blob storage container per tenant, with all durable writes flowing
  through an indexing endpoint
- support optional dual/multi-write storage replicas where ingress writes commit
  to all required storage accounts before success, or complete asynchronously via
  a queued operation
- support maximal scale-out through extensible hash partitioning and sticky
  routing by tenant plus product, user/session or query key
- support bulk ingestion for initial load and real-time ingestion for updates
- serve product search, browse, autocomplete and recommendation placements
- support primary, variant and collection product constructs
- support dynamic facets, filtering, boost, bury and pin controls
- support personalization from visitor, session and segment signals
- support business-goal optimized ranking by placement
- support conversational clarification for broad or ambiguous queries
- support catalog enrichment and product-quality diagnostics
- support tenant isolation, privacy, audit, rollback and operational safety
- keep the product schema close enough to external commerce API shapes that migration remains
  practical

## 3. Non-goals for the first implementation

V2 does not initially require:

- a database-first architecture
- a managed vector database
- online model training inside the serving process
- full replacement of all merchandising rules on day one
- dependence on any single storage, scripting or serving runtime
- custom implementations where reliable Python libraries already exist

The V2 retail engine must be able to consume any valid catalog snapshot and run
behind a provider-neutral API host.

## 4. Top-level catalog snapshot

The canonical snapshot shape is:

```json
{
  "metadata": {},
  "products": [],
  "inventory": [],
  "events": [],
  "rules": [],
  "servingConfigs": [],
  "questionFlows": [],
  "personalization": {},
  "queryUnderstanding": {},
  "kpis": [],
  "migration": {},
  "synonyms": []
}
```

The snapshot is validated against `catalog.schema.json`.

## 5. Shared ingestion model

Search and recommendations use the same source data:

```text
cold catalog snapshots + committed append blobs + feature snapshots
  -> validation/enrichment
  -> materialized runtime
  -> search + browse + suggestions + recommendations
```

If a retailer enables both search and recommendations, the system must not
require duplicate ingestion of catalog or user-event data.

## 6. Product model

### 6.1 Product types

Supported product types:

| Type | Meaning |
| --- | --- |
| `TYPE_UNSPECIFIED` | Compatibility value. Runtime should normalize to configured default. |
| `PRIMARY` | Search/browse grid entry and parent for variants. |
| `VARIANT` | Purchasable or selectable product variation. |
| `COLLECTION` | Bundle or grouped set of products sold or presented together. |

### 6.2 Primary products

Primary products are parent/container records and normally appear in search and
browse result grids.

Rules:

- `id` is required.
- `title` is required.
- `type` is `PRIMARY`.
- `primaryProductId` is empty or equal to `id`.
- Primary products should contain only fields shared across variants.
- Primary products with variants can hold synthetic/derived availability and
  price range fields.

### 6.3 Variant products

Variant products inherit common fields from their primary product and override
variant-specific fields.

Rules:

- `id` is required.
- `type` is `VARIANT`.
- `primaryProductId` is required.
- Variant fields may override `title`, `description`, `priceInfo`,
  `availability`, `availableQuantity`, `images`, `colorInfo`, `sizes`,
  `materials`, `patterns`, `conditions` and `attributes`.
- Purchase and inventory validation should resolve to the variant product where
  applicable.

Effective variant resolution:

```text
effectiveVariant = primary shared fields + variant overrides
```

### 6.4 Collection products

Collections represent bundles or product groups.

Rules:

- `type` is `COLLECTION`.
- `collectionMemberIds` contains primary or variant product IDs.
- Non-existent member IDs may be accepted at ingestion but should produce
  quality diagnostics.

## 7. Commerce product compatibility

The V2 product schema supports the following external commerce API product fields:

- `name`
- `id`
- `type`
- `primaryProductId`
- `collectionMemberIds`
- `gtin`
- `categories`
- `title`
- `brands`
- `description`
- `languageCode`
- `attributes`
- `tags`
- `priceInfo`
- `priceInfo.priceRange`
- `rating`
- `availableTime`
- `availability`
- `availableQuantity`
- `fulfillmentInfo`
- `uri`
- `images`
- `audience`
- `colorInfo`
- `sizes`
- `materials`
- `patterns`
- `conditions`
- `promotions`
- `publishTime`
- `retrievableFields`
- `variants`
- `localInventories`
- `expireTime`
- `ttl`

Compatibility details:

- `ttl` may be a REST duration string such as `"2592000s"` or a warehouse-style
  object with `seconds` and `nanos`.
- `retrievableFields` may be a REST comma-separated field-mask string or a
  runtime-friendly array.
- `attributes` are stored as a JSON object keyed by attribute name. Import and
  export adapters should convert repeated `{ key, value }` records where needed.
- `attributes.searchable` and `attributes.indexable` are accepted for migration
  compatibility.
- `variants`, `priceInfo.priceRange` and `localInventories` may be materialized
  output fields or snapshot inputs depending on the ingestion path.

## 8. Attribute model

Attributes are represented as:

```json
{
  "attributes": {
    "waterproof": {
      "booleanValues": [true],
      "searchable": false,
      "indexable": true
    },
    "size": {
      "text": ["M"],
      "searchable": false,
      "indexable": true
    },
    "rating": {
      "numbers": [4.7],
      "searchable": false,
      "indexable": true
    }
  }
}
```

Import validation should enforce:

- stable attribute keys
- one value type per attribute where possible
- no empty text values
- bounded text and number cardinality
- explicit decision on whether an attribute is searchable, facetable or
  boostable

The production system should prefer central attribute configuration, but product
level flags are kept for migration compatibility.

## 9. Inventory model

V2 supports two inventory representations:

1. `product.localInventories[]` for external commerce API REST compatibility.
2. Top-level `inventory[]` for high-volume real-time updates.

Inventory records may include:

- `productId`
- `placeId`
- `priceInfo`
- `attributes`
- `availableQuantity`
- `availability`
- `fulfillmentTypes`
- `updateTime`

Inventory updates must be timestamp-aware, idempotent and replayable.

Availability behavior:

- primary products without variants use primary availability directly
- primary products with variants may derive effective availability from variants
- variant products hold actual purchasable availability where applicable
- out-of-stock rerouting is a merchandising and serving concern

## 10. User event model

User events are the learning signal for personalization, ranking and
recommendations.

Minimum supported event types:

- search
- browse
- product view
- click
- add-to-cart
- purchase

Events should include:

- event type
- event timestamp
- visitor/session/user pseudonymous ID
- query where applicable
- product IDs where applicable
- placement/serving config where applicable
- attribution token where applicable

Events must avoid raw PII by default.

## 11. Ingestion and ETL

Required ingestion pipelines:

| Pipeline | Mode | Purpose |
| --- | --- | --- |
| Catalog bulk import | Batch | Initial products, variants, collections, categories, brands, prices and attributes. |
| Catalog real-time updates | Streaming/API | Product, price and attribute updates. |
| Inventory real-time updates | Streaming/API | Stock, fulfillment and location updates. |
| User event bulk import | Batch | Historical training and replay data. |
| User event real-time ingestion | Streaming/API | Fresh behavior signals for personalization and ranking. |

Pipelines must:

- extract from source systems
- transform to the V2 schema
- validate required fields and enums
- normalize product IDs and variant relationships
- deduplicate retries idempotently
- preserve ordering where required
- checkpoint progress
- support replay
- dead-letter invalid records
- expose freshness, lag and failure metrics

## 12. Materialized runtime

Validated snapshots and update streams are projected into an immutable
`CatalogRuntime`.

Production serving uses a two-tier runtime:

```text
immutable base CatalogRuntime + mutable LiveOverlay = served view
```

The immutable base owns low-churn catalog/search/recommendation structures. The
live overlay owns high-churn inventory, price/offer overrides, current session
features, short-window counters, product tombstones and small catalog deltas.

Required views:

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
- `rulePlan`
- `servingConfigPlan`
- `questionFlowPlan`
- `personalizationFeatures`

Runtime update model:

```text
new snapshot/update batch -> validate -> build new CatalogRuntime -> atomic swap
real-time update -> validate -> update LiveOverlay -> compact into next runtime
```

The previous runtime should remain available for rollback.

## 13. Retrieval and ranking

Search should combine:

- lexical retrieval
- semantic/vector retrieval
- semantic query understanding
- synonym detection and expansion
- shopper intent and context extraction
- filters
- facets
- availability signals
- event-derived popularity and conversion signals
- personalization signals
- merchandising rules
- business objective weights

Baseline scoring:

```text
score =
  lexicalWeight * lexicalScore +
  semanticWeight * semanticScore +
  personalizationWeight * affinityScore +
  businessRulesWeight * ruleScore +
  availabilityWeight * availabilityScore
```

Business-oriented scoring inputs:

```text
engagement -> clicks/add-to-cart signals
revenue -> price * conversion probability
margin -> price - cost
stock clearance -> inventory age + available quantity
customer fit -> segment/category/brand/attribute affinity
```

## 14. Search capability

Search is query-led product retrieval.

Search must support:

- keyword search
- hybrid lexical + semantic ranking
- NLP query understanding
- semantic synonym detection
- shopper intent extraction
- context-aware search
- category browse
- filters
- dynamic facets
- boost, bury and pin
- personalization
- availability-aware ranking
- query understanding
- conversational refinement
- result diagnostics in staging/debug mode

Search should normally retrieve/rank primary products first and hydrate the
result card with the best/default variant where appropriate.

Semantic search must understand what the shopper means, not just what tokens
they typed. The query understanding layer should identify:

- normalized query text
- query intent
- product category intent
- brand/entity mentions
- requested attributes
- implicit context
- synonyms and equivalent phrases
- broad-query or low-confidence cases that need refinement

Example:

```text
"rain coat for mountain walking"
  -> normalizedQuery: "waterproof hiking jacket"
  -> intent: product_search
  -> category: Outdoor > Clothing > Jackets
  -> attributes: waterproof=true, activity=hiking
  -> synonyms: rainproof, weatherproof
```

The semantic model may use open-source embeddings, rerankers, LLM-based query
parsing or a vendor-managed model. The serving contract remains the same:

```text
query -> intent/context interpretation -> candidates -> rerank -> explainable result set
```

## 15. Recommendations capability

Recommendations are product-led, user-led or placement-led retrieval.

Recommendation placements:

- home page personalized rows
- search result modules
- browse/category modules
- product detail similar items
- frequently bought together
- cart complements
- recently viewed continuation
- no-results alternatives
- checkout cross-sell
- checkout upsell
- email campaign recommendations
- mobile app recommendations
- kiosk/call-center recommendations

Initial algorithms may use:

- content similarity
- category/brand/attribute similarity
- co-occurrence from add-to-cart and purchase events
- popular products by segment/category
- business objective weighting

Later model implementations can replace materialization without changing the
serving API.

### 15.1 Curated recommendation models

Recommendation models should be objective-specific rather than one generic list.

Required model objectives:

| Objective | Optimizes for |
| --- | --- |
| `ctr` | Click-through rate and engagement. |
| `conversion` | Conversion rate / purchase probability. |
| `revenue_per_order` | Basket value and revenue per order. |
| `margin` | Gross profit where cost data is available. |
| `cross_sell` | Complementary products and attach rate. |
| `upsell` | Higher-value alternatives, upgrades and add-ons. |
| `cold_start` | New users/products using content and enrichment signals. |

Models should be retrainable offline on a scheduled cadence. The target cadence
is daily retraining from site behavior, with the option to run faster incremental
feature refreshes for session/context signals.

Required recommendation model types:

| Model type | Description |
| --- | --- |
| `others_you_might_like` | Similar or adjacent products based on current product/session context. |
| `frequently_bought_together` | Co-purchase and cart-complement recommendations. |
| `recommended_for_you` | Personalized recommendations from visitor/session/persona features. |
| `recently_viewed` | Continuation of recent product-view history. |
| `page_level_optimization` | Placement-level selection/ranking optimized for the current page context. |
| `buy_it_again` | Replenishment or repeat-purchase recommendations. |
| `on_sale` | Personalized or contextual sale/promotion recommendations. |
| `bestsellers` | Popular products by category, query, segment or global window. |
| `new_arrivals` | Fresh products weighted by publish/available time. |
| `trending_products` | Products with recent velocity in views, clicks, carts or purchases. |
| `top_rated_products` | Products ranked by rating and rating confidence. |

Merchandising teams must be able to refine recommendation outputs with rules and
serving configs:

```text
model candidates -> business rules -> objective ranking -> final placement
```

### 15.2 Touchpoint coverage

Recommendations must work across the full user journey:

| Touchpoint | Example recommendation behavior |
| --- | --- |
| Home page | Personalized rows, trending categories, recently viewed continuation. |
| Search | Related searches, cross-sell modules, alternatives when result confidence is low. |
| Browse/category | Category-aware popular products and personalized category picks. |
| Product detail page | Similar items, frequently bought together, compatible accessories. |
| Add to cart | Cart complements and bundles. |
| Checkout | Last-mile cross-sell and upsell with low-friction add-ons. |
| No-results page | Alternative products, spelling/synonym suggestions, adjacent categories. |
| Email/mobile | Personalized product rows using the same serving configs. |
| Contact center/kiosk | Assisted-shopping recommendations based on conversation/session context. |

The implementation must be channel-neutral: web, mobile, email, kiosk and
contact-center channels call the same recommendation service with different
placements and context.

### 15.3 Cross-sell and upsell

Cross-sell recommends complementary products that increase basket size.

Upsell recommends higher-value alternatives, upgrades or add-ons.

Signals:

- product compatibility
- basket contents
- co-purchase events
- product category hierarchy
- price ladder
- margin
- availability
- shopper persona
- current journey stage

Serving must keep hard constraints intact:

- do not recommend unavailable products unless backorder/preorder is allowed
- respect safety/compliance exclusions
- avoid irrelevant high-price upsells that harm conversion
- preserve diversity where configured

### 15.4 Frictionless fallback experience

No-results and low-confidence searches must not dead-end.

Fallback response options:

- spelling correction
- synonym expansion
- broader category alternatives
- nearby category recommendations
- popular products in adjacent categories
- personalized alternatives from current session/persona
- cold-start recommendations from content and enrichment features
- clarification question flow

No-results pages should call the recommendation service with placement
`no-results-alternatives` and include the failed query/context.

### 15.5 Search-based recommendations

Search-based recommendations improve findability even before or after a query
returns exact matches.

Supported search-based recommendation feeds:

- bestsellers
- new arrivals
- trending products
- top-rated products
- popular in this category
- popular for this query
- alternatives for this query
- related brands/categories

These feeds should be generated from the same catalog, event and serving-config
runtime as search.

### 15.6 Real-time predictions

Retrieved recommendations must adapt to real-time context.

Real-time inputs:

- current query
- current category/page
- current product
- cart contents
- recent product views
- recent add-to-cart events
- recent orders where available
- inventory/availability changes
- pricing changes
- special offers/promotions
- assortment changes

The recommendation service should combine:

```text
offline model/materialized candidates
  + real-time session features
  + real-time inventory/pricing/offers
  + merchandising rules
  -> final recommendations
```

Search and browsing behavior should update session features immediately so the
next request can adapt without waiting for daily retraining.

## 16. Cold-start handling

V2 must produce useful results for:

- new products with no events
- new users with no history
- new sessions with limited behavior
- assortment changes
- pricing changes
- inventory changes
- newly enriched catalog attributes

Cold-start strategy:

| Cold-start case | Fallback signals |
| --- | --- |
| New product | Catalog text, category, brand, attributes, image tags, price, margin, availability, enriched taxonomy. |
| New variant | Primary product inheritance, variant attributes, inventory, price, size/color/material. |
| New user | Current query/session context, geolocation/fulfillment context where allowed, global popularity, category trends. |
| New session | First-party session events, query intent, anonymous segment, popularity/conversion priors. |
| Assortment change | Fresh catalog snapshot, derived category/brand priors, similarity to existing products. |
| Pricing change | Updated price features, margin/revenue objective, price-band affinity. |

The runtime should never depend solely on historical interaction events. Ranking
must degrade gracefully to content, enrichment and business priors when behavior
data is sparse.

Cold-start materialization:

```text
product content features
enriched taxonomy features
brand/category priors
price-band priors
availability priors
global popularity priors
similar product graph
```

Catalog enrichment improves cold-start by adding high-quality attributes,
taxonomy and image-derived tags before a product has behavioral data.

## 17. Predictive autocomplete

Autocomplete should be objective-aware and generate suggestions as users type.

Suggestion types:

- search query suggestions
- brand suggestions
- category suggestions
- product previews
- attribute/refinement suggestions

Suggestion ranking objectives:

- popularity
- conversion
- click-through rate
- revenue
- margin
- availability
- personalization fit

Autocomplete materialization:

```text
prefix -> query suggestions
prefix -> brand suggestions
prefix -> category suggestions
prefix -> product previews
prefix + persona -> personalized suggestions
```

Autocomplete response shape should support:

```json
{
  "prefix": "wat",
  "suggestions": [
    {
      "text": "waterproof jacket",
      "type": "search",
      "score": 0.94
    },
    {
      "text": "Contoso Trail",
      "type": "brand",
      "score": 0.71
    }
  ],
  "productPreviews": []
}
```

Product previews should be hydrated from the same product runtime used by search
and recommendations.

## 18. Query understanding and conversational refinement

The relevance model should produce structured interpretation, not opaque final
ranking decisions.

Example:

```json
{
  "originalQuery": "waterproof jacket for hiking",
  "normalizedQuery": "waterproof hiking jacket",
  "intent": "product_search",
  "categories": ["Outdoor > Clothing > Jackets"],
  "attributes": {
    "waterproof": true,
    "activity": "hiking"
  },
  "synonyms": ["rainproof", "weatherproof"],
  "clarificationNeeded": false
}
```

Broad or low-confidence queries should return a refinement payload:

```json
{
  "query": "jacket",
  "refinement": {
    "questionFlowId": "outdoor-clarifier",
    "nextQuestion": "What are you using it for?",
    "options": ["hiking", "running", "commuting", "camping"]
  }
}
```

Question flows define:

- trigger conditions
- ordered questions
- answer options
- preference keys written to session state
- channels where the question applies

## 19. Real-time personalization and shopper personas

Personalization must use online and offline behavior to curate results for an
individual shopper or anonymous session.

Inputs:

- online behavior: searches, clicks, product views, add-to-cart, purchases
- in-store behavior where available: store purchases, pickup, loyalty events
- historical user events
- current session events
- segment membership
- product/catalog attributes

Materialized persona features:

```text
visitor/session -> brand affinity
visitor/session -> category affinity
visitor/session -> color affinity
visitor/session -> size affinity
visitor/session -> price-band affinity
visitor/session -> fulfillment preference
visitor/session -> recent intent
```

Personalization should affect both:

- search result ordering
- recommendation candidate generation and ranking

Ranking example:

```text
shopper prefers Contoso Trail + ember rose + size M
  -> boost matching products
  -> prefer in-stock size M variants
  -> keep business guardrails and hard rules intact
```

Real-time personalization must be bounded and safe:

- current-session events can update immediately
- durable historical profiles can update asynchronously
- missing persona data falls back to anonymous/session/global signals
- all IDs should be pseudonymous by default
- user deletion/export workflows must cover persona features

## 20. Merchandising controls

Merchandising is represented as data.

Rules can:

- boost products, brands, categories or attributes
- bury products
- pin products
- filter products
- reroute unavailable products
- attach to specific placements
- launch promotions

Rules must be classified during migration:

| Status | Meaning |
| --- | --- |
| `essential` | Contractual, legal, safety, availability or hard business rule. |
| `experimental` | Candidate for A/B testing. |
| `retire` | Legacy manual relevance rule that should be removed. |
| `ai_replaced` | Relevance rule replaced by model/ranking behavior. |

The target state is a small essential rule set plus AI-driven relevance,
personalization and revenue optimization.

Merchandising optimization requirements:

- ranking models optimized for revenue and business impact
- automatic boost eligibility for target audiences or segments
- reduced manual curation/configuration through model-driven ranking
- fallback logic to avoid zero recommendations
- promotion-aware ranking
- audience-aware boost/bury controls
- safe rule testing before publish
- rollback for bad rules or bad model outputs

Fallback hierarchy for empty recommendation placements:

```text
personalized candidates
  -> context/category candidates
  -> bestsellers/trending/top-rated
  -> cold-start/content-similar candidates
  -> configured fallback collection
```

## 21. Serving configs and KPIs

Serving configs define placement-specific ranking behavior and optimization
goals.

Supported objectives:

- conversion
- revenue
- CTR
- margin
- stock clearance
- balanced

KPIs should be selected before model/ranking optimization.

Common KPIs:

- revenue per search
- click-through rate
- conversion rate
- add-to-cart rate
- revenue per session
- margin per session
- zero-result rate
- stock clearance

Each serving config should define:

- placement
- objective
- ranking weights
- attached rule IDs
- question flow ID where applicable
- primary KPI and guardrails

## 22. Catalog enrichment

Catalog enrichment is an offline pipeline step before materialization.

Enrichment outputs may include:

- normalized taxonomy
- inferred attributes
- extracted colors, materials, sizes and patterns
- image-derived tags
- duplicate detection
- title cleanup
- category confidence
- quality score and issues
- searchability/facetability flags

The first implementation can use open-source models or deterministic heuristics.
The schema must preserve enough enriched metadata for retrieval, ranking and
explainability.

## 23. Product API surface

V2 should mirror the operational concepts of the commerce Product resource:

| Operation | Requirement |
| --- | --- |
| `create` | Create one product in a staging snapshot or update journal. |
| `patch` | Apply partial product update by field mask. |
| `delete` | Remove or tombstone one product. |
| `get` | Fetch one product by ID. |
| `list` | Page products in a branch/catalog. |
| `import` | Bulk import products for initial load or rebuild. |
| `purge` | Delete a selected product set under a branch/catalog. |
| `setInventory` | Replace inventory fields with timestamp-aware conflict handling. |
| `addLocalInventories` | Add/update local inventory records for places. |
| `removeLocalInventories` | Remove local inventory records for places. |

Deprecated fulfillment-place APIs should map to local-inventory operations.

## 24. Serving API surface

Minimum serving APIs:

- product get/list
- product import/sync
- inventory update
- user event write
- search
- browse
- suggestions/autocomplete
- recommendations
- cross-sell recommendations
- upsell recommendations
- no-results alternatives
- serving config read/update
- rule/control read/update
- question flow read/update
- health/status

The compatibility layer should additionally mirror the external commerce REST
resource structure documented in `API-COMPATIBILITY.md`:

- products
- user events
- placements
- serving configs
- controls
- attributes config
- completion data
- models
- catalogs
- operations

Frontend-facing adapters must handle:

- result ordering
- facets and dynamic facet counts
- pinned/boosted/buried results
- refinement questions
- recommendation placements
- attribution/event tokens
- unavailable product reroutes
- diagnostics for staging/debugging

## 25. Safety, privacy and responsibility

Production V2 must provide:

- tenant data isolation
- access control for catalog, events, rules and analytics
- no cross-tenant learning unless explicitly enabled and anonymized
- GDPR delete/export workflows
- PII minimization in events
- event retention controls
- audit log for merchandising and catalog changes
- bad-feed and bad-rule rollback
- documented service-level objectives
- pipeline audit and replay history

Snapshot files should avoid raw PII by default.

## 26. Composable commerce architecture

V2 must be headless and modular so retailers can fit it into an existing
commerce stack.

Architecture requirements:

- API-first serving layer
- independent catalog ingestion
- independent event ingestion
- independent recommendation/search serving
- independent merchandising configuration
- portable JSON snapshot format
- replaceable model providers
- replaceable storage/index backends
- channel-neutral placements
- no hard dependency on a managed provider, a managed cloud platform or any single managed search provider

The core contract is:

```text
valid V2 data + configured serving placement -> deterministic API response
```

This keeps the engine composable across:

- existing ecommerce platforms
- custom storefronts
- mobile apps
- email personalization systems
- contact-center applications
- in-store kiosks
- analytics/experimentation platforms

The first implementation can be in-memory and snapshot-driven. Production
deployments can later swap storage, model and serving infrastructure without
changing the catalog/event/schema contract.

## 27. Evaluation and testing

Required test layers:

- schema validation
- ETL transform tests
- bulk ingestion tests
- real-time ingestion tests
- materialized runtime build tests
- search functional tests
- recommendation functional tests
- cross-sell/upsell functional tests
- no-results alternative tests
- facet/filter/rule tests
- personalization tests
- staging end-to-end tests
- load tests for serving and ingestion
- offline replay/evaluation against KPIs

Staging acceptance:

1. Bulk catalog load succeeds.
2. Real-time catalog and inventory updates flow into the serving runtime.
3. Real-time user events are accepted and materialized.
4. Search connects to the serving backend.
5. Browse/category pages use the same serving layer.
6. Recommendations return from the same catalog/event data.
7. Results render in the frontend in the correct order.
8. Facets, merchandising rules and refinement questions display correctly.
9. Event logging works from frontend interactions.
10. End-to-end behavior passes a high-level functional test.

## 28. Migration roadmap

| Milestone | Outcome |
| --- | --- |
| 1. Data audit | Catalog, inventory and user event feeds identified; quality gaps documented. |
| 2. KPI definition | Primary KPI and guardrails selected per placement. |
| 3. Schema mapping | Source fields mapped into `catalog.schema.json`. |
| 4. Baseline runtime | In-memory search, facets, suggestions and recommendations built from one snapshot. |
| 5. Event learning | Click/add-to-cart/purchase events feed ranking and recommendation features. |
| 6. Rule rationalization | Manual rules classified as essential, retired, experimental or AI-replaced. |
| 7. Personalization | Segment/session/visitor affinities affect search and recommendations. |
| 8. Conversational refinement | Broad queries trigger ordered clarification flows. |
| 9. ETL implementation | Bulk and real-time catalog, inventory and event pipelines built and tested. |
| 10. API integration | Application backend calls search, browse, suggest and recommendation APIs. |
| 11. Frontend adaptation | Frontend-facing adapter handles response shape and ordered results. |
| 12. Staging E2E | Staging proves live catalog/event updates, search and recommendations. |
| 13. Evaluation | Offline replay and online A/B tests compare KPI lift against baseline. |
| 14. Production hardening | Privacy, audit, rollback, tenant isolation, SLOs and runbooks completed. |

## 29. Completion criteria

The V2 implementation is production-candidate when:

- ETL pipelines for catalog, inventory and user events are built and tested.
- Bulk ingestion and real-time updates are both supported.
- Search and recommendations reuse the same ingested data.
- Backend services are integrated with product, inventory, event, search, browse,
  suggestion and recommendation APIs.
- Data pipelines are robust and scalable under load.
- Frontend adapter logic displays the new response shape correctly.
- Ranking behavior is tied to explicit KPIs and guardrails.
- Manual merchandising rules are rationalized into a manageable rule set.
- Safety, privacy, audit and rollback controls are present.
- Recommendation models/strategies exist for CTR, conversion, revenue per order,
  cross-sell, upsell and cold-start.
- No-results and low-confidence queries return useful alternatives or
  clarification flows.
- The architecture is headless/composable and has no hard dependency on a managed provider,
  a managed cloud platform or any single managed provider.
- Staging end-to-end testing confirms query-to-results and event feedback loops.
