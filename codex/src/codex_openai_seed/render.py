from __future__ import annotations

from pathlib import Path
from typing import Any

from .gitutil import git_available
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
        "- Do not bypass sandboxing or approvals.",
        "- Do not print or persist secrets.",
        "- Keep claims scoped to observed evidence.",
    ])
    return "\n".join(parts).strip()


def render_argv(task: dict[str, Any]) -> list[str]:
    execution = task.get("execution", {})
    target = task.get("target_repo", {})
    argv = ["codex", "exec"]
    if execution.get("json", True):
        argv.append("--json")
    if execution.get("ephemeral", True):
        argv.append("--ephemeral")
    if execution.get("sandbox"):
        argv.extend(["--sandbox", execution["sandbox"]])
    # ask_for_approval is validated by policy.py but omitted from argv because
    # codex CLI 0.142.5 does not support --ask-for-approval.
    if target.get("path"):
        repo_path = target["path"]
        argv.extend(["--cd", repo_path])
        if not git_available(repo_path):
            argv.append("--skip-git-repo-check")
    if execution.get("model"):
        argv.extend(["--model", execution["model"]])
    if execution.get("profile"):
        argv.extend(["--profile", execution["profile"]])
    if execution.get("web_search"):
        argv.append("--search")
    for flag in execution.get("extra_flags", []) or []:
        argv.append(flag)
    argv.append(render_prompt(task))
    return argv


def render_guards(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    execution = task.get("execution", {})
    task_policy = task.get("policy", {})
    allow_web = bool(task_policy.get("allow_web_search", policy.get("allow_web_search_default", False)))
    return {
        "deny_flags": list(policy.get("deny_flags", [])),
        "sandbox": execution.get("sandbox"),
        "require_json_output": bool(execution.get("json", policy.get("require_json_output", True))),
        "require_ephemeral": bool(execution.get("ephemeral", True)),
        "forbid_web_search": not bool(execution.get("web_search", False)) and not allow_web,
    }


def render_plan(
    task: dict[str, Any],
    verdict: dict[str, Any],
    task_path: str | Path | None = None,
    verdict_path: str | Path | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assert_verdict_matches_task(task, verdict)
    plan = {
        "schema": "vaultsovereign.codex.run_plan.v1",
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
            "No OpenAI API key or access token is persisted in the plan.",
            "Prompt text is persisted by design; policy rejects common secret patterns before rendering.",
        ],
        "claim_boundary": "Plan only: no Codex execution has occurred.",
    }
    plan["plan_hash"] = plan_body_hash(plan)
    return plan