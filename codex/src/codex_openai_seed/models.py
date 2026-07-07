from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class TargetRepo(StrictModel):
    name: str
    path: str = "."
    remote: str | None = None
    expected_root_markers: list[str] = []


class Prompt(StrictModel):
    instruction: str
    context: str | None = None


class Execution(StrictModel):
    mode: str = "codex_exec"
    sandbox: str = "read-only"
    ask_for_approval: str = "never"
    json: bool = True
    ephemeral: bool = True
    web_search: bool = False
    model: str | None = None
    profile: str | None = None
    extra_flags: list[str] = []


class TaskBundle(StrictModel):
    schema: str = Field(pattern="^vaultsovereign\\.codex\\.task_bundle\\.v1$")
    task_id: str
    target_repo: TargetRepo
    prompt: Prompt
    execution: Execution
    policy: dict[str, Any]
    operator_approval: dict[str, Any]
