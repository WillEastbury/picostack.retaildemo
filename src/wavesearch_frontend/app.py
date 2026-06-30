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
            return HTMLResponse(orchestrator_html())
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
        return HTMLResponse(platform_guide_html())

    @app.get("/orchestrator", response_class=HTMLResponse)
    async def orchestrator() -> HTMLResponse:
        return HTMLResponse(orchestrator_html())

    return app
