# Retail Search V2

V2 is the proposed production direction for the retail search service:

```text
cold retail catalog JSON snapshot
  + committed append blobs
  -> validate
  -> build in-memory materialized views
  -> serve search / suggest / recommend / product APIs
```

The retail search engine should be able to start from cold catalog blobs and
committed append blob segments, then materialize everything it needs in memory.

## Goals

- Keep provisioning cheap and simple.
- Make catalog import/debugging easy: inspect one JSON snapshot plus committed
  append segments.
- Build all query-serving structures at startup or after an atomic snapshot swap.
- Keep the serving platform completely in memory; durable state is blob
  snapshots and append blobs with tail markers.
- Support optional dual/multi-write storage replicas for ingress writes, with
  all required storage accounts committed before success or asynchronous
  operation completion.
- Stay close to widely used commerce product and event API shapes.
- Support later production features without forcing a database-first design.
- Support merchandising controls: boost, bury, pin and filter.
- Support configurable clarification/question flows.
- Support personalization and business-goal optimized serving configs.
- Support AI commerce search as two linked capabilities: search and recommendations.
- Support websites, mobile apps, kiosks, call-center apps and voice shopping from the same serving configs.
- Support safety, privacy, tenant isolation and compliance as explicit service requirements.

## Source files

| File | Purpose |
| --- | --- |
| `SUMMARY.md` | Cross-page summary of the V2 platform, storage, endpoint, runtime, API and deployment design. |
| `SYSTEM-SPECIFICATION.md` | Consolidated system specification for the platform, storage, partitioning, runtime, APIs and operations. |
| `MODULE-LAYER-DESIGN.md` | Layered module design for API, auth, partitioning, domain services, runtime, indexing and blob storage. |
| `V1-DEMO.md` | Runnable V1 FastAPI demo implementation and reusable module map. |
| `ENGINEERING-GUARDRAILS.md` | Product quality, cost and reuse-first engineering guardrails. |
| `SPECIFICATION.md` | End-to-end V2 product, ingestion, serving, ranking, safety and migration specification. |
| `API-COMPATIBILITY.md` | External commerce REST API compatibility map for resources, methods, request concepts and response shapes. |
| `FEATURES-API-BUILD-PLAN.md` | Consolidated feature catalogue, API surface mapping and implementation build plan. |
| `MODULAR-API-HOST-DESIGN.md` | Python API host design mapping commerce API areas and V2 features into composable modules. |
| `INMEMORY-PYTHON-RUNTIME.md` | Embedded Python runtime design using raw catalog JSON, event logs, Parquet features and in-memory indexes. |
| `PLATFORM-ARCHITECTURE.md` | Platform architecture mapping service capabilities to Python libraries, modules, runtime planes and deployment stages. |
| `ARCHITECTURE-AMENDMENTS.md` | Rubber-duck review amendments covering live overlays, inventory precedence, events, pagination, scaling and schema hardening. |
| `BLOB-STORAGE.md` | Blob snapshot and append blob tail-marker persistence model for the fully in-memory platform. |
| `AZURE-TENANT-SERVICE-TOPOLOGY.md` | Azure tenant storage and endpoint topology using one blob container per tenant. |
| `AKS-FASTAPI-DEV-OPERATIONS.md` | Lean AKS/FastAPI deployment, management pipeline, and authentication/STS design. |
| `PRODUCTION-HARDENING.md` | Production hardening, security, logging, observability, performance and runbook design. |
| `SCALEOUT-PARTITIONING.md` | Extensible hash partitioning, sticky routing and partitioned storage/runtime ownership for maximal scale-out. |
| `MULTI-REGION-CLUSTERING.md` | Multi-region and multi-cluster routing, failover, CDN-like read behavior and region-aware partition ownership. |
| `ENRICHMENT-COMPONENTS.md` | Enrichment pipeline components, outputs, quality issues and runtime materialization. |
| `EVENT-SCHEMAS.md` | Event schema design for attribution, KPI joins, personalization and warehouse-style analytics. |
| `ARCHITECTURE-ENDPOINTS.excalidraw` | Editable architecture diagram showing endpoints, calls, STS, indexing, blob storage and async consumers. |
| `catalog.schema.json` | JSON Schema for the V2 catalog snapshot. |
| `sample-catalog.json` | Small example catalog with products, variants, inventory, events, rules and synonyms. |
| `materialized-views.md` | What is built in memory from the JSON snapshot. |

