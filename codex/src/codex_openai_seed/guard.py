from __future__ import annotations

from typing import Any


def _argv_value(argv: list[str], flag: str) -> str | None:
    if flag not in argv:
        return None
    idx = argv.index(flag)
    if idx + 1 >= len(argv):
        return None
    return argv[idx + 1]


def _argv_has_flag(argv: list[str], flag: str) -> bool:
    return flag in argv


def validate_argv(argv: list[str], guards: dict[str, Any]) -> None:
    if not argv or argv[0] != "codex" or len(argv) < 2 or argv[1] != "exec":
        raise ValueError("argv must invoke codex exec")

    for flag in guards.get("deny_flags", []):
        if _argv_has_flag(argv, flag):
            raise ValueError(f"Denied flag present in argv: {flag}")

    sandbox = guards.get("sandbox")
    if sandbox:
        argv_sandbox = _argv_value(argv, "--sandbox")
        if argv_sandbox != sandbox:
            raise ValueError(f"argv sandbox {argv_sandbox!r} does not match guarded sandbox {sandbox!r}")

    if guards.get("require_json_output") and not _argv_has_flag(argv, "--json"):
        raise ValueError("Guarded run requires --json in argv")

    if guards.get("require_ephemeral") and not _argv_has_flag(argv, "--ephemeral"):
        raise ValueError("Guarded run requires --ephemeral in argv")

    if guards.get("forbid_web_search") and _argv_has_flag(argv, "--search"):
        raise ValueError("Guarded run forbids --search in argv")