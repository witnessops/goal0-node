from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(repo: str | Path, args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=Path(repo),
        text=True,
        capture_output=True,
        timeout=timeout,
        shell=False,
    )
    return result.returncode, result.stdout, result.stderr


def git_available(repo: str | Path) -> bool:
    try:
        code, _, _ = run_git(repo, ["rev-parse", "--is-inside-work-tree"])
        return code == 0
    except Exception:
        return False


def git_head(repo: str | Path) -> str | None:
    if not git_available(repo):
        return None
    code, out, _ = run_git(repo, ["rev-parse", "HEAD"])
    return out.strip() if code == 0 else None


def git_status_porcelain(repo: str | Path) -> str | None:
    if not git_available(repo):
        return None
    code, out, _ = run_git(repo, ["status", "--porcelain=v1"])
    return out if code == 0 else None


def git_diff_binary(repo: str | Path) -> str | None:
    if not git_available(repo):
        return None
    code, out, _ = run_git(repo, ["diff", "--binary"])
    return out if code == 0 else None
