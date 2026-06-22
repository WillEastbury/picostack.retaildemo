from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class BlobStore(Protocol):
    def read_text(self, path: str) -> str: ...
    def write_text(self, path: str, value: str) -> None: ...
    def append_text(self, path: str, value: str) -> None: ...
    def exists(self, path: str) -> bool: ...
    def list(self, prefix: str) -> list[str]: ...
    def acquire_lease(self, path: str, owner: str) -> str: ...
    def release_lease(self, path: str, lease_id: str) -> None: ...


class LocalBlobStore:
    """Development/test adapter that mimics blob paths on the filesystem.

    Production code should use an Azure Blob adapter behind the same protocol.
    This adapter is intentionally useful for fast dev only.
    """

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, path: str) -> Path:
        clean = path.strip("/").replace("..", "_")
        return self.root / clean

    def read_text(self, path: str) -> str:
        return self._path(path).read_text(encoding="utf-8")

    def write_text(self, path: str, value: str) -> None:
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")

    def append_text(self, path: str, value: str) -> None:
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="") as handle:
            handle.write(value)

    def exists(self, path: str) -> bool:
        return self._path(path).exists()

    def list(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        if base.is_file():
            return [prefix.strip("/")]
        results: list[str] = []
        for item in base.rglob("*"):
            if item.is_file():
                results.append(item.relative_to(self.root).as_posix())
        return sorted(results)

    def acquire_lease(self, path: str, owner: str) -> str:
        lease_path = self._path(path + ".lease")
        lease_path.parent.mkdir(parents=True, exist_ok=True)
        if lease_path.exists():
            current = json.loads(lease_path.read_text(encoding="utf-8"))
            if current.get("owner") != owner:
                raise RuntimeError(f"lease already held by {current.get('owner')}")
        lease_id = f"{owner}:{path}"
        lease_path.write_text(json.dumps({"owner": owner, "leaseId": lease_id}), encoding="utf-8")
        return lease_id

    def release_lease(self, path: str, lease_id: str) -> None:
        lease_path = self._path(path + ".lease")
        if not lease_path.exists():
            return
        current = json.loads(lease_path.read_text(encoding="utf-8"))
        if current.get("leaseId") == lease_id:
            lease_path.unlink()
