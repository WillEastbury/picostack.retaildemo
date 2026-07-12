from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


def platform_guide_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WaveSearch Labs - Indexing and API Platform Guide</title>
  <script>
  (() => {
    const param = new URLSearchParams(window.location.search).get("clawpilotTheme");
    const theme =
      param || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  })();
  </script>
  <style>
:root {
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 24px;
  background: var(--cp-bg);
  color: var(--cp-text);
  font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3 { margin: 0 0 12px; }
p { margin: 0 0 12px; color: var(--cp-text-muted); }
a { color: var(--cp-link); text-decoration: none; }
a:hover { text-decoration: underline; }
.layout { max-width: 1100px; margin: 0 auto; display: grid; gap: 16px; }
.card {
  background: var(--cp-surface);
  border: 1px solid var(--cp-border);
  border-radius: 16px;
  box-shadow: 0 0 2px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.14);
  padding: 16px;
}
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.diagram-grid { display: grid; gap: 10px; }
.diagram-row { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.diagram-node {
  border: 1px solid var(--cp-border);
  border-radius: 12px;
  background: var(--cp-surface-soft);
  padding: 10px;
  color: var(--cp-text);
  font-weight: 600;
}
.diagram-arrow {
  text-align: center;
  color: var(--cp-text-soft);
  font-size: 20px;
  line-height: 1;
}
.pill {
  display: inline-block;
  border: 1px solid var(--cp-border);
  background: var(--cp-surface-soft);
  color: var(--cp-text-muted);
  border-radius: 0.625rem;
  padding: 4px 8px;
  margin: 2px 6px 2px 0;
  font-size: 12px;
}
ul { margin: 0; padding-left: 20px; }
li { margin: 6px 0; color: var(--cp-text-muted); }
.matrix {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}
.matrix th, .matrix td {
  border: 1px solid var(--cp-border);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
  color: var(--cp-text-muted);
}
.matrix th {
  color: var(--cp-text);
  background: var(--cp-surface-soft);
}
code, pre, textarea {
  font-family: Consolas, "Courier New", Courier, monospace;
}
textarea {
  width: 100%;
  min-height: 280px;
  background: var(--cp-surface-soft);
  color: var(--cp-text);
  border: 1px solid var(--cp-border);
  border-radius: 0.625rem;
  padding: 12px;
  resize: vertical;
}
.btn {
  border: 1px solid var(--cp-accent);
  background: var(--cp-accent);
  color: var(--cp-accent-fg);
  border-radius: 0.625rem;
  padding: 8px 12px;
  cursor: pointer;
}
.btn:hover { background: var(--cp-accent-hover); border-color: var(--cp-accent-hover); }
  </style>
</head>
<body>
  <div class="layout">
    <div class="card">
      <h1>WaveSearch Labs: Indexing, Search, and Recommendations</h1>
      <p>This document explains how product data is indexed, how search and recommendations APIs are executed, and how the demo platform is composed and operated.</p>
      <span class="pill">Demo-only</span>
      <span class="pill">AKS dev overlay</span>
      <span class="pill">In-cluster Kaniko builds</span>
      <span class="pill">Zero-trust tokens via STS</span>
    </div>

    <div class="card">
      <h2>Architecture (runtime)</h2>
      <div class="grid">
        <div>
          <h3>Control Plane</h3>
          <ul>
            <li><strong>wave-sts</strong>: issues and validates audience-scoped JWT tokens.</li>
            <li><strong>wavesearch-frontend</strong>: operator UI for ingest, query tests, merchandising rules, and analytics.</li>
          </ul>
        </div>
        <div>
          <h3>Commerce Plane</h3>
          <ul>
            <li><strong>wavestore-erp-api</strong>: source of truth for products, stock, pricing, orders, and export catalog.</li>
            <li><strong>wavestore-frontend</strong>: shopper UI with basket module, checkout module, account module, and ERP order placement.</li>
          </ul>
        </div>
        <div>
          <h3>Search Plane</h3>
          <ul>
            <li><strong>wavesearch-api</strong>: indexing runtime, query API, recommendation API, events pipeline, and admin controls.</li>
            <li><strong>Ingress (nginx)</strong>: host/path routing through one shared public IP.</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Platform flow graphic</h2>
      <div class="diagram-grid">
        <div class="diagram-row">
          <div class="diagram-node">Shopper host: store.retail...</div>
          <div class="diagram-node">ERP host: erp.retail...</div>
          <div class="diagram-node">Labs host: labs.retail...</div>
        </div>
        <div class="diagram-arrow">↓</div>
        <div class="diagram-row">
          <div class="diagram-node">Shared ingress routing (host/path)</div>
        </div>
        <div class="diagram-arrow">↓</div>
        <div class="diagram-row">
          <div class="diagram-node">wave-sts (tokens, audience, scopes)</div>
          <div class="diagram-node">wavestore-erp-api (catalog/order truth)</div>
          <div class="diagram-node">wavesearch-api (index/query/recommend/events)</div>
        </div>
        <div class="diagram-arrow">↓</div>
        <div class="diagram-row">
          <div class="diagram-node">Runtime index + events overlay + analytics summary</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Modular integration boundaries</h2>
      <div class="grid">
        <div>
          <h3>Storefront modules</h3>
          <ul>
            <li><strong>Basket module</strong>: local basket state, quantity controls, totals, and checkout payload construction.</li>
            <li><strong>Checkout module</strong>: calls <code>POST /v2/checkout</code> and persists placed orders to account history.</li>
            <li><strong>Account module</strong>: sign-in via STS and order history via <code>GET /v2/account/orders</code>.</li>
            <li><strong>Promotions module</strong>: loads ERP offers via <code>GET /v2/offers</code>; banner click applies offer query/category/productIds and executes storefront search.</li>
          </ul>
        </div>
        <div>
          <h3>ERP modules</h3>
          <ul>
            <li><strong>Order module</strong>: <code>POST /erp/orders</code> validates items, prices from ERP pricing state, decrements stock, and creates invoice.</li>
            <li><strong>Catalog module</strong>: <code>/erp/products</code>, <code>/erp/stock</code>, <code>/erp/pricing</code>, <code>/erp/offers</code>, <code>/erp/export/catalog</code>.</li>
          </ul>
        </div>
        <div>
          <h3>Search modules</h3>
          <ul>
            <li><strong>Ingest module</strong>: <code>/search/ingest/from-erp</code> materializes catalog snapshots into runtime indexes.</li>
            <li><strong>Query module</strong>: <code>/search/query</code> handles retrieval + facets.</li>
            <li><strong>Merchandising module</strong>: <code>/search/admin/rules</code> applies boost/bury/pin controls at ranking time.</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>How indexing works</h2>
      <ul>
        <li>Catalog data originates in <code>wavestore-erp-api</code> and is exported via <code>/erp/export/catalog</code>.</li>
        <li>WaveSearch ingests via <code>POST /search/ingest/from-erp</code> with tenant and token context.</li>
        <li>The API snapshots product JSON and rebuilds in-memory runtime indexes for low-latency query and recommendation execution.</li>
        <li>Merchandising controls (boost/bury rules) are appended through admin APIs and applied at ranking time.</li>
      </ul>
    </div>

    <div class="card">
      <h2>Tech stack and how components fit together</h2>
      <table class="matrix">
        <thead>
          <tr><th>Layer</th><th>What is used</th><th>Role in result generation</th></tr>
        </thead>
        <tbody>
          <tr><td>Frontend GUIs</td><td>FastAPI + server-rendered HTML + Bootstrap-styled UI</td><td>Operator controls for ingest, rules, analytics, and simulation; storefront executes shopper search/browse journeys.</td></tr>
          <tr><td>API services</td><td>FastAPI (wave-sts, wavesearch-api, wavestore-erp-api, storefront)</td><td>STS secures each call, ERP supplies catalog truth, Search API serves query/recommend/events/admin flows.</td></tr>
          <tr><td>Search runtime</td><td>In-memory <code>CatalogRuntime</code> with tokenized postings lists, per-document term-frequency maps, doc-length stats, variant links, and live overlays</td><td>Builds low-latency candidate sets using in-memory token indexes, scores with BM25-style relevance math, applies merchandising/inventory signals, and returns ranked products + facet-ready metadata.</td></tr>
          <tr><td>State + telemetry</td><td>Catalog snapshot files, partitioned append logs (events/rules/inventory), runtime status overlays, and admin analytics summaries</td><td>Captures search/view/click activity and operator rule changes, preserves replayable history, and exposes feedback loops for relevance tuning and diagnostics.</td></tr>
          <tr><td>Deployment</td><td>AKS wave-dev, shared ingress, ACR images built for ARM</td><td>Hosts all components on one routed platform so APIs and UIs stay consistent end-to-end.</td></tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>How and what is used for ingestion and search</h2>
      <div class="grid">
        <div>
          <h3>Ingestion pipeline (source of truth to runtime)</h3>
          <ol>
            <li><strong>Catalog source:</strong> ERP exports product/stock/price data via <code>/erp/export/catalog</code>.</li>
            <li><strong>Ingestion trigger:</strong> Search API receives <code>POST /search/ingest/from-erp</code> (or <code>/search/ingest/catalog</code>) with tenant-scoped auth.</li>
            <li><strong>Snapshot stage:</strong> payload is written as a catalog snapshot JSON file for deterministic runtime rebuild input.</li>
            <li><strong>Runtime build:</strong> <code>RuntimeBuilder</code> parses products/variants into a new <code>CatalogRuntime</code> (products map, postings index, term frequencies, document lengths, variant graph).</li>
            <li><strong>Activation:</strong> rebuilt runtime is swapped in-memory and immediately serves query/recommend calls.</li>
          </ol>
        </div>
        <div>
          <h3>Search execution path (query to ranked results)</h3>
          <ol>
            <li><strong>Tokenization:</strong> query text is lowercased/tokenized into searchable terms.</li>
            <li><strong>Candidate retrieval:</strong> postings lists return candidate product IDs with matching terms.</li>
            <li><strong>Scoring:</strong> term frequency + document length + corpus frequency are combined (BM25-like) into relevance scores.</li>
            <li><strong>Tuning overlays:</strong> merchandising rules (boost/bury/pin), availability posture, and operator settings influence final rank.</li>
            <li><strong>Result shaping:</strong> response includes scored products and metadata used by storefront cards, facets, and browse rails.</li>
          </ol>
        </div>
        <div>
          <h3>Browse/recommend generation path</h3>
          <ol>
            <li><strong>Seed context:</strong> recommendation requests use a seed product and optional visitor context.</li>
            <li><strong>Similarity basis:</strong> overlap across category/brand/tag signals drives candidate relatedness.</li>
            <li><strong>Policy layer:</strong> merchandising and availability controls still apply, keeping recommendation behavior aligned with search posture.</li>
            <li><strong>Feedback loop:</strong> <code>/search/events</code> telemetry (search/view/click) informs operator decisions through analytics and simulation tools in the admin GUI.</li>
          </ol>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Search and recommendations APIs</h2>
      <div class="grid">
        <div>
          <h3>Search</h3>
          <ul>
            <li><code>POST /search/query</code> with query text, optional filters, and page size.</li>
            <li>Requires <code>search.query</code> scope.</li>
            <li>Returns ranked products with facets and metadata from indexed catalog fields.</li>
          </ul>
        </div>
        <div>
          <h3>Recommendations</h3>
          <ul>
            <li><code>POST /search/recommend</code> with <code>productId</code>, <code>visitorId</code>, and page size.</li>
            <li>Uses catalog relationships and behavior signals to produce related products.</li>
            <li>Also requires <code>search.query</code> scope.</li>
          </ul>
        </div>
        <div>
          <h3>Operational APIs</h3>
          <ul>
            <li><code>POST /search/events</code> for click/search telemetry ingestion.</li>
            <li><code>GET /search/admin/analytics</code> for click-through and usage summaries.</li>
            <li><code>POST /search/admin/rules</code> for boost/bury controls.</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>How results are generated (user-level view)</h2>
      <ul>
        <li><strong>Search:</strong> when a shopper types a query, WaveSearch finds matching products from the indexed catalog, applies in-stock and merchandising signals, then returns a ranked list.</li>
        <li><strong>Recommendations:</strong> when a shopper views a product or browses history, WaveSearch returns similar or related products using product relationships and behavior cues.</li>
        <li><strong>Facets:</strong> the system aggregates the matched set into facet buckets (such as category, brand, availability) so users can refine quickly.</li>
        <li><strong>Metadata:</strong> each result carries product fields from the index (title, description, price, inventory, brand/category/tags, image links) so UIs do not need extra lookup calls per card.</li>
        <li><strong>Clickstream:</strong> user actions (search, click, view) are ingested via <code>/search/events</code> and summarized for analytics and ranking tuning.</li>
      </ul>
    </div>

    <div class="card">
      <h2>How results are generated (implementation-level deep dive)</h2>
      <div class="grid">
        <div>
          <h3>Search ranking pipeline</h3>
          <ol>
            <li><strong>Candidate generation:</strong> tokenize query; retrieve candidate products from in-memory runtime indexes.</li>
            <li><strong>Base scoring:</strong> compute relevance score from term overlap / backend rank.</li>
            <li><strong>Merchandising adjustments:</strong> apply boost/bury/pin actions from admin rules.</li>
            <li><strong>Inventory adjustment:</strong> penalize out-of-stock and slightly uplift healthy in-stock items.</li>
            <li><strong>Filter + sort:</strong> apply category/brand/availability/price/stock filters and finalize ranking.</li>
          </ol>
        </div>
        <div>
          <h3>Facets and metadata return shape</h3>
          <ul>
            <li>Facets are computed from the final result set using indexed fields (category, brand, availability counters).</li>
            <li>Result documents include product metadata copied from indexed catalog snapshots plus overlayed stock/pricing context.</li>
            <li>This enables one response to populate cards, filters, and status badges in the storefront.</li>
          </ul>
          <h3>Recommendations pipeline</h3>
          <ul>
            <li>Input context: <code>productId</code> and optional visitor context.</li>
            <li>Candidate generation favors related categories/brands and known similarity relationships.</li>
            <li>Scoring reuses merchandising + availability controls so recommendations respect boost/bury and stock posture.</li>
          </ul>
        </div>
        <div>
          <h3>Clickstream ingestion and usage</h3>
          <ol>
            <li>Storefront posts events to <code>POST /search/events</code> (search, click, view, etc.).</li>
            <li>WaveSearch appends events to the tenant/partition append-log for durable replay and auditability.</li>
            <li>In-memory counters/analytics are updated and surfaced via <code>GET /search/admin/analytics</code>.</li>
            <li>Signals are used for operator decisions (boost/bury tuning, no-result diagnosis, promo effectiveness checks).</li>
            <li>On rebuild/recovery, durable snapshots + append logs can reconstruct state and analytics context.</li>
          </ol>
        </div>
      </div>

      <div class="card">
        <h2>Tuning levers: what influences search and browse results</h2>
        <table class="matrix">
          <thead>
            <tr><th>Lever</th><th>Effect on search/browse</th><th>Where to tune</th><th>Where visible in Search Admin GUI</th></tr>
          </thead>
          <tbody>
            <tr><td>Boost/Bury/Pin rules</td><td>Moves specific products up/down/fixed in ranked results and recommendation ordering.</td><td><code>POST /search/admin/rules</code></td><td><strong>Merchandising rules</strong> table + <strong>Rule editor</strong> modal.</td></tr>
            <tr><td>Catalog quality (title, description, categories, tags, brand)</td><td>Changes token matches, candidate generation, facet quality, and recommendation overlap.</td><td>ERP catalog data + <code>/search/ingest/from-erp</code></td><td><strong>Ingest from ERP</strong> action + query result detail modal for inspection.</td></tr>
            <tr><td>Inventory/availability posture</td><td>Out-of-stock can be penalized and in-stock items favored in ranking behavior.</td><td>ERP stock updates + ingest refresh</td><td>Result table and detail view after query/recommend runs.</td></tr>
            <tr><td>Behavior events (search/view/click)</td><td>Improves analytics feedback loop for rule and relevance tuning decisions.</td><td><code>POST /search/events</code></td><td><strong>Behavior simulation</strong> actions + <strong>Analytics</strong> panel.</td></tr>
            <tr><td>Query/recommend request parameters</td><td>Controls candidate scope and result set depth (for example page size, seed product).</td><td><code>/search/query</code>, <code>/search/recommend</code></td><td><strong>Query and recommendations</strong> controls (query, page size, seed product).</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h2>Key design assumptions</h2>
      <ul>
        <li>This environment is demo-only and deploys dev overlay replicas.</li>
        <li>All services are independently deployable but run as one logical platform behind shared ingress.</li>
        <li>Authentication is mandatory: bearer token + tenant header + audience/scope checks.</li>
        <li>For this ARM AKS cluster, images are built in-cluster with Kaniko and pushed to ACR.</li>
        <li>Ingress remains centralized: per-service hostnames route through the same ingress public IP.</li>
      </ul>
    </div>

    <div class="card">
      <h2>Pricing guide (estimate)</h2>
      <p>These are planning estimates for Azure-hosted AKS operation of this stack, focused on infrastructure (compute, storage, networking, observability), not engineering labor.</p>
      <table class="matrix">
        <thead>
          <tr><th>Profile</th><th>Typical footprint</th><th>Estimated monthly cost (USD)</th><th>Notes</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Demo / sandbox</td>
            <td>1 small ARM node pool, low replica counts, low ingest cadence</td>
            <td>$350 - $900</td>
            <td>Good for showcases and functional testing. Cost dominated by always-on AKS nodes and baseline monitoring.</td>
          </tr>
          <tr>
            <td>Pre-prod / pilot</td>
            <td>2-3 ARM nodes, moderate wavesearch-api replicas, daily ingestion</td>
            <td>$1,200 - $3,000</td>
            <td>Adds headroom for concurrency, resilience, and richer telemetry retention.</td>
          </tr>
          <tr>
            <td>Higher-scale multi-team</td>
            <td>Dedicated search node pool, autoscaling API replicas, heavy event volume</td>
            <td>$5,000 - $14,000+</td>
            <td>Network egress, log volume, and retention windows become significant cost drivers.</td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top:10px;"><strong>Main cost levers:</strong> replica count, node SKU, event volume retention, ingress/egress traffic, and observability sampling level.</p>
    </div>

    <div class="card">
      <h2>WaveSearch API benchmark estimate at scale</h2>
      <p>The values below are modeled from the current in-memory retrieval/scoring approach and are intended as sizing guidance before formal load testing.</p>
      <table class="matrix">
        <thead>
          <tr><th>Scale tier</th><th>Catalog size (products)</th><th>wavesearch-api replicas</th><th>Estimated query performance</th><th>Estimated recommend performance</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Small</td>
            <td>50k - 150k</td>
            <td>2</td>
            <td>p50 20-40ms, p95 70-140ms, ~200-450 req/s aggregate</td>
            <td>p50 10-25ms, p95 35-90ms, ~300-700 req/s aggregate</td>
          </tr>
          <tr>
            <td>Medium</td>
            <td>150k - 500k</td>
            <td>4</td>
            <td>p50 35-70ms, p95 120-260ms, ~350-900 req/s aggregate</td>
            <td>p50 18-45ms, p95 70-170ms, ~500-1,200 req/s aggregate</td>
          </tr>
          <tr>
            <td>Large</td>
            <td>500k - 1.5M</td>
            <td>6-8</td>
            <td>p50 60-130ms, p95 220-500ms, ~600-1,600 req/s aggregate</td>
            <td>p50 30-80ms, p95 120-300ms, ~800-2,000 req/s aggregate</td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top:10px;"><strong>Assumptions:</strong> warm runtime in memory, balanced tenant mix, token verification on, no cold-start rebuild in the request path, and standard ingress limits.</p>
      <p><strong>Recommended next step for precision:</strong> run k6/Locust load profiles against <code>/search/query</code>, <code>/search/recommend</code>, and <code>/search/events</code> with your real catalog shape and event mix, then tune replica autoscaling thresholds from observed p95 and CPU saturation.</p>
    </div>

    <div class="card">
      <h2>Prompt to rebuild the platform from scratch</h2>
      <p>Use this prompt with Copilot/agent mode to recreate the stack end-to-end:</p>
      <textarea id="rebuildPrompt" readonly>Build a demo-only enterprise retail search system (Vertex Retail Search equivalent behavior) on AKS using OSS components, with no Azure AI Search dependency.

Business intent:
- Showcase reusable demo architecture with clear service boundaries.
- Support dynamic facets, boost/bury merchandising, recommendations, and analytics.
- Run as a dev-only environment (no production store topology).

Create these six deployable services:
1) wave-sts (auth service): issue/validate short-lived JWTs with audience + scope enforcement.
2) wavestore-erp-api: source of truth for products, stock, pricing, offers, customers, orders, invoices; expose /erp/export/catalog.
3) wavesearch-api: ingest catalog from ERP; provide /search/query, /search/recommend, /search/events, /search/admin/*.
4) wavestore-frontend: shopper UI (Bootswatch style) for search, recs, basket, order placement.
5) wavestore-erp-frontend: WaveFunction/BareMetalJsTools style ERP admin GUI.
6) wavesearch-frontend: WaveFunction/BareMetalJsTools style search ops GUI + platform docs pages.

Functional requirements:
- Zero-trust everywhere: bearer token required, X-Tenant-Id required, tenant header/token match required.
- Enforce audience-scoped tokens and route-level scopes (no implicit admin bypass).
- Search supports keyword retrieval + facets + merchandising boost/bury controls.
- Recommendations endpoint supports product/visitor context and returns priced products.
- Events endpoint captures click/search telemetry; admin analytics endpoint summarizes behavior.
- ERP-to-search ingestion path: POST /search/ingest/from-erp using ERP export + token.

Platform and deployment constraints:
- AKS namespace: wave-dev only.
- Single shared ingress controller/public IP; host-based routing under retail.demos.wavefunctionlabs.com.
- Required hosts:
  store.retail.demos.wavefunctionlabs.com
  erp.retail.demos.wavefunctionlabs.com
  labs.retail.demos.wavefunctionlabs.com
  sts.retail.demos.wavefunctionlabs.com
  search-api.retail.demos.wavefunctionlabs.com
  erp-api.retail.demos.wavefunctionlabs.com
  orchestrator.retail.demos.wavefunctionlabs.com
- Build images in-cluster with Kaniko (ARM node compatible), push to ACR, then rollout.
- Do not rely on remote CI builds for demo deploys.

Documentation/UI deliverables:
- Demo orchestrator page linking all UIs and service endpoints, with architecture summary.
- Platform guide page explaining indexing flow, APIs, design assumptions, and rebuild prompt.
- README + deployment runbook with build/deploy/health/smoke commands.

Validation criteria:
- All six deployments healthy in wave-dev.
- Ingress routes live on shared IP.
- Search, recommend, ingest, analytics, and order flows callable end-to-end.
- Frontend style policy: Bootswatch for storefront/search page; WaveFunction style for other GUIs.</textarea>
      <div style="margin-top:12px;">
        <button class="btn" id="copyPrompt">Copy rebuild prompt</button>
      </div>
    </div>
  </div>
  <script>
    document.getElementById("copyPrompt").addEventListener("click", async () => {
      const el = document.getElementById("rebuildPrompt");
      try {
        await navigator.clipboard.writeText(el.value);
        alert("Prompt copied.");
      } catch {
        el.select();
        document.execCommand("copy");
        alert("Prompt copied.");
      }
    });
  </script>
</body>
</html>
"""


def orchestrator_html() -> str:
    return """<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Wave Retail Demo Orchestrator</title>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>
  <style>
    body { background: #f8f9fa; }
    .diagram-layer { border: 1px solid #dee2e6; border-radius: 0.5rem; padding: 0.75rem; background: #fff; }
    .node { border: 1px solid #dee2e6; border-radius: 0.5rem; padding: 0.5rem 0.75rem; background: #f8f9fa; }
    .arrow { text-align: center; color: #6c757d; font-weight: 700; }
    .flow-tree ul { margin-bottom: 0.5rem; }
    .flow-tree li { margin-bottom: 0.35rem; }
  </style>
</head>
<body>
<div class='container py-4'>
  <div class='mb-4'>
    <h1 class='display-6 mb-2'>Wave Retail Demo Orchestrator</h1>
    <p class='text-muted mb-2'>Entry points, service connectivity, and data flow across the retail demo platform.</p>
    <span class='badge text-bg-primary me-1'>Demo-only topology</span>
    <span class='badge text-bg-secondary me-1'>AKS wave-dev</span>
    <span class='badge text-bg-success me-1'>In-cluster ARM builds</span>
    <span class='badge text-bg-dark'>STS scoped JWTs</span>
  </div>

  <div class='card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5'>Entry points</h2>
      <div class='row g-3'>
        <div class='col-md-4'>
          <div class='node h-100'>
            <h3 class='h6'>Shopper</h3>
            <a href='https://store.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>store.retail.demos.wavefunctionlabs.com</a><br>
            <a href='https://storefront.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>storefront.retail.demos.wavefunctionlabs.com</a>
          </div>
        </div>
        <div class='col-md-4'>
          <div class='node h-100'>
            <h3 class='h6'>ERP admin</h3>
            <a href='https://erp.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>erp.retail.demos.wavefunctionlabs.com</a>
          </div>
        </div>
        <div class='col-md-4'>
          <div class='node h-100'>
            <h3 class='h6'>Search ops + docs</h3>
            <a href='https://labs.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>labs.retail.demos.wavefunctionlabs.com</a><br>
            <a href='https://orchestrator.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>orchestrator.retail.demos.wavefunctionlabs.com</a><br>
            <a href='/platform-guide' target='_blank' rel='noopener'>/platform-guide</a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class='card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5'>Entry-point and layer diagram</h2>
      <div class='diagram-layer mb-2'>
        <div class='row g-2'>
          <div class='col-md-4'><div class='node'>Storefront hosts</div></div>
          <div class='col-md-4'><div class='node'>ERP host</div></div>
          <div class='col-md-4'><div class='node'>Labs + Orchestrator hosts</div></div>
        </div>
      </div>
      <div class='arrow'>|</div>
      <div class='arrow'>v</div>
      <div class='diagram-layer mb-2'>
        <div class='node'>Shared ingress layer (nginx, host-based routing)</div>
      </div>
      <div class='arrow'>|</div>
      <div class='arrow'>v</div>
      <div class='diagram-layer mb-2'>
        <div class='row g-2'>
          <div class='col-md-4'><div class='node'>wavestore-frontend</div></div>
          <div class='col-md-4'><div class='node'>wavestore-erp-frontend</div></div>
          <div class='col-md-4'><div class='node'>wavesearch-frontend</div></div>
        </div>
      </div>
      <div class='arrow'>|</div>
      <div class='arrow'>v</div>
      <div class='diagram-layer mb-2'>
        <div class='row g-2'>
          <div class='col-md-4'><div class='node'>wave-sts</div></div>
          <div class='col-md-4'><div class='node'>wavestore-erp-api</div></div>
          <div class='col-md-4'><div class='node'>wavesearch-api</div></div>
        </div>
      </div>
      <div class='arrow'>|</div>
      <div class='arrow'>v</div>
      <div class='diagram-layer'>
        <div class='node'>Data/state layer: ERP catalog + orders, search runtime index, events/analytics overlays</div>
      </div>
    </div>
  </div>

  <div class='card shadow-sm mb-3'>
    <div class='card-body flow-tree'>
      <h2 class='h5'>Connection tree and data flow</h2>
      <ul>
        <li><strong>Entry hosts</strong>
          <ul>
            <li>store* -> wavestore-frontend -> /search, /erp, /sts routes</li>
            <li>erp -> wavestore-erp-frontend -> ERP API + STS</li>
            <li>labs/orchestrator -> wavesearch-frontend -> Search API + ERP API + STS</li>
          </ul>
        </li>
        <li><strong>Identity/auth</strong>
          <ul>
            <li>All frontends obtain scoped JWTs from wave-sts</li>
            <li>All backend routes enforce audience/scope + tenant headers</li>
          </ul>
        </li>
        <li><strong>Catalog and index lifecycle</strong>
          <ul>
            <li>wavestore-erp-api maintains product, stock, pricing, offer, order data</li>
            <li>wavesearch-api ingest pulls /erp/export/catalog and rebuilds runtime index</li>
            <li>Storefront query/recommend calls are served from the search runtime index</li>
          </ul>
        </li>
        <li><strong>Shopping and telemetry</strong>
          <ul>
            <li>Checkout path: storefront -> /v2/checkout -> ERP order placement/invoice</li>
            <li>Clickstream path: storefront -> /search/events -> analytics/ops feedback</li>
            <li>Ops path: labs -> /search/admin/* (rules, config, analytics)</li>
          </ul>
        </li>
      </ul>
    </div>
  </div>

  <div class='card shadow-sm'>
    <div class='card-body'>
      <h2 class='h5'>Service endpoint checks</h2>
      <div class='row g-3'>
        <div class='col-md-4'><a href='https://sts.retail.demos.wavefunctionlabs.com/healthz' target='_blank' rel='noopener'>STS health</a></div>
        <div class='col-md-4'><a href='https://search-api.retail.demos.wavefunctionlabs.com/healthz' target='_blank' rel='noopener'>Search API health</a></div>
        <div class='col-md-4'><a href='https://erp-api.retail.demos.wavefunctionlabs.com/healthz' target='_blank' rel='noopener'>ERP API health</a></div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""


def labs_html(sts: str, search_api: str, erp_api: str) -> str:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WaveSearch Labs Admin</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root {
      --cp-bg: #f5f1ff;
      --cp-surface: #ffffff;
      --cp-surface-soft: #f8f4ff;
      --cp-border: #d9cfef;
      --cp-border-strong: #b8a6dc;
      --cp-text: #1b1230;
      --cp-text-muted: #6a5f85;
      --cp-accent: #593196;
      --cp-accent-hover: #47267a;
      --cp-accent-2: #e06c00;
      --cp-nav: #2d0f5e;
      --cp-accent-fg: #ffffff;
      --cp-link: #593196;
      --cp-danger: #a91f40;
    }
    body {
      margin: 0;
      background: var(--cp-bg);
      color: var(--cp-text);
      font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .page-wrap { max-width: 1320px; margin: 0 auto; padding: 18px; }
    .glass {
      background: var(--cp-surface);
      border: 1px solid var(--cp-border);
      border-radius: 14px;
      box-shadow: 0 6px 24px rgba(45,15,94,.08);
    }
    .hero {
      background: linear-gradient(135deg, var(--cp-nav) 0%, var(--cp-accent) 55%, var(--cp-accent-2) 100%);
      color: #fff;
      border-radius: 16px;
      padding: 18px 20px;
      margin-bottom: 14px;
    }
    .hero .muted { color: rgba(255,255,255,.88); }
    .muted { color: var(--cp-text-muted); }
    .form-control, .form-select {
      background: var(--cp-surface-soft);
      border-color: var(--cp-border);
      color: var(--cp-text);
    }
    .form-control:focus, .form-select:focus {
      background: var(--cp-surface-soft);
      color: var(--cp-text);
      border-color: var(--cp-accent);
      box-shadow: 0 0 0 .2rem rgba(89,49,150,.18);
    }
    .btn-wave {
      border: 1px solid var(--cp-accent);
      background: var(--cp-accent);
      color: var(--cp-accent-fg);
      font-weight: 700;
    }
    .btn-wave:hover { background: var(--cp-accent-hover); border-color: var(--cp-accent-hover); color: #fff; }
    .btn-ghost {
      border: 1px solid var(--cp-accent);
      background: #fff;
      color: var(--cp-accent);
    }
    .btn-ghost:hover { background: var(--cp-surface-soft); border-color: var(--cp-accent-hover); color: var(--cp-accent-hover); }
    .table {
      --bs-table-bg: #fff;
      --bs-table-color: var(--cp-text);
      --bs-table-border-color: var(--cp-border);
      --bs-table-hover-bg: var(--cp-surface-soft);
    }
    .table thead th { background: var(--cp-surface-soft); color: var(--cp-text-muted); font-weight: 700; }
    .mono { font-family: Consolas, "Courier New", Courier, monospace; }
    .text-link { color: var(--cp-link); text-decoration: none; }
    .text-link:hover { text-decoration: underline; }
    .stat-pill {
      display: inline-block;
      border: 1px solid rgba(255,255,255,.5);
      background: rgba(255,255,255,.12);
      color: #fff;
      border-radius: 10px;
      padding: 4px 10px;
      font-size: .85rem;
      margin-right: 6px;
      margin-bottom: 6px;
    }
    .paging { display: flex; align-items: center; gap: 8px; }
    .lever-table td, .lever-table th { vertical-align: top; }
    .modal-content {
      background: var(--cp-surface);
      border: 1px solid var(--cp-border);
      color: var(--cp-text);
    }
    .modal-header, .modal-footer { border-color: var(--cp-border); }
    @media (max-width: 991.98px) { .page-wrap { padding: 12px; } }
  </style>
</head>
<body>
<div class="page-wrap">
  <div class="hero">
    <div class="d-flex flex-wrap justify-content-between align-items-start gap-3">
      <div>
        <h1 class="h3 mb-1">WaveSearch Labs Control Panel</h1>
        <p class="muted mb-2">Search ops, ingestion, merchandising rules, analytics, and simulation.</p>
        <a class="text-link" href="/platform-guide" target="_blank" rel="noopener">Open platform guide</a>
      </div>
      <div class="text-end">
        <div class="stat-pill">wavesearch-api</div>
        <div class="stat-pill">wavestore-erp-api</div>
        <div class="stat-pill">wave-sts</div>
      </div>
    </div>
  </div>

  <div class="glass p-3 mb-3">
    <div class="row g-2 align-items-end">
      <div class="col-lg-3"><label class="form-label mb-1">Tenant</label><input id="tenant" class="form-control" value="demo-tenant"></div>
      <div class="col-lg-3"><label class="form-label mb-1">User</label><input id="user" class="form-control" value="search.admin"></div>
      <div class="col-lg-3"><label class="form-label mb-1">Password</label><input id="password" class="form-control" value="demo123!" type="password"></div>
      <div class="col-lg-3 d-flex gap-2">
        <button id="signIn" class="btn btn-wave flex-grow-1">Sign in</button>
        <button id="signOut" class="btn btn-ghost flex-grow-1">Sign out</button>
      </div>
    </div>
    <div id="authState" class="muted small mt-2">Signed out</div>
  </div>

  <div class="row g-3">
    <div class="col-xl-7">
      <div class="glass p-3 h-100">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">Query and recommendations</h2>
          <button id="ingestFromErp" class="btn btn-sm btn-wave">Ingest from ERP</button>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-lg-7">
            <label class="form-label mb-1">Search query</label>
            <input id="query" class="form-control" value="jacket">
          </div>
          <div class="col-lg-2">
            <label class="form-label mb-1">Page size</label>
            <input id="pageSize" class="form-control" type="number" min="1" max="100" value="10">
          </div>
          <div class="col-lg-3 d-grid">
            <label class="form-label mb-1">&nbsp;</label>
            <button id="runQuery" class="btn btn-wave">Run query</button>
          </div>
          <div class="col-lg-7">
            <label class="form-label mb-1">Recommend seed product ID</label>
            <input id="recommendProductId" class="form-control" value="SKU-107">
          </div>
          <div class="col-lg-5 d-grid">
            <label class="form-label mb-1">&nbsp;</label>
            <button id="runRecommend" class="btn btn-ghost">Run recommend</button>
          </div>
        </div>
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h3 class="h6 mb-0">Results</h3>
          <div class="paging">
            <button id="resultsPrev" class="btn btn-sm btn-ghost">Prev</button>
            <span id="resultsPageInfo" class="small muted">Page 1</span>
            <button id="resultsNext" class="btn btn-sm btn-ghost">Next</button>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead><tr><th>Id</th><th>Title</th><th>Score</th><th class="text-end">Actions</th></tr></thead>
            <tbody id="resultsBody"><tr><td colspan="4" class="muted">No results yet.</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="col-xl-5">
      <div class="glass p-3 mb-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">Merchandising rules</h2>
          <div class="d-flex gap-2">
            <button id="loadConfig" class="btn btn-sm btn-ghost">Refresh</button>
            <button id="newRule" class="btn btn-sm btn-wave">New rule</button>
          </div>
        </div>
        <div class="d-flex justify-content-between align-items-center mb-2">
          <div class="small muted">Boost, bury, and pin controls (paged)</div>
          <div class="paging">
            <button id="rulesPrev" class="btn btn-sm btn-ghost">Prev</button>
            <span id="rulesPageInfo" class="small muted">Page 1</span>
            <button id="rulesNext" class="btn btn-sm btn-ghost">Next</button>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead><tr><th>Rule Id</th><th>Boost</th><th>Bury</th><th class="text-end">Actions</th></tr></thead>
            <tbody id="rulesBody"><tr><td colspan="4" class="muted">No rules loaded.</td></tr></tbody>
          </table>
        </div>
      </div>

      <div class="glass p-3 mb-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">Ranking and browse levers</h2>
          <a class="text-link small" href="/platform-guide" target="_blank" rel="noopener">Technical details</a>
        </div>
        <div class="table-responsive">
          <table class="table table-sm lever-table mb-0">
            <thead><tr><th>Lever</th><th>Primary control</th><th>Quick action</th></tr></thead>
            <tbody>
              <tr>
                <td>Boost/Bury/Pin merchandising</td>
                <td>Rule editor modal</td>
                <td><button id="openRuleEditorFromLevers" class="btn btn-sm btn-ghost">Open rule editor</button></td>
              </tr>
              <tr>
                <td>Catalog content and ingest freshness</td>
                <td>Ingest from ERP</td>
                <td><button id="runIngestFromLevers" class="btn btn-sm btn-ghost">Run ingest</button></td>
              </tr>
              <tr>
                <td>Behavior signals (search/view/click)</td>
                <td>Behavior simulation + events</td>
                <td><button id="runSimFromLevers" class="btn btn-sm btn-ghost">Simulate journey</button></td>
              </tr>
              <tr>
                <td>Ranking depth and candidate window</td>
                <td>Query text + page size + recommend seed</td>
                <td><button id="runQueryFromLevers" class="btn btn-sm btn-ghost">Run query</button></td>
              </tr>
              <tr>
                <td>Tuning feedback loop</td>
                <td>Analytics and config review</td>
                <td><button id="loadAnalyticsFromLevers" class="btn btn-sm btn-ghost">Load analytics</button></td>
              </tr>
              <tr>
                <td>Explainability / pre-post AI comparison</td>
                <td>Search Explorer diagnostics table</td>
                <td><button id="viewDiagnosticsFromLevers" class="btn btn-sm btn-ghost">View diagnostics</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="glass p-3 mb-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">Behavior simulation</h2>
          <button id="simulateBrowse" class="btn btn-sm btn-wave">Simulate browse journey</button>
        </div>
        <div class="row g-2">
          <div class="col-md-6"><label class="form-label mb-1">Visitor id</label><input id="simVisitorId" class="form-control" value="demo-visitor-01"></div>
          <div class="col-md-6"><label class="form-label mb-1">Search text</label><input id="simSearchText" class="form-control" value="jacket"></div>
          <div class="col-md-8"><label class="form-label mb-1">Clicked product id</label><input id="simProductId" class="form-control" value="SKU-107"></div>
          <div class="col-md-4 d-grid"><label class="form-label mb-1">&nbsp;</label><button id="simulateClick" class="btn btn-ghost">Simulate click</button></div>
        </div>
      </div>

      <div class="glass p-3 mb-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">AI harness (Azure Foundry)</h2>
          <button id="refreshAiToggle" class="btn btn-sm btn-ghost">Refresh status</button>
        </div>
        <div id="aiToggleUnavailable" class="alert alert-warning py-2 px-3 small mb-2 d-none">Foundry endpoint is not configured on this deployment.</div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" role="switch" id="aiRerankToggle">
          <label class="form-check-label small" for="aiRerankToggle">LLM reranking (can add latency per query)</label>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" role="switch" id="aiIntentToggle">
          <label class="form-check-label small" for="aiIntentToggle">Query intent classification</label>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" role="switch" id="aiVectorToggle">
          <label class="form-check-label small" for="aiVectorToggle">Hybrid vector search (lexical + embedding RRF fusion)</label>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" role="switch" id="aiEnrichToggle">
          <label class="form-check-label small" for="aiEnrichToggle">LLM catalog enrichment at ingest (synonyms/use-cases baked into the index, not per query)</label>
        </div>
        <div id="aiToggleStatus" class="small muted">Sign in and refresh to view current state.</div>
      </div>

      <div class="glass p-3 mb-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">Query redirects</h2>
          <button id="refreshRedirects" class="btn btn-sm btn-ghost">Refresh</button>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-md-4"><input id="redirectQuery" class="form-control form-control-sm" placeholder="Trigger query, e.g. summer sale"></div>
          <div class="col-md-4"><input id="redirectUrl" class="form-control form-control-sm" placeholder="/collections/summer-sale"></div>
          <div class="col-md-3"><input id="redirectLabel" class="form-control form-control-sm" placeholder="Label (optional)"></div>
          <div class="col-md-1 d-grid"><button id="saveRedirect" class="btn btn-sm btn-wave">Add</button></div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead><tr><th>Query</th><th>Target URL</th><th>Label</th><th class="text-end">Actions</th></tr></thead>
            <tbody id="redirectsBody"><tr><td colspan="4" class="muted">No redirects loaded.</td></tr></tbody>
          </table>
        </div>
      </div>

      <div class="glass p-3 mb-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">Ranking objective</h2>
          <button id="refreshObjective" class="btn btn-sm btn-ghost">Refresh</button>
        </div>
        <p class="small muted mb-2">What should ranking optimize for, tenant-wide, on top of relevance? Built from real logged view/click/purchase events (Reciprocal Rank Fusion against the relevance order -- nudges, doesn't fully override).</p>
        <div class="d-flex gap-2 mb-2">
          <select id="objectiveSelect" class="form-select form-select-sm" style="max-width:220px;">
            <option value="relevance">Relevance (default)</option>
            <option value="ctr">Click-through rate</option>
            <option value="conversion">Conversion rate</option>
            <option value="revenue">Revenue</option>
          </select>
          <button id="saveObjective" class="btn btn-sm btn-wave">Apply</button>
        </div>
        <div id="objectiveStatus" class="small muted mb-2">Sign in and refresh to view current state.</div>
        <div id="mlModelStatus" class="small muted mb-2">ML model status will appear here after refresh.</div>
        <div class="d-flex gap-2 mb-2">
          <button id="resetMlModel" class="btn btn-sm btn-ghost">Reset ML model</button>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead><tr><th>Product</th><th>Views</th><th>Clicks</th><th>Purchases</th><th>CTR</th><th>Conv.</th><th>Revenue</th></tr></thead>
            <tbody id="objectiveStatsBody"><tr><td colspan="7" class="muted">No performance data loaded.</td></tr></tbody>
          </table>
        </div>
      </div>

      <div class="glass p-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h5 mb-0">Analytics</h2>
          <button id="loadAnalytics" class="btn btn-sm btn-ghost">Load analytics</button>
        </div>
        <div class="table-responsive">
          <table class="table table-sm mb-0">
            <tbody id="analyticsBody"><tr><td class="muted">No analytics loaded.</td></tr></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <div class="glass p-3 mt-3">
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h2 class="h5 mb-0">Search Explorer — pre/post AI diagnostics</h2>
      <button id="refreshDiagnostics" class="btn btn-sm btn-ghost">Refresh</button>
    </div>
    <div class="d-flex justify-content-between align-items-center mb-2">
      <div class="small muted">Every <span class="mono">/search/query</span> call is recorded with its lexical (pre-AI) order and final (post-AI) order so you can inspect exactly what the reranker and intent classifier changed.</div>
      <div class="paging">
        <button id="diagnosticsPrev" class="btn btn-sm btn-ghost">Prev</button>
        <span id="diagnosticsPageInfo" class="small muted">Page 1</span>
        <button id="diagnosticsNext" class="btn btn-sm btn-ghost">Next</button>
      </div>
    </div>
    <div class="table-responsive">
      <table class="table table-sm align-middle mb-0">
        <thead><tr><th>Time</th><th>Query</th><th>Results</th><th>Rerank</th><th>Intent</th><th>Order changed</th><th class="text-end">Actions</th></tr></thead>
        <tbody id="diagnosticsBody"><tr><td colspan="7" class="muted">No searches recorded yet. Run a query to populate this list.</td></tr></tbody>
      </table>
    </div>
  </div>

  <div class="glass p-3 mt-3">
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h2 class="h5 mb-0">API output / console</h2>
      <button id="clearOutput" class="btn btn-sm btn-ghost">Clear</button>
    </div>
    <pre id="out" class="mono mb-0" style="max-height:260px;overflow:auto;background:#111;border:1px solid var(--cp-border);border-radius:12px;padding:10px;color:#ddd;"></pre>
  </div>
</div>

<div class="modal fade" id="ruleModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Rule editor</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <div id="ruleValidation" class="alert alert-danger d-none mb-3"></div>
        <div class="row g-2">
          <div class="col-md-6"><label class="form-label">Rule id</label><input id="ruleId" class="form-control" placeholder="boost-wave-enterprise"></div>
          <div class="col-md-6"><label class="form-label">Partition key (optional)</label><input id="rulePartition" class="form-control" placeholder="default"></div>
          <div class="col-12"><label class="form-label">Boost product IDs (comma separated)</label><input id="ruleBoost" class="form-control" placeholder="SKU-107,SKU-108"></div>
          <div class="col-12"><label class="form-label">Bury product IDs (comma separated)</label><input id="ruleBury" class="form-control" placeholder="SKU-LOW-001"></div>
          <div class="col-12"><label class="form-label">Pin product IDs (comma separated)</label><input id="rulePin" class="form-control" placeholder="SKU-HERO-001"></div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-ghost" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-wave" id="saveRuleModal">Save rule</button>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="resultModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-xl modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Result details</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <pre id="resultDetail" class="mono mb-0" style="min-height:200px;background:#111;border:1px solid var(--cp-border);border-radius:12px;padding:10px;color:#ddd;"></pre>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="diagnosticModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-xl modal-dialog-scrollable">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Search diagnostic: before/after AI transformation</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <div id="diagnosticMeta" class="small muted mb-3"></div>
        <div class="row g-3">
          <div class="col-md-6">
            <h3 class="h6">Before AI (lexical/BM25 order)</h3>
            <div class="table-responsive">
              <table class="table table-sm align-middle mb-0">
                <thead><tr><th>#</th><th>Id</th><th>Title</th><th>Score</th></tr></thead>
                <tbody id="diagnosticPreBody"></tbody>
              </table>
            </div>
          </div>
          <div class="col-md-6">
            <h3 class="h6">After AI (final order)</h3>
            <div class="table-responsive">
              <table class="table table-sm align-middle mb-0">
                <thead><tr><th>#</th><th>Id</th><th>Title</th><th>Score</th><th>Rank Δ</th></tr></thead>
                <tbody id="diagnosticPostBody"></tbody>
              </table>
            </div>
          </div>
        </div>
        <div id="diagnosticAiDetail" class="mt-3"></div>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
const cfg = { sts: "__STS__", search: "__SEARCH__", erp: "__ERP__" };
const state = { searchToken: "", erpToken: "", signedIn: false, rules: [], rulesPage: 1, rulesPageSize: 8, results: [], resultsPage: 1, resultsPageSize: 8, diagnostics: [], diagnosticsPage: 1, diagnosticsPageSize: 8 };
const el = (id) => document.getElementById(id);
const ruleModal = new bootstrap.Modal(el("ruleModal"));
const resultModal = new bootstrap.Modal(el("resultModal"));
const diagnosticModal = new bootstrap.Modal(el("diagnosticModal"));

function parseJsonSafe(text) { try { return JSON.parse(text); } catch { return null; } }
function toList(value) { if (!value) return []; if (Array.isArray(value)) return value.map(String).filter(Boolean); return String(value).split(",").map(v => v.trim()).filter(Boolean); }
function page(items, pageNumber, size) { const totalPages = Math.max(1, Math.ceil(items.length / size)); const pageSafe = Math.min(Math.max(1, pageNumber), totalPages); const start = (pageSafe - 1) * size; return { pageSafe, totalPages, rows: items.slice(start, start + size) }; }
function setAuthState(msg, ok = false) { const node = el("authState"); node.textContent = msg; node.className = ok ? "small text-success mt-2" : "small muted mt-2"; }
function writeOut(label, payload) { const text = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2); el("out").textContent = `[${new Date().toLocaleTimeString()}] ${label}\\n${text}\\n\\n` + el("out").textContent; }
function readTenant() { return (el("tenant").value || "demo-tenant").trim() || "demo-tenant"; }
function requireSignIn() { if (!state.searchToken || !state.erpToken) throw new Error("Sign in first."); }
function authHeaders(withPartition = false) { const headers = { "Content-Type": "application/json", "Authorization": `Bearer ${state.searchToken}`, "X-Tenant-Id": readTenant() }; if (withPartition) { const key = (el("rulePartition").value || "").trim(); if (key) headers["X-Retail-Partition-Key"] = key; } return headers; }

async function callJson(url, method = "GET", body = null, headers = {}) {
  const resp = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : null });
  const text = await resp.text();
  const data = parseJsonSafe(text) || text;
  if (!resp.ok) {
    const detail = typeof data === "object" && data ? (data.detail || data.error || JSON.stringify(data)) : String(data);
    throw new Error(`${resp.status} ${detail}`);
  }
  return data;
}
function normalizeRules(configPayload) {
  if (!configPayload || typeof configPayload !== "object") return [];
  if (Array.isArray(configPayload.rules)) return configPayload.rules.filter(r => r && typeof r === "object");
  const candidates = [];
  for (const value of Object.values(configPayload)) {
    if (Array.isArray(value)) {
      for (const item of value) if (item && typeof item === "object" && (item.id || item.actions)) candidates.push(item);
    } else if (value && typeof value === "object" && (value.id || value.actions)) {
      candidates.push(value);
    }
  }
  return candidates;
}
function renderRules() {
  const body = el("rulesBody");
  const p = page(state.rules, state.rulesPage, state.rulesPageSize);
  state.rulesPage = p.pageSafe;
  el("rulesPageInfo").textContent = `Page ${p.pageSafe} / ${p.totalPages} (${state.rules.length})`;
  if (!p.rows.length) { body.innerHTML = '<tr><td colspan="4" class="muted">No rules loaded.</td></tr>'; return; }
  body.innerHTML = p.rows.map((rule, idx) => {
    const id = String(rule.id || `rule-${idx + 1}`);
    const actions = rule.actions || {};
    const boost = Array.isArray(actions.boost) ? actions.boost.length : 0;
    const bury = Array.isArray(actions.bury) ? actions.bury.length : 0;
    const rowIndex = (p.pageSafe - 1) * state.rulesPageSize + idx;
    return `<tr><td class="mono">${id}</td><td>${boost}</td><td>${bury}</td><td class="text-end"><button class="btn btn-sm btn-ghost" data-rule-index="${rowIndex}">Edit</button></td></tr>`;
  }).join("");
  body.querySelectorAll("button[data-rule-index]").forEach(btn => btn.addEventListener("click", () => openRuleModal(Number(btn.dataset.ruleIndex))));
}
function renderResults() {
  const body = el("resultsBody");
  const p = page(state.results, state.resultsPage, state.resultsPageSize);
  state.resultsPage = p.pageSafe;
  el("resultsPageInfo").textContent = `Page ${p.pageSafe} / ${p.totalPages} (${state.results.length})`;
  if (!p.rows.length) { body.innerHTML = '<tr><td colspan="4" class="muted">No results yet.</td></tr>'; return; }
  body.innerHTML = p.rows.map((row, idx) => {
    const id = String(row.id || row.product?.id || "-");
    const title = String(row.title || row.product?.title || "-");
    const score = row.score ?? "-";
    const rowIndex = (p.pageSafe - 1) * state.resultsPageSize + idx;
    return `<tr><td class="mono">${id}</td><td>${title}</td><td>${score}</td><td class="text-end"><button class="btn btn-sm btn-ghost" data-result-index="${rowIndex}">View</button></td></tr>`;
  }).join("");
  body.querySelectorAll("button[data-result-index]").forEach(btn => {
    btn.addEventListener("click", () => {
      const row = state.results[Number(btn.dataset.resultIndex)];
      el("resultDetail").textContent = JSON.stringify(row, null, 2);
      resultModal.show();
    });
  });
}
function renderAnalytics(data) {
  const body = el("analyticsBody");
  if (!data || typeof data !== "object") { body.innerHTML = '<tr><td class="muted">No analytics loaded.</td></tr>'; return; }
  const rows = Object.entries(data);
  if (!rows.length) { body.innerHTML = '<tr><td class="muted">No analytics entries.</td></tr>'; return; }
  body.innerHTML = rows.map(([k, v]) => `<tr><th class="mono" style="width:40%;">${k}</th><td class="mono">${typeof v === "object" ? JSON.stringify(v) : String(v)}</td></tr>`).join("");
}
function renderDiagnostics() {
  const body = el("diagnosticsBody");
  const p = page(state.diagnostics, state.diagnosticsPage, state.diagnosticsPageSize);
  state.diagnosticsPage = p.pageSafe;
  el("diagnosticsPageInfo").textContent = `Page ${p.pageSafe} / ${p.totalPages} (${state.diagnostics.length})`;
  if (!p.rows.length) { body.innerHTML = '<tr><td colspan="7" class="muted">No searches recorded yet. Run a query to populate this list.</td></tr>'; return; }
  body.innerHTML = p.rows.map(item => {
    const time = String(item.timestamp || "").replace("T", " ").replace("Z", "");
    const queryText = item.query ? item.query : "(empty)";
    return `<tr>
      <td class="small mono">${time}</td>
      <td class="mono">${queryText}</td>
      <td>${item.resultCount ?? "-"}</td>
      <td>${item.rerankApplied ? "Applied" : "—"}</td>
      <td>${item.intentApplied ? "Applied" : "—"}</td>
      <td>${item.orderChanged ? "Yes" : "No"}</td>
      <td class="text-end"><button class="btn btn-sm btn-ghost" data-diagnostic-id="${item.id}">Compare</button></td>
    </tr>`;
  }).join("");
  body.querySelectorAll("button[data-diagnostic-id]").forEach(btn => {
    btn.addEventListener("click", () => openDiagnosticModal(btn.dataset.diagnosticId));
  });
}
async function loadDiagnostics() {
  requireSignIn();
  const data = await callJson(cfg.search + "/search/admin/diagnostics?limit=100", "GET", null, authHeaders());
  state.diagnostics = Array.isArray(data.diagnostics) ? data.diagnostics : [];
  state.diagnosticsPage = 1;
  renderDiagnostics();
  writeOut("search/admin/diagnostics", data);
}
async function openDiagnosticModal(diagnosticId) {
  try {
    requireSignIn();
    const data = await callJson(cfg.search + "/search/admin/diagnostics/" + encodeURIComponent(diagnosticId), "GET", null, authHeaders());
    const entry = data.diagnostic || {};
    const pre = Array.isArray(entry.preResults) ? entry.preResults : [];
    const post = Array.isArray(entry.postResults) ? entry.postResults : [];
    const preIndexById = new Map(pre.map((row, idx) => [row.id, idx]));
    const timeText = String(entry.timestamp || "").replace("T", " ").replace("Z", "");
    el("diagnosticMeta").innerHTML = `
      <div><strong>Query:</strong> <span class="mono">${entry.query || "(empty)"}</span> &nbsp; <strong>Time:</strong> ${timeText}</div>
      <div><strong>Filters:</strong> <span class="mono">${JSON.stringify(entry.filters || {})}</span></div>
    `;
    el("diagnosticPreBody").innerHTML = pre.length
      ? pre.map((row, idx) => `<tr><td>${idx + 1}</td><td class="mono">${row.id}</td><td>${row.title}</td><td>${row.score ?? "-"}</td></tr>`).join("")
      : '<tr><td colspan="4" class="muted">No results.</td></tr>';
    el("diagnosticPostBody").innerHTML = post.length
      ? post.map((row, idx) => {
          const originalIndex = preIndexById.has(row.id) ? preIndexById.get(row.id) : null;
          let delta = '<span class="muted">new</span>';
          if (originalIndex !== null) {
            const diff = originalIndex - idx;
            if (diff > 0) delta = `<span class="text-success">up ${diff}</span>`;
            else if (diff < 0) delta = `<span class="text-danger">down ${Math.abs(diff)}</span>`;
            else delta = '<span class="muted">unchanged</span>';
          }
          return `<tr><td>${idx + 1}</td><td class="mono">${row.id}</td><td>${row.title}</td><td>${row.score ?? "-"}</td><td>${delta}</td></tr>`;
        }).join("")
      : '<tr><td colspan="5" class="muted">No results.</td></tr>';
    const ai = entry.ai || {};
    const rerank = ai.rerank || {};
    const intent = ai.intent || {};
    el("diagnosticAiDetail").innerHTML = `
      <h3 class="h6">AI transformation detail</h3>
      <div class="small">
        <strong>Rerank:</strong> enabled=${Boolean(rerank.enabled)}, applied=${Boolean(rerank.applied)}${rerank.error ? `, error=${rerank.error}` : ""}
        ${rerank.rationale ? `<br>Rationale: ${rerank.rationale}` : ""}
      </div>
      <div class="small mt-2">
        <strong>Intent:</strong> enabled=${Boolean(intent.enabled)}, applied=${Boolean(intent.applied)}${intent.intent ? `, intent=${intent.intent} (confidence ${intent.confidence})` : ""}${intent.error ? `, error=${intent.error}` : ""}
        ${intent.notes ? `<br>Notes: ${intent.notes}` : ""}
      </div>
    `;
    diagnosticModal.show();
  } catch (err) {
    writeOut("diagnostic.error", String(err));
  }
}
function openRuleModal(index = null) {
  el("ruleValidation").classList.add("d-none");
  const source = index === null ? {} : (state.rules[index] || {});
  const actions = source.actions || {};
  el("ruleId").value = source.id || "";
  el("rulePartition").value = source.partitionKey || "";
  el("ruleBoost").value = (actions.boost || []).map(x => x.productId).filter(Boolean).join(",");
  el("ruleBury").value = (actions.bury || []).map(x => x.productId).filter(Boolean).join(",");
  el("rulePin").value = (actions.pin || []).map(x => x.productId).filter(Boolean).join(",");
  ruleModal.show();
}
function buildRulePayload() {
  const id = (el("ruleId").value || "").trim();
  if (!id) throw new Error("Rule id is required.");
  const boost = toList(el("ruleBoost").value).map(productId => ({ productId }));
  const bury = toList(el("ruleBury").value).map(productId => ({ productId }));
  const pin = toList(el("rulePin").value).map(productId => ({ productId }));
  const actions = {};
  if (boost.length) actions.boost = boost;
  if (bury.length) actions.bury = bury;
  if (pin.length) actions.pin = pin;
  return { id, actions };
}

async function signIn() {
  const tenant = readTenant();
  const username = (el("user").value || "").trim();
  const password = el("password").value || "";
  if (!username || !password) throw new Error("Username and password are required.");
  const tokenReq = await callJson(cfg.sts + "/sts/login", "POST", { audience: "wavesearch-api", tenant, username, password, scopes: ["search.query", "search.admin", "search.ingest", "events.write"] }, { "Content-Type": "application/json", "X-Tenant-Id": tenant });
  const erpReq = await callJson(cfg.sts + "/sts/login", "POST", { audience: "wavestore-erp-api", tenant, username, password, scopes: ["erp.export", "erp.read"] }, { "Content-Type": "application/json", "X-Tenant-Id": tenant });
  state.searchToken = String(tokenReq.access_token || "");
  state.erpToken = String(erpReq.access_token || "");
  state.signedIn = Boolean(state.searchToken && state.erpToken);
  setAuthState(state.signedIn ? `Signed in as ${username}` : "Sign in failed", state.signedIn);
  writeOut("auth", { signedIn: state.signedIn, tenant, username });
}
function signOut() { state.searchToken = ""; state.erpToken = ""; state.signedIn = false; setAuthState("Signed out"); }
async function ingestFromErp() { requireSignIn(); const data = await callJson(cfg.search + "/search/ingest/from-erp", "POST", { erpCatalogUrl: cfg.erp + "/erp/export/catalog", erpToken: state.erpToken }, authHeaders()); writeOut("ingest/from-erp", data); }
async function runQuery() { requireSignIn(); const query = (el("query").value || "").trim(); const pageSize = Math.max(1, Number(el("pageSize").value || 10)); const data = await callJson(cfg.search + "/search/query", "POST", { query, pageSize }, authHeaders()); state.results = Array.isArray(data.results) ? data.results : []; state.resultsPage = 1; renderResults(); writeOut("search/query", data); try { await loadDiagnostics(); } catch { /* best-effort refresh */ } }
async function runRecommend() { requireSignIn(); const productId = (el("recommendProductId").value || "").trim(); const pageSize = Math.max(1, Number(el("pageSize").value || 10)); const data = await callJson(cfg.search + "/search/recommend", "POST", { productId, pageSize }, authHeaders()); state.results = Array.isArray(data.results) ? data.results : []; state.resultsPage = 1; renderResults(); writeOut("search/recommend", data); }
async function loadConfig() {
  requireSignIn();
  const data = await callJson(cfg.search + "/search/admin/config", "GET", null, authHeaders());
  state.rules = normalizeRules(data);
  state.rulesPage = 1;
  renderRules();
  applyAiToggleState(data.ai);
  writeOut("search/admin/config", data);
}
async function loadAnalytics() { requireSignIn(); const data = await callJson(cfg.search + "/search/admin/analytics", "GET", null, authHeaders()); renderAnalytics(data); writeOut("search/admin/analytics", data); }
function renderRedirects(rows) {
  const body = el("redirectsBody");
  if (!body) return;
  if (!rows || !rows.length) { body.innerHTML = '<tr><td colspan="4" class="muted">No redirects loaded.</td></tr>'; return; }
  body.innerHTML = rows.map(r => `<tr><td class="mono">${r.query}</td><td class="mono">${r.url}</td><td>${r.label || ""}</td><td class="text-end"><button class="btn btn-sm btn-ghost redirect-delete" data-query="${r.query}">Remove</button></td></tr>`).join("");
  body.querySelectorAll(".redirect-delete").forEach(btn => {
    btn.addEventListener("click", () => deleteRedirect(btn.dataset.query).catch(err => writeOut("redirects.error", String(err))));
  });
}
async function loadRedirects() {
  requireSignIn();
  const data = await callJson(cfg.search + "/search/admin/redirects", "GET", null, authHeaders());
  renderRedirects(data.redirects || []);
  writeOut("search/admin/redirects", data);
}
async function saveRedirect() {
  requireSignIn();
  const query = (el("redirectQuery").value || "").trim();
  const url = (el("redirectUrl").value || "").trim();
  const label = (el("redirectLabel").value || "").trim();
  if (!query || !url) { writeOut("redirects.error", "query and url are required"); return; }
  const data = await callJson(cfg.search + "/search/admin/redirects", "POST", { query, url, label }, authHeaders());
  el("redirectQuery").value = ""; el("redirectUrl").value = ""; el("redirectLabel").value = "";
  await loadRedirects();
  writeOut("search/admin/redirects.save", data);
}
async function deleteRedirect(query) {
  requireSignIn();
  const data = await callJson(cfg.search + "/search/admin/redirects/" + encodeURIComponent(query), "DELETE", null, authHeaders());
  await loadRedirects();
  writeOut("search/admin/redirects.delete", data);
}
function renderObjectiveStats(rows) {
  const body = el("objectiveStatsBody");
  if (!body) return;
  if (!rows || !rows.length) { body.innerHTML = '<tr><td colspan="7" class="muted">No performance data loaded.</td></tr>'; return; }
  body.innerHTML = rows.map(r => `<tr><td>${r.title}</td><td>${r.views}</td><td>${r.clicks}</td><td>${r.purchases}</td><td>${(r.ctr * 100).toFixed(1)}%</td><td>${(r.conversionRate * 100).toFixed(1)}%</td><td>$${r.revenue}</td></tr>`).join("");
}
function renderMlModelStatus(model) {
  const target = el("mlModelStatus");
  if (!target) return;
  const objectives = model.objectives || {};
  const parts = Object.keys(objectives).map(name => {
    const m = objectives[name];
    const badge = m.ready ? "ready (ML-driven)" : `warming up (${m.eventsTrained}/${model.minEventsForMl} events, heuristic fallback)`;
    return `${name}: ${badge}`;
  });
  target.textContent = `ML model -- ${parts.join(" | ")}`;
}
async function loadRankingObjective() {
  requireSignIn();
  const data = await callJson(cfg.search + "/search/admin/ranking-objective", "GET", null, authHeaders());
  if (el("objectiveSelect")) el("objectiveSelect").value = data.objective || "relevance";
  if (el("objectiveStatus")) el("objectiveStatus").textContent = `Current objective: ${data.objective}`;
  const stats = await callJson(cfg.search + "/search/admin/product-performance?limit=20", "GET", null, authHeaders());
  renderObjectiveStats(stats.products || []);
  const model = await callJson(cfg.search + "/search/admin/ml-model", "GET", null, authHeaders());
  renderMlModelStatus(model);
  writeOut("search/admin/ranking-objective", data);
}
async function saveRankingObjective() {
  requireSignIn();
  const objective = el("objectiveSelect").value;
  const data = await callJson(cfg.search + "/search/admin/ranking-objective", "POST", { objective }, authHeaders());
  if (el("objectiveStatus")) el("objectiveStatus").textContent = `Current objective: ${data.objective}`;
  writeOut("search/admin/ranking-objective.save", data);
}
async function resetMlModel() {
  requireSignIn();
  const data = await callJson(cfg.search + "/search/admin/ml-model/reset", "POST", {}, authHeaders());
  await loadRankingObjective();
  writeOut("search/admin/ml-model.reset", data);
}
function applyAiToggleState(ai) {
  const unavailable = el("aiToggleUnavailable");
  const rerankToggle = el("aiRerankToggle");
  const intentToggle = el("aiIntentToggle");
  const vectorToggle = el("aiVectorToggle");
  const enrichToggle = el("aiEnrichToggle");
  const statusEl = el("aiToggleStatus");
  if (!ai) { if (statusEl) statusEl.textContent = "AI status unavailable."; return; }
  const available = Boolean(ai.available);
  const vectorAvailable = Boolean(ai.vectorAvailable);
  if (unavailable) unavailable.classList.toggle("d-none", available);
  if (rerankToggle) { rerankToggle.checked = Boolean(ai.rerankEnabled); rerankToggle.disabled = !available; }
  if (intentToggle) { intentToggle.checked = Boolean(ai.intentEnabled); intentToggle.disabled = !available; }
  if (vectorToggle) { vectorToggle.checked = Boolean(ai.vectorEnabled); vectorToggle.disabled = !vectorAvailable; }
  if (enrichToggle) { enrichToggle.checked = Boolean(ai.enrichEnabled); enrichToggle.disabled = !available; }
  if (statusEl) {
    statusEl.textContent = available
      ? `Foundry available. Rerank ${ai.rerankEnabled ? "ON" : "OFF"}, Intent ${ai.intentEnabled ? "ON" : "OFF"}, Vector ${ai.vectorEnabled ? "ON" : "OFF"} (index: ${ai.vectorIndexSize || 0} products), Enrich-at-ingest ${ai.enrichEnabled ? "ON" : "OFF"}.`
      : "Foundry endpoint is not configured on this deployment.";
  }
}
async function toggleAi(field, checked) {
  requireSignIn();
  const payload = field === "rerank" ? { rerankEnabled: checked } : field === "intent" ? { intentEnabled: checked } : field === "vector" ? { vectorEnabled: checked } : { enrichEnabled: checked };
  const data = await callJson(cfg.search + "/search/admin/ai-toggle", "POST", payload, authHeaders());
  applyAiToggleState({ available: data.available, rerankEnabled: data.rerankEnabled, intentEnabled: data.intentEnabled, vectorEnabled: data.vectorEnabled, vectorAvailable: data.vectorAvailable, vectorIndexSize: data.vectorIndexSize, enrichEnabled: data.enrichEnabled });
  writeOut("search/admin/ai-toggle", data);
}
async function saveRuleFromModal() {
  try {
    requireSignIn();
    const payload = buildRulePayload();
    const data = await callJson(cfg.search + "/search/admin/rules", "POST", payload, authHeaders(true));
    writeOut("search/admin/rules", data);
    ruleModal.hide();
    await loadConfig();
  } catch (err) {
    const node = el("ruleValidation");
    node.textContent = err.message || String(err);
    node.classList.remove("d-none");
  }
}
async function postEvent(eventType, payload) {
  requireSignIn();
  const data = await callJson(cfg.search + "/search/events", "POST", { eventType, timestamp: new Date().toISOString(), ...payload }, authHeaders());
  writeOut("search/events", data);
  return data;
}
async function simulateClick() {
  const visitorId = (el("simVisitorId").value || "demo-visitor-01").trim();
  const productId = (el("simProductId").value || "").trim();
  if (!productId) throw new Error("Clicked product id is required.");
  await postEvent("click", { visitorId, productId });
  await runRecommend();
}
async function simulateBrowseJourney() {
  const visitorId = (el("simVisitorId").value || "demo-visitor-01").trim();
  const query = (el("simSearchText").value || "jacket").trim();
  const productId = (el("simProductId").value || "SKU-107").trim();
  await postEvent("search", { visitorId, query });
  await postEvent("view", { visitorId, productId });
  await postEvent("click", { visitorId, productId });
  el("recommendProductId").value = productId;
  await runRecommend();
}

