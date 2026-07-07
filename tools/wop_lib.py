#!/usr/bin/env python3
"""Shared helpers for WitnessOps operator tools."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any

UNSIGNED_PLACEHOLDER: dict[str, str] = {
    "algorithm": "unsigned",
    "note": "excluded_from_signing_payload_v1",
}

DEFAULT_PRIVATE_KEY = Path("/home/ops/witnessops-node/identity/private/node_ed25519.pem")
DEFAULT_PUBLIC_KEY = Path("/home/ops/witnessops-node/identity/public/node_ed25519.pub.pem")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hashref_bytes(data: bytes) -> str:
    return "sha256:" + sha256_hex(data)


def signing_payload(receipt_obj: dict[str, Any]) -> dict[str, Any]:
    payload = dict(receipt_obj)
    payload["signature"] = dict(UNSIGNED_PLACEHOLDER)
    return payload


def signing_payload_bytes(receipt_obj: dict[str, Any]) -> bytes:
    return canonical_bytes(signing_payload(receipt_obj))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _decode_openssh_private_blob(blob: bytes) -> bytes:
    if not blob.startswith(b"openssh-key-v1\x00"):
        raise ValueError("not_openssh_private_key_v1")
    offset = len(b"openssh-key-v1\x00")

    def read_string(data: bytes, pos: int) -> tuple[str, int]:
        length = int.from_bytes(data[pos : pos + 4], "big")
        pos += 4
        return data[pos : pos + length].decode("ascii"), pos + length

    cipher, offset = read_string(blob, offset)
    kdf, offset = read_string(blob, offset)
    _kdfoptions, offset = read_string(blob, offset)
    if cipher != "none" or kdf != "none":
        raise ValueError("encrypted_openssh_key_not_supported")
    num_keys = int.from_bytes(blob[offset : offset + 4], "big")
    offset += 4
    if num_keys != 1:
        raise ValueError("unsupported_openssh_key_count")

    pub_len = int.from_bytes(blob[offset : offset + 4], "big")
    offset += 4 + pub_len
    priv_len = int.from_bytes(blob[offset : offset + 4], "big")
    offset += 4
    private_section = blob[offset : offset + priv_len]

    check1 = int.from_bytes(private_section[0:4], "big")
    check2 = int.from_bytes(private_section[4:8], "big")
    if check1 != check2:
        raise ValueError("openssh_private_section_check_mismatch")

    key_type_len = int.from_bytes(private_section[8:12], "big")
    key_type = private_section[12 : 12 + key_type_len].decode("ascii")
    if key_type != "ssh-ed25519":
        raise ValueError(f"unsupported_key_type:{key_type}")

    pos = 12 + key_type_len
    pub_field_len = int.from_bytes(private_section[pos : pos + 4], "big")
    pos += 4 + pub_field_len
    priv_field_len = int.from_bytes(private_section[pos : pos + 4], "big")
    pos += 4
    seed = private_section[pos : pos + 32]
    if len(seed) != 32:
        raise ValueError("invalid_ed25519_seed_length")
    return seed


def load_ed25519_private_key(path: Path):
    from nacl.signing import SigningKey

    text = _read_text(path)
    if "BEGIN OPENSSH PRIVATE KEY" in text:
        body = "".join(line.strip() for line in text.splitlines() if line and not line.startswith("-----"))
        blob = base64.b64decode(body)
        seed = _decode_openssh_private_blob(blob)
        return SigningKey(seed)

    if "BEGIN PRIVATE KEY" in text:
        der = base64.b64decode("".join(line.strip() for line in text.splitlines() if line and not line.startswith("-----")))
        # PKCS#8 Ed25519 private key: last 32 bytes are seed in common Debian openssl output.
        if len(der) < 32:
            raise ValueError("invalid_pkcs8_private_key")
        return SigningKey(der[-32:])

    raise ValueError("unsupported_private_key_format")


def _openssh_public_body(text: str) -> bytes:
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("ssh-ed25519 "):
            parts = line.split()
            if len(parts) < 2:
                raise ValueError("invalid_openssh_public_key")
            return base64.b64decode(parts[1])
        if "BEGIN PUBLIC KEY" in text:
            body = "".join(ln.strip() for ln in text.splitlines() if ln and not ln.startswith("-----"))
            der = base64.b64decode(body)
            # SubjectPublicKeyInfo for Ed25519 ends with 32-byte pubkey.
            return der[-32:]
    raise ValueError("unsupported_public_key_format")


def load_ed25519_public_key(path: Path):
    from nacl.signing import VerifyKey

    text = _read_text(path)
    key_bytes = _openssh_public_body(text)
    if len(key_bytes) == 32:
        return VerifyKey(key_bytes)
    if b"ssh-ed25519" in key_bytes:
        return VerifyKey(key_bytes[-32:])
    raise ValueError("invalid_ed25519_public_key")


def fingerprint_public_key(path: Path) -> str:
    key = load_ed25519_public_key(path)
    digest = hashlib.sha256(bytes(key)).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")