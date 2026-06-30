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
        html = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>WaveStore ERP Frontend</title><link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/pulse/bootstrap.min.css'></head><body><div class='container py-4'>
<h1>WaveStore ERP</h1><p class='text-body-secondary'>GUI for Orders, Invoices, Products, Stock, Offers, Pricing, Customers.</p>
<div class='card mb-3'><div class='card-body row g-2'><div class='col-md-3'><input id='tenant' class='form-control' value='demo-tenant'></div><div class='col-md-3'><input id='user' class='form-control' value='erp.admin'></div><div class='col-md-3'><button id='signIn' class='btn btn-primary w-100'>Sign in</button></div><div class='col-md-3 text-body-secondary d-flex align-items-center' id='authState'>Signed out</div></div></div>
<div class='row g-3'><div class='col-lg-6'><div class='card'><div class='card-header'>Product / Stock / Pricing / Offers / Customer upsert</div><div class='card-body'><textarea id='payload' class='form-control mb-2' rows='8'>{{"id":"SKU-ENTERPRISE-001","title":"Enterprise Demo Product","categories":["Demo"],"brands":["WaveStore"],"price":19.99,"availableQuantity":20}}</textarea><div class='d-grid gap-2'><button class='btn btn-outline-primary' data-act='products'>Upsert Product</button><button class='btn btn-outline-primary' data-act='stock'>Set Stock</button><button class='btn btn-outline-primary' data-act='pricing'>Set Pricing</button><button class='btn btn-outline-primary' data-act='offers'>Upsert Offer</button><button class='btn btn-outline-primary' data-act='customers'>Upsert Customer</button></div></div></div></div>
<div class='col-lg-6'><div class='card'><div class='card-header'>Query</div><div class='card-body d-grid gap-2'><button class='btn btn-secondary' data-get='products'>List Products</button><button class='btn btn-secondary' data-get='stock'>List Stock</button><button class='btn btn-secondary' data-get='pricing'>List Pricing</button><button class='btn btn-secondary' data-get='offers'>List Offers</button><button class='btn btn-secondary' data-get='customers'>List Customers</button><button class='btn btn-secondary' data-get='orders'>List Orders</button><button class='btn btn-secondary' data-get='invoices'>List Invoices</button></div></div></div></div>
<div class='card mt-3'><div class='card-header'>Output</div><div class='card-body'><pre id='out' class='mb-0' style='max-height:360px;overflow:auto'></pre></div></div>
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
