from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


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
<h1>WaveSearch Labs</h1><p class='text-body-secondary'>Boost/bury controls, promotions, facets, analytics, click-through stats.</p>
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

    return app