## Top-level catalog shape

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
  "synonyms": []
}
```

## Product shape

The product document intentionally uses familiar commerce API naming where useful:

- `id`
- `name`
- `type`
- `primaryProductId`
- `collectionMemberIds`
- `gtin`
- `title`
- `description`
- `languageCode`
- `categories`
- `brands`
- `uri`
- `images`
- `priceInfo`
  - `priceRange`
- `rating`
- `ttl`
- `availableTime`
- `availability`
- `availableQuantity`
- `fulfillmentInfo`
- `attributes`
- `audience`
- `colorInfo`
- `sizes`
- `materials`
- `patterns`
- `conditions`
- `tags`
- `publishTime`
- `expireTime`
- `promotions`
- `variants`
- `localInventories`
- `retrievableFields`

## Commerce schema compatibility notes

The current V2 product schema covers the important commerce product fields:

- resource identity: `name`, `id`
- product grouping: `type`, `primaryProductId`, `collectionMemberIds`
- identifiers: `gtin`
- content: `title`, `description`, `languageCode`, `categories`, `brands`,
  `tags`
- custom attributes: `attributes`
- price: `priceInfo`
- variant-derived price bands: `priceInfo.priceRange`
- quality: `rating`
- lifecycle: `publishTime`, `expireTime`, `ttl`, `availableTime`
- inventory: `availability`, `availableQuantity`, `fulfillmentInfo`,
  `localInventories`
- presentation: `uri`, `images`, `audience`, `colorInfo`
- retail dimensions: `sizes`, `materials`, `patterns`, `conditions`
- commercial controls: `promotions`

One intentional representation difference: warehouse-style schemas often model
`attributes` as repeated `{ key, value }` records. V2 models attributes as a
JSON object keyed by attribute name:

```json
{
  "attributes": {
    "waterproof": { "booleanValues": [true] },
    "size": { "text": ["M"] }
  }
}
```

The ETL layer should transform repeated key/value rows into this map for runtime
efficiency, while export adapters can transform the map back to repeated records
when needed.

Additional REST parity details:

- V2 accepts both REST-style `ttl` duration strings such as `"2592000s"` and the
  warehouse-style `{ "seconds": 2592000, "nanos": 0 }` shape.
- V2 accepts both deprecated REST `retrievableFields` comma-separated field-mask
  strings and the earlier array form used by the local runtime.
- `attributes.searchable` and `attributes.indexable` are captured for migration
  compatibility, even though the production design should prefer a central
  attribute configuration over product-level flags.
- `priceInfo.priceRange` and nested `variants[]` may be output/materialized
  fields. V2 can accept them in snapshots for demos, but import pipelines should
  be able to derive them from variant products.
- `localInventories[]` is present on products for REST compatibility, while V2
  also keeps top-level `inventory[]` for high-volume update streams.

## Product API surface to mirror

The V2 product service should map to standard commerce product operations:

| Operation | V2 equivalent |
| --- | --- |
| `create` | Create one product in a staging snapshot or update journal. |
| `patch` | Apply partial product update by field mask. |
| `delete` | Remove or tombstone one product. |
| `get` | Fetch one product by ID. |
| `list` | Page products in a branch/catalog. |
| `import` | Bulk import products for initial load/rebuild. |
| `purge` | Delete a selected product set under a branch/catalog. |
| `setInventory` | Replace inventory fields with timestamp-aware conflict handling. |
| `addLocalInventories` | Add/update local inventory records for places. |
| `removeLocalInventories` | Remove local inventory records for places. |

Deprecated `addFulfillmentPlaces` and `removeFulfillmentPlaces` should map to
local-inventory updates rather than becoming first-class V2 APIs.

## Retail product constructs

### Primary products

Primary products are the parent/container product records. They group variants
and act as the default entries in the search grid.

Primary products should contain only attributes shared by every variant:

- `id`
- `type = PRIMARY`
- `primaryProductId`
- `title`
- `description`
- shared `categories`
- shared `brands`
- shared `images`
- shared `attributes`

For a primary product, `id` and `primaryProductId` should be identical. The
sample keeps `primaryProductId` nullable for compatibility with source feeds,
but the normalized runtime should materialize the primary ID as the product ID.

Search grid behavior:

```text
search/browse candidate = primary product
variant products = selectable purchase options under the primary product
```

### Variant products

Variant products inherit common attributes from their primary product and add or
override variant-specific values.

Variant products should include:

- `id`
- `type = VARIANT`
- `primaryProductId`
- inherited or overridden `title`
- inherited or overridden `description`
- variant `priceInfo` where different
- variant `availability`
- variant `availableQuantity`
- variant attributes such as color, size, material, fit or pack size

Variant-specific values override primary values for purchase, inventory and
display. Shared fields do not need to be duplicated on every variant.

Materialization should produce:

```text
primaryProduct -> variants[]
variantProduct -> inherited effective product
search result -> primary product + best/default variant
```

## Serving model

At runtime, the service should not query the raw JSON directly. It should build:

```text
productsById
variantsByPrimaryId
categoryTree
brandIndex
textInvertedIndex
facetIndex
numericRangeIndex
availabilityIndex
suggestPrefixIndex
productVectors
vectorBuckets
eventStats
rulePlan
```

Then API requests are served from those materialized views.

## Shared ingestion model

Search and recommendations must use the same ingested data:

```text
catalog data + user events
  -> validation/enrichment
  -> materialized runtime
  -> search results + recommendations
