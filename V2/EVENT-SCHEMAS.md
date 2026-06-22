# Event Schemas

## 1. Purpose

Events are the learning signal for search, recommendations, personalization,
KPI measurement and real-time session adaptation.

V2 events must support both:

- commerce-compatible ingestion concepts
- warehouse-style analytical aggregation
- in-memory real-time overlays

## 2. Event design principles

Events must be:

- append-only
- deduplicatable
- pseudonymous by default
- attributable to a serving response
- joinable to products and variants
- safe for bulk replay
- rich enough to compute KPIs
- compact enough for high-volume ingestion

## 3. Base event schema

All events share this envelope:

```json
{
  "eventId": "evt-001",
  "eventType": "search",
  "eventTime": "2026-06-22T11:01:00Z",
  "visitorId": "visitor-123",
  "sessionId": "session-abc",
  "userId": null,
  "attributionToken": "attr-search-001",
  "placement": "search",
  "servingConfigId": "default-search",
  "channel": "web",
  "userAgent": "optional",
  "ipHash": "optional",
  "labels": {}
}
```

`eventId` is required for idempotency where possible. If a source system cannot
provide one, the ingestion layer must derive one from stable fields.

## 4. Supported event types

| Event type | Purpose |
| --- | --- |
| `search` | User searched for a query. |
| `browse` | User browsed a category or collection. |
| `category-page-view` | Category page impression. |
| `detail-page-view` | Product detail page view. |
| `product-view` | Product impression in a list/module. |
| `click` | User clicked a product/result. |
| `add-to-cart` | Product added to cart. |
| `purchase` | Order placed. |
| `refund` | Product refunded. |
| `return` | Product returned. |
| `recommendation-impression` | Recommendation module was shown. |
| `autocomplete-select` | User selected autocomplete suggestion. |
| `question-answer` | User answered a clarification question. |

## 5. Product detail records

Events that involve products should include `productDetails`.

```json
{
  "productDetails": [
    {
      "productId": "SKU-001-M-ROSE",
      "primaryProductId": "SKU-001",
      "position": 1,
      "quantity": 1,
      "price": 129.99,
      "currencyCode": "GBP"
    }
  ]
}
```

Use variant IDs for purchase/cart events where variants are selected. Include
primary IDs for rollups.

## 6. Search event payload

```json
{
  "eventType": "search",
  "query": "waterproof jacket",
  "pageCategories": ["Outdoor > Clothing > Jackets"],
  "attributionToken": "attr-search-001",
  "productDetails": [
    { "productId": "SKU-001", "position": 1 }
  ]
}
```

Used for:

- query popularity
- zero-result rate
- query-to-click learning
- revenue per search
- autocomplete training

## 7. Click event payload

```json
{
  "eventType": "click",
  "attributionToken": "attr-search-001",
  "productDetails": [
    { "productId": "SKU-001", "position": 1 }
  ]
}
```

Used for:

- CTR
- ranking feedback
- query/product association

## 8. Purchase event payload

```json
{
  "eventType": "purchase",
  "transactionInfo": {
    "transactionId": "order-123",
    "value": 129.99,
    "currencyCode": "GBP",
    "tax": 0,
    "shipping": 0
  },
  "productDetails": [
    {
      "productId": "SKU-001-M-ROSE",
      "primaryProductId": "SKU-001",
      "quantity": 1,
      "price": 129.99,
      "currencyCode": "GBP"
    }
  ]
}
```

Used for:

- conversion rate
- revenue per search
- revenue per session
- frequently bought together
- buy it again
- margin ranking where cost is available

## 9. Recommendation events

Recommendation impressions and clicks should include:

- placement
- servingConfigId
- attributionToken
- model/strategy ID
- productDetails with positions

This lets V2 evaluate each recommendation model type separately.

## 10. Clarification question events

Question-answer events should include:

```json
{
  "eventType": "question-answer",
  "questionFlowId": "outdoor-clarifier",
  "questionId": "activity",
  "answer": "hiking",
  "writesPreference": "activity"
}
```

Used for:

- conversational refinement
- session personalization
- question flow optimization

## 11. KPI joins

The core KPI join key is:

```text
attributionToken + placement + servingConfigId
```

Examples:

```text
search event -> click event -> add-to-cart event -> purchase event
```

From this chain V2 computes:

- CTR
- conversion rate
- add-to-cart rate
- revenue per search
- revenue per session
- recommendation attach rate
- zero-result recovery rate

## 12. Privacy fields

Allowed identity fields:

- `visitorId`
- `sessionId`
- pseudonymous `userId`

Avoid:

- raw email
- raw phone number
- raw address
- full IP address
- payment details

If needed, store only salted hashes or externally managed identity references.

## 13. Storage layout

Live writes:

```text
blob://catalogs/{catalog}/branches/{branch}/append/events/YYYY/MM/DD/worker-{id}/segment-{id}.jsonl
```

Compacted analytics:

```text
blob://catalogs/{catalog}/branches/{branch}/snapshots/{version}/events/date=YYYY-MM-DD/events.parquet
```

Feature snapshots:

```text
blob://catalogs/{catalog}/branches/{branch}/snapshots/{version}/features/product_stats.parquet
blob://catalogs/{catalog}/branches/{branch}/snapshots/{version}/features/query_stats.parquet
blob://catalogs/{catalog}/branches/{branch}/snapshots/{version}/features/serving_config_kpis.parquet
blob://catalogs/{catalog}/branches/{branch}/snapshots/{version}/features/persona_features.parquet
```

## 14. Materialized features

Events materialize into:

```text
product -> views/clicks/carts/purchases/revenue
query -> impressions/clicks/purchases/revenue
servingConfig -> KPI metrics
visitor/session -> affinities
product -> co-purchase products
query -> clicked/purchased products
category -> trending/bestseller products
```

## 15. Ingestion validation

Reject or dead-letter events when:

- `eventType` is unknown
- `eventTime` is missing
- product IDs are malformed
- purchase has no transaction value and no product prices
- attribution token is required but absent for served-result events
- event exceeds size limits
- event contains raw PII in blocked fields
