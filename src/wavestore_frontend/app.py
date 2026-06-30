from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


def create_app() -> FastAPI:
    app = FastAPI(title="WaveStore Frontend")
    sts = os.environ.get("WAVE_STS_URL", "http://127.0.0.1:8801")
    search_api = os.environ.get("WAVESEARCH_API_URL", "http://127.0.0.1:8803")
    erp_api = os.environ.get("WAVESTORE_ERP_API_URL", "http://127.0.0.1:8802")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavestore-frontend"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        html = f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>WaveStore Frontend</title>
  <link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/pulse/bootstrap.min.css'>
</head>
<body>
<div class='container py-4'>
  <h1 class='mb-3'>WaveStore</h1>
  <p class='text-body-secondary'>Shopper UI using WaveSearch for search/recommendations and ERP for order placement.</p>

  <div class='card mb-3'><div class='card-body'>
    <div class='row g-2'>
      <div class='col-md-3'><input id='tenant' class='form-control' value='demo-tenant' placeholder='Tenant'></div>
      <div class='col-md-3'><input id='user' class='form-control' value='wave.shopper' placeholder='User'></div>
      <div class='col-md-6 d-flex gap-2'><button id='signIn' class='btn btn-primary'>Sign in via STS</button><span id='authState' class='text-body-secondary align-self-center'>Signed out</span></div>
    </div>
  </div></div>

  <div class='card mb-3'><div class='card-body'>
    <div class='input-group'>
      <input id='query' class='form-control' placeholder='Search products, brands, categories'>
      <button id='searchBtn' class='btn btn-primary'>Search</button>
    </div>
  </div></div>

  <div class='row g-3'>
    <div class='col-lg-8'>
      <div class='card'><div class='card-header'>Products</div><div class='card-body'><div id='results' class='row row-cols-1 row-cols-md-2 g-3'></div></div></div>
    </div>
    <div class='col-lg-4'>
      <div class='card mb-3'><div class='card-header'>Recommendations</div><div class='card-body'><div id='recs' class='list-group'></div></div></div>
      <div class='card'><div class='card-header'>Basket</div><div class='card-body'>
        <div id='basket' class='list-group mb-3'></div>
        <button id='placeOrder' class='btn btn-success w-100'>Place order</button>
      </div></div>
    </div>
  </div>
</div>
<script>
const cfg = {{ sts: '{sts}', searchApi: '{search_api}', erpApi: '{erp_api}' }};
const state = {{ searchToken: '', erpToken: '', items: [], basket: [] }};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));

async function tokenFor(audience, scopes) {{
  const body = {{ audience, tenant: document.getElementById('tenant').value, subject: document.getElementById('user').value, scopes }};
  const res = await fetch(cfg.sts + '/sts/token', {{ method:'POST', headers: {{'Content-Type':'application/json','X-Tenant-Id': document.getElementById('tenant').value}}, body: JSON.stringify(body) }});
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || 'STS error');
  return json.access_token;
}}

async function signIn() {{
  state.searchToken = await tokenFor('wavesearch-api', ['search.query','events.write']);
  state.erpToken = await tokenFor('wavestore-erp-api', ['erp.read','erp.order']);
  document.getElementById('authState').textContent = 'Signed in';
}}

async function search() {{
  const q = document.getElementById('query').value;
  const res = await fetch(cfg.searchApi + '/search/query', {{
    method:'POST',
    headers: {{'Content-Type':'application/json','Authorization':'Bearer ' + state.searchToken,'X-Tenant-Id': document.getElementById('tenant').value}},
    body: JSON.stringify({{ query: q, pageSize: 24 }})
  }});
  const json = await res.json();
  state.items = json.results || [];
  renderResults();
}}

function addToBasket(product) {{
  const existing = state.basket.find(x => x.productId === product.id);
  if (existing) existing.quantity += 1; else state.basket.push({{ productId: product.id, title: product.title, quantity: 1 }});
  renderBasket();
}}

function renderResults() {{
  const root = document.getElementById('results');
  root.innerHTML = '';
  for (const item of state.items) {{
    const p = item.product || item;
    const col = document.createElement('div');
    col.className = 'col';
    col.innerHTML = `<div class='card h-100'><div class='card-body'><h5>${{esc(p.title || p.id)}}</h5><p class='small text-body-secondary'>${{esc((p.categories||[]).join(', '))}}</p><div class='d-flex justify-content-between align-items-center'><strong>£${{Number((p.priceInfo||{{}}).price || p.price || 0).toFixed(2)}}</strong><div class='btn-group'><button class='btn btn-outline-secondary btn-sm' data-rec='${{esc(p.id)}}'>Rec</button><button class='btn btn-primary btn-sm' data-add='${{esc(p.id)}}'>Add</button></div></div></div></div>`;
    col.querySelector('[data-add]').addEventListener('click', () => addToBasket(p));
    col.querySelector('[data-rec]').addEventListener('click', () => loadRecs(p.id));
    root.appendChild(col);
  }}
}}

async function loadRecs(productId) {{
  const res = await fetch(cfg.searchApi + '/search/recommend', {{
    method:'POST',
    headers: {{'Content-Type':'application/json','Authorization':'Bearer ' + state.searchToken,'X-Tenant-Id': document.getElementById('tenant').value}},
    body: JSON.stringify({{ productId, pageSize: 6, visitorId: document.getElementById('user').value }})
  }});
  const json = await res.json();
  const recs = document.getElementById('recs');
  recs.innerHTML = '';
  for (const item of (json.results || [])) {{
    const p = item.product || item;
    const row = document.createElement('button');
    row.className = 'list-group-item list-group-item-action';
    row.textContent = `${{p.title || p.id}}`;
    row.addEventListener('click', () => addToBasket(p));
    recs.appendChild(row);
  }}
}}

function renderBasket() {{
  const root = document.getElementById('basket');
  root.innerHTML = '';
  for (const item of state.basket) {{
    const row = document.createElement('div');
    row.className = 'list-group-item d-flex justify-content-between align-items-center';
    row.innerHTML = `<span>${{esc(item.title)}}</span><span class='badge text-bg-primary'>${{item.quantity}}</span>`;
    root.appendChild(row);
  }}
}}

async function placeOrder() {{
  if (!state.basket.length) return;
  const res = await fetch(cfg.erpApi + '/erp/orders', {{
    method:'POST',
    headers: {{'Content-Type':'application/json','Authorization':'Bearer ' + state.erpToken,'X-Tenant-Id': document.getElementById('tenant').value}},
    body: JSON.stringify({{ customerId: document.getElementById('user').value, items: state.basket.map(x => ({{ productId: x.productId, quantity: x.quantity }})) }})
  }});
  const json = await res.json();
  alert(json.order ? `Order ${{json.order.id}} placed` : JSON.stringify(json));
  state.basket = [];
  renderBasket();
}}

document.getElementById('signIn').addEventListener('click', () => signIn().catch(err => alert(err.message)));
document.getElementById('searchBtn').addEventListener('click', () => search().catch(err => alert(err.message)));
document.getElementById('placeOrder').addEventListener('click', () => placeOrder().catch(err => alert(err.message)));
</script>
</body>
</html>"""
        return HTMLResponse(html)

    return app
