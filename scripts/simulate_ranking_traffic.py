"""Simulates realistic shopper traffic against wavesearch-api to exercise and verify the
tunable ranking-objective engine (heuristic ratio scoring AND the online two-tower ML model in
retail_v2.ml_ranker), end-to-end, against a real deployment.

What it does:
  1. Picks a "target" product that starts near the bottom of a baseline query's relevance order.
  2. Fires a batch of simulated view/click/add_to_cart/purchase events for that product from many
     distinct simulated visitors (via POST /search/events, the same endpoint the storefront's
     trackEvent() calls) -- enough to push the ML model for ctr/conversion/revenue past
     MIN_EVENTS_FOR_ML.
  3. For each objective (ctr, conversion, revenue), sets it via POST /search/admin/ranking-objective,
     re-runs the baseline query, and reports where the target product moved to plus whether
     GET /search/admin/ml-model reports the model as "ready" (i.e. actually driving the ranking,
     not falling back to the heuristic).
  4. Restores the objective to "relevance" and prints a PASS/FAIL summary.

Usage:
    python scripts/simulate_ranking_traffic.py --base-url https://search-api.retail.demos.wavefunctionlabs.com
    python scripts/simulate_ranking_traffic.py --base-url http://127.0.0.1:8803 --tenant demo-tenant --events 40

Requires: aiohttp (already a project dependency, see requirements.txt / other scripts/*.py).
"""

from __future__ import annotations

import argparse
import asyncio
import random
from typing import Any

import aiohttp


async def get_json(session: aiohttp.ClientSession, url: str, headers: dict[str, str]) -> Any:
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        return await response.json()


async def post_json(session: aiohttp.ClientSession, url: str, headers: dict[str, str], payload: Any) -> Any:
    async with session.post(url, headers=headers, json=payload) as response:
        response.raise_for_status()
        return await response.json()


async def fetch_admin_token(session: aiohttp.ClientSession, sts_url: str, username: str, password: str, tenant: str) -> str:
    # Admin endpoints (ranking-objective, ml-model, product-performance) require a real bearer
    # token with the search.admin scope -- search/query and search/events stay public/anonymous
    # (see public_search_context in wavesearch_api/app.py) since those are shopper-facing.
    body = await post_json(
        session, f"{sts_url.rstrip('/')}/sts/login", {}, {"username": username, "password": password, "audience": "wavesearch-api", "tenant": tenant}
    )
    return str(body["access_token"])


def _rank_of(results: list[dict[str, Any]], product_id: str) -> int | None:
    for index, row in enumerate(results):
        if str(row.get("id")) == product_id:
            return index
    return None


