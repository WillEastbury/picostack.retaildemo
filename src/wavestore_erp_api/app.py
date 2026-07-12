from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import Depends, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

from wave_shared.auth import context_from_auth, require_scope


@dataclass
class ERPState:
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    stock: dict[str, dict[str, Any]] = field(default_factory=dict)
    pricing: dict[str, dict[str, Any]] = field(default_factory=dict)
    offers: dict[str, dict[str, Any]] = field(default_factory=dict)
    customers: dict[str, dict[str, Any]] = field(default_factory=dict)
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    invoices: dict[str, dict[str, Any]] = field(default_factory=dict)
    # SAP-style hierarchies: a tree of named nodes (not just flat "A > B > C" category strings)
    # that products/customers can be assigned to, and that pricing condition records (see
    # /erp/pricing/conditions) and promotions can target at ANY level, not just a leaf. Two
    # separate namespaces -- "product" and "customer" -- but identical node shape, so the same
    # CRUD/resolution code (see _hierarchy_store/_node_path/_node_ancestors) serves both.
    product_hierarchy: dict[str, dict[str, Any]] = field(default_factory=dict)
    customer_hierarchy: dict[str, dict[str, Any]] = field(default_factory=dict)


class ERPStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = ERPState()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.state = ERPState(**{k: payload.get(k, {}) for k in ERPState.__dataclass_fields__.keys()})

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.state.__dict__, indent=2), encoding="utf-8")


def _cors_origins() -> list[str]:
    configured = os.environ.get("WAVE_CORS_ORIGINS")
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    return [
        "http://127.0.0.1:8805",
        "http://localhost:8805",
        "http://localhost:3000",
    ]


