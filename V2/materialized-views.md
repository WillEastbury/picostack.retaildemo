# V2 Materialized Views

The V2 engine starts from one catalog JSON snapshot and builds query-serving
views in memory.

## Shared source of truth

Search and recommendations are different serving paths over the same source
data:

```text
catalog snapshot
event stream/snapshot
rules
serving configs
personalization features
```

They should be ingested once and materialized into multiple views:

```text
shared ingestion -> CatalogRuntime
CatalogRuntime.search(...)
CatalogRuntime.recommend(...)
```

This avoids duplicate product/event ingestion and keeps search behavior,
recommendation behavior, merchandising rules and personalization signals
consistent.

## ETL pipeline state

The runtime should track ingestion state separately from serving indexes:

```text
pipeline -> domain
pipeline -> mode
pipeline -> checkpoint
pipeline -> lag/freshness
pipeline -> validation failures
pipeline -> dead-letter records
pipeline -> replay cursor
```

Bulk and real-time ingestion both write into the same validated snapshot/update
model. Search and recommendations consume the resulting materialized runtime,
not the raw source tables.

Pipeline quality directly affects model quality:

```text
missing catalog data -> poor retrieval
missing inventory data -> unavailable products in results
missing events -> weak personalization/recommendations
duplicate events -> biased ranking
stale data -> incorrect business outcomes
```

## KPI views

KPIs are materialized per placement so ranking experiments can be measured
against the intended business outcome:

```text
placement -> primary KPI
placement -> guardrail metrics
placement -> baseline score
placement -> experiment score
```

Example KPI features:

```text
revenue per search
CTR
conversion rate
add-to-cart rate
revenue per session
margin per session
zero-result rate
stock clearance rate
```

## Product lookup

```text
productsById: productId -> product
variantsByPrimaryId: primaryProductId -> variant[]
primaryByVariantId: variantProductId -> primaryProductId
effectiveProductByVariantId: variantProductId -> inherited/effective product
collectionsById: collectionId -> product
collectionMembersById: collectionId -> productId[]
gtinIndex: gtin -> productId
localInventoriesByProductId: productId -> localInventory[]
localInventoryByPlaceId: placeId -> productId[]
```

Used by:

- product detail
- search result hydration
- recommend result hydration
- checkout/cart validation

## Primary/variant materialization

Primary products are the search/browse grid entries. Variant products are
purchase/display options under the primary product.

Materialize:

```text
primaryProductId -> primary product
primaryProductId -> variant products[]
variantProductId -> primaryProductId
variantProductId -> effective product
```

Effective variant product resolution:

```text
effectiveVariant = primary shared fields + variant overrides
```

Search and browse should normally retrieve/rank primary products first:

```text
candidate product id = primaryProductId
result card = primary product + best/default variant
```

Inventory and purchase validation should resolve to variants:

```text
selected size/color -> variantProductId -> inventory/price/fulfillment
```

## Text index

```text
term -> posting[]
posting = { productId, fieldMask, termFrequency }
```

Fields:

- `title`
- `description`
- `categories`
- `brands`
- `tags`
- selected `attributes.*.text`

Ranking starts with BM25 or BM25F so title/category/brand hits can be weighted
more than description-only hits.

## Facets

```text
facetName -> value -> { count, productIds? }
```

Default facets:

- category
- brand
- availability
- price bucket
- rating
- selected custom attributes

Facet result counts should be computed over the filtered result set where
possible, with global counts cached for landing pages.

## Numeric/range indexes

```text
field -> sorted(value, productId)[]
priceRange -> primaryProductId
```

Initial numeric indexes:

- price
- availableQuantity
- rating
- cost / margin signal where present
- variant-derived price ranges

## Retail dimension indexes

Materialize common commerce API dimensions as first-class filters/facets:

```text
size -> productId[]
material -> productId[]
pattern -> productId[]
condition -> productId[]
promotionId -> productId[]
languageCode -> productId[]
placeId -> productId[]
fulfillmentType -> productId[]
```

These can also be derived from `attributes`, but top-level retail dimensions
make migration from warehouse-shaped feeds simpler and improve explainability.

## Suggestions

```text
prefix -> suggestion[]
suggestion = { text, type, score }
```

Sources:

- product titles
- categories
- brands
- popular queries from events
- synonym terms

Predictive autocomplete should materialize objective-aware suggestions:

```text
prefix -> search query suggestions
prefix -> brand suggestions
prefix -> category suggestions
prefix -> product previews
prefix + persona -> personalized suggestions
```

Ranking inputs:

```text
popularity
conversion
CTR
revenue
margin
availability
personalization fit
```

## Vector candidates

```text
vectorBucket -> productId[]
productId -> embedding/vector/signature
```

V2 can begin with deterministic lightweight vectors for local demos, but the
production path should allow offline-generated embeddings from ONNX or other
open-source models.

## Query understanding

The query understanding layer materializes and serves reusable model outputs:

```text
queryNormalizationCache: raw query -> normalized query
intentCache: raw query -> intent/entities/categories/attributes
synonymExpansion: term -> equivalent terms
semanticQueryVector: raw query -> vector/signature
clarificationTrigger: query pattern -> question flow id
intentContext: raw query -> shopper intent/context/features
```

This lets the product retrieval layer stay deterministic and explainable even
when LLMs or embedding models are used.

It should support ecommerce-specific semantic interpretation:

```text
"rain coat for mountain walking"
  -> waterproof hiking jacket
  -> Outdoor > Clothing > Jackets
  -> waterproof=true, activity=hiking
```