async def run(args: argparse.Namespace) -> int:
    base = args.base_url.rstrip("/")
    public_headers = {"X-Tenant-Id": args.tenant}
    async with aiohttp.ClientSession() as session:
        admin_token = await fetch_admin_token(session, args.sts_url, args.admin_user, args.admin_password, args.tenant)
        admin_headers = {"X-Tenant-Id": args.tenant, "Authorization": f"Bearer {admin_token}"}
        print(f"authenticated as {args.admin_user!r} against {args.sts_url} (scope includes search.admin)")

        print(f"\n== baseline query {args.query!r} (tenant={args.tenant}) ==")
        baseline = await post_json(session, f"{base}/search/query", public_headers, {"query": args.query, "pageSize": args.page_size})
        results = baseline.get("results") or []
        if len(results) < 3:
            print(f"FAIL: baseline query returned only {len(results)} results, need at least 3 to demonstrate a rank shift")
            return 1
        target = str(results[-1].get("id"))
        target_title = (results[-1].get("product") or {}).get("title", target)
        baseline_rank = _rank_of(results, target)
        print(f"target product: {target} ({target_title}) starts at rank #{baseline_rank + 1} of {len(results)}")

        # Restore to relevance first so events/objective changes from a prior run don't skew this one.
        await post_json(session, f"{base}/search/admin/ranking-objective", admin_headers, {"objective": "relevance"})

        print(f"\n== firing {args.events} simulated visitor sessions at {target} ==")
        rng = random.Random(42)
        for i in range(args.events):
            visitor_id = f"sim-visitor-{i:04d}"
            # Every simulated visitor views + clicks; a fraction also add-to-cart + purchase, so
            # the ctr model gets the most training signal, conversion/revenue get a realistic
            # smaller subset -- mirrors a typical view->click->cart->purchase drop-off funnel.
            await post_json(session, f"{base}/search/events", public_headers, {"visitorId": visitor_id, "eventType": "view", "productId": target})
            await post_json(session, f"{base}/search/events", public_headers, {"visitorId": visitor_id, "eventType": "click", "productId": target})
            if rng.random() < 0.6:
                await post_json(session, f"{base}/search/events", public_headers, {"visitorId": visitor_id, "eventType": "add_to_cart", "productId": target})
            if rng.random() < 0.4:
                await post_json(session, f"{base}/search/events", public_headers, {"visitorId": visitor_id, "eventType": "purchase", "productId": target})
        print("done firing events")

        model_stats = await get_json(session, f"{base}/search/admin/ml-model", admin_headers)
        print(f"\n== ML model stats (minEventsForMl={model_stats.get('minEventsForMl')}) ==")
        for objective, stats in model_stats.get("objectives", {}).items():
            print(f"  {objective:10s} eventsTrained={stats.get('eventsTrained'):>4}  ready={stats.get('ready')}  lossEma={stats.get('lossEma')}")

        perf = await get_json(session, f"{base}/search/admin/product-performance?limit=100", admin_headers)
        target_perf = next((row for row in perf.get("products", []) if row.get("productId") == target), None)
        print(f"\ntarget performance counters: {target_perf}")

        print("\n== objective sweep ==")
        overall_pass = True
        for objective in ("ctr", "conversion", "revenue"):
            await post_json(session, f"{base}/search/admin/ranking-objective", admin_headers, {"objective": objective})
            response = await post_json(session, f"{base}/search/query", public_headers, {"query": args.query, "pageSize": args.page_size})
            new_results = response.get("results") or []
            new_rank = _rank_of(new_results, target)
            meta = response.get("rankingObjective") or {}
            moved_up = new_rank is not None and baseline_rank is not None and new_rank < baseline_rank
            status = "PASS" if moved_up else "FAIL"
            overall_pass = overall_pass and moved_up
            print(
                f"  [{status}] objective={objective:10s} method={meta.get('method', '?'):9s} "
                f"applied={meta.get('applied')}  rank #{baseline_rank + 1} -> #{(new_rank or -1) + 1}"
            )

        # Always leave the tenant back on relevance ranking when the script exits.
        await post_json(session, f"{base}/search/admin/ranking-objective", admin_headers, {"objective": "relevance"})
        print(f"\n== {'ALL PASS' if overall_pass else 'SOME FAILED'} == (objective reset to relevance)")
        return 0 if overall_pass else 2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="https://search-api.retail.demos.wavefunctionlabs.com", help="wavesearch-api base URL")
    parser.add_argument("--sts-url", default="https://sts.retail.demos.wavefunctionlabs.com", help="wave-sts base URL, used to obtain a search.admin bearer token")
    parser.add_argument("--admin-user", default="search.admin", help="wave-sts username with the search.admin scope")
    parser.add_argument("--admin-password", default="demo123!", help="wave-sts password for --admin-user")
    parser.add_argument("--tenant", default="demo-tenant", help="X-Tenant-Id header value")
    parser.add_argument("--query", default="boot", help="baseline search query to rank the target product within")
    parser.add_argument("--events", type=int, default=100, help="number of simulated visitor sessions to fire (each visitor fires 2-4 events)")
    parser.add_argument("--page-size", type=int, default=10, help="page size for the baseline/verification query")
    args = parser.parse_args()
    exit_code = asyncio.run(run(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
