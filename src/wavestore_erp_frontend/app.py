from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


def create_app() -> FastAPI:
    app = FastAPI(title="WaveStore ERP Frontend")
    sts = os.environ.get("WAVE_STS_URL", "http://127.0.0.1:8801")
    erp_api = os.environ.get("WAVESTORE_ERP_API_URL", "http://127.0.0.1:8802")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavestore-erp-frontend"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        html = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>WaveStore ERP</title>
  <style>
    :root {{ --bg:#111; --panel:#1d1d1d; --soft:#171717; --line:#333; --text:#f5f5f5; --muted:#aaa; --accent:#fd8ea1; --accent-soft:#3a2028; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Segoe UI", Aptos, Calibri, sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
    .top {{ display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:16px; }}
    .brand {{ font-size:28px; font-weight:900; letter-spacing:-.04em; }}
    .panel {{ background: var(--panel); border:1px solid var(--line); border-radius:16px; padding:14px; }}
    .muted {{ color: var(--muted); }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:12px; }}
    .stack {{ display:grid; gap:8px; }}
    input, textarea {{ width:100%; border:1px solid #444; border-radius:10px; padding:12px; background:var(--soft); color:var(--text); }}
    textarea {{ min-height:180px; font-family: Consolas, "Courier New", Courier, monospace; }}
    button {{ border:0; border-radius:10px; padding:11px 14px; background:var(--accent); color:#171717; font-weight:800; cursor:pointer; }}
    button.secondary {{ background:#2a2a2a; color:var(--text); border:1px solid #444; }}
    pre {{ margin:0; max-height:360px; overflow:auto; background:#0b0b0b; border:1px solid var(--line); border-radius:12px; padding:10px; color:var(--muted); }}
    @media (max-width: 980px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<div class='wrap'>
  <div class='top'>
    <div>
      <div class='brand'>WaveStore ERP</div>
      <div class='muted'>WaveFunction-style admin UI for products, stock, pricing, offers, customers, orders, and invoices.</div>
    </div>
    <div class='stack' style='grid-template-columns:1fr 1fr auto auto; align-items:center;'>
      <input id='tenant' value='demo-tenant'>
      <input id='user' value='erp.admin'>
      <button id='signIn'>Sign in</button>
      <span id='authState' class='muted'>Signed out</span>
    </div>
  </div>

  <div class='grid'>
    <div class='panel'>
      <h3>Upsert commands</h3>
      <textarea id='payload'>{{"id":"SKU-ENTERPRISE-001","title":"Enterprise Demo Product","categories":["Demo"],"brands":["WaveStore"],"price":19.99,"availableQuantity":20}}</textarea>
      <div class='stack' style='margin-top:10px; grid-template-columns:1fr 1fr;'>
        <button data-act='products'>Upsert Product</button>
        <button data-act='stock'>Set Stock</button>
        <button data-act='pricing'>Set Pricing</button>
        <button data-act='offers'>Upsert Offer</button>
        <button data-act='customers'>Upsert Customer</button>
      </div>
    </div>

    <div class='panel'>
      <h3>Queries</h3>
      <div class='stack' style='grid-template-columns:1fr 1fr;'>
        <button class='secondary' data-get='products'>List Products</button>
        <button class='secondary' data-get='stock'>List Stock</button>
        <button class='secondary' data-get='pricing'>List Pricing</button>
        <button class='secondary' data-get='offers'>List Offers</button>
        <button class='secondary' data-get='customers'>List Customers</button>
        <button class='secondary' data-get='orders'>List Orders</button>
        <button class='secondary' data-get='invoices'>List Invoices</button>
      </div>
    </div>
  </div>

  <div class='panel' style='margin-top:12px;'>
    <h3>Output</h3>
    <pre id='out'></pre>
  </div>
</div>
<script>
const cfg={{sts:'{sts}',erp:'{erp_api}'}};let token='';
async function signIn(){{const r=await fetch(cfg.sts+'/sts/token',{{method:'POST',headers:{{'Content-Type':'application/json','X-Tenant-Id':document.getElementById('tenant').value}},body:JSON.stringify({{audience:'wavestore-erp-api',tenant:document.getElementById('tenant').value,subject:document.getElementById('user').value,scopes:['erp.read','erp.write','erp.order']}})}});const j=await r.json();token=j.access_token||'';document.getElementById('authState').textContent=token?'Signed in':'Failed';}}
async function call(path,method='GET',body=null){{const r=await fetch(cfg.erp+path,{{method,headers:{{'Content-Type':'application/json','Authorization':'Bearer '+token,'X-Tenant-Id':document.getElementById('tenant').value}},body:body?JSON.stringify(body):null}});const t=await r.text();document.getElementById('out').textContent=t;}}
for(const b of document.querySelectorAll('[data-get]')){{b.addEventListener('click',()=>call('/erp/'+b.dataset.get));}}
for(const b of document.querySelectorAll('[data-act]')){{b.addEventListener('click',()=>{{const p=JSON.parse(document.getElementById('payload').value||'{{}}');const map={{products:'/erp/products',stock:'/erp/stock:set',pricing:'/erp/pricing',offers:'/erp/offers',customers:'/erp/customers'}};call(map[b.dataset.act],'POST',p);}});}}
document.getElementById('signIn').addEventListener('click',()=>signIn().catch(e=>alert(e.message)));
</script></body></html>"""
        return HTMLResponse(html)

    return app
