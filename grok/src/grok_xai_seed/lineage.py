from __future__ import annotations

from copy import deepcopy
from typing import Any

from .hashing import hashref_json


def operator_intent_hash(task: dict[str, Any]) -> str:
    approval = task.get("operator_approval", {})
    task_body = deepcopy(task)
    task_body.get("operator_approval", {}).pop("intent_hash", None)
    payload = {
        "task_id": task.get("task_id"),
        "task_body_hash": hashref_json(task_body),
        "approved_by": approval.get("approved_by"),
        "approved_at": approval.get("approved_at"),
    }
    return hashref_json(payload)


def plan_body_hash(plan: dict[str, Any]) -> str:
    body = deepcopy(plan)
    body.pop("plan_hash", None)
    return hashref_json(body)


def assert_verdict_matches_task(task: dict[str, Any], verdict: dict[str, Any]) -> None:
    if verdict.get("decision") != "allow":
        raise ValueError("Policy verdict decision must be allow")
    if verdict.get("task_id") != task.get("task_id"):
        raise ValueError("Verdict task_id does not match task bundle")
    if verdict.get("task_hash") != hashref_json(task):
        raise ValueError("Verdict task_hash does not match task bundle")


def assert_plan_matches_task_and_verdict(
    task: dict[str, Any],
    verdict: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    assert_verdict_matches_task(task, verdict)
    if plan.get("task_id") != task.get("task_id"):
        raise ValueError("Plan task_id does not match task bundle")
    lineage = plan.get("lineage", {})
    if lineage.get("task_hash") != hashref_json(task):
        raise ValueError("Plan lineage task_hash does not match task bundle")
    if lineage.get("policy_verdict_hash") != hashref_json(verdict):
        raise ValueError("Plan lineage policy_verdict_hash does not match verdict")
    if plan.get("plan_hash") != plan_body_hash(plan):
        raise ValueError("Plan plan_hash does not match plan body")


def assert_evidence_matches_plan(plan: dict[str, Any], evidence: dict[str, Any]) -> None:
    if evidence.get("task_id") != plan.get("task_id"):
        raise ValueError("Evidence task_id does not match plan")
    if evidence.get("plan_hash") != hashref_json(plan):
        raise ValueError("Evidence plan_hash does not match plan")