```

The service should not require duplicate ingestion when both capabilities are
enabled. Product/catalog documents, inventory updates, events, rules and
personalization features are ingested once, then projected into the indexes and
views each serving path needs.

Shared source data:

- product catalog
- variants and collections
- inventory and availability
- user events: view, search, click, add-to-cart, purchase
- merchandising rules
- serving configs
- personalization segments and affinities

Derived serving views:

- search retrieval indexes
- suggestion indexes
- semantic/vector candidate indexes
- recommendation candidate graphs
- visitor/session affinity features
- product/query conversion features

## Data domains to onboard

The migration starts with three core data domains:

| Domain | Purpose | Examples |
| --- | --- | --- |
| Catalog | Defines what can be searched, recommended and merchandised. | Products, variants, collections, categories, brands, attributes, images, prices. |
| Inventory | Controls availability-aware ranking, filtering, rerouting and stock-clearance strategies. | Available quantity, fulfillment location, pickup/shipping availability, backorder/preorder status. |
| User events | Teaches the system what customers search, click, view, add to cart and buy. | Search, browse, product view, click, add-to-cart, purchase, refund/return where allowed. |

These should be treated as first-class inputs to both search and
recommendations. Catalog and inventory explain what can be served; events
explain what performs.

## KPI and optimization strategy

Before tuning models or ranking weights, define the primary KPI for each
serving config. The KPI becomes the optimization target and the benchmark for
success.

Common KPIs:

- revenue per search
- click-through rate
- conversion rate
- add-to-cart rate
- revenue per session
- margin per session
- zero-result rate reduction
- stock clearance

Example placement goals:

| Placement | Primary KPI | Secondary guardrails |
| --- | --- | --- |
| Search results | Revenue per search | Conversion, zero-result rate, latency. |
| Autocomplete | CTR | Query reformulation rate, latency. |
| Product recommendations | Conversion rate | Diversity, availability, margin. |
| Cart complements | Revenue per session | Attach rate, customer satisfaction. |
| Stock clearance row | Inventory reduction | Margin floor, brand constraints. |

## Business rules vs AI optimization

The migration should explicitly separate essential rules from rules that the AI
ranking layer can replace.

Keep rules when they are contractual, legal, operational or safety-critical:

- supplier/brand agreements
- compliance exclusions
- age-restricted products
- recalled products
- out-of-stock rerouting
- hard promotion placements
- regional availability restrictions

Retire or reduce rules when they are trying to approximate relevance manually:

- broad synonym lists
- hand-ranked category boosts
- static seasonal boosts
- manual "popular item" boosts
- duplicated query rewrites
- hundreds/thousands of micro-merchandising rules

Target state:

```text
many hand-crafted relevance rules
  -> small essential rule set
  -> AI handles personalization, relevance, conversion and revenue optimization
