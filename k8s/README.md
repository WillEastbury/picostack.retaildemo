# WaveStore AKS Deployment

Kubernetes manifests for deploying all 6 Wave services to AKS.

## Architecture

```
┌─ wave-system namespace ─────────────────────────────────┐
│                                                          │
│  ┌─ Frontends ────────────┐   ┌─ Backends ──────────┐  │
│  │ wavestore-frontend     │   │ wave-sts (STS)      │  │
│  │ wavestore-erp-frontend │   │ wavestore-erp-api   │  │
│  │ wavesearch-frontend    │   │ wavesearch-api      │  │
│  └────────────────────────┘   └─────────────────────┘  │
│                                                          │
│  All services use:                                       │
│  - JWT auth from wave-sts (audience-scoped)             │
│  - Service-to-service discovery via DNS                 │
│  - X-Tenant-Id header for multi-tenant isolation        │
│  - ClusterIP services (no external exposure yet)        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Resource Requirements

| Service | Replicas | Memory Req | Memory Limit | CPU Req | CPU Limit |
|---------|----------|-----------|--------------|---------|-----------|
| wave-sts | 2 | 128Mi | 256Mi | 50m | 200m |
| wavestore-erp-api | 2 | 256Mi | 512Mi | 100m | 500m |
| wavesearch-api | 3 | 384Mi | 768Mi | 150m | 1000m |
| wavestore-frontend | 2 | 64Mi | 256Mi | 50m | 200m |
| wavestore-erp-frontend | 2 | 64Mi | 256Mi | 50m | 200m |
| wavesearch-frontend | 2 | 64Mi | 256Mi | 50m | 200m |
| **Total** | **13** | **960Mi (~0.94 GB)** | **2304Mi (~2.25 GB)** | **450m (0.5 cores)** | **2300m (2.3 cores)** |

## Requirements

- AKS cluster with at least 1 node (dev: 2GB RAM, 2 CPU; prod: 4 GB per node)
- kubectl configured to target your cluster
- Kustomize v4+ (included with kubectl v1.26+)
- Docker images pushed to ghcr.io under your account with tags

## Deployment

### 1. Create Namespace

```bash
kubectl create namespace wave-system
kubectl create namespace wave-dev   # for dev
kubectl create namespace wave-prod  # for prod
```

### 2. Deploy Base (or overlay)

**Dev (single replica per service):**
```bash
kubectl apply -k k8s/overlays/dev
```

**Production (higher replicas, pinned versions):**
```bash
kubectl apply -k k8s/overlays/prod
```

**Manual base:**
```bash
kubectl apply -k k8s/base
```

### 3. Verify Deployment

```bash
# Check pods
kubectl get pods -n wave-system

# Check services
kubectl get svc -n wave-system

# View logs from a specific service
kubectl logs -n wave-system deployment/wave-sts -f
```

## Local Testing (Port Forward)

```bash
# Forward each service to localhost
kubectl port-forward -n wave-system svc/wave-sts 8801:8801 &
kubectl port-forward -n wave-system svc/wavestore-erp-api 8802:8802 &
kubectl port-forward -n wave-system svc/wavesearch-api 8803:8803 &
kubectl port-forward -n wave-system svc/wavestore-frontend 8804:8804 &
kubectl port-forward -n wave-system svc/wavestore-erp-frontend 8805:8805 &
kubectl port-forward -n wave-system svc/wavesearch-frontend 8806:8806 &

