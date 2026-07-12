"""Online two-tower recommendation ranker -- a real, continuously-retraining ML model.

This is the "how would we actually build the ML model" follow-through: a small two-tower
recommender (one embedding per visitor, one embedding + bias per product) trained with a single
SGD step per qualifying event, using a pairwise Bayesian Personalized Ranking (BPR) loss -- the
same family of technique production implicit-feedback recommenders use. Unlike a batch-trained
model, there is no offline training job and no model registry/hot-swap: every click/add-to-cart/
purchase event nudges the live in-memory embeddings immediately (record-by-record), so ranking
reflects the last few seconds of shopper behavior, not last night's batch.

Architecture:
  - Item tower: a d-dim embedding vector + scalar bias per product (per tenant, per objective).
  - User tower: a d-dim embedding vector per visitor.
  - score(visitor, product) = dot(user_embedding, item_embedding) + item_bias.
  - Training signal: a positive event (click for the CTR model, purchase for conversion/revenue)
    is paired against a handful of randomly sampled "negative" products, and one BPR-style SGD
    step pushes score(positive) above score(negative). This avoids needing an impression log
    (a natural "shown but ignored" negative) that this demo platform doesn't capture.
  - Cold start: a product/visitor with no trained embedding yet scores exactly 0.0, which the
    caller (see app.py _objective_score) treats identically to "no performance data yet" and
    falls back to the simpler heuristic ratio score until a tenant's model has processed enough
    events (see MIN_EVENTS_FOR_ML in app.py) to be trusted for that objective.

Three independent objective models per tenant (ctr / conversion / revenue) rather than one
shared multi-task model -- simpler to reason about, verify, and reset independently, and cheap
enough at demo scale (d=16 floats per product/visitor) that sharing isn't worth the complexity.
"""

from __future__ import annotations

import random
import time
from typing import Any

import numpy as np

DIM = 16
LEARNING_RATE = 0.08
REGULARIZATION = 0.002
NEGATIVES_PER_EVENT = 3


class OnlineTwoTowerRanker:
    """A single objective's two-tower model (e.g. just the CTR model, or just the revenue model)."""

    def __init__(self, dim: int = DIM, lr: float = LEARNING_RATE, reg: float = REGULARIZATION, seed: int = 13) -> None:
        self.dim = dim
        self.lr = lr
        self.reg = reg
        self._rng = random.Random(seed)
        self.item_emb: dict[str, np.ndarray] = {}
        self.item_bias: dict[str, float] = {}
        self.user_emb: dict[str, np.ndarray] = {}
        self.events_trained = 0
        self.pairs_trained = 0
        self.loss_ema: float | None = None
        self.last_trained_at: float | None = None

    def _init_vector(self) -> np.ndarray:
        return (np.array([self._rng.random() for _ in range(self.dim)]) - 0.5) * 0.1

    def _item(self, product_id: str) -> np.ndarray:
        vec = self.item_emb.get(product_id)
        if vec is None:
            vec = self._init_vector()
            self.item_emb[product_id] = vec
            self.item_bias[product_id] = 0.0
        return vec

    def _user(self, visitor_id: str) -> np.ndarray:
        vec = self.user_emb.get(visitor_id)
        if vec is None:
            vec = self._init_vector()
            self.user_emb[visitor_id] = vec
        return vec

    def score(self, visitor_id: str, product_id: str) -> float:
        # Deliberately 0.0 (not a lazily-initialized cold embedding's near-zero dot product) for
        # any product this model has never trained on -- callers rely on 0.0 meaning "no signal
        # yet, fall back to the heuristic score" rather than a noisy random-init guess.
        if product_id not in self.item_emb:
            return 0.0
        item = self.item_emb[product_id]
        bias = self.item_bias.get(product_id, 0.0)
        if not visitor_id or visitor_id not in self.user_emb:
            # No specific visitor context -- this is exactly the tenant-wide ranking-objective
            # case (an anonymous/aggregate query, not a per-visitor personalization lookup). The
            # item bias term is what BPR training pushes toward "this item generally outranks
            # others for this objective" independent of any single user's embedding, so it's the
            # right visitor-agnostic proxy for a global popularity/CTR/conversion/revenue score.
            return float(bias)
        return float(np.dot(self.user_emb[visitor_id], item) + bias)

    def _train_pair(self, visitor_id: str, positive_id: str, negative_id: str, weight: float) -> float:
        u = self._user(visitor_id)
        pos = self._item(positive_id)
        neg = self._item(negative_id)
        margin = float(np.dot(u, pos - neg) + (self.item_bias[positive_id] - self.item_bias[negative_id]))
        sigmoid = 1.0 / (1.0 + np.exp(-margin))
        gradient = weight * (1.0 - sigmoid)  # how hard to push "positive should outrank negative"
        self.user_emb[visitor_id] = u + self.lr * (gradient * (pos - neg) - self.reg * u)
        self.item_emb[positive_id] = pos + self.lr * (gradient * u - self.reg * pos)
        self.item_emb[negative_id] = neg + self.lr * (-gradient * u - self.reg * neg)
        self.item_bias[positive_id] = self.item_bias[positive_id] + self.lr * gradient * weight
        self.item_bias[negative_id] = self.item_bias[negative_id] - self.lr * gradient * weight
        self.pairs_trained += 1
        return float(-np.log(sigmoid + 1e-9))

    def train_event(self, visitor_id: str, positive_id: str, catalog_ids: list[str], weight: float = 1.0) -> None:
        """One record-by-record online training step, called synchronously as each qualifying
        event arrives -- no batching, no offline job. A handful of ~16-dim vector ops, so this
        costs well under a millisecond even inline on the request path."""
        if not visitor_id or not positive_id or len(catalog_ids) < 2:
            return
        pool = [pid for pid in catalog_ids if pid != positive_id]
        if not pool:
            return
        negatives = self._rng.sample(pool, min(NEGATIVES_PER_EVENT, len(pool)))
        losses = [self._train_pair(visitor_id, positive_id, negative_id, weight) for negative_id in negatives]
        mean_loss = sum(losses) / len(losses)
        self.loss_ema = mean_loss if self.loss_ema is None else (0.95 * self.loss_ema + 0.05 * mean_loss)
        self.events_trained += 1
        self.last_trained_at = time.time()

    def stats(self) -> dict[str, Any]:
        return {
            "eventsTrained": self.events_trained,
            "pairsTrained": self.pairs_trained,
            "itemsLearned": len(self.item_emb),
            "usersLearned": len(self.user_emb),
            "lossEma": round(self.loss_ema, 4) if self.loss_ema is not None else None,
            "lastTrainedAt": self.last_trained_at,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "dim": self.dim,
            "item_emb": {pid: vec.tolist() for pid, vec in self.item_emb.items()},
            "item_bias": dict(self.item_bias),
            "user_emb": {vid: vec.tolist() for vid, vec in self.user_emb.items()},
            "events_trained": self.events_trained,
            "pairs_trained": self.pairs_trained,
            "loss_ema": self.loss_ema,
        }

    def load_snapshot(self, data: dict[str, Any]) -> None:
        try:
            self.item_emb = {pid: np.array(vec, dtype=float) for pid, vec in (data.get("item_emb") or {}).items()}
            self.item_bias = {pid: float(bias) for pid, bias in (data.get("item_bias") or {}).items()}
            self.user_emb = {vid: np.array(vec, dtype=float) for vid, vec in (data.get("user_emb") or {}).items()}
            self.events_trained = int(data.get("events_trained") or 0)
            self.pairs_trained = int(data.get("pairs_trained") or 0)
            self.loss_ema = data.get("loss_ema")
        except Exception:
            pass