## Events and learning

Events are loaded separately from the product catalog and materialized into:

```text
skuStats:
  views
  addToCarts
  purchases
  orders

queryStats:
  query -> clicked product IDs
  query -> purchased product IDs
```

Those stats feed ranking:

```text
score = lexical + vector + rules + popularity + conversion + availability
```

The same event stats are reused for recommendations:

```text
views/clicks -> popularity and engagement
add-to-cart -> affinity and complement signals
purchases -> conversion and also-bought signals
search events -> query-to-product learning
```

## Rules

Rules compile into a placement-aware plan:

```text
placement -> condition -> actions
```

Actions:

- boost
- bury
- pin
- filter

Rules should be applied after candidate generation and before final pagination.

Rules should also be inventoried for migration:

```text
rule -> essential | retire | experimental | ai_replaced
```

The goal is to keep hard business/safety/availability constraints while letting
AI ranking replace manual relevance tuning where possible.

## Serving configs

Serving configs compile into:

```text
placement -> ranking weights
placement -> attached rule ids
placement -> objective
placement -> question flow id
```

The ranking engine reads those weights while scoring:

```text
score =
  lexicalWeight * lexicalScore +
  semanticWeight * semanticScore +
  personalizationWeight * affinityScore +
  businessRulesWeight * ruleScore +
  availabilityWeight * availabilityScore
```

The ranking inputs map directly to business needs:

```text
engagement -> ctr/click/add-to-cart signals
revenue -> price * conversion probability
margin -> price - cost
stock clearance -> inventory age + available quantity
customer fit -> segment/category/brand/attribute affinity
```

## Question flows

Question flows compile into:

```text
trigger -> ordered questions
question -> preference key
```

They can be shared across:

- web search
- mobile search
- voice shopping
- kiosk flows
- call-center assistant flows

The runtime can return a refinement payload when a query is broad or ambiguous:

```text
query -> trigger match -> next question -> preference update -> rerank
```

## Recommendations

Recommendation views are built from the same catalog and event data:

```text
similarItems: productId -> productIds
alsoBought: productId -> productIds
userAffinity: segment/visitor -> productIds
cartComplements: productId -> productIds
```

Initial algorithms can be simple:

- content similarity from product text/attributes/categories
- co-occurrence from add-to-cart/purchase events
- popularity within category
- business objective weighting

Later algorithms can replace the materialization step without changing the
serving API.

Recommendation placements should support:

```text
home page personalized rows
search modules
browse/category modules
product detail similar items
cart complements
checkout cross-sell
checkout upsell
no-results alternatives
email campaign recommendations
mobile app recommendations
kiosk/call-center assistant recommendations
```

Objective-specific recommendation views:

```text
ctrCandidates: placement/context -> productIds
conversionCandidates: placement/context -> productIds
revenuePerOrderCandidates: placement/context -> productIds
crossSellCandidates: cart/product -> productIds
upsellCandidates: product/cart -> productIds
coldStartCandidates: product/session/context -> productIds
noResultsAlternatives: failed query/context -> productIds/categories/questions
othersYouMightLike: product/session -> productIds
frequentlyBoughtTogether: product/cart -> productIds
recommendedForYou: visitor/session -> productIds
recentlyViewed: visitor/session -> productIds
pageLevelOptimization: page/placement/context -> productIds
buyItAgain: visitor/session -> productIds
onSale: visitor/session/context -> productIds
bestsellers: category/query/window -> productIds
newArrivals: category/window -> productIds
trendingProducts: category/query/window -> productIds
topRatedProducts: category/query -> productIds
```

Retraining/materialization cadence:

```text
daily offline model/materialization refresh
real-time session feature refresh
real-time inventory/availability refresh
```

Real-time prediction overlay:

```text
sessionRecentViews
sessionRecentCarts
sessionRecentOrders
currentCart
currentQuery
currentPage
currentOffers
currentInventory
```

Fallback plans:

```text
placement -> personalized fallback
placement -> category fallback
placement -> bestseller/trending fallback
placement -> configured fallback collection
```

## Cold-start features

Materialize fallback features so new products and users can still receive useful
results:

```text
product -> content features
product -> enriched taxonomy features
product -> image/tag features
product -> category/brand priors
product -> price-band priors
product -> availability priors
product -> similar product ids
anonymous/session -> current query intent
anonymous/session -> global popularity priors
```

Cold-start products should rank from catalog/enrichment features before they
have clicks or purchases. Cold-start users should rank from query/session
context, global priors and business objectives before they have a durable
profile.

## Personalization features

Materialize:

```text
visitor -> segment ids
visitor -> category affinities
visitor -> brand affinities
visitor -> price-band affinities
visitor -> color affinities
visitor -> size affinities
visitor -> fulfillment preferences
session -> current intent/context
query -> historically clicked SKUs
query -> historically purchased SKUs
```

For anonymous sessions, fall back to:

```text
current session events
popular query stats
global conversion/margin signals
```

## Safety and audit views

Materialize operational controls:

```text
tenantId -> allowed catalog ids
ruleChangeAudit -> entries
snapshotVersion -> checksum/signature
privacyConfig -> retention/delete/export settings
pipelineAudit -> ingestion checkpoints/failures/replays
```

These are not search indexes, but they are required for production serving.

## Atomic swap

Build views into a new immutable `CatalogRuntime`:

```text
CatalogSnapshot -> CatalogRuntime
```

When complete:

```text
currentRuntime = newRuntime
```

This gives predictable rollback and zero partial-index states.