el("signIn").addEventListener("click", () => signIn().catch(err => writeOut("auth.error", String(err))));
el("signOut").addEventListener("click", () => signOut());
el("ingestFromErp").addEventListener("click", () => ingestFromErp().catch(err => writeOut("ingest.error", String(err))));
el("runQuery").addEventListener("click", () => runQuery().catch(err => writeOut("query.error", String(err))));
el("runRecommend").addEventListener("click", () => runRecommend().catch(err => writeOut("recommend.error", String(err))));
el("loadConfig").addEventListener("click", () => loadConfig().catch(err => writeOut("config.error", String(err))));
el("loadAnalytics").addEventListener("click", () => loadAnalytics().catch(err => writeOut("analytics.error", String(err))));
el("refreshRedirects")?.addEventListener("click", () => loadRedirects().catch(err => writeOut("redirects.error", String(err))));
el("saveRedirect")?.addEventListener("click", () => saveRedirect().catch(err => writeOut("redirects.error", String(err))));
el("refreshObjective")?.addEventListener("click", () => loadRankingObjective().catch(err => writeOut("objective.error", String(err))));
el("saveObjective")?.addEventListener("click", () => saveRankingObjective().catch(err => writeOut("objective.error", String(err))));
el("resetMlModel")?.addEventListener("click", () => resetMlModel().catch(err => writeOut("objective.error", String(err))));
el("refreshAiToggle").addEventListener("click", () => loadConfig().catch(err => writeOut("config.error", String(err))));
el("aiRerankToggle").addEventListener("change", e => toggleAi("rerank", e.target.checked).catch(err => writeOut("ai-toggle.error", String(err))));
el("aiIntentToggle").addEventListener("change", e => toggleAi("intent", e.target.checked).catch(err => writeOut("ai-toggle.error", String(err))));
el("aiVectorToggle").addEventListener("change", e => toggleAi("vector", e.target.checked).catch(err => writeOut("ai-toggle.error", String(err))));
el("aiEnrichToggle").addEventListener("change", e => toggleAi("enrich", e.target.checked).catch(err => writeOut("ai-toggle.error", String(err))));
el("newRule").addEventListener("click", () => openRuleModal(null));
el("saveRuleModal").addEventListener("click", () => saveRuleFromModal());
el("simulateClick").addEventListener("click", () => simulateClick().catch(err => writeOut("simulate.click.error", String(err))));
el("simulateBrowse").addEventListener("click", () => simulateBrowseJourney().catch(err => writeOut("simulate.browse.error", String(err))));
el("openRuleEditorFromLevers").addEventListener("click", () => openRuleModal(null));
el("runIngestFromLevers").addEventListener("click", () => ingestFromErp().catch(err => writeOut("ingest.error", String(err))));
el("runSimFromLevers").addEventListener("click", () => simulateBrowseJourney().catch(err => writeOut("simulate.browse.error", String(err))));
el("runQueryFromLevers").addEventListener("click", () => runQuery().catch(err => writeOut("query.error", String(err))));
el("loadAnalyticsFromLevers").addEventListener("click", () => loadAnalytics().catch(err => writeOut("analytics.error", String(err))));
el("viewDiagnosticsFromLevers").addEventListener("click", () => loadDiagnostics().catch(err => writeOut("diagnostics.error", String(err))));
el("clearOutput").addEventListener("click", () => { el("out").textContent = ""; });
el("rulesPrev").addEventListener("click", () => { state.rulesPage = Math.max(1, state.rulesPage - 1); renderRules(); });
el("rulesNext").addEventListener("click", () => { state.rulesPage = state.rulesPage + 1; renderRules(); });
el("resultsPrev").addEventListener("click", () => { state.resultsPage = Math.max(1, state.resultsPage - 1); renderResults(); });
el("resultsNext").addEventListener("click", () => { state.resultsPage = state.resultsPage + 1; renderResults(); });
el("refreshDiagnostics").addEventListener("click", () => loadDiagnostics().catch(err => writeOut("diagnostics.error", String(err))));
el("diagnosticsPrev").addEventListener("click", () => { state.diagnosticsPage = Math.max(1, state.diagnosticsPage - 1); renderDiagnostics(); });
el("diagnosticsNext").addEventListener("click", () => { state.diagnosticsPage = state.diagnosticsPage + 1; renderDiagnostics(); });