class MLRankerRegistry:
    """Per-tenant, per-objective collection of OnlineTwoTowerRanker models -- the plug-in point
    for WaveSearch: one registry instance, wired into the event-tracking and ranking-objective
    code paths, is the entire integration surface."""

    OBJECTIVES = ("ctr", "conversion", "revenue")

    def __init__(self) -> None:
        self._by_tenant: dict[str, dict[str, OnlineTwoTowerRanker]] = {}

    def ranker(self, tenant_id: str, objective: str) -> OnlineTwoTowerRanker:
        tenant_models = self._by_tenant.setdefault(tenant_id, {})
        model = tenant_models.get(objective)
        if model is None:
            model = OnlineTwoTowerRanker()
            tenant_models[objective] = model
        return model

    def train_event(
        self,
        tenant_id: str,
        event_type: str,
        visitor_id: str,
        product_id: str,
        revenue: float,
        catalog_ids: list[str],
    ) -> None:
        # Event -> which objective model(s) get a training step, and how strongly:
        #   click        -> CTR model (this IS the positive-click signal it optimizes for)
        #   add_to_cart  -> conversion model, moderate weight (real intent, not yet a completed sale)
        #   purchase     -> conversion model (full weight) + revenue model (weighted by log(1+value))
        # "view" alone is intentionally NOT used as a training positive here -- it's too weak/noisy
        # for a pairwise ranking loss without a matching impression log to draw confident negatives
        # from (a view says "seen", not "preferred over the alternatives").
        if event_type == "click":
            self.ranker(tenant_id, "ctr").train_event(visitor_id, product_id, catalog_ids, weight=1.0)
        elif event_type == "add_to_cart":
            self.ranker(tenant_id, "conversion").train_event(visitor_id, product_id, catalog_ids, weight=0.5)
        elif event_type == "purchase":
            self.ranker(tenant_id, "conversion").train_event(visitor_id, product_id, catalog_ids, weight=1.0)
            revenue_weight = float(np.log1p(max(0.0, revenue))) or 1.0
            self.ranker(tenant_id, "revenue").train_event(visitor_id, product_id, catalog_ids, weight=revenue_weight)

    def stats(self, tenant_id: str) -> dict[str, dict[str, Any]]:
        tenant_models = self._by_tenant.get(tenant_id, {})
        return {
            objective: (tenant_models[objective].stats() if objective in tenant_models else OnlineTwoTowerRanker().stats())
            for objective in self.OBJECTIVES
        }

    def score(self, tenant_id: str, objective: str, visitor_id: str, product_id: str) -> float:
        model = self._by_tenant.get(tenant_id, {}).get(objective)
        return model.score(visitor_id, product_id) if model else 0.0

    def is_ready(self, tenant_id: str, objective: str, min_events: int) -> bool:
        model = self._by_tenant.get(tenant_id, {}).get(objective)
        return bool(model and model.events_trained >= min_events)

    def snapshot(self) -> dict[str, Any]:
        return {
            tenant_id: {objective: model.snapshot() for objective, model in models.items()}
            for tenant_id, models in self._by_tenant.items()
        }

    def load_snapshot(self, data: dict[str, Any]) -> None:
        for tenant_id, models in (data or {}).items():
            if not isinstance(models, dict):
                continue
            for objective, snap in models.items():
                if objective not in self.OBJECTIVES or not isinstance(snap, dict):
                    continue
                self.ranker(tenant_id, objective).load_snapshot(snap)

    def reset(self, tenant_id: str, objective: str | None = None) -> None:
        tenant_models = self._by_tenant.setdefault(tenant_id, {})
        for obj in ([objective] if objective else list(self.OBJECTIVES)):
            tenant_models[obj] = OnlineTwoTowerRanker()
