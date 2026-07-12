import json, time, urllib.request

def call(url, method="GET", body=None, headers=None):
    h = headers or {}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode())
    return time.perf_counter() - t0, result

tenant = "demo-tenant"

# 1. Time STS login (password verify path) directly
dt, login = call("http://wave-sts:8801/sts/login", "POST",
             {"tenant": tenant, "username": "wave.user", "password": "demo123!",
              "audience": "wavesearch-api", "scopes": ["search.query", "events.write"]},
             {"Content-Type": "application/json", "X-Tenant-Id": tenant})
print("STS /sts/login (password verify) took %.1f ms" % (dt * 1000))
token = login["access_token"]

# 2. Time direct wavesearch-api query with pre-obtained token (in-cluster, no proxy hop)
H = {"Content-Type": "application/json", "X-Tenant-Id": tenant, "Authorization": "Bearer " + token}
dt, resp = call("http://wavesearch-api:8803/search/query", "POST", {"query": "jacket", "pageSize": 10, "filters": {}}, H)
print("Direct wavesearch-api /search/query took %.1f ms (ai enabled=%s)" % (dt * 1000, resp.get("ai", {}).get("enabled")))

# 3. Time the full storefront proxy path (wavestore-frontend -> STS login -> wavesearch-api)
dt, resp2 = call("http://wavestore-frontend:8804/v2/search", "POST", {"query": "jacket", "pageSize": 10, "filters": {}},
                  {"Content-Type": "application/json", "X-Tenant-Id": tenant})
print("Full /v2/search proxy path took %.1f ms" % (dt * 1000))

# 4. Repeat the full proxy path 5 times to see per-call token-issuance overhead
times = []
for _ in range(5):
    dt, _ = call("http://wavestore-frontend:8804/v2/search", "POST", {"query": "jacket", "pageSize": 10, "filters": {}},
                  {"Content-Type": "application/json", "X-Tenant-Id": tenant})
    times.append(dt * 1000)
print("Repeated /v2/search times (ms):", ["%.1f" % t for t in times])
