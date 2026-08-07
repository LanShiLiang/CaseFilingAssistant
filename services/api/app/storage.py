from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
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

    def stage_stream(self, suffix: str, stream: BinaryIO, max_bytes: int) -> StoredBlob:
        """有界流式写入上传件；超限时不保留 staging 文件。"""

        key = f"staging/{uuid4().hex}{suffix}"
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        digest = hashlib.sha256()
        size = 0
        try:
            with temporary.open("wb") as output:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("file_too_large")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if size == 0:
                raise ValueError("empty_file")
            os.replace(temporary, target)
            return StoredBlob(key=key, sha256=digest.hexdigest(), size_bytes=size)
        except Exception:
            temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise

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

    def read_prefix(self, key: str, size: int = 16) -> bytes:
        with self._resolve(key).open("rb") as stream:
            return stream.read(size)

    def verify(self, key: str, expected_sha256: str, expected_size: int) -> bool:
        path = self.path_for(key)
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        return size == expected_size and digest.hexdigest() == expected_sha256

    def iter_keys(self, category: str) -> list[str]:
        root = self._resolve(category)
        if not root.exists():
            return []
        return [
            path.relative_to(self.root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        ]

    def delete_unreferenced(
        self, category: str, referenced: set[str], grace_seconds: int
    ) -> list[str]:
        deleted: list[str] = []
        cutoff = time.time() - grace_seconds
        for key in self.iter_keys(category):
            path = self._resolve(key)
            if key not in referenced and path.stat().st_mtime <= cutoff:
                path.unlink(missing_ok=True)
                deleted.append(key)
        return deleted

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