setAuthState("Signed out");
renderRules();
renderResults();
renderAnalytics(null);
renderDiagnostics();
</script>
</body>
</html>
"""
    return html.replace("__STS__", sts).replace("__SEARCH__", search_api).replace("__ERP__", erp_api)


def merged_docs_html() -> str:
    return """<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Wave Retail Platform Guide + Orchestrator</title>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>
  <style>
    :root {
      --cp-bg: #f5f1ff;
      --cp-surface: #ffffff;
      --cp-surface-soft: #f8f4ff;
      --cp-border: #d9cfef;
      --cp-text: #1b1230;
      --cp-text-muted: #6a5f85;
      --cp-accent: #593196;
      --cp-accent-hover: #47267a;
      --cp-accent-2: #e06c00;
      --cp-nav: #2d0f5e;
    }
    body { background: var(--cp-bg); color: var(--cp-text); font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif; }
    .hero {
      background: linear-gradient(135deg, var(--cp-nav) 0%, var(--cp-accent) 55%, var(--cp-accent-2) 100%);
      color: #fff;
      border-radius: 1rem;
      padding: 1rem 1.25rem;
    }
    .hero .text-secondary { color: rgba(255,255,255,.88) !important; }
    .wave-accent { color: var(--cp-accent); }
    .wave-card { border: 1px solid var(--cp-border); border-radius: 1rem; background: var(--cp-surface); }
    .node { border: 1px solid var(--cp-border); border-radius: .75rem; background: var(--cp-surface-soft); padding: .75rem; height: 100%; }
    .flow-arrow { text-align: center; color: var(--cp-text-muted); font-weight: 700; }
    .mono { font-family: Consolas, "Courier New", monospace; }
    .table thead th { background: var(--cp-surface-soft); color: var(--cp-text-muted); }
    .btn-outline-primary { color: var(--cp-accent); border-color: var(--cp-accent); }
    .btn-outline-primary:hover { background: var(--cp-accent); border-color: var(--cp-accent); }
  </style>
