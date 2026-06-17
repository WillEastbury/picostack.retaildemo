#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/build"
mkdir -p "$OUT"

gcc -std=c11 -Wall -Wextra -Werror -fPIC -shared \
  -DPICOWAL_HOST=1 -DPICOWAL_NO_DEFAULT_STORE=1 \
  -I"$ROOT/src" \
  -I"$ROOT/../picowal/src" \
  -I"$ROOT/../picowal.retailprimitives/src" \
  "$ROOT/../picowal/src/picowal_api.c" \
  "$ROOT/../picowal/src/picowal_search.c" \
  "$ROOT/../picowal/src/picowal_store_fs.c" \
  "$ROOT/../picowal.retailprimitives/src/picowal_retail.c" \
  "$ROOT/src/demo_bridge.c" \
  -lm \
  -o "$OUT/libpicostack_retail_demo.so"

echo "$OUT/libpicostack_retail_demo.so"
