class CodexSeedError(Exception):
    """Base exception for codex-openai-seed."""


class PolicyDenied(CodexSeedError):
    """Task was denied by policy."""


class ExecutionError(CodexSeedError):
    """Codex execution failed before evidence could be captured."""


class VerificationError(CodexSeedError):
    """Receipt verification failed."""