</head>
<body>
<div class='container py-4'>
  <div class='hero mb-3'>
    <div class='d-flex flex-wrap justify-content-between gap-2 align-items-start'>
      <div>
        <h1 class='h3 mb-1'>Wave Retail Platform Guide + Orchestrator</h1>
        <p class='mb-2 text-secondary'>Unified technical and operational view of the WaveSearch + WaveStore platform.</p>
        <span class='badge text-bg-light text-dark me-1'>AKS wave-dev</span>
        <span class='badge text-bg-light text-dark me-1'>ARM in-cluster builds</span>
        <span class='badge text-bg-light text-dark'>STS audience + scope auth</span>
      </div>
      <div>
        <a class='btn btn-sm btn-light me-1' href='https://labs.retail.demos.wavefunctionlabs.com'>Search Admin GUI</a>
        <a class='btn btn-sm btn-outline-light' href='https://store.retail.demos.wavefunctionlabs.com'>WaveStore</a>
      </div>
    </div>
  </div>


  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Entry points and service map</h2>
      <p class='text-secondary mb-2'>Each host is an ingress entry point into a specific frontend/API service chain. Shopper and operator traffic share the same ingress layer but route to different service surfaces and scopes.</p>
      <div class='row g-3 mb-2'>
        <div class='col-sm-6 col-lg-3'><div class='node h-100'><strong>Shopper</strong><br><a href='https://store.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>WaveStore Storefront</a><hr class='my-2'><span class='small text-secondary'>Routes to <span class='mono'>wavestore-frontend</span> for browse/search/account/checkout, then to <span class='mono'>wavesearch-api</span> and <span class='mono'>wavestore-erp-api</span> via service APIs.</span></div></div>
        <div class='col-sm-6 col-lg-3'><div class='node h-100'><strong>ERP admin</strong><br><a href='https://erp.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>ERP Simulation</a><hr class='my-2'><span class='small text-secondary'>Routes to <span class='mono'>wavestore-erp-frontend</span> for CRUD/admin tasks, backed by <span class='mono'>wavestore-erp-api</span> and STS-issued admin scopes.</span></div></div>
        <div class='col-sm-6 col-lg-3'><div class='node h-100'><strong>Search ops/docs</strong><br><a href='https://labs.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>Search Admin Labs</a><hr class='my-2'><span class='small text-secondary'>Routes to <span class='mono'>wavesearch-frontend</span> (search admin GUI + this platform guide), which drives <span class='mono'>/search/admin/*</span>, ingest, simulation, and analytics.</span></div></div>
        <div class='col-sm-6 col-lg-3'><div class='node h-100'><strong>Identity admin</strong><br><a href='https://sts.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>STS Admin</a><hr class='my-2'><span class='small text-secondary'>Routes directly to <span class='mono'>wave-sts</span> for user/audience/scope management, token issuance, and validation tooling.</span></div></div>
      </div>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Public host</th><th>Primary service</th><th>Downstream dependencies</th></tr></thead>
          <tbody>
            <tr><td class='mono'>store.retail.demos.wavefunctionlabs.com</td><td class='mono'>wavestore-frontend</td><td>wavesearch-api, wavestore-erp-api, wave-sts</td></tr>
            <tr><td class='mono'>erp.retail.demos.wavefunctionlabs.com</td><td class='mono'>wavestore-erp-frontend</td><td>wavestore-erp-api, wave-sts</td></tr>
            <tr><td class='mono'>labs.retail.demos.wavefunctionlabs.com</td><td class='mono'>wavesearch-frontend</td><td>wavesearch-api, wavestore-erp-api, wave-sts</td></tr>
            <tr><td class='mono'>sts.retail.demos.wavefunctionlabs.com</td><td class='mono'>wave-sts</td><td>user/audience/scope admin UI + token issuance/validation</td></tr>
            <tr><td class='mono'>search-api.retail.demos.wavefunctionlabs.com</td><td class='mono'>wavesearch-api</td><td>runtime index, append logs, wave-sts</td></tr>
            <tr><td class='mono'>erp-api.retail.demos.wavefunctionlabs.com</td><td class='mono'>wavestore-erp-api</td><td>ERP state store, wave-sts</td></tr>
          </tbody>
        </table>
      </div>
      <div class='flow-arrow'>↓ ingress (host/path routing) ↓</div>
      <div class='row g-2 mt-1'>
        <div class='col-md-4'><div class='node'>wave-sts</div></div>
        <div class='col-md-4'><div class='node'>wavestore-erp-api</div></div>
        <div class='col-md-4'><div class='node'>wavesearch-api</div></div>
      </div>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Service dependency graph</h2>
      <p class='text-secondary mb-2'>Call relationships between shopper/admin surfaces, core services, and the optional Azure Foundry AI harness used for reranking and intent classification.</p>
      <div class='mermaid'>
