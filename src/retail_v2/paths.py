from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantPaths:
    tenant_id: str
    branch_id: str = "default_branch"

    @property
    def root(self) -> str:
        return f"tenants/{self.tenant_id}"

    def manifest(self) -> str:
        return f"{self.root}/manifests/current.json"

    def partition_map(self) -> str:
        return f"{self.root}/branches/{self.branch_id}/partition-map/current.json"

    def product_blob(self, product_id: str) -> str:
        return f"{self.root}/branches/{self.branch_id}/products/{product_id}.json"

    def feature_blob(self, feature_name: str, partition_id: str) -> str:
        return f"{self.root}/branches/{self.branch_id}/features/{feature_name}/{partition_id}.json"

    def append_segment(self, stream: str, partition_id: str, segment_id: str) -> str:
        return f"{self.root}/branches/{self.branch_id}/append/{stream}/{partition_id}/{segment_id}.jsonl"

    def lease_blob(self, stream: str, partition_id: str) -> str:
        return f"{self.root}/branches/{self.branch_id}/leases/{stream}/{partition_id}.lease"
