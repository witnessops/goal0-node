from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .io import read_json, write_json
from .policy import validate_task
from .receipts import issue_receipt, verify_receipt
from .render import render_plan
from .runner import execute_bound_plan

app = typer.Typer(no_args_is_help=True, help="Governed OpenAI Codex CLI overlay.")
console = Console()
WOPS_ROOT = Path("/home/ops/witnessops-node")
DEFAULT_POLICY = WOPS_ROOT / "policies/codex_exec_policy.v1.json"
DEFAULT_NODE_KEY = WOPS_ROOT / "identity/private/node_ed25519.pem"


def _write(path: Path, data: object) -> None:
    write_json(path, data)
    console.print(f"[green]wrote[/green] {path}")


def _load_policy(policy: Path) -> dict:
    return read_json(policy)


@app.command("keygen")
def keygen_cmd(
    private_key: Path = typer.Option(..., "--private-key"),
    public_key: Path = typer.Option(..., "--public-key"),
) -> None:
    """Generate an Ed25519 operator keypair."""
    from .signing import generate_keypair

    generate_keypair(private_key, public_key)
    console.print(f"[green]wrote[/green] {private_key}")
    console.print(f"[green]wrote[/green] {public_key}")


@app.command("intent-hash")
def intent_hash_cmd(
    task: Path = typer.Option(..., "--task"),
) -> None:
    """Compute the operator intent hash expected for a task bundle."""
    from .lineage import operator_intent_hash

    task_obj = read_json(task)
    value = operator_intent_hash(task_obj)
    console.print_json(data={"task_id": task_obj.get("task_id"), "intent_hash": value})


@app.command("validate")
def validate_cmd(
    task: Path = typer.Option(..., "--task"),
    policy: Path = typer.Option(DEFAULT_POLICY, "--policy"),
    out: Optional[Path] = typer.Option(None, "--out"),
    strict: bool = typer.Option(True, "--strict/--no-strict"),
) -> None:
    """Validate a governed Codex task bundle against local policy."""
    task_obj = read_json(task)
    policy_obj = _load_policy(policy)
    verdict = validate_task(task_obj, policy_obj)
    out = out or WOPS_ROOT / "evidence/codex_policy" / f"{task_obj.get('task_id', 'task')}.verdict.json"
    _write(out, verdict)
    console.print_json(data=verdict)
    if strict and verdict.get("decision") != "allow":
        raise typer.Exit(code=2)


@app.command("render")
def render_cmd(
    task: Path = typer.Option(..., "--task"),
    verdict: Path = typer.Option(..., "--verdict"),
    out: Path = typer.Option(..., "--out"),
    policy: Path = typer.Option(DEFAULT_POLICY, "--policy"),
) -> None:
    """Render a codex exec argv plan. No Codex execution occurs."""
    task_obj = read_json(task)
    verdict_obj = read_json(verdict)
    policy_obj = _load_policy(policy)
    plan = render_plan(task_obj, verdict_obj, task_path=task, verdict_path=verdict, policy=policy_obj)
    _write(out, plan)
    console.print_json(data={"task_id": plan["task_id"], "plan_hash": plan["plan_hash"], "argv_preview": plan["argv"][:8] + ["..."]})


@app.command("run")
def run_cmd(
    plan: Path = typer.Option(..., "--plan"),
    out: Path = typer.Option(..., "--out"),
    task: Optional[Path] = typer.Option(None, "--task"),
    verdict: Optional[Path] = typer.Option(None, "--verdict"),
    policy: Path = typer.Option(DEFAULT_POLICY, "--policy"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    timeout_seconds: int = typer.Option(600, "--timeout-seconds"),
) -> None:
    """Dry-run or execute a rendered Codex run plan and capture evidence."""
    plan_obj = read_json(plan)
    policy_obj = _load_policy(policy)
    if task is None or verdict is None:
        raise typer.BadParameter("Bound execution requires both --task and --verdict")
    task_obj = read_json(task)
    verdict_obj = read_json(verdict)
    evidence = execute_bound_plan(
        task_obj,
        verdict_obj,
        plan_obj,
        timeout_seconds=timeout_seconds,
        secret_patterns=policy_obj.get("secret_patterns", []),
        redact_output_secrets=bool(policy_obj.get("redact_output_secrets", True)),
        dry_run=dry_run,
    )
    _write(out, evidence)
    console.print_json(data={"transport": evidence["transport"], "return_code": evidence["return_code"], "evidence_hash": evidence["evidence_hash"]})


@app.command("seal")
def seal_cmd(
    task: Path = typer.Option(..., "--task"),
    verdict: Path = typer.Option(..., "--verdict"),
    plan: Path = typer.Option(..., "--plan"),
    run: Path = typer.Option(..., "--run"),
    receipt: Path = typer.Option(..., "--receipt"),
    private_key: Optional[Path] = typer.Option(None, "--private-key"),
) -> None:
    """Issue a signed or unsigned receipt over task, verdict, plan, and execution evidence."""
    task_obj = read_json(task)
    verdict_obj = read_json(verdict)
    plan_obj = read_json(plan)
    run_obj = read_json(run)
    key_path = private_key
    if key_path is None and DEFAULT_NODE_KEY.exists():
        key_path = DEFAULT_NODE_KEY
    receipt_obj = issue_receipt(
        task_obj,
        verdict_obj,
        plan_obj,
        run_obj,
        paths={
            "task": str(task),
            "policy_verdict": str(verdict),
            "run_plan": str(plan),
            "execution_evidence": str(run),
        },
        private_key_path=key_path,
    )
    _write(receipt, receipt_obj)
    console.print_json(data={"receipt_id": receipt_obj["receipt_id"], "receipt_hash": receipt_obj["receipt_hash"], "signed": receipt_obj["signature"]["algorithm"] != "unsigned"})


@app.command("verify")
def verify_cmd(
    receipt: Path = typer.Option(..., "--receipt"),
    task: Optional[Path] = typer.Option(None, "--task"),
    verdict: Optional[Path] = typer.Option(None, "--verdict"),
    plan: Optional[Path] = typer.Option(None, "--plan"),
    run: Optional[Path] = typer.Option(None, "--run"),
    public_key: Optional[Path] = typer.Option(None, "--public-key"),
    allow_partial: bool = typer.Option(False, "--allow-partial/--strict"),
) -> None:
    """Verify receipt artifact bindings and optional Ed25519 signature."""
    receipt_obj = read_json(receipt)
    paths = receipt_obj.get("evidence_paths", {}) or {}
    selected = {
        "task": task or paths.get("task"),
        "policy_verdict": verdict or paths.get("policy_verdict"),
        "run_plan": plan or paths.get("run_plan"),
        "execution_evidence": run or paths.get("execution_evidence"),
    }
    artifacts = {name: read_json(path) for name, path in selected.items() if path and Path(path).exists()}
    if public_key is None and not receipt_obj.get("signature", {}).get("public_key_pem"):
        default_pub = WOPS_ROOT / "identity/public/node_ed25519.pub.pem"
        if default_pub.exists():
            public_key = default_pub
    report = verify_receipt(receipt_obj, artifacts=artifacts, public_key_path=public_key)
    console.print_json(data=report)
    if report.get("decision") == "fail" or (report.get("decision") == "partial" and not allow_partial):
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()