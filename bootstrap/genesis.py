#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "witnessops.ducky_genesis"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hashref_bytes(data: bytes) -> str:
    return "sha256:" + sha256_bytes(data)


def hashref_string(value: str) -> str:
    return hashref_bytes(value.encode("utf-8"))


def hashref_file(path: Path) -> str:
    return "sha256:" + sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_run(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=5, check=False)
        out = (result.stdout or "").strip()
        return out or None
    except Exception:
        return None


def hardware_hashes() -> dict[str, Any]:
    system = platform.system().lower()
    values: dict[str, str] = {}

    if system == "darwin":
        raw = safe_run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
        if raw:
            for line in raw.splitlines():
                if "IOPlatformSerialNumber" in line:
                    parts = line.split('"')
                    if len(parts) >= 4:
                        values["apple_platform_serial_hash"] = hashref_string(parts[3])
                if "IOPlatformUUID" in line:
                    parts = line.split('"')
                    if len(parts) >= 4:
                        values["apple_platform_uuid_hash"] = hashref_string(parts[3])
    elif system == "linux":
        paths = {
            "dmi_product_uuid_hash": Path("/sys/class/dmi/id/product_uuid"),
            "dmi_product_serial_hash": Path("/sys/class/dmi/id/product_serial"),
            "dmi_board_serial_hash": Path("/sys/class/dmi/id/board_serial"),
        }
        for name, p in paths.items():
            try:
                raw = p.read_text(encoding="utf-8", errors="ignore").strip()
                if raw:
                    values[name] = hashref_string(raw)
            except Exception:
                pass
    elif system == "windows":
        # Prefer PowerShell-native script on Windows. This is a best-effort fallback.
        uuid = safe_run(["wmic", "csproduct", "get", "uuid"])
        if uuid:
            lines = [x.strip() for x in uuid.splitlines() if x.strip() and "uuid" not in x.lower()]
            if lines:
                values["windows_csproduct_uuid_hash"] = hashref_string(lines[0])
        serial = safe_run(["wmic", "bios", "get", "serialnumber"])
        if serial:
            lines = [x.strip() for x in serial.splitlines() if x.strip() and "serial" not in x.lower()]
            if lines:
                values["windows_bios_serial_hash"] = hashref_string(lines[0])

    return {
        "schema": f"{SCHEMA}.hardware_hashes.v1",
        "note": "Raw hardware identifiers are not stored. Only SHA-256 hash references are stored.",
        "values": values,
    }


def file_hashes(root: Path, rel: str) -> list[dict[str, Any]]:
    base = root / rel
    items: list[dict[str, Any]] = []
    if not base.exists():
        return items
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.name != ".gitkeep":
            items.append({
                "relative_path": str(p.relative_to(root)),
                "bytes": p.stat().st_size,
                "sha256": hashref_file(p),
            })
    return items


def require_consent() -> None:
    if os.environ.get("WOPGENESIS_CONSENT") == "GENESIS":
        return
    print("\nWitnessOps Genesis bootstrap")
    print("This will create local hash-only evidence and a genesis receipt on this USB volume.")
    print("It will not collect credentials, create persistence, or use the network.")
    print("Type GENESIS to confirm this is your owned or authorized device.")
    answer = input("> ").strip()
    if answer != "GENESIS":
        print("Consent token not supplied. Exiting.")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="WitnessOps consent-first genesis receipt bootstrap")
    parser.add_argument("--root", type=Path, default=None, help="USB root. Defaults to parent of bootstrap directory.")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    root = args.root.resolve() if args.root else script_path.parents[1]
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    (root / "receipts").mkdir(parents=True, exist_ok=True)
    (root / "private").mkdir(parents=True, exist_ok=True)
    (root / "seeds").mkdir(parents=True, exist_ok=True)

    require_consent()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_dir = root / "evidence" / run_id
    receipt_dir = root / "receipts" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)

    consent_event = {
        "schema": f"{SCHEMA}.consent_event.v1",
        "run_id": run_id,
        "confirmed_at": utc_now(),
        "confirmation_phrase": "GENESIS",
        "claim": "Operator confirmed owned or authorized device at visible prompt.",
    }

    baseline = {
        "schema": f"{SCHEMA}.hardware_baseline.private_hashonly.v1",
        "run_id": run_id,
        "collected_at": utc_now(),
        "privacy": "hash_only_for_host_user_and_hardware_identifiers",
        "system": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "hostname_hash": hashref_string(socket.gethostname()),
            "user_hash": hashref_string(getpass.getuser()),
        },
        "hardware_identifier_hashes": hardware_hashes(),
    }

    seed_hashes = {
        "schema": f"{SCHEMA}.seed_file_hashes.v1",
        "run_id": run_id,
        "base": "seeds/",
        "files": file_hashes(root, "seeds"),
    }

    private_hashes = {
        "schema": f"{SCHEMA}.private_evidence_hashes.v1",
        "run_id": run_id,
        "base": "private/",
        "privacy": "Only file hashes and sizes are recorded here. Raw private files are not copied into receipts.",
        "files": file_hashes(root, "private"),
    }

    script_hashes = {
        "schema": f"{SCHEMA}.bootstrap_script_hashes.v1",
        "run_id": run_id,
        "files": file_hashes(root, "bootstrap"),
    }

    artifacts = {
        "consent_event": consent_event,
        "hardware_baseline": baseline,
        "seed_file_hashes": seed_hashes,
        "private_evidence_hashes": private_hashes,
        "bootstrap_script_hashes": script_hashes,
    }

    paths: dict[str, Path] = {}
    for name, value in artifacts.items():
        p = evidence_dir / f"{name}.json"
        write_json(p, value)
        paths[name] = p

    evidence_manifest = {
        "schema": f"{SCHEMA}.evidence_manifest.v1",
        "run_id": run_id,
        "created_at": utc_now(),
        "artifacts": [
            {
                "name": name,
                "relative_path": str(path.relative_to(root)),
                "sha256": hashref_file(path),
                "bytes": path.stat().st_size,
            }
            for name, path in paths.items()
        ],
    }
    manifest_path = evidence_dir / "evidence_manifest.json"
    write_json(manifest_path, evidence_manifest)

    receipt = {
        "schema": "witnessops.genesis_receipt.v1",
        "receipt_id": "genesis_000",
        "run_id": run_id,
        "issued_at": utc_now(),
        "claim": {
            "type": "bootstrap_custody_started",
            "statement": "WitnessOps governed execution chain initialized from consent-first USB genesis bootstrap.",
            "boundary": "This proves local starting custody artifact hashes. It does not prove ownership, external execution, or third-party publication.",
        },
        "evidence": {
            "evidence_manifest_path": str(manifest_path.relative_to(root)),
            "evidence_manifest_hash": hashref_file(manifest_path),
            "private_evidence_mode": "hash_only",
        },
        "lineage": {
            "parent_receipt_id": None,
            "parent_receipt_hash": None,
        },
        "signature": {
            "algorithm": "unsigned",
            "note": "Sign this receipt later with witnessops-receipt-kit or another Ed25519 receipt signer.",
        },
    }
    receipt_path = receipt_dir / "genesis_000.json"
    write_json(receipt_path, receipt)
    sidecar = receipt_dir / "genesis_000.json.sha256"
    sidecar.write_text(f"{hashref_file(receipt_path).split(':', 1)[1]}  genesis_000.json\n", encoding="utf-8")

    print("\nGENESIS RECEIPT WRITTEN")
    print(f"run_id={run_id}")
    print(f"receipt={receipt_path}")
    print(f"receipt_sha256={hashref_file(receipt_path)}")


if __name__ == "__main__":
    main()