flowchart LR
  subgraph Shopper["Shopper surface"]
    Store["WaveStore Storefront"]
  end
  subgraph Admin["Admin surfaces"]
    ERPUI["WaveStore ERP Admin"]
    LabsUI["WaveSearch Labs Admin"]
    STSUI["STS Admin"]
  end
  subgraph Core["Core services"]
    STS["wave-sts"]
    ERP["wavestore-erp-api"]
    Search["wavesearch-api"]
  end
  subgraph AI["External AI"]
    Foundry[["Azure Foundry gpt-5-nano"]]
  end

  Store -->|login and tokens| STS
  Store -->|catalog, account, orders| ERP
  Store -->|search, recommend, events| Search

  ERPUI -->|tokens| STS
  ERPUI -->|CRUD| ERP

  LabsUI -->|tokens| STS
  LabsUI -->|ingest, query, rules, analytics| Search
  LabsUI -->|export catalog read| ERP

  STSUI -->|user and scope admin| STS

  Search -->|validate tokens| STS
  Search -->|ingest from| ERP
  Search -->|rerank and classify intent| Foundry

  ERP -->|validate tokens| STS
      </div>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Tech stack and runtime internals</h2>
      <div class='table-responsive'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Layer</th><th>What is used</th><th>How it fits</th></tr></thead>
          <tbody>
            <tr><td>UI surfaces</td><td>FastAPI + server-rendered HTML + Bootstrap Wave styling</td><td>Storefront, ERP admin, Search admin, and this unified doc surface.</td></tr>
            <tr><td>Search runtime</td><td class='mono'>CatalogRuntime + postings + term-frequency + doc length + variant links</td><td>Serves low-latency candidate retrieval and ranking directly from in-memory structures.</td></tr>
            <tr><td>Ranking model</td><td class='mono'>BM25-style term scoring + merchandising/inventory overlays</td><td>Converts lexical relevance into final ordered results; supports server-side filter constraints.</td></tr>
            <tr><td>State + telemetry</td><td>Catalog snapshots, append logs (events/rules/inventory), analytics overlays</td><td>Supports replay/debug and relevance tuning loops using behavior and operator actions.</td></tr>
            <tr><td>Platform</td><td>AKS + shared ingress + ACR</td><td>Single routed platform with multi-service hostnames and ARM-compatible deployments.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>How ingestion and search are generated</h2>
      <div class='row g-3'>
        <div class='col-lg-4'>
          <h3 class='h6'>Ingestion</h3>
          <ol class='small text-secondary mb-0'>
            <li>ERP exports catalog via <span class='mono'>/erp/export/catalog</span>.</li>
            <li>Search API ingests via <span class='mono'>/search/ingest/from-erp</span>.</li>
            <li>Snapshot JSON is written, then runtime rebuilt in memory.</li>
            <li>New runtime is activated for query/recommend traffic.</li>
          </ol>
        </div>
        <div class='col-lg-4'>
          <h3 class='h6'>Search query path</h3>
          <ol class='small text-secondary mb-0'>
            <li>Query tokenization and postings candidate retrieval.</li>
            <li>BM25-style scoring per candidate document:
              <ul class='mb-0'>
                <li><strong>TF:</strong> repeated query terms in a product increase relevance.</li>
                <li><strong>IDF:</strong> rarer terms across the catalog carry more weight.</li>
                <li><strong>Length normalization:</strong> long descriptions do not win purely by word count.</li>
              </ul>
            </li>
            <li>Server-side filters (facet/price/stock/availability/tag) applied.</li>
            <li>Facet buckets and ranked products returned.</li>
          </ol>
        </div>
        <div class='col-lg-4'>
          <h3 class='h6'>Browse/recommend path</h3>
          <ol class='small text-secondary mb-0'>
            <li>Seed product and visitor context determine related candidates.</li>
            <li>Category/brand/tag overlap scoring is computed.</li>
            <li>Merchandising and availability posture influence final ordering.</li>
            <li>Search/click/view events feed analytics for tuning.</li>
          </ol>
        </div>
      </div>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>AI harness (Azure Foundry) for reranking and intent classification</h2>
      <p class='text-secondary mb-2'>The search platform now supports an optional second-stage AI pass after lexical retrieval. It keeps the fast server-side candidate retrieval/filtering path, then uses Azure Foundry to improve precision.</p>
      <div class='table-responsive'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Capability</th><th>How it works</th><th>Response visibility</th></tr></thead>
          <tbody>
            <tr><td>Intent classification</td><td>Classifies query intent and proposes inferred filters from the request query/filters payload.</td><td>Returned under <span class='mono'>ai.intent</span> in <span class='mono'>/search/query</span> responses.</td></tr>
            <tr><td>LLM reranking</td><td>Reranks top-N lexical candidates for semantic relevance while preserving backend constraints and filter boundaries.</td><td>Returned under <span class='mono'>ai.rerank</span>; reordered results in the same query response.</td></tr>
            <tr><td>Safety fallback</td><td>If the model call fails or times out, lexical ranking is preserved and the error is surfaced in metadata.</td><td><span class='mono'>ai.rerank.error</span> / <span class='mono'>ai.intent.error</span> (when applicable).</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-1'><strong>Foundry configuration (environment):</strong></p>
      <ul class='text-secondary mb-0'>
        <li><span class='mono'>RETAIL_V2_LLM_ENDPOINT</span>, <span class='mono'>RETAIL_V2_LLM_DEPLOYMENT</span>, <span class='mono'>RETAIL_V2_LLM_API_VERSION</span>, <span class='mono'>RETAIL_V2_LLM_API_KEY</span></li>
        <li><span class='mono'>RETAIL_V2_LLM_RERANK_ENABLED</span>, <span class='mono'>RETAIL_V2_LLM_INTENT_ENABLED</span>, <span class='mono'>RETAIL_V2_LLM_RERANK_TOP_N</span>, <span class='mono'>RETAIL_V2_LLM_TIMEOUT_SECONDS</span></li>
      </ul>
      <p class='text-secondary mb-1 mt-3'><strong>Exact prompts/templates used (verbatim from <span class='mono'>wavesearch_api/app.py</span>):</strong></p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Call</th><th>System prompt</th><th>User payload shape</th></tr></thead>
          <tbody>
            <tr>
              <td>Intent classification</td>
              <td class='mono'>"You classify retail search intent. Return strict JSON with keys: intent (string), confidence (0-1), inferredFilters (object), notes (string)."</td>
              <td class='mono'>{"query": &lt;search text&gt;, "filters": &lt;active facet filters&gt;}</td>
            </tr>
            <tr>
              <td>LLM reranking</td>
              <td class='mono'>"You rerank retail candidates for user relevance. Return strict JSON with keys: rerankedIndexes (array of integers, unique, subset/permutation of provided indexes), rationale (string)."</td>
              <td class='mono'>{"query": &lt;search text&gt;, "candidates": [{"index","id","title","description","categories","brands","tags","availability","price"}, ...]}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'>Both calls request <span class='mono'>response_format: json_object</span> (with a plain-text fallback if the model rejects that parameter), run concurrently via <span class='mono'>asyncio.gather</span>, and are capped at <span class='mono'>RETAIL_V2_LLM_TIMEOUT_SECONDS</span> each; reranking only sends the top <span class='mono'>RETAIL_V2_LLM_RERANK_TOP_N</span> candidates to bound prompt size and cost.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Search Explorer: pre/post AI diagnostics</h2>
      <p class='text-secondary mb-2'>Every <span class='mono'>/search/query</span> call is recorded server-side with its lexical (pre-AI/BM25) result order and its final (post-AI) result order, so operators can inspect exactly what reranking and intent classification changed for any real search.</p>
      <div class='table-responsive'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Endpoint</th><th>Purpose</th><th>Where visible in Search Admin GUI</th></tr></thead>
          <tbody>
            <tr><td class='mono'>GET /search/admin/diagnostics</td><td>Lists recent searches per tenant (query, result count, whether rerank/intent applied, whether order changed).</td><td><strong>Search Explorer</strong> paged table.</td></tr>
            <tr><td class='mono'>GET /search/admin/diagnostics/{id}</td><td>Returns full pre-AI and post-AI result lists plus rerank rationale and intent classification detail for one search.</td><td><strong>Search diagnostic</strong> comparison modal (side-by-side before/after tables with rank deltas).</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'>Diagnostics are held in an in-memory ring buffer per tenant (default 50 entries, configurable via <span class='mono'>RETAIL_V2_SEARCH_DIAGNOSTICS_MAX</span>) so recent activity is inspectable without impacting query latency.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Hybrid search: lexical (BM25) + vector embeddings, RRF-fused</h2>
      <p class='text-secondary mb-2'>Pure lexical/BM25 search can only find products that share at least one token with the query &mdash; a query like "something to keep me warm on a freezing winter hike" shares zero words with a product titled "Aurora Storm Shell Jacket" and would previously return almost nothing. Hybrid search adds a second, independent retrieval path over vector embeddings and fuses the two rankings, so semantically related products surface even with no keyword overlap.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Stage</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Embedding model</strong></td><td><span class='mono'>text-embedding-3-small</span>, deployed on the same Azure OpenAI/Foundry resource as the <span class='mono'>gpt-5-nano</span> rerank model (env <span class='mono'>RETAIL_V2_EMBEDDING_DEPLOYMENT</span>).</td></tr>
            <tr><td><strong>Index build</strong></td><td>Every product's title/description/categories/brands/tags text is embedded once and cached in-memory as a single L2-normalized numpy matrix (<span class='mono'>vector_matrix</span>, shape N&times;D, plus a parallel <span class='mono'>vector_ids</span> list), rebuilt automatically on every catalog ingest while the toggle is on, or on-demand the moment the toggle is switched on if the index is empty.</td></tr>
            <tr><td><strong>Query time</strong></td><td>The query text is embedded (one call), L2-normalized, and compared against every indexed product vector via a single vectorized matrix-vector multiply (numpy/BLAS) rather than a Python loop &mdash; comfortably sub-100ms up to roughly 100k-1M vectors on one core. Still "brute-force" in that every vector participates (no ANN/graph index skips comparisons); results respect the same category/brand/tag/availability/price/stock filters as the lexical path.</td></tr>
            <tr><td><strong>Fusion</strong></td><td>Reciprocal Rank Fusion (RRF) combines the lexical rank and vector rank <em>by position</em>, not raw score (BM25 and cosine similarity are on incomparable scales): <span class='mono'>score = 1/(k + lexical_rank) + 1/(k + vector_rank)</span>, <span class='mono'>k</span> configurable via <span class='mono'>RETAIL_V2_RRF_K</span> (default 60, the standard literature value). Existing LLM reranking, if also enabled, then runs on top of the fused order exactly as before.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-1'><strong>Off by default</strong> (env <span class='mono'>RETAIL_V2_VECTOR_ENABLED</span>), toggled live per the same pattern as LLM rerank/intent via <span class='mono'>POST /search/admin/ai-toggle</span> (<span class='mono'>vectorEnabled</span>) from the <strong>AI harness</strong> panel in Search Admin, with index size/availability visible in <span class='mono'>GET /search/admin/config</span>. <span class='mono'>POST /search/admin/vector-index/rebuild</span> forces a manual rebuild.</p>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> querying "something to keep me warm on a freezing winter hike" (2 lexical BM25 candidates only) returned Aurora Storm Shell Jacket plus several hiking boots pulled in purely by vector similarity (flagged <span class='mono'>vectorOnly: true</span> in the response) &mdash; at ~270-320ms per query, dominated by the single query-embedding call, well under the ~1-1.8s LLM rerank path.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Vector search at real scale: what this demo does <em>not</em> solve</h2>
      <p class='text-secondary mb-2'>This demo's catalog is ~100 products. A real retail customer can have millions of SKUs and variants, and "brute-force" here means exactly that: every query compares against every stored vector, with no index structure skipping comparisons. Worth being explicit about where that breaks and what the honest production answer looks like.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Concern</th><th>Why it breaks at millions of SKUs</th><th>Production answer</th></tr></thead>
          <tbody>
            <tr><td><strong>Compute</strong></td><td>Even a vectorized numpy matmul is <span class='mono'>O(N&times;D)</span> per query &mdash; linear in catalog size. Fine at 100k-1M vectors on one core; a query against 10M+ vectors on every request stops being "fast enough."</td><td>An Approximate Nearest Neighbor (ANN) index &mdash; HNSW (graph-based) or IVF (cluster-based) &mdash; that answers in roughly <span class='mono'>O(log N)</span> by skipping the vast majority of comparisons, at the cost of being approximate.</td></tr>
            <tr><td><strong>Memory</strong></td><td>1M products &times; 1536 dims &times; 4 bytes (float32) &asymp; 6GB just for vectors, held in one process. Doesn't fit comfortably in a single pod, and this demo's in-memory index is process-local (one copy per replica, same limitation as the catalog runtime itself).</td><td>An externalized, purpose-built vector store: <strong>Azure AI Search</strong> vector index, <strong>Azure Cosmos DB (DiskANN vCore)</strong>, or self-hosted <strong>pgvector</strong>/<strong>FAISS</strong> service &mdash; something that shards/persists vectors outside of each API replica's process memory.</td></tr>
            <tr><td><strong>Freshness</strong></td><td>Re-embedding the whole catalog on every ingest (this demo's approach) is fine at 100 products (~1.3s); at millions of SKUs a full re-embed is a substantial batch job.</td><td>Incremental/delta embedding: only re-embed products that actually changed since the last ingest, tracked by a content hash or updated-at timestamp.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'>This ties directly to the same architectural gap already tracked for the catalog runtime itself (see the single-writer/multi-reader scaling item below): a real deployment needs the vector index externalized and shared across replicas, not held per-pod in memory, for exactly the same reasons.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>LLM at ingestion, not query time: catalog enrichment</h2>
      <p class='text-secondary mb-2'>Rerank and intent classification ask the LLM to reason fresh on <em>every query</em> &mdash; cost and latency that scale with query volume. But relevance-widening work that doesn't depend on the specific query &mdash; synonyms, use-cases, occasions, audience/gift framing a shopper might type but a title/description never uses, plus category-typical features that are true in general but never actually written down (hiking boots are expected to be water-resistant with ankle support; the raw catalog description often just says "Footwear item N for everyday retail browsing") &mdash; can be done <em>once per product, at ingest</em> instead, and reused by every future query for free.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Aspect</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>What it generates</strong></td><td>For each product, the LLM returns two things: (1) 5-10 additional search keywords/phrases not already present in the title/description (synonyms, use-cases, seasons, audience/gift framing); (2) 2-5 category-typical <em>inferred features</em> the description is missing (e.g. "water-resistant", "ankle support" for a hiking boot) &mdash; explicitly scoped to genuinely standard-for-the-category attributes, not invented specifics like exact certifications or ratings.</td></tr>
            <tr><td><strong>Where it lands</strong></td><td>Keywords merge into the product's <span class='mono'>tags</span> list (deduped, case-insensitive); inferred features are appended to the <span class='mono'>description</span> as a clearly-labeled "Typically includes: ..." sentence (never rewritten into the description as an unqualified factual claim, and guarded against duplicate re-appending on repeat ingests). Both happen <em>before</em> the catalog runtime is built and <em>before</em> vector embeddings are computed, so lexical (BM25) postings and vector embeddings benefit automatically with zero changes to either retrieval path.</td></tr>
            <tr><td><strong>Batching</strong></td><td>One LLM call enriches a whole batch of products at once (default 15/call, env <span class='mono'>RETAIL_V2_LLM_ENRICH_BATCH_SIZE</span>), with up to <span class='mono'>RETAIL_V2_LLM_ENRICH_MAX_CONCURRENCY</span> (default 6) batches running concurrently &mdash; cost/latency scales with <span class='mono'>catalog_size &divide; batch_size</span>, not with catalog size directly, and pays out at ingest time, off the query-serving path entirely.</td></tr>
            <tr><td><strong>Separate token/timeout budget</strong></td><td>A 15-product enrichment batch generates far more output than a single rerank/intent call &mdash; reusing the query-time <span class='mono'>max_completion_tokens</span>/timeout (tuned tight for per-query latency) silently truncated the JSON and/or timed out on every batch. Enrichment now has its own, much larger budget: <span class='mono'>RETAIL_V2_LLM_ENRICH_MAX_COMPLETION_TOKENS</span> (default <span class='mono'>300 &times; batch_size</span>) and <span class='mono'>RETAIL_V2_LLM_ENRICH_TIMEOUT_SECONDS</span> (default 60s) &mdash; since ingest is off the query-serving path, there's no latency pressure to keep these tight.</td></tr>
            <tr><td><strong>Cost curve vs. rerank/intent</strong></td><td>Rerank/intent cost is proportional to <em>query volume</em> (paid forever, on every search). Enrichment cost is proportional to <em>catalog size</em> and only re-paid when the catalog changes &mdash; a catalog changes far less often than searches arrive, so the amortized per-query cost trends toward zero as traffic grows, the opposite of the rerank/intent curve.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-1'><strong>Off by default</strong> (env <span class='mono'>RETAIL_V2_LLM_ENRICH_ENABLED</span>), toggled via <span class='mono'>POST /search/admin/ai-toggle</span> (<span class='mono'>enrichEnabled</span>) from the same AI harness panel; runs automatically on the next <span class='mono'>POST /search/ingest/catalog</span> or <strong>Ingest from ERP</strong> action once switched on, with an <span class='mono'>enrichment</span> block (products enriched, descriptions augmented, batch count/errors) returned in the ingest response.</p>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> re-ingesting the 103-product demo catalog with enrichment on took ~22s (7 concurrent batches) and enriched all 103 products; a generic "Summit Boot 132" (originally "Footwear item 132 for everyday retail browsing and search.") gained tags including <span class='mono'>hiking boot</span>, <span class='mono'>boot waterproof</span>, <span class='mono'>ankle support</span> and a description suffix "Typically includes: hiking boot, sturdy outsole, ankle support, lace-up design, outerwear of footwear." &mdash; so a query for "waterproof hiking boots" now matches lexically, not just via the vector path.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Enriching the source of truth: <span class='mono'>POST /erp/admin/enrich-catalog</span></h2>
      <p class='text-secondary mb-2'>wavesearch-api's ingest-time enrichment (above) only ever touched its own transient in-memory copy of the catalog -- re-ingesting from ERP without ERP's own data being enriched would just bring the bland originals back. The real fix is enriching the ERP's own product records directly, once, so the improved description/categories are permanent and every future ingest (from any consumer) already gets the enriched version for free.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Aspect</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>What it does</strong></td><td><span class='mono'>POST /erp/admin/enrich-catalog</span> on <span class='mono'>wavestore-erp-api</span> (requires <span class='mono'>erp.write</span>) rewrites each product's <span class='mono'>description</span> into 2-3 natural sentences that weave in category-typical features (e.g. "typically provide ankle support, durable outsole grip, and reliable weather resistance" for boots) and expands <span class='mono'>categories</span> into a richer taxonomy (e.g. <span class='mono'>Outdoor &gt; Footwear &gt; Boots</span>, <span class='mono'>Outdoor &gt; Hiking</span>), persisting both directly into the ERP's own product store.</td></tr>
            <tr><td><strong>Idempotent by default</strong></td><td>Each enriched product is marked <span class='mono'>_llmEnriched: true</span>; subsequent calls skip already-enriched products (<span class='mono'>{"applied": false, "reason": "no products need enrichment"}</span>) unless called with <span class='mono'>{"force": true}</span>, so re-running it doesn't keep re-writing descriptions on every call.</td></tr>
            <tr><td><strong>Same batching/config pattern</strong></td><td>Reuses the identical batched-call design as wavesearch-api's enrichment (default 15 products/call, up to 6 concurrent batches, its own generous token budget/timeout independent of any query-time path) against the same Foundry <span class='mono'>gpt-5-nano</span> deployment.</td></tr>
            <tr><td><strong>Completes the loop</strong></td><td>Once ERP is enriched, <strong>Ingest from ERP</strong> (<span class='mono'>POST /search/ingest/from-erp</span>) pulls the permanently-improved descriptions/categories into the search index automatically -- no per-ingest LLM cost needed on the wavesearch-api side anymore for products already enriched at the source.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> seeded ERP's (previously empty) product store from the 103-product demo catalog, ran <span class='mono'>/erp/admin/enrich-catalog</span> (~13s for all 103, 7 batches), confirmed a second call correctly no-ops, confirmed <span class='mono'>/erp/export/catalog</span> (ERP's own source-of-truth export) already returns the enriched description/categories, then re-ran <strong>Ingest from ERP</strong> and confirmed the search index picked up the same permanently-enriched text with zero wavesearch-api-side LLM calls needed.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Tunable ranking objective (CTR / conversion / revenue) -- backed by a real, continuously-retraining ML model</h2>
      <p class='text-secondary mb-2'>Vertex AI Search for Retail's recommendation models let an operator choose an optimization objective (click-through rate, conversion rate, revenue) for the trained model to target. This platform now has a real (if intentionally small) trainable model too: an <strong>online two-tower recommender</strong>, trained record-by-record as events arrive -- no batch job, no offline training run, no model registry hot-swap. A heuristic views/clicks/purchases ratio is kept as the automatic cold-start fallback until a tenant's model has learned enough to be trusted.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Aspect</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Model</strong></td><td>Per-tenant, per-objective (<span class='mono'>ctr</span>/<span class='mono'>conversion</span>/<span class='mono'>revenue</span>) two-tower model: a d=16 embedding + bias per product, a d=16 embedding per visitor. <span class='mono'>score = dot(user, item) + bias</span>. Trained with a pairwise Bayesian Personalized Ranking (BPR) SGD step -- a click/add-to-cart/purchase event is paired against a few randomly sampled unclicked products, and one gradient step pushes the real event's score above the sampled negatives'. See <span class='mono'>retail_v2/ml_ranker.py</span>.</td></tr>
            <tr><td><strong>Real-time retraining</strong></td><td>Every qualifying event trains inline on the request path inside <span class='mono'>_track_visitor_event</span> -- a few ~16-dim vector operations, sub-millisecond. There is no separate training job or schedule: the model a query sees reflects events logged moments earlier.</td></tr>
            <tr><td><strong>Tenant-wide vs. personalized scoring</strong></td><td>The ranking-objective step is a tenant-wide POLICY (same order for every shopper), so it scores using the item's learned <em>bias</em> term alone (a visitor-agnostic "this item generally wins for this objective" signal) rather than any one visitor's embedding -- the full personalized dot-product is available in the same model for a future recommend-style use case, just not applied here.</td></tr>
            <tr><td><strong>Cold start &amp; fallback</strong></td><td>A product the model has never trained on scores exactly 0.0 and is treated as "no signal" -- ranking falls back to the heuristic views/clicks/purchases ratio (<span class='mono'>_objective_score</span>) until a tenant's model for that objective has processed &ge; <span class='mono'>MIN_EVENTS_FOR_ML</span> (20) events. <span class='mono'>GET /search/admin/ml-model</span> reports events trained, loss, and whether each objective is "ready" (ML-driven) or still on the heuristic. Every ranking-objective response also carries a <span class='mono'>method: "ml" | "heuristic"</span> field -- never a silent black box.</td></tr>
            <tr><td><strong>Where it applies</strong></td><td><span class='mono'>/search/query</span>, <span class='mono'>/search/browse</span>, and <span class='mono'>/search/recommend</span> all blend the objective score into the existing relevance order via Reciprocal Rank Fusion (same technique as hybrid search and personalization) -- nudging results, not fully overriding them. Applied AFTER AI rerank but BEFORE personalization/merchandising, same layering as before.</td></tr>
            <tr><td><strong>Admin controls</strong></td><td><span class='mono'>GET/POST /search/admin/ranking-objective</span> (pick the objective), <span class='mono'>GET /search/admin/product-performance</span> (raw counters), <span class='mono'>GET /search/admin/ml-model</span> (model stats/readiness), <span class='mono'>POST /search/admin/ml-model/reset</span> (wipe a tenant's model and restart learning from scratch) -- all in the <strong>Ranking objective</strong> panel in Search Admin.</td></tr>
            <tr><td><strong>Persistence</strong></td><td>Model embeddings/biases, product performance counters, and the selected objective are all snapshotted to blob storage (every 10 trained events, to bound write volume) and reloaded on startup -- survives pod restarts.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-2'><strong>Verified live</strong> with <span class='mono'>scripts/simulate_ranking_traffic.py</span> (a repeatable traffic-simulation test script -- logs in for a search.admin token, fires simulated view/click/add_to_cart/purchase events for a chosen "boot" query's lowest-ranked product from 25+ distinct simulated visitors, sweeps all three objectives, and asserts the target moved up in rank for each): the target product started at rank #10 of 10 for both a "boot" query (SKU-187) and a "jacket" query (SKU-141); after firing simulated traffic, all three objectives reported <span class='mono'>method: "ml"</span> (the model, not the heuristic, drove the ranking) and moved the target to roughly rank #4-#6 for every objective -- a real, measurable, reproducible ranking shift driven by online learning, not a canned demo.</p>
      <p class='text-secondary mb-0'><span class='mono'>python scripts/simulate_ranking_traffic.py --base-url https://search-api.retail.demos.wavefunctionlabs.com --query boot --events 25</span> re-runs this end-to-end check against the live deployment at any time.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Visual search: describe it, or upload a photo -- no image generation, no CLIP</h2>
      <p class='text-secondary mb-2'><span class='mono'>POST /search/visual</span> closes the last Vertex AI Search for Retail gap (multi-modal/image search) without provisioning any new infrastructure. Two input modes feed the same downstream pipeline:</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Mode</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Text description</strong></td><td>A shopper types a vague or detailed visual description (e.g. "something that looks like a shoe", "a red waterproof hiking jacket"). <span class='mono'>gpt-5-nano</span> expands it into the concrete category/color/material/style/use-case words a real product listing would contain.</td></tr>
            <tr><td><strong>Uploaded photo</strong></td><td>A shopper uploads a real image. Rather than a separate CLIP-style image-embedding model/index, the same <span class='mono'>gpt-5-nano</span> deployment analyzes the photo directly via native vision input (confirmed working with a direct test call -- no new deployment needed) and describes what it sees in the identical category/color/material/style vocabulary.</td></tr>
            <tr><td><strong>Why not generate an image</strong></td><td>A literal "generate a picture, then search by image similarity" round-trip needs <span class='mono'>gpt-image-1</span> (DALL-E 3 is retired), which isn't deployable in this resource's region -- would require a second cross-region Azure OpenAI resource. Both text and photo modes here get the same practical outcome (rich visual terms feeding hybrid search) using only what's already deployed.</td></tr>
            <tr><td><strong>Shared pipeline</strong></td><td>Whichever mode produces the expanded query, it's run through the exact same <span class='mono'>_run_search_pipeline</span> as <span class='mono'>/search/query</span> (hybrid retrieval, rerank, personalization, merchandising, dynamic facets) -- extracted into a shared function specifically so this didn't need a second copy of the ranking pipeline.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> "something that looks like a shoe" expanded to "shoe-like footwear, ... sneaker-inspired silhouette ..." and returned Summit Boots (the closest footwear in this catalog); uploading a real product photo of a blue/orange color-block waterproof jacket correctly identified it ("Outerwear / Jacket", "color: blue, rust-orange", "material: waterproof/windbreaker fabric") and returned the Aurora Storm Shell Jacket and Trail Ridge Shell products at the top of results. Wired into the WaveStore home page as a "Describe &amp; search" box with an "Or upload a photo" file picker.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Personalization, dynamic faceting, and a dedicated browse endpoint</h2>
      <p class='text-secondary mb-2'>Three more gaps closed from the Vertex AI Search for Retail comparison, all reusing the platform's existing bolt-on-layer pattern (retrieval untouched, additional passes composed on top).</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Feature</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Personalization</strong></td><td><span class='mono'>POST /search/events</span> was previously a write-only sink -- clickstream telemetry was logged but never used. It's now public (anonymous shoppers can log events without auth, same posture as search) and every view/click/add-to-cart/purchase event builds a per-visitor category/brand/tag affinity profile (weighted by intent strength: purchase &gt; add-to-cart &gt; click &gt; view). <span class='mono'>/search/query</span>, <span class='mono'>/search/recommend</span>, and the new <span class='mono'>/search/browse</span> all accept an optional <span class='mono'>visitorId</span> and blend that affinity into ranking via Reciprocal Rank Fusion -- nudging results toward a shopper's taste without fully overriding relevance or the query itself, applied after AI rerank but before merchandising (an explicit business rule still has the final say). Persisted to blob storage, surviving restarts like everything else.</td></tr>
            <tr><td><strong>Dynamic faceting</strong></td><td>Beyond the existing static category/brand/availability facets, every <span class='mono'>/search/query</span> and <span class='mono'>/search/browse</span> response now includes price-range buckets and a top-tags facet computed from the actual candidate pool -- and any facet dimension with fewer than 2 distinct values in the current result set is dynamically omitted (e.g. no pointless "Category: Outdoor (12)" facet once already filtered to Outdoor).</td></tr>
            <tr><td><strong>Dedicated browse endpoint</strong></td><td><span class='mono'>POST /search/browse</span> -- category/collection navigation with no free-text query, mirroring Vertex's browse concept: same filters/sort/facets/merchandising/personalization pipeline as search, minus lexical retrieval and minus rerank/intent/vector (nothing for an LLM or embedding to usefully rerank without a query). Defaults to in-stock-first ordering when no explicit sort is given -- an honest proxy for "revenue-optimized" browse ranking given this demo has no real sales/margin data to rank by.</td></tr>
            <tr><td><strong>Storefront wiring</strong></td><td>The shared, hardcoded <span class='mono'>"wave-store-visitor"</span> constant was replaced with a real persistent per-browser visitor id (localStorage-backed), and the storefront now actually fires <span class='mono'>search</span>/<span class='mono'>view</span>/<span class='mono'>add_to_cart</span>/<span class='mono'>purchase</span> events on the corresponding real actions -- previously wired up as an API capability nobody called from the live UI.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> simulated a visitor viewing/clicking/purchasing three jacket products (Contoso Trail brand); an "Outdoor" browse for that visitor then returned Trail Ridge Shell jackets ahead of Summit Boots in the top 5, versus a mixed boots/jackets baseline with no visitor history. A "boot" query's facets included price ranges (<span class='mono'>Under $25</span>, <span class='mono'>$50-$100</span>) and top tags (<span class='mono'>hiking boot</span>, <span class='mono'>waterproof boot</span>, ...) alongside the existing category/availability facets.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Delta ingestion and cross-restart persistence (real Azure Blob Storage)</h2>
      <p class='text-secondary mb-2'>Every ingest previously re-embedded and re-enriched the <em>entire</em> catalog from scratch, every time -- adding one new product to a large catalog paid the full LLM/embedding cost of the whole catalog again. And since the catalog runtime, vector index, merchandising rules, redirects, and promotions were all process-local in-memory state, a pod restart (or a routine redeploy) silently reset everything back to empty/default.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Aspect</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Content-hash delta detection</strong></td><td>Each product's indexable fields (title/description/categories/brands/tags/availability/price) are hashed (sha256 of a canonical JSON form). A product whose hash is unchanged since the last ingest skips both LLM enrichment and re-embedding entirely, reusing its cached tags/description/vector.</td></tr>
            <tr><td><strong>Self-referential re-ingest handled correctly</strong></td><td>Re-posting the currently-served (already-enriched) catalog back into <span class='mono'>/search/ingest/catalog</span> -- a very plausible "refresh" action -- is recognized as unchanged too: each cache entry stores both the original pre-enrichment <span class='mono'>sourceHash</span> and the resulting <span class='mono'>outputHash</span>, and incoming content matching <em>either</em> is treated as a cache hit.</td></tr>
            <tr><td><strong>Real persistence backend</strong></td><td>A new <span class='mono'>AzureBlobStore</span> adapter (<span class='mono'>retail_v2/azure_blob_store.py</span>) implements the same <span class='mono'>BlobStore</span> protocol as the existing filesystem-backed dev adapter, backed by a real Azure Storage Account + container. Selected automatically when <span class='mono'>RETAIL_V2_BLOB_ACCOUNT_NAME</span>/<span class='mono'>_ACCOUNT_KEY</span> are configured; falls back to the local filesystem adapter otherwise. Unlike a Kubernetes emptyDir volume (survives container restarts but not a full pod reschedule/rollout), a real blob container survives every redeploy.</td></tr>
            <tr><td><strong>What's persisted</strong></td><td>The last-ingested catalog itself, the vector embedding cache, the enrichment cache, merchandising rules, query redirects, and promotions -- all rehydrated automatically on <span class='mono'>@app.on_event("startup")</span>, before the first request is served.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> a cold ingest of the 103-product catalog took ~22s (full LLM enrichment + embedding); re-ingesting the identical catalog afterward took <strong>248ms</strong> with 104/104 products reused from cache for both enrichment and vectors. After a full pod restart, <span class='mono'>vectorIndexSize</span> was already 104 before any ingest ran, and a subsequent re-ingest again reused all 104 vectors with zero new embedding calls -- confirming the cache and the underlying catalog both survive a real redeploy, not just a within-process cache. A merchandising rule and a query redirect created before a restart were both still present and enforced afterward.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Fixed: merchandising boost/bury/pin rules now actually apply</h2>
      <p class='text-secondary mb-2'>A gap analysis against Vertex AI Search for Retail surfaced a real bug, not a missing feature: <span class='mono'>POST /search/admin/rules</span> has always accepted and stored boost/bury/pin rules, and both the Search Admin GUI and this doc described them as live ranking controls -- but no query path ever actually read them. Setting a rule had zero effect on search or recommendation ordering.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Aspect</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Where it's applied</strong></td><td>As the <em>final</em> ranking step in both <span class='mono'>POST /search/query</span> and <span class='mono'>POST /search/recommend</span>, after lexical/vector retrieval and after any LLM rerank. Business rules represent an explicit merchandising decision and should override AI/relevance ranking, not be undone by it.</td></tr>
            <tr><td><strong>Semantics</strong></td><td><strong>Pin:</strong> forced to the top, in the order pinned. <strong>Boost:</strong> moved ahead of neutral results, relative order preserved. <strong>Bury:</strong> moved to the bottom. A product listed in both boost and bury (contradictory rules) is treated as buried -- an explicit "hide this" decision wins over "promote this". Rules only re-rank products already present in the result set; they never inject unrelated products that didn't match the query/filters.</td></tr>
            <tr><td><strong>Transparency</strong></td><td>Every response now includes a <span class='mono'>merchandising</span> block (<span class='mono'>applied</span>, <span class='mono'>pinned</span>/<span class='mono'>boosted</span>/<span class='mono'>buried</span> counts) so it's immediately visible whether rules fired and how many products they touched.</td></tr>
            <tr><td><strong>Rule cleanup</strong></td><td>Added the missing <span class='mono'>DELETE /search/admin/rules/{'{'}id{'}'}</span> (rules previously had no way to be removed once created).</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> searching "boot" gave baseline order <span class='mono'>[SKU-192, SKU-197, SKU-172, SKU-162, SKU-187]</span>; after pinning SKU-187 and burying SKU-192, the same query returned <span class='mono'>[SKU-187, SKU-197, SKU-172, SKU-162, SKU-192]</span> -- pinned item moved to first, buried item moved to last, everything else kept its relative order. Confirmed the new delete endpoint correctly reverts <span class='mono'>merchandising.applied</span> back to false.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Autocomplete, typo tolerance, and query redirects</h2>
      <p class='text-secondary mb-2'>A gap analysis against Google Vertex AI Search for Retail's feature set flagged these as the platform's biggest missing category: query understanding beyond raw keyword matching. Three features close that gap, all bolted on as a separate layer without touching the core BM25 engine (same design principle as hybrid search and rerank).</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Feature</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Autocomplete</strong></td><td><span class='mono'>GET /search/autocomplete?query=...&amp;limit=...</span> (public, proxied via <span class='mono'>GET /v2/search/autocomplete</span> on the storefront) returns prefix-matched product title, category, and brand suggestions from a vocabulary rebuilt on every catalog ingest. Wired live into the WaveStore search box as a debounced (180ms) dropdown.</td></tr>
            <tr><td><strong>Suggestion diversification</strong></td><td>Patterned SKU-variant catalogs (e.g. "Summit Boot 102", "Summit Boot 117", "Summit Boot 122", ...) would otherwise flood autocomplete with near-duplicate suggestions. Titles are collapsed to one suggestion per "base" (trailing SKU number/size-color suffix stripped) before returning, mirroring Vertex's diversification concept.</td></tr>
            <tr><td><strong>Spelling correction / typo tolerance</strong></td><td>Query terms with zero matches anywhere in the indexed vocabulary are fuzzy-matched (<span class='mono'>difflib.get_close_matches</span>, stdlib, no new dependency) against real indexed terms and substituted before the lexical search runs (e.g. "jaket" &rarr; "jacket"). Applied only to the <em>lexical</em> path, not the vector-embedding query text -- embeddings already tolerate minor typos via subword similarity, and "correcting" a valid natural-language word based on a fuzzy string match risks corrupting a semantic query far more than it helps. <span class='mono'>spellCorrection</span> is returned in every <span class='mono'>/search/query</span> response for transparency.</td></tr>
            <tr><td><strong>Query redirects</strong></td><td><span class='mono'>POST /search/admin/rules</span>'s sibling for navigation: <span class='mono'>POST /search/admin/redirects</span> maps an exact (tokenized) query to a fixed URL (e.g. "summer sale" &rarr; <span class='mono'>/collections/summer-sale</span>), managed from a new <strong>Query redirects</strong> panel in Search Admin. Every <span class='mono'>/search/query</span> response includes a <span class='mono'>redirect</span> block so the storefront can choose to navigate instead of (or alongside) showing ranked results.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'><strong>Verified live:</strong> autocomplete for "sum" returns a single diversified "Summit Boot 102" suggestion (not 20 near-duplicates); autocomplete and full search for the misspelling "jaket" both correct to "jacket" and return the Aurora Storm Shell Jacket; a "summer sale" redirect was created, matched on the next search, and listed/removable via the admin API.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Two-tier category navbar (top-level + subcategories)</h2>
      <p class='text-secondary mb-2'>Catalog categories are hierarchical strings (e.g. <span class='mono'>"Outdoor &gt; Footwear &gt; Boots"</span>, <span class='mono'>"Outdoor &gt; Hiking"</span>). The storefront previously flattened every full path into one long top-level nav bar; it now groups by the first segment only, with a second bar of subcategories revealed underneath once a top-level category is selected.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Aspect</th><th>Detail</th></tr></thead>
          <tbody>
            <tr><td><strong>Category tree</strong></td><td>Built client-side from the loaded catalog: each hierarchical category string is split on <span class='mono'>&gt;</span>, grouped by its first segment, with the remainder mapped back to the original full path for exact filtering.</td></tr>
            <tr><td><strong>Top-level click</strong></td><td>Filters/searches by the top segment (e.g. "Outdoor") and reveals its subcategory bar underneath, if it has any children.</td></tr>
            <tr><td><strong>Subcategory click</strong></td><td>Filters/searches by the exact full category path (e.g. "Outdoor &gt; Hiking"), keeping the subcategory bar visible with that entry highlighted.</td></tr>
            <tr><td><strong>Filter wiring</strong></td><td>Category-nav clicks drive search through a dedicated override (<span class='mono'>state.navCategoryOverride</span>) rather than the manual category <span class='mono'>&lt;select&gt;</span>, since the dropdown only lists full leaf paths as options and can't represent a top-level-only selection; the override is cleared whenever the shopper interacts with the manual filters directly.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Promotions search index</h2>
      <p class='text-secondary mb-2'>Promotions/offers are indexed in-memory the same way products are: a per-tenant store plus a token-postings index built from each offer's title/subtitle/cta/category/brand/discount fields. This makes promotions a first-class searchable entity in WaveStore rather than only a client-side offer list.</p>
      <div class='table-responsive'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Endpoint</th><th>Purpose</th><th>Where visible</th></tr></thead>
          <tbody>
            <tr><td class='mono'>POST /search/ingest/promotions</td><td>Indexes a promotions list directly.</td><td>Fired automatically as part of Ingest from ERP.</td></tr>
            <tr><td class='mono'>POST /search/ingest/from-erp</td><td>Ingests the catalog and, best-effort, the ERP's <span class='mono'>/erp/offers</span> in the same action.</td><td><strong>Ingest from ERP</strong> button in Search Admin GUI.</td></tr>
            <tr><td class='mono'>POST /search/offers</td><td>Searches indexed promotions by query text; empty query returns all.</td><td>Proxied as <span class='mono'>POST /v2/offers/search</span> and surfaced as the <strong>Search offers</strong> box on the WaveStore home page.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'>Product-level linkage stays authoritative: each offer's <span class='mono'>productIds</span> list (set in ERP) still drives which products actually receive the discount when a shopper clicks through; the search index only makes the promotion itself discoverable by text.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Performance, cost, and horizontal scaling (measured, not estimated)</h2>
      <p class='text-secondary mb-2'>These figures were captured directly against the live <span class='mono'>wave-dev</span> <span class='mono'>wavesearch-api</span> pod (1 replica, 150m/1 vCPU request/limit, 384Mi/768Mi memory, catalog of 103 products), not modelled.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Path</th><th>Result</th><th>Notes</th></tr></thead>
          <tbody>
            <tr><td>Lexical/BM25 only (in-process, no HTTP)</td><td class='mono'>~61,000 req/s</td><td>Pure candidate retrieval + scoring cost; effectively free at this catalog size.</td></tr>
            <tr><td>Full HTTP path, AI disabled</td><td class='mono'>~550 req/s sustained, sub-2ms avg latency</td><td>Scales cleanly through 50 concurrent requests with zero failures on a single pod.</td></tr>
            <tr><td>Full HTTP path, AI reranking + intent classification enabled</td><td class='mono'>~1.0-1.8s avg latency/query</td><td>Down from ~4.7s after the reasoning/prompt optimization below; still bounded by the Azure OpenAI round-trip, not by the API itself.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-1'><strong>Current default: AI reranking and intent classification are switched OFF</strong> in <span class='mono'>wave-dev</span> to keep query latency low (sub-2ms instead of ~1-2s). Both can be re-enabled live, per feature, from the <strong>AI harness</strong> panel in the Search Admin GUI without a redeploy (backed by <span class='mono'>POST /search/admin/ai-toggle</span>), so the cost/latency-vs-relevance tradeoff is now an explicit operator decision rather than a fixed deployment setting.</p>
      <p class='text-secondary mb-1'><strong>AI-enabled latency optimization (3-4x faster, ~4.7s &rarr; ~1-1.8s):</strong> profiling the raw Azure OpenAI call in isolation found the model deployment, <span class='mono'>gpt-5-nano</span>, is a reasoning model that silently burns hidden "reasoning tokens" (~256 tokens, roughly 1s) before ever emitting the JSON answer &mdash; wasted cost for a deterministic rerank/classify task with no chain-of-thought benefit. Three changes were made in <span class='mono'>wavesearch_api/_llm_chat_json</span> and <span class='mono'>_rerank_results</span>: (1) set <span class='mono'>reasoning_effort=minimal</span> (env <span class='mono'>RETAIL_V2_LLM_REASONING_EFFORT</span>), which drove measured reasoning tokens to 0; (2) capped <span class='mono'>max_completion_tokens</span> (env <span class='mono'>RETAIL_V2_LLM_MAX_COMPLETION_TOKENS</span>, default 300) to bound worst-case generation length; (3) trimmed the rerank candidate payload sent per product (dropped description/availability/price, truncated title) and shortened the requested rationale to &le;15 words, cutting prompt tokens roughly in half (~1,818 &rarr; ~850 for a 20-candidate rerank). All three are independent, measured levers &mdash; verified via an isolated raw-call profiling script before and after, not guessed.</p>
      <p class='text-secondary mb-1'><strong>Reliability bug found and fixed during this benchmarking:</strong> the AI rerank/intent HTTP calls were originally made synchronously inside <span class='mono'>async def</span> handlers, which blocked the single shared event loop under concurrent load. At just 20 concurrent requests this made <span class='mono'>/healthz</span> stop responding and Kubernetes killed and restarted the pod. Fixed by moving those calls onto worker threads via <span class='mono'>asyncio.to_thread</span>, and by running rerank + intent classification <strong>concurrently</strong> (via <span class='mono'>asyncio.gather</span>) instead of sequentially, which also roughly halved AI-enabled latency (from ~9-10s to ~4.7s worst case, before the reasoning/prompt optimization above brought it down further to ~1-1.8s).</p>
      <p class='text-secondary mb-1'><strong>Can you run more than one instance in parallel?</strong> Yes for stateless read traffic, but with an important caveat today: merchandising rules, search diagnostics, and the ingested catalog runtime are held in <strong>process-local memory</strong> in each <span class='mono'>wavesearch-api</span> pod. Multiple replicas behind the same Kubernetes Service will each hold independent state — an ingest or rule change applied to one pod is invisible to the others until they are individually refreshed. Scaling replicas today is safe for pure query/recommend throughput, but not yet safe for consistent admin/ingest behavior.</p>
      <p class='text-secondary mb-0'><strong>Planned fix:</strong> move to a single-writer/multi-reader model — one writer replica owns ingest and rule mutation and publishes change notifications; reader replicas subscribe and refresh their local runtime, so read throughput can scale horizontally without state divergence.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm mb-3'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Search auth posture: public endpoint, cached tokens, CORS</h2>
      <p class='text-secondary mb-2'>Profiling the "in-memory search takes 1.4s?" question found the real cost wasn't the search itself (BM25 scoring is sub-millisecond) but the auth path wrapped around it: every single <span class='mono'>/v2/search</span> call from WaveStore minted a brand-new token via a full STS <span class='mono'>/sts/login</span> round-trip, including a 120,000-iteration PBKDF2-HMAC-SHA256 password verify, on every request.</p>
      <div class='table-responsive mb-2'>
        <table class='table table-sm align-middle'>
          <thead><tr><th>Change</th><th>Detail</th><th>Effect</th></tr></thead>
          <tbody>
            <tr><td><strong>Public search endpoints</strong></td><td><span class='mono'>POST /search/query</span>, <span class='mono'>/search/recommend</span>, and <span class='mono'>/search/offers</span> on <span class='mono'>wavesearch-api</span> no longer require a bearer token at all &mdash; they're read-only and already reachable by any anonymous shopper on the storefront, so requiring a signed JWT just to read the catalog added latency without adding real protection. Admin, ingest, and event-write endpoints are unchanged and still require an authenticated, scoped token.</td><td>WaveStore's <span class='mono'>do_search</span>/<span class='mono'>do_recommend</span>/<span class='mono'>do_search_offers</span> proxy calls no longer call STS at all for these paths.</td></tr>
            <tr><td><strong>CORS enabled</strong></td><td><span class='mono'>CORSMiddleware</span> added to <span class='mono'>wavesearch-api</span>, allowing <span class='mono'>store.retail.demos.wavefunctionlabs.com</span> (WaveStore) as an origin by default; configurable via <span class='mono'>WAVE_CORS_ORIGINS</span> (comma-separated).</td><td>Lets a browser call <span class='mono'>wavesearch-api</span> directly if needed, not only via the storefront's server-side proxy.</td></tr>
            <tr><td><strong>Token cache + longer TTL</strong></td><td>For the auth paths that remain (e.g. ERP offers), WaveStore's <span class='mono'>issue_token()</span> now caches tokens in-process per (audience, tenant, subject, scopes) and requests the maximum STS-allowed TTL of 3600s (up from a fresh 900s token every call), refreshing ~60s before expiry.</td><td>STS round-trips for those remaining calls drop from once-per-request to roughly once-per-hour per unique token key.</td></tr>
          </tbody>
        </table>
      </div>
      <p class='text-secondary mb-0'>Measured in-cluster after the fix: <span class='mono'>/v2/search</span> repeat calls run in ~3-4ms end-to-end (down from ~1.4s), with the one-time STS <span class='mono'>/sts/login</span> password verify itself confirmed at ~120ms in isolation &mdash; i.e. the fix was removing the round-trip from the hot path, not making the password hash faster.</p>
    </div>
  </div>

  <div class='card wave-card shadow-sm'>
    <div class='card-body'>
      <h2 class='h5 wave-accent'>Tuning levers exposed in Search Admin GUI</h2>
      <ul class='mb-0 text-secondary'>
        <li><strong>Merchandising rules:</strong> boost/bury/pin in Rules table and Rule modal.</li>
        <li><strong>Ingestion freshness:</strong> Ingest from ERP button (also indexes promotions).</li>
        <li><strong>Behavior simulation:</strong> simulated search/view/click event actions.</li>
        <li><strong>Ranking depth/input:</strong> query text, page size, recommend seed.</li>
        <li><strong>Feedback loop:</strong> analytics and config panels.</li>
        <li><strong>Explainability:</strong> Search Explorer pre/post AI diagnostics with rank-delta comparison.</li>
        <li><strong>AI cost/latency tradeoff:</strong> live rerank/intent toggles in the AI harness panel.</li>
        <li><strong>Retrieval strategy:</strong> hybrid lexical+vector toggle (AI harness panel) for semantic recall beyond keyword overlap.</li>
        <li><strong>Ingestion-time enrichment:</strong> LLM catalog enrichment toggle (AI harness panel) widens BM25/vector vocabulary once per product, off the per-query cost path.</li>
        <li><strong>Auth/latency posture:</strong> search/recommend/offers are public + CORS-enabled with no per-request STS round-trip; remaining authenticated calls use a cached, long-TTL token.</li>
      </ul>
    </div>
  </div>
