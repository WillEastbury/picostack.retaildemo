from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    branch_id: str = "default_branch"
    scopes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PartitionRoute:
    tenant_id: str
    partition_key: str
    partition_id: str
    owner: str
    map_version: str


@dataclass(frozen=True)
class ProductRecord:
    id: str
    title: str
    type: str = "PRIMARY"
    primary_product_id: str | None = None
    description: str = ""
    categories: tuple[str, ...] = ()
    brands: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    availability: str = "IN_STOCK"
    available_quantity: int = 0
    price: float | None = None
    raw: JsonDict = field(default_factory=dict)

    @classmethod
    def from_json(cls, product: JsonDict) -> "ProductRecord":
        price_info = product.get("priceInfo") if isinstance(product.get("priceInfo"), dict) else {}
        return cls(
            id=str(product["id"]),
            title=str(product.get("title") or product["id"]),
            type=str(product.get("type") or "PRIMARY"),
            primary_product_id=product.get("primaryProductId"),
            description=str(product.get("description") or ""),
            categories=tuple(str(x) for x in product.get("categories", []) if x),
            brands=tuple(str(x) for x in product.get("brands", []) if x),
            tags=tuple(str(x) for x in product.get("tags", []) if x),
            availability=str(product.get("availability") or "IN_STOCK"),
            available_quantity=int(product.get("availableQuantity") or 0),
            price=float(price_info["price"]) if price_info.get("price") is not None else None,
            raw=product,
        )


@dataclass(frozen=True)
class AppendRecord:
    record_type: str
    tenant_id: str
    stream: str
    partition_id: str
    partition_key: str
    sequence: int
    record_id: str
    record_time: str
    payload: JsonDict

    def to_json(self, segment_id: str) -> JsonDict:
        return {
            "recordType": self.record_type,
            "tenantId": self.tenant_id,
            "stream": self.stream,
            "partitionId": self.partition_id,
            "partitionKey": self.partition_key,
            "segmentId": segment_id,
            "sequence": self.sequence,
            "recordId": self.record_id,
            "recordTime": self.record_time,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class TailMarker:
    segment_id: str
    sequence: int
    record_count: int
    content_hash: str
    closed_time: str

    def to_json(self) -> JsonDict:
        return {
            "recordType": "tail",
            "segmentId": self.segment_id,
            "sequence": self.sequence,
            "recordCount": self.record_count,
            "contentHash": self.content_hash,
            "closedTime": self.closed_time,
        }
