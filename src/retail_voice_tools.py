from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "find_items",
        "description": "Search the shop catalog for matching products.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The product search query."},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "check_stock",
        "description": "Check stock for a known product id or product search phrase.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "query": {"type": "string"},
            },
        },
    },
    {
        "type": "function",
        "name": "order_items",
        "description": "Create a demo order for a product. This is a demo order and no payment is taken.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "query": {"type": "string"},
                "quantity": {"type": "integer"},
                "customer_name": {"type": "string"},
            },
        },
    },
    {
        "type": "function",
        "name": "check_shipping_status",
        "description": "Check the shipping status of a demo order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
            },
            "required": ["order_id"],
        },
    },
]


@dataclass
class RetailVoiceToolContext:
    bridge: Any
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _first_product(self, product_id: str | None, query: str | None) -> dict[str, Any] | None:
        if product_id:
            product = self.bridge.product(product_id)
            if "error" not in product:
                return product
        if query:
            result = self.bridge.search(query)
            hits = result.get("results") or []
            if hits:
                return hits[0].get("product") or hits[0]
        return None

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "find_items":
            query = str(arguments.get("query") or "")
            return self.bridge.search(query)

        if name == "check_stock":
            product = self._first_product(arguments.get("product_id"), arguments.get("query"))
            if not product:
                return {"found": False, "message": "No matching demo product was found."}
            return {
                "found": True,
                "product": product,
                "in_stock": int(product.get("inventory") or 0) > 0,
                "inventory": int(product.get("inventory") or 0),
            }

        if name == "order_items":
            product = self._first_product(arguments.get("product_id"), arguments.get("query"))
            if not product:
                return {"ordered": False, "message": "No matching demo product was found."}
            quantity = max(1, int(arguments.get("quantity") or 1))
            order_id = "voice-ord-" + uuid.uuid4().hex[:8]
            subtotal = round(float(product.get("price") or 0.0) * quantity, 2)
            order = {
                "id": order_id,
                "status": "CONFIRMED",
                "shippingStatus": "Processing",
                "customerName": str(arguments.get("customer_name") or "Voice shopper"),
                "items": [{"product": product, "quantity": quantity, "lineTotal": subtotal}],
                "summary": {"subtotal": subtotal, "total": subtotal},
            }
            self.orders[order_id] = order
            return {"ordered": True, "order": order}

        if name == "check_shipping_status":
            order_id = str(arguments.get("order_id") or "")
            order = self.orders.get(order_id)
            if not order:
                return {
                    "found": False,
                    "message": "I could not find that demo order. Try the order number shown after checkout.",
                }
            return {"found": True, "order": order, "shippingStatus": order["shippingStatus"]}

        return {"error": f"Unknown retail voice tool: {name}"}
