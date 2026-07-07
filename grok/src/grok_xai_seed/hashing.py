from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def hashref_json(value: Any) -> str:
    return f"sha256:{sha256_json(value)}"


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def hashref_file(path: str | Path) -> str:
    return f"sha256:{sha256_file(path)}"


def hashref_bytes(data: bytes) -> str:
    return f"sha256:{sha256_bytes(data)}"