from __future__ import annotations

import tempfile
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retail_v2.app import create_app
from retail_v2.blob_store import LocalBlobStore
from retail_v2.services import RetailV2Service


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        service = RetailV2Service(LocalBlobStore(Path(tmp)), ROOT / "V2" / "sample-catalog.json")
        client = TestClient(create_app(service))
        token = client.post("/v2/auth/token", json={"tenant": "tenant-a", "subject": "tester", "scopes": ["admin", "search.query", "events.write", "inventory.write"]}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        status = client.get("/v2/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["productCount"] >= 2

        products = client.get("/v2/catalog/products", headers=headers)
        assert products.status_code == 200
        assert products.json()["products"]

        search = client.post("/v2/search", json={"query": "waterproof jacket"}, headers=headers)
        assert search.status_code == 200
        assert search.json()["results"]

        recs = client.post("/v2/recommend", json={"productId": "SKU-001"}, headers=headers)
        assert recs.status_code == 200
        assert "results" in recs.json()

        event = client.post(
            "/v2/userEvents:write",
            json={"eventId": "evt-smoke", "eventType": "click", "visitorId": "visitor-smoke", "productIds": ["SKU-001"], "eventTime": "2026-06-22T12:00:00Z"},
            headers=headers,
        )
        assert event.status_code == 200
        event_body = event.json()
        assert event_body["accepted"] is True
        assert event_body["partitionId"].startswith("p")

        inventory = client.post(
            "/v2/inventory:set",
            json={"productId": "SKU-001-M-ROSE", "availableQuantity": 12, "availability": "IN_STOCK"},
            headers=headers,
        )
        assert inventory.status_code == 200
        assert inventory.json()["accepted"] is True

        rule = client.post("/v2/rules", json={"id": "pin-smoke", "actions": {"pin": [{"productId": "SKU-001", "position": 1}]}}, headers=headers)
        assert rule.status_code == 200

        final_status = client.get("/v2/status", headers=headers).json()
        assert final_status["eventOverlayCount"] == 1
        assert final_status["inventoryOverlayCount"] == 1

    print("retail v2 smoke ok")


if __name__ == "__main__":
    main()
