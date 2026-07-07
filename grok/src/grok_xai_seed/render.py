from __future__ import annotations

from pathlib import Path
from typing import Any

from .hashing import hashref_json
from .lineage import assert_verdict_matches_task, plan_body_hash
from .timeutil import utc_now


def render_prompt(task: dict[str, Any]) -> str:
    prompt = task.get("prompt", {})
    parts = [prompt.get("instruction", "")]
    if prompt.get("context"):
        parts.extend(["", "Context:", prompt["context"]])
    parts.extend([
        "",
        "Governance constraints:",
        "- Do not bypass sandboxing or permission controls.",
        "- Do not print or persist secrets.",
        "- Keep claims scoped to observed evidence.",
    ])
    return "\n".join(parts).strip()


def _default_allowed_tools(task: dict[str, Any]) -> list[str]:
    task_policy = task.get("policy", {})
    intended = task_policy.get("intended_effect", "read_only_report")
    if intended == "read_only_report":
        return ["read_file", "grep", "list_dir"]
    return []


def _default_disallowed_tools(task: dict[str, Any]) -> list[str]:
    task_policy = task.get("policy", {})
    intended = task_policy.get("intended_effect", "read_only_report")
    if intended == "read_only_report":
        return [
            "run_terminal_cmd",
            "web_search",
            "web_fetch",
            "search_replace",
            "write",
            "delete_file",
        ]
    if intended == "workspace_write":
        base = ["web_search", "web_fetch"]
        if not task_policy.get("allow_shell", False):
            base.insert(0, "run_terminal_cmd")
        return base
    return ["web_search", "web_fetch"]


def render_argv(task: dict[str, Any]) -> list[str]:
    execution = task.get("execution", {})
    target = task.get("target_repo", {})
    argv = ["grok"]

    output_format = execution.get("output_format", "json")
    argv.extend(["--output-format", output_format])

    if execution.get("model"):
        argv.extend(["-m", execution["model"]])

    if target.get("path"):
        argv.extend(["--cwd", target["path"]])

    max_turns = execution.get("max_turns", 8)
    argv.extend(["--max-turns", str(max_turns)])

    if execution.get("sandbox"):
        argv.extend(["--sandbox", execution["sandbox"]])

    if execution.get("disable_web_search", True):
        argv.append("--disable-web-search")

    allowed = execution.get("allowed_tools")
    if allowed is None and task.get("policy", {}).get("intended_effect") == "read_only_report":
        allowed = _default_allowed_tools(task)
    if allowed:
        argv.extend(["--tools", ",".join(allowed)])
    else:
        disallowed = execution.get("disallowed_tools")
        if disallowed is None:
            disallowed = _default_disallowed_tools(task)
        if disallowed:
            argv.extend(["--disallowed-tools", ",".join(disallowed)])

    for flag in execution.get("extra_flags", []) or []:
        argv.append(flag)

    argv.extend(["-p", render_prompt(task)])
    return argv


def render_guards(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    execution = task.get("execution", {})
    task_policy = task.get("policy", {})
    allowed = execution.get("allowed_tools")
    if allowed is None and task_policy.get("intended_effect") == "read_only_report":
        allowed = _default_allowed_tools(task)
    guards = {
        "deny_flags": list(policy.get("deny_flags", [])),
        "deny_tools": list(policy.get("deny_tools", [])),
        "denied_write_tools": list(policy.get("denied_write_tools", [])),
        "require_disable_web_search": bool(execution.get("disable_web_search", True)),
        "sandbox": execution.get("sandbox"),
        "tool_mode": "allowlist" if allowed else "denylist",
        "allowed_tools": allowed or [],
    }
    return guards


def render_plan(
    task: dict[str, Any],
    verdict: dict[str, Any],
    task_path: str | Path | None = None,
    verdict_path: str | Path | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assert_verdict_matches_task(task, verdict)
    plan = {
        "schema": "vaultsovereign.grok.run_plan.v1",
        "task_id": task.get("task_id"),
        "created_at": utc_now(),
        "argv": render_argv(task),
        "guards": render_guards(task, policy or {}),
        "lineage": {
            "task_path": str(task_path) if task_path else None,
            "policy_verdict_path": str(verdict_path) if verdict_path else None,
            "task_hash": hashref_json(task),
            "policy_verdict_hash": hashref_json(verdict),
        },
        "redactions": [
            "No xAI API key or access token is persisted in the plan.",
            "Prompt text is persisted by design; policy rejects common secret patterns before rendering.",
        ],
        "claim_boundary": "Plan only: no Grok execution has occurred.",
    }
    plan["plan_hash"] = plan_body_hash(plan)
    return plan