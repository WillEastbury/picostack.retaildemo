# Enrichment Components

## 1. Purpose

Catalog enrichment makes products more discoverable before they have enough
behavioral data. It is the main cold-start lever for new products, sparse
catalogs and poor merchant feeds.

V2 enrichment is an offline pipeline that produces explicit, explainable fields
used by search, recommendations, facets, autocomplete and query understanding.

## 2. Enrichment architecture

```text
raw product
  -> normalize
  -> enrich text/category/attributes/images/quality
  -> validate
  -> write enriched product snapshot
  -> build CatalogRuntime
```

Enrichment must be deterministic enough to debug. Every enriched field should
carry:

- source component
- confidence
- evidence where possible
- generated timestamp
- whether the value is merchant-supplied or inferred

## 3. Component map

| Component | Input | Output | Used by |
| --- | --- | --- | --- |
| Taxonomy classifier | title, description, merchant category, attributes | normalized categories, taxonomy confidence | browse, facets, cold-start ranking |
| Attribute extractor | title, description, specs, existing attributes | inferred attributes | filters, facets, semantic search |
| Color normalizer | color text, images, attributes | `colorInfo`, color families, display colors | facets, personalization |
| Size normalizer | size strings, variants | normalized sizes, size systems/types | variant selection, filters |
| Material/pattern extractor | text, attributes, images | materials, patterns | facets, semantic search |
| Title cleaner | title, brand, category | normalized title, duplicate-token removal | text search, autocomplete |
| Description summarizer | long description/specs | concise searchable summary | search snippets |
| Image tagger | product images | image-derived tags/colors/category hints | cold-start, visual relevance |
| Duplicate detector | title, GTIN, image hash, brand | duplicate/near-duplicate groups | catalog quality |
| Compatibility extractor | product type, attributes, category | compatibility facts | cross-sell/upsell |
| Quality scorer | all product fields | quality score/issues | feed diagnostics, ranking guardrails |
| Searchability scorer | text/attribute coverage | searchable/facetable/indexable hints | attribute config, diagnostics |

## 4. Enrichment output shape

Products may carry an `enrichment` object:

```json
{
  "enrichment": {
    "version": "2026-06-22.enrich-v1",
    "generatedTime": "2026-06-22T12:00:00Z",
    "taxonomy": {
      "normalizedCategories": ["Outdoor > Clothing > Jackets"],
      "confidence": 0.94,
      "source": "taxonomy-classifier"
    },
    "derivedAttributes": {
      "activity": { "text": ["hiking"], "confidence": 0.88 },
      "weather": { "text": ["rain"], "confidence": 0.91 }
    },
    "imageTags": [
      { "tag": "hooded jacket", "confidence": 0.82 }
    ],
    "quality": {
      "score": 0.92,
      "issues": []
    }
  }
}
```

## 5. Quality issue types

Recommended issue codes:

| Code | Meaning |
| --- | --- |
| `missing_title` | Product title is missing or empty. |
| `missing_category` | Primary product has no category. |
| `missing_image` | Product has no usable image. |
| `missing_price` | Product has no current price. |
| `missing_brand` | Brand is missing where category expects one. |
| `invalid_variant_group` | Variant is missing or has invalid primary ID. |
| `duplicate_gtin` | Multiple products share GTIN unexpectedly. |
| `weak_description` | Description is too short or non-descriptive. |
| `low_attribute_coverage` | Product lacks important category attributes. |
| `conflicting_availability` | Product/variant/inventory availability disagree. |

## 6. Python implementation choices

| Enrichment need | Python implementation |
| --- | --- |
| deterministic normalization | custom rules, `regex`, `rapidfuzz` |
| taxonomy classifier | rules first, then `fastembed` / `sentence-transformers` |
| attribute extraction | regex/rules, small LLM/ONNX model later |
| image tags | optional CLIP/ONNX model later |
| duplicate detection | hashes, `rapidfuzz`, vector similarity |
| quality scoring | deterministic rule engine |
| batch processing | `polars`, Python workers |

Start deterministic. Add ML where it improves measurable quality.

## 7. Runtime materialization

Enrichment feeds:

```text
normalized category -> categoryTree, browse indexes
derived attributes -> facetIndex, filter indexes, query understanding
image tags -> cold-start features, semantic vector text
quality score -> ranking guardrail
compatibility facts -> cross-sell/upsell graphs
```

Enriched fields should be folded into the base runtime, not updated as a
high-churn live overlay.

## 8. Guardrails

Enrichment must not silently override merchant truth.

Precedence:

```text
merchant explicit field
  > merchant custom attribute
  > deterministic normalization
  > model-inferred value
```

If enrichment conflicts with merchant data, keep both and emit a quality issue.

