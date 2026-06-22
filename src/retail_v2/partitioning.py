from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import PartitionRoute, TenantContext


def stable_hash(value: str) -> int:
    return int.from_bytes(hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest(), "big")


@dataclass(frozen=True)
class PartitionMap:
    tenant_id: str
    version: str = "partition-map-v1"
    partitions: int = 64
    owners: tuple[str, ...] = ("local-owner",)

    def partition_id(self, key: str) -> str:
        slot = stable_hash(f"{self.tenant_id}:{key}") % self.partitions
        return f"p{slot:04d}"

    def owner_for_partition(self, partition_id: str) -> str:
        slot = int(partition_id[1:])
        return self.owners[slot % len(self.owners)]

    def route(self, key: str) -> PartitionRoute:
        pid = self.partition_id(key)
        return PartitionRoute(
            tenant_id=self.tenant_id,
            partition_key=key,
            partition_id=pid,
            owner=self.owner_for_partition(pid),
            map_version=self.version,
        )


class PartitionRouter:
    def __init__(self, owners: tuple[str, ...] = ("local-owner",), partitions: int = 64):
        self.owners = owners
        self.partitions = partitions

    def map_for(self, context: TenantContext) -> PartitionMap:
        return PartitionMap(tenant_id=context.tenant_id, partitions=self.partitions, owners=self.owners)

    def resolve(self, context: TenantContext, key: str) -> PartitionRoute:
        return self.map_for(context).route(key)
