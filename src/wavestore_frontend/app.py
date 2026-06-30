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
  <title>WaveStore</title>
  <link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/pulse/bootstrap.min.css'>
  <style>
    body {{ background: #faf8f6; }}
    .topbar {{ border-bottom: 1px solid rgba(0,0,0,.08); background: #fff; }}
    .brand {{ font-weight: 700; letter-spacing: .4px; }}
    .category-strip {{ white-space: nowrap; overflow-x: auto; padding-bottom: 4px; }}
    .offer-rail {{ border: 1px dashed rgba(0,0,0,.18); border-radius: .75rem; }}
    .product-grid .card {{ min-height: 260px; }}
    .price-tag {{ font-size: 1.05rem; font-weight: 700; }}
    .muted-mini {{ font-size: .84rem; color: #6c757d; }}
  </style>
</head>
<body>
<header class='topbar mb-3'>
  <div class='container py-3'>
    <div class='d-flex justify-content-between align-items-center gap-3 flex-wrap'>
      <div class='brand fs-3'>WaveStore</div>
      <div class='d-flex align-items-center gap-2'>
        <input id='tenant' class='form-control form-control-sm' style='max-width:170px' value='demo-tenant' placeholder='Tenant'>
        <input id='user' class='form-control form-control-sm' style='max-width:170px' value='wave.shopper' placeholder='User'>
        <a href='https://orchestrator.retail.demos.wavefunctionlabs.com' target='_blank' rel='noopener' class='btn btn-sm btn-outline-secondary'>Demo Orchestrator</a>
        <button id='signIn' class='btn btn-sm btn-primary'>Sign in</button>
        <span id='authState' class='text-body-secondary small'>Signed out</span>
      </div>
    </div>
  </div>
</header>

<div class='container pb-4'>
  <div class='card mb-3'>
    <div class='card-body category-strip d-flex gap-2'>
      <button class='btn btn-outline-secondary btn-sm cat' data-q='jacket'>Jackets</button>
      <button class='btn btn-outline-secondary btn-sm cat' data-q='shoe'>Shoes</button>
      <button class='btn btn-outline-secondary btn-sm cat' data-q='jeans'>Jeans</button>
      <button class='btn btn-outline-secondary btn-sm cat' data-q='dress'>Dresses</button>
      <button class='btn btn-outline-secondary btn-sm cat' data-q='hoodie'>Hoodies</button>
      <button class='btn btn-outline-secondary btn-sm cat' data-q='summer'>Summer</button>
    </div>
  </div>

  <div class='card mb-3 offer-rail'>
    <div class='card-body py-2 d-flex justify-content-between align-items-center flex-wrap gap-2'>
      <div><strong>WaveStore Offers:</strong> 2-for-1 selected accessories · Free shipping over £40 · New customer 10% off</div>
      <button id='quickPromoSearch' class='btn btn-sm btn-outline-primary'>Show promo products</button>
    </div>
  </div>

  <div class='card mb-3'>
    <div class='card-body'>
      <div class='input-group'>
        <input id='query' class='form-control' value='jacket' placeholder='Search products, brands, categories'>
        <button id='searchBtn' class='btn btn-primary'>Search</button>
      </div>
    </div>
  </div>

  <div class='row g-3'>
    <div class='col-xl-9'>
      <div class='card'>
        <div class='card-header d-flex justify-content-between align-items-center'>
          <span>Products</span>
          <span id='resultCount' class='muted-mini'>0 items</span>
        </div>
        <div class='card-body'>
          <div id='results' class='row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3 product-grid'></div>
        </div>
      </div>
    </div>
    <div class='col-xl-3'>
      <div class='card mb-3'>
        <div class='card-header'>People also viewed</div>
        <div class='card-body'><div id='recs' class='list-group'></div></div>
      </div>
      <div class='card'>
        <div class='card-header'>Basket</div>
        <div class='card-body'>
          <div id='basket' class='list-group mb-3'></div>
          <div class='d-flex justify-content-between mb-2'><span>Total</span><strong id='basketTotal'>£0.00</strong></div>
          <button id='placeOrder' class='btn btn-success w-100'>Place order</button>
        </div>
      </div>
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
  document.getElementById('authState').textContent = 'Signed in as ' + document.getElementById('user').value;
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
  document.getElementById('resultCount').textContent = state.items.length + ' items';
  renderResults();
  if (state.items.length) {{
    const first = state.items[0].product || state.items[0];
    if (first && first.id) loadRecs(first.id);
  }}
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
    const price = Number((p.priceInfo||{{}}).price || p.price || 0).toFixed(2);
    const col = document.createElement('div');
    col.className = 'col';
    col.innerHTML = `<div class='card h-100'>
      <div class='card-body d-flex flex-column'>
        <div class='mb-2 muted-mini'>${{esc((p.brands||[]).join(', ') || 'WaveStore')}}</div>
        <h6 class='mb-2'>${{esc(p.title || p.id)}}</h6>
        <p class='muted-mini mb-3'>${{esc((p.categories||[]).join(' · ') || 'General')}}</p>
        <div class='mt-auto'>
          <div class='d-flex justify-content-between align-items-center mb-2'>
            <span class='price-tag'>£${{price}}</span>
            <span class='badge text-bg-light'>${{esc(p.id || '')}}</span>
          </div>
          <div class='btn-group w-100'>
            <button class='btn btn-outline-secondary btn-sm' data-rec='${{esc(p.id)}}'>Similar</button>
            <button class='btn btn-primary btn-sm' data-add='${{esc(p.id)}}'>Add to basket</button>
          </div>
        </div>
      </div>
    </div>`;
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
    const price = Number((p.priceInfo||{{}}).price || p.price || 0).toFixed(2);
    const row = document.createElement('button');
    row.className = 'list-group-item list-group-item-action';
    row.innerHTML = `<div class='d-flex justify-content-between align-items-start'>
      <span class='text-start'>${{esc(p.title || p.id)}}</span>
      <strong>£${{price}}</strong>
    </div>`;
    row.addEventListener('click', () => addToBasket(p));
    recs.appendChild(row);
  }}
}}

function renderBasket() {{
  const root = document.getElementById('basket');
  root.innerHTML = '';
  let total = 0;
  for (const item of state.basket) {{
    const src = state.items.map(x => x.product || x).find(x => x.id === item.productId) || {{}};
    const unit = Number((src.priceInfo||{{}}).price || src.price || 0);
    total += unit * item.quantity;
    const row = document.createElement('div');
    row.className = 'list-group-item d-flex justify-content-between align-items-center';
    row.innerHTML = `<span>${{esc(item.title)}}</span><span class='badge text-bg-primary'>${{item.quantity}}</span>`;
    root.appendChild(row);
  }}
  document.getElementById('basketTotal').textContent = '£' + total.toFixed(2);
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
document.getElementById('quickPromoSearch').addEventListener('click', () => {{
  document.getElementById('query').value = 'sale';
  search().catch(err => alert(err.message));
}});
for (const b of document.querySelectorAll('.cat')) {{
  b.addEventListener('click', () => {{
    document.getElementById('query').value = b.dataset.q || '';
    search().catch(err => alert(err.message));
  }});
}}
</script>
</body>
</html>"""
        return HTMLResponse(html)

    return app
