from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredBlob:
    key: str
    sha256: str
    size_bytes: int


class LocalBlobStore:
    """只接受服务端生成的不透明 key，并以同目录临时文件 + 原子替换发布内容。"""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("storage_key_outside_root")
        return candidate

    def write_bytes(self, category: str, suffix: str, content: bytes) -> StoredBlob:
        staged = self.stage_bytes(suffix, content)
        return self.publish(staged, category)

    def stage_bytes(self, suffix: str, content: bytes) -> StoredBlob:
        """先写入不可见 staging key；业务 CAS 通过后再发布到正式分类。"""

        digest = hashlib.sha256(content).hexdigest()
        key = f"staging/{uuid4().hex}{suffix}"
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        with temporary.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        return StoredBlob(key=key, sha256=digest, size_bytes=len(content))

    def publish(self, staged: StoredBlob, category: str) -> StoredBlob:
        if not staged.key.startswith("staging/"):
            raise ValueError("blob_not_staged")
        source = self.path_for(staged.key)
        key = f"{category}/{uuid4().hex}{source.suffix}"
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        return StoredBlob(key=key, sha256=staged.sha256, size_bytes=staged.size_bytes)

    def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    def read_bytes(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def path_for(self, key: str) -> Path:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path

    def is_writable(self) -> bool:
        probe = self.root / f".probe-{uuid4().hex}"
        try:
            probe.write_bytes(b"ok")
            return True
        finally:
            probe.unlink(missing_ok=True)