</div>
<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>
<script>
  mermaid.initialize({ startOnLoad: true, theme: 'neutral' });
</script>
</body>
</html>"""


def create_app() -> FastAPI:
    app = FastAPI(title="WaveSearch Labs Frontend")
    sts = os.environ.get("WAVE_STS_URL", "http://127.0.0.1:8801")
    search_api = os.environ.get("WAVESEARCH_API_URL", "http://127.0.0.1:8803")
    erp_api = os.environ.get("WAVESTORE_ERP_API_URL", "http://127.0.0.1:8802")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavesearch-frontend"}

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host == "orchestrator.retail.demos.wavefunctionlabs.com":
            return HTMLResponse(merged_docs_html())
        return HTMLResponse(labs_html(sts, search_api, erp_api))
        html = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>WaveSearch Labs</title>
  <style>
    :root {{ --bg:#111; --panel:#1d1d1d; --soft:#171717; --line:#333; --text:#f5f5f5; --muted:#aaa; --accent:#fd8ea1; --accent-soft:#3a2028; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Segoe UI", Aptos, Calibri, sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
    .top {{ display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:16px; }}
    .brand {{ font-size:28px; font-weight:900; letter-spacing:-.04em; }}
    .panel {{ background: var(--panel); border:1px solid var(--line); border-radius:16px; padding:14px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    .muted {{ color: var(--muted); }}
    .stack {{ display:grid; gap:8px; }}
    input, textarea {{ width:100%; border:1px solid #444; border-radius:10px; padding:12px; background:var(--soft); color:var(--text); }}
    textarea {{ min-height:130px; font-family: Consolas, "Courier New", Courier, monospace; }}
    button {{ border:0; border-radius:10px; padding:11px 14px; background:var(--accent); color:#171717; font-weight:800; cursor:pointer; }}
    button.secondary {{ background:#2a2a2a; color:var(--text); border:1px solid #444; }}
    pre {{ margin:0; max-height:360px; overflow:auto; background:#0b0b0b; border:1px solid var(--line); border-radius:12px; padding:10px; color:var(--muted); }}
    a {{ color:var(--accent); text-decoration:none; }}
    @media (max-width: 980px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<div class='wrap'>
  <div class='top'>
    <div>
      <div class='brand'>WaveSearch Labs</div>
      <div class='muted'>Boost/bury controls, promotions, facets, analytics, and click-through stats.</div>
      <div><a href='/orchestrator' target='_blank' rel='noopener'>Open demo orchestrator</a> · <a href='/platform-guide' target='_blank' rel='noopener'>Open indexing/search/recommendations architecture guide</a></div>
    </div>
    <div class='stack' style='grid-template-columns:1fr 1fr 1fr auto auto; align-items:center;'>
      <input id='tenant' value='demo-tenant'>
      <input id='user' value='search.admin'>
      <input id='password' value='demo123!' type='password'>
      <button id='signIn'>Sign in</button>
      <span id='authState' class='muted'>Signed out</span>
    </div>
  </div>

  <div class='grid'>
    <div class='panel'>
      <h3>Ingestion + Query Test</h3>
      <div class='stack'>
        <button id='ingestFromErp'>Ingest catalog from ERP</button>
        <input id='query' value='jacket'>
        <button id='runQuery'>Run search query</button>
      </div>
    </div>
    <div class='panel'>
      <h3>Controls</h3>
      <textarea id='rule'>{{"id":"boost-wave-enterprise","actions":{{"boost":[{{"productId":"SKU-ENTERPRISE-001"}}],"bury":[{{"productId":"SKU-LOW-001"}}]}}}}</textarea>
      <div class='stack' style='margin-top:10px;'>
        <button id='saveRule'>Save boost/bury rule</button>
      </div>
    </div>
  </div>

  <div class='grid' style='margin-top:12px;'>
    <div class='panel'>
      <h3>Analytics</h3>
      <div class='stack'>
        <button class='secondary' id='loadAnalytics'>Load user analytics & clickthrough stats</button>
        <button class='secondary' id='loadConfig'>Load promotions/facets config</button>
      </div>
    </div>
    <div class='panel'>
      <h3>Output</h3>
      <pre id='out'></pre>
    </div>
  </div>
</div>
<script>
const cfg={{sts:'{sts}',search:'{search_api}',erp:'{erp_api}'}};let token='';let erpToken='';
async function signIn(){{const tenant=document.getElementById('tenant').value;const username=document.getElementById('user').value;const password=document.getElementById('password').value;const tokenReq=await fetch(cfg.sts+'/sts/login',{{method:'POST',headers:{{'Content-Type':'application/json','X-Tenant-Id':tenant}},body:JSON.stringify({{audience:'wavesearch-api',tenant,username,password,scopes:['search.query','search.admin','search.ingest','events.write']}})}});const tokenJson=await tokenReq.json();if(!tokenReq.ok)throw new Error(tokenJson.detail||'STS login failed');token=tokenJson.access_token||'';const erpReq=await fetch(cfg.sts+'/sts/login',{{method:'POST',headers:{{'Content-Type':'application/json','X-Tenant-Id':tenant}},body:JSON.stringify({{audience:'wavestore-erp-api',tenant,username,password,scopes:['erp.export']}})}});const erpJson=await erpReq.json();if(!erpReq.ok)throw new Error(erpJson.detail||'STS login failed');erpToken=erpJson.access_token||'';document.getElementById('authState').textContent=token&&erpToken?'Signed in':'Failed';}}
async function api(path,method='GET',body=null){{const r=await fetch(cfg.search+path,{{method,headers:{{'Content-Type':'application/json','Authorization':'Bearer '+token,'X-Tenant-Id':document.getElementById('tenant').value}},body:body?JSON.stringify(body):null}});document.getElementById('out').textContent=await r.text();}}
document.getElementById('ingestFromErp').addEventListener('click',()=>api('/search/ingest/from-erp','POST',{{erpCatalogUrl:cfg.erp+'/erp/export/catalog',erpToken}}));
document.getElementById('runQuery').addEventListener('click',()=>api('/search/query','POST',{{query:document.getElementById('query').value,pageSize:10}}));
document.getElementById('saveRule').addEventListener('click',()=>api('/search/admin/rules','POST',JSON.parse(document.getElementById('rule').value||'{{}}')));
document.getElementById('loadAnalytics').addEventListener('click',()=>api('/search/admin/analytics'));
document.getElementById('loadConfig').addEventListener('click',()=>api('/search/admin/config'));
document.getElementById('signIn').addEventListener('click',()=>signIn().catch(e=>alert(e.message)));
</script></body></html>"""
        return HTMLResponse(html)

    @app.get("/platform-guide", response_class=HTMLResponse)
    async def platform_guide() -> HTMLResponse:
        return HTMLResponse(merged_docs_html())

    @app.get("/orchestrator", response_class=HTMLResponse)
    async def orchestrator() -> HTMLResponse:
        return HTMLResponse(merged_docs_html())

    return app
