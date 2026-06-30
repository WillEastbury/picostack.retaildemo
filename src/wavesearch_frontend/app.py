from __future__ import annotations

import os

from fastapi import FastAPI
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
      <textarea id="rebuildPrompt" readonly>Create a demo-only retail search platform on AKS with six services: wave-sts, wavestore-erp-api, wavesearch-api, wavestore-frontend, wavestore-erp-frontend, wavesearch-frontend. Requirements: (1) zero-trust JWT auth with tenant isolation and scope-based authorization; (2) ERP is source of truth and exports catalog; (3) wavesearch-api ingests ERP catalog and serves /search/query and /search/recommend plus events and admin analytics/rules; (4) all services run as Kubernetes deployments/services in a wave-dev namespace; (5) ingress host routing under *.retail.demos.wavefunctionlabs.com through one shared ingress controller IP; (6) ARM-compatible in-cluster Kaniko builds into ACR; (7) docs and runbook for build, deploy, health checks, and smoke validation.</textarea>
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


def create_app() -> FastAPI:
    app = FastAPI(title="WaveSearch Labs Frontend")
    sts = os.environ.get("WAVE_STS_URL", "http://127.0.0.1:8801")
    search_api = os.environ.get("WAVESEARCH_API_URL", "http://127.0.0.1:8803")
    erp_api = os.environ.get("WAVESTORE_ERP_API_URL", "http://127.0.0.1:8802")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavesearch-frontend"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        html = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>WaveSearch Labs</title><link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/pulse/bootstrap.min.css'></head><body><div class='container py-4'>
<h1>WaveSearch Labs</h1><p class='text-body-secondary'>Boost/bury controls, promotions, facets, analytics, click-through stats.</p><p><a href='/platform-guide' target='_blank' rel='noopener'>Open indexing/search/recommendations architecture guide</a></p>
<div class='card mb-3'><div class='card-body row g-2'><div class='col-md-3'><input id='tenant' class='form-control' value='demo-tenant'></div><div class='col-md-3'><input id='user' class='form-control' value='search.admin'></div><div class='col-md-3'><button id='signIn' class='btn btn-primary w-100'>Sign in</button></div><div class='col-md-3 text-body-secondary d-flex align-items-center' id='authState'>Signed out</div></div></div>
<div class='row g-3'><div class='col-lg-6'><div class='card'><div class='card-header'>Ingestion + query test</div><div class='card-body d-grid gap-2'><button id='ingestFromErp' class='btn btn-outline-primary'>Ingest catalog from ERP</button><input id='query' class='form-control' value='jacket'><button id='runQuery' class='btn btn-outline-primary'>Run search query</button></div></div></div>
<div class='col-lg-6'><div class='card'><div class='card-header'>Controls</div><div class='card-body'><textarea id='rule' class='form-control mb-2' rows='6'>{{"id":"boost-wave-enterprise","actions":{{"boost":[{{"productId":"SKU-ENTERPRISE-001"}}],"bury":[{{"productId":"SKU-LOW-001"}}]}}}}</textarea><button id='saveRule' class='btn btn-outline-primary w-100'>Save boost/bury rule</button></div></div></div></div>
<div class='row g-3 mt-1'><div class='col-lg-6'><div class='card'><div class='card-header'>Analytics</div><div class='card-body d-grid gap-2'><button id='loadAnalytics' class='btn btn-secondary'>Load user analytics & clickthrough stats</button><button id='loadConfig' class='btn btn-secondary'>Load promotions/facets config</button></div></div></div><div class='col-lg-6'><div class='card'><div class='card-header'>Output</div><div class='card-body'><pre id='out' style='max-height:360px;overflow:auto' class='mb-0'></pre></div></div></div></div>
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

    return app
