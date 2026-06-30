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
            <li><strong>wavestore-frontend</strong>: shopper UI using search + recommendations and ERP order placement.</li>
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
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Wave Retail Demo Orchestrator</title>
  <style>
    :root { --bg:#111; --panel:#1d1d1d; --soft:#171717; --line:#333; --text:#f5f5f5; --muted:#aaa; --accent:#fd8ea1; --accent-soft:#3a2028; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", Aptos, Calibri, sans-serif; background: var(--bg); color: var(--text); }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .brand { font-size: 34px; font-weight: 900; letter-spacing: -.04em; margin: 0 0 6px; }
    .muted { color: var(--muted); }
    .panel { background: var(--panel); border:1px solid var(--line); border-radius:16px; padding:14px; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(260px,1fr)); gap:12px; }
    .card { background: var(--soft); border:1px solid var(--line); border-radius:12px; padding:12px; }
    .card h3 { margin: 0 0 8px; }
    .links { display:grid; gap:8px; margin-top:8px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    ul { margin: 0; padding-left: 18px; }
    li { margin: 6px 0; color: var(--muted); }
    .pill { display:inline-block; margin-right:8px; margin-bottom:8px; background: var(--accent-soft); color: var(--accent); border:1px solid var(--line); border-radius:999px; padding:4px 10px; font-size:12px; font-weight:700; }
  </style>
</head>
<body>
<div class='wrap'>
  <h1 class='brand'>Wave Retail Demo Orchestrator</h1>
  <p class='muted'>Single landing page for the demo platform: where to go, what each component does, and how indexing/search/recommendations flow through the system.</p>
  <div>
    <span class='pill'>Demo-only topology</span>
    <span class='pill'>AKS wave-dev</span>
    <span class='pill'>Kaniko in-cluster builds</span>
    <span class='pill'>STS + scoped JWTs</span>
  </div>

  <div class='panel' style='margin-top:12px;'>
    <h2 style='margin-top:0;'>Platform overview</h2>
    <ul>
      <li><strong>wave-sts</strong> issues audience-scoped tokens and enforces scope contracts.</li>
      <li><strong>wavestore-erp-api</strong> is source-of-truth for products, stock, pricing, orders, and catalog export.</li>
      <li><strong>wavesearch-api</strong> ingests ERP catalog snapshots, rebuilds runtime index, serves search/recommend APIs, and tracks events/analytics.</li>
      <li><strong>Frontends</strong>: storefront (shopper), ERP admin, and WaveSearch Labs operator UI.</li>
      <li><strong>Ingress</strong>: all hosts route through one shared nginx ingress public IP.</li>
    </ul>
  </div>

  <div class='grid' style='margin-top:12px;'>
    <div class='card'>
      <h3>Shopper experience</h3>
      <p class='muted'>Bootswatch storefront for demo shopping, recommendations, and order placement.</p>
      <div class='links'>
        <a href='https://store.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>store.retail.demos.wavefunctionlabs.com</a>
        <a href='https://storefront.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>storefront.retail.demos.wavefunctionlabs.com</a>
        <a href='https://voicedemo.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>voicedemo.demos.wavefunctionlabs.com</a>
      </div>
    </div>

    <div class='card'>
      <h3>ERP admin</h3>
      <p class='muted'>WaveFunction-style admin UI for catalog, stock, pricing, customers, orders, and invoices.</p>
      <div class='links'>
        <a href='https://erp.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>erp.retail.demos.wavefunctionlabs.com</a>
        <a href='https://erp-frontend.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>erp-frontend.retail.demos.wavefunctionlabs.com</a>
      </div>
    </div>

    <div class='card'>
      <h3>Search Labs + platform docs</h3>
      <p class='muted'>WaveFunction-style control UI for ingestion, merchandising, analytics, plus platform guide.</p>
      <div class='links'>
        <a href='https://labs.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>labs.retail.demos.wavefunctionlabs.com</a>
        <a href='https://labs-frontend.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>labs-frontend.retail.demos.wavefunctionlabs.com</a>
        <a href='/platform-guide' target='_blank' rel='noopener'>/platform-guide</a>
      </div>
    </div>

    <div class='card'>
      <h3>Original storefront (preserved)</h3>
      <p class='muted'>Legacy WaveStore/Pico Outfitters storefront from the earlier demo build, kept live for reference and comparison.</p>
      <div class='links'>
        <a href='https://store.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener'>Open original storefront</a>
      </div>
    </div>
  </div>

  <div class='grid' style='margin-top:12px;'>
    <div class='card'>
      <h3>Service endpoints</h3>
      <div class='links'>
        <a href='https://sts.retail.demos.wavefunctionlabs.com/healthz' target='_blank' rel='noopener'>STS health</a>
        <a href='https://search-api.retail.demos.wavefunctionlabs.com/healthz' target='_blank' rel='noopener'>Search API health</a>
        <a href='https://erp-api.retail.demos.wavefunctionlabs.com/healthz' target='_blank' rel='noopener'>ERP API health</a>
      </div>
    </div>
    <div class='card'>
      <h3>How data flows</h3>
      <ul>
        <li>ERP updates product/stock/pricing state.</li>
        <li>Labs calls <code>/search/ingest/from-erp</code> to pull ERP catalog export.</li>
        <li>WaveSearch rebuilds runtime index and serves query/recommend endpoints.</li>
        <li>Storefront consumes those APIs and posts events back for analytics.</li>
      </ul>
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
    <div class='stack' style='grid-template-columns:1fr 1fr auto auto; align-items:center;'>
      <input id='tenant' value='demo-tenant'>
      <input id='user' value='search.admin'>
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
async function signIn(){{const tenant=document.getElementById('tenant').value;const subject=document.getElementById('user').value;const tokenReq=await fetch(cfg.sts+'/sts/token',{{method:'POST',headers:{{'Content-Type':'application/json','X-Tenant-Id':tenant}},body:JSON.stringify({{audience:'wavesearch-api',tenant,subject,scopes:['search.query','search.admin','search.ingest','events.write']}})}});const tokenJson=await tokenReq.json();if(!tokenReq.ok)throw new Error(tokenJson.detail||'STS issue failed');token=tokenJson.access_token||'';const erpReq=await fetch(cfg.sts+'/sts/token',{{method:'POST',headers:{{'Content-Type':'application/json','X-Tenant-Id':tenant}},body:JSON.stringify({{audience:'wavestore-erp-api',tenant,subject,scopes:['erp.export']}})}});const erpJson=await erpReq.json();if(!erpReq.ok)throw new Error(erpJson.detail||'STS issue failed');erpToken=erpJson.access_token||'';document.getElementById('authState').textContent=token&&erpToken?'Signed in':'Failed';}}
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
