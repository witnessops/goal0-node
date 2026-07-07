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
    if not argv or argv[0] != "grok":
        raise ValueError("argv must invoke grok")

    for flag in guards.get("deny_flags", []):
        if _argv_has_flag(argv, flag):
            raise ValueError(f"Denied flag present in argv: {flag}")

    denied_write = set(guards.get("denied_write_tools", []))
    tool_mode = guards.get("tool_mode")
    if tool_mode == "allowlist":
        allowed = set(guards.get("allowed_tools", []))
        tools_value = _argv_value(argv, "--tools")
        if not tools_value:
            raise ValueError("Read-only guarded run requires --tools allowlist in argv")
        requested = {part.strip() for part in tools_value.split(",") if part.strip()}
        unknown = sorted(requested - allowed)
        dangerous = sorted(requested.intersection(denied_write))
        if unknown:
            raise ValueError(f"argv --tools contains non-allowed tools: {unknown}")
        if dangerous:
            raise ValueError(f"argv --tools contains denied tools: {dangerous}")
    else:
        disallowed_value = _argv_value(argv, "--disallowed-tools")
        if disallowed_value:
            requested = {part.strip() for part in disallowed_value.split(",") if part.strip()}
            if requested.intersection(set(guards.get("deny_tools", []))):
                raise ValueError("argv unblocked policy-denied tools")

    if guards.get("require_disable_web_search") and not _argv_has_flag(argv, "--disable-web-search"):
        raise ValueError("Guarded run requires --disable-web-search in argv")

    sandbox = guards.get("sandbox")
    if sandbox:
        argv_sandbox = _argv_value(argv, "--sandbox")
        if argv_sandbox != sandbox:
            raise ValueError(f"argv sandbox {argv_sandbox!r} does not match guarded sandbox {sandbox!r}")