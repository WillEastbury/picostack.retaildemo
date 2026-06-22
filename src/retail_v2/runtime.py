from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .models import ProductRecord


TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(value: str) -> list[str]:
    return TOKEN_RE.findall(value.lower())


@dataclass(frozen=True)
class CatalogRuntime:
    products_by_id: dict[str, ProductRecord]
    variants_by_primary_id: dict[str, tuple[str, ...]]
    postings: dict[str, tuple[str, ...]]
    doc_lengths: dict[str, int]
    term_frequency: dict[str, Counter[str]]
    version: str = "runtime-v1"

    def product(self, product_id: str) -> ProductRecord | None:
        return self.products_by_id.get(product_id)


@dataclass
class LiveOverlay:
    inventory: dict[str, dict] = field(default_factory=dict)
    events_seen: int = 0


class RuntimeBuilder:
    def build(self, catalog: dict) -> CatalogRuntime:
        products: dict[str, ProductRecord] = {}
        variants: dict[str, list[str]] = defaultdict(list)
        for raw in catalog.get("products", []):
            self._add_product(raw, products, variants)
            for variant in raw.get("variants", []) or []:
                self._add_product(variant, products, variants)

        term_docs: dict[str, set[str]] = defaultdict(set)
        term_frequency: dict[str, Counter[str]] = {}
        doc_lengths: dict[str, int] = {}
        for product_id, product in products.items():
            text = " ".join(
                [
                    product.title,
                    product.description,
                    " ".join(product.categories),
                    " ".join(product.brands),
                    " ".join(product.tags),
                ]
            )
            counts = Counter(tokenize(text))
            term_frequency[product_id] = counts
            doc_lengths[product_id] = sum(counts.values()) or 1
            for term in counts:
                term_docs[term].add(product_id)
        postings = {term: tuple(sorted(ids)) for term, ids in term_docs.items()}
        return CatalogRuntime(
            products_by_id=products,
            variants_by_primary_id={k: tuple(v) for k, v in variants.items()},
            postings=postings,
            doc_lengths=doc_lengths,
            term_frequency=term_frequency,
        )

    def _add_product(self, raw: dict, products: dict[str, ProductRecord], variants: dict[str, list[str]]) -> None:
        product = ProductRecord.from_json(raw)
        products[product.id] = product
        if product.type == "VARIANT" and product.primary_product_id:
            variants[product.primary_product_id].append(product.id)


class SearchEngine:
    def search(self, runtime: CatalogRuntime, query: str, limit: int = 10) -> dict:
        terms = tokenize(query)
        if not terms:
            return {"query": query, "totalSize": 0, "results": []}
        candidates: set[str] = set()
        for term in terms:
            candidates.update(runtime.postings.get(term, ()))
        scores = []
        total_docs = max(1, len(runtime.products_by_id))
        avg_len = sum(runtime.doc_lengths.values()) / total_docs if total_docs else 1
        for product_id in candidates:
            score = 0.0
            freqs = runtime.term_frequency[product_id]
            doc_len = runtime.doc_lengths[product_id]
            for term in terms:
                tf = freqs.get(term, 0)
                if not tf:
                    continue
                df = len(runtime.postings.get(term, ())) or 1
                idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
                score += idf * ((tf * 2.2) / (tf + 1.2 * (1 - 0.75 + 0.75 * doc_len / avg_len)))
            scores.append((score, product_id))
        scores.sort(reverse=True)
        results = []
        for score, product_id in scores[:limit]:
            product = runtime.products_by_id[product_id]
            results.append({"id": product.id, "title": product.title, "score": round(score, 4), "product": product.raw})
        return {"query": query, "totalSize": len(scores), "results": results}

    def recommend(self, runtime: CatalogRuntime, product_id: str | None = None, limit: int = 10) -> dict:
        product = runtime.products_by_id.get(product_id or "") if product_id else None
        if product:
            seed_terms = set(product.categories + product.brands + product.tags)
            scored = []
            for other in runtime.products_by_id.values():
                if other.id == product.id:
                    continue
                overlap = len(seed_terms.intersection(other.categories + other.brands + other.tags))
                if overlap:
                    scored.append((overlap, other.id))
            scored.sort(reverse=True)
            ids = [pid for _, pid in scored[:limit]]
        else:
            ids = list(runtime.products_by_id)[:limit]
        return {"productId": product_id, "results": [{"id": pid, "title": runtime.products_by_id[pid].title} for pid in ids]}


def load_catalog_file(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
