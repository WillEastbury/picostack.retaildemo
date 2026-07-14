# AGENTS.md — picostack.retaildemo operating notes

> Purpose: durable operational knowledge for whoever (human or agent) next touches this repo's
> live AKS deployment (`store.retail.demos.wavefunctionlabs.com` and friends). See `k8s/README.md`
> for the full deployment reference; this file captures gotchas learned the hard way.

## Live deployment topology

- Namespace: `wave-dev` (there is also `wave-system`/`wave-prod` per `k8s/README.md`, but the
  public demo domains route through `wave-dev` — confirm with `kubectl get ingress --all-namespaces`).
- Deployments: `wave-sts`, `wavesearch-api`, `wavesearch-frontend`, `wavestore-erp-api`,
  `wavestore-erp-frontend`, `wavestore-frontend`.
- Registry: **`tileforgeacr.azurecr.io`** (an Azure Container Registry), not `ghcr.io` — the
  `images:` remap in `k8s/overlays/dev/kustomization.yaml` rewrites the base manifests'
  `ghcr.io/willeastbury/...` image names to `tileforgeacr.azurecr.io/...:dev` at apply time.
- Default tenant header for the storefront is `X-Tenant-Id: demo-tenant` (see
  `src/wavestore_frontend/app.py`'s `tenant_value()`), **not** `demo` — using the wrong tenant when
  testing the API directly can coincidentally still return results, which is misleading.
- The customer-facing storefront's entire HTML/JS is the single file **`telemetry-demo.html`** at
  the repo root, served via `_render_telemetry_page()` in `src/wavestore_frontend/app.py`
  (a simple `{{PAGE_MODE}}` string replace) — `app.py` itself is only ~700 lines of routing/API
  glue and does **not** contain the storefront's search/basket/checkout JS directly. Don't assume
  the JS you need is embedded in `app.py`; check `telemetry-demo.html`.

## AKS nodes are arm64 — always cross-build

`kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.nodeInfo.architecture}{"\n"}{end}'`
reports `arm64` for the `wave-dev` node pool. A `docker build` run locally on an amd64 workstation
silently produces an amd64 image; Kubernetes will schedule and start the pod fine, but the
container immediately dies with `exec format error` (visible via
`kubectl logs -n wave-dev <pod> --previous`) and the Deployment sits in `CrashLoopBackOff`.

**Never build locally for this cluster.** Build directly via ACR Tasks, which build in Azure
(no local Docker or QEMU emulation needed), and always pass `--platform linux/arm64` explicitly:

```powershell
cd C:\source\picostack.retaildemo
az acr build --registry tileforgeacr --image wavestore-frontend:dev `
  -f src/wavestore_frontend/Dockerfile --platform linux/arm64 .
```

Swap the `-f` Dockerfile path and `--image` name per service (see `k8s/README.md`'s image table).

If the streamed build log crashes the PowerShell console with
`UnicodeEncodeError: 'charmap' codec can't encode characters ...` — that's a `colorama`/cp1252
console-encoding bug in the Azure CLI itself, not a build failure. Set the console to UTF-8 and/or
suppress streaming, then check the final JSON for `"status": "Succeeded"`:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
az acr build --registry tileforgeacr --image wavestore-frontend:dev `
  -f src/wavestore_frontend/Dockerfile --platform linux/arm64 . --no-logs
```

After a successful build, ship it with a rollout restart (all Deployments here already run
`imagePullPolicy: Always`, so a restart is enough to re-pull the newly pushed `:dev` tag):

```powershell
kubectl -n wave-dev rollout restart deploy/wavestore-frontend
kubectl -n wave-dev rollout status deploy/wavestore-frontend --timeout=120s
```

Verify the new pod is healthy and actually serving the new code before considering the job done:

```powershell
kubectl get pods -n wave-dev -l app=wavestore-frontend
Invoke-WebRequest -Uri "https://store.retail.demos.wavefunctionlabs.com/" -UseBasicParsing |
  Select-String "<some string unique to your change>"
```

## Known-fixed bug (for reference)

`telemetry-demo.html`'s client-side search state had two independent "sticky filter" flags,
`state.activeOfferId` and `state.navCategoryOverride`. Every fresh-search entry point must clear
**both** — historically some entry points (search button, Enter key, autocomplete-suggestion
click, visual search, voice-query-from-URL) only cleared `activeOfferId`, leaving a stale
category-nav filter in place that silently narrowed unrelated keyword searches down to whatever
category was last browsed (e.g. a rain-jacket search returning only "coffee" because of a stale
"Grocery > Coffee" nav override). If similar "search returns wrong/narrow results" bugs recur,
check `readFilters()` and every call site that resets `state.activeOfferId` or
`state.navCategoryOverride` for the same asymmetry.