# Then access locally:
# http://localhost:8804 - WaveStore Storefront
# http://localhost:8805 - WaveStore ERP Admin
# http://localhost:8806 - WaveSearch Labs Admin
```

## Container Image Requirements

> **Note (ARM cluster):** build images **in-cluster** for `linux/arm64`.  
> Local default `docker build` outputs can be `amd64` and will fail on ARM nodes (`exec format error`).

Each service Dockerfile is included in this repo and should be built from the repo root with `-f`:

```bash
docker build -f src/wave_sts/Dockerfile -t ghcr.io/willeastbury/wave-sts:latest .
docker build -f src/wavestore_erp_api/Dockerfile -t ghcr.io/willeastbury/wavestore-erp-api:latest .
docker build -f src/wavesearch_api/Dockerfile -t ghcr.io/willeastbury/wavesearch-labs-retail-search-api:latest .
docker build -f src/wavestore_frontend/Dockerfile -t ghcr.io/willeastbury/wavestore-frontend:latest .
docker build -f src/wavestore_erp_frontend/Dockerfile -t ghcr.io/willeastbury/wavestore-erp-frontend:latest .
docker build -f src/wavesearch_frontend/Dockerfile -t ghcr.io/willeastbury/wavesearch-labs-frontend:latest .

docker push ghcr.io/willeastbury/wave-sts:latest
docker push ghcr.io/willeastbury/wavestore-erp-api:latest
docker push ghcr.io/willeastbury/wavesearch-labs-retail-search-api:latest
docker push ghcr.io/willeastbury/wavestore-frontend:latest
docker push ghcr.io/willeastbury/wavestore-erp-frontend:latest
docker push ghcr.io/willeastbury/wavesearch-labs-frontend:latest
```

## Service Discovery & Auth

**Inside the cluster:**
- Services communicate via DNS: `http://<service-name>:port`
- Example: `http://wavesearch-api:8803/search/query`
- All services validate JWT tokens from `wave-sts`
- Tenant isolation via `X-Tenant-Id` header

**From outside (current):**
- `k8s/base/ingress-frontends.yaml` exposes all three frontends and routes same-origin `/sts`, `/search`, `/erp` API calls.
- Hosts:
  - `store.wave.local` -> WaveStore storefront + APIs
  - `erp.wave.local` -> ERP admin + APIs
  - `labs.wave.local` -> WaveSearch Labs admin + APIs
- Add DNS records or local `/etc/hosts` entries to your ingress external IP.

## Secrets Management

**Current (Dev/Demo only):**
- Secrets are stored in `k8s/base/secrets.yaml` with a placeholder
- **⚠️ DO NOT use in production**

**Production (recommended):**
- Use Azure KeyVault with workload identity
- Use Sealed Secrets or similar
- Rotate `WAVE_STS_SECRET` regularly

```bash
# Example with Azure KeyVault:
kubectl patch serviceaccount wave-sts -n wave-prod \
  -p '{"metadata":{"annotations":{"azure.workload.identity/client-id":"<client-id>"}}}'
```

## Monitoring & Observability

Each pod exposes `/healthz`:
- `/healthz` - wave-sts
- `/healthz` - wavestore-erp-api
- `/healthz` - wavesearch-api
- `/healthz` - all frontends

Kubernetes livenessProbe/readinessProbe automatically monitor these.

For deeper monitoring:
- Add Prometheus scrape targets
- Use Application Insights or similar
- Check pod logs: `kubectl logs -n wave-system <pod-name>`

## Scaling

```bash
# Scale a specific deployment
kubectl scale deployment/wavesearch-api -n wave-system --replicas=5

# Or edit the overlay and reapply:
# vim k8s/overlays/prod/kustomization.yaml
# kubectl apply -k k8s/overlays/prod
```

## Cleanup

```bash
kubectl delete namespace wave-system  # Deletes all Wave services
kubectl delete namespace wave-dev
kubectl delete namespace wave-prod
```

## Troubleshooting

### Pods not starting?
```bash
kubectl describe pod <pod-name> -n wave-system
kubectl logs <pod-name> -n wave-system
```

### Services not discovering each other?
```bash
# Check DNS from inside a pod:
kubectl run -it --rm debug --image=busybox -n wave-system -- nslookup wave-sts
```

### Slow startup?
- Image pull may take time; use `imagePullPolicy: IfNotPresent` locally
- Check node resources: `kubectl top nodes`

---

**Next:** Set ingress DNS records and replace the demo STS secret in `k8s/base/secrets.yaml`.