def create_app() -> FastAPI:
    app = FastAPI(title="WaveStore ERP API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    store = ERPStore(Path(os.environ.get("WAVESTORE_ERP_DATA") or (Path(os.getenv("TEMP") or ".") / "wavestore-erp-state.json")))

    # LLM catalog enrichment config (same Azure OpenAI/Foundry resource + gpt-5-nano deployment
    # used by wavesearch-api's rerank/intent/enrich features). Enriching here -- directly on the
    # ERP's own source-of-truth product records -- persists the improved description/categories
    # permanently, instead of wavesearch-api's per-ingest enrichment which only ever touched its
    # own transient in-memory copy and had to be redone on every re-ingest.
    llm_endpoint = str(os.environ.get("RETAIL_V2_LLM_ENDPOINT") or "").rstrip("/")
    llm_deployment = str(os.environ.get("RETAIL_V2_LLM_DEPLOYMENT") or "").strip()
    llm_api_version = str(os.environ.get("RETAIL_V2_LLM_API_VERSION") or "2025-01-01-preview").strip()
    llm_api_key = str(os.environ.get("RETAIL_V2_LLM_API_KEY") or "").strip()
    llm_reasoning_effort = str(os.environ.get("RETAIL_V2_LLM_REASONING_EFFORT") or "minimal").strip()
    llm_enrich_batch_size = max(1, int(os.environ.get("RETAIL_V2_LLM_ENRICH_BATCH_SIZE") or "15"))
    llm_enrich_max_concurrency = max(1, int(os.environ.get("RETAIL_V2_LLM_ENRICH_MAX_CONCURRENCY") or "6"))
    llm_enrich_timeout_seconds = max(5, int(os.environ.get("RETAIL_V2_LLM_ENRICH_TIMEOUT_SECONDS") or "60"))
    llm_enrich_max_completion_tokens = max(
        256, int(os.environ.get("RETAIL_V2_LLM_ENRICH_MAX_COMPLETION_TOKENS") or str(400 * llm_enrich_batch_size))
    )

    def _llm_available() -> bool:
        return bool(llm_endpoint and llm_deployment and llm_api_key)

    def _extract_json_object(raw_text: str) -> dict[str, Any]:
        text = (raw_text or "").strip()
        if not text:
            raise ValueError("empty LLM response")
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            parsed = json.loads(text[first : last + 1])
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("LLM response was not a JSON object")

    def _llm_chat_json(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        if not _llm_available():
            raise RuntimeError("LLM endpoint is not configured")
        url = f"{llm_endpoint}/openai/deployments/{llm_deployment}/chat/completions?api-version={llm_api_version}"
        base_body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
            ],
            "reasoning_effort": llm_reasoning_effort,
            "max_completion_tokens": llm_enrich_max_completion_tokens,
        }
        attempts = [
            {**base_body, "response_format": {"type": "json_object"}},
            base_body,
        ]
        payload: dict[str, Any] | None = None
        last_error: Exception | None = None
        for body in attempts:
            req = Request(
                url=url,
                method="POST",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "api-key": llm_api_key},
            )
            try:
                with urlopen(req, timeout=llm_enrich_timeout_seconds) as response:  # nosec B310 - trusted configured endpoint
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"LLM HTTP {exc.code}: {detail}")
                continue
            except URLError as exc:
                last_error = RuntimeError(f"LLM network error: {exc}")
                continue
        if payload is None:
            raise last_error or RuntimeError("LLM request failed")
        raw_content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _extract_json_object(raw_content)

    def _enrich_erp_products_batch(batch: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        # One LLM call enriches a whole batch of ERP products at once (id -> rewritten
        # description + refined categories), not one call per product.
        candidates = [
            {
                "id": product_id,
                "title": str(product.get("title") or "")[:120],
                "description": str(product.get("description") or "")[:300],
                "categories": list(product.get("categories") or []),
                "brands": list(product.get("brands") or []),
            }
            for product_id, product in batch
        ]
        system_prompt = (
            "You enrich retail ERP product records. For each product, return an improved 'description' "
            "(2-3 natural sentences) that keeps any existing facts and naturally weaves in features that are "
            "STANDARD/TYPICAL for this general category of product and commonly expected by shoppers, even if "
            "not stated (e.g. hiking boots are typically water-resistant with ankle support; winter jackets "
            "are typically insulated and wind-resistant) -- phrase these as typical/expected for the category, "
            "not as verified specifics (no invented exact ratings, certifications, or materials). Also return "
            "'categories': a refined/expanded list of 2-4 category tags (broader taxonomy terms useful for "
            "browsing/faceting, keeping any existing categories that are still accurate). Return strict JSON "
            "with key 'enrichments': array of {id (string), description (string), categories (array of "
            "strings)}, one entry per product id given, same order not required."
        )
        result = _llm_chat_json(system_prompt, {"products": candidates})
        rows = result.get("enrichments")
        by_id: dict[str, dict[str, Any]] = {}
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                product_id = str(row.get("id") or "").strip()
                if not product_id:
                    continue
                description = str(row.get("description") or "").strip()
                categories = row.get("categories")
                by_id[product_id] = {
                    "description": description,
                    "categories": [str(c).strip() for c in categories if str(c).strip()] if isinstance(categories, list) else [],
                }
        return by_id

    async def _enrich_erp_catalog(force: bool) -> dict[str, Any]:
        if not _llm_available():
            return {"enabled": False, "applied": False, "reason": "LLM endpoint is not configured"}
        candidates = [
            (product_id, product)
            for product_id, product in store.state.products.items()
            if force or not product.get("_llmEnriched")
        ]
        if not candidates:
            return {"enabled": True, "applied": False, "reason": "no products need enrichment (already enriched; pass force=true to re-run)"}
        batches = [candidates[i : i + llm_enrich_batch_size] for i in range(0, len(candidates), llm_enrich_batch_size)]
        semaphore = asyncio.Semaphore(llm_enrich_max_concurrency)

        async def _run_batch(batch: list[tuple[str, dict[str, Any]]]) -> tuple[dict[str, dict[str, Any]], str | None]:
            async with semaphore:
                try:
                    return await asyncio.to_thread(_enrich_erp_products_batch, batch), None
                except Exception as exc:
                    return {}, str(exc)

        batch_results = await asyncio.gather(*[_run_batch(batch) for batch in batches])
        enrichment_by_id: dict[str, dict[str, Any]] = {}
        batch_errors: list[str] = []
        for batch_result, batch_error in batch_results:
            enrichment_by_id.update(batch_result)
            if batch_error:
                batch_errors.append(batch_error)

        enriched_count = 0
        for product_id, enrichment in enrichment_by_id.items():
            product = store.state.products.get(product_id)
            if product is None:
                continue
            if enrichment.get("description"):
                product["description"] = enrichment["description"]
            if enrichment.get("categories"):
                existing = [str(c) for c in (product.get("categories") or [])]
                existing_lower = {c.strip().lower() for c in existing}
                merged = list(existing)
                for category in enrichment["categories"]:
                    if category.lower() not in existing_lower:
                        merged.append(category)
                        existing_lower.add(category.lower())
                product["categories"] = merged
            product["_llmEnriched"] = True
            enriched_count += 1
        if enriched_count:
            store._save()
        result = {
            "enabled": True,
            "applied": enriched_count > 0,
            "productsEnriched": enriched_count,
            "batches": len(batches),
        }
        if batch_errors:
            result["batchErrors"] = batch_errors[:5]
            result["batchErrorCount"] = len(batch_errors)
        return result

    def erp_context(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant_id: Annotated[str | None, Header()] = None,
    ):
        return context_from_auth("wavestore-erp-api", authorization=authorization, x_tenant_id=x_tenant_id, require_tenant_header=True)

    # --- Product & customer hierarchies (SAP-style: a real tree of named nodes, not a flat
    # category string) -- shared implementation for both namespaces. ---
    def _hierarchy_store(kind: str) -> dict[str, dict[str, Any]]:
        if kind == "product":
            return store.state.product_hierarchy
        if kind == "customer":
            return store.state.customer_hierarchy
        raise ValueError(f"unknown hierarchy kind: {kind}")

    def _node_ancestors(kind: str, node_id: str) -> list[str]:
        # Self-to-root chain (most specific first) -- exactly the order a SAP-style condition
        # record lookup needs to try: node itself, then its parent, then grandparent, etc.,
        # stopping at the first level that has a matching price/promotion rule.
        nodes = _hierarchy_store(kind)
        chain: list[str] = []
        current = node_id
        seen: set[str] = set()
        while current and current in nodes and current not in seen:
            seen.add(current)
            chain.append(current)
            current = nodes[current].get("parentId") or ""
        return chain

    def _node_path(kind: str, node_id: str) -> str:
        chain = _node_ancestors(kind, node_id)
        nodes = _hierarchy_store(kind)
        return " > ".join(nodes[n]["name"] for n in reversed(chain)) if chain else ""

    def _node_level(kind: str, node_id: str) -> int:
        return len(_node_ancestors(kind, node_id))

    def _decorated_node(kind: str, node: dict[str, Any]) -> dict[str, Any]:
        node_id = str(node.get("id") or "")
        return {**node, "path": _node_path(kind, node_id), "level": _node_level(kind, node_id)}

    def _hierarchy_children(kind: str, parent_id: str | None) -> list[dict[str, Any]]:
        nodes = _hierarchy_store(kind)
        parent_key = parent_id or None
        return [n for n in nodes.values() if (n.get("parentId") or None) == parent_key]

    def _upsert_hierarchy_node(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        nodes = _hierarchy_store(kind)
        node_id = str(payload.get("id") or f"{kind}-node-{uuid4().hex[:8]}")
        parent_id = payload.get("parentId") or None
        if parent_id and parent_id not in nodes:
            raise ValueError(f"parentId {parent_id!r} does not exist in the {kind} hierarchy")
        if parent_id == node_id:
            raise ValueError("a node cannot be its own parent")
        # Prevent cycles: the new parent can't be a descendant of this node (walk the candidate
        # parent's own ancestor chain and make sure this node doesn't appear in it).
        if parent_id:
            ancestor_ids = _node_ancestors(kind, parent_id)
            if node_id in ancestor_ids:
                raise ValueError("assigning that parent would create a cycle in the hierarchy")
        row = {"id": node_id, "name": str(payload.get("name") or node_id), "parentId": parent_id}
        nodes[node_id] = row
        store._save()
        return _decorated_node(kind, row)

    def _delete_hierarchy_node(kind: str, node_id: str) -> dict[str, Any]:
        nodes = _hierarchy_store(kind)
        if node_id not in nodes:
            return {"error": "node not found"}
        if _hierarchy_children(kind, node_id):
            return {"error": "cannot delete a node with children -- delete or reparent its children first"}
        entity_field = "hierarchyNodeId"
        assigned = [
            entity_id
            for entity_id, entity in (store.state.products if kind == "product" else store.state.customers).items()
            if entity.get(entity_field) == node_id
        ]
        if assigned:
            return {"error": f"cannot delete a node with {len(assigned)} {kind}(s) still assigned to it -- reassign them first"}
        removed = nodes.pop(node_id)
        store._save()
        return {"accepted": True, "deleted": removed}

    def _decorate_entity_hierarchy(kind: str, entity: dict[str, Any]) -> dict[str, Any]:
        # Adds a read-only "hierarchyPath"/"hierarchyAncestorIds" view onto a product/customer
        # record for convenience (e.g. the ERP admin UI showing "Outdoor > Footwear > Boots"
        # instead of just a raw node id) -- the stored record itself only keeps hierarchyNodeId.
        node_id = entity.get("hierarchyNodeId")
        if not node_id or node_id not in _hierarchy_store(kind):
            return entity
        return {**entity, "hierarchyPath": _node_path(kind, node_id), "hierarchyAncestorIds": _node_ancestors(kind, node_id)}

    def _normalize_product_id(value: str) -> str:
        return value.strip().lower()

    def _find_by_product_id(rows: dict[str, dict[str, Any]], product_id: str) -> dict[str, Any] | None:
        if product_id in rows:
            return rows[product_id]
        normalized = _normalize_product_id(product_id)
        for key, row in rows.items():
            if _normalize_product_id(key) == normalized:
                return row
            row_product_id = str(row.get("productId") or row.get("id") or "")
            if row_product_id and _normalize_product_id(row_product_id) == normalized:
                return row
        return None

    def _resolve_item_price(product_id: str, item_price: Any = None) -> float:
        if item_price is not None:
            try:
                return float(item_price)
            except (TypeError, ValueError):
                pass
        pricing_row = _find_by_product_id(store.state.pricing, product_id)
        if pricing_row:
            try:
                return float(pricing_row.get("price") or 0.0)
            except (TypeError, ValueError):
                pass
        product_row = _find_by_product_id(store.state.products, product_id)
        if product_row:
            if isinstance(product_row.get("priceInfo"), dict):
                try:
                    return float(product_row["priceInfo"].get("price") or 0.0)
                except (TypeError, ValueError):
                    pass
            try:
                return float(product_row.get("price") or 0.0)
            except (TypeError, ValueError):
                pass
        return 0.0

    def _normalize_order_items(items: list[Any]) -> tuple[list[dict[str, Any]], float]:
        total = 0.0
        normalized_items: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            product_id = str(item.get("productId") or "")
            qty = max(1, int(item.get("quantity") or 1))
            price = _resolve_item_price(product_id, item.get("price"))
            total += qty * price
            normalized_items.append({"productId": product_id, "quantity": qty, "price": price})
        return normalized_items, round(total, 2)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavestore-erp-api"}

    # --- Product & customer hierarchies ---
    @app.get("/erp/hierarchy/{kind}")
    async def list_hierarchy(kind: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        if kind not in ("product", "customer"):
            return {"error": "kind must be 'product' or 'customer'"}
        nodes = _hierarchy_store(kind)
        decorated = [_decorated_node(kind, n) for n in nodes.values()]
        decorated.sort(key=lambda n: (n["level"], n["path"]))
        return {"kind": kind, "nodes": decorated}

    @app.post("/erp/hierarchy/{kind}")
    async def upsert_hierarchy_node(kind: str, payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        if kind not in ("product", "customer"):
            return {"error": "kind must be 'product' or 'customer'"}
        try:
            node = _upsert_hierarchy_node(kind, payload)
        except ValueError as exc:
            return {"error": str(exc)}
        return {"accepted": True, "node": node}

    @app.get("/erp/hierarchy/{kind}/{node_id}")
    async def get_hierarchy_node(kind: str, node_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        if kind not in ("product", "customer"):
            return {"error": "kind must be 'product' or 'customer'"}
        nodes = _hierarchy_store(kind)
        row = nodes.get(node_id)
        if not row:
            return {"error": "node not found"}
        decorated = _decorated_node(kind, row)
        decorated["children"] = [_decorated_node(kind, c) for c in _hierarchy_children(kind, node_id)]
        decorated["ancestorIds"] = _node_ancestors(kind, node_id)
        return {"node": decorated}

    @app.delete("/erp/hierarchy/{kind}/{node_id}")
    async def delete_hierarchy_node_endpoint(kind: str, node_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        if kind not in ("product", "customer"):
            return {"error": "kind must be 'product' or 'customer'"}
        return _delete_hierarchy_node(kind, node_id)

    @app.get("/erp/products")
    async def list_products(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        rows = sorted(store.state.products.values(), key=lambda p: p.get("id", ""))
        return {"products": [_decorate_entity_hierarchy("product", p) for p in rows]}

    @app.post("/erp/products")
    async def upsert_product(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        product_id = str(payload.get("id") or payload.get("sku") or "").strip()
        if not product_id:
            return {"error": "id is required"}
        hierarchy_node_id = payload.get("hierarchyNodeId")
        if hierarchy_node_id and hierarchy_node_id not in store.state.product_hierarchy:
            return {"error": f"hierarchyNodeId {hierarchy_node_id!r} does not exist in the product hierarchy"}
        merged = {"id": product_id, **payload}
        store.state.products[product_id] = merged
        if product_id not in store.state.stock:
            store.state.stock[product_id] = {"productId": product_id, "availableQuantity": int(payload.get("availableQuantity") or 0), "availability": str(payload.get("availability") or "IN_STOCK")}
        if product_id not in store.state.pricing:
            price = payload.get("price")
            if price is None and isinstance(payload.get("priceInfo"), dict):
                price = payload["priceInfo"].get("price")
            store.state.pricing[product_id] = {"productId": product_id, "price": float(price or 0.0), "currencyCode": str(payload.get("currencyCode") or "GBP")}
        store._save()
        return {"accepted": True, "product": _decorate_entity_hierarchy("product", merged)}

    @app.get("/erp/products/{product_id}")
    async def get_product(product_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        row = store.state.products.get(product_id)
        if not row:
            return {"error": "product not found"}
        return {"product": row}

    @app.delete("/erp/products/{product_id}")
    async def delete_product(product_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        row = store.state.products.pop(product_id, None)
        if not row:
            return {"error": "product not found"}
        store.state.stock.pop(product_id, None)
        store.state.pricing.pop(product_id, None)
        store._save()
        return {"accepted": True, "deleted": product_id}

    @app.get("/erp/stock")
    async def list_stock(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"stock": sorted(store.state.stock.values(), key=lambda s: s.get("productId", ""))}

    @app.post("/erp/stock:set")
    async def set_stock(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        product_id = str(payload.get("productId") or "").strip()
        if not product_id:
            return {"error": "productId is required"}
        row = {
            "productId": product_id,
            "availableQuantity": int(payload.get("availableQuantity") or 0),
            "availability": str(payload.get("availability") or ("OUT_OF_STOCK" if int(payload.get("availableQuantity") or 0) <= 0 else "IN_STOCK")),
        }
        store.state.stock[product_id] = row
        store._save()
        return {"accepted": True, "stock": row}

    @app.get("/erp/pricing")
    async def list_pricing(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"pricing": sorted(store.state.pricing.values(), key=lambda s: s.get("productId", ""))}

    @app.post("/erp/pricing")
    async def upsert_pricing(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        product_id = str(payload.get("productId") or "").strip()
        if not product_id:
            return {"error": "productId is required"}
        row = {"productId": product_id, "price": float(payload.get("price") or 0.0), "currencyCode": str(payload.get("currencyCode") or "GBP")}
        store.state.pricing[product_id] = row
        store._save()
        return {"accepted": True, "pricing": row}

    @app.get("/erp/offers")
    async def list_offers(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"offers": sorted(store.state.offers.values(), key=lambda s: s.get("id", ""))}

    @app.post("/erp/offers")
    async def upsert_offer(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        offer_id = str(payload.get("id") or f"offer-{uuid4().hex[:8]}")
        row = {"id": offer_id, **payload}
        store.state.offers[offer_id] = row
        store._save()
        return {"accepted": True, "offer": row}

    @app.get("/erp/offers/{offer_id}")
    async def get_offer(offer_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        row = store.state.offers.get(offer_id)
        if not row:
            return {"error": "offer not found"}
        return {"offer": row}

    @app.delete("/erp/offers/{offer_id}")
    async def delete_offer(offer_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        row = store.state.offers.pop(offer_id, None)
        if not row:
            return {"error": "offer not found"}
        store._save()
        return {"accepted": True, "deleted": offer_id}

    @app.get("/erp/promotions")
    async def list_promotions(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        return {"promotions": sorted(store.state.offers.values(), key=lambda s: s.get("id", ""))}

    @app.post("/erp/promotions")
    async def upsert_promotion(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        promotion_id = str(payload.get("id") or f"promo-{uuid4().hex[:8]}")
        row = {"id": promotion_id, **payload}
        store.state.offers[promotion_id] = row
        store._save()
        return {"accepted": True, "promotion": row}

    @app.get("/erp/promotions/{promotion_id}")
    async def get_promotion(promotion_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        row = store.state.offers.get(promotion_id)
        if not row:
            return {"error": "promotion not found"}
        return {"promotion": row}

    @app.delete("/erp/promotions/{promotion_id}")
    async def delete_promotion(promotion_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        row = store.state.offers.pop(promotion_id, None)
        if not row:
            return {"error": "promotion not found"}
        store._save()
        return {"accepted": True, "deleted": promotion_id}

    @app.get("/erp/customers")
    async def list_customers(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        rows = sorted(store.state.customers.values(), key=lambda c: c.get("id", ""))
        return {"customers": [_decorate_entity_hierarchy("customer", c) for c in rows]}

    @app.post("/erp/customers")
    async def upsert_customer(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        customer_id = str(payload.get("id") or f"cust-{uuid4().hex[:8]}")
        hierarchy_node_id = payload.get("hierarchyNodeId")
        if hierarchy_node_id and hierarchy_node_id not in store.state.customer_hierarchy:
            return {"error": f"hierarchyNodeId {hierarchy_node_id!r} does not exist in the customer hierarchy"}
        row = {"id": customer_id, **payload}
        store.state.customers[customer_id] = row
        store._save()
        return {"accepted": True, "customer": _decorate_entity_hierarchy("customer", row)}

    @app.get("/erp/customers/{customer_id}")
    async def get_customer(customer_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        row = store.state.customers.get(customer_id)
        if not row:
            return {"error": "customer not found"}
        return {"customer": _decorate_entity_hierarchy("customer", row)}

    @app.delete("/erp/customers/{customer_id}")
    async def delete_customer(customer_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        row = store.state.customers.pop(customer_id, None)
        if not row:
            return {"error": "customer not found"}
        store._save()
        return {"accepted": True, "deleted": customer_id}

    @app.get("/erp/orders")
    async def list_orders(customerId: str | None = None, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        rows = list(store.state.orders.values())
        if customerId:
            rows = [row for row in rows if str(row.get("customerId") or "") == customerId]
        repaired = False
        for row in rows:
            items = row.get("items")
            if not isinstance(items, list):
                continue
            normalized_items, total = _normalize_order_items(items)
            if normalized_items != items or round(float(row.get("total") or 0.0), 2) != total:
                row["items"] = normalized_items
                row["total"] = total
                repaired = True
        if repaired:
            invoice_by_order_id = {
                str(invoice.get("orderId") or ""): invoice
                for invoice in store.state.invoices.values()
                if isinstance(invoice, dict)
            }
            for row in rows:
                invoice = invoice_by_order_id.get(str(row.get("id") or ""))
                if invoice:
                    invoice["amount"] = round(float(row.get("total") or 0.0), 2)
            store._save()
        rows.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return {"orders": rows}

    @app.post("/erp/orders")
    async def place_order(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.order")
        customer_id = str(payload.get("customerId") or "guest")
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        if not items:
            return {"error": "items are required"}
        order_id = f"ord-{uuid4().hex[:10]}"
        normalized_items, total = _normalize_order_items(items)
        for item in normalized_items:
            product_id = str(item.get("productId") or "")
            qty = max(1, int(item.get("quantity") or 1))
            stock_row = store.state.stock.get(product_id)
            if stock_row:
                stock_row["availableQuantity"] = max(0, int(stock_row.get("availableQuantity") or 0) - qty)
                stock_row["availability"] = "IN_STOCK" if stock_row["availableQuantity"] > 0 else "OUT_OF_STOCK"
        order = {"id": order_id, "customerId": customer_id, "items": normalized_items, "status": "PLACED", "total": total, "currencyCode": "GBP", "createdAt": __import__("datetime").datetime.utcnow().isoformat() + "Z"}
        invoice_id = f"inv-{uuid4().hex[:10]}"
        invoice = {"id": invoice_id, "orderId": order_id, "customerId": customer_id, "status": "OPEN", "amount": order["total"], "currencyCode": "GBP", "createdAt": order["createdAt"]}
        store.state.orders[order_id] = order
        store.state.invoices[invoice_id] = invoice
        store._save()
        return {"accepted": True, "order": order, "invoice": invoice}

    @app.get("/erp/orders/{order_id}")
    async def get_order(order_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        row = store.state.orders.get(order_id)
        if not row:
            return {"error": "order not found"}
        return {"order": row}

    @app.put("/erp/orders/{order_id}")
    async def update_order(order_id: str, payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        existing = store.state.orders.get(order_id)
        if not existing:
            return {"error": "order not found"}
        updated = {**existing, **payload, "id": order_id}
        if isinstance(updated.get("items"), list):
            normalized_items, total = _normalize_order_items(updated["items"])
            updated["items"] = normalized_items
            updated["total"] = total
        store.state.orders[order_id] = updated
        store._save()
        return {"accepted": True, "order": updated}

    @app.delete("/erp/orders/{order_id}")
    async def delete_order(order_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        row = store.state.orders.pop(order_id, None)
        if not row:
            return {"error": "order not found"}
        invoice_ids = [invoice_id for invoice_id, invoice in store.state.invoices.items() if str(invoice.get("orderId") or "") == order_id]
        for invoice_id in invoice_ids:
            store.state.invoices.pop(invoice_id, None)
        store._save()
        return {"accepted": True, "deleted": order_id}

    @app.get("/erp/invoices")
    async def list_invoices(customerId: str | None = None, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        rows = list(store.state.invoices.values())
        if customerId:
            rows = [row for row in rows if str(row.get("customerId") or "") == customerId]
        rows.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return {"invoices": rows}

    @app.post("/erp/invoices")
    async def upsert_invoice(payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        invoice_id = str(payload.get("id") or f"inv-{uuid4().hex[:10]}")
        row = {"id": invoice_id, **payload}
        store.state.invoices[invoice_id] = row
        store._save()
        return {"accepted": True, "invoice": row}

    @app.get("/erp/invoices/{invoice_id}")
    async def get_invoice(invoice_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.read")
        row = store.state.invoices.get(invoice_id)
        if not row:
            return {"error": "invoice not found"}
        return {"invoice": row}

    @app.put("/erp/invoices/{invoice_id}")
    async def update_invoice(invoice_id: str, payload: dict[str, Any], context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        existing = store.state.invoices.get(invoice_id)
        if not existing:
            return {"error": "invoice not found"}
        row = {**existing, **payload, "id": invoice_id}
        store.state.invoices[invoice_id] = row
        store._save()
        return {"accepted": True, "invoice": row}

    @app.delete("/erp/invoices/{invoice_id}")
    async def delete_invoice(invoice_id: str, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        row = store.state.invoices.pop(invoice_id, None)
        if not row:
            return {"error": "invoice not found"}
        store._save()
        return {"accepted": True, "deleted": invoice_id}

    @app.get("/erp/export/catalog")
    async def export_catalog(context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.export")
        products = []
        for product_id, product in store.state.products.items():
            stock = store.state.stock.get(product_id, {})
            pricing = store.state.pricing.get(product_id, {})
            products.append({
                "id": product_id,
                "title": str(product.get("title") or product_id),
                "description": str(product.get("description") or ""),
                "categories": list(product.get("categories") or []),
                "brands": list(product.get("brands") or []),
                "tags": list(product.get("tags") or []),
                "availability": str(stock.get("availability") or product.get("availability") or "IN_STOCK"),
                "availableQuantity": int(stock.get("availableQuantity") or product.get("availableQuantity") or 0),
                "priceInfo": {
                    "price": float(pricing.get("price") or product.get("price") or 0.0),
                    "currencyCode": str(pricing.get("currencyCode") or product.get("currencyCode") or "GBP"),
                },
                "images": list(product.get("images") or []),
            })
        return {"products": products}

    @app.post("/erp/admin/enrich-catalog")
    async def enrich_catalog(payload: dict[str, Any] | None = None, context=Depends(erp_context)) -> dict[str, Any]:
        require_scope(context, "erp.write")
        force = bool((payload or {}).get("force"))
        result = await _enrich_erp_catalog(force)
        return {"accepted": result.get("applied", False) or "reason" in result, **result}

    return app
