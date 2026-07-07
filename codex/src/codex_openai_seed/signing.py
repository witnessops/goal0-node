from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def _repo_root() -> Path:
    root = os.environ.get("WOPS_ROOT")
    if root:
        return Path(root)
    return Path(__file__).resolve().parents[3]


WOPS_TOOLS = _repo_root() / "tools"
if str(WOPS_TOOLS) not in sys.path:
    sys.path.insert(0, str(WOPS_TOOLS))


def _is_openssh_private_key(path: Path) -> bool:
    try:
        return "BEGIN OPENSSH PRIVATE KEY" in path.read_text(encoding="utf-8")
    except OSError:
        return False


def generate_keypair(private_key_path: str | Path, public_key_path: str | Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path = Path(private_key_path)
    public_path = Path(public_key_path)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    private_path.chmod(0o600)


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    key_path = Path(path)
    if _is_openssh_private_key(key_path):
        raise TypeError("OpenSSH private keys must be loaded via load_signing_key()")
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Expected Ed25519 private key")
    return key


def load_signing_key(path: str | Path) -> Any:
    key_path = Path(path)
    if _is_openssh_private_key(key_path):
        from wop_lib import load_ed25519_private_key

        return load_ed25519_private_key(key_path)
    return load_private_key(key_path)


def load_public_key(path: str | Path) -> Ed25519PublicKey | Any:
    key_path = Path(path)
    text = key_path.read_text(encoding="utf-8")
    if "BEGIN OPENSSH" in text or text.strip().startswith("ssh-ed25519 "):
        from wop_lib import load_ed25519_public_key

        return load_ed25519_public_key(key_path)
    key = serialization.load_pem_public_key(key_path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("Expected Ed25519 public key")
    return key


def public_pem(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def public_key_pem_for_private(private_key_path: str | Path) -> str:
    private_path = Path(private_key_path)
    if _is_openssh_private_key(private_path):
        public_path = private_path.parent.parent / "public" / "node_ed25519.pub.pem"
        if public_path.exists():
            return public_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Companion public key not found for {private_path}")
    return public_pem(load_private_key(private_path))


def sign(private_key: Any, data: bytes) -> str:
    if isinstance(private_key, Ed25519PrivateKey):
        return base64.b64encode(private_key.sign(data)).decode("ascii")
    signed = private_key.sign(data)
    signature_bytes = signed.signature if hasattr(signed, "signature") else signed
    return base64.b64encode(signature_bytes).decode("ascii")


def verify(public_key: Any, signature_b64: str, data: bytes) -> bool:
    try:
        if isinstance(public_key, Ed25519PublicKey):
            public_key.verify(base64.b64decode(signature_b64), data)
            return True
        public_key.verify(data, base64.b64decode(signature_b64))
        return True
    except (InvalidSignature, Exception):
        return False