```

The merchandising console should show which rules are essential, experimental,
retired or AI-replaced.

## API familiarization

Before implementation, the team should walk through the AI Commerce Search API
surface and map each endpoint to the V2 equivalent.

Core API families to understand:

- catalog import/update
- inventory update
- user event ingestion
- search
- recommendations
- autocomplete/suggestions
- serving config management
- control/rule management
- model/tuning/evaluation where available

V2 should keep API boundaries close enough that a later managed-service or
hybrid backend remains possible.

## ETL and API integration phase

AI Commerce Search depends on catalog, inventory and user-event data being
mapped into the required serving schema. Real retailers usually start from
multiple source tables or feeds, so V2 needs explicit ETL pipelines rather than
assuming the source system already emits the final JSON shape.

Required ETL paths:

| Pipeline | Mode | Purpose |
| --- | --- | --- |
| Catalog bulk import | Batch/bulk | Initial load of products, variants, collections, categories, brands, prices and attributes. |
| Catalog real-time updates | Streaming/API | Continuous product changes, price updates, attribute edits and availability changes. |
| Inventory real-time updates | Streaming/API | Stock level, fulfillment, backorder/preorder and location availability updates. |
| User event bulk import | Batch/bulk | Historical training/replay data for baseline ranking and recommendations. |
| User event real-time ingestion | Streaming/API | Search, browse, click, view, add-to-cart and purchase events for fresh personalization and learning. |

Pipeline responsibilities:

- extract from source systems
- transform into the V2 catalog/event schema
- validate required fields and enum values
- normalize product IDs/SKUs/variant relationships
- preserve event ordering where required
- deduplicate retries idempotently
- dead-letter invalid records
- expose freshness, lag and failure metrics
- support replay from a known checkpoint

## Backend and frontend integration phase

Application backends need to call the new serving APIs for:

- search
- browse/category pages
- autocomplete/suggestions
- recommendations
- product hydration where needed
- event logging after impressions, clicks and purchases

The frontend-facing backend may need an adapter because the new search response
shape can differ from the previous implementation. That adapter should handle:

- result ordering
- facets and dynamic facet counts
- pinned/boosted/buried results
- refinement questions
- recommendation placements
- attribution tokens / event tokens
- unavailable product reroutes
- response diagnostics for staging/debugging

## Pipeline robustness requirements

The data pipelines are part of model quality. Missing or delayed events directly
reduce personalization and recommendation quality, while bad catalog data harms
retrieval and ranking.

Robustness requirements:

- bulk import and real-time ingestion both supported
- exactly-once or idempotent-at-least-once processing
- backpressure handling during traffic spikes
- durable queues/checkpoints
- retry with bounded exponential backoff
- dead-letter queue for bad records
- schema validation before publish
- freshness and completeness dashboards
- load tests for catalog and event ingestion
- replay support for recovery and model rebuilds

## Staging functional test

The implementation phase is complete when staging can prove:

1. Bulk catalog load succeeds.
2. Real-time catalog and inventory updates flow into the serving runtime.
3. Real-time user events are accepted and materialized.
4. Search connects to the AI Commerce Search backend.
5. Browse/category pages use the same serving layer.
6. Recommendations return from the same catalog/event data.
7. Results render in the frontend in the correct order.
8. Facets, merchandising rules and refinement questions display correctly.
9. Event logging works from frontend interactions.
10. End-to-end behavior passes a high-level functional test.

## Implementation acceptance criteria

This phase is done when:

- ETL pipelines for catalog, inventory and user events are built and tested.
- Bulk ingestion and real-time updates are both supported.
- Backend services are integrated with search, browse and recommendation APIs.
- Data pipelines are robust and scalable under load.
- Frontend adapter logic displays the new response shape correctly.
- Staging end-to-end testing confirms query-to-results and event feedback loops.

## Migration roadmap

Suggested milestone path:

| Milestone | Outcome |
| --- | --- |
| 1. Data audit | Catalog, inventory and event feeds identified; quality gaps documented. |
| 2. KPI definition | Primary KPI and guardrails selected per placement. |
| 3. V2 schema mapping | Current product/event/inventory fields mapped into `catalog.schema.json`. |
| 4. Baseline runtime | In-memory search, facets, suggestions and recommendations built from one snapshot. |
| 5. Event learning | Click/add-to-cart/purchase events feed ranking and recommendation features. |
| 6. Rule rationalization | Manual rules classified as essential, retired, experimental or AI-replaced. |
| 7. Personalization | Segment/session/visitor affinities affect search and recommendations. |
| 8. Conversational refinement | Broad queries trigger ordered clarification flows. |
| 9. ETL implementation | Bulk and real-time catalog, inventory and event pipelines built and tested. |
| 10. API integration | Application backend calls search, browse, suggest and recommendation APIs. |
| 11. Frontend adaptation | Frontend-facing adapter handles the new response shape and renders ordered results. |
| 12. Staging E2E | Staging proves live catalog/event updates, search results and recommendations. |
| 13. Evaluation | Offline replay and online A/B tests compare KPI lift against baseline. |
| 14. Production hardening | Privacy, audit, rollback, tenant isolation, SLOs and operational runbooks completed. |

## Merchandising and business goals

V2 treats merchandising as data:

- boost products, brands, categories or attributes
- bury products that are out of stock, low margin, low quality or strategically de-prioritized
- pin products to positions
- filter products for a placement
- attach rules to serving configs

Serving configs define the business goal for a placement:

```json
{
  "id": "default-search",
  "placement": "search",
  "objective": "revenue",
  "ranking": {
    "lexicalWeight": 1.0,
    "semanticWeight": 0.35,
    "personalizationWeight": 0.45,
    "businessRulesWeight": 0.4,
    "availabilityWeight": 0.25
  }
}
```

Supported objective types:

- `conversion`
- `revenue`
- `ctr`
- `margin`
- `stock_clearance`
- `balanced`

## Clarification / question flows

Question flows let the retailer control what questions are asked and in what
order when the query is ambiguous or low confidence:

```json
{
  "id": "outdoor-clarifier",
  "trigger": {
    "queryContainsAny": ["jacket", "boots", "waterproof"],
    "lowConfidenceBelow": 0.55
  },
  "questions": [
    {
      "id": "activity",
      "text": "What are you using it for?",
      "type": "single_select",
      "options": ["hiking", "running", "commuting", "camping"],
      "writesPreference": "activity"
    }
  ]
}
```

These flows can be used by web, voice, kiosk and call-center channels.

## Personalization

Personalization is loaded as materialized features rather than requiring an
online database for every query:

```text
visitor/session events -> segment/affinity features -> ranking features
```

The catalog snapshot can include segment definitions and objective weights.
Runtime event logs can be folded into a new snapshot or a sidecar feature file.

## AI commerce search capabilities

V2 should expose two primary capabilities:

### Search

Search is query-led product retrieval:

- product search
- category/browse search
- facets and filters
- suggestions/autocomplete
- boost/bury/pin merchandising
- semantic and lexical ranking
- personalization by session, visitor or segment

### Recommendations

Recommendations are product-led or user-led retrieval:

- similar items
- frequently bought together
- recommended for you
- recently viewed continuation
- cart complements
- email/mobile/kiosk/call-center recommendations

Both capabilities use the same materialized runtime:

```text
catalog + events + rules + personalization -> materialized runtime
```

That shared runtime is the key design point: if a retailer enables both search
and recommendations, the catalog feed and event feed are loaded once and reused
by both serving APIs.

## Capability needs captured

| Need | V2 capability |
| --- | --- |
| Transform search with highly personalized results and recommendations at scale | Materialized visitor/session/segment features feed both search ranking and recommendation generation. |
| Use AI-driven product rankings and catalog enhancements to maximize revenue and drive engagement | Serving configs combine lexical, semantic, personalization, availability, merchandising and business-objective scores. Catalog enrichment adds taxonomy, attributes, quality signals and searchability metadata before indexing. |
| Leverage commerce-tuned relevance LLMs to understand what customers are looking for | Query understanding can run as an offline/online model step that emits normalized intent, entities, categories, attributes, synonyms, vector query features and clarification triggers. The first implementation can use OSS models; the API shape should not depend on a specific vendor. |
| Understand true user intent with semantic search | NLP query understanding, semantic embeddings/rerankers and synonym detection map broad shopper language to product intent, context, categories and attributes. |
| Deliver real-time personalized search results | Current session events and historical online/in-store behavior materialize shopper personas such as brand, color, size, category and fulfillment affinities. |
| Generate results for cold-start products and users | Content, enrichment, taxonomy, image tags, category/brand priors, popularity priors and current-session context provide fallback ranking signals. |
| Predictive autocomplete | Prefix indexes generate search, brand, category and product-preview suggestions ranked by popularity, conversion, CTR, revenue, margin, availability and personalization fit. |
| Curated recommendations | Objective-specific recommendation strategies optimize CTR, conversion, revenue per order, margin, cross-sell, upsell and cold-start outcomes. |
| Engage customers at every touchpoint | Channel-neutral placements support home, search, browse, product detail, add-to-cart, checkout, no-results, email, mobile, kiosk and contact-center use cases. |
| Personalized cross-sell and up-sell | Basket, product, persona, compatibility, price-ladder and margin signals drive complementary products, upgrades and add-ons. |
| Frictionless buyer experience | No-results and low-confidence searches return spelling/synonym fixes, alternatives, adjacent categories, cold-start recommendations or clarification flows. |
| Recommendation model types | Supports others-you-might-like, frequently-bought-together, recommended-for-you, recently-viewed, page-level optimization, buy-it-again, on-sale, bestsellers, new-arrivals, trending and top-rated feeds. |
| Search-based recommendations | Search and browse contexts can surface bestsellers, new arrivals, trending products, top-rated products, popular-for-query products and alternatives. |
| Merchandising optimization | Revenue/business-impact ranking, audience boosts, reduced manual curation, promotion awareness and configured fallback logic avoid zero recommendations. |
| Real-time predictions | Recommendations combine offline candidates with real-time search, browse, view, cart, order, assortment, price, inventory and offer signals. |
| Composable commerce solutions | V2 is headless, modular, API-first and provider-neutral, with replaceable storage, model and serving backends. |
| Guide users to refine and narrow broad search queries through back-and-forth conversation | `questionFlows` define ordered clarification prompts, triggers, options and preference writes for web, mobile, voice, kiosk and call-center channels. |
| Take advantage of built-in safety and merchandising features | `rules`, `servingConfigs`, audit metadata, tenant isolation, privacy controls and atomic snapshot rollback are part of the V2 serving contract. |

## Query understanding / relevance model hook

The relevance model should produce a structured query interpretation rather than
directly deciding final results:

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

This keeps the system explainable:

```text
query -> model interpretation -> candidate retrieval -> rules/personalization -> final ranking
```

Commerce-tuned LLMs or OSS embedding/rerank models can be swapped in behind this
contract without changing the product/catalog schema.

## Conversational refinement

Broad or low-confidence queries should not just return weak results. They should
return results plus a refinement plan:

```json
{
  "query": "jacket",
  "results": [],
  "refinement": {
    "questionFlowId": "outdoor-clarifier",
    "nextQuestion": "What are you using it for?",
    "options": ["hiking", "running", "commuting", "camping"]
  }
}
```

Each answer writes a preference into the session and re-runs search with a more
specific interpretation.

## Merchandising console requirements

The V2 schema captures the data that a future console would edit.

Business users should be able to:

- boost products, brands, categories and attributes
- bury out-of-stock or strategically de-prioritized products
- pin products to exact positions
- configure result reroutes when inventory changes
- launch promotions
- attach rules to placements
- test strategies before publishing
- deploy a rule set instantly through atomic snapshot swap
- tune objectives such as conversion, revenue, CTR, margin or stock clearance

The runtime artifact for this is:

```text
rules[] + servingConfigs[] -> rulePlan + servingConfigPlan
```

## Catalog improvement requirements

V2 should support catalog enrichment as an offline pipeline step before
materialization. The initial OSS/custom version should be explicit about which
enrichment components it owns, while the schema leaves room for richer
equivalent enrichment outputs later.

Enrichment outputs to support:

- normalized taxonomy
- inferred attributes
- extracted colors/materials/sizes
- image-derived tags
- duplicate detection
- title cleanup
- category confidence
- missing attribute diagnostics
- searchability/facetability flags

Suggested fields:

```json
{
  "attributes": {},
  "derivedAttributes": {},
  "taxonomy": {},
  "quality": {
    "score": 0.92,
    "issues": []
  }
}
```

## Safety and responsibility requirements

The production service must treat safety/privacy as part of the serving model:

- tenant data isolation
- access control for catalog, events, rules and analytics
- no cross-tenant learning unless explicitly enabled and anonymized
- GDPR delete/export workflows
- PII minimization in events
- event retention controls
- audit log for merchandising and catalog changes
- safe rollback for bad feeds/rules
- documented service-level objectives

V2 snapshot files should avoid raw PII by default. Visitor and user identifiers
should be pseudonymous or externally managed.

## Update model

Start simple:

1. Upload/replace catalog JSON.
2. Validate against `catalog.schema.json`.
3. Build a new in-memory index beside the current one.
4. Atomically swap when ready.
5. Keep the previous snapshot for rollback.

Incremental updates can come later, but full snapshot rebuild gives the cleanest
first production path.

## Storage relationship

V2 should not require any single storage engine as the source of truth. The
search engine should consume any valid V2 catalog JSON snapshot and can persist
snapshots, event logs, patch journals and index artifacts through replaceable
storage adapters.
