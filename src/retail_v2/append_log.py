from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from .blob_store import BlobStore
from .models import AppendRecord, TailMarker
from .paths import TenantPaths


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AppendWriter:
    def __init__(self, store: BlobStore, owner_id: str = "local-owner"):
        self.store = store
        self.owner_id = owner_id

    def append_one(self, paths: TenantPaths, stream: str, route, record_type: str, payload: dict) -> dict:
        segment_id = f"{stream}-{route.partition_id}-{uuid4().hex}"
        sequence = 1
        record_id = str(payload.get("eventId") or payload.get("id") or uuid4())
        record = AppendRecord(
            record_type=record_type,
            tenant_id=paths.tenant_id,
            stream=stream,
            partition_id=route.partition_id,
            partition_key=route.partition_key,
            sequence=sequence,
            record_id=record_id,
            record_time=utc_now(),
            payload=payload,
        )
        line_payload = json.dumps(record.to_json(segment_id), separators=(",", ":"))
        content_hash = "sha256:" + hashlib.sha256(line_payload.encode("utf-8")).hexdigest()
        tail = TailMarker(segment_id=segment_id, sequence=sequence, record_count=1, content_hash=content_hash, closed_time=utc_now())
        segment_path = paths.append_segment(stream, route.partition_id, segment_id)
        lease_path = paths.lease_blob(stream, route.partition_id)
        lease = self.store.acquire_lease(lease_path, self.owner_id)
        try:
            self.store.append_text(segment_path, line_payload + "\n")
            self.store.append_text(segment_path, json.dumps(tail.to_json(), separators=(",", ":")) + "\n")
        finally:
            self.store.release_lease(lease_path, lease)
        return {
            "accepted": True,
            "tenantId": paths.tenant_id,
            "stream": stream,
            "partitionId": route.partition_id,
            "partitionKey": route.partition_key,
            "segmentId": segment_id,
            "recordId": record_id,
            "tail": tail.to_json(),
        }
