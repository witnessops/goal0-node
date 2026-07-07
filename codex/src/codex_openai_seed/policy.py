from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .hashing import hashref_json
from .lineage import operator_intent_hash
from .timeutil import utc_now

PASS = "pass"
FAIL = "fail"


def _check(checks: list[dict[str, Any]], check_id: str, result: str, detail: str = "") -> None:
    entry = {"id": check_id, "result": result}
    if detail:
        entry["detail"] = detail
    checks.append(entry)


def prompt_text(task: dict[str, Any]) -> str:
    prompt = task.get("prompt", {})
    return "\n".join(str(prompt.get(k, "")) for k in ("instruction", "context"))


def validate_task(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    execution = task.get("execution", {})
    task_policy = task.get("policy", {})
    approval = task.get("operator_approval", {})
    text = prompt_text(task)

    _check(checks, "schema", PASS if task.get("schema") == "vaultsovereign.codex.task_bundle.v1" else FAIL)
    _check(checks, "mode_codex_exec", PASS if execution.get("mode") == "codex_exec" else FAIL)
    _check(checks, "prompt_present", PASS if text.strip() else FAIL)
    max_chars = int(policy.get("max_prompt_chars", 12000))
    _check(checks, "prompt_size", PASS if len(text) <= max_chars else FAIL, f"chars={len(text)} max={max_chars}")

    if policy.get("require_operator_approval", True):
        ok = bool(approval.get("approved_by") and approval.get("approved_at") and approval.get("intent_hash"))
        _check(checks, "operator_approval_present", PASS if ok else FAIL)
        expected_intent = operator_intent_hash(task)
        _check(
            checks,
            "operator_intent_bound",
            PASS if approval.get("intent_hash") == expected_intent else FAIL,
            f"expected={expected_intent}",
        )
    else:
        _check(checks, "operator_approval_present", PASS, "not required by policy")
        _check(checks, "operator_intent_bound", PASS, "not required by policy")

    sandbox = execution.get("sandbox")
    allowed_sandboxes = policy.get("allowed_sandboxes", ["read-only", "workspace-write"])
    task_allows_danger = bool(task_policy.get("allow_danger_full_access"))
    policy_allows_danger = bool(policy.get("allow_danger_full_access"))
    if sandbox in allowed_sandboxes:
        _check(checks, "sandbox_allowed", PASS)
    elif sandbox == "danger-full-access" and task_allows_danger and policy_allows_danger:
        _check(checks, "sandbox_allowed", PASS, "danger-full-access explicitly allowed")
    else:
        _check(checks, "sandbox_allowed", FAIL, f"sandbox={sandbox!r}")

    approval_mode = execution.get("ask_for_approval")
    _check(
        checks,
        "approval_mode_allowed",
        PASS if approval_mode in policy.get("allowed_approval_modes", []) else FAIL,
        f"ask_for_approval={approval_mode!r}",
    )

    denied_flags = set(policy.get("deny_flags", []))
    requested_flags = set(execution.get("extra_flags", []) or [])
    dangerous = sorted(denied_flags.intersection(requested_flags))
    _check(checks, "dangerous_flags_absent", PASS if not dangerous else FAIL, f"found={dangerous}")

    web_search = bool(execution.get("web_search", False))
    allow_web = bool(task_policy.get("allow_web_search", policy.get("allow_web_search_default", False)))
    _check(checks, "web_search_policy", PASS if (not web_search or allow_web) else FAIL)

    secret_hits = []
    for pattern in policy.get("secret_patterns", []):
        if re.search(pattern, text):
            secret_hits.append(pattern)
    _check(checks, "secrets_absent", PASS if not secret_hits else FAIL, f"matched_patterns={secret_hits}")

    target_repo = task.get("target_repo", {})
    repo_path = Path(str(target_repo.get("path", ".")))
    _check(checks, "target_repo_path_shape", PASS if str(repo_path) else FAIL)
    if policy.get("require_target_repo_exists", True):
        _check(checks, "target_repo_exists", PASS if repo_path.exists() else FAIL, f"path={repo_path}")
    else:
        _check(checks, "target_repo_exists", PASS, "not required by policy")
    markers = target_repo.get("expected_root_markers", []) or []
    if markers and policy.get("require_expected_root_markers", True):
        missing = [marker for marker in markers if not (repo_path / marker).exists()]
        _check(checks, "expected_root_markers_present", PASS if not missing else FAIL, f"missing={missing}")
    else:
        _check(checks, "expected_root_markers_present", PASS, "not required or no markers configured")

    decision = "allow" if all(c["result"] == PASS for c in checks) else "deny"
    verdict = {
        "schema": "vaultsovereign.codex.policy_verdict.v1",
        "task_id": task.get("task_id"),
        "policy_version": policy.get("policy_version", policy.get("schema", "unknown")),
        "decision": decision,
        "checked_at": utc_now(),
        "checks": checks,
        "task_hash": hashref_json(task),
    }
    base = deepcopy(verdict)
    verdict["verdict_hash"] = hashref_json(base)
    return verdict
