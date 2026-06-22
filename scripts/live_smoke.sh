#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash scripts/build_demo_lib.sh >/tmp/picostack_build.out
python3 -m pip install --user --break-system-packages -q -r requirements.txt

PYTHONPATH=../picoweb/src:. python3 src/retail_asgi_server.py \
  --host 127.0.0.1 --port 8789 >/tmp/picostack_demo.out 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT

ready=0
for _ in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8789/ >/tmp/picostack_home.html 2>/tmp/picostack_curl.err; then
    ready=1
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    cat /tmp/picostack_demo.out
    exit 1
  fi
  sleep 0.5
done
if [ "$ready" != "1" ]; then
  cat /tmp/picostack_demo.out
  cat /tmp/picostack_curl.err
  exit 1
fi

curl -fsS -X POST http://127.0.0.1:8789/api/retail/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"waterproof jacket"}' >/tmp/picostack_search.json
curl -fsS http://127.0.0.1:8789/api/retail/voice/config >/tmp/picostack_voice.json
curl -fsS -X POST http://127.0.0.1:8789/api/product-service/products:generate \
  -H 'Content-Type: application/json' \
  -d '{"count":50,"seed":7}' >/tmp/picostack_generate.json
curl -fsS 'http://127.0.0.1:8789/api/product-service/products?offset=0&limit=5' >/tmp/picostack_product_page.json

grep -q "PicoStack Retail Search" /tmp/picostack_home.html
grep -q "results" /tmp/picostack_search.json
grep -q "find_items" /tmp/picostack_voice.json
grep -q "generated" /tmp/picostack_generate.json
grep -q "products" /tmp/picostack_product_page.json

kill "$pid"
wait "$pid" 2>/dev/null || true
trap - EXIT
echo "picostack retail demo live smoke ok"
