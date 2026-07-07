from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .gitutil import git_diff_binary, git_head, git_status_porcelain
from .guard import validate_argv
from .hashing import hashref_json, sha256_bytes
from .lineage import assert_evidence_matches_plan, assert_plan_matches_task_and_verdict, plan_body_hash
from .redaction import redact_secrets, scan_secrets
from .timeutil import utc_now


def _repo_from_plan(plan: dict[str, Any]) -> Path:
    argv = plan.get("argv", [])
    if "--cwd" in argv:
        idx = argv.index("--cwd")
        if idx + 1 < len(argv):
            return Path(argv[idx + 1])
    return Path(".")


def _prompt_present(argv: list[str]) -> bool:
    return "-p" in argv or "--prompt" in argv or "--single" in argv or "--prompt-file" in argv


def _prepare_output(
    stdout: str,
    stderr: str,
    secret_patterns: list[str],
    redact_output_secrets: bool,
) -> tuple[str, str, dict[str, Any]]:
    meta: dict[str, Any] = {
        "stdout_secret_patterns": scan_secrets(stdout, secret_patterns),
        "stderr_secret_patterns": scan_secrets(stderr, secret_patterns),
    }
    if not redact_output_secrets:
        return stdout, stderr, meta
    stdout, stdout_hits = redact_secrets(stdout, secret_patterns)
    stderr, stderr_hits = redact_secrets(stderr, secret_patterns)
    meta["stdout_redacted_patterns"] = stdout_hits
    meta["stderr_redacted_patterns"] = stderr_hits
    meta["output_redacted"] = bool(stdout_hits or stderr_hits)
    return stdout, stderr, meta


def dry_run_evidence(plan: dict[str, Any]) -> dict[str, Any]:
    validate_argv(plan.get("argv", []), plan.get("guards", {}))
    started = utc_now()
    stdout = {
        "dry_run": True,
        "argv": plan.get("argv", []),
        "note": "Grok CLI was not executed.",
    }
    evidence = {
        "schema": "vaultsovereign.grok.execution_evidence.v1",
        "task_id": plan.get("task_id"),
        "started_at": started,
        "finished_at": utc_now(),
        "transport": "dry_run",
        "return_code": 0,
        "stdout": stdout,
        "stderr": "",
        "grok_binary": shutil.which("grok"),
        "git": {
            "repo": str(_repo_from_plan(plan)),
            "head_before": None,
            "head_after": None,
            "status_before": None,
            "status_after": None,
            "diff_sha256": None,
            "diff_bytes": 0,
        },
        "plan_hash": hashref_json(plan),
        "plan_body_hash": plan_body_hash(plan),
        "output_handling": {"mode": "dry_run"},
    }
    evidence["evidence_hash"] = hashref_json(evidence)
    return evidence


def execute_plan(
    plan: dict[str, Any],
    timeout_seconds: int = 600,
    secret_patterns: list[str] | None = None,
    redact_output_secrets: bool = True,
) -> dict[str, Any]:
    argv = plan.get("argv", [])
    if not argv or argv[0] != "grok":
        raise ValueError("Run plan must render a grok argv vector")
    if not _prompt_present(argv):
        raise ValueError("Run plan must include a Grok prompt flag")
    if not shutil.which("grok"):
        raise FileNotFoundError("grok binary not found on PATH; rerun with --dry-run or install Grok CLI")
    validate_argv(argv, plan.get("guards", {}))

    repo = _repo_from_plan(plan)
    started = utc_now()
    head_before = git_head(repo)
    status_before = git_status_porcelain(repo)
    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        shell=False,
    )
    diff = git_diff_binary(repo) or ""
    patterns = secret_patterns or []
    stdout, stderr, output_meta = _prepare_output(
        proc.stdout,
        proc.stderr,
        patterns,
        redact_output_secrets=redact_output_secrets,
    )
    evidence = {
        "schema": "vaultsovereign.grok.execution_evidence.v1",
        "task_id": plan.get("task_id"),
        "started_at": started,
        "finished_at": utc_now(),
        "transport": "grok_cli",
        "return_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "grok_binary": shutil.which("grok"),
        "git": {
            "repo": str(repo),
            "head_before": head_before,
            "head_after": git_head(repo),
            "status_before": status_before,
            "status_after": git_status_porcelain(repo),
            "diff_sha256": sha256_bytes(diff.encode("utf-8")) if diff else None,
            "diff_bytes": len(diff.encode("utf-8")),
        },
        "plan_hash": hashref_json(plan),
        "plan_body_hash": plan_body_hash(plan),
        "output_handling": output_meta,
    }
    evidence["evidence_hash"] = hashref_json(evidence)
    return evidence


def execute_bound_plan(
    task: dict[str, Any],
    verdict: dict[str, Any],
    plan: dict[str, Any],
    timeout_seconds: int = 600,
    secret_patterns: list[str] | None = None,
    redact_output_secrets: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    assert_plan_matches_task_and_verdict(task, verdict, plan)
    evidence = dry_run_evidence(plan) if dry_run else execute_plan(
        plan,
        timeout_seconds=timeout_seconds,
        secret_patterns=secret_patterns,
        redact_output_secrets=redact_output_secrets,
    )
    assert_evidence_matches_plan(plan, evidence)
    return evidence