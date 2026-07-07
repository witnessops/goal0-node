from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from pathlib import Path

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

    _check(checks, "schema", PASS if task.get("schema") == "vaultsovereign.grok.task_bundle.v1" else FAIL)
    _check(checks, "mode_grok_headless", PASS if execution.get("mode") == "grok_headless" else FAIL)
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

    output_format = execution.get("output_format", "json")
    allowed_formats = policy.get("allowed_output_formats", ["json", "plain", "streaming-json"])
    _check(
        checks,
        "output_format_allowed",
        PASS if output_format in allowed_formats else FAIL,
        f"output_format={output_format!r}",
    )

    if policy.get("require_json_output", True):
        _check(checks, "json_output_required", PASS if output_format == "json" else FAIL)
    else:
        _check(checks, "json_output_required", PASS, "not required by policy")

    sandbox = execution.get("sandbox")
    allowed_sandboxes = policy.get("allowed_sandboxes", ["strict", "normal"])
    if sandbox is None:
        _check(checks, "sandbox_allowed", PASS, "sandbox omitted")
    elif sandbox in allowed_sandboxes:
        _check(checks, "sandbox_allowed", PASS)
    else:
        _check(checks, "sandbox_allowed", FAIL, f"sandbox={sandbox!r}")

    max_turns = execution.get("max_turns")
    max_turns_cap = int(policy.get("max_turns_cap", 25))
    if max_turns is None:
        _check(checks, "max_turns_allowed", PASS, "defaulted at render")
    else:
        _check(
            checks,
            "max_turns_allowed",
            PASS if 1 <= int(max_turns) <= max_turns_cap else FAIL,
            f"max_turns={max_turns} cap={max_turns_cap}",
        )

    denied_flags = set(policy.get("deny_flags", []))
    requested_flags = set(execution.get("extra_flags", []) or [])
    dangerous = sorted(denied_flags.intersection(requested_flags))
    _check(checks, "dangerous_flags_absent", PASS if not dangerous else FAIL, f"found={dangerous}")

    denied_tools = set(policy.get("deny_tools", []))
    requested_tools = set(execution.get("disallowed_tools", []) or [])
    blocked = sorted(denied_tools.intersection(requested_tools))
    _check(checks, "deny_tools_not_unblocked", PASS if not blocked else FAIL, f"found={blocked}")

    allowed_tools = execution.get("allowed_tools")
    if allowed_tools is None and task_policy.get("intended_effect") == "read_only_report":
        allowed_tools = policy.get("allowed_read_only_tools", ["read_file", "grep", "list_dir"])
    policy_allowed = set(policy.get("allowed_read_only_tools", ["read_file", "grep", "list_dir"]))
    policy_denied = set(policy.get("denied_write_tools", ["run_terminal_cmd", "search_replace", "write", "delete_file", "web_search", "web_fetch"]))
    if allowed_tools is None:
        _check(checks, "allowed_tools_policy", PASS, "denylist mode")
    else:
        unknown = sorted(set(allowed_tools) - policy_allowed)
        dangerous_allowed = sorted(set(allowed_tools).intersection(policy_denied.union(denied_tools)))
        _check(checks, "allowed_tools_policy", PASS if not unknown else FAIL, f"unknown={unknown}")
        _check(checks, "allowed_tools_safe", PASS if not dangerous_allowed else FAIL, f"found={dangerous_allowed}")

    disable_web = bool(execution.get("disable_web_search", True))
    allow_web = bool(task_policy.get("allow_web_search", policy.get("allow_web_search_default", False)))
    _check(checks, "web_search_policy", PASS if (disable_web or allow_web) else FAIL)

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
        "schema": "vaultsovereign.grok.policy_verdict.v1",
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