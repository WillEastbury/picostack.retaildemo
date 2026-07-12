from __future__ import annotations

import json
import os

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobLeaseClient, BlobServiceClient


class AzureBlobStore:
    """Real Azure Blob Storage adapter implementing the same BlobStore protocol as
    LocalBlobStore (read_text/write_text/append_text/exists/list/acquire_lease/release_lease).

    This is the production-shaped persistence layer for catalog/vector/enrichment caches and
    admin state (rules/redirects/promotions): unlike LocalBlobStore (filesystem-backed, wiped on
    every pod recreation) or a k8s emptyDir volume (survives container restarts within a pod but
    not a full rollout), a real blob container survives every redeploy, rollout restart, and pod
    reschedule, since it lives outside the cluster entirely.
    """

    def __init__(self, account_name: str, account_key: str, container_name: str):
        account_url = f"https://{account_name}.blob.core.windows.net"
        self._service = BlobServiceClient(account_url=account_url, credential=account_key)
        self._container_name = container_name
        try:
            self._service.create_container(container_name)
        except ResourceExistsError:
            pass

    def _blob(self, path: str):
        clean = path.strip("/")
        return self._service.get_blob_client(container=self._container_name, blob=clean)

    def read_text(self, path: str) -> str:
        try:
            return self._blob(path).download_blob(encoding="utf-8").readall()
        except ResourceNotFoundError as exc:
            raise FileNotFoundError(path) from exc

    def write_text(self, path: str, value: str) -> None:
        self._blob(path).upload_blob(value, overwrite=True, encoding="utf-8")

    def append_text(self, path: str, value: str) -> None:
        blob = self._blob(path)
        try:
            existing = blob.download_blob(encoding="utf-8").readall()
        except ResourceNotFoundError:
            existing = ""
        blob.upload_blob(existing + value, overwrite=True, encoding="utf-8")

    def exists(self, path: str) -> bool:
        return self._blob(path).exists()

    def list(self, prefix: str) -> list[str]:
        clean = prefix.strip("/")
        container = self._service.get_container_client(self._container_name)
        return sorted(b.name for b in container.list_blobs(name_starts_with=clean))

    def acquire_lease(self, path: str, owner: str) -> str:
        blob = self._blob(path)
        if not blob.exists():
            blob.upload_blob(json.dumps({"owner": owner}), overwrite=False, encoding="utf-8")
        lease = BlobLeaseClient(blob)
        lease.acquire(lease_duration=60)
        return lease.id

    def release_lease(self, path: str, lease_id: str) -> None:
        blob = self._blob(path)
        lease = BlobLeaseClient(blob, lease_id=lease_id)
        try:
            lease.release()
        except ResourceNotFoundError:
            pass


def azure_blob_store_from_env() -> "AzureBlobStore | None":
    """Builds an AzureBlobStore from RETAIL_V2_BLOB_ACCOUNT_NAME/ACCOUNT_KEY/CONTAINER env vars,
    or returns None if not configured (callers should fall back to LocalBlobStore for local dev)."""
    account_name = str(os.environ.get("RETAIL_V2_BLOB_ACCOUNT_NAME") or "").strip()
    account_key = str(os.environ.get("RETAIL_V2_BLOB_ACCOUNT_KEY") or "").strip()
    container_name = str(os.environ.get("RETAIL_V2_BLOB_CONTAINER") or "wavesearch-catalog-cache").strip()
    if not account_name or not account_key:
        return None
    return AzureBlobStore(account_name, account_key, container_name)
