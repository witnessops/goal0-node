from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization

from .hashing import canonical_bytes, hashref_bytes, hashref_json
from .lineage import (
    assert_evidence_matches_plan,
    assert_plan_matches_task_and_verdict,
    assert_verdict_matches_task,
    operator_intent_hash,
)
from .signing import load_public_key, load_signing_key, public_key_pem_for_private, sign, verify
from .timeutil import utc_now


def _payload_for_signature(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(receipt)
    payload.pop("receipt_hash", None)
    payload["signature"] = {
        "algorithm": "unsigned",
        "note": "excluded_from_signing_payload_v1",
    }
    return payload


def issue_receipt(
    task: dict[str, Any],
    verdict: dict[str, Any],
    plan: dict[str, Any],
    run: dict[str, Any],
    paths: dict[str, str | None] | None = None,
    private_key_path: str | Path | None = None,
) -> dict[str, Any]:
    assert_verdict_matches_task(task, verdict)
    assert_plan_matches_task_and_verdict(task, verdict, plan)
    assert_evidence_matches_plan(plan, run)
    receipt = {
        "schema": "vaultsovereign.codex.receipt.v1",
        "receipt_id": "rcpt_codex_" + hashref_json(run).split(":", 1)[1][:16],
        "issued_at": utc_now(),
        "claim": {
            "type": "codex_task_policy_checked_and_execution_evidence_recorded",
            "boundary": "This receipt does not prove correctness, merge, deployment, or absence of defects.",
            "task_id": task.get("task_id"),
            "transport": run.get("transport"),
            "return_code": run.get("return_code"),
        },
        "authority": {
            "operator": task.get("operator_approval", {}).get("approved_by"),
            "operator_intent_hash": task.get("operator_approval", {}).get("intent_hash"),
            "operator_intent_expected": operator_intent_hash(task),
            "policy_verdict_hash": hashref_json(verdict),
        },
        "evidence": {
            "task_hash": hashref_json(task),
            "policy_verdict_hash": hashref_json(verdict),
            "run_plan_hash": hashref_json(plan),
            "execution_evidence_hash": hashref_json(run),
        },
        "evidence_paths": paths or {},
        "signature": {
            "algorithm": "unsigned",
            "public_key_id": None,
            "public_key_pem": None,
            "signature": None,
            "note": "No private key supplied at receipt issuance.",
        },
    }
    if private_key_path:
        private_key = load_signing_key(private_key_path)
        payload = _payload_for_signature(receipt)
        payload_bytes = canonical_bytes(payload)
        public_path = Path(private_key_path).parent.parent / "public" / "node_ed25519.pub.pem"
        receipt["signature"] = {
            "algorithm": "ed25519",
            "public_key_id": "debian-codex-node-ed25519-v1",
            "public_key_path": str(public_path) if public_path.exists() else None,
            "public_key_pem": public_key_pem_for_private(private_key_path),
            "signature_encoding": "base64",
            "signature": sign(private_key, payload_bytes),
            "signed_payload_hash": hashref_bytes(payload_bytes),
        }
    receipt["receipt_hash"] = hashref_json(receipt)
    return receipt


def _verify_hash(report: dict[str, Any], name: str, obj: dict[str, Any], expected: str | None) -> None:
    observed = hashref_json(obj)
    report["checks"].append({
        "id": f"{name}_hash",
        "result": "pass" if expected and observed == expected else "fail",
        "expected": expected,
        "observed": observed,
    })


def verify_receipt(
    receipt: dict[str, Any],
    artifacts: dict[str, dict[str, Any]] | None = None,
    public_key_path: str | Path | None = None,
) -> dict[str, Any]:
    artifacts = artifacts or {}
    evidence = receipt.get("evidence", {})
    report = {
        "schema": "vaultsovereign.codex.verifier_report.v1",
        "receipt_id": receipt.get("receipt_id"),
        "checked_at": utc_now(),
        "checks": [],
    }
    for name, key in [
        ("task", "task_hash"),
        ("policy_verdict", "policy_verdict_hash"),
        ("run_plan", "run_plan_hash"),
        ("execution_evidence", "execution_evidence_hash"),
    ]:
        if name in artifacts:
            _verify_hash(report, name, artifacts[name], evidence.get(key))
        else:
            report["checks"].append({"id": f"{name}_hash", "result": "skip", "detail": "artifact not supplied"})

    sig = receipt.get("signature", {})
    if sig.get("algorithm") == "ed25519":
        signed_receipt = deepcopy(receipt)
        signed_receipt.pop("receipt_hash", None)
        payload = _payload_for_signature(signed_receipt)
        payload_bytes = canonical_bytes(payload)
        key_path = public_key_path
        if key_path is None and sig.get("public_key_path"):
            key_path = Path(sig["public_key_path"])
        if key_path and Path(key_path).exists():
            public_key = load_public_key(key_path)
        else:
            pem = sig.get("public_key_pem")
            if pem and "BEGIN PUBLIC KEY" in pem:
                public_key = serialization.load_pem_public_key(pem.encode("utf-8"))
            elif pem:
                import tempfile

                with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
                    handle.write(pem)
                    temp_path = Path(handle.name)
                try:
                    public_key = load_public_key(temp_path)
                finally:
                    temp_path.unlink(missing_ok=True)
            else:
                public_key = None
        ok = bool(public_key and verify(public_key, sig.get("signature", ""), payload_bytes))
        report["checks"].append({"id": "signature", "result": "pass" if ok else "fail"})
    else:
        report["checks"].append({"id": "signature", "result": "skip", "detail": "receipt is unsigned"})

    task_obj = artifacts.get("task")
    verdict_obj = artifacts.get("policy_verdict")
    plan_obj = artifacts.get("run_plan")
    run_obj = artifacts.get("execution_evidence")
    if task_obj and verdict_obj:
        try:
            assert_verdict_matches_task(task_obj, verdict_obj)
            report["checks"].append({"id": "task_verdict_lineage", "result": "pass"})
        except ValueError as exc:
            report["checks"].append({"id": "task_verdict_lineage", "result": "fail", "detail": str(exc)})
    if task_obj and verdict_obj and plan_obj:
        try:
            assert_plan_matches_task_and_verdict(task_obj, verdict_obj, plan_obj)
            report["checks"].append({"id": "task_plan_lineage", "result": "pass"})
        except ValueError as exc:
            report["checks"].append({"id": "task_plan_lineage", "result": "fail", "detail": str(exc)})
    if plan_obj and run_obj:
        try:
            assert_evidence_matches_plan(plan_obj, run_obj)
            report["checks"].append({"id": "plan_evidence_lineage", "result": "pass"})
        except ValueError as exc:
            report["checks"].append({"id": "plan_evidence_lineage", "result": "fail", "detail": str(exc)})
    if task_obj:
        expected = operator_intent_hash(task_obj)
        observed = task_obj.get("operator_approval", {}).get("intent_hash")
        report["checks"].append({
            "id": "operator_intent_bound",
            "result": "pass" if observed == expected else "fail",
            "expected": expected,
            "observed": observed,
        })

    hard = [c["result"] for c in report["checks"] if c["result"] != "skip"]
    report["decision"] = "pass" if hard and all(r == "pass" for r in hard) else "partial" if not hard else "fail"
    